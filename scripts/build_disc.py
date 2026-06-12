#!/usr/bin/env python3
"""Build the CD audio soundpack and cue sheet from the FLAC rips.

Decodes each configured FLAC to raw redbook PCM (44.1 kHz / 16-bit /
stereo, little-endian), pads to 2352-byte sector boundaries, concatenates
into a single soundpack bin, and writes a cue sheet next to the patched
ROM (which must share the cue's basename per the MSU-MD convention).

Run from the repo root: python3 scripts/build_disc.py
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import patch_config as cfg

SECTOR = 2352          # bytes per redbook sector
FPS = 75               # sectors (frames) per second


def msf(sector):
    s, f = divmod(sector, FPS)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}:{f:02d}"


def main():
    out = Path("build")
    out.mkdir(exist_ok=True)

    pack = bytearray()
    offsets = []
    for path in cfg.AUDIO_TRACKS:
        data, rate = sf.read(path, dtype="int16", always_2d=True)
        if rate != 44100 or data.shape[1] != 2:
            print(f"{path}: must be 44.1 kHz stereo (got {rate} Hz, "
                  f"{data.shape[1]}ch)", file=sys.stderr)
            return 1
        pcm = data.astype("<i2").tobytes()
        if len(pcm) % SECTOR:
            pcm += b"\x00" * (SECTOR - len(pcm) % SECTOR)
        offsets.append(len(pack) // SECTOR)
        pack += pcm
        print(f"track {len(offsets):2d}  {msf(offsets[-1])}  "
              f"{len(pcm) // SECTOR:5d} sectors  {path}")

    (out / cfg.SOUNDPACK_NAME).write_bytes(pack)

    cue = [f'FILE "{cfg.SOUNDPACK_NAME}" BINARY']
    for i, off in enumerate(offsets, 1):
        cue.append(f"  TRACK {i:02d} AUDIO")
        cue.append(f"    INDEX 01 {msf(off)}")
    cue_path = out / f"{cfg.OUTPUT_BASENAME}.cue"
    cue_path.write_text("\n".join(cue) + "\n")

    print(f"wrote build/{cfg.SOUNDPACK_NAME} "
          f"({len(pack)} bytes, {len(offsets)} tracks)")
    print(f"wrote {cue_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
