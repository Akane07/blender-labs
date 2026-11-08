"""Компоновка собственных рендеров и обрезка настоящих снимков Blender."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from lab11_content import PANELS
ROOT=Path(__file__).resolve().parents[2];FIG=ROOT/'work/lab11/figures'
font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',28)
for key,panels in PANELS.items():
    if len(panels)==1:
        name,label=panels[0];im=Image.open(FIG/(name+'.png')).convert('RGB')
        bg=Image.new('RGB',im.size,im.getpixel((0,0)))
        mask=ImageChops.difference(im,bg).convert('L').point(lambda v:255 if v>10 else 0)
        box=mask.getbbox()
        if box:
            l,t,r,b=box;im=im.crop((max(0,l-45),max(0,t-45),min(im.width,r+45),min(im.height,b+45)))
        if label:
            out=Image.new('RGB',(im.width,im.height+60),'#e8edf1');out.paste(im,(0,60));ImageDraw.Draw(out).text((out.width/2,25),label,font=font,fill='black',anchor='mm')
        else:out=im
    else:
        w=700;h=500;out=Image.new('RGB',(w*len(panels),h+55),'#e8edf1');d=ImageDraw.Draw(out)
        for j,(name,label) in enumerate(panels):
            im=Image.open(FIG/(name+'.png')).convert('RGB').resize((w,h),Image.Resampling.LANCZOS);out.paste(im,(j*w,55));d.text((j*w+w/2,26),label,font=font,fill='black',anchor='mm')
    out.save(FIG/(key+'.jpg'),quality=93,subsampling=0,optimize=True)
# Выданные фрагменты интерфейса неизменны; убрана только строка с локальным путём.
# Для повторной сборки отчёта берём сохранённые PNG из output, не генерируем интерфейс.
ui=ROOT/'output/lab11/Снимки_интерфейса'
for key in ['ph_push','ph_normals','ph_patch','ph_hair']:
    Image.open(ui/(key+'.png')).convert('RGB').save(FIG/(key+'.jpg'),quality=95,subsampling=0)
preview=Image.new('RGB',(1200,1480),'#f3f4f5');d=ImageDraw.Draw(preview)
titlefont=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf',38)
d.text((600,34),'Лабораторная 11 — Blender',font=titlefont,fill='black',anchor='mm')
tiles=[('push','1. Push'),('edges','2. Stretch'),('bud','3. Собственный бутон'),('pumpkin','4. Тыква-светильник'),('detach','5. Detach'),('tessellate','6. Edit Mesh'),('msmooth','7. Edit Poly'),('cut','8. Cut и Extrude'),('patch','9. Управляемый навес'),('fur','10. Мех и щетина')]
for k,(key,label) in enumerate(tiles):
    x=k%2*600;y=72+k//2*280;im=Image.open(FIG/(key+'.jpg')).convert('RGB');im.thumbnail((570,228))
    preview.paste(im,(x+(600-im.width)//2,y+37));d.text((x+300,y+16),label,font=font,fill='black',anchor='mm')
preview.save(ROOT/'output/lab11/Превью_Лаба11.png')
print('COMPOSE_OK',len(PANELS),'renders, 4 native UI crops')
