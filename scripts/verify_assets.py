#!/usr/bin/env python3
"""Verify that the user-supplied source assets match the expected hashes.

Usage: python3 scripts/verify_assets.py

Exits nonzero if any file is missing or mismatched. Run from the repo root.
"""
import hashlib
import sys
from pathlib import Path

MANIFEST = Path("assets/manifest.sha256")


def main():
    if not MANIFEST.exists():
        print(f"missing {MANIFEST}", file=sys.stderr)
        return 1
    failures = 0
    for line in MANIFEST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected, path = line.split(None, 1)
        p = Path(path)
        if not p.exists():
            print(f"MISSING   {path}")
            failures += 1
            continue
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected:
            print(f"MISMATCH  {path}")
            print(f"          expected {expected}")
            print(f"          actual   {actual}")
            failures += 1
        else:
            print(f"ok        {path}")
    if failures:
        print(f"\n{failures} file(s) failed verification. See README.md for "
              "where these assets must come from.", file=sys.stderr)
        return 1
    print("\nAll assets verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
