#!/usr/bin/env python3
"""Generate icon files in multiple hicolor sizes from a source icon.

Usage:
    generate_icon_sizes.py <input_icon> <output_dir>

Generates icon.png files at standard hicolor sizes (16, 24, 32, 48, 64, 128, 256)
under <output_dir>/<size>x<size>/apps/icon_name.png, ready for installation to
/usr/share/icons/hicolor/.

Requires Pillow (PIL).
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print(
        "ERROR: Pillow is required. Install with: pip install pillow",
        file=sys.stderr,
    )
    sys.exit(1)

# Standard hicolor icon sizes.
ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_icon",
        type=Path,
        help="source icon file (e.g. icon.png)",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="output directory where size subdirs are created",
    )
    parser.add_argument(
        "--name",
        default="icon.png",
        help="output filename (default: icon.png)",
    )
    args = parser.parse_args(argv)

    if not args.input_icon.is_file():
        print(f"ERROR: input file not found: {args.input_icon}", file=sys.stderr)
        return 1

    # Load the source icon.
    try:
        img = Image.open(args.input_icon)
    except Exception as exc:
        print(f"ERROR: failed to load {args.input_icon}: {exc}", file=sys.stderr)
        return 1

    # Generate each size.
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for size in ICON_SIZES:
        size_dir = args.output_dir / f"{size}x{size}" / "apps"
        size_dir.mkdir(parents=True, exist_ok=True)

        output_path = size_dir / args.name
        try:
            # Resize with high-quality resampling.
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(output_path, "PNG")
            print(f"Generated {size}x{size}: {output_path}")
        except Exception as exc:
            print(f"ERROR: failed to generate {size}x{size}: {exc}", file=sys.stderr)
            return 1

    print(f"Successfully generated icons at sizes: {', '.join(map(str, ICON_SIZES))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
