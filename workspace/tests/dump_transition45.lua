-- 스테이지 4 진입 -> 클리어 트리거($03C3=$7F) -> 스테이지 5 전환 후 CHR/NT 덤프.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local cleared = false
local dumped = false
local settle = nil

emu.addMemoryCallback(function()
  if (frames >= 1550 and frames <= 1556) or (frames >= 1900 and frames <= 1906) then
    emu.write(0x15, 0x10, emu.memType.nesMemory)
    emu.write(0x2B, 0x10, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

local function dump()
  local f = io.open(OUT .. "/chr.bin", "wb")
  local bytes = {}
  for a = 0, 0x1FFF do
    bytes[#bytes + 1] = string.char(emu.read(a, emu.memType.nesPpuMemory))
  end
  f:write(table.concat(bytes))
  f:close()
  local g = io.open(OUT .. "/nt.bin", "wb")
  local nb = {}
  for a = 0, 0x7FF do
    nb[#nb + 1] = string.char(emu.read(a, emu.memType.nesNametableRam))
  end
  g:write(table.concat(nb))
  g:close()
  local s = io.open(OUT .. "/shot.png", "wb")
  s:write(emu.takeScreenshot())
  s:close()
  say(string.format("dump f%d lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
end

emu.addEventCallback(function()
  frames = frames + 1
  if frames <= 2400 then
    emu.write(0x0D, 4, emu.memType.nesMemory)
  end
  if frames == 2800 and not cleared then
    emu.write(0x03C3, 0x7F, emu.memType.nesMemory)
    cleared = true
    say("clear trigger f" .. frames)
  end
  if cleared and not settle and emu.read(0x0D, emu.memType.nesMemory) == 5 then
    settle = frames + 1500  -- 브리핑·맵·스폰까지 진행
    say("lv5 도달 f" .. frames)
  end
  if settle and frames == settle and not dumped then
    dumped = true
    dump()
    log:close()
    emu.stop(0)
  end
  if frames >= 12000 then
    say("타임아웃 lv=" .. emu.read(0x0D, emu.memType.nesMemory))
    log:close()
    emu.stop(1)
  end
end, emu.eventType.startFrame)

say("transition 4->5 시작")
