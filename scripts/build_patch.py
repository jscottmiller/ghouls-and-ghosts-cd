#!/usr/bin/env python3
"""Build the patched ROM and the distributable BPS patch.

Generates all 68000 glue code (driver init, command send, per-cue stubs)
from the tables in patch_config.py, verifies every hook site against the
expected original bytes before touching it, and emits:

    build/<OUTPUT_BASENAME>.md   patched 1 MB ROM
    build/ghouls-cd.bps          BPS patch (original ROM -> patched ROM)

Run from the repo root: python3 scripts/build_patch.py
"""
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import patch_config as cfg
from bpstool import create_bps


# ---------------------------------------------------------------- assembler

class Asm:
    """Tiny two-pass 68000 emitter for the fixed instruction shapes we need."""

    def __init__(self, base):
        self.base = base
        self.buf = bytearray()
        self.labels = {}
        self.fixups = []   # (offset, kind, target_label)

    def here(self):
        return self.base + len(self.buf)

    def label(self, name):
        assert name not in self.labels, name
        self.labels[name] = self.here()

    def raw(self, data):
        self.buf += data

    def w(self, *words):
        for v in words:
            self.buf += v.to_bytes(2, "big")

    def l(self, value):
        self.buf += value.to_bytes(4, "big")

    # -- instructions ------------------------------------------------------
    def move_w_imm_d0(self, imm):       self.w(0x303C, imm & 0xFFFF)
    def andi_w_imm_d0(self, imm):       self.w(0x0240, imm & 0xFFFF)
    def addi_b_imm_d0(self, imm):       self.w(0x0600, imm & 0xFF)
    def addi_w_imm_d0(self, imm):       self.w(0x0640, imm & 0xFFFF)
    def cmpi_b_imm_d0(self, imm):       self.w(0x0C00, imm & 0xFF)
    def move_l_d0_sp(self):             self.w(0x2F00)   # move.l d0,-(a7)
    def move_l_sp_d0(self):             self.w(0x201F)   # move.l (a7)+,d0
    def move_l_d1_sp(self):             self.w(0x2F01)
    def move_l_sp_d1(self):             self.w(0x221F)
    def move_w_imm_d1(self, imm):       self.w(0x323C, imm & 0xFFFF)
    def nop(self):                      self.w(0x4E71)
    def rts(self):                      self.w(0x4E75)
    def jsr_w(self, addr):              self.w(0x4EB8, addr & 0xFFFF)
    def jmp_w(self, addr):              self.w(0x4EF8, addr & 0xFFFF)
    def jsr_l(self, addr):              self.w(0x4EB9); self.l(addr)
    def jmp_l(self, addr):              self.w(0x4EF9); self.l(addr)
    def tst_b_abs_l(self, addr):        self.w(0x4A39); self.l(addr)
    def addq_b_1_abs_l(self, addr):     self.w(0x5239); self.l(addr)
    def move_w_d0_abs_l(self, addr):    self.w(0x33C0); self.l(addr)
    def move_b_d0_abs_l(self, addr):    self.w(0x13C0); self.l(addr)
    def move_w_imm_abs_l(self, imm, addr):
        self.w(0x33FC, imm & 0xFFFF); self.l(addr)
    def move_w_imm_abs_w(self, imm, addr):
        self.w(0x31FC, imm & 0xFFFF, addr & 0xFFFF)
    def move_l_imm_abs_l(self, imm, addr):
        self.w(0x23FC); self.l(imm); self.l(addr)
    def move_b_abs_l_d0(self, addr):    self.w(0x1039); self.l(addr)
    def andi_b_imm_d0(self, imm):       self.w(0x0200, imm & 0xFF)

    # -- label-relative branches (fixed up in resolve()) --------------------
    def beq_s(self, target):
        self.fixups.append((len(self.buf), "b8", target)); self.w(0x6700)

    def bne_s(self, target):
        self.fixups.append((len(self.buf), "b8", target)); self.w(0x6600)

    def bra_s(self, target):
        self.fixups.append((len(self.buf), "b8", target)); self.w(0x6000)

    def dbra_d1(self, target):
        self.fixups.append((len(self.buf), "b16", target)); self.w(0x51C9, 0)

    def bsr_w(self, target):
        self.fixups.append((len(self.buf), "b16", target)); self.w(0x6100, 0)

    def resolve(self):
        for off, kind, target in self.fixups:
            dest = self.labels[target]
            pc = self.base + off + 2
            disp = dest - pc
            if kind == "b8":
                assert -128 <= disp <= 127 and disp != 0, (target, disp)
                self.buf[off + 1] = disp & 0xFF
            else:
                assert -32768 <= disp <= 32767, (target, disp)
                self.buf[off + 2:off + 4] = (disp & 0xFFFF).to_bytes(2, "big")


