-- 스테이지 5 진입 후 오른쪽 이동 주입으로 서핑 구간까지 진행하며 주기 덤프.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local moving = false

emu.addMemoryCallback(function()
  if (frames >= 1550 and frames <= 1556) or (frames >= 1900 and frames <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  elseif moving then
    emu.write(0x15, 0x01, emu.memType.nesMemory)  -- Right 유지
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
  if frames <= 2400 then
    emu.write(0x0D, 5, emu.memType.nesMemory)
  end
  if frames == 3000 then moving = true end
  if frames >= 3600 and frames % 600 == 0 and frames <= 12000 then
    dump(string.format("f%05d", frames))
  end
  if frames >= 12200 then
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("surf 진행 시작")
