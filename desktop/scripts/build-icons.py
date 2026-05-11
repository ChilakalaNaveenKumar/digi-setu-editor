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
# Where to drop the browser favicon set (tab + iOS home-screen icons).
# Both frontends ship copies so the index.html <link rel="icon" ...> tags
# resolve cleanly in both web and Tauri-served contexts.
FAVICON_DIRS = [
    ROOT / "web" / "frontend" / "public",
    ROOT / "desktop" / "frontend" / "public",
]
# We intentionally use the TIGHT-CROPPED variant for icon generation so
# the rendered glyph reaches all four edges of the icon canvas. The full
# wordmark logo stays at SVG_SOURCE for use in the in-app header (which
# has more horizontal real estate).
SVG_TIGHT = Path(__file__).resolve().parent / "_logo-tight.svg"

BG_COLOR = (15, 23, 42, 255)            # slate-900 = #0F172A
GLYPH_COLOR = (255, 255, 255, 255)
MASTER_SIZE = 1024
CORNER_RADIUS_RATIO = 0.2237            # Apple "squircle" approximation


# We deliberately DROP the rounded-square background and let the glyph fill
# essentially the entire canvas (98%). At 32px every pixel matters and the
# old Apple-HIG squircle bg was eating ~30% of the available pixels for
# decoration. macOS / Windows / Linux all render icons over the platform's
# own dock/taskbar backdrop, so the bg layer was redundant anyway.
GLYPH_FILL = 0.98


def _have(cmd: str) -> bool:
    """True if `cmd` resolves on PATH."""
    from shutil import which
    return which(cmd) is not None


