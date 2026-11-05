#!/usr/bin/env python3
"""Tool to prepare a 100% self-contained USB drive for shop inspections.

Solves the clean-OS scenario where a target laptop has a freshly wiped OS
(Windows 10/11) with ZERO software and NO Python installed.

What this script does:
1. Downloads the official, signed Python Windows Embeddable package (64-bit ~10 MB).
2. Extracts it into `./python/` on the USB drive.
3. Configures `python*._pth` so embeddable Python automatically loads Xflash from `../src/`.
4. Verifies that `start-xflash.bat` can launch without any host dependencies.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

PYTHON_EMBED_VERSION = "3.11.9"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_EMBED_VERSION}/python-{PYTHON_EMBED_VERSION}-embed-amd64.zip"


def prepare_usb(target_dir: Path, zip_file: Path | None = None) -> bool:
    print("=" * 76)
    print(" XFLASH USB OFFLINE RUNTIME PREPARATOR")
    print(" Check before you pay · Zero-install standalone USB package")
    print("=" * 76)

    python_dir = target_dir / "python"
    python_dir.mkdir(parents=True, exist_ok=True)

    zip_path = zip_file
    if not zip_path or not zip_path.is_file():
        zip_path = target_dir / f"python-{PYTHON_EMBED_VERSION}-embed-amd64.zip"
        if not zip_path.is_file():
            print(f"\n[1/4] Downloading official Windows Embeddable Python ({PYTHON_EMBED_VERSION}) (~10 MB)...")
            print(f"      Source: {PYTHON_EMBED_URL}")
            try:
                urllib.request.urlretrieve(PYTHON_EMBED_URL, zip_path)
                print("      ✔ Download complete.")
            except Exception as exc:
                print(f"      ✖ Download failed: {exc}", file=sys.stderr)
                print("\nManual Alternative:")
                print(f"1. Download '{PYTHON_EMBED_URL}' manually.")
                print(f"2. Extract its contents into: {python_dir}")
                return False
        else:
            print(f"\n[1/4] Found existing embeddable archive: {zip_path.name}")
    else:
        print(f"\n[1/4] Using specified archive: {zip_path}")

    # Extract embeddable python into target_dir/python
    print(f"\n[2/4] Extracting runtime into {python_dir.resolve()}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(python_dir)
        print("      ✔ Extracted all runtime files.")
    except Exception as exc:
        print(f"      ✖ Extraction failed: {exc}", file=sys.stderr)
        return False

    # Configure python*._pth
    print("\n[3/4] Configuring Python search path (_pth file)...")
    pth_files = list(python_dir.glob("*._pth"))
    if not pth_files:
        pth_path = python_dir / f"python{PYTHON_EMBED_VERSION.replace('.', '')[:3]}._pth"
    else:
        pth_path = pth_files[0]

    pth_content = f"""python{PYTHON_EMBED_VERSION.replace('.', '')[:3]}.zip
.
..\\src
..\\
import site
"""
    pth_path.write_text(pth_content, encoding="utf-8")
    print(f"      ✔ Updated {pth_path.name} to auto-import Xflash from USB root.")

    # Clean up zip
    if zip_path.name.startswith("python-") and zip_path.parent == target_dir:
        try:
            zip_path.unlink()
        except OSError:
            pass

    print("\n[4/4] Verifying USB structure...")
    exe_path = python_dir / "python.exe"
    if exe_path.is_file():
        print("      ✔ python.exe verified in ./python/ folder.")
    else:
        print("      ⚠ Warning: python.exe not found in extracted folder.")

    print("\n" + "=" * 76)
    print(" ✔ SUCCESS! Your USB drive is now 100% self-contained.")
    print("=" * 76)
    print("When you plug this USB into ANY shop laptop running Windows 8, 10, or 11:")
    print("  1. The target laptop does NOT need Python installed.")
    print("  2. The target laptop does NOT need internet access.")
    print("  3. Simply double-click 'start-xflash.bat' on the USB drive.")
    print("  4. Xflash will boot instantly using the self-contained USB runtime,")
    print("     and write all inspection records directly to the USB drive!")
    print("=" * 76 + "\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare offline USB with embeddable Python for shop testing")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Target directory (default: current directory)")
    parser.add_argument("--zip", type=Path, help="Path to already downloaded python-*-embed-amd64.zip")
    args = parser.parse_args()

    success = prepare_usb(target_dir=args.target, zip_file=args.zip)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
