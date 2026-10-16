-- 사용자 세이브(슬롯2) 로드 -> 엔딩 깨짐 진단 덤프.
local OUT = "@@OUT@@"
local STATE = "@@STATE@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local loaded = false
local load_at = nil

emu.addMemoryCallback(function()
  if loaded then return end
  local f = assert(io.open(STATE, "rb"))
  local data = f:read("*a")
  f:close()
  loaded = true
  emu.loadSavestate(data)
  load_at = frames
  say("state loaded f" .. frames)
end, emu.callbackType.exec, 0x8D87)

emu.addMemoryCallback(function()
  local bd = emu.read(0xBD, emu.memType.nesMemory)
  local ce = emu.read(0xCE, emu.memType.nesMemory)
  say(string.format("f%05d briefing id=%d", frames, bd * 4 + (ce % 4)))
end, emu.callbackType.exec, 0xE80D)

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
end, emu.callbackType.exec, 0xAB9E)

local function dump(tag)
  local bytes = {}
  for a = 0, 0x1FFF do
    bytes[#bytes + 1] = string.char(emu.read(a, emu.memType.nesPpuMemory))
  end
  local f = io.open(OUT .. "/chr_" .. tag .. ".bin", "wb")
  f:write(table.concat(bytes))
  f:close()
  local nb = {}
  for a = 0, 0x7FF do
    nb[#nb + 1] = string.char(emu.read(a, emu.memType.nesNametableRam))
  end
  local g = io.open(OUT .. "/nt_" .. tag .. ".bin", "wb")
  g:write(table.concat(nb))
  g:close()
  local rb = {}
  for a = 0, 0xFF do
    rb[#rb + 1] = string.format("%02X", emu.read(0x0700 + a, emu.memType.nesMemory))
  end
  local h = io.open(OUT .. "/buf_" .. tag .. ".txt", "w")
  h:write(table.concat(rb, " "))
  h:close()
  local s = io.open(OUT .. "/shot_" .. tag .. ".png", "wb")
  s:write(emu.takeScreenshot())
  s:close()
  local st = emu.getState()
  say(string.format("dump %s f%d lv=%d BD=%02X CE=%02X bgPT=%04X bgOn=%s", tag, frames,
    emu.read(0x0D, emu.memType.nesMemory), emu.read(0xBD, emu.memType.nesMemory),
    emu.read(0xCE, emu.memType.nesMemory),
    st["ppu.control.backgroundPatternAddr"] or -1,
    tostring(st["ppu.mask.backgroundEnabled"])))
end

emu.addEventCallback(function()
  frames = frames + 1
  if not load_at then return end
  local rel = frames - load_at
  if rel == 30 or rel == 300 or rel == 900 or rel == 1800 or rel == 3000 or rel == 4500 then
    dump(string.format("r%04d", rel))
  end
  if rel >= 6000 then
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("diag_state2 시작")