# ----------------------------------------------------------- code generation

def generate_code(asm):
    c = cfg

    # Vendored MSU-MD driver blob at CODE_BASE; call its base to init.
    asm.label("DRIVER")
    blob = Path("vendor/msu-md/msu-drv.bin").read_bytes()
    asm.raw(blob)
    if len(asm.buf) & 1:
        asm.raw(b"\x00")

    # SEND: issue the command word in d0 to the gate array.
    # Bounded wait so a missing Sega CD degrades to silent music, not a hang.
    # Returns d0 = $00FF (the Z80 driver's "silence music" command) so play
    # stubs can fall through into the game's own send routine to mute FM.
    asm.label("SEND")
    asm.move_l_d1_sp()
    asm.move_w_imm_d1(0x4000)
    asm.label("SEND_wait")
    asm.tst_b_abs_l(0xA12020)
    asm.beq_s("SEND_write")
    asm.dbra_d1("SEND_wait")
    asm.bra_s("SEND_exit")          # timed out: drop the command
    asm.label("SEND_write")
    asm.move_w_d0_abs_l(0xA12010)
    asm.addq_b_1_abs_l(0xA1201F)
    asm.label("SEND_exit")
    asm.move_l_sp_d1()
    asm.move_w_imm_d0(0x00FF)
    asm.rts()

    # CDSTOP_x: stop the CD, then forward the original sound ID in d0 to
    # the game's send routine (FM fallback for unmapped cues).
    for name, send in (("CDSTOP_1C04", c.SOUND_SEND_1C04),
                       ("CDSTOP_1C06", c.SOUND_SEND_1C06)):
        asm.label(name)
        asm.move_l_d0_sp()
        asm.move_w_imm_d0(c.CMD_STOP)
        asm.bsr_w("SEND")
        asm.move_l_sp_d0()
        asm.jmp_w(send)

    # FILTER: replaces `move.b d0,$A01C06` inside the $878 send routine.
    # Special-cases music ID $92 (level-variant cue) onto a CD track.
    track, loop = c.FILTER_92_TRACK
    asm.label("FILTER")
    asm.cmpi_b_imm_d0(0x92)
    asm.beq_s("FILTER_92")
    asm.move_b_d0_abs_l(0xA01C06)
    asm.rts()
    asm.label("FILTER_92")
    asm.move_w_imm_d0((c.CMD_PLAY_LOOP if loop else c.CMD_PLAY) | track)
    asm.bsr_w("SEND")
    asm.move_b_d0_abs_l(0xA01C06)   # d0 = $FF -> mute FM music
    asm.rts()

    # DISPATCH: replaces `andi.w #$ff,d0 + bsr.w $878` at the scripted
    # music site -- the six level themes.
    asm.label("DISPATCH")
    asm.andi_w_imm_d0(0x00FF)
    items = sorted(c.LEVEL_THEMES.items())
    for music_id, _ in items:
        asm.cmpi_b_imm_d0(music_id)
        asm.beq_s(f"LVL_{music_id:02X}")
    asm.jmp_w(c.SOUND_SEND_1C06)    # not a level theme: pass through
    for i, (music_id, (track, loop)) in enumerate(items):
        asm.label(f"LVL_{music_id:02X}")
        asm.move_w_imm_d0((c.CMD_PLAY_LOOP if loop else c.CMD_PLAY) | track)
        if i < len(items) - 1:
            asm.bra_s("DISPATCH_go")
    asm.label("DISPATCH_go")
    asm.bsr_w("SEND")
    asm.jmp_w(c.SOUND_SEND_1C06)    # d0 = $FF -> mute FM music

    # Per-site FM-fallback stubs (only the kinds that need displaced code).
    for addr, kind, op, send in c.FM_FALLBACK_SITES:
        helper = "CDSTOP_1C04" if send == c.SOUND_SEND_1C04 else "CDSTOP_1C06"
        if kind in ("imm", "imm_tail"):
            asm.label(f"STUB_{addr:06X}")
            asm.move_w_imm_d0(op)
            asm.jmp_l(asm.labels[helper])
        elif kind == "computed":
            asm.label(f"STUB_{addr:06X}")
            if op == "addi_b_0x84":
                asm.addi_b_imm_d0(0x84)
            elif op == "addi_w_0x81":
                asm.addi_w_imm_d0(0x81)
            else:
                raise ValueError(op)
            asm.jmp_l(asm.labels[helper])
        # 'jsr'/'jmp' kinds retarget in place; no stub needed.

    # PAUSE/RESUME: command written immediately (no wait, no registers
    # clobbered beyond the displaced instruction's effect), matching the
    # play-tested behavior of ArcadeTV's patch.
    asm.label("PAUSE")
    asm.move_w_imm_abs_w(0x0001, 0xF63A)        # displaced original
    asm.move_w_imm_abs_l(c.CMD_PAUSE_FADE, 0xA12010)
    asm.addq_b_1_abs_l(0xA1201F)
    asm.rts()

    asm.label("RESUME")
    asm.move_w_imm_abs_w(0x0000, 0xF63A)        # displaced original
    asm.move_w_imm_abs_l(c.CMD_RESUME, 0xA12010)
    asm.addq_b_1_abs_l(0xA1201F)
    asm.rts()

    # TITLE: runs in the title/sound-init path. Stops any CD playback
    # (e.g. returning to title with a level theme looping), then performs
    # the displaced original work.
    asm.label("TITLE")
    asm.move_w_imm_abs_l(c.CMD_STOP, 0xA12010)
    asm.addq_b_1_abs_l(0xA1201F)
    asm.jsr_w(c.SOUND_INIT_CE6)                 # displaced original bsr
    asm.move_w_imm_abs_l(0x0100, 0xA11100)      # displaced original busreq
    asm.rts()

    # ENTRY: new reset target. TMSS unlock, driver init, volume, then the
    # original entry point.
    asm.label("ENTRY")
    asm.move_b_abs_l_d0(0xA10001)
    asm.andi_b_imm_d0(0x0F)
    asm.beq_s("ENTRY_notmss")
    asm.move_l_imm_abs_l(0x53454741, 0xA14000)  # 'SEGA'
    asm.label("ENTRY_notmss")
    asm.jsr_l(asm.labels["DRIVER"])
    asm.move_w_imm_d0(cfg.CMD_VOLUME_MAX)
    asm.bsr_w("SEND")
    asm.jmp_w(c.ORIGINAL_ENTRY)

    asm.resolve()


