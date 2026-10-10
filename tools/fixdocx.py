import re, zipfile, shutil, sys
src = sys.argv[1]; tmp = src + ".tmp"
zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == "word/document.xml":
        s = data.decode("utf-8")
        def fix(m):
            found = {k: v for v, k in re.findall(r'(<w:(top|left|bottom|right)\b[^>]*/>)', m.group(1))}
            return "<w:pBdr>" + "".join(found[k] for k in ("top", "left", "bottom", "right") if k in found) + "</w:pBdr>"
        s = re.sub(r"<w:pBdr>(.*?)</w:pBdr>", fix, s)
        data = s.encode("utf-8")
    zout.writestr(item, data)
zout.close(); zin.close(); shutil.move(tmp, src)
