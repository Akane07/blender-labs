"""Проверка фактических файлов рендера, размеров и контрольных опытов."""
from pathlib import Path
import json
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab12';FIG=WORK/'figures';records=[]
for path in sorted(FIG.glob('[0-9]*.png')):
    im=Image.open(path).convert('RGBA');a=np.asarray(im)
    records.append({'key':path.stem,'size':list(im.size),'rgb_min':int(a[:,:,:3].min()),'rgb_max':int(a[:,:,:3].max()),'mean_rgb':float(a[:,:,:3].mean()),'alpha_nonzero':int((a[:,:,3]>0).sum()),'alpha_zero':int((a[:,:,3]==0).sum())})
by={r['key']:r for r in records}
assert len(records)==14
for key in ['09_unlit_eevee','10_unlit_direct','11_unlit_gi']:
    assert by[key]['rgb_max']<=3 and by[key]['mean_rgb']<.1
assert by['04_region']['size']==[1175,500] and by['05_crop']['size']==[517,220]
assert by['04_region']['alpha_zero']>400000 and by['05_crop']['alpha_zero']==0
assert by['03_selected']['alpha_zero']>0 and by['03_selected']['rgb_max']>100
assert by['06_blowup']['size']==[1175,500]
a=np.asarray(Image.open(FIG/'13_lit_direct.png').convert('RGB'),dtype=float)
b=np.asarray(Image.open(FIG/'14_lit_gi.png').convert('RGB'),dtype=float)
difference=float(np.abs(a-b).mean());assert difference>.1
jpeg=Image.open(ROOT/'output/lab12/Вестибюль_235.jpg')
assert jpeg.format=='JPEG' and jpeg.size==(1175,500) and jpeg.mode=='RGB'
result={'passed':True,'renders':records,'lit_mean_absolute_difference_8bit':difference,'jpeg':{'format':jpeg.format,'size':list(jpeg.size),'mode':jpeg.mode}}
(WORK/'pixel-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('IMAGE_QA_OK',len(records),'renders; RGB JPEG;',round(difference,6),'lit difference')