# ------------------------------------------------------------- site patching

def be32(v):
    return v.to_bytes(4, "big")


def jsr_l_bytes(addr):
    return b"\x4e\xb9" + be32(addr)


def jmp_l_bytes(addr):
    return b"\x4e\xf9" + be32(addr)


NOP = b"\x4e\x71"


def patch_sites(rom, labels):
    c = cfg
    edits = []  # (addr, expected original bytes, new bytes, description)

    def site(addr, expect, new, desc):
        edits.append((addr, bytes.fromhex(expect.replace(" ", "")), new, desc))

    # Boot plumbing.
    site(0x000004, "00 00 02 08", be32(labels["ENTRY"]), "reset vector")
    site(0x000100, "53454741204d45474120445249564520",
         b"SEGA MEGASD     ", "header system name")
    site(0x0001A4, "00 09 ff ff", bytes.fromhex("000fffff"), "header ROM end")
    site(0x000252, "66 00 00 94", NOP + NOP, "skip checksum failure branch")

    # Core sound hooks.
    site(c.FILTER_SITE, "13 c0 00 a0 1c 06",
         jsr_l_bytes(labels["FILTER"]), "$878 mailbox write -> FILTER")
    site(c.PAUSE_SITE, "31 fc 00 01 f6 3a",
         jsr_l_bytes(labels["PAUSE"]), "pause handler -> PAUSE")
    site(c.RESUME_SITE, "31 fc 00 00 f6 3a",
         jsr_l_bytes(labels["RESUME"]), "resume handler -> RESUME")
    site(c.TITLE_SITE, "61 00 ef 2e 33 fc 01 00 00 a1 11 00",
         jsr_l_bytes(labels["TITLE"]) + NOP * 3, "title/init path -> TITLE")
    site(c.SCRIPTED_DISPATCH_SITE, "02 40 00 ff 61 00 ce a4",
         jsr_l_bytes(labels["DISPATCH"]) + NOP, "level themes -> DISPATCH")

    # FM-fallback sites.
    for addr, kind, op, send in c.FM_FALLBACK_SITES:
        stub = labels.get(f"STUB_{addr:06X}")
        helper = labels["CDSTOP_1C04" if send == c.SOUND_SEND_1C04
                        else "CDSTOP_1C06"]
        orig_imm = {
            c.SOUND_SEND_1C04: 0x856, c.SOUND_SEND_1C06: 0x878}[send]
        if kind in ("imm", "computed"):
            # original: 4 bytes of ID load/arith + 4-byte bsr.w
            old = bytes(rom[addr:addr + 4])
            bsr = bytes(rom[addr + 4:addr + 8])
            assert bsr[:2] == b"\x61\x00", f"{addr:06X}: expected bsr.w"
            disp = int.from_bytes(bsr[2:4], "big", signed=True)
            assert addr + 6 + disp == orig_imm, f"{addr:06X}: bsr target"
            edits.append((addr, old + bsr, jsr_l_bytes(stub) + NOP,
                          f"FM fallback (ID via stub) at {addr:06X}"))
        elif kind == "imm_tail":
            old = bytes(rom[addr:addr + 4])
            bra = bytes(rom[addr + 4:addr + 8])
            assert bra[:2] == b"\x60\x00", f"{addr:06X}: expected bra.w"
            disp = int.from_bytes(bra[2:4], "big", signed=True)
            assert addr + 6 + disp == orig_imm, f"{addr:06X}: bra target"
            edits.append((addr, old + bra, jmp_l_bytes(stub) + NOP,
                          f"FM fallback (tail) at {addr:06X}"))
        elif kind in ("jsr", "jmp"):
            opbytes = b"\x4e\xb9" if kind == "jsr" else b"\x4e\xf9"
            jaddr = addr + 4   # after the move.w #ID,d0
            old = bytes(rom[jaddr:jaddr + 6])
            assert old == opbytes + be32(orig_imm), f"{jaddr:06X}: {old.hex()}"
            edits.append((jaddr, old, opbytes + be32(helper),
                          f"FM fallback (retarget) at {addr:06X}"))

    for addr, expect, new, desc in edits:
        actual = bytes(rom[addr:addr + len(expect)])
        if actual != expect:
            raise AssertionError(
                f"{desc}: original bytes mismatch at {addr:06X}: "
                f"expected {expect.hex()} got {actual.hex()}")
        assert len(new) == len(expect), desc
        rom[addr:addr + len(new)] = new
    return len(edits)


