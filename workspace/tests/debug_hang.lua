-- KR dev 빌드 행 진단: 패치·업로드 경로 실행 추적.
-- Mesen.exe --testRunner debug_hang.lua rom.nes

local OUT = "@@OUT@@"
local log = io.open(OUT .. "/debug_log.txt", "w")
local function say(s) log:write(s .. "\n"); log:flush() end

local frames = 0
local hits = {}
local done = false

local function trace(tag)
  return function(addr, value)
    if done then return end
    hits[tag] = (hits[tag] or 0) + 1
    if hits[tag] <= 12 then
      local s = emu.getState()
      say(string.format("f%05d %s pc=%04X 19=%02X 2D=%02X 2E=%02X", frames, tag,
        addr, emu.read(0x19, emu.memType.nesMemory),
        emu.read(0x2D, emu.memType.nesMemory), emu.read(0x2E, emu.memType.nesMemory)))
    end
  end
end

emu.addMemoryCallback(trace("patch-in  $E89F"), emu.callbackType.exec, 0xE89F)
emu.addMemoryCallback(trace("jsr-site  $E8A7"), emu.callbackType.exec, 0xE8A7)
emu.addMemoryCallback(trace("upload    $B000"), emu.callbackType.exec, 0xB000)
emu.addMemoryCallback(trace("upl-loop  $B022"), emu.callbackType.exec, 0xB022)
emu.addMemoryCallback(trace("upl-rts   $B05E"), emu.callbackType.exec, 0xB05E)
emu.addMemoryCallback(trace("back      $E8B0"), emu.callbackType.exec, 0xE8B0)
emu.addMemoryCallback(trace("old-rts   $E8EE"), emu.callbackType.exec, 0xE8EE)
emu.addMemoryCallback(trace("nmi-stub  $FF8C"), emu.callbackType.exec, 0xFF8C)

emu.addEventCallback(function()
  local buttons = {}
  if frames >= 1550 and frames <= 1558 then buttons["start"] = true end
  emu.setInput(0, buttons)
end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  frames = frames + 1
  if frames == 4300 then
    done = true
    say("--- f4300 상태 ---")
    local st = emu.getState()
    say(string.format("pc=%04X", st["cpu.pc"] or -1))
    for k, v in pairs(st) do
      if string.find(k, "prg") or string.find(k, "Prg") then
        say(k .. " = " .. tostring(v))
      end
    end
    local buf = {}
    for i = 0, 31 do buf[#buf + 1] = string.format("%02X", emu.read(0x0700 + i, emu.memType.nesMemory)) end
    say("0700: " .. table.concat(buf, " "))
    local counts = {}
    for k, v in pairs(hits) do counts[#counts + 1] = k .. "=" .. v end
    say("hits: " .. table.concat(counts, " "))
    log:close()
    emu.stop(0)
  end
end, emu.eventType.startFrame)

say("디버그 시작")
