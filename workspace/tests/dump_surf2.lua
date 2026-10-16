-- 실게임 확인(브리핑/레벨명 훅) + 스테이지5 우측 진행 + 주기 덤프.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local lv_seen = false
local moving = false

emu.addMemoryCallback(function()
  local bd = emu.read(0xBD, emu.memType.nesMemory)
  local ce = emu.read(0xCE, emu.memType.nesMemory)
  say(string.format("f%05d briefing id=%d", frames, bd * 4 + (ce % 4)))
end, emu.callbackType.exec, 0xE80D)

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
  lv_seen = true
end, emu.callbackType.exec, 0xAB9E)

emu.addMemoryCallback(function()
  if (frames >= 1550 and frames <= 1556) or (frames >= 1900 and frames <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  elseif moving then
    emu.write(0x15, 0x01, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

local function dump(tag)
  local f = io.open(OUT .. "/chr_" .. tag .. ".bin", "wb")
  local bytes = {}
  for a = 0, 0x1FFF do
    bytes[#bytes + 1] = string.char(emu.read(a, emu.memType.nesPpuMemory))
  end
  f:write(table.concat(bytes))
  f:close()
  local s = io.open(OUT .. "/shot_" .. tag .. ".png", "wb")
  s:write(emu.takeScreenshot())
  s:close()
  say(string.format("dump %s f%d lv=%d", tag, frames, emu.read(0x0D, emu.memType.nesMemory)))
end

emu.addEventCallback(function()
  frames = frames + 1
  if not lv_seen then
    emu.write(0x0D, 5, emu.memType.nesMemory)
  end
  if lv_seen and not moving and frames >= 2600 then moving = true end
  if moving and frames % 700 == 0 and frames <= 13000 then
    dump(string.format("f%05d", frames))
  end
  if frames >= 13200 then
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("surf2 시작")
