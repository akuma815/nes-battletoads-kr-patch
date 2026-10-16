"""전 뱅크 빈 공간 실측: 같은 바이트(00 또는 FF)가 64바이트 이상 이어지는 구간.

'빈 공간 후보'일 뿐이며, 실제 사용 전에는 해당 구간 참조 부재를 별도로 확인해야 한다.

실행: python workspace/scripts/free_space.py
출력: workspace/analysis/free_space.txt
"""
from __future__ import annotations

import btlib

MIN_RUN = 64


def main() -> None:
    prg = btlib.load_prg()
    lines: list[str] = ["# 빈 공간 후보 (동일 바이트 64+ 런)", ""]
    total_by_bank: dict[int, int] = {}
    for bank in range(8):
        base = bank * 0x8000
        data = prg[base : base + 0x8000]
        i = 0
        runs: list[tuple[int, int, int]] = []
        while i < len(data):
            b = data[i]
            j = i
            while j < len(data) and data[j] == b:
                j += 1
            if j - i >= MIN_RUN and b in (0x00, 0xFF):
                runs.append((i, j - i, b))
            i = j
        total = sum(r[1] for r in runs)
        total_by_bank[bank] = total
        lines.append(f"## bank {bank}: 합계 {total} bytes")
        for off, ln, b in runs:
            cpu = 0x8000 + off
            lines.append(f"  cpu ${cpu:04X}~${cpu + ln - 1:04X} ({ln:5d} bytes, {b:02X}) prg+{base + off:#07x}")
        lines.append("")

    out = btlib.ROOT / "workspace" / "analysis" / "free_space.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {out}")
    for bank, total in total_by_bank.items():
        print(f"bank {bank}: {total} bytes")


if __name__ == "__main__":
    main()
