"""Компоновка настоящих рендеров и уже обрезанных снимков интерфейса."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from lab13_content import PANELS,UI
ROOT=Path(__file__).resolve().parents[2];FIG=ROOT/'work/lab13/figures';OUT=ROOT/'output/lab13'
font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',26)
for key,panels in PANELS.items():
    cols=2 if len(panels)>1 else 1;rows=(len(panels)+cols-1)//cols
    w=680 if cols==2 else 1000
    square=key in {'shadows','lightview'};hh=w if square else round(w*.75)
    canvas=Image.new('RGB',(w*cols,(hh+50)*rows),'#edf0f2');d=ImageDraw.Draw(canvas)
    for i,(code,label) in enumerate(panels):
        im=Image.open(FIG/(code+'.png')).convert('RGB');im.thumbnail((w,hh),Image.Resampling.LANCZOS)
        x=(i%cols)*w;y=(i//cols)*(hh+50);canvas.paste(im,(x+(w-im.width)//2,y+50+(hh-im.height)//2))
        ff=font
        for sz in range(26,17,-1):
            ff=ImageFont.truetype('C:/Windows/Fonts/times.ttf',sz)
            if d.textbbox((0,0),label,font=ff)[2]<w-20:break
        d.text((x+w/2,y+25),label,font=ff,fill='black',anchor='mm')
    canvas.save(FIG/(key+'.jpg'),quality=96,subsampling=0)
for key in UI:
    Image.open(OUT/'Снимки_интерфейса'/(key+'.png')).convert('RGB').save(FIG/(key+'.jpg'),quality=97,subsampling=0)
canvas=Image.new('RGB',(1600,720),'#edf0f2');d=ImageDraw.Draw(canvas)
ff=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf',39);d.text((800,34),'Лабораторная 13 — управление светом',font=ff,fill='black',anchor='mm')
d.text((800,81),'10 заданий на исходном вестибюле пользователя',font=font,fill='black',anchor='mm')
for i,code in enumerate(['08c','09']):
    im=Image.open(FIG/(code+'.png')).convert('RGB').resize((800,600),Image.Resampling.LANCZOS);canvas.paste(im,(i*800,120))
canvas.save(OUT/'Превью_Лаба13.png')
print('COMPOSE_OK',len(PANELS),'render figures',len(UI),'native UI')
