"""Runtime-check every generated stage QA target and its clear transition in Mesen."""
from __future__ import annotations

import json
import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "build" / "Battletoads_KR_dev.nes"
MESEN = Path(r"H:\Mesen\Mesen.exe")
OUT = ROOT / "work" / "qa" / "stage_end" / "verification"

LUA = r'''local TARGET = @@TARGET@@
local OUT = "@@OUT@@"
local frame = 0
local done = false
local first_name_level = -1
local log = assert(io.open(OUT .. "/log.txt", "w"))

local function say(message)
  log:write(message .. "\n")
  log:flush()
end

local function capture(tag)
  local f = assert(io.open(OUT .. "/" .. tag .. ".png", "wb"))
  f:write(emu.takeScreenshot())
  f:close()
  say(string.format("%s frame=%d level=%d entity0=$%02X", tag, frame,
    emu.read(0x000D, emu.memType.nesMemory),
    emu.read(0x03C3, emu.memType.nesMemory)))
end

emu.addMemoryCallback(function()
  if (frame >= 1550 and frame <= 1556) or
     (frame >= 1900 and frame <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

emu.addMemoryCallback(function()
  local level = emu.read(0x000D, emu.memType.nesMemory)
  if first_name_level < 0 then first_name_level = level end
  say(string.format("level-name-call frame=%d level=%d", frame, level))
end, emu.callbackType.exec, 0xAB9E)

emu.addEventCallback(function()
  if done then return end
  frame = frame + 1
  if frame >= 1850 and frame <= 1910 then
    emu.write(0x000D, TARGET, emu.memType.nesMemory)
  end
  if frame == 2100 or frame == 2800 then
    capture(string.format("target_f%05d", frame))
  end
  if frame == 3000 then
    emu.write(0x03C3, 0x7F, emu.memType.nesMemory)
    capture("clear_f03000")
  end
  if frame == 3600 then
    capture(string.format("after_f%05d", frame))
  end
  if frame >= 3800 then
    local current = emu.read(0x000D, emu.memType.nesMemory)
    local pass = first_name_level == TARGET and current == TARGET + 1
    say(string.format("RESULT target=%d first_name_level=%d current=%d pass=%s",
      TARGET, first_name_level, current, tostring(pass)))
    done = true
    emu.stop(pass and 0 or 1)
  end
end, emu.eventType.startFrame)
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-stage", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.from_stage <= 14:
        raise SystemExit("--from-stage must be 1..14")
    OUT.mkdir(parents=True, exist_ok=True)
    for target in range(args.from_stage, 15):
        stage_out = OUT / f"stage_{target:02d}"
        if stage_out.exists():
            shutil.rmtree(stage_out)
        stage_out.mkdir()
        lua_path = stage_out / "verify.lua"
        lua_path.write_text(
            LUA.replace("@@TARGET@@", str(target)).replace(
                "@@OUT@@", stage_out.as_posix()
            ),
            encoding="utf-8",
        )
        staged_rom = stage_out / "rom.nes"
        shutil.copyfile(ROM, staged_rom)
        proc = subprocess.run(
            [str(MESEN), "--testRunner", str(lua_path), str(staged_rom)],
            cwd=MESEN.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )
        log_path = stage_out / "log.txt"
        if not log_path.is_file():
            raise SystemExit(f"stage {target:02d}: Mesen produced no log")
        log = log_path.read_text(encoding="utf-8")
        result_line = next(
            (line for line in log.splitlines() if line.startswith("RESULT ")), ""
        )
        passed = "pass=true" in result_line
        staged_rom.unlink(missing_ok=True)
        lua_path.unlink(missing_ok=True)
        print(f"stage {target:02d}: {'PASS' if passed else 'FAIL'} {result_line}")

    results = []
    for target in range(1, 15):
        log_path = OUT / f"stage_{target:02d}" / "log.txt"
        if not log_path.is_file():
            results.append({"stage": target, "passed": False, "result": "missing log"})
            continue
        result_line = next(
            (line for line in log_path.read_text(encoding="utf-8").splitlines()
             if line.startswith("RESULT ")),
            "",
        )
        results.append(
            {"stage": target, "passed": "pass=true" in result_line, "result": result_line}
        )

    summary = {"all_passed": all(r["passed"] for r in results), "results": results}
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
