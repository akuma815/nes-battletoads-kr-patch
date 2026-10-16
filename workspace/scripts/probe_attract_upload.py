"""뱅크 1 범용 PPU 업로더($8012)와 블록 테이블($8190) 해독 (R7).

실행: python workspace/scripts/probe_attract_upload.py
출력: workspace/analysis/attract_upload.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workspace" / "scripts"))
import btlib  # noqa: E402
from dis6502 import disasm  # noqa: E402

OUT = ROOT / "workspace" / "analysis" / "attract_upload.txt"

prg = btlib.load_prg()
b1 = prg[0x8000:0x10000]
lines: list[str] = []
add = lines.append

add("# $8012 전체 디스어셈블 ($8012-$8190)")
for a, t in disasm(b1, 0x8000, 0x0012, 0x0190):
    add(f"${a:04X}: {t}")
add("")

add("# $8190 포인터 테이블 (16엔트리 가정)")
for i in range(0, 32, 2):
    ptr = int.from_bytes(b1[0x190 + i : 0x192 + i], "little")
    add(f"  X={i:02X}: ${ptr:04X}")
add("")

add("# 각 포인터의 블록 헤더 미리보기")
for i in range(0, 32, 2):
    ptr = int.from_bytes(b1[0x190 + i : 0x192 + i], "little")
    if not 0x8000 <= ptr < 0xFFF0:
        continue
    off = ptr - 0x8000
    chunk = b1[off : off + 40]
    add(f"  X={i:02X} ${ptr:04X}: {chunk.hex(' ').upper()}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}")
