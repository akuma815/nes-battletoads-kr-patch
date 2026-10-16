"""한글 빌드용 인코딩 라이브러리: ko_lines -> 슬롯-인덱스 심볼열, 허프만 트리 생성.

설계(SURVEY A8):
- 문자열마다 고유 글리프를 등장순으로 슬롯 $C5..에 배정. 심볼 = 슬롯 번호.
- 줄 경계 = $80(개행) + $80+N(개행+들여쓰기 N) 쌍 — 원본의 [FC][8N]과 같은 2행 간격.
  첫 줄은 리터럴 공백 센터링(원본 관행). $FC 심볼은 사용하지 않는다.
- 후행 빈 줄은 원문 소스의 후행 {fc} 수를 그대로 $80 반복으로 보존.
- 종료 $FD. 트리는 기존 테이블 자리(내부노드<=104, 리프<=105)에 맞아야 한다.
"""
from __future__ import annotations

import heapq
import json
import re
from collections import Counter

import btlib

BOX_W = 26  # 박스 내부 폭(실측 A2)
SLOT0 = 0xC5

CH_MAP = {"?": '"', ",": "､"}  # ko 문자 -> 원문 글리프 키 정규화('"'=물음표 글리프, '､'=쉼표)


def center_indent(width: int) -> int:
    return max(0, (BOX_W - width) // 2)


def trailing_fc(src_text: str) -> int:
    """소스 토큰 텍스트 말미의 빈 줄({fc} 연속) 수."""
    m = re.search(r"((?:\{fc\})+)$", src_text)
    return len(m.group(1)) // 4 if m else 0


def string_to_symbols(ko_lines: list[str], tail_fc: int) -> tuple[list[int], list[str]]:
    """(심볼열($FD 미포함), 글리프 키 목록: 슬롯 순서)"""
    glyphs: list[str] = []
    slot: dict[str, int] = {}

    def sym_for(ch: str) -> int:
        ch = CH_MAP.get(ch, ch)
        if ch not in slot:
            # 실효 상한 48($C5~$F4): 엔진의 텍스트 슬롯 설계 예산(프리로드 $81F3=48개).
            # $F5~$FB는 엔딩 초상화 등 씬 아트가 쓴다(55슬롯이 초상화를 덮은 사건으로 실측).
            # $FC/$FD는 디코더 예약이라 어차피 불가.
            if len(glyphs) >= 48:
                raise ValueError("슬롯 48 초과")
            slot[ch] = SLOT0 + len(glyphs)
            glyphs.append(ch)
        return slot[ch]

    syms: list[int] = []
    first = ko_lines[0]
    for ch in " " * center_indent(len(first)) + first:
        syms.append(sym_for(ch))
    for line in ko_lines[1:]:
        # 원본 [FC][8N] 전개와 동일한 버퍼 패턴: $80, 공백, $80+N.
        # 공백을 빼면 렌더러가 한 줄만 내려간다(krdev2 실측).
        syms.append(0x80)
        syms.append(sym_for(" "))
        syms.append(0x80 + min(11, center_indent(len(line))))
        for ch in line:
            syms.append(sym_for(ch))
    for _ in range(tail_fc):
        syms.append(0x80)
        syms.append(sym_for(" "))
    return syms, glyphs


def build_huffman(freq: Counter) -> dict[int, str]:
    """심볼 -> 비트열. 힙 항목 (빈도, 안정키, 노드)"""
    heap: list[tuple[int, int, object]] = []
    for i, (sym, f) in enumerate(sorted(freq.items())):
        heap.append((f, i, sym))
    heapq.heapify(heap)
    n = len(freq)
    while len(heap) > 1:
        fa, _, a = heapq.heappop(heap)
        fb, _, b = heapq.heappop(heap)
        heap.append((fa + fb, n, (a, b)))
        heapq.heapify(heap)
        n += 1
    codes: dict[int, str] = {}

    def walk(node, prefix: str) -> None:
        if isinstance(node, tuple):
            walk(node[0], prefix + "0")
            walk(node[1], prefix + "1")
        else:
            codes[node] = prefix or "0"

    walk(heap[0][2], "")
    return codes


def tree_tables(codes: dict[int, str]) -> tuple[bytes, bytes, bytes]:
    """디코더 형식의 (bit0, bit1, symbols) 테이블 생성.

    노드 0 = 루트. 내부 노드 값 = 노드 번호(<0x80), 리프 값 = 0x80+심볼인덱스.
    """
    bit0: list[int | None] = [None]
    bit1: list[int | None] = [None]
    symbols: list[int] = []

    def insert(node: int, bits: str, sym: int) -> None:
        table = bit1 if bits[0] == "1" else bit0
        if len(bits) == 1:
            symbols.append(sym)
            table[node] = 0x80 + len(symbols) - 1
            return
        nxt = table[node]
        if nxt is None:
            bit0.append(None)
            bit1.append(None)
            nxt = len(bit0) - 1
            table[node] = nxt
        insert(nxt, bits[1:], sym)

    for sym, bits in sorted(codes.items(), key=lambda kv: (len(kv[1]), kv[1])):
        insert(0, bits, sym)
    if any(v is None for v in bit0) or any(v is None for v in bit1):
        raise ValueError("불완전 트리")
    return bytes(bit0), bytes(bit1), bytes(symbols)


def load_corpus() -> tuple[list[list[int]], list[list[str]]]:
    """번역본 -> (문자열별 심볼열, 문자열별 글리프 키 목록)"""
    tr = json.loads(
        (btlib.ROOT / "workspace" / "text" / "translation" / "translation.json").read_text(
            encoding="utf-8"
        )
    )
    src = json.loads(
        (btlib.ROOT / "workspace" / "text" / "source" / "briefings.json").read_text(
            encoding="utf-8"
        )
    )
    all_syms: list[list[int]] = []
    all_glyphs: list[list[str]] = []
    for e, s in zip(tr["briefings"], src["entries"]):
        assert e["id"] == s["entry_id"]
        if e["status"] == "excluded" or not e.get("ko"):
            # id 116(레벨명 테이블) 등: 원시 심볼 그대로 재인코드(소비자가 버퍼의
            # 원문자를 직접 읽는 워킹셋-생략 경로). 글리프 목록 불필요.
            raw = bytes.fromhex(s["sym_hex"].replace(" ", ""))
            all_syms.append(list(raw))
            all_glyphs.append([])
            continue
        syms, glyphs = string_to_symbols(e["ko"], trailing_fc(s["text"]))
        all_syms.append(syms)
        all_glyphs.append(glyphs)
    return all_syms, all_glyphs


if __name__ == "__main__":
    all_syms, all_glyphs = load_corpus()
    freq: Counter[int] = Counter()
    for syms in all_syms:
        freq.update(syms)
        freq[0xFD] += 1
    codes = build_huffman(freq)
    bit0, bit1, symtab = tree_tables(codes)
    total_bits = sum(len(codes[s]) for syms in all_syms for s in syms + [0xFD])
    n_bytes = (total_bits + 7) // 8
    glyph_repertoire = sorted({g for gl in all_glyphs for g in gl})
    list_bytes = sum(1 + 2 * len(gl) for gl in all_glyphs)
    print(f"심볼 종류: {len(freq)} (리프 한도 105)")
    print(f"내부 노드: {len(bit0)} (한도 104)")
    print(f"스트림: {total_bits}비트 = {n_bytes}B (한도 4181)")
    print(f"코드 길이: {min(map(len, codes.values()))}~{max(map(len, codes.values()))}비트")
    print(f"글리프 레퍼토리: {len(glyph_repertoire)}종, 목록 총 {list_bytes}B, 폰트 {len(glyph_repertoire) * 8}B")
