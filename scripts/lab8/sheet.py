"""Контакт-лист рендеров: python scripts/lab8/sheet.py build/figs8 out.jpg [имена...]"""
import sys, glob, os, math
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
names = sys.argv[3:]
fs = [os.path.join(src, n + ".png") for n in names] if names else sorted(glob.glob(src + "/*.png"), key=os.path.getmtime)
ims = []
for f in fs:
    im = Image.open(f).convert("RGB"); im.thumbnail((520, 420)); ims.append(im)
cols = 3; W = 520; H = max(i.height for i in ims)
sheet = Image.new("RGB", (W * cols, H * math.ceil(len(ims) / cols)), "white")
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * W, (k // cols) * H))
sheet.save(out, quality=88)
