-- 브리핑 디코드 진입($E800)에서 BD/CE를 강제해 id 117 폭주를 재현/검증한다.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local forced = false
local shot_at = nil

emu.addMemoryCallback(function()
  if not forced then
    forced = true
    emu.write(0xBD, 0x1D, emu.memType.nesMemory)
    emu.write(0xCE, 0x01, emu.memType.nesMemory)
    say(string.format("f%05d id117 강제", frames))
    shot_at = frames + 120
  end
end, emu.callbackType.exec, 0xE801)

emu.addMemoryCallback(function()
  say(string.format("f%05d UPLOAD id=%d", frames, emu.read(0x19, emu.memType.nesMemory)))
end, emu.callbackType.exec, 0xB000)

emu.addEventCallback(function()
  frames = frames + 1
  if shot_at and (frames == shot_at or frames == shot_at + 240 or frames == shot_at + 600) then
    local s = io.open(OUT .. string.format("/shot_f%05d.png", frames), "wb")
    s:write(emu.takeScreenshot())
    s:close()
    say("shot f" .. frames)
  end
  if shot_at and frames >= shot_at + 700 then
    log:close()
    emu.stop(0)
  end
  if frames >= 9000 then
    log:close()
    emu.stop(1)
  end
end, emu.eventType.startFrame)

say("force_id117 시작")
