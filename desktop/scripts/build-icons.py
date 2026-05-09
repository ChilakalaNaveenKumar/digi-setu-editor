#!/usr/bin/env python3
"""
Rebuild every platform-specific app icon from a single high-resolution source.

Why this exists:
- The original `icon.png` (512x512) was being downscaled by macOS to dock/menu-bar
  sizes (16/32 px) on the fly, producing visibly blurred results.
- We generate a proper 1024x1024 master and pre-render every size that macOS,
  Windows and Linux expect, with high-quality Lanczos resampling.

Outputs (overwrites in place):
- desktop/src-tauri/icons/icon.png                      (1024x1024 PNG master)
- desktop/src-tauri/icons/icon.icns                     (macOS multi-resolution)
- desktop/src-tauri/icons/icon.ico                      (Windows multi-resolution)
- desktop/src-tauri/icons/{16,32,64,128,256,512,1024}*.png
- desktop/src-tauri/icons/Square*Logo.png + StoreLogo.png (Windows Store)
"""
from __future__ import annotations

import argparse
import base64
import io
import re
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = ROOT / "desktop" / "src-tauri" / "icons"
SVG_SOURCE = ROOT / "web" / "frontend" / "public" / "digi-setu-logo.svg"

BG_COLOR = (15, 23, 42, 255)            # slate-900 = #0F172A
GLYPH_COLOR = (255, 255, 255, 255)
MASTER_SIZE = 1024
GLYPH_FILL = 0.70                       # Apple HIG: glyph fills ~68-72% of canvas
CORNER_RADIUS_RATIO = 0.2237            # Apple "squircle" approximation


def extract_glyph_from_svg(svg_path: Path) -> Image.Image:
    """The vue 'svg' is actually a base64 PNG wrapped in <pattern>. Decode it."""
    raw = svg_path.read_text()
    m = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", raw)
    if not m:
        raise SystemExit(f"no embedded png inside {svg_path}")
    data = base64.b64decode(m.group(1))
    return Image.open(io.BytesIO(data)).convert("RGBA")


def autocrop_alpha(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        raise SystemExit("source glyph has no visible pixels")
    return img.crop(bbox)


def render_master(glyph: Image.Image) -> Image.Image:
    """Compose the 1024x1024 master: rounded-square bg + centered white glyph."""
    canvas = Image.new("RGBA", (MASTER_SIZE, MASTER_SIZE), (0, 0, 0, 0))

    # Rounded-square mask for the navy background.
    mask = Image.new("L", (MASTER_SIZE, MASTER_SIZE), 0)
    radius = int(MASTER_SIZE * CORNER_RADIUS_RATIO)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, MASTER_SIZE - 1, MASTER_SIZE - 1),
        radius=radius,
        fill=255,
    )
    bg = Image.new("RGBA", (MASTER_SIZE, MASTER_SIZE), BG_COLOR)
    canvas.paste(bg, (0, 0), mask)

    # Force the glyph to pure white (ignore source colour fringes from JPG-ish PNG).
    g = glyph.copy()
    r, gg, b, a = g.split()
    white = Image.new("RGBA", g.size, GLYPH_COLOR)
    g = Image.composite(white, Image.new("RGBA", g.size, (0, 0, 0, 0)), a)

    # Scale glyph to fit GLYPH_FILL of the master while preserving aspect ratio.
    target = int(MASTER_SIZE * GLYPH_FILL)
    w, h = g.size
    scale = min(target / w, target / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    g = g.resize((nw, nh), Image.LANCZOS)

    ox = (MASTER_SIZE - nw) // 2
    oy = (MASTER_SIZE - nh) // 2
    canvas.alpha_composite(g, (ox, oy))
    return canvas


def hi_quality_resize(master: Image.Image, size: int) -> Image.Image:
    """Two-step downscale (mip-map style) keeps thin lines crisp at small sizes."""
    img = master
    while img.size[0] // 2 > size:
        img = img.resize((img.size[0] // 2, img.size[1] // 2), Image.LANCZOS)
    return img.resize((size, size), Image.LANCZOS)


def write_macos_icns(master: Image.Image, out: Path) -> None:
    iconset = out.with_suffix(".iconset")
    if iconset.exists():
        for f in iconset.iterdir():
            f.unlink()
    iconset.mkdir(parents=True, exist_ok=True)

    pairs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for name, size in pairs:
        hi_quality_resize(master, size).save(iconset / name, "PNG")

    if out.exists():
        out.unlink()
    subprocess.run(
        ["iconutil", "--convert", "icns", "--output", str(out), str(iconset)],
        check=True,
    )
    for f in iconset.iterdir():
        f.unlink()
    iconset.rmdir()


def write_windows_ico(master: Image.Image, out: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [hi_quality_resize(master, s) for s in sizes]
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


def write_pngs(master: Image.Image) -> None:
    # Tauri default sizes
    for size in [32, 64, 128]:
        hi_quality_resize(master, size).save(ICON_DIR / f"{size}x{size}.png", "PNG")
    hi_quality_resize(master, 256).save(ICON_DIR / "128x128@2x.png", "PNG")
    master.save(ICON_DIR / "icon.png", "PNG")

    # Windows Store assets keep the same artwork (sizes per MS template)
    store_sizes = {
        "Square30x30Logo.png": 30,
        "Square44x44Logo.png": 44,
        "Square71x71Logo.png": 71,
        "Square89x89Logo.png": 89,
        "Square107x107Logo.png": 107,
        "Square142x142Logo.png": 142,
        "Square150x150Logo.png": 150,
        "Square284x284Logo.png": 284,
        "Square310x310Logo.png": 310,
        "StoreLogo.png": 50,
    }
    for name, size in store_sizes.items():
        hi_quality_resize(master, size).save(ICON_DIR / name, "PNG")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild Digi Setu app icons.")
    parser.add_argument("--source", type=Path, default=SVG_SOURCE,
                        help=f"glyph source (svg-with-embedded-png), default: {SVG_SOURCE}")
    args = parser.parse_args(argv)

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2

    print(f"[icons] source       : {args.source.relative_to(ROOT)}")
    glyph = autocrop_alpha(extract_glyph_from_svg(args.source))
    print(f"[icons] glyph cropped: {glyph.size[0]}x{glyph.size[1]}")

    master = render_master(glyph)
    print(f"[icons] master       : {MASTER_SIZE}x{MASTER_SIZE}")

    write_pngs(master)
    print("[icons] wrote PNG variants")

    write_macos_icns(master, ICON_DIR / "icon.icns")
    print("[icons] wrote icon.icns (10 embedded sizes)")

    write_windows_ico(master, ICON_DIR / "icon.ico")
    print("[icons] wrote icon.ico (7 embedded sizes)")

    print(f"[icons] done -> {ICON_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