# ----------------------------------------------------------------------- main

def main():
    src = Path(cfg.ROM_FILE).read_bytes()
    if zlib.crc32(src) != cfg.ROM_CRC32:
        print(f"ROM CRC mismatch: expected {cfg.ROM_CRC32:08X}, "
              f"got {zlib.crc32(src):08X}", file=sys.stderr)
        return 1

    asm = Asm(cfg.CODE_BASE)
    generate_code(asm)
    assert cfg.CODE_BASE + len(asm.buf) <= cfg.PADDED_SIZE

    rom = bytearray(src)
    rom += asm.buf
    rom += b"\x00" * (cfg.PADDED_SIZE - len(rom))
    n = patch_sites(rom, asm.labels)

    out = Path("build")
    out.mkdir(exist_ok=True)
    rom_path = out / f"{cfg.OUTPUT_BASENAME}.md"
    rom_path.write_bytes(rom)
    bps = create_bps(src, bytes(rom))
    (out / "ghouls-cd.bps").write_bytes(bps)

    print(f"generated {len(asm.buf)} bytes of code at "
          f"{cfg.CODE_BASE:06X}, patched {n} sites")
    for name in ("DRIVER", "SEND", "CDSTOP_1C04", "CDSTOP_1C06", "FILTER",
                 "DISPATCH", "PAUSE", "RESUME", "TITLE", "ENTRY"):
        print(f"  {name:<12} {asm.labels[name]:06X}")
    print(f"wrote {rom_path} (crc32 {zlib.crc32(rom):08X})")
    print(f"wrote build/ghouls-cd.bps ({len(bps)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
