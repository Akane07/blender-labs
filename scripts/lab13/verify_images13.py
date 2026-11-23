"""Проверка размеров кадров и реально изменившегося освещения."""
from pathlib import Path
from PIL import Image
import numpy as np,json
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab13';FIG=WORK/'figures';jobs=json.loads((WORK/'render_jobs.json').read_text(encoding='utf-8'))
checks=[];arrays={};measurements={}
def check(name,ok,details=None):checks.append({'check':name,'ok':bool(ok),'details':details})
for job in jobs:
    k=job['key'];im=Image.open(FIG/(k+'.png'));check(k+' размер кадра',im.size==(1000,1000 if k.startswith('02') or k=='10' else 750));a=np.array(im.convert('RGB'),dtype=float);arrays[k]=a
    measurements[k]={'mean_rgb':a.mean(axis=(0,1)).tolist(),'size':list(im.size)};check(k+' освещённая геометрия',float(a.std())>15)
check('Множитель 1.5 повышает яркость',arrays['01b'].mean()>arrays['01a'].mean())
for a,b,label in [('01b','01c','Исключение теней деревьев'),('02a','02b','Другой алгоритм теней'),('02a','02d','Мягкие тени'),('08b','08c','Исключение цилиндра из света')]:
    delta=float(np.abs(arrays[a]-arrays[b]).mean());measurements[label]=delta;check(label+' меняет пиксели',delta>.005,delta)
building=arrays['04b'][330:470,400:650];check('Синий оттенок строения',building[:,:,2].mean()>building[:,:,0].mean()*1.15)
check('Far темнит дальнюю часть сцены',arrays['05'][160:270,400:650].mean()<arrays['01a'][160:270,400:650].mean())
check('Тёплое освещение неба',arrays['09'][:,:,0].mean()>arrays['09'][:,:,2].mean()*1.7)
r={'passed':all(x['ok'] for x in checks),'checks':checks,'measurements':measurements};(WORK/'pixel-qa.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print('PIXEL_QA',r['passed'],len(checks));assert r['passed']
