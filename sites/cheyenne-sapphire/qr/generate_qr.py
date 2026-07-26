#!/usr/bin/env python3
"""Generate Cheyenne Sapphire's Instagram QR code.

Outputs (in this folder):
  cheyenne-ig-qr.png        — high-res plain QR (2400×2400), black on white
  cheyenne-ig-qr-card.png   — branded card: logo on top, QR below, caption
"""
from pathlib import Path
import segno
from PIL import Image, ImageDraw, ImageFont

URL = "https://www.instagram.com/cheyennesapphireofficial/"
OUT = Path(__file__).parent
LOGO = OUT / "cheyenne-logo.png"

# H = 30% error correction — survives print/scan.
qr = segno.make(URL, error="h")

# 1. Plain high-res QR PNG
qr.save(OUT / "cheyenne-ig-qr.png", scale=40, border=4, dark="#000000", light="#ffffff")

# 2. Branded card — logo on top, QR below, handle caption
qr.save(OUT / "_tmp-qr.png", scale=30, border=2, dark="#1a1a1a", light="#ffffff")
qr_img = Image.open(OUT / "_tmp-qr.png").convert("RGBA")

CARD_W = 1600
MARGIN = 120
BG = (255, 255, 255, 255)

# Logo — fit to card width
logo = Image.open(LOGO).convert("RGBA")
logo_w = CARD_W - 2 * MARGIN
logo_h = int(logo.height * (logo_w / logo.width))
logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

# QR — sized to fit card width
qr_w = CARD_W - 2 * MARGIN
qr_img = qr_img.resize((qr_w, qr_w), Image.NEAREST)

# Caption
caption = "@cheyennesapphireofficial"
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 60)
except Exception:
    font = ImageFont.load_default()

gap = 70
cap_h = 120
CARD_H = MARGIN + logo_h + gap + qr_w + gap + cap_h + MARGIN

card = Image.new("RGBA", (CARD_W, CARD_H), BG)
y = MARGIN
card.paste(logo, ((CARD_W - logo_w) // 2, y), logo)
y += logo_h + gap
card.paste(qr_img, ((CARD_W - qr_w) // 2, y), qr_img)
y += qr_w + gap

draw = ImageDraw.Draw(card)
bbox = draw.textbbox((0, 0), caption, font=font)
tw = bbox[2] - bbox[0]
draw.text(((CARD_W - tw) // 2, y), caption, fill=(60, 60, 60, 255), font=font)

card.convert("RGB").save(OUT / "cheyenne-ig-qr-card.png", "PNG")

(OUT / "_tmp-qr.png").unlink(missing_ok=True)
print("Wrote cheyenne-ig-qr.png and cheyenne-ig-qr-card.png")
