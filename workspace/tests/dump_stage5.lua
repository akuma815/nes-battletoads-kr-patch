-- 스테이지 5 진입 후 CHR(패턴 테이블)과 네임테이블을 덤프한다.
local OUT = "@@OUT@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0

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
  local st = emu.getState()
  say(string.format("dump f%d lv=%d bgPT=%04X", frames,
    emu.read(0x0D, emu.memType.nesMemory), st["ppu.control.backgroundPatternAddr"] or -1))
end

emu.addEventCallback(function()
  frames = frames + 1
  if frames <= 2400 then
    emu.write(0x0D, 5, emu.memType.nesMemory)
  end
  if frames == 3000 then
    dump()
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("stage5 dump 시작")
