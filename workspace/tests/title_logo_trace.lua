-- 타이틀 로고 CHR-RAM 쓰기의 CPU 소비 경로와 ROM 매핑을 추적한다.

local OUT = "G:/Downloads/Korean Traslate Project/Games/Battletoads/work/qa/title_logo_probe/trace.txt"
local START_FRAME = 7000
local STOP_FRAME = 8610
local frames = 0
local pcs = {}
local first_write = nil
local last_write = nil
local total = 0

emu.addMemoryCallback(function(addr, value)
  if frames < START_FRAME or frames > STOP_FRAME then return end
  local s = emu.getState()
  local pc = s["cpu.pc"]
  local mapped = emu.convertAddress(pc, emu.memType.nesMemory)
  local rom_addr = -1
  local rom_type = -1
  if mapped then
    rom_addr = mapped.address
    rom_type = mapped.memType
  end
  local ppu_addr = s["ppu.memoryAddress"] or -1
  local key = string.format("%04X/%06X/%d/%04X", pc, rom_addr, rom_type, ppu_addr)
  local rec = pcs[key]
  if not rec then
    rec = {pc=pc, rom=rom_addr, mem=rom_type, count=0, first=frames, last=frames,
           min_addr=ppu_addr, max_addr=ppu_addr}
    pcs[key] = rec
  end
  rec.count = rec.count + 1
  rec.last = frames
  if ppu_addr < rec.min_addr then rec.min_addr = ppu_addr end
  if ppu_addr > rec.max_addr then rec.max_addr = ppu_addr end
  total = total + 1
  if not first_write then first_write = {frame=frames, addr=ppu_addr, value=value, pc=pc, rom=rom_addr} end
  last_write = {frame=frames, addr=ppu_addr, value=value, pc=pc, rom=rom_addr}
end, emu.callbackType.write, 0x2007, 0x2007, emu.cpuType.nes, emu.memType.nesMemory)

local function emit()
  local f = assert(io.open(OUT, "w"))
  f:write(string.format("total=%d\n", total))
  if first_write then
    f:write(string.format("first frame=%d chr=$%04X value=$%02X pc=$%04X rom=$%06X\n",
      first_write.frame, first_write.addr, first_write.value, first_write.pc, first_write.rom))
    f:write(string.format("last  frame=%d chr=$%04X value=$%02X pc=$%04X rom=$%06X\n",
      last_write.frame, last_write.addr, last_write.value, last_write.pc, last_write.rom))
  end
  local rows = {}
  for _, rec in pairs(pcs) do rows[#rows + 1] = rec end
  table.sort(rows, function(a, b) return a.count > b.count end)
  for _, rec in ipairs(rows) do
    f:write(string.format("pc=$%04X rom=$%06X mem=%d count=%d frames=%d..%d chr=$%04X..$%04X\n",
      rec.pc, rec.rom, rec.mem, rec.count, rec.first, rec.last, rec.min_addr, rec.max_addr))
  end
  f:close()
end

emu.addEventCallback(function()
  frames = frames + 1
  if frames >= STOP_FRAME then
    emit()
    emu.stop(0)
  end
end, emu.eventType.startFrame)
