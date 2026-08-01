#!/usr/bin/env python
# ZPX OS - Standalone Boot Loader
# Run this to boot ZPX OS without needing to remember the ZPX command
# Usage: python boot.py
#        ./boot.py  (Unix)
#        boot.py    (Windows)

import sys
import os

def main():
    # Find ZPX project root (where src/ and self_host/ exist)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = script_dir

    # Walk up to find ZPX root
    while project_root != os.path.dirname(project_root):
        src_dir = os.path.join(project_root, 'src')
        self_host_dir = os.path.join(project_root, 'self_host')
        if os.path.isdir(src_dir) and os.path.isdir(self_host_dir):
            break
        project_root = os.path.dirname(project_root)

    if not os.path.isdir(os.path.join(project_root, 'src')):
        print("")
        print("  ZPX OS - Boot Loader")
        print("  ────────────────────────────────────────")
        print("  ERROR: ZPX project not found")
        print("  Please run from the ZPX project directory:")
        print("    pip install zpx-lang")
        print("    python -m src run zpx-os/boot.zpx")
        print("")
        sys.exit(1)

    sys.path.insert(0, project_root)
    os.chdir(project_root)

    # Import and run ZPX OS
    from src.cli import main as zpx_main

    # Override sys.argv to point to boot.zpx
    sys.argv = ['zpx', 'run', 'zpx-os/boot.zpx']

    try:
        zpx_main()
    except SystemExit:
        pass

if __name__ == '__main__':
    main()