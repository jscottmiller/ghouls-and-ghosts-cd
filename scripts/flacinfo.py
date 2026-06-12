#!/usr/bin/env python3
"""Dependency-free FLAC STREAMINFO reader.

Prints sample rate, channels, bit depth, and duration for each FLAC file
given on the command line. Used by asset verification so builders don't
need ffprobe just to sanity-check their rips.
"""
import struct
import sys


def streaminfo(path):
    with open(path, "rb") as f:
        if f.read(4) != b"fLaC":
            raise ValueError(f"{path}: not a FLAC file")
        while True:
            header = f.read(4)
            if len(header) < 4:
                raise ValueError(f"{path}: no STREAMINFO block found")
            last = bool(header[0] & 0x80)
            block_type = header[0] & 0x7F
            length = int.from_bytes(header[1:4], "big")
            if block_type == 0:  # STREAMINFO
                data = f.read(length)
                bits = int.from_bytes(data[10:18], "big")
                sample_rate = bits >> 44
                channels = ((bits >> 41) & 0x7) + 1
                bps = ((bits >> 36) & 0x1F) + 1
                total_samples = bits & ((1 << 36) - 1)
                return sample_rate, channels, bps, total_samples
            if last:
                raise ValueError(f"{path}: no STREAMINFO block found")
            f.seek(length, 1)


def main():
    for path in sys.argv[1:]:
        rate, ch, bps, samples = streaminfo(path)
        secs = samples / rate if rate else 0
        print(f"{path}\t{rate} Hz\t{ch}ch\t{bps}-bit\t{secs:7.1f}s\t({int(secs)//60}:{int(secs)%60:02d})")


if __name__ == "__main__":
    main()
