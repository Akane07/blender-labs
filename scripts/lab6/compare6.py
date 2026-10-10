"""Склейка «без рельефа | с рельефом» для отчёта."""
import os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
F = os.path.join(ROOT, "build", "figs6")
a = Image.open(os.path.join(F, "f_nobump_crop.png")).convert("RGB"); b = Image.open(os.path.join(F, "f_bump_crop.png")).convert("RGB")
gap = 12
s = Image.new("RGB", (a.width + b.width + gap, a.height), "white"); s.paste(a, (0, 0)); s.paste(b, (a.width + gap, 0))
d = ImageDraw.Draw(s)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
except OSError:
    font = ImageFont.load_default()
for x, t in ((20, "Без карты неровностей"), (a.width + gap + 20, "С картой неровностей")):
    bb = d.textbbox((x, 18), t, font=font); d.rectangle([bb[0] - 8, bb[1] - 6, bb[2] + 8, bb[3] + 6], fill=(0, 0, 0)); d.text((x, 18), t, fill="white", font=font)
s.save(os.path.join(F, "f_bump_compare.png"))
