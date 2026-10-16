-- stage_13_end.mss -> 엔딩 전체 재생: 브리핑 id 로그 + 업로드 진입 로그 + 주기 덤프.
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
  say(string.format("f%05d briefing id=%d (BD=%02X CE=%02X)", frames, bd * 4 + (ce % 4), bd, ce))
end, emu.callbackType.exec, 0xE80D)

emu.addMemoryCallback(function()
  say(string.format("f%05d UPLOAD id=%d", frames, emu.read(0x19, emu.memType.nesMemory)))
end, emu.callbackType.exec, 0xB000)

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
end, emu.callbackType.exec, 0xAB9E)

local function shot(tag)
  local s = io.open(OUT .. "/shot_" .. tag .. ".png", "wb")
  s:write(emu.takeScreenshot())
  s:close()
end

emu.addEventCallback(function()
  frames = frames + 1
  if not load_at then return end
  local rel = frames - load_at
  if rel % 500 == 0 and rel <= 9000 then
    shot(string.format("r%04d", rel))
  end
  if rel >= 9200 then
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("diag_ending 시작")
