"""PNG → JPG для отчёта: python scripts/tojpg.py build/figs5 build/figs5_jpg"""
import sys, glob, os
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for f in glob.glob(src + "/*.png"):
    Image.open(f).convert("RGB").save(os.path.join(dst, os.path.basename(f)[:-4] + ".jpg"), quality=90)
