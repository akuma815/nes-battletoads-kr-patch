"""뱅크 6 허프만 압축 문자열 전체 추출.

$E821/$E8EF 디스어셈블에서 확정한 사양을 그대로 에뮬레이트한다.
- 포인터 테이블 $EA54: 엔트리 2바이트(lo, hi). byteoff = (hi>>3)<<8 | lo,
  hi&7 = (첫 바이트에 남은 비트 수 - 1). 엔트리 하나 = 문자열 4개(id&3만큼 $FD 스킵).
- 스트림 접근은 ($1C),Y=7 고정이므로 실효 첫 바이트 = $EA89 + byteoff + 7.
  첫 바이트에서 (7 - (hi&7)) 비트를 버린 뒤 MSB 우선으로 읽는다.
- 트리: bit0 노드 $E91B, bit1 노드 $E983 (각 104), 값>=0x80이면 리프,
  심볼 = $E9EB[값-0x80] (심볼 105개).
- $FD = 문자열 종료. $FC = 제어(개행+공백 계열) — 원문 그대로 토큰 보존.

실행: python workspace/scripts/extract_text.py
출력: workspace/analysis/strings_decoded.txt
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "original" / "Battletoads (Japan).nes"
OUT = ROOT / "workspace" / "analysis" / "strings_decoded.txt"

prg = ROM.read_bytes()[16:]
B6 = 6 * 0x8000


def rd(cpu: int) -> int:
    return prg[B6 + cpu - 0x8000]


BIT0 = bytes(rd(0xE91B + i) for i in range(104))
BIT1 = bytes(rd(0xE983 + i) for i in range(104))
SYMS = bytes(rd(0xE9EB + i) for i in range(105))
PTR = 0xEA54
STREAM = 0xEA89


class BitReader:
    def __init__(self, cpu_addr: int, discard: int):
        self.addr = cpu_addr
        self.bit = 0
        for _ in range(discard):
            self.next()

    def next(self) -> int:
        b = (rd(self.addr) >> (7 - self.bit)) & 1
        self.bit += 1
        if self.bit == 8:
            self.bit = 0
            self.addr += 1
        return b


def decode_symbol(br: BitReader) -> int:
    x = 0
    while True:
        v = (BIT1 if br.next() else BIT0)[x]
        if v >= 0x80:
            return SYMS[v - 0x80]
        x = v


def sym_repr(s: int) -> str:
    if s == 0xFC:
        return "[FC]"
    if s == 0xFD:
        return "[FD]"
    if 0x20 <= s <= 0x7E:
        return chr(s)
    if 0xA1 <= s <= 0xDF:
        return chr(0xFF61 + s - 0xA1)  # JIS X 0201 반각 가나
    return f"[{s:02X}]"


def entry(idx: int) -> tuple[int, int]:
    lo = rd(PTR + idx * 2)
    hi = rd(PTR + idx * 2 + 1)
    byteoff = ((hi >> 3) << 8) | lo
    discard = 7 - (hi & 7)
    return byteoff, discard


lines: list[str] = []
add = lines.append
add("# 허프만 문자열 전체 디코드 (뱅크 6)")
add(f"포인터 테이블 $EA54, 스트림 기준 $EA89 (prg+{B6 + STREAM - 0x8000:#x})")
add("")

n_entries = (STREAM - PTR) // 2  # 26
max_stream_off = 0
for e in range(n_entries):
    byteoff, discard = entry(e)
    br = BitReader(STREAM + byteoff + 7, discard)
    add(f"## entry {e} (id {e * 4}..{e * 4 + 3}) byteoff={byteoff:#x} discard={discard}")
    for sub in range(4):
        sid = e * 4 + sub
        out: list[str] = []
        raw: list[int] = []
        try:
            while True:
                s = decode_symbol(br)
                if s == 0xFD:
                    break
                raw.append(s)
                out.append(sym_repr(s))
                if len(raw) > 2000:
                    out.append(" …중단(2000+)")
                    break
        except IndexError:
            out.append(" …범위밖")
            add(f"[{sid:3d}] {''.join(out)}")
            break
        text = "".join(out).replace("[FC]", "\n[FC]")
        add(f"[{sid:3d}] ({len(raw)} syms)")
        for ln in text.split("\n"):
            add(f"      {ln}")
    max_stream_off = max(max_stream_off, br.addr - STREAM)
    add("")

add(f"최대 도달 스트림 오프셋: {max_stream_off:#x} (cpu ${STREAM + max_stream_off:04X})")
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {OUT}")
