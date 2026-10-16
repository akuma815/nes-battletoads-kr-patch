"""Battletoads (Japan).nes 초기 정적 분석.

- iNES 헤더/해시(헤더 포함·제외) 요약
- Mapper 7(AxROM) 32KiB 뱅크별 리셋/NMI/IRQ 벡터 후보
- ASCII 문자열 런 스캔(뱅크·파일 오프셋 표기)

실행: python workspace/scripts/analyze_rom.py
출력: workspace/analysis/rom_static.txt
"""
from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "rom_static.txt"

HEADER = 16
BANK32 = 0x8000


def hashes(data: bytes) -> dict[str, str]:
    return {
        "sha256": hashlib.sha256(data).hexdigest().upper(),
        "sha1": hashlib.sha1(data).hexdigest().upper(),
        "md5": hashlib.md5(data).hexdigest().upper(),
        "crc32": f"{zlib.crc32(data) & 0xFFFFFFFF:08X}",
    }


def ascii_runs(prg: bytes, min_len: int = 6):
    """대문자/숫자/일부 구두점 중심의 ASCII 런을 찾는다(NES 관행상 소문자도 허용)."""
    ok = set(range(0x20, 0x7F))
    runs = []
    start = None
    for i, b in enumerate(prg):
        if b in ok:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_len:
                s = prg[start:i].decode("ascii")
                # 문자 비중이 낮은 잡음 제거
                letters = sum(c.isalpha() for c in s)
                if letters >= max(3, len(s) // 3):
                    runs.append((start, s))
            start = None
    if start is not None and len(prg) - start >= min_len:
        s = prg[start:].decode("ascii")
        letters = sum(c.isalpha() for c in s)
        if letters >= max(3, len(s) // 3):
            runs.append((start, s))
    return runs


def main() -> None:
    raw = ROM.read_bytes()
    header, prg = raw[:HEADER], raw[HEADER:]
    lines: list[str] = []
    add = lines.append

    add("# Battletoads (Japan).nes 정적 분석")
    add("")
    add(f"파일 크기: {len(raw)} bytes / PRG: {len(prg)} bytes")
    add(f"헤더: {header.hex(' ').upper()}")
    add("")
    add("## 해시")
    for label, data in (("헤더 포함", raw), ("헤더 제외(PRG 전체)", prg)):
        h = hashes(data)
        add(f"- {label}: CRC32={h['crc32']} MD5={h['md5']}")
        add(f"  SHA1={h['sha1']}")
        add(f"  SHA256={h['sha256']}")
    add("")

    add("## 32KiB 뱅크별 벡터 (AxROM: $8000-$FFFF 전체 교체)")
    add("뱅크 | 파일오프셋(PRG) | NMI | RESET | IRQ")
    n_banks = len(prg) // BANK32
    for b in range(n_banks):
        base = b * BANK32
        tail = prg[base + BANK32 - 6 : base + BANK32]
        nmi = int.from_bytes(tail[0:2], "little")
        rst = int.from_bytes(tail[2:4], "little")
        irq = int.from_bytes(tail[4:6], "little")
        add(f"{b} | {base:#08x} | ${nmi:04X} | ${rst:04X} | ${irq:04X}")
    add("")

    add("## ASCII 런 (6+ 글자, 문자 비중 필터)")
    runs = ascii_runs(prg)
    add(f"총 {len(runs)}건")
    for off, s in runs:
        bank = off // BANK32
        add(f"bank {bank} prg+{off:#07x} file+{off + HEADER:#07x}: {s!r}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT} ({len(lines)} lines, {len(runs)} ascii runs)")


if __name__ == "__main__":
    main()
