"""뱅크 1 $86CF(글리프 업로드 후보) 디스어셈블.

실행: python workspace/scripts/probe_glyph_upload.py
출력: workspace/analysis/glyph_upload.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workspace" / "scripts"))
from dis6502 import disasm  # noqa: E402

ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "glyph_upload.txt"

prg = ROM.read_bytes()[16:]
b1 = prg[0x8000:0x10000]
lines: list[str] = []
for a, t in disasm(b1, 0x8000, 0x86CF - 0x8000, 0x8790 - 0x8000):
    lines.append(f"${a:04X}: {t}")
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}")
