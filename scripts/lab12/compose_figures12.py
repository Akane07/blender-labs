"""Компоновка подлинных рендеров с сохранением пропорций и альфа-канала."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
from lab12_content import PANELS,UI
ROOT=Path(__file__).resolve().parents[2];FIG=ROOT/'work/lab12/figures';OUT=ROOT/'output/lab12';OUT.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',26)
def flatten(im):
    im=im.convert('RGBA');bg=Image.new('RGBA',im.size,'#edf0f2');d=ImageDraw.Draw(bg)
    for y in range(0,im.height,20):
        for x in range(0,im.width,20):
            if (x//20+y//20)%2:d.rectangle((x,y,x+19,y+19),fill='#cbd1d6')
    return Image.alpha_composite(bg,im).convert('RGB')
for key,panels in PANELS.items():
    if key=='formats':
        out=Image.new('RGB',(1600,680),'white');d=ImageDraw.Draw(out)
        for i,(name,label) in enumerate(panels):
            im=flatten(Image.open(FIG/(name+'.png')));im.thumbnail((780,600));out.paste(im,(i*800+(800-im.width)//2,50));d.text((i*800+400,22),label,font=font,fill='black',anchor='mm')
    elif len(panels)==1:
        name,label=panels[0];im=flatten(Image.open(FIG/(name+'.png')));out=Image.new('RGB',(im.width,im.height+48),'#e8edf1');out.paste(im,(0,48));ImageDraw.Draw(out).text((im.width/2,22),label,font=font,fill='black',anchor='mm')
    else:
        w=620 if len(panels)==2 else 480;h=round(w*500/1175);out=Image.new('RGB',(w*len(panels),h+48),'#e8edf1');d=ImageDraw.Draw(out)
        for i,(name,label) in enumerate(panels):
            im=flatten(Image.open(FIG/(name+'.png'))).resize((w,h),Image.Resampling.LANCZOS);out.paste(im,(i*w,48));label_font=font
            for size in range(26,15,-1):
                label_font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',size)
                if d.textbbox((0,0),label,font=label_font)[2]<w-12:break
            d.text((i*w+w/2,22),label,font=label_font,fill='black',anchor='mm')
    out.save(FIG/(key+'.jpg'),quality=95,subsampling=0)
ui=OUT/'Снимки_интерфейса'
for key in UI:
    if (ui/(key+'.png')).exists():Image.open(ui/(key+'.png')).convert('RGB').save(FIG/(key+'.jpg'),quality=95,subsampling=0)
im=flatten(Image.open(FIG/'02_frame_235.png'));preview=Image.new('RGB',(1175,600),'#f3f4f5');preview.paste(im,(0,100));d=ImageDraw.Draw(preview);f=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf',36);d.text((587,32),'Лабораторная 12 — визуализация вестибюля',font=f,fill='black',anchor='mm');d.text((587,75),'Исходная модель пользователя из лабораторной 7',font=font,fill='black',anchor='mm');preview.save(OUT/'Превью_Лаба12.png')
print('COMPOSE_OK',len(PANELS),'render figures',sum((ui/(k+'.png')).exists() for k in UI),'native UI')
