#!/usr/bin/env python3
"""Apply a BPS patch and report what it changed.

Usage:
    python3 scripts/bpstool.py <patch.bps> <source.bin> [-o output.bin]

Verifies source/target/patch CRC32s, writes the patched output if requested,
and prints a map of changed regions (byte diff of source vs target, plus any
appended data beyond the source length).
"""
import argparse
import sys
import zlib


def read_varint(buf, pos):
    data, shift = 0, 1
    while True:
        x = buf[pos]
        pos += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, pos
        shift <<= 7
        data += shift


def apply_bps(patch, source):
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS1 patch")
    crc_src, crc_tgt, crc_patch = (
        int.from_bytes(patch[-12:-8], "little"),
        int.from_bytes(patch[-8:-4], "little"),
        int.from_bytes(patch[-4:], "little"),
    )
    if zlib.crc32(patch[:-4]) != crc_patch:
        raise ValueError("patch CRC mismatch (corrupt download?)")
    if zlib.crc32(source) != crc_src:
        raise ValueError(
            f"source CRC mismatch: patch wants {crc_src:08X}, "
            f"got {zlib.crc32(source):08X}"
        )

    pos = 4
    src_size, pos = read_varint(patch, pos)
    tgt_size, pos = read_varint(patch, pos)
    meta_size, pos = read_varint(patch, pos)
    metadata = patch[pos:pos + meta_size]
    pos += meta_size
    if src_size != len(source):
        raise ValueError(f"source size mismatch: {src_size} != {len(source)}")

    target = bytearray(tgt_size)
    out = 0
    src_rel = tgt_rel = 0
    end = len(patch) - 12
    while pos < end:
        data, pos = read_varint(patch, pos)
        cmd, length = data & 3, (data >> 2) + 1
        if cmd == 0:  # SourceRead
            target[out:out + length] = source[out:out + length]
        elif cmd == 1:  # TargetRead
            target[out:out + length] = patch[pos:pos + length]
            pos += length
        elif cmd == 2:  # SourceCopy
            data, pos = read_varint(patch, pos)
            src_rel += (-1 if data & 1 else 1) * (data >> 1)
            target[out:out + length] = source[src_rel:src_rel + length]
            src_rel += length
        else:  # TargetCopy (may overlap itself; copy byte-wise)
            data, pos = read_varint(patch, pos)
            tgt_rel += (-1 if data & 1 else 1) * (data >> 1)
            for i in range(length):
                target[out + i] = target[tgt_rel + i]
            tgt_rel += length
        out += length

    if zlib.crc32(target) != crc_tgt:
        raise ValueError("target CRC mismatch after apply")
    return bytes(target), metadata


def write_varint(value):
    out = bytearray()
    while True:
        x = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(x | 0x80)
            return bytes(out)
        out.append(x)
        value -= 1


def create_bps(source, target):
    """Create a BPS patch from source to target.

    Simple encoder: SourceRead for matching runs, TargetRead for new bytes,
    with an RLE pass (overlapped TargetCopy) for long repeated runs such as
    ROM padding. Good enough for hook patches; not a general delta encoder.
    """
    out = bytearray(b"BPS1")
    out += write_varint(len(source))
    out += write_varint(len(target))
    out += write_varint(0)  # no metadata

    actions = []  # ('sr'|'tr'|'rle', start, length)
    n = len(target)
    i = 0
    while i < n:
        if i < len(source) and source[i] == target[i]:
            start = i
            while i < n and i < len(source) and source[i] == target[i]:
                i += 1
            actions.append(("sr", start, i - start))
            continue
        # new/changed bytes: check for a repeated-byte run worth RLE'ing
        start = i
        while i < n and not (i < len(source) and source[i] == target[i]):
            run = 1
            while i + run < n and target[i + run] == target[i]:
                run += 1
            if run >= 32:
                if i > start:
                    actions.append(("tr", start, i - start))
                actions.append(("tr", i, 1))
                actions.append(("rle", i + 1, run - 1))
                i += run
                start = i
            else:
                i += run
        if i > start:
            actions.append(("tr", start, i - start))

    tgt_rel = 0
    for kind, start, length in actions:
        if kind == "sr":
            out += write_varint(((length - 1) << 2) | 0)
        elif kind == "tr":
            out += write_varint(((length - 1) << 2) | 1)
            out += target[start:start + length]
        else:  # rle: TargetCopy overlapping forward copy from start-1
            out += write_varint(((length - 1) << 2) | 3)
            offset = (start - 1) - tgt_rel
            out += write_varint((abs(offset) << 1) | (1 if offset < 0 else 0))
            tgt_rel = (start - 1) + length

    out += zlib.crc32(source).to_bytes(4, "little")
    out += zlib.crc32(target).to_bytes(4, "little")
    out += zlib.crc32(out).to_bytes(4, "little")
    return bytes(out)


def changed_regions(source, target, gap=16):
    """Yield (start, end) ranges where target differs from source.

    Runs of unchanged bytes shorter than `gap` are merged into one region.
    """
    regions = []
    n = min(len(source), len(target))
    i = 0
    while i < n:
        if source[i] != target[i]:
            start = i
            last = i
            while i < n:
                if source[i] != target[i]:
                    last = i
                elif i - last >= gap:
                    break
                i += 1
            regions.append((start, last + 1))
        else:
            i += 1
    if len(target) > len(source):
        regions.append((len(source), len(target)))
    return regions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patch")
    ap.add_argument("source")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    patch = open(args.patch, "rb").read()
    source = open(args.source, "rb").read()
    target, metadata = apply_bps(patch, source)
    if metadata:
        print(f"metadata: {metadata[:200]!r}")
    print(f"source {len(source)} bytes -> target {len(target)} bytes, CRCs ok")
    print("\nchanged regions:")
    total = 0
    for start, endr in changed_regions(source, target):
        kind = "appended" if start >= len(source) else "modified"
        total += endr - start
        print(f"  {start:06X}-{endr:06X}  {endr - start:6} bytes  {kind}")
    print(f"\n{total} bytes changed/appended")
    if args.output:
        with open(args.output, "wb") as f:
            f.write(target)
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
