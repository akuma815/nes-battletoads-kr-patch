-- BizHawk 교차 QA: 오버사이즈 512K 로드 + 시작 흐름 + 한글 표시 스크린샷.
-- EmuHawk.exe --lua=이파일 rom.nes
local OUT = "@@OUT@@"

pcall(function() client.speedmode(1600) end)

local SHOT_AT = {[900]=true, [1600]=true, [1750]=true, [2000]=true, [2200]=true,
                 [2500]=true, [2800]=true, [3200]=true, [3600]=true, [4200]=true}

while true do
  local f = emu.framecount()
  if (f >= 1540 and f <= 1560) or (f >= 1890 and f <= 1910) then
    joypad.set({Start = true}, 1)
  end
  if SHOT_AT[f] then
    client.screenshot(OUT .. "/bh_f" .. string.format("%05d", f) .. ".png")
  end
  if f >= 4600 then
    client.screenshot(OUT .. "/bh_final.png")
    client.exit()
  end
  emu.frameadvance()
end
