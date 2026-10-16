-- 텍스트 호출 흐름 계측: 브리핑($E80D)·레벨명($AB9E) 디코드 시점 로그 + 자동 스크린샷.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/flow_log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local pending = {}

emu.addMemoryCallback(function()
  local bd = emu.read(0xBD, emu.memType.nesMemory)
  local ce = emu.read(0xCE, emu.memType.nesMemory)
  say(string.format("f%05d briefing-call BD=%02X CE=%02X id=%d", frames, bd, ce, bd * 4 + (ce % 4)))
end, emu.callbackType.exec, 0xE80D)

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME-call ($AB9E)", frames))
  pending[frames + 40] = string.format("lvname_f%05d", frames)
end, emu.callbackType.exec, 0xAB9E)

-- 조이패드 루틴 RTS($8D87) 직후 엣지 변수를 덮어써 스타트를 주입한다.
local pad_hits = 0
emu.addMemoryCallback(function()
  pad_hits = pad_hits + 1
  if (frames >= 1550 and frames <= 1556) or (frames >= 1900 and frames <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

emu.addEventCallback(function()
  frames = frames + 1
  if frames == 1600 or frames == 2100 or frames == 2600 then
    local png = emu.takeScreenshot()
    local f = io.open(OUT .. string.format("/auto_f%05d.png", frames), "wb")
    f:write(png)
    f:close()
    say(string.format("f%05d pad_hits=%d", frames, pad_hits))
  end
  local name = pending[frames]
  if name then
    local png = emu.takeScreenshot()
    local f = io.open(OUT .. "/" .. name .. ".png", "wb")
    f:write(png)
    f:close()
    say("shot " .. name)
    pending[frames] = nil
  end
  if frames >= 11000 then
    say("종료 " .. frames)
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("flow 디버그 시작")
