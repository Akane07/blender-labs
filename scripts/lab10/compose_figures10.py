"""Компоновка собственных рендеров без изменения геометрии и интерфейса."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from lab10_content import PANELS
ROOT=Path(__file__).resolve().parents[2];FIG=ROOT/'work/lab10/figures'
font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',28)
for key,panels in PANELS.items():
    if len(panels)==1:
        name,label=panels[0];im=Image.open(FIG/(name+'.png')).convert('RGB')
        background=Image.new('RGB',im.size,im.getpixel((0,0)))
        mask=ImageChops.difference(im,background).convert('L').point(lambda v:255 if v>10 else 0)
        box=mask.getbbox()
        if box:
            l,t,r,b=box;im=im.crop((max(0,l-45),max(0,t-45),min(im.width,r+45),min(im.height,b+45)))
        if label:
            out=Image.new('RGB',(im.width,im.height+60),'#e8edf1');out.paste(im,(0,60));d=ImageDraw.Draw(out);d.text((out.width/2,25),label,font=font,fill='black',anchor='mm')
        else:out=im
    else:
        w=700;h=500;out=Image.new('RGB',(w*len(panels),h+55),'#e8edf1');d=ImageDraw.Draw(out)
        for j,(name,label) in enumerate(panels):
            im=Image.open(FIG/(name+'.png')).convert('RGB');im=im.resize((w,h),Image.Resampling.LANCZOS);out.paste(im,(j*w,55));d.text((j*w+w/2,26),label,font=font,fill='black',anchor='mm')
    out.save(FIG/(key+'.jpg'),quality=93,subsampling=0,optimize=True)
print('COMPOSE_OK',len(PANELS))