def rasterise_glyph(svg_path: Path, target_w: int, target_h: int) -> Image.Image:
    """Rasterise the source SVG to fit (target_w x target_h), preserving aspect.

    For TRUE vector SVGs we hand the size directly to `rsvg-convert` so the
    glyph gets pixel-perfect anti-aliasing at the final output resolution —
    NEVER a downscaled bitmap, which is where small icons lose their crisp
    edges. For the legacy embedded-PNG-in-SVG case (the old vue export) we
    decode the bitmap once and Lanczos-resample, since there's no vector
    data to rasterise from.
    """
    raw = svg_path.read_text()
    embedded = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", raw)
    if embedded:
        data = base64.b64decode(embedded.group(1))
        bitmap = Image.open(io.BytesIO(data)).convert("RGBA")
        bitmap = autocrop_alpha(bitmap)
        w, h = bitmap.size
        scale = min(target_w / w, target_h / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        return bitmap.resize((nw, nh), Image.LANCZOS)

    if not _have("rsvg-convert"):
        raise SystemExit(
            "rsvg-convert is required to rasterise vector SVGs. "
            "Install it via `brew install librsvg`."
        )
    proc = subprocess.run(
        [
            "rsvg-convert",
            "--width", str(target_w),
            "--height", str(target_h),
            "--keep-aspect-ratio",
            str(svg_path),
        ],
        check=True,
        capture_output=True,
    )
    return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")


def autocrop_alpha(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        raise SystemExit("source glyph has no visible pixels")
    return img.crop(bbox)


def render_at(svg_path: Path, size: int) -> Image.Image:
    """Render a single icon at exactly (size x size).

    Strategy: rasterise the SVG natively at the final size via rsvg-convert
    so every pixel gets pixel-perfect anti-aliasing, then centre it on a
    transparent (size x size) canvas. No squircle bg — every pixel goes to
    the actual glyph. The platform (Dock, Taskbar, Activity bar) supplies
    its own backdrop.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    target = max(1, int(size * GLYPH_FILL))
    glyph = rasterise_glyph(svg_path, target, target)

    # Force every visible pixel to pure white using the alpha as a mask.
    _, _, _, alpha = glyph.split()
    glyph = Image.composite(
        Image.new("RGBA", glyph.size, GLYPH_COLOR),
        Image.new("RGBA", glyph.size, (0, 0, 0, 0)),
        alpha,
    )

    nw, nh = glyph.size
    ox = (size - nw) // 2
    oy = (size - nh) // 2
    canvas.alpha_composite(glyph, (ox, oy))
    return canvas


def write_macos_icns(svg_path: Path, out: Path) -> None:
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
        render_at(svg_path, size).save(iconset / name, "PNG")

    if out.exists():
        out.unlink()
    subprocess.run(
        ["iconutil", "--convert", "icns", "--output", str(out), str(iconset)],
        check=True,
    )
    for f in iconset.iterdir():
        f.unlink()
    iconset.rmdir()


def write_windows_ico(svg_path: Path, out: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [render_at(svg_path, s) for s in sizes]
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


def write_favicons(svg_path: Path) -> None:
    """Drop favicon.ico + favicon-32 + favicon-192 + apple-touch-icon.png
    into every frontend public dir so the <link rel="icon"> tags in
    index.html actually resolve."""
    for tgt in FAVICON_DIRS:
        if not tgt.exists():
            continue
        ico = [render_at(svg_path, s) for s in (16, 32, 48)]
        ico[0].save(
            tgt / "favicon.ico",
            format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48)],
            append_images=ico[1:],
        )
        render_at(svg_path, 32).save(tgt / "favicon-32.png", "PNG")
        render_at(svg_path, 192).save(tgt / "favicon-192.png", "PNG")
        render_at(svg_path, 180).save(tgt / "apple-touch-icon.png", "PNG")


def write_pngs(svg_path: Path) -> None:
    for size in [32, 64, 128]:
        render_at(svg_path, size).save(ICON_DIR / f"{size}x{size}.png", "PNG")
    render_at(svg_path, 256).save(ICON_DIR / "128x128@2x.png", "PNG")
    render_at(svg_path, MASTER_SIZE).save(ICON_DIR / "icon.png", "PNG")

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
        render_at(svg_path, size).save(ICON_DIR / name, "PNG")


def _build_tight_variant() -> Path:
    """Generate (or refresh) the tight-cropped SVG used for icon rendering.

    The wordmark SVG has ~16% of its bounding box reserved as whitespace
    padding. For icon contexts we want every pixel to count, so we measure
    the alpha bbox of a high-res rasterisation and rewrite the viewBox to
    fit the content (with a ~5% safety margin so anti-aliased edges aren't
    clipped). Result lives next to this script as `_logo-tight.svg`.
    """
    if not _have("rsvg-convert"):
        return SVG_SOURCE  # fall back to the un-cropped source.
    out = subprocess.run(
        ["rsvg-convert", "--width", "4096", str(SVG_SOURCE)],
        check=True, capture_output=True,
    ).stdout
    bm = Image.open(io.BytesIO(out)).convert("RGBA")
    bbox = bm.getbbox()
    if not bbox:
        return SVG_SOURCE
    W, H = bm.size
    sx, sy = 0, 0
    raw = SVG_SOURCE.read_text()
    m = re.search(r'viewBox="([^"]+)"', raw)
    if m:
        vx, vy, vw, vh = (float(x) for x in m.group(1).split())
        sx, sy = vw / W, vh / H
        bx = vx + bbox[0] * sx
        by = vy + bbox[1] * sy
        bw = (bbox[2] - bbox[0]) * sx
        bh = (bbox[3] - bbox[1]) * sy
    else:
        bx, by = bbox[0], bbox[1]
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = max(bw, bh) * 0.05
    bx -= margin; by -= margin
    bw += 2 * margin; bh += 2 * margin
    new_vb = f"{bx:.2f} {by:.2f} {bw:.2f} {bh:.2f}"
    s = re.sub(r'\swidth="[^"]*"', "", raw, count=1)
    s = re.sub(r'\sheight="[^"]*"', "", s, count=1)
    s = re.sub(r'viewBox="[^"]*"', f'viewBox="{new_vb}"', s, count=1)
    SVG_TIGHT.write_text(s)
    return SVG_TIGHT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild Digi Setu app icons.")
    parser.add_argument("--source", type=Path, default=None,
                        help=f"glyph source (default: tight-crop of {SVG_SOURCE.relative_to(ROOT)})")
    args = parser.parse_args(argv)

    src = args.source or _build_tight_variant()

    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr)
        return 2

    print(f"[icons] source       : {src.relative_to(ROOT)}")
    print(f"[icons] strategy     : rasterise SVG natively at every output size")
    args.source = src

    write_pngs(args.source)
    print("[icons] wrote PNG variants (icon.png + Tauri sizes + Square*Logo)")

    write_favicons(args.source)
    print("[icons] wrote browser favicons (favicon.ico + 32/192/apple-touch)")

    write_macos_icns(args.source, ICON_DIR / "icon.icns")
    print("[icons] wrote icon.icns (10 native renders)")

    write_windows_ico(args.source, ICON_DIR / "icon.ico")
    print("[icons] wrote icon.ico (7 native renders)")

    print(f"[icons] done -> {ICON_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
