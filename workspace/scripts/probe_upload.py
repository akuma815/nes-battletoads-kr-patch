"""$FFA7 트램펄린, 뱅크 6 함수 디스패치, $DCE8 테이블, 폰트 후보 탐색.

실행: python workspace/scripts/probe_upload.py
출력: workspace/analysis/upload_probe.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workspace" / "scripts"))
from dis6502 import disasm  # noqa: E402

ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "upload_probe.txt"

prg = ROM.read_bytes()[16:]
lines: list[str] = []
add = lines.append


def bankbytes(b: int) -> bytes:
    return prg[b * 0x8000 : (b + 1) * 0x8000]


b6 = bankbytes(6)

add("# 뱅크 6 $FF80-$FFFF (공용 스텁 추정)")
for addr, text in disasm(b6, 0x8000, 0xFF80 - 0x8000, 0xFFFA - 0x8000):
    add(f"${addr:04X}: {text}")
add("")

add("# 뱅크 6 $8000-$8040 (뱅크 함수 테이블 후보)")
for addr, text in disasm(b6, 0x8000, 0x0000, 0x0040):
    add(f"${addr:04X}: {text}")
add("")
add("$8000부터 워드 나열:")
for i in range(0, 0x20, 2):
    w = int.from_bytes(b6[i : i + 2], "little")
    add(f"  +{i:02X}: ${w:04X}")
add("")

add("# $DCE8 테이블 덤프 (128 bytes: ASCII→글리프 매핑 추정)")
off = 0xDCE8 - 0x8000
chunk = b6[off : off + 0x80]
for i in range(0, 0x80, 16):
    add(f"  ${0xDCE8 + i:04X}: " + chunk[i : i + 16].hex(" ").upper())
add("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}")
