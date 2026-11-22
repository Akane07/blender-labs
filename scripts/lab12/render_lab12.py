"""Рендер фактических сцен и самостоятельное JPEG из Blender."""
from pathlib import Path
import bpy,sys,json,time,struct
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab12';FIG=WORK/'figures';FIG.mkdir(parents=True,exist_ok=True);OUT=ROOT/'output/lab12'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Лаба12_Blender.blend'),use_scripts=False)
ONLY=next((set(a.split('=',1)[1].split(',')) for a in sys.argv if a.startswith('--only=')),None);PREVIEW='--preview' in sys.argv
stats=[]
for j in json.loads((WORK/'render_jobs.json').read_text(encoding='utf-8')):
    if ONLY and j['key'] not in ONLY:continue
    s=bpy.data.scenes[j['scene']];bpy.context.window.scene=s
    s.render.resolution_percentage=100;s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(FIG/(('preview_' if PREVIEW else '')+j['key']+'.png'))
    if PREVIEW and s.render.engine=='CYCLES':s.render.engine='BLENDER_EEVEE'
    start=time.perf_counter();bpy.ops.render.render(write_still=True)
    width,height=struct.unpack('>II',Path(s.render.filepath).read_bytes()[16:24])
    stats.append({'key':j['key'],'engine':s.render.engine,'seconds':round(time.perf_counter()-start,3),'width':width,'height':height})
    if j['key']=='02_frame_235' and not PREVIEW:
        # Сохранение реального Render Result в JPEG без повторного рендера.
        s.render.image_settings.file_format='JPEG';s.render.image_settings.color_mode='RGB';s.render.image_settings.quality=95
        bpy.data.images['Render Result'].save_render(str(OUT/'Вестибюль_235.jpg'),scene=s)
    print('DONE',j['key'],flush=True)
(WORK/('preview-stats.json' if PREVIEW else 'render-stats.json')).write_text(json.dumps(stats,indent=2),encoding='utf-8')
print('LAB12_RENDER_OK',flush=True)
