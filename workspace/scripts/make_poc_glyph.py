"""가시성 PoC ROM 생성: 컷신 폰트의 タ(글리프 0x4E)를 한글 '안'으로 교체.

- 컷신 1bpp 폰트: 뱅크 1, CPU $8337 + id*8 (= prg+0x8337, 파일 +0x10)
- タ = 0xC0 - 0x72 = 글리프 0x4E → 파일 오프셋 0x10 + 0x8337 + 0x4E*8 = 0x85B7
- 인트로 첫 문장 "RASH! ZITZ! ﾀｲﾍﾝﾀﾞ!"의 모든 タ 자리에 '안'이 나오면 성공.
- Galmuri8x8.ttf는 truetype 사이즈 16에서 8x8 픽셀 글리프를 낸다.

실행: python workspace/scripts/make_poc_glyph.py
출력: build/poc_glyph.nes, workspace/font/poc_glyph_preview.txt
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ROM_IN = ROOT / "original" / "Battletoads (Japan).nes"
ROM_OUT = ROOT / "build" / "poc_glyph.nes"
PREVIEW = ROOT / "workspace" / "font" / "poc_glyph_preview.txt"
FONT_TTF = ROOT.parents[1] / "Font" / "Galmuri8x8.ttf"

ORIG_SHA256 = "B831F75C36EEF329A34D0E0D9308CDF85864EDD87E7DA6D8E408307F8BF402D8"

FONT_BASE_FILE = 0x10 + 0x8337  # 뱅크1 CPU $8337
GLYPH_ID_TA = 0xC0 - 0x72  # 0x4E


def render_8x8(ch: str) -> bytes:
    font = ImageFont.truetype(str(FONT_TTF), 16)
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
    raw = bytearray(ROM_IN.read_bytes())
    got = hashlib.sha256(raw).hexdigest().upper()
    if got != ORIG_SHA256:
        raise SystemExit(f"원본 해시 불일치: {got}")

    glyph = render_8x8("안")
    off = FONT_BASE_FILE + GLYPH_ID_TA * 8
    before = bytes(raw[off : off + 8])
    raw[off : off + 8] = glyph

    ROM_OUT.parent.mkdir(exist_ok=True)
    ROM_OUT.write_bytes(raw)

    lines = [
        f"원본 タ(글리프 {GLYPH_ID_TA:#x}) @ file+{off:#x}: {before.hex(' ').upper()}",
        f"교체 '안': {glyph.hex(' ').upper()}",
        "",
    ]
    for y in range(8):
        lines.append("".join("#" if glyph[y] & (0x80 >> x) else "." for x in range(8)))
    PREVIEW.write_text("\n".join(lines), encoding="utf-8")

    print(f"PoC ROM: {ROM_OUT}")
    print(f"교체 오프셋 file+{off:#x}, 원본 8바이트: {before.hex(' ').upper()}")
    print(f"SHA256: {hashlib.sha256(raw).hexdigest().upper()}")


if __name__ == "__main__":
    main()
