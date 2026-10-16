-- Battletoads 타이틀 화면의 실제 소비 자산을 덤프한다.
-- 기준 프레임은 기존 krdev8 QA에서 로고+메뉴가 안정적으로 표시된 8600프레임이다.

local OUT = "G:/Downloads/Korean Traslate Project/Games/Battletoads/work/qa/title_logo_probe"
local TARGET_FRAME = 8600
local STOP_FRAME = 8610
local frames = 0

local function dump_binary(path, start_addr, size, mem_type)
  local f = assert(io.open(path, "wb"))
  local chunk = {}
  for i = 0, size - 1 do
    chunk[#chunk + 1] = string.char(emu.read(start_addr + i, mem_type))
    if #chunk == 1024 then
      f:write(table.concat(chunk))
      chunk = {}
    end
  end
  if #chunk > 0 then f:write(table.concat(chunk)) end
  f:close()
end

emu.addEventCallback(function()
  frames = frames + 1
  if frames == TARGET_FRAME then
    dump_binary(OUT .. "/chr_ram_0000_1fff.bin", 0x0000, 0x2000, emu.memType.nesChrRam)
    dump_binary(OUT .. "/nametable_0000_03ff.bin", 0x0000, 0x0400, emu.memType.nesNametableRam)
    dump_binary(OUT .. "/palette_00_1f.bin", 0x0000, 0x0020, emu.memType.nesPaletteRam)
    local png = assert(emu.takeScreenshot())
    local f = assert(io.open(OUT .. "/title_f08600.png", "wb"))
    f:write(png)
    f:close()

    local s = emu.getState()
    local log = assert(io.open(OUT .. "/probe.txt", "w"))
    log:write(string.format("frame=%d\n", frames))
    log:write(string.format("backgroundPatternAddr=$%04X\n", s["ppu.control.backgroundPatternAddr"]))
    log:write(string.format("backgroundEnabled=%s\n", tostring(s["ppu.mask.backgroundEnabled"])))
    log:close()
  end
  if frames >= STOP_FRAME then emu.stop(0) end
end, emu.eventType.startFrame)

