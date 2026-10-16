"""번역 아티팩트의 추출 기준선(source) JSON 생성.

- workspace/text/source/briefings.json  : 시스템 1(허프만) 104개
- workspace/text/source/fixed_strings.json : 시스템 2(비압축) 45개

보호 필드(원문 심볼/바이트, 토큰 텍스트, 구조)는 이 스크립트만 만든다.
번역은 workspace/text/translation/translation.json 만 수정한다.

토큰(가역): {fc}=0xFC(개행+공백1 단축), {nl:N}=0x80+N(개행+공백N),
가나=반각 U+FF61~, ASCII=그대로. 종료자 0xFD는 저장하지 않는다(엔트리 경계).

실행: python workspace/scripts/extract_artifacts.py
"""
from __future__ import annotations

import json

import btlib
import probe_story


def tokenize(syms: list[int]) -> str:
    out = []
    for s in syms:
        if s == btlib.SYM_NL:
            out.append("{fc}")
        elif 0x80 <= s <= 0x9F:
            out.append(f"{{nl:{s - 0x80}}}")
        else:
            out.append(btlib.sym_repr(s))
    return "".join(out)


def main() -> None:
    prg = btlib.load_prg()
    src_dir = btlib.ROOT / "workspace" / "text" / "source"
    src_dir.mkdir(parents=True, exist_ok=True)

    strings = btlib.extract_all(prg)
    briefings = {
        "table_id": "briefings",
        "source": {
            "system": "huffman-bank6",
            "pointer_table": "$EA54",
            "stream": "$EA90..$FAE4",
            "rom_sha256": btlib.ORIG_SHA256,
            "terminator": "FD",
            "notes": "엔트리 순서 = 스트림 순서. 자세한 구조는 workspace/analysis/SURVEY.md A2",
        },
        "entries": [
            {
                "entry_id": i,
                "sym_hex": bytes(syms).hex(" ").upper(),
                "text": tokenize(syms),
            }
            for i, syms in enumerate(strings)
        ],
    }
    (src_dir / "briefings.json").write_text(
        json.dumps(briefings, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    fixed_entries = []
    for i, (cpu, ppu, body) in enumerate(probe_story.parse_strings(prg)):
        fixed_entries.append(
            {
                "entry_id": i,
                "cpu": f"${cpu:04X}",
                "ppu": f"${ppu:04X}",
                "raw_hex": body.hex(" ").upper(),
                "byte_len": len(body),
                "text": "".join(btlib.sym_repr(b) for b in body),
            }
        )
    fixed = {
        "table_id": "fixed_strings",
        "source": {
            "system": "uncompressed-bank6",
            "renderer": "$DA00",
            "block": "$DA3F..$DD07",
            "rom_sha256": btlib.ORIG_SHA256,
            "format": "[ppu hi][ppu lo][chars...][00]",
            "notes": "가나=JIS X 0201, ASCII=$DCE8 테이블. SURVEY.md A5. 제자리 교체 시 byte_len 이하 유지",
        },
        "entries": fixed_entries,
    }
    (src_dir / "fixed_strings.json").write_text(
        json.dumps(fixed, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"briefings: {len(strings)}, fixed: {len(fixed_entries)}")


if __name__ == "__main__":
    main()
