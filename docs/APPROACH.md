# Technical Approach

## Goal

Ghouls'n Ghosts (Genesis) playing with redbook CD audio via Sega CD, with the
game itself otherwise untouched. Sound effects remain on the YM2612/PSG;
music comes off the disc.

## What we know about the ROM so far

From initial recon of `Ghouls'n Ghosts (World) (Rev A)` (640 KB, header
`GM 00004013-02`):

- The 68000 never writes the YM2612 directly (zero references to `$A04000`);
  the sound driver runs entirely on the **Z80**.
- The 68k-side sound interface is a small cluster of routines at ROM
  **`$000840`–`$000980`**, each wrapped in Z80 bus request/release
  (`$A11100`):
  - `move.b d0,($A01C04).l` — send a sound ID to the Z80 driver
  - `move.b d0,($A01C06).l` — second command channel
  - `move.b #$80,($A01C08).l` / `($A01C09).l` — flag-style commands
    (likely pause/stop/fade — to be confirmed in a debugger)
- The Z80 driver is uploaded once at boot (`lea $A00000` at `$00081C`,
  init code near `$000800`).

This is the ideal shape for the hack: a handful of centralized "send sound
command" routines to trampoline. Classify the ID as music vs. SFX, route
music IDs to the Sega CD, and let SFX pass through to the Z80 driver
unchanged. Music IDs also get suppressed on the Z80 side (or replaced with a
silent song) so FM music never starts.

## Phase 1 — Mode 1 ("MSU-MD" style): cartridge + Sega CD

When a Genesis boots with both a cartridge and a Sega CD attached, the
cartridge runs and the Sega CD hardware is fully available as a peripheral
("Mode 1"). The cart-side code loads a small driver into the sub-CPU's
program RAM; after that, playing CD audio is a matter of writing simple
commands (play track N, loop, stop, pause, volume) to the gate-array
communication registers.

Work items:

1. **Disassemble around the sound mailbox.** Find the 68k routine(s) that
   write `$A00009`, and enumerate the music vs. SFX ID space (play the game,
   log writes in an emulator with a debugger).
2. **Integrate a Mode 1 CD driver.** Use or adapt the open-source MSU-MD
   driver (sub-CPU binary + cart-side init/command code).
3. **Hook the mailbox routine.** Trampoline from the original routine into
   our code (placed in the unused space at the top of the 1 MB cart address
   range — the ROM is 640 KB, so `$0A0000+` is free). Map music IDs → CD
   track numbers, issue play/loop commands, swallow the FM music trigger.
   Pause/unpause and "stop music" events need the same treatment.
4. **Build pipeline.** `ffmpeg` decodes FLAC → 44.1 kHz/16-bit/stereo PCM
   (the rips are already in that format, so this is lossless), scripts emit a
   CUE/BIN with a data track + audio tracks, and the ROM patch is produced as
   a BPS so the repo never contains Capcom/Sega bytes.
5. **Test.** Genesis Plus GX (and other emulators with Mode 1 + CD support),
   then real hardware (flashcart + Sega CD).

Deliverable: `ghouls-cd.bps` (apply to your own ROM) + `ghouls-cd.cue/bin`
(built from your own FLACs).

Risk: **low**. This is a well-trodden technique with existing open-source
drivers, and the game's sound architecture (Z80 driver + single mailbox)
makes the hook clean. Fit-and-finish issues to expect: loop behavior
(redbook loops restart the track — we may master intro+loop into the track
audio), music that must resume mid-track after pause, and tracks the game
tempo-syncs to gameplay (none expected in this title).

## Phase 2 — Boot-from-CD (a true Sega CD release)

A disc that boots on a stock Sega CD with no cartridge. This is much harder
because of the Sega CD memory map:

- The main 68k sees only **256 KB of Word RAM** (`$200000`) plus a **128 KB
  banked window** into the sub-CPU's 512 KB program RAM (`$020000`).
- The game is **640 KB linked at `$000000`** with absolute addressing
  throughout. It cannot simply be copied somewhere and run.

