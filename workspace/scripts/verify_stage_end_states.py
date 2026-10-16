"""Load all stage-ending Mesen states and verify their next-state transition."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "build" / "Battletoads_KR_dev.nes"
MESEN = Path(r"H:\Mesen\Mesen.exe")
STATES = ROOT / "work" / "qa" / "stage_end" / "states"
OUT = ROOT / "work" / "qa" / "stage_end" / "state_verification"

LUA = r'''local TARGET = @@TARGET@@
local STATE = "@@STATE@@"
local OUT = "@@OUT@@"
local loaded = false
local frames = 0
local done = false

emu.addMemoryCallback(function()
  if done or loaded then return end
  local f = assert(io.open(STATE, "rb"))
  local data = f:read("*a")
  f:close()
  loaded = true
  emu.loadSavestate(data)
end, emu.callbackType.exec, 0x8D87)

emu.addEventCallback(function()
  if done or not loaded then return end
  frames = frames + 1
  if frames == 600 then
    local current = emu.read(0x000D, emu.memType.nesMemory)
    local pass = current == TARGET + 1
    local shot = assert(io.open(OUT .. "/after.png", "wb"))
    shot:write(emu.takeScreenshot())
    shot:close()
    local log = assert(io.open(OUT .. "/result.txt", "w"))
    log:write(string.format("target=%d current=%d pass=%s\n",
      TARGET, current, tostring(pass)))
    log:close()
    done = true
    emu.stop(pass and 0 or 1)
  end
end, emu.eventType.startFrame)
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="battletoads_state_verify_") as temp:
        temp_path = Path(temp)
        staged_rom = temp_path / "rom.nes"
        shutil.copyfile(ROM, staged_rom)
        for target in range(1, 15):
            stage_out = OUT / f"stage_{target:02d}"
            stage_out.mkdir(exist_ok=True)
            state = STATES / f"stage_{target:02d}_end.mss"
            script = temp_path / f"verify_{target:02d}.lua"
            script.write_text(
                LUA.replace("@@TARGET@@", str(target))
                .replace("@@STATE@@", state.as_posix())
                .replace("@@OUT@@", stage_out.as_posix()),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [str(MESEN), "--testRunner", str(script), str(staged_rom)],
                cwd=MESEN.parent,
                capture_output=True,
                text=True,
                timeout=20,
            )
            result = (stage_out / "result.txt").read_text(encoding="utf-8").strip()
            passed = proc.returncode == 0 and "pass=true" in result
            results.append({"stage": target, "passed": passed, "result": result})
            print(f"stage {target:02d}: {'PASS' if passed else 'FAIL'} {result}")

    summary = {"all_passed": all(r["passed"] for r in results), "results": results}
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
