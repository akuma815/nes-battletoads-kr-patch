-- stage_04_end.mss 로드 -> 전환 -> 스테이지 5 플레이(우측 진행) -> 주기 덤프.
local OUT = "@@OUT@@"
local STATE = "@@STATE@@"
local log = io.open(OUT .. "/log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local loaded = false
local lv5_at = nil

emu.addMemoryCallback(function()
  if not loaded then
    local f = assert(io.open(STATE, "rb"))
    local data = f:read("*a")
    f:close()
    loaded = true
    emu.loadSavestate(data)
    say("state loaded f" .. frames)
    return
  end
  -- 레벨 5 도착 후 우측 진행(유지+엣지 동시 주입)
  if lv5_at and frames >= lv5_at + 400 then
    emu.write(0x15, 0x01, emu.memType.nesMemory)
    emu.write(0x29, 0x00, emu.memType.nesMemory)
    emu.write(0x2B, 0x01, emu.memType.nesMemory)
  end
end, emu.callbackType.exec, 0x8D87)

emu.addMemoryCallback(function()
  say(string.format("f%05d LEVELNAME lv=%d", frames, emu.read(0x0D, emu.memType.nesMemory)))
end, emu.callbackType.exec, 0xAB9E)

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
  if loaded and not lv5_at and emu.read(0x0D, emu.memType.nesMemory) == 5 then
    lv5_at = frames
    say("lv5 도달 f" .. frames)
  end
  if lv5_at and frames == lv5_at + 500 then
    say(string.format("f%05d in15=%02X in2B=%02X", frames,
      emu.read(0x15, emu.memType.nesMemory), emu.read(0x2B, emu.memType.nesMemory)))
  end
  if lv5_at and (frames - lv5_at) % 700 == 0 and frames > lv5_at then
    dump(string.format("f%05d", frames))
  end
  if lv5_at and frames >= lv5_at + 11000 then
    log:close()
    emu.stop(0)
  end
  if frames >= 20000 then
    say("타임아웃")
    log:close()
    emu.stop(1)
  end
end, emu.eventType.startFrame)

say("state->surf 시작")
