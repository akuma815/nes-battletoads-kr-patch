"""Generate Mesen savestates immediately after each stage-clear trigger."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "build" / "Battletoads_KR_dev.nes"
MESEN = Path(r"H:\Mesen\Mesen.exe")
OUT = ROOT / "work" / "qa" / "stage_end" / "states"
ROM_SHA256 = "300D7A335E404FCBA4522D21AB58AF1DC77140DD7C4A6DE4EA7331E50B6E5090"

LUA = r'''local TARGET = @@TARGET@@
local STATE = "@@STATE@@"
local frame = 0
local save_pending = false
local done = false

emu.addMemoryCallback(function()
  if done then return end
  if save_pending then
    local data = emu.createSavestate()
    local f = assert(io.open(STATE, "wb"))
    f:write(data)
    f:close()
    done = true
    emu.stop(0)
    return
  end
  if (frame >= 1550 and frame <= 1556) or
     (frame >= 1900 and frame <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

emu.addEventCallback(function()
  if done then return end
  frame = frame + 1
  if frame >= 1850 and frame <= 1910 then
    emu.write(0x000D, TARGET, emu.memType.nesMemory)
  end
  if frame == 3000 then
    emu.write(0x03C3, 0x7F, emu.memType.nesMemory)
    save_pending = true
  end
end, emu.eventType.startFrame)
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    if sha256(ROM) != ROM_SHA256:
        raise SystemExit("최종 한글 ROM SHA-256 불일치")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory(prefix="battletoads_stage_states_") as temp:
        temp_path = Path(temp)
        staged_rom = temp_path / "rom.nes"
        shutil.copyfile(ROM, staged_rom)
        for target in range(1, 15):
            state = OUT / f"stage_{target:02d}_end.mss"
            script = temp_path / f"stage_{target:02d}.lua"
            script.write_text(
                LUA.replace("@@TARGET@@", str(target)).replace(
                    "@@STATE@@", state.as_posix()
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [str(MESEN), "--testRunner", str(script), str(staged_rom)],
                cwd=MESEN.parent,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0 or not state.is_file():
                raise SystemExit(f"stage {target:02d} state generation failed")
            manifest.append(
                {
                    "stage": target,
                    "file": state.name,
                    "size": state.stat().st_size,
                    "sha256": sha256(state),
                }
            )
            print(f"stage {target:02d}: {state.stat().st_size} bytes")

    (OUT / "SHA256.json").write_text(
        json.dumps(
            {"rom_sha256": ROM_SHA256, "mesen": str(MESEN), "states": manifest},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()



