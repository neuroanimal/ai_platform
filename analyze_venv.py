#!/usr/bin/env python3
"""Analyze venv structure"""

import os
from pathlib import Path

venv_path = Path("/home/estagrz/repo/.venv.ai/lib/python3.15/site-packages")

print(f"Checking: {venv_path}\n")

symlinks = []
real_files = []
so_files = []

for item in venv_path.iterdir():
    if item.is_symlink():
        target = os.readlink(item)
        symlinks.append((item.name, target))
        # Check for .so files in symlinked dirs
        if item.is_dir():
            for so in item.rglob("*.so"):
                so_files.append((so.name, "symlinked"))
    elif item.is_file() or item.is_dir():
        real_files.append(item.name)
        if item.is_dir():
            for so in item.rglob("*.so"):
                so_files.append((so.name, "real"))

print(f"Symlinks: {len(symlinks)}")
print(f"Real files/dirs: {len(real_files)}")
print(f"\n.so files found: {len(so_files)}")

if so_files:
    print("\nCompiled extensions (will crash if from 3.13):")
    for name, source in so_files[:10]:
        print(f"  {name} ({source})")
    if len(so_files) > 10:
        print(f"  ... and {len(so_files) - 10} more")
