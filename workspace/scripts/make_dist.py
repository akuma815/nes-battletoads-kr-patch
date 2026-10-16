"""배포물을 만든다. 원본 ROM은 절대 포함하지 않고 xdelta 차분 패치만 낸다.

City Connection의 make_dist.py 구조를 따른다.

    dist/Battletoads_KR_Patch_<날짜>/
    ├─ Battletoads_KR_<날짜>.xdelta
    ├─ apply.cmd / apply.ps1 / README_적용방법.txt / SHA256.txt
    ├─ release_report.json
    └─ tools/xdelta3.exe

사용법: python workspace/scripts/make_dist.py [--date YYYYMMDD] [--stage pre|release]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "original" / "Battletoads (Japan).nes"
BUILD = ROOT / "build" / "Battletoads_KR_dev.nes"
DIST = ROOT / "dist"
TOOLS = ROOT.parents[1] / "Tools" / "xdelta3-3.2.0-windows-x86_64"
XDELTA = TOOLS / "xdelta3.exe"
LEDGER = ROOT / "workspace" / "text" / "translation" / "translation.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_text(path: Path, text: str, bom: bool = False) -> None:
    """UTF-8 + CRLF. `.ps1`은 BOM 필수(PS 5.1 한글 인코딩)."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)


APPLY_CMD = """@echo off
chcp 65001 >nul
if "%~1"=="" (
  echo 사용법: 원본 .nes 파일을 이 파일 위로 끌어다 놓으세요.
  echo         또는  apply.cmd "Battletoads (Japan).nes"
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply.ps1" "%~f1"
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
"""

APPLY_PS1 = """param([Parameter(Mandatory = $true)][string]$InputRom)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $InputRom).Path
$base = [IO.Path]::GetFileNameWithoutExtension($source)
$dir = Split-Path -Parent $source
$output = Join-Path $dir ($base + '_KR.nes')
$patch = Join-Path $PSScriptRoot '{patch_name}'
$xdelta = Join-Path $PSScriptRoot 'tools\\xdelta3.exe'

try {{ [Console]::OutputEncoding = [Text.Encoding]::UTF8 }} catch {{ }}

$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
if ($sourceHash -ne '{src_sha_upper}') {{
    Write-Host ''
    Write-Host '[실패] 지원하지 않는 원본입니다.' -ForegroundColor Red
    Write-Host "  넣은 파일 : $source"
    Write-Host "  이 파일의 SHA-256 : $sourceHash"
    Write-Host '  필요한 SHA-256    : {src_sha_upper}'
    Write-Host ''
    Write-Host '  대상은 Battletoads (Japan) 일본판 262,160바이트 ROM입니다.'
    exit 1
}}

& $xdelta -d -f -s $source $patch $output
if ($LASTEXITCODE -ne 0) {{
    Write-Host "[실패] xdelta 오류 (종료 코드 $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}}

$outputHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $output).Hash
if ($outputHash -ne '{out_sha_upper}') {{
    Write-Host '[실패] 패치 결과가 기대값과 다릅니다.' -ForegroundColor Red
    Write-Host "  결과 SHA-256 : $outputHash"
    exit 1
}}

Write-Host ''
Write-Host '[완료] 한글 패치를 적용했습니다.' -ForegroundColor Green
Write-Host "  $output"
exit 0
"""