Known strategies from the fan-conversion scene (to be researched in depth):

- Relocate/patch the code to run from Word RAM, with the sub-CPU serving
  asset reads (graphics/level data are the bulk of the 640 KB; resident code
  may fit in 256 KB).
- Use the banked program-RAM window for paged data access, patching every
  cross-bank reference.

Either way it's per-game reverse-engineering work, an order of magnitude
beyond Phase 1. Everything from Phase 1 carries forward (music hooks, track
map, CD mastering), so Phase 1 is the right first milestone regardless.

Risk: **high / research needed**, tracked separately.

## Prior art & references

- **MSU-MD driver** (krikzz): <https://github.com/krikzz/msu-md> — **MIT
  licensed**, so we can vendor it. Mode 1 driver blob is linked into the cart
  ROM and `jsr`'d at init (returns 0 on success, 1 if no Mega CD). Command
  interface via the Mode 1 gate-array comm registers:
  - `$A12010` command / `$A12011` argument
  - `$A1201F` command clock (increment to latch)
  - `$A12020` status (0 = ready, 1 = init, 2 = busy — spin until 0)
  - Commands: `$11` play once (arg = track 1–99), `$12` play looped,
    `$13` pause (arg = fade in 1/75 s), `$14` resume, `$15` volume (0–255),
    `$16` seek-emulation toggle, `$1A` play with sector offset.
- **An MSU-MD patch for Ghouls'n Ghosts already exists** (by ArcadeTV,
  targeting the JUE REV 02 ROM), with MD+ conversion by PepilloPEV and
  Arcade/X68000 soundpacks by Relikk:
  <https://www.zeldix.net/t2212-ghouls-n-ghosts-md-msu-md>. ArcadeTV's GitHub
  source is offline; the BPS survives via Zeldix / the archive.org MD+
  collection. Diffing that BPS against the stock ROM is a fast way to recover
  proven hook points. Our local ROM: `(World) (Rev A)`, CRC32 `4F2561D5`,
  header serial `GM 00004013-02` — verify the existing patch's target CRC
  before assuming compatibility.
- **No boot-from-CD conversion of GnG exists** — Phase 2 would be novel work.
  Best templates: Amy Farbright's Sonic 1 Mega CD port
  (<https://foreverwip.github.io/projects/s1mcd.html>,
  <https://github.com/foreverWIP/s1disasm/tree/MMD>) which streams the game
  as MMD overlay modules into Word RAM; the megadev framework
  (<https://github.com/drojaazu/megadev>); retrodev's Sega CD docs and
  BuildSCD (<https://www.retrodev.com/segacd.html>).
- **Sound driver**: classified by the community as "pre-SMPS Z80, Type 2,
  Capcom mod" (<https://github.com/sonicretro/smps-rips>,
  <https://www.vgmpf.com/Wiki/index.php?title=Mega_Drive%2FGenesis_Sound_Driver_List>).
  ValleyBell's SMPS Research Pack / SMPSPlay
  (<https://github.com/ValleyBell/SMPSPlay>) document the command set. No
  full disassembly of the game exists; hansbonini's sega2asm has a
  Daimakaimura config (<https://github.com/hansbonini/sega2asm>).
- **Emulators for testing**: Genesis Plus GX (libretro) is the reference for
  MSU-MD and MD+ (needs Sega CD BIOSes; ROM + CUE + audio in one dir). Kega
  Fusion works with `CartBootEnabled=1`. BlastEm support is partial/shaky.
  MiSTer plays MSU-MD via the MegaCD core.

## Audio source

*Arthur to Astaroth no Nazomakaimura* (Saturn, 1996) — a Capcom puzzle
spin-off whose disc carries fully arranged versions of the Makaimura themes.
The 17-track rip is 44.1 kHz/16-bit/stereo throughout. Tracks 1–9 and 15 are
long (~4 min) arrangements; 10, 17 are short jingles; 11–14, 16 are mid-length
pieces. Mapping these onto the game's music IDs (stage themes, boss, ending,
jingles) is a listening exercise tracked in [track-map.md](track-map.md).
