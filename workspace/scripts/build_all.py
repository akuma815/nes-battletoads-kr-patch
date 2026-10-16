"""Battletoads (J) 한글 개발 빌드 생성 (시스템 1: 컷신 브리핑 + 시스템 2: 스토리).

설계: workspace/analysis/SURVEY.md A8·A9·A10.
- 512KiB 확장(뱅크 8~15 신설, 꼬리 스텁의 뱅크 상수 $FF91/$FFAA 뱅크별 패치)
- 시스템 1: 뱅크 6 제자리 새 트리·포인터·스트림, 뱅크 8 폰트·목록·업로드, $E89F 패치
- 시스템 2: 공용 폰트($8337, 뱅크 1)의 재사용 슬롯에 스토리 음절 글리프를 심고
  문자열을 제자리 교체(바이트 = 글리프+0x72, 시작 주소·본문 길이 불변, 중앙정렬 재계산)
- 게이트: 번역 상태·크기 한도·슬롯 풀 충족·산출물 디코드 라운드트립

산출: build/Battletoads_KR_dev.nes (2차 검토·QA 전 개발 빌드)
실행: python workspace/scripts/build_all.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import btlib
import kr_encoding as ke
import probe_story
import title_logo
from dis6502 import disasm

OUT_ROM = btlib.ROOT / "build" / "Battletoads_KR_dev.nes"
REPORT = btlib.ROOT / "build" / "build_report.txt"
FONT_TTF = btlib.ROOT / "inputs" / "Galmuri8x8.ttf"

BANK = 0x8000
B6 = 6 * BANK
B8 = 8 * BANK

# 뱅크 8 배치 (CPU 주소)
FONT_CPU = 0x8000
PTRS_CPU = 0x9000
LISTS_CPU = 0x9100
CODE_CPU = 0xB000

# 뱅크 6 제자리 (CPU 주소)
TAB_BIT0 = 0xE91B
TAB_BIT1 = 0xE983
TAB_SYMS = 0xE9EB
TAB_PTR = 0xEA54
STREAM = 0xEA90
# 스트림 실측 한도: $EA90~$FEF9 ($FEFA부터 뱅크 6 코드). 세션 7 분모 교정으로 확정.
STREAM_MAX = 0xFEFA - 0xEA90
# 원본 유효 문자열은 117(id 0~116)이나, 엔딩 시퀀서가 id 117~119를 실제로 디코드한다
# (사용자 세이브 포렌식 + id 117 강제 재현으로 확정). 빈 문자열 3개를 정식 발행해
# 분모를 120으로 확장한다 — 원본의 쓰레기-비트 디코드보다 안전하다.
N_STRINGS = 120
N_ENTRIES = 30

PATCH_LO = 0xE89F  # 교체 시작(원본 dedup 패스)
PATCH_HI = 0xE8EE  # 원본 RTS(보존)

# 뱅크 8 업로드 루틴 (핸드 어셈블, 위 CPU 주소 고정)
# count=0 가드 필수: DEC/BNE 후위 감소 구조라 0이면 255회 언더플로 폭주한다
# (엔딩 id 117 사건의 방어선. 빈 목록 항목과 함께 이중 방어).
UPLOAD_CODE = bytes.fromhex(
    "A5190AAA"  # $B000 LDA $19; ASL; TAX
    "BD0090851C"  # $B004 LDA $9000,X; STA $1C
    "BD0190851D"  # $B009 LDA $9001,X; STA $1D
    "AD0220"  # $B00E LDA $2002
    "A91C8D0620"  # $B011 LDA #$1C; STA $2006
    "A9508D0620"  # $B016 LDA #$50; STA $2006
    "A000"  # $B01B LDY #$00
    "B11C"  # $B01D LDA ($1C),Y  (count)
    "F03F"  # $B01F BEQ $B060 (count=0 -> RTS)
    "851E"  # $B021 STA $1E
    "C8"  # $B023 INY
    # glyph loop ($B024)
    "B11C8506C8"  # LDA ($1C),Y; STA $06; INY
    "B11C8507C8"  # LDA ($1C),Y; STA $07; INY
    "06062607"  # ASL $06; ROL $07  (x3 = id*8)
    "06062607"
    "06062607"
    "A50709808507"  # LDA $07; ORA #$80; STA $07  (폰트 기준 $8000)
    "841B"  # STY $1B
    "A000"  # LDY #$00
    "B1068D0720C8C008D0F6"  # plane0: LDA ($06),Y; STA $2007; INY; CPY #8; BNE
    "A000"
    "B1068D0720C8C008D0F6"  # plane1 동일
    "A41B"  # LDY $1B
    "C61E"  # DEC $1E
    "D0C4"  # $B05E BNE glyph loop($B024)
    "60"  # $B060 RTS
)

# $E89F 패치 (뱅크 6·뱅크 8 동일 미러). 데이터 바이트 08/06은 $E8EC/$E8ED.
PATCH_CODE = bytes.fromhex(
    "8519"  # STA $19 (문자열 ID)
    "ADECE8" "8DECE8"  # LDA/STA $E8EC(=08) -> 뱅크 8 전환
    "2000B0"  # JSR $B000 (뱅크 8 업로드)
    "ADEDE8" "8DEDE8"  # LDA/STA $E8ED(=06) -> 뱅크 6 복귀
    "60"  # RTS
)


def render_hangul(ch: str, font: ImageFont.FreeTypeFont) -> bytes:
    img = Image.new("L", (16, 16), 0)
    ImageDraw.Draw(img).text((0, 0), ch, font=font, fill=255)
    px = img.load()
    rows = []
    for y in range(8):
        b = 0
        for x in range(8):
            if px[x, y] > 127:
                b |= 0x80 >> x
        rows.append(b)
    if not any(rows):
        raise SystemExit(f"Galmuri 글리프 없음: {ch!r}")
    return bytes(rows)


def orig_glyph_id(prg: bytes, ch: str) -> int:
    """원본 공용 폰트($8337)의 글리프 ID (SURVEY A3 매핑)."""
    code = ord(ch)
    if code < 0x80:
        table = prg[B6 + 0xDCE8 - 0x8000 + code]
        return (table - 0xFC) & 0xFF
    jis = 0xA1 + (code - 0xFF61)  # 반각 가나
    return jis - 0x72


def glyph_of_byte(prg: bytes, b: int) -> int:
    """시스템 2 문자열 바이트 -> 글리프 ID."""
    if b >= 0x80:
        return b - 0x72
    table = prg[B6 + 0xDCE8 - 0x8000 + b]
    return (table - 0xFC) & 0xFF


def build_system2(
    prg: bytes, rom: bytearray, tr: dict, galmuri, add, extra_keep: set[int]
) -> dict[str, int]:
    """스토리 제자리 교체 + 공용 폰트 재사용 슬롯에 음절 글리프 기록.

    extra_keep: 시스템 1의 원문 유지 문자열(레벨명 id 116 등)이 공용 폰트로
    렌더하는 글리프들. 이걸 빼먹으면 SURF CITY의 F가 한글로 덮인다(실플레이 발견).
    반환: 음절 -> 문자열 바이트 매핑(검증용).
    """
    src_entries = probe_story.parse_strings(prg)
    fixed = tr["fixed"]
    assert len(fixed) == len(src_entries)

    # 유지 글리프: 미번역(excluded) 문자열의 원 바이트 + 숫자·공백·'!' + 번역문 ASCII
    keep: set[int] = set(range(0x05, 0x0F)) | {0x02, 0x04} | extra_keep
    reserved_ascii: set[int] = set()
    for e, (cpu, ppu, body) in zip(fixed, src_entries):
        if e["status"] == "excluded" or not e.get("ko"):
            for b in body:
                keep.add(glyph_of_byte(prg, b))
        else:
            for ch in e["ko"]:
                if ord(ch) < 0x80 and ch != " ":
                    reserved_ascii.add(orig_glyph_id(prg, ch))
                elif ch == "･":
                    keep.add(0x33)
    keep |= reserved_ascii

    pool = [g for g in range(0x0E, 0x6E) if g not in keep]

    syllables: list[str] = []
    for e in fixed:
        if e["status"] == "excluded" or not e.get("ko"):
            continue
        for ch in e["ko"]:
            if "가" <= ch <= "힣" and ch not in syllables:
                syllables.append(ch)
    add(f"시스템 2: 음절 {len(syllables)}종 / 재사용 슬롯 {len(pool)}개")
    if len(syllables) > len(pool):
        raise SystemExit(f"시스템 2 슬롯 부족: 음절 {len(syllables)} > 풀 {len(pool)}")

    syl_byte: dict[str, int] = {}
    for syl, glyph in zip(syllables, pool):
        syl_byte[syl] = glyph + 0x72
        rom[0x8337 + glyph * 8 : 0x8337 + glyph * 8 + 8] = render_hangul(syl, galmuri)

    n_replaced = 0
    for e, (cpu, ppu, body) in zip(fixed, src_entries):
        if e["status"] == "excluded" or not e.get("ko"):
            continue
        enc = bytearray()
        for ch in e["ko"]:
            if ch in syl_byte:
                enc.append(syl_byte[ch])
            elif ch == "･":
                enc.append(0xA5)
            elif ord(ch) < 0x80:
                enc.append(ord(ch))
            else:
                raise SystemExit(f"fixed {e['id']}: 인코딩 불가 문자 {ch!r}")
        if len(enc) > len(body):
            raise SystemExit(f"fixed {e['id']}: {len(enc)}B > 원본 {len(body)}B")
        col = (32 - len(enc)) // 2
        col = min(col, 32 - len(body))  # 패딩 포함 줄 넘김 방지
        new_ppu = (ppu & ~0x1F) | col
        enc += b"\x20" * (len(body) - len(enc))  # 공백 패딩(빈 타일)
        off = B6 + cpu - 0x8000
        rom[off] = new_ppu >> 8
        rom[off + 1] = new_ppu & 0xFF
        rom[off + 2 : off + 2 + len(enc)] = enc
        n_replaced += 1
    add(f"시스템 2: 문자열 {n_replaced}건 제자리 교체(시작 주소·본문 길이 불변)")
    return syl_byte


def main() -> None:
    global OUT_ROM, REPORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-rom', type=Path, default=btlib.ROM_PATH)
    parser.add_argument('--output-dir', type=Path, help='New output folder (must not exist)')
    args = parser.parse_args()
    btlib.ROM_PATH = args.source_rom.resolve()
    title_logo.ORIGINAL = btlib.ROM_PATH
    prg = btlib.load_prg(btlib.ROM_PATH)
    if hashlib.sha256(FONT_TTF.read_bytes()).hexdigest() != '97ba3dcc2cd5e5b2927e4e6ba9558a48a2a194a852c420df160654d66bbf2a05':
        raise SystemExit('Pinned Galmuri8x8 font hash mismatch')
    if args.output_dir:
        output = args.output_dir.resolve()
        if output.exists():
            raise SystemExit('Use a new output directory; existing results are never overwritten.')
        OUT_ROM = output / OUT_ROM.name
        REPORT = output / REPORT.name
    OUT_ROM.parent.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    add = report.append

    # ---- 게이트 1: 번역 상태 ----
    tr = json.loads(
        (btlib.ROOT / "workspace/text/translation/translation.json").read_text(encoding="utf-8")
    )
    bad = [
        e["id"]
        for e in tr["briefings"]
        if e["status"] not in ("distribution_eligible", "excluded", "needs_review")
    ]
    if bad:
        raise SystemExit(f"브리핑 상태 부적격: {bad}")
    pending_b = [e["id"] for e in tr["briefings"] if e["status"] == "needs_review"]
    if pending_b:
        pass  # 아래 report에 함께 기록
    bad_f = [
        e["id"]
        for e in tr["fixed"]
        if e["status"] not in ("distribution_eligible", "excluded", "needs_review")
    ]
    if bad_f:
        raise SystemExit(f"fixed 상태 부적격: {bad_f}")
    pending = [e["id"] for e in tr["fixed"] if e["status"] == "needs_review"]
    add(f"게이트: 브리핑 {len(tr['briefings'])}건·fixed 45건 상태 적격 (분모 117)")
    if pending_b:
        add(f"개발 입력 경고: briefing {pending_b} = needs_review(검토 대기) — 릴리스 후보 불가")
    if pending:
        add(f"개발 입력 경고: fixed {pending} = needs_review(재승인 대기) — 릴리스 후보 불가")
    add("릴리스 후보 마커: 사용자 최종 문안·전투 두꺼비 v8 로고 통합 — 최종 배포 QA 대상")

    # ---- 인코딩 ----
    all_syms, all_glyphs = ke.load_corpus()
    # id 117~119: 엔딩 시퀀서가 디코드하는 유령 ID — 빈 문자열($FD만) + 빈 글리프 목록
    all_syms += [[], [], []]
    all_glyphs += [[], [], []]
    assert len(all_syms) == N_STRINGS
    freq: Counter[int] = Counter()
    for syms in all_syms:
        freq.update(syms)
        freq[0xFD] += 1
    codes = ke.build_huffman(freq)
    bit0, bit1, symtab = ke.tree_tables(codes)
    if len(bit0) > 104 or len(symtab) > 105:
        raise SystemExit(f"트리 크기 초과: 노드 {len(bit0)}, 리프 {len(symtab)}")

    stream_bits: list[str] = []
    bitpos = 0
    entries: list[tuple[int, int]] = []
    for i, syms in enumerate(all_syms):
        if i % 4 == 0:
            entries.append(btlib.make_pointer_entry(bitpos))
        for s in syms + [0xFD]:
            stream_bits.append(codes[s])
            bitpos += len(codes[s])
    bits = "".join(stream_bits)
    stream = bytearray()
    for i in range(0, len(bits), 8):
        stream.append(int(bits[i : i + 8].ljust(8, "0"), 2))
    if len(stream) > STREAM_MAX:
        raise SystemExit(f"스트림 {len(stream)}B > {STREAM_MAX}B")
    add(f"트리: 노드 {len(bit0)}/104, 리프 {len(symtab)}/105. 스트림 {len(stream)}B/{STREAM_MAX}B")

    # ---- 글리프 레퍼토리·폰트 ----
    repertoire: list[str] = []
    rep_index: dict[str, int] = {}
    for glyphs in all_glyphs:
        for g in glyphs:
            if g not in rep_index:
                rep_index[g] = len(repertoire)
                repertoire.append(g)
    galmuri = ImageFont.truetype(str(FONT_TTF), 16)
    # 원본 재사용은 화면 검증된 글리프만(A-Z, 0-9, 공백, '!'). 나머지 구두점은
    # Galmuri 렌더 — ':'가 원본 테이블 경유로 엉뚱한 자형이 나왔다(krdev2 실측).
    ORIG_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !･")  # ･은 원본 글리프 0x33
    GALMURI_ALT = {"､": ",", '"': "?", "｢": "｢", "｣": "｣"}
    font_blob = bytearray()
    n_orig = n_new = 0
    for ch in repertoire:
        if ch in ORIG_OK:
            gid = orig_glyph_id(prg, ch)
            off = 0x8337 + gid * 8
            font_blob += prg[off : off + 8]
            n_orig += 1
        else:
            font_blob += render_hangul(GALMURI_ALT.get(ch, ch), galmuri)
            n_new += 1
    add(f"폰트: {len(repertoire)}글리프 ({n_new} Galmuri + {n_orig} 원본 재사용) = {len(font_blob)}B")

    # ---- 글리프 목록 ----
    ptrs = bytearray()
    lists = bytearray()
    for glyphs in all_glyphs:
        ptrs += (LISTS_CPU + len(lists)).to_bytes(2, "little")
        lists.append(len(glyphs))
        for g in glyphs:
            lists += rep_index[g].to_bytes(2, "little")
    if LISTS_CPU + len(lists) >= CODE_CPU:
        raise SystemExit("글리프 목록이 코드 영역 침범")
    add(f"글리프 목록: 포인터 {len(ptrs)}B + 데이터 {len(lists)}B")

    # ---- ROM 조립 ----
    raw = bytearray(btlib.ROM_PATH.read_bytes())
    header = raw[:16]
    header[4] = 32  # 512KiB
    rom = bytearray(prg) + bytearray(b"\xff" * (8 * BANK))

    def put6(cpu: int, data: bytes) -> None:
        rom[B6 + cpu - 0x8000 : B6 + cpu - 0x8000 + len(data)] = data

    def put8(cpu: int, data: bytes) -> None:
        rom[B8 + cpu - 0x8000 : B8 + cpu - 0x8000 + len(data)] = data

    # 뱅크 6: 테이블(잔여는 0 패딩)·포인터·스트림
    put6(TAB_BIT0, bit0 + b"\x00" * (104 - len(bit0)))
    put6(TAB_BIT1, bit1 + b"\x00" * (104 - len(bit1)))
    put6(TAB_SYMS, symtab + b"\x00" * (105 - len(symtab)))
    ptr_blob = bytearray()
    for lo, hi in entries:
        ptr_blob += bytes([lo, hi])
    put6(TAB_PTR, bytes(ptr_blob))
    put6(STREAM, bytes(stream))

    # 뱅크 6: $E89F 패치 (원본 기대 바이트 검증 후)
    orig_region = prg[B6 + PATCH_LO - 0x8000 : B6 + PATCH_HI - 0x8000 + 1]
    if orig_region[:2] != bytes.fromhex("A900") or orig_region[-1] != 0x60:
        raise SystemExit("패치 대상 원본 바이트 불일치")
    region = bytearray(b"\xea" * (PATCH_HI - PATCH_LO + 1))
    region[: len(PATCH_CODE)] = PATCH_CODE
    region[0xE8EC - PATCH_LO] = 0x08
    region[0xE8ED - PATCH_LO] = 0x06
    region[0xE8EE - PATCH_LO] = 0x60
    put6(PATCH_LO, bytes(region))

    # 뱅크 8: 폰트·목록·코드·패치 미러·꼬리 스텁
    put8(FONT_CPU, bytes(font_blob))
    put8(PTRS_CPU, bytes(ptrs))
    put8(LISTS_CPU, bytes(lists))
    put8(CODE_CPU, UPLOAD_CODE)
    put8(PATCH_LO, bytes(region))
    tail = prg[B6 + 0xFF80 - 0x8000 : B6 + 0x10000 - 0x8000]
    for nb in range(8, 16):
        rom[nb * BANK + 0x7F80 : nb * BANK + 0x8000] = tail
        rom[nb * BANK + 0x7FAA] = nb  # $FFA7 트램펄린의 ORA #bank 상수
        # NMI 스텁의 LDA #bank 상수($FF91). 이걸 빼먹으면 NMI가 뱅크 6으로
        # 복귀해 뱅크 8 코드 실행 중 폭주한다(krdbg1에서 실측).
        rom[nb * BANK + 0x7F91] = nb

    # ---- 시스템 2: 스토리 제자리 교체 + 공용 폰트 슬롯 재배치 ----
    # 원문 유지 브리핑(레벨명 id 116)의 문자는 공용 폰트로 렌더되므로 보호한다.
    extra_keep: set[int] = set()
    for e, syms in zip(tr["briefings"], all_syms):
        if e["status"] != "excluded":
            continue
        for s in syms:
            if 0x20 <= s < 0x80:
                extra_keep.add(glyph_of_byte(prg, s))
            elif s >= 0xA0:
                extra_keep.add(s - 0x72)
    syl_byte = build_system2(prg, rom, tr, galmuri, add, extra_keep)

    out_buf = bytearray(bytes(header) + bytes(rom))

    # ---- 최종 타이틀 로고: 승인 v8 원화 → 4색 CHR → 원본 RLE 슬롯 ----
    logo_packed, logo_source, logo_info = title_logo.build_logo_stream(save_assets=False)
    if bytes(out_buf[title_logo.PACKED_START:title_logo.PACKED_END]) != logo_source:
        raise SystemExit("정식 빌드의 타이틀 로고 원본 슬롯이 예상과 다름")
    out_buf[title_logo.PACKED_START:title_logo.PACKED_START + len(logo_packed)] = logo_packed
    out = bytes(out_buf)
    add(
        "타이틀 로고: 전투 두꺼비 v8 "
        f"RLE {len(logo_packed)}/{title_logo.PACKED_END - title_logo.PACKED_START}B, 왕복 통과"
    )

    # ---- 게이트 2: 산출물 라운드트립 ----
    class RomView:
        pass

    built_prg = out[16:]

    def rd(cpu: int) -> int:
        return built_prg[B6 + cpu - 0x8000]

    t_bit0 = built_prg[B6 + TAB_BIT0 - 0x8000 :][: len(bit0)]
    t_bit1 = built_prg[B6 + TAB_BIT1 - 0x8000 :][: len(bit1)]
    t_syms = built_prg[B6 + TAB_SYMS - 0x8000 :][: len(symtab)]

    def decode_all() -> list[list[int]]:
        outp: list[list[int]] = []
        for e in range(N_ENTRIES):
            lo = rd(TAB_PTR + e * 2)
            hi = rd(TAB_PTR + e * 2 + 1)
            byteoff = ((hi >> 3) << 8) | lo
            bp = byteoff * 8 + (7 - (hi & 7))
            for _ in range(min(4, N_STRINGS - e * 4)):
                syms: list[int] = []
                while True:
                    x = 0
                    while True:
                        byte = rd(STREAM + bp // 8)
                        b = (byte >> (7 - bp % 8)) & 1
                        bp += 1
                        v = (t_bit1 if b else t_bit0)[x]
                        if v >= 0x80:
                            s = t_syms[v - 0x80]
                            break
                        x = v
                    if s == 0xFD:
                        break
                    syms.append(s)
                outp.append(syms)
        return outp

    decoded = decode_all()
    if decoded != all_syms:
        for i, (a, b) in enumerate(zip(decoded, all_syms)):
            if a != b:
                raise SystemExit(f"라운드트립 실패: 문자열 {i}")
    add(f"게이트: 빌드 산출물 디코드 라운드트립 {len(all_syms)}/{N_STRINGS} 일치")

    # ---- 게이트 2b: 시스템 2 산출물 검증 ----
    byte_syl = {v: k for k, v in syl_byte.items()}
    built_fixed = probe_story.parse_strings(built_prg)
    orig_fixed = probe_story.parse_strings(prg)
    for e, (cpu, ppu, body), (ocpu, oppu, obody) in zip(tr["fixed"], built_fixed, orig_fixed):
        if e["status"] == "excluded" or not e.get("ko"):
            if body != obody or ppu != oppu:
                raise SystemExit(f"fixed {e['id']}: 미번역 문자열 변형됨")
            continue
        if cpu != ocpu or len(body) != len(obody):
            raise SystemExit(f"fixed {e['id']}: 시작 주소/길이 변형")
        text = ""
        for b in body:
            if b in byte_syl:
                text += byte_syl[b]
            elif b == 0xA5:
                text += "･"
            else:
                text += chr(b)
        if text.rstrip(" ") != e["ko"]:
            raise SystemExit(f"fixed {e['id']}: 디코드 불일치 {text!r}")
    add(f"게이트: 시스템 2 디코드 검증 {len(built_fixed)}건 통과(미번역 원형 보존 포함)")

    # ---- 게이트 3: 패치·루틴 디스어셈블 확인 ----
    add("패치 디스어셈블($E89F~):")
    for a, t in disasm(built_prg[B6 : B6 + BANK], 0x8000, PATCH_LO - 0x8000, PATCH_LO - 0x8000 + len(PATCH_CODE)):
        add(f"  ${a:04X}: {t}")
    add("업로드 루틴 디스어셈블($B000~, 앞부분):")
    for a, t in disasm(built_prg[B8 : B8 + BANK], 0x8000, CODE_CPU - 0x8000, CODE_CPU - 0x8000 + 0x30):
        add(f"  ${a:04X}: {t}")

    OUT_ROM.write_bytes(out)
    sha = hashlib.sha256(out).hexdigest().upper()
    add(f"산출: {OUT_ROM.name} ({len(out)}B) SHA256={sha}")
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
