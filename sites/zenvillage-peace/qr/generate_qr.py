#!/usr/bin/env python3
"""Generate the World Peace Weekend QR code for zenvillage.live/peace.

Outputs (in this folder):
  zenvillage-peace-qr.png        — high-res PNG (2400×2400), gradient brand colors
  zenvillage-peace-qr-mono.png   — high-res PNG (2400×2400), pure black on white (best print fidelity)
  zenvillage-peace-qr.svg        — vector, gradient brand colors
  zenvillage-peace-qr-mono.svg   — vector, mono
  zenvillage-peace-qr-card.png   — printable 4×6 card with QR + caption (for the flyer corner)
"""
from pathlib import Path
import segno
from PIL import Image, ImageDraw, ImageFont

URL = "https://zenvillage.live/peace"
OUT = Path(__file__).parent

# Error correction H = 30% — heavy enough to survive print/scan + a small overlay if we want one.
qr = segno.make(URL, error="h")

# 1. PNG — brand color (deep lilac). For the flyer / digital posters.
#    Save SVG first then rasterize via PIL so we get true RGB output (segno's
#    PNG writer uses palette mode which can drop hex colors).
qr.save(
    OUT / "_tmp-color.svg",
    scale=1,
    border=4,
    dark="#7e5cb8",
    light="#ffffff",
)

def render_png_rgb(out_path: Path, dark: tuple, scale: int = 60):
    """Render the QR to an RGB PNG at the given scale (px per module)."""
    size_modules = qr.symbol_size(scale=1, border=4)[0]
    px = size_modules * scale
    img = Image.new("RGB", (px, px), (255, 255, 255))
    matrix = [list(row) for row in qr.matrix]
    # Account for the border.
    border = 4
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            if cell:  # dark module
                x0 = (x + border) * scale
                y0 = (y + border) * scale
                for yy in range(y0, y0 + scale):
                    for xx in range(x0, x0 + scale):
                        img.putpixel((xx, yy), dark)
    img.save(out_path, "PNG", optimize=True)

# Faster path: build at 1 module = 1 px then upscale with NEAREST.
def render_png_rgb_fast(out_path: Path, dark: tuple, scale: int = 60):
    border = 4
    size_modules = qr.symbol_size(scale=1, border=0)[0]  # without border
    inner = size_modules
    total = inner + 2 * border
    base = Image.new("RGB", (total, total), (255, 255, 255))
    pixels = base.load()
    for y, row in enumerate(qr.matrix):
        for x, cell in enumerate(row):
            if cell:
                pixels[x + border, y + border] = dark
    out = base.resize((total * scale, total * scale), Image.NEAREST)
    out.save(out_path, "PNG", optimize=True)

# Brand color (lilac) — for digital + the flyer
render_png_rgb_fast(
    OUT / "zenvillage-peace-qr.png",
    dark=(126, 92, 184),
    scale=60,   # 41 modules × 60 = 2460 px
)

# Mono — most reliable for small print + photocopiers
render_png_rgb_fast(
    OUT / "zenvillage-peace-qr-mono.png",
    dark=(26, 21, 48),
    scale=60,
)

# Clean up the temp SVG used for sanity-checking the encoder
(OUT / "_tmp-color.svg").unlink(missing_ok=True)

# 3. SVG — vector, brand color. Use this for any printer that asks for vector.
qr.save(
    OUT / "zenvillage-peace-qr.svg",
    scale=24,
    border=4,
    dark="#7e5cb8",
    light="#ffffff",
)

# 4. SVG — vector, mono.
qr.save(
    OUT / "zenvillage-peace-qr-mono.svg",
    scale=24,
    border=4,
    dark="#1a1530",
    light="#ffffff",
)

# 5. Printable card with QR + caption — designed to drop on the flyer or use standalone.
#    4×6 inches @ 300 DPI = 1200×1800 px.
CARD_W, CARD_H = 1200, 1800
PAPER = (246, 241, 234)         # warm cream, matches site
INK   = (26, 21, 48)
LILAC = (155, 92, 184)
ROSE  = (217, 122, 122)
TEAL  = (79, 157, 148)

card = Image.new("RGB", (CARD_W, CARD_H), PAPER)
draw = ImageDraw.Draw(card)

# Open the freshly-saved color QR and paste it centered-top.
qr_img = Image.open(OUT / "zenvillage-peace-qr.png").convert("RGB")
qr_size = 900
qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
qr_x = (CARD_W - qr_size) // 2
qr_y = 240
card.paste(qr_img, (qr_x, qr_y))

# Decorative ring above the QR
ring_y = 140
ring_r = 38
ring_cx = CARD_W // 2
draw.ellipse(
    (ring_cx - ring_r, ring_y - ring_r, ring_cx + ring_r, ring_y + ring_r),
    outline=LILAC, width=4,
)
draw.line((ring_cx, ring_y - ring_r, ring_cx, ring_y + ring_r), fill=LILAC, width=4)
draw.line((ring_cx, ring_y, ring_cx - 28, ring_y + 28), fill=LILAC, width=4)
draw.line((ring_cx, ring_y, ring_cx + 28, ring_y + 28), fill=LILAC, width=4)

# Try to load nicer fonts; fall back to default if missing.
def load_font(size, italic=False, bold=False):
    candidates = []
    if italic:
        candidates += [
            "/Library/Fonts/Cormorant Garamond Italic.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
            "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        ]
    if bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
        ]
    candidates += [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# Headline + subline below the QR
def centered(text, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((CARD_W - w) // 2, y), text, font=font, fill=fill)

centered("Scan to join", qr_y + qr_size + 40, load_font(58, italic=True), INK)
centered("WORLD PEACE WEEKEND", qr_y + qr_size + 130, load_font(46, bold=True), INK)
centered("May 2 + 3  ·  Zen Village", qr_y + qr_size + 200, load_font(36), TEAL)

# Footer URL
centered("zenvillage.live/peace", CARD_H - 90, load_font(34, italic=True), LILAC)

card.save(OUT / "zenvillage-peace-qr-card.png", "PNG", optimize=True)

# Print summary
import os
files = [
    "zenvillage-peace-qr.png",
    "zenvillage-peace-qr-mono.png",
    "zenvillage-peace-qr.svg",
    "zenvillage-peace-qr-mono.svg",
    "zenvillage-peace-qr-card.png",
]
for f in files:
    p = OUT / f
    print(f"  {f}  ({os.path.getsize(p):,} bytes)")

print(f"\nEncoded URL: {URL}")
print(f"Error correction: H (30%)")
print(f"Modules: {qr.symbol_size(scale=1, border=0)[0]}×{qr.symbol_size(scale=1, border=0)[1]}")
