-- 세이브1 로드 직후/타이핑 중 네임테이블 덤프로 아티팩트 기원 판별.
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

local function dump(tag)
  local nb = {}
  for a = 0, 0x7FF do
    nb[#nb + 1] = string.char(emu.read(a, emu.memType.nesNametableRam))
  end
  local g = io.open(OUT .. "/nt_" .. tag .. ".bin", "wb")
  g:write(table.concat(nb))
  g:close()
  local s = io.open(OUT .. "/shot_" .. tag .. ".png", "wb")
  s:write(emu.takeScreenshot())
  s:close()
  say("dump " .. tag .. " f" .. frames)
end

emu.addEventCallback(function()
  frames = frames + 1
  if not load_at then return end
  local rel = frames - load_at
  if rel == 3 then dump("load") end
  if rel == 260 then dump("typing") end
  if rel == 700 then dump("mid") end
  if rel == 1100 then
    dump("late")
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("diag_state1_nt 시작")
