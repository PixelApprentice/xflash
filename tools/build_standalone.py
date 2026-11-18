#!/usr/bin/env python3
"""Build standalone zero-install single binaries or zipapp packages for Xflash.

Supports two offline packaging options:
1. PyInstaller single-file executable (xflash.exe / xflash binary)
2. Python Standard Library ZipApp archive (xflash.pyz)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def build_zipapp(output_path: Path) -> bool:
    """Package the xflash package into a standalone .pyz using stdlib zipapp."""
    print("=" * 76)
    print(" BUILDING STANDALONE ZIPAPP (xflash.pyz)")
    print("=" * 76)

    build_dir = ROOT_DIR / "build" / "zipapp_staging"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy src/xflash
    src_pkg = ROOT_DIR / "src" / "xflash"
    dest_pkg = build_dir / "xflash"
    shutil.copytree(src_pkg, dest_pkg)

    # Create __main__.py inside staging
    main_file = build_dir / "__main__.py"
    main_file.write_text(
        "import sys\n"
        "from xflash.cli import main\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    zipapp.create_archive(
        source=build_dir,
        target=output_path,
        interpreter="/usr/bin/env python3" if os.name != "nt" else None,
        compressed=True,
    )

    # Make executable on POSIX
    if os.name != "nt":
        output_path.chmod(output_path.stat().st_mode | 0o111)

    print(f"✔ Successfully created standalone ZipApp archive: {output_path.resolve()}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  Execution: python3 {output_path.name} serve --portable\n")
    return True


def build_pyinstaller(dist_dir: Path) -> bool:
    """Compile a single-file zero-dependency executable using PyInstaller."""
    print("=" * 76)
    print(" COMPILING STANDALONE BINARY WITH PYINSTALLER")
    print("=" * 76)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("⚠ PyInstaller is not installed in the current environment.")
        print("To install PyInstaller, run: pip install pyinstaller")
        print("Falling back to Python Embeddable runtime or ZipApp package.")
        return False

    static_dir = ROOT_DIR / "src" / "xflash" / "web" / "static"
    cli_entry = ROOT_DIR / "run.py"

    separator = ";" if os.name == "nt" else ":"
    add_data = f"{static_dir}{separator}xflash/web/static"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "xflash",
        "--paths",
        str(ROOT_DIR / "src"),
        "--add-data",
        add_data,
        "--distpath",
        str(dist_dir),
        str(cli_entry),
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe_suffix = ".exe" if os.name == "nt" else ""
        out_bin = dist_dir / f"xflash{exe_suffix}"
        print(f"\n✔ Standalone binary built successfully: {out_bin.resolve()}")
        print(f"  Copy '{out_bin.name}' to your USB stick for 100% zero-install testing on any laptop!")
        return True
    else:
        print(f"\n✖ PyInstaller failed with exit code {result.returncode}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Xflash as a standalone single executable or archive.")
    parser.add_argument("--all", action="store_true", help="Build both PyInstaller binary and stdlib zipapp archive")
    parser.add_argument("--pyinstaller", action="store_true", help="Compile single-file binary with PyInstaller")
    parser.add_argument("--zipapp", action="store_true", help="Create .pyz zipapp archive using Python stdlib")
    parser.add_argument("--out", type=Path, help="Output destination path")
    args = parser.parse_args()

    if args.all:
        dist_dir = args.out or (ROOT_DIR / "dist")
        p_ok = build_pyinstaller(dist_dir)
        z_ok = build_zipapp(dist_dir / "xflash.pyz")
        return 0 if (p_ok and z_ok) else 1
    elif args.pyinstaller:
        dist_dir = args.out or (ROOT_DIR / "dist")
        success = build_pyinstaller(dist_dir)
        return 0 if success else 1
    else:
        # Default to zipapp
        out_file = args.out or (ROOT_DIR / "dist" / "xflash.pyz")
        success = build_zipapp(out_file)
        return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
