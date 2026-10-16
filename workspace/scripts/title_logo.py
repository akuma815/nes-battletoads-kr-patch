"""Battletoads 타이틀 로고 추출·결정론적 한글 시안·PoC ROM 생성.

원본 타이틀은 뱅크 7의 $97A2 스트림을 $8AA3~$8B6D 루틴이 풀어
CHR-RAM $1000에 0xC3타일을 올린다. 스트림은 첫 두 바이트를 0/FF
RLE 마커로 사용하고, 그 밖의 바이트는 리터럴이다.

실행:
    python -X utf8 workspace/scripts/title_logo.py
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "original" / "Battletoads (Japan).nes"
DEV_ROM = ROOT / "build" / "Battletoads_KR_dev.nes"
OUT_ROM = ROOT / "build" / "Battletoads_KR_logo_poc_v8.nes"
EVIDENCE = ROOT / "work" / "qa" / "title_logo_probe"
ASSETS = ROOT / "workspace" / "graphics" / "title_logo"
REFERENCE_ART = ASSETS / "title_logo_reference_custom_v1.png"

EXPECTED_ROM_SHA256 = "B831F75C36EEF329A34D0E0D9308CDF85864EDD87E7DA6D8E408307F8BF402D8"
PACKED_START = 0x397B2
PACKED_END = 0x3A297
RAW_SIZE = 0xC3 * 16
PATTERN_BASE = 0x1000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def decode_rle(packed: bytes, raw_size: int = RAW_SIZE) -> tuple[bytes, int]:
    zero_marker, ff_marker = packed[:2]
    out = bytearray()
    pos = 2
    while len(out) < raw_size:
        value = packed[pos]
        pos += 1
        if value == zero_marker or value == ff_marker:
            count = packed[pos]
            pos += 1
            out.extend(bytes([0x00 if value == zero_marker else 0xFF]) * count)
        else:
            out.append(value)
    if len(out) != raw_size:
        raise ValueError(f"RLE 출력 크기 불일치: {len(out)} != {raw_size}")
    return bytes(out), pos


def encode_rle(raw: bytes) -> bytes:
    used = set(raw)
    markers = [v for v in range(1, 255) if v not in used]
    if len(markers) < 2:
        raise ValueError("RLE 마커로 쓸 미사용 바이트가 2개 미만")
    zero_marker, ff_marker = markers[:2]
    out = bytearray([zero_marker, ff_marker])
    pos = 0
    while pos < len(raw):
        value = raw[pos]
        if value in (0x00, 0xFF):
            end = pos + 1
            while end < len(raw) and raw[end] == value and end - pos < 255:
                end += 1
            run = end - pos
            if run >= 3:
                out.extend((zero_marker if value == 0 else ff_marker, run))
                pos = end
                continue
        out.append(value)
        pos += 1
    return bytes(out)


def decode_tile(tile: bytes) -> list[int]:
    pixels: list[int] = []
    for y in range(8):
        p0, p1 = tile[y], tile[y + 8]
        for x in range(8):
            bit = 7 - x
            pixels.append(((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1))
    return pixels


def encode_tile(pixels: list[int]) -> bytes:
    if len(pixels) != 64:
        raise ValueError("타일 픽셀 수가 64가 아님")
    p0 = bytearray(8)
    p1 = bytearray(8)
    for y in range(8):
        for x in range(8):
            value = pixels[y * 8 + x]
            bit = 7 - x
            p0[y] |= (value & 1) << bit
            p1[y] |= ((value >> 1) & 1) << bit
    return bytes(p0 + p1)


def render_tiles(raw: bytes, nametable: bytes) -> Image.Image:
    canvas = Image.new("P", (256, 120), 0)
    # 확인용 RGB 팔레트: 검정, 밝은 녹색, 어두운 녹색, 황록색.
    canvas.putpalette([0, 0, 0, 70, 170, 0, 0, 80, 0, 210, 230, 0] + [0] * 756)
    px = canvas.load()
    for ty in range(15):
        for tx in range(32):
            tile_id = nametable[ty * 32 + tx]
            tile = raw[tile_id * 16 : (tile_id + 1) * 16]
            vals = decode_tile(tile)
            for y in range(8):
                for x in range(8):
                    px[tx * 8 + x, ty * 8 + y] = vals[y * 8 + x]
    return canvas


def render_syllable(ch: str, size: int, angle: int) -> Image.Image:
    """폰트를 쓰지 않고 음절 자모를 굵은 픽셀 로고 도형으로 직접 그린다."""
    mask = Image.new("L", (48, 48), 0)
    d = ImageDraw.Draw(mask)

    def stroke(points: list[tuple[int, int]], width: int = 9) -> None:
        # 좌우 대칭을 일부러 피한 꺾은선으로 원본 손그림 로고의 불규칙성을 준다.
        d.line(points, fill=255, width=width, joint="curve")

    if ch == "전":
        # ㅈ + ㅓ + ㄴ
        stroke([(4, 5), (23, 4)])
        stroke([(14, 6), (6, 18)])
        stroke([(14, 6), (23, 17)])
        stroke([(32, 3), (31, 25)])
        stroke([(23, 14), (33, 13)])
        stroke([(8, 25), (7, 38), (34, 38)])
    elif ch == "투":
        # ㅌ + ㅜ
        stroke([(6, 5), (38, 4)])
        stroke([(8, 5), (8, 22), (37, 21), (37, 4)])
        stroke([(9, 13), (36, 12)])
        stroke([(6, 30), (39, 29)])
        stroke([(23, 29), (23, 42)])
    elif ch == "두":
        # ㄷ + ㅜ
        stroke([(7, 5), (38, 4), (37, 23), (7, 24), (7, 5)])
        stroke([(5, 32), (40, 31)])
        stroke([(23, 31), (23, 43)])
    elif ch == "꺼":
        # ㄲ + ㅓ
        stroke([(3, 5), (14, 4), (14, 20)])
        stroke([(17, 5), (27, 4), (27, 20)])
        stroke([(37, 3), (36, 28)])
        stroke([(28, 15), (39, 14)])
    elif ch == "비":
        # ㅂ + ㅣ
        stroke([(6, 5), (27, 4), (27, 39), (6, 39), (6, 5)])
        stroke([(7, 21), (27, 20)])
        stroke([(38, 3), (37, 41)])
    else:
        raise ValueError(f"지원하지 않는 로고 음절: {ch}")

    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError(f"빈 로고 음절: {ch}")
    mask = mask.crop((max(0, bbox[0] - 2), max(0, bbox[1] - 2),
                      min(48, bbox[2] + 2), min(48, bbox[3] + 2)))
    target_height = round(size * 0.56)
    target_width = max(1, round(mask.width * target_height / mask.height))
    mask = mask.resize((target_width, target_height), Image.Resampling.NEAREST)
    return mask.rotate(angle, resample=Image.Resampling.NEAREST, expand=True, fillcolor=0)


def make_handdraw_concept(original: Image.Image) -> Image.Image:
    concept = Image.new("P", original.size, 0)
    concept.putpalette(original.getpalette())
    src = original.load()
    dst = concept.load()

    # 본체와 맞닿은 원문 글자를 포함한 연결 성분을 얻고, 그 안의 영문 자소
    # 구멍은 메운다. 아래가 열린 중앙 아치 구멍은 외부와 연결되므로 유지된다.
    w, h = original.size
    component: set[tuple[int, int]] = set()
    q = deque([(128, 40)])
    while q:
        x, y = q.popleft()
        if (x, y) in component or not (0 <= x < w and 0 <= y < h) or src[x, y] == 0:
            continue
        component.add((x, y))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    q.append((x + dx, y + dy))

    min_x = min(x for x, _ in component)
    max_x = max(x for x, _ in component)
    min_y = min(y for _, y in component)
    max_y = max(y for _, y in component)
    outside: set[tuple[int, int]] = set()
    q = deque()
    for x in range(min_x, max_x + 1):
        q.append((x, min_y))
        q.append((x, max_y))
    for y in range(min_y, max_y + 1):
        q.append((min_x, y))
        q.append((max_x, y))
    while q:
        x, y = q.popleft()
        if (x, y) in outside or not (min_x <= x <= max_x and min_y <= y <= max_y):
            continue
        if (x, y) in component:
            continue
        outside.add((x, y))
        q.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))

    body = Image.new("L", original.size, 0)
    body_px = body.load()
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if (x, y) not in outside:
                body_px[x, y] = 255
    interior = body.filter(ImageFilter.MinFilter(5))
    interior_px = interior.load()

    # 아래·오른쪽의 짙은 녹색 그림자, 황록색 외곽, 녹색 본체 순서.
    for y in range(h):
        for x in range(w):
            if x >= 2 and y >= 3 and body_px[x - 2, y - 3]:
                dst[x, y] = 2
    for y in range(h):
        for x in range(w):
            if body_px[x, y]:
                dst[x, y] = 1 if interior_px[x, y] else 3
    # 압축을 해치지 않는 규칙적 점묘를 내부 일부에만 추가한다.
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if interior_px[x, y] and (x + y * 3) % 17 == 0:
                dst[x, y] = 2

    # 본체와 분리된 등록상표 표시는 원본 픽셀을 그대로 보존한다.
    for y in range(32, 58):
        for x in range(194, 222):
            if src[x, y]:
                dst[x, y] = src[x, y]

    # 각 음절의 크기·기울기·기준선을 아치에 개별 배치한다.
    specs = [
        ("전", 68, 22, 60, 78),
        ("투", 60, 10, 91, 61),
        ("두", 52, 0, 131, 51),
        ("꺼", 60, -10, 164, 61),
        ("비", 68, -22, 196, 78),
    ]
    for ch, size, angle, cx, cy in specs:
        mask = render_syllable(ch, size, angle)
        x0 = round(cx - mask.width / 2)
        y0 = round(cy - mask.height / 2)
        mpx = mask.load()
        # 짙은 녹색 외곽·그림자 뒤에 황록색 본문을 얹는다.
        outline = mask.filter(ImageFilter.MaxFilter(5))
        opx = outline.load()
        for y in range(outline.height):
            for x in range(outline.width):
                if not opx[x, y]:
                    continue
                xx, yy = x0 + x, y0 + y
                if 0 <= xx < 256 and 0 <= yy < 120 and interior_px[xx, yy]:
                    dst[xx, yy] = 2
        for y in range(mask.height):
            for x in range(mask.width):
                if not mpx[x, y]:
                    continue
                xx, yy = x0 + x, y0 + y
                if 0 <= xx + 2 < 256 and 0 <= yy + 3 < 120 and interior_px[xx + 2, yy + 3]:
                    dst[xx + 2, yy + 3] = 2
                if 0 <= xx < 256 and 0 <= yy < 120 and interior_px[xx, yy]:
                    dst[xx, yy] = 3

    return concept


def make_concept(original: Image.Image) -> Image.Image:
    """승인된 고해상도 조형을 원본 타이틀의 184x88 4색 영역으로 환원한다."""
    reference = Image.open(REFERENCE_ART).convert("RGB")
    # 실제 네임테이블의 오른쪽 표시 한계는 26열 끝(x=215)이다. 원화 경계
    # 왼쪽 60px·오른쪽 100px을 포함해 끝점을 x≈206으로 당긴다.
    logo = reference.crop((143, 158, 1198, 610))
    logo = logo.resize((184, 88), Image.Resampling.NEAREST)

    concept = Image.new("P", original.size, 0)
    concept.putpalette(original.getpalette())
    dst = concept.load()
    src = logo.load()

    # NES 원본 팔레트 의미: 0=투명/검정, 1=밝은 녹색, 2=짙은 녹색, 3=노랑/오렌지.
    # 생성 원화의 중간색은 최근접 색 대신 역할별로 분류해 글자와 본체 대비를 보존한다.
    reduced = [[0 for _ in range(184)] for _ in range(88)]
    for y in range(88):
        for x in range(184):
            r, g, b = src[x, y]
            peak = max(r, g, b)
            if peak < 38:
                value = 0
            elif r >= 145 and g >= 75 and b <= 105 and r >= g * 1.05:
                value = 3
            elif g >= 65 and g >= r * 0.78 and g >= b * 1.25:
                value = 1 if (g + r // 3) >= 135 else 2
            elif r >= 110 and g >= 100 and b < 90:
                value = 3
            else:
                value = 2 if peak >= 55 else 0
            reduced[y][x] = value

    # 생성 원화의 피부 점묘 중 고립된 1픽셀만 제거한다. 글자(3)와 외곽(0)은 건드리지 않는다.
    for _ in range(3):
        cleaned = [row[:] for row in reduced]
        for y in range(1, 87):
            for x in range(1, 183):
                if reduced[y][x] not in (1, 2):
                    continue
                neighbors = [
                    reduced[yy][xx]
                    for yy in range(y - 1, y + 2)
                    for xx in range(x - 1, x + 2)
                    if xx != x or yy != y
                ]
                light = neighbors.count(1)
                dark = neighbors.count(2)
                if light >= 6:
                    cleaned[y][x] = 1
                elif dark >= 6:
                    cleaned[y][x] = 2
        reduced = cleaned

    for y in range(88):
        for x in range(184):
            dst[40 + x, 32 + y] = reduced[y][x]

    return concept


def canvas_to_tiles(concept: Image.Image, nametable: bytes, original_raw: bytes) -> bytes:
    px = concept.load()
    positions: dict[int, list[tuple[int, int]]] = {}
    for ty in range(4, 15):
        for tx in range(32):
            tile_id = nametable[ty * 32 + tx]
            if 1 <= tile_id <= 0xC1:
                positions.setdefault(tile_id, []).append((tx, ty))

    raw = bytearray(original_raw)
    for tile_id in range(1, 0xC2):
        pos = positions[tile_id][0]
        # 원본에서 두 위치가 공유하는 0B/8F는 외곽 보존 타일이므로 그대로 둔다.
        if len(positions[tile_id]) > 1:
            continue
        tx, ty = pos
        vals = [px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
        raw[tile_id * 16 : (tile_id + 1) * 16] = encode_tile(vals)
    return bytes(raw)


def build_logo_stream(save_assets: bool = False) -> tuple[bytes, bytes, dict[str, object]]:
    """최종 v8 로고 스트림과 원본 슬롯을 반환한다. 정식 빌드에서도 같은 게이트를 쓴다."""
    original_rom = ORIGINAL.read_bytes()
    if sha256(original_rom) != EXPECTED_ROM_SHA256:
        raise SystemExit("지원 원본 SHA-256 불일치")

    packed_region = original_rom[PACKED_START:PACKED_END]
    original_raw, consumed = decode_rle(packed_region)
    if consumed != PACKED_END - PACKED_START:
        raise SystemExit(f"원본 스트림 경계 불일치: {consumed} != {PACKED_END - PACKED_START}")

    chr_dump = (EVIDENCE / "chr_ram_0000_1fff.bin").read_bytes()
    if original_raw != chr_dump[PATTERN_BASE : PATTERN_BASE + RAW_SIZE]:
        raise SystemExit("원본 디코드와 타이틀 런타임 CHR-RAM 덤프 불일치")
    nametable = (EVIDENCE / "nametable_0000_03ff.bin").read_bytes()

    original_image = render_tiles(original_raw, nametable)
    concept = make_concept(original_image)
    if save_assets:
        ASSETS.mkdir(parents=True, exist_ok=True)
        original_image.save(ASSETS / "original_logo_index.png")
        concept.save(ASSETS / "title_logo_concept_v8.png")

    target_raw = canvas_to_tiles(concept, nametable, original_raw)
    packed = encode_rle(target_raw)
    if len(packed) > PACKED_END - PACKED_START:
        raise SystemExit(f"한글 로고 스트림 초과: {len(packed)} > {PACKED_END - PACKED_START}")
    if decode_rle(packed)[0] != target_raw:
        raise SystemExit("한글 로고 RLE 라운드트립 실패")

    info: dict[str, object] = {
        "source_rom_sha256": sha256(original_rom),
        "runtime_chr_sha256": sha256(chr_dump),
        "packed_source": {"start": PACKED_START, "end": PACKED_END, "size": len(packed_region)},
        "packed_target_size": len(packed),
        "raw_roundtrip": True,
        "text": "전투 두꺼비",
        "art_policy": "승인 고해상도 커스텀 원화를 184x88 NES 4색 인덱스로 환원",
    }
    return packed, packed_region, info


def main() -> None:
    packed, packed_region, manifest = build_logo_stream(save_assets=True)

    dev = bytearray(DEV_ROM.read_bytes())
    if bytes(dev[PACKED_START:PACKED_END]) != packed_region:
        raise SystemExit("개발 ROM의 로고 원본 바이트가 예상과 다름")
    dev[PACKED_START : PACKED_START + len(packed)] = packed
    OUT_ROM.write_bytes(dev)

    manifest["output_rom"] = str(OUT_ROM.relative_to(ROOT))
    manifest["output_rom_sha256"] = sha256(bytes(dev))
    (ASSETS / "title_logo_poc_v8.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
