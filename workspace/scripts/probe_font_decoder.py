"""폰트 후보 1bpp 렌더 + 허프만 디코더 후보(zp $1B-$1E 접근) 탐색.

실행: python workspace/scripts/probe_font_decoder.py
출력: workspace/analysis/font_probe.txt
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "font_probe.txt"

prg = ROM.read_bytes()[16:]
lines: list[str] = []
add = lines.append


def render_1bpp(off: int, count: int, per_row: int = 16) -> None:
    """off부터 count개의 8바이트 1bpp 셀을 ASCII 아트로 렌더."""
    for row_start in range(0, count, per_row):
        n = min(per_row, count - row_start)
        add(
            "cells "
            + ", ".join(f"{row_start + i}@{off + (row_start + i) * 8:#x}" for i in (0, n - 1))
        )
        for y in range(8):
            row = []
            for c in range(n):
                b = prg[off + (row_start + c) * 8 + y]
                row.append("".join("#" if b & (0x80 >> x) else "." for x in range(8)))
            add(" ".join(row))
        add("")


add("# 뱅크 1 prg+0x8700 부근 1bpp 렌더 (셀 96개)")
render_1bpp(0x8700, 96)

add("# 허프만/비트리더 후보: zp $1B-$1E를 만지는 opcode 패턴 위치")
patterns = {
    "ASL $1B": bytes([0x06, 0x1B]),
    "LSR $1B": bytes([0x46, 0x1B]),
    "ROL $1B": bytes([0x26, 0x1B]),
    "LDA $1B": bytes([0xA5, 0x1B]),
    "STA $1B": bytes([0x85, 0x1B]),
    "DEC $1E": bytes([0xC6, 0x1E]),
    "INC $1C": bytes([0xE6, 0x1C]),
    "LDA ($1C),Y": bytes([0xB1, 0x1C]),
}
hits: dict[int, list[str]] = {}
for name, pat in patterns.items():
    start = 0
    while True:
        i = prg.find(pat, start)
        if i < 0:
            break
        hits.setdefault(i, []).append(name)
        start = i + 1

# 서로 64바이트 안에 3종 이상 몰려 있는 클러스터만 보고
offs = sorted(hits)
clusters: list[tuple[int, int, set[str]]] = []
i = 0
while i < len(offs):
    j = i
    names: set[str] = set()
    while j < len(offs) and offs[j] - offs[i] <= 96:
        names.update(hits[offs[j]])
        j += 1
    if len(names) >= 3:
        clusters.append((offs[i], offs[j - 1], names))
        i = j
    else:
        i += 1

for a, b, names in clusters:
    bank = a // 0x8000
    cpu = 0x8000 + (a % 0x8000)
    add(f"bank {bank} prg+{a:#07x} (cpu ${cpu:04X})..+{b - a}: {sorted(names)}")
    chunk = prg[a - 16 : b + 24]
    add("  " + chunk.hex(" ").upper())
add("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}; clusters={len(clusters)}")
