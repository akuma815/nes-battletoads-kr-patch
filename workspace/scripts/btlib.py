"""Battletoads (J) 공용 분석 모듈: ROM 로드, 허프만 테이블, 디코드/인코드.

사양 근거는 workspace/analysis/SURVEY.md A2·A3. 주소는 뱅크 6 CPU 기준.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM_PATH = ROOT / "original" / "Battletoads (Japan).nes"
ORIG_SHA256 = "B831F75C36EEF329A34D0E0D9308CDF85864EDD87E7DA6D8E408307F8BF402D8"

BANK6 = 6 * 0x8000
ADDR_BIT0 = 0xE91B
ADDR_BIT1 = 0xE983
ADDR_SYMS = 0xE9EB
ADDR_PTR = 0xEA54
ADDR_STREAM = 0xEA89  # 실효 첫 바이트는 +7 (($1C),Y=7 고정 접근)
N_NODES = 104
N_SYMS = 105
N_ENTRIES = 26
N_STRINGS = N_ENTRIES * 4

SYM_END = 0xFD  # 문자열 종료
SYM_NL = 0xFC  # 디코드 시 $80,$20으로 전개

# 실제 분모(세션 7 교정): 포인터 테이블은 30엔트리($EA54~$EA8F, 스트림 실효
# 시작 $EA90 직전까지)이고 유효 문자열은 id 0~116의 117개다. id 117~119는
# 호출부가 없어 존재하지 않는다(스트림 꼬리 잡음). id 116은 레벨 이름 테이블로
# $AB9E가 리터럴 호출하며 워킹셋 재구축을 생략한다(버퍼에 원시 문자 유지).
N_ENTRIES_FULL = 30
N_STRINGS_FULL = 117


def load_prg(path: Path = ROM_PATH, verify: bool = True) -> bytes:
    raw = path.read_bytes()
    if verify:
        got = hashlib.sha256(raw).hexdigest().upper()
        if got != ORIG_SHA256:
            raise SystemExit(f"원본 해시 불일치: {got}")
    return raw[16:]


def b6(prg: bytes, cpu: int) -> int:
    return prg[BANK6 + cpu - 0x8000]


def b6_slice(prg: bytes, cpu: int, n: int) -> bytes:
    off = BANK6 + cpu - 0x8000
    return prg[off : off + n]


class Tables:
    def __init__(self, prg: bytes):
        self.bit0 = b6_slice(prg, ADDR_BIT0, N_NODES)
        self.bit1 = b6_slice(prg, ADDR_BIT1, N_NODES)
        self.syms = b6_slice(prg, ADDR_SYMS, N_SYMS)

    def codebook(self) -> dict[int, str]:
        """심볼 바이트 -> 비트 문자열. 트리를 뿌리(노드 0)부터 전개."""
        codes: dict[int, str] = {}

        def walk(node: int, prefix: str) -> None:
            for bit, table in ((0, self.bit0), (1, self.bit1)):
                v = table[node]
                p = prefix + str(bit)
                if v >= 0x80:
                    sym = self.syms[v - 0x80]
                    if sym in codes:
                        raise ValueError(f"중복 심볼 {sym:#04x}: {codes[sym]} / {p}")
                    codes[sym] = p
                else:
                    walk(v, p)

        walk(0, "")
        return codes


class BitReader:
    """스트림 절대 비트 위치 기반 리더. base_cpu는 실효 첫 바이트 주소."""

    def __init__(self, prg: bytes, base_cpu: int, bitpos: int = 0):
        self.prg = prg
        self.base = base_cpu
        self.bitpos = bitpos

    def next(self) -> int:
        byte = b6(self.prg, self.base + self.bitpos // 8)
        b = (byte >> (7 - self.bitpos % 8)) & 1
        self.bitpos += 1
        return b


def decode_symbol(t: Tables, br: BitReader) -> int:
    x = 0
    while True:
        v = (t.bit1 if br.next() else t.bit0)[x]
        if v >= 0x80:
            return t.syms[v - 0x80]
        x = v


def read_pointer_entry(prg: bytes, idx: int) -> tuple[int, int]:
    """(byteoff, start_bit_in_byte). start_bit = 첫 바이트에서 버릴 비트 수."""
    lo = b6(prg, ADDR_PTR + idx * 2)
    hi = b6(prg, ADDR_PTR + idx * 2 + 1)
    byteoff = ((hi >> 3) << 8) | lo
    return byteoff, 7 - (hi & 7)


def make_pointer_entry(bitpos: int) -> tuple[int, int]:
    """스트림 절대 비트 위치 -> (lo, hi) 포인터 엔트리 바이트."""
    byteoff, start_bit = bitpos // 8, bitpos % 8
    lo = byteoff & 0xFF
    hi = ((byteoff >> 8) << 3) | (7 - start_bit)
    return lo, hi


def extract_all(prg: bytes, n_strings: int = N_STRINGS_FULL) -> list[list[int]]:
    """문자열 n_strings개의 심볼 목록($FD 미포함)을 스트림 순서대로 돌려준다."""
    t = Tables(prg)
    out: list[list[int]] = []
    n_entries = (n_strings + 3) // 4
    for e in range(n_entries):
        byteoff, start_bit = read_pointer_entry(prg, e)
        br = BitReader(prg, ADDR_STREAM + 7, byteoff * 8 + start_bit)
        for _ in range(min(4, n_strings - e * 4)):
            syms: list[int] = []
            while True:
                s = decode_symbol(t, br)
                if s == SYM_END:
                    break
                syms.append(s)
            out.append(syms)
    return out


def sym_repr(s: int) -> str:
    if 0x20 <= s <= 0x7E:
        return chr(s)
    if 0xA1 <= s <= 0xDF:
        return chr(0xFF61 + s - 0xA1)
    return f"[{s:02X}]"
