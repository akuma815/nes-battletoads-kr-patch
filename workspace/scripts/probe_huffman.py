"""뱅크 6 허프만 디코더 주변 디스어셈블 + 테이블 덤프 + 폰트 재정렬 렌더.

실행: python workspace/scripts/probe_huffman.py
출력: workspace/analysis/huffman_probe.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workspace" / "scripts"))
from dis6502 import disasm  # noqa: E402

ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "huffman_probe.txt"

prg = ROM.read_bytes()[16:]
BANK6 = 6 * 0x8000
bank6 = prg[BANK6 : BANK6 + 0x8000]
lines: list[str] = []
add = lines.append

add("# 뱅크 6 $E800-$E9A0 디스어셈블 (허프만 디코더 주변)")
for addr, text in disasm(bank6, 0x8000, 0xE800 - 0x8000, 0xE91B - 0x8000):
    add(f"${addr:04X}: {text}")
add("")

add("# 테이블 덤프")
for name, lo, hi in (
    ("bit0 nodes $E91B", 0xE91B, 0xE983),
    ("bit1 nodes $E983", 0xE983, 0xE9EB),
    ("symbols  $E9EB", 0xE9EB, 0xEA58),
):
    add(f"## {name} ({hi - lo} bytes)")
    chunk = bank6[lo - 0x8000 : hi - 0x8000]
    for i in range(0, len(chunk), 16):
        add(f"  +{i:02X}: " + chunk[i : i + 16].hex(" ").upper())
add("")

add("# 뱅크 1 폰트 재렌더 (base=prg 0x8703, 셀 160개)")
FONT = 0x8703
for row_start in range(0, 160, 16):
    add(f"cells {row_start}..{row_start + 15} @ {FONT + row_start * 8:#x}")
    for y in range(8):
        row = []
        for c in range(row_start, row_start + 16):
            b = prg[FONT + c * 8 + y]
            row.append("".join("#" if b & (0x80 >> x) else "." for x in range(8)))
        add(" ".join(row))
    add("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}")
