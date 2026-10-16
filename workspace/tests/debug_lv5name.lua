-- 레벨 5 이름 화면 캡처: $000D=5 강제 + 스타트 주입 + $AB9E 훅.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local shot_at = nil

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME-call lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
  if not shot_at then shot_at = frames + 45 end
end, emu.callbackType.exec, 0xAB9E)

emu.addMemoryCallback(function()
  if (frames >= 1550 and frames <= 1556) or (frames >= 1900 and frames <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

emu.addEventCallback(function()
  frames = frames + 1
  emu.write(0x0D, 5, emu.memType.nesMemory)
  if shot_at and frames == shot_at then
    local f = io.open(OUT .. "/lv5name.png", "wb")
    f:write(emu.takeScreenshot())
    f:close()
    say("shot lv5name f" .. frames)
  end
  if frames >= 3200 then
    say("종료")
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("lv5 캡처 시작")
