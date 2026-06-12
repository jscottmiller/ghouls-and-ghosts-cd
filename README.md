# Ghouls'n Ghosts CD

A Sega CD enhancement of the Genesis/Mega Drive version of **Ghouls'n Ghosts**:
the original game, untouched except that the soundtrack plays as redbook CD
audio, using the arranged Makaimura tracks from *Arthur to Astaroth no
Nazomakaimura* (Saturn, 1996).

## What this repo contains

Only original code, build scripts, and documentation. **No copyrighted
material is included or distributed.** To build, you must supply your own:

| Asset | Where it goes | Source |
|---|---|---|
| `Ghouls'n Ghosts (World) (Rev A).md` | `assets/rom/` | Your own dump of the Genesis cartridge (640 KB) |
| `01.flac` … `17.flac` | `assets/audio/` | Your own rip of the *Arthur to Astaroth no Nazomakaimura* (Saturn) audio tracks (44.1 kHz / 16-bit / stereo) |

Verify your assets match the expected dumps:

```sh
python3 scripts/verify_assets.py
```

## Building

Work in progress — see [docs/APPROACH.md](docs/APPROACH.md) for the technical
plan and current status.

Planned dependencies: `python3`, `ffmpeg` (FLAC → CD audio conversion), and a
68000 assembler.

## How it works (short version)

- **Phase 1 (Mode 1 / MSU-MD):** a patched ROM runs from cartridge with a Sega
  CD attached. The Sega CD's sub-CPU runs a small driver that plays CD audio
  tracks on command. The game's "play music" calls are intercepted and routed
  to the CD; sound effects stay on the YM2612/PSG. Output: a patch you apply
  to your ROM, plus a CUE/ISO built from your FLACs.
- **Phase 2 (boot-from-CD):** a true Sega CD disc that boots on a stock
  console, loading the game from CD. Significantly more involved — see the
  approach doc.

## License

Code in this repository: MIT (see LICENSE). Ghouls'n Ghosts and its music are
© Capcom / Sega; this project does not grant you any rights to them.
