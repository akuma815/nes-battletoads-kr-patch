"""한글 문장 PoC ROM 생성: 인트로 문자열(ID 0)을 한글로 교체.

방식(인코딩 무변경):
- 문장의 한글 음절을 기존 심볼 테이블의 가나 코드에 1:1로 임시 배정하고,
  해당 가나 글리프(뱅크1 $8337+id*8)를 Galmuri 음절 글리프로 교체한다.
- 문자열 0만 새 심볼열로 바꾸고 104개 전체를 기존 트리로 재인코드,
  포인터 테이블 26엔트리를 재생성한다.
- 제약: 스트림 뒤($FAE5~)에 다른 데이터가 있으므로 총 스트림은 원본
  4181바이트 이내여야 한다. 빈도 높은 음절에 짧은 코드를 배정해 맞춘다.

실행: python workspace/scripts/make_poc_sentence.py
출력: build/poc_sentence.nes, workspace/analysis/poc_sentence_map.txt
"""
from __future__ import annotations

from collections import Counter

from PIL import Image, ImageDraw, ImageFont

import btlib

FONT_TTF = btlib.ROOT.parents[1] / "Font" / "Galmuri8x8.ttf"
ROM_OUT = btlib.ROOT / "build" / "poc_sentence.nes"
MAP_OUT = btlib.ROOT / "workspace" / "analysis" / "poc_sentence_map.txt"

FONT_BASE_FILE = 0x10 + 0x8337  # 뱅크1 CPU $8337
STREAM_FILE = 0x10 + btlib.BANK6 + (btlib.ADDR_STREAM + 7 - 0x8000)
PTR_FILE = 0x10 + btlib.BANK6 + (btlib.ADDR_PTR - 0x8000)
MAX_STREAM_BYTES = 4181  # 원본 크기. $FAE5부터는 다른 데이터라 넘으면 안 된다.
MAX_SLOTS = 59  # $07C5~$07FF 워킹셋

# 새 인트로. None = 제어 토큰(원본 그대로), str = 표시 문자.
LINES = [
    "         RASH! ZITZ! 큰일이다!",
    (0x83, "PIMPLE과 ANGELICA공주가"),
    (0x84, "DARKQUEEN에게 납치되었다!"),
    (0x81, "둘은 전함 GARGANTUA에 있는 듯하다"),
    (0x85, "둘을 구출해 다오!"),
]


def render_8x8(ch: str, font: ImageFont.FreeTypeFont) -> bytes:
    img = Image.new("L", (16, 16), 0)
    ImageDraw.Draw(img).text((0, 0), ch, font=font, fill=255)
    px = img.load()
    rows = []
    for y in range(8):
        b = 0
        for x in range(8):
            if px[x, y] > 127:
                b |= 0x80 >> x
        rows.append(b)
    if not any(rows):
        raise SystemExit(f"글리프가 비어 있다: {ch!r}")
    return bytes(rows)


def main() -> None:
    prg = btlib.load_prg()
    t = btlib.Tables(prg)
    codes = t.codebook()
    strings = btlib.extract_all(prg)

    # 배정 가능한 가나 심볼(0xA1~0xDD)을 코드 길이 오름차순으로
    kana_pool = sorted(
        (s for s in codes if 0xA1 <= s <= 0xDD),
        key=lambda s: (len(codes[s]), s),
    )

    # 문장 -> 음절 빈도
    hangul: Counter[str] = Counter()
    for line in LINES:
        text = line if isinstance(line, str) else line[1]
        for ch in text:
            if ord(ch) > 0x7E:
                hangul[ch] += 1
    syllables = [ch for ch, _ in hangul.most_common()]
    if len(syllables) > len(kana_pool):
        raise SystemExit(f"음절 {len(syllables)} > 가용 가나 심볼 {len(kana_pool)}")
    mapping = {ch: kana_pool[i] for i, ch in enumerate(syllables)}

    # 새 문자열 0 심볼열
    new0: list[int] = []
    for i, line in enumerate(LINES):
        if isinstance(line, tuple):
            ctrl, text = line
            new0 += [btlib.SYM_NL, ctrl]
        else:
            text = line
        for ch in text:
            new0.append(mapping[ch] if ord(ch) > 0x7E else ord(ch))
    for s in new0:
        if s not in codes:
            raise SystemExit(f"심볼 테이블에 없는 코드 {s:#04x}")

    # 워킹셋 슬롯 수 검사(공백 포함 고유 글리프, $8x 제어 제외)
    uniq = {s for s in new0 if not (0x80 <= s <= 0x9F) and s != btlib.SYM_NL}
    if len(uniq) > MAX_SLOTS:
        raise SystemExit(f"고유 글리프 {len(uniq)} > 슬롯 {MAX_SLOTS}")

    # 재인코드
    old_bits = sum(len(codes[s]) for s in strings[0] + [btlib.SYM_END])
    new_bits = sum(len(codes[s]) for s in new0 + [btlib.SYM_END])
    strings[0] = new0
    stream_bits: list[str] = []
    bitpos = 0
    entries: list[tuple[int, int]] = []
    for i, syms in enumerate(strings):
        if i % 4 == 0:
            entries.append(btlib.make_pointer_entry(bitpos))
        for s in syms + [btlib.SYM_END]:
            stream_bits.append(codes[s])
            bitpos += len(codes[s])
    bits = "".join(stream_bits)
    n_bytes = (len(bits) + 7) // 8
    print(f"문자열 0: {old_bits}→{new_bits}비트 ({new_bits - old_bits:+d}), 총 스트림 {n_bytes}바이트 (한도 {MAX_STREAM_BYTES})")
    if n_bytes > MAX_STREAM_BYTES:
        raise SystemExit("스트림이 원본 영역을 넘는다. 문장을 줄여라.")

    stream = bytearray()
    for i in range(n_bytes):
        chunk = bits[i * 8 : (i + 1) * 8]
        stream.append(int(chunk.ljust(8, "0"), 2))

    # ROM 패치
    raw = bytearray(btlib.ROM_PATH.read_bytes())
    raw[STREAM_FILE : STREAM_FILE + n_bytes] = stream
    for e, (lo, hi) in enumerate(entries):
        raw[PTR_FILE + e * 2] = lo
        raw[PTR_FILE + e * 2 + 1] = hi

    font = ImageFont.truetype(str(FONT_TTF), 16)
    map_lines = [f"음절 {len(syllables)}개, 고유 글리프 {len(uniq)}/{MAX_SLOTS}", ""]
    for ch, kana in mapping.items():
        gid = kana - 0x72
        off = FONT_BASE_FILE + gid * 8
        raw[off : off + 8] = render_8x8(ch, font)
        map_lines.append(
            f"{ch} -> kana {kana:02X} ({btlib.sym_repr(kana)}) glyph {gid:02X} file+{off:#x} code {codes[kana]} ({len(codes[kana])}b)"
        )

    ROM_OUT.write_bytes(raw)
    MAP_OUT.write_text("\n".join(map_lines), encoding="utf-8")
    print(f"PoC ROM: {ROM_OUT}")
    print(f"매핑표: {MAP_OUT}")


if __name__ == "__main__":
    main()
