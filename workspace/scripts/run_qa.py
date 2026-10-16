"""Mesen 헤드리스로 Battletoads ROM을 돌리고 스크린샷·버퍼 덤프를 모은다.

City Connection의 run_qa.py를 기반으로 했다. Battletoads 전용으로
$07C5 글리프 워킹셋 감지 자동 촬영이 템플릿에 들어 있다.

사용법:
    python workspace/scripts/run_qa.py build/poc_glyph.nes --out work/qa/poc
    python workspace/scripts/run_qa.py build/poc_glyph.nes --out work/qa/poc --frames 4000 --shots 300:3900:300
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "workspace" / "tests" / "qa_capture.lua.tmpl"
DEFAULT_MESEN = Path(r"H:\Mesen\Mesen.exe")

# 부팅 -> 타이틀에서 Start -> 인트로 컷신. 프레임 수는 NTSC 60fps 기준 가설이며
# 첫 실행 로그를 보고 조정한다.
DEFAULT_PRESSES = [
    {"from": 400, "to": 410, "button": "start"},
    {"from": 700, "to": 708, "button": "start"},
]
# 워킹셋 감지 후 이만큼 지난 프레임에 촬영 (텍스트가 화면에 그려질 시간을 준다)
DEFAULT_WATCH_DELAYS = [10, 60, 150, 300]


def lua_table(obj) -> str:
    if isinstance(obj, dict):
        items = ", ".join(f"[{lua_table(k)}]={lua_table(v)}" for k, v in obj.items())
        return "{" + items + "}"
    if isinstance(obj, list):
        return "{" + ", ".join(lua_table(v) for v in obj) + "}"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, str):
        return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(obj)


def lua_press_table(presses: list[dict]) -> str:
    parts = [
        "{from=%d, to=%d, button=%s}" % (p["from"], p["to"], lua_table(p["button"]))
        for p in presses
    ]
    return "{" + ", ".join(parts) + "}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", help="프로젝트 루트 기준 ROM 경로")
    ap.add_argument("--out", default="work/qa/run")
    ap.add_argument("--frames", type=int, default=4000)
    ap.add_argument("--mesen", default=str(DEFAULT_MESEN))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument(
        "--shots",
        help="고정 촬영 프레임. '600,700,800' 또는 '600:900:20'(from:to:step)",
    )
    ap.add_argument("--no-input", action="store_true", help="입력 없이 어트랙트 모드만 돌린다")
    ap.add_argument(
        "--press",
        action="append",
        default=[],
        metavar="FRAME:BUTTON",
        help="지정 프레임부터 8프레임 동안 버튼을 누른다. 예: --press 500:start",
    )
    ap.add_argument(
        "--poke",
        action="append",
        default=[],
        metavar="ADDR=VAL",
        help="매 프레임 시작 시 RAM 강제 기록. 예: --poke BD=28 (16진 주소=10진/0x값)",
    )
    args = ap.parse_args()

    mesen = Path(args.mesen)
    if not mesen.exists():
        raise SystemExit(f"Mesen.exe를 찾을 수 없다: {mesen}")

    rom = ROOT / args.rom
    if not rom.exists():
        raise SystemExit(f"ROM 없음: {rom}")

    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shots: dict[int, str] = {}
    if args.shots:
        if ":" in args.shots:
            a, b, step = (int(x) for x in args.shots.split(":"))
            frames_list = list(range(a, b + 1, step))
        else:
            frames_list = [int(x) for x in args.shots.split(",")]
        shots = {f: f"f{f:05d}" for f in frames_list if f <= args.frames}

    if args.no_input:
        presses: list[dict] = []
    elif args.press:
        presses = []
        for spec in args.press:
            f_s, _, btn = spec.partition(":")
            presses.append({"from": int(f_s), "to": int(f_s) + 8, "button": btn})
    else:
        presses = list(DEFAULT_PRESSES)

    pokes = []
    for spec in args.poke:
        addr_s, _, val_s = spec.partition("=")
        pokes.append({"addr": int(addr_s, 16), "value": int(val_s, 0)})
    script = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("@@OUT@@", str(out).replace("\\", "/"))
        .replace("@@SHOTS@@", lua_table(shots))
        .replace("@@PRESSES@@", lua_press_table(presses))
        .replace("@@LAST_FRAME@@", str(args.frames))
        .replace("@@WATCH_DELAYS@@", lua_table(DEFAULT_WATCH_DELAYS))
        .replace(
            "@@POKES@@",
            "{" + ", ".join("{addr=%d, value=%d}" % (p["addr"], p["value"]) for p in pokes) + "}",
        )
    )
    script_path = out / "qa_capture.lua"
    script_path.write_text(script, encoding="utf-8")

    # Mesen은 경로에 공백이 있으면 인자 분해에 민감하다. 실행 전 공백 없는 곳으로 복사한다.
    staged_rom = out / "rom.nes"
    shutil.copyfile(rom, staged_rom)

    cmd = [str(mesen), "--testRunner", str(script_path), str(staged_rom)]
    print("실행:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    proc = None
    try:
        proc = subprocess.run(
            cmd, cwd=str(mesen.parent), capture_output=True, text=True, timeout=args.timeout
        )
        print(f"종료 코드: {proc.returncode}")
    except subprocess.TimeoutExpired:
        print(f"{args.timeout}초 안에 종료되지 않았다. Lua 오류로 스크립트가 죽었을 수 있다.")

    log = out / "qa_log.txt"
    if log.exists():
        print("\n--- qa_log.txt ---")
        print(log.read_text(encoding="utf-8"))
    else:
        print("\nqa_log.txt가 없다. Lua 스크립트가 실행되지 않았다.")
        if proc and proc.stdout:
            print(proc.stdout[-2000:])
        sys.exit(1)

    pngs = sorted(out.glob("*.png"))
    print(f"스크린샷 {len(pngs)}장: {', '.join(p.name for p in pngs)}")
    print(f"출력 폴더: {out}")


if __name__ == "__main__":
    main()
