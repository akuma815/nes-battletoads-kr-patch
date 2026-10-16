"""허프만 재인코드 라운드트립 검증.

104개 문자열을 기존 트리로 재인코드해 하나의 연속 비트스트림을 만들고,
(1) 스트림 바이트가 원본과 동일한지, (2) 재생성한 포인터 테이블 26엔트리가
원본과 동일한지 확인한다. 마지막 부분 바이트의 패딩 비트는 원본 비트를 채워
비교한다(디코더는 그 비트를 읽지 않는다).

실행: python workspace/scripts/roundtrip.py
"""
from __future__ import annotations

import btlib


def main() -> None:
    prg = btlib.load_prg()
    t = btlib.Tables(prg)
    codes = t.codebook()
    print(f"코드북: 심볼 {len(codes)}개 (중복 없음), 코드 길이 {min(map(len, codes.values()))}~{max(map(len, codes.values()))}비트")

    strings = btlib.extract_all(prg)
    assert len(strings) == btlib.N_STRINGS

    # 재인코드: 문자열 0..103을 연속으로, 각각 $FD 종료 포함
    bits: list[str] = []
    bitpos = 0
    group_bitpos: list[int] = []
    for i, syms in enumerate(strings):
        if i % 4 == 0:
            group_bitpos.append(bitpos)
        for s in syms + [btlib.SYM_END]:
            bits.append(codes[s])
            bitpos += len(codes[s])
    stream_bits = "".join(bits)
    total_bits = len(stream_bits)
    print(f"재인코드 스트림: {total_bits}비트 = {total_bits / 8:.1f}바이트")

    # 포인터 테이블 재생성·비교
    ptr_ok = True
    for e, bp in enumerate(group_bitpos):
        lo, hi = btlib.make_pointer_entry(bp)
        olo = btlib.b6(prg, btlib.ADDR_PTR + e * 2)
        ohi = btlib.b6(prg, btlib.ADDR_PTR + e * 2 + 1)
        if (lo, hi) != (olo, ohi):
            ptr_ok = False
            print(f"  엔트리 {e} 불일치: 재생성 {lo:02X} {hi:02X} vs 원본 {olo:02X} {ohi:02X} (bitpos {bp})")
    print(f"포인터 테이블 26엔트리: {'동일' if ptr_ok else '불일치'}")

    # 스트림 바이트 재조립(패딩은 원본 비트로 채움)·비교
    n_bytes = (total_bits + 7) // 8
    orig = btlib.b6_slice(prg, btlib.ADDR_STREAM + 7, n_bytes)
    rebuilt = bytearray()
    for i in range(n_bytes):
        chunk = stream_bits[i * 8 : (i + 1) * 8]
        if len(chunk) < 8:
            orig_bits = f"{orig[i]:08b}"
            chunk = chunk + orig_bits[len(chunk) :]
        rebuilt.append(int(chunk, 2))
    same = bytes(rebuilt) == orig
    print(f"스트림 {n_bytes}바이트: {'바이트 동일' if same else '불일치'}")
    if not same:
        for i, (a, b) in enumerate(zip(rebuilt, orig)):
            if a != b:
                print(f"  첫 불일치 +{i:#x}: 재조립 {a:02X} vs 원본 {b:02X}")
                break

    end_cpu = btlib.ADDR_STREAM + 7 + n_bytes
    print(f"스트림 구간: ${btlib.ADDR_STREAM + 7:04X}~${end_cpu - 1:04X} (다음 주소 ${end_cpu:04X})")

    if ptr_ok and same:
        print("라운드트립 통과: 인코더는 원본과 완전 동등하다.")
    else:
        raise SystemExit("라운드트립 실패")


if __name__ == "__main__":
    main()
