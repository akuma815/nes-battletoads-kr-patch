"""어트랙트 -STORY- 텍스트 후보 탐색: 가나(0xA1-0xDF)+ASCII 혼합 바이트 런.

실행: python workspace/scripts/probe_attract.py
출력: workspace/analysis/attract_candidates.txt
"""
from __future__ import annotations

import btlib

MIN_LEN = 8
MIN_KANA = 4


def main() -> None:
    prg = btlib.load_prg()
    ok = set(range(0x20, 0x7F)) | set(range(0xA1, 0xE0))
    lines: list[str] = []
    start = None
    for i in range(len(prg) + 1):
        b = prg[i] if i < len(prg) else -1
        if b in ok:
            if start is None:
                start = i
            continue
        if start is not None:
            run = prg[start:i]
            n_kana = sum(1 for x in run if 0xA1 <= x <= 0xDF)
            if len(run) >= MIN_LEN and n_kana >= MIN_KANA:
                bank = start // 0x8000
                cpu = 0x8000 + start % 0x8000
                text = "".join(btlib.sym_repr(x) for x in run)
                lines.append(f"bank {bank} cpu ${cpu:04X} prg+{start:#07x} len {len(run)}")
                lines.append(f"  {text}")
            start = None

    out = btlib.ROOT / "workspace" / "analysis" / "attract_candidates.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {out} ({len(lines) // 2}건)")


if __name__ == "__main__":
    main()