def readme_text(patch_name: str, day: str, src_sha: str, out_sha: str, stage: str) -> str:
    stage_note = (
        "※ 이 패키지는 검증용 사전 배포판(pre-release)입니다.\n"
        if stage == "pre"
        else ""
    )
    return f"""========================================================================
 배틀토드 (패미컴) 한글 패치 ({day[:4]}-{day[4:6]}-{day[6:]})
 대상: 일본판 Battletoads (Japan) / Masaya·Rare 1991
========================================================================
{stage_note}
■ 구성

  {patch_name}        ROM 패치
  apply.cmd                          적용 도우미
  apply.ps1                          적용 스크립트
  tools\\xdelta3.exe                  xdelta 3.2.0
  SHA256.txt                         배포 파일 무결성 목록
  release_report.json                패치 생성·역검증 기록

원본 또는 패치 완료 ROM은 배포물에 포함되지 않습니다.


■ 1. 적용 방법

원본 .nes 파일을 apply.cmd 위로 끌어다 놓거나 다음처럼 실행합니다.

  apply.cmd "Battletoads (Japan).nes"

출력은 원본 옆의 `<원본 이름>_KR.nes`입니다.

원본과 결과물 검증값:

  원본:    {ORIGINAL.stat().st_size:,} 바이트 (No-Intro "Battletoads (Japan)")
           {src_sha.upper()}
  패치 후: {BUILD.stat().st_size:,} 바이트
           {out_sha.upper()}

패치 후 파일은 원본의 2배(512KiB)입니다. 한글 글꼴과 새 텍스트 데이터를
확장 영역에 넣기 때문입니다.


■ 2. 번역 범위

  · 레벨 사이의 브리핑 컷신 전체(T.Bird 교수·Dark Queen 대사 104개)
  · 타이틀 스토리 화면 전체
  · 게임 오버 시 격려·조롱 대사, 엔딩 대사
  · 타이틀 로고 `BATTLETOADS` → `전투 두꺼비`

■ 3. 원문을 유지한 것

  · 인명·지명·레벨명(RASH, DARK QUEEN, TURBO TUNNEL 등) — 일본판도
    라틴 문자를 그대로 쓰며, 그 스타일을 따랐습니다
  · 메뉴(1 PLAYER 등)·저작권 표기 — 일본판 원문 그대로
  · MEGA WARP 등 치트 문구


■ 4. 실행 환경 (중요)

패치 후 ROM은 512KiB 오버사이즈 매퍼 7(AxROM)입니다.

  · 에뮬레이터: Mesen 2, BizHawk 2.11에서 검증했습니다. 대부분의
    현행 에뮬레이터에서 동작할 것으로 예상합니다.
  · 플래시 카트리지(Everdrive 등): 오버사이즈 매퍼 7을 지원하는
    기기에서 동작합니다.
  · 순정 AxROM 기판 실기: 보드가 256KiB까지만 지원하므로 동작하지
    않습니다.


■ 5. 제거

원본 .nes 파일을 그대로 다시 사용하면 됩니다. 패치는 원본을 수정하지
않고 별도 파일을 만듭니다.


■ 6. 주의·저작권

패치 적용이 끝난 .nes 파일을 배포하지 마세요. xdelta 파일만 공유할 수
있습니다. SHA256.txt로 배포 파일의 무결성을 확인할 수 있습니다.

xdelta3 3.2.0은 Apache License 2.0 도구입니다(tools\\README_xdelta3.md).

한글 글꼴은 Galmuri8x8(© 2019-2025 Lee Minseo, SIL Open Font License 1.1,
galmuri.quiple.dev)에서 8×8 비트맵으로 변환해 ROM에 넣었습니다. OFL 조건에
따라 글꼴 자체는 판매되지 않으며, 글꼴 파일은 배포물에 포함되지 않습니다.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    ap.add_argument("--stage", choices=["pre", "release"], default="pre")
    ap.add_argument("--keep-old", action="store_true")
    args = ap.parse_args()

    for p in (ORIGINAL, BUILD, XDELTA):
        if not p.exists():
            raise SystemExit(f"없음: {p}")

    day = args.date
    name = f"Battletoads_KR_Patch_{day}"
    pkg = DIST / name
    patch_name = f"Battletoads_KR_{day}.xdelta"

    if DIST.exists() and not args.keep_old:
        shutil.rmtree(DIST)
    (pkg / "tools").mkdir(parents=True, exist_ok=True)

    patch = pkg / patch_name
    subprocess.run(
        [str(XDELTA), "-e", "-f", "-s", str(ORIGINAL), str(BUILD), str(patch)],
        check=True,
        capture_output=True,
    )

    src_sha = sha256(ORIGINAL)
    out_sha = sha256(BUILD)

    shutil.copyfile(XDELTA, pkg / "tools" / "xdelta3.exe")
    readme_x = TOOLS / "README.md"
    if readme_x.exists():
        shutil.copyfile(readme_x, pkg / "tools" / "README_xdelta3.md")

    write_text(pkg / "apply.cmd", APPLY_CMD)
    write_text(
        pkg / "apply.ps1",
        APPLY_PS1.format(
            patch_name=patch_name,
            src_sha_upper=src_sha.upper(),
            out_sha_upper=out_sha.upper(),
        ),
        bom=True,
    )
    write_text(pkg / "README_적용방법.txt", readme_text(patch_name, day, src_sha, out_sha, args.stage))

    # 역검증: 만든 패치를 실제로 적용해 결과 해시 확인
    with tempfile.TemporaryDirectory() as td:
        check = Path(td) / "roundtrip.nes"
        subprocess.run(
            [str(XDELTA), "-d", "-f", "-s", str(ORIGINAL), str(patch), str(check)],
            check=True,
            capture_output=True,
        )
        reverse = "PASS" if sha256(check) == out_sha else "FAIL"
    if reverse != "PASS":
        raise SystemExit("역검증 실패")

    # apply.ps1 실전 검증(공백 경로 + 잘못된 원본 거부)
    with tempfile.TemporaryDirectory() as td:
        space_dir = Path(td) / "패치 테스트 폴더"
        space_dir.mkdir()
        src_copy = space_dir / ORIGINAL.name
        shutil.copyfile(ORIGINAL, src_copy)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(pkg / "apply.ps1"), str(src_copy)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        produced = src_copy.with_name(src_copy.stem + "_KR.nes")
        apply_ok = proc.returncode == 0 and produced.exists() and sha256(produced) == out_sha
        bad = space_dir / "wrong.nes"
        bad.write_bytes(b"\x00" * 1000)
        bad_proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(pkg / "apply.ps1"), str(bad)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        reject_ok = bad_proc.returncode != 0
    if not apply_ok:
        raise SystemExit(f"apply.ps1 검증 실패\n{proc.stdout}\n{proc.stderr}")
    if not reject_ok:
        raise SystemExit("apply.ps1이 잘못된 원본을 거부하지 않는다")

    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "release_stage": "pre-release test build" if args.stage == "pre" else "release",
        "status": "PASS: patch reverse-verified and apply helper tested",
        "distribution_policy": "single ROM patch, Japan revision only, oversize AxROM 512KiB",
        "contains_original_game_files": False,
        "release_date": day,
        "patches": [{
            "id": "JP",
            "rom": ORIGINAL.name,
            "mapper": 7,
            "patch": patch_name,
            "patch_size": patch.stat().st_size,
            "patch_sha256": sha256(patch),
            "source_size": ORIGINAL.stat().st_size,
            "source_sha256": src_sha,
            "target_size": BUILD.stat().st_size,
            "target_sha256": out_sha,
            "reverse_verification": reverse,
        }],
        "coverage": {
            "title_logo_translated": True,
            "briefings_translated": sum(
                1 for e in led["briefings"] if e["status"] == "distribution_eligible"
            ),
            "briefings_kept_original": [e["id"] for e in led["briefings"] if e["status"] == "excluded"],
            "fixed_translated": sum(
                1 for e in led["fixed"] if e["status"] == "distribution_eligible" and e.get("ko")
            ),
            "fixed_kept_original": sum(1 for e in led["fixed"] if e["status"] == "excluded"),
        },
        "verification": {
            "build_gates": "PASS: 117/117 decode roundtrip, slot/width/pool limits",
            "emulator": "Mesen 2: final ROM 11000-frame flow, title logo/menu, briefing call, level-name hook / BizHawk 2.11.2: final ROM boot, title logo/menu, start flow",
            "hardware": "not applicable (oversize AxROM, stock boards unsupported)",
        },
    }
    (pkg / "release_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    entries = []
    for f in sorted(pkg.rglob("*")):
        if f.is_file() and f.name != "SHA256.txt":
            entries.append(f"{sha256(f).upper()}  {f.relative_to(pkg).as_posix()}")
    write_text(pkg / "SHA256.txt", "\n".join(entries) + "\n")

    zip_path = shutil.make_archive(str(DIST / name), "zip", root_dir=DIST, base_dir=name)

    print(f"패키지 : {pkg}")
    for f in sorted(pkg.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(pkg).as_posix():<38} {f.stat().st_size:>9,} bytes")
    print(f"ZIP    : {zip_path} ({Path(zip_path).stat().st_size:,} bytes)")
    print(f"역검증 : {reverse}")


if __name__ == "__main__":
    main()
