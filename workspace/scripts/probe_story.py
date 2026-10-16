"""뱅크 6 $DA00-$DCE8 비압축 문자열 영역 전체 해독.

인코딩 가설(네임테이블 실측 기반):
- 타일 = 저장 바이트 - 0x2F
- A-Z/구두점/공백은 ASCII 그대로, 히라가나는 0x6A(あ)부터 오십음순
- 접두/종료 바이트 구조는 덤프로 판별

실행: python workspace/scripts/probe_story.py
출력: workspace/analysis/story_strings.txt
"""
from __future__ import annotations

import btlib

REGION_LO = 0xDA00
REGION_HI = 0xDCE8

# 타일 0x3B(あ)~ 오십음. 네임테이블 실측: あ=3B, る=63, ん=68 가정 검증용
GOJUON = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"


def tile_repr(t: int) -> str:
    if t == 0x00:
        return "␣"  # 공백 타일(스토리 화면 배경)
    if 0x01 <= t <= 0x0B:
        return "0123456789?"[t - 1] if t <= 0x0B else "?"
    if t == 0x0D:
        return "-"
    if 0x12 <= t <= 0x2B:
        return chr(ord("A") + t - 0x12)
    if 0x3B <= t <= 0x3B + len(GOJUON) - 1:
        return GOJUON[t - 0x3B]
    return f"[{t + 0x2F:02X}]"


def byte_repr(b: int) -> str:
    if b == 0x20:
        return " "
    if 0x21 <= b <= 0x7E and not 0x6A <= b:
        return chr(b)
    return tile_repr((b - 0x2F) & 0xFF)


STRINGS_LO = 0xDA3F  # $DA00 렌더러의 RTS 직후
STRINGS_HI = 0xDD08  # 이후는 ASCII→타일 테이블($DCE8+0x20 유효 구간)


def parse_strings(prg: bytes) -> list[tuple[int, int, bytes]]:
    """[(cpu주소, PPU주소, 본문바이트)] 목록. 형식: [PPU hi][PPU lo][chars...][00]"""
    out = []
    cpu = STRINGS_LO
    while cpu < STRINGS_HI:
        hi = btlib.b6(prg, cpu)
        lo = btlib.b6(prg, cpu + 1)
        if not 0x20 <= hi <= 0x23:
            raise SystemExit(f"${cpu:04X}: PPU 상위 바이트가 아니다: {hi:02X}")
        body = bytearray()
        p = cpu + 2
        while (b := btlib.b6(prg, p)) != 0x00:
            body.append(b)
            p += 1
        out.append((cpu, (hi << 8) | lo, bytes(body)))
        cpu = p + 1
    return out


def main() -> None:
    prg = btlib.load_prg()
    data = btlib.b6_slice(prg, REGION_LO, REGION_HI - REGION_LO)
    lines: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hexs = chunk.hex(" ").upper()
        text = "".join(byte_repr(b) for b in chunk)
        lines.append(f"${REGION_LO + i:04X}: {hexs:<47} | {text}")

    lines.append("")
    lines.append("# 문자열 파싱 (형식: [PPU hi][PPU lo][chars...][00])")
    strs = parse_strings(prg)
    kana_pool: set[int] = set()
    for cpu, ppu, body in strs:
        text = "".join(btlib.sym_repr(b) for b in body)
        kana_pool.update(b for b in body if 0xA1 <= b <= 0xDF)
        row, col = divmod(ppu - 0x2000, 32)
        lines.append(f"${cpu:04X} ppu ${ppu:04X} (r{row:02d} c{col:02d}) len {len(body):3d}: {text}")
    lines.append("")
    lines.append(f"총 {len(strs)}개 문자열, 블록 ${STRINGS_LO:04X}~${STRINGS_HI - 1:04X} ({STRINGS_HI - STRINGS_LO} bytes)")
    lines.append(f"가나 종류 {len(kana_pool)}개: " + " ".join(f"{k:02X}" for k in sorted(kana_pool)))

    out = btlib.ROOT / "workspace" / "analysis" / "story_strings.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {out} ({len(strs)} strings)")


if __name__ == "__main__":
    main()
