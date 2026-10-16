"""한글 초안 코퍼스 통계·제약 검사 (R1/R5 설계 입력).

검사:
- ID 커버리지·기준선 해시 일치
- 허용 문자 집합(한글 음절, A-Z, 숫자, 지정 구두점)
- briefings: 줄 길이 ≤26(경고 24), 문자열별 고유 글리프 ≤59
- fixed: byte_len 이하(제자리 교체 제약)
- 전체 고유 음절 수 vs 허프만 리프 상한 129 (R1 판정)
- 새 코퍼스 최적 허프만 크기 추정 vs 원본 스트림 4181B

실행: python workspace/scripts/stats_korean.py
출력: workspace/analysis/korean_stats.txt
"""
from __future__ import annotations

import heapq
import json
from collections import Counter

import btlib

TR = btlib.ROOT / "workspace" / "text" / "translation" / "translation.json"
SRC_B = btlib.ROOT / "workspace" / "text" / "source" / "briefings.json"
SRC_F = btlib.ROOT / "workspace" / "text" / "source" / "fixed_strings.json"
OUT = btlib.ROOT / "workspace" / "analysis" / "korean_stats.txt"

ALLOWED_ASCII = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !.-:'?,")
ALLOWED_PUNCT = set("､･｢｣")
MAX_WIDTH = 26
WARN_WIDTH = 24
MAX_SLOTS = 48  # 엔진 텍스트 슬롯 예산 $C5~$F4. $F5+는 씬 아트 영역(세션 9 실측)
LEAF_LIMIT = 129
STREAM_LIMIT = 4181


def is_hangul(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def huffman_bits(freq: Counter) -> tuple[int, int]:
    """(총 비트수, 리프 수) — 최적 이진 허프만."""
    heap = [(f, i, None) for i, f in enumerate(freq.values())]
    vals = list(freq.values())
    if len(vals) == 1:
        return vals[0], 1
    heapq.heapify(heap)
    depth_cost = 0
    n = len(heap)
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        merged = a[0] + b[0]
        depth_cost += merged
        heapq.heappush(heap, (merged, n, None))
        n += 1
    return depth_cost, len(vals)


def main() -> None:
    tr = json.loads(TR.read_text(encoding="utf-8"))
    src_b = json.loads(SRC_B.read_text(encoding="utf-8"))
    src_f = json.loads(SRC_F.read_text(encoding="utf-8"))
    lines: list[str] = []
    add = lines.append
    problems: list[str] = []

    if tr["meta"]["baseline_rom_sha256"] != btlib.ORIG_SHA256:
        problems.append("기준선 해시 불일치")

    b_ids = [e["entry_id"] for e in src_b["entries"]]
    t_ids = [e["id"] for e in tr["briefings"]]
    if b_ids != t_ids:
        problems.append("briefings ID 불일치")
    f_ids = [e["entry_id"] for e in src_f["entries"]]
    tf_ids = [e["id"] for e in tr["fixed"]]
    if f_ids != tf_ids:
        problems.append("fixed ID 불일치")

    syllables: Counter[str] = Counter()
    others: Counter[str] = Counter()
    slot_report: list[tuple[int, int]] = []

    for e in tr["briefings"]:
        if e.get("status") == "excluded":
            continue
        if not e.get("ko"):
            problems.append(f"briefing {e['id']}: ko 없음")
            continue
        uniq: set[str] = set()
        for li, line in enumerate(e["ko"]):
            if len(line) > MAX_WIDTH:
                problems.append(f"briefing {e['id']} L{li}: {len(line)}자 > {MAX_WIDTH}")
            elif len(line) > WARN_WIDTH:
                add(f"경고: briefing {e['id']} L{li}: {len(line)}자(들여쓰기 여유 축소)")
            for ch in line:
                if is_hangul(ch):
                    syllables[ch] += 1
                    uniq.add(ch)
                elif ch in ALLOWED_ASCII or ch in ALLOWED_PUNCT:
                    others[ch] += 1
                    if ch != " ":
                        uniq.add(ch)
                    else:
                        uniq.add(ch)  # 공백도 글리프 슬롯을 차지한다
                else:
                    problems.append(f"briefing {e['id']}: 허용 외 문자 {ch!r}")
        slot_report.append((e["id"], len(uniq)))
        if len(uniq) > MAX_SLOTS:
            problems.append(f"briefing {e['id']}: 고유 글리프 {len(uniq)} > {MAX_SLOTS}")

    fixed_syll: Counter[str] = Counter()
    for e, s in zip(tr["fixed"], src_f["entries"]):
        if e["status"] == "excluded" or not e.get("ko"):
            continue
        cost = 0
        for ch in e["ko"]:
            if is_hangul(ch):
                fixed_syll[ch] += 1
                cost += 1
            elif ch in ALLOWED_ASCII or ch in ALLOWED_PUNCT:
                cost += 1
            else:
                problems.append(f"fixed {e['id']}: 허용 외 문자 {ch!r}")
        if cost > s["byte_len"]:
            problems.append(f"fixed {e['id']}: {cost}B > 원본 {s['byte_len']}B")

    add("")
    add("# 한글 초안 코퍼스 통계")
    add(f"브리핑 음절 종류: {len(syllables)}")
    add(f"스토리(fixed) 음절 종류: {len(fixed_syll)}")
    total_syll = set(syllables) | set(fixed_syll)
    add(f"전체 음절 종류: {len(total_syll)} (공용 폰트 레퍼토리 수요)")
    add(f"비한글 글리프 종류(브리핑): {len([c for c in others if c != ' '])}")

    # 시스템 1 심볼 수요: 음절 + ASCII/구두점 + 제어({fc},{nl}계열 12종) + 종료
    sys1_symbols = len(syllables) + len([c for c in others]) + 12 + 2
    add("")
    add("# R1 판정 (시스템 1 허프만)")
    add(f"필요 심볼 수(추정): {sys1_symbols} (음절 {len(syllables)} + 기타 {len(others)} + 제어 14)")
    add(f"리프 상한 {LEAF_LIMIT}: {'초과 -> 재설계 필요' if sys1_symbols > LEAF_LIMIT else '이내'}")

    # 새 코퍼스 최적 허프만 추정(음절 그대로 심볼일 때)
    corpus: Counter[str] = Counter()
    for e in tr["briefings"]:
        for line in e.get("ko") or []:
            corpus.update(line)
        corpus["\n"] += max(0, len(e.get("ko") or []) - 1)
        corpus["\x00"] += 1  # 종료
    bits, leaves = huffman_bits(corpus)
    add(f"새 코퍼스 최적 허프만: 리프 {leaves}, 본문 {bits}비트 = {bits / 8:.0f}B")
    add(f"원본 스트림 한도 {STREAM_LIMIT}B 대비: {bits / 8 - STREAM_LIMIT:+.0f}B (테이블 별도)")

    add("")
    add("# 문자열별 고유 글리프(워킹셋 슬롯) 상위 10")
    for i, n in sorted(slot_report, key=lambda x: -x[1])[:10]:
        add(f"  briefing {i}: {n}/{MAX_SLOTS}")

    add("")
    if problems:
        add(f"# 제약 위반 {len(problems)}건")
        lines.extend(f"  - {p}" for p in problems)
    else:
        add("# 제약 위반 없음")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
