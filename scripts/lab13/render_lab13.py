"""Иллюстрации из настоящих сцен, без изменения сохранённых .blend."""
from pathlib import Path
import bpy,json,time,sys,struct
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab13';FIG=WORK/'figures';FIG.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab13/Лаба13_Blender.blend'),use_scripts=False)
ONLY=next((set(x.split('=',1)[1].split(',')) for x in sys.argv if x.startswith('--only=')),None);PREVIEW='--preview' in sys.argv;stats=[]
for j in json.loads((WORK/'render_jobs.json').read_text(encoding='utf-8')):
    if ONLY and j['key'] not in ONLY:continue
    s=bpy.data.scenes[j['scene']];bpy.context.window.scene=s;bpy.context.view_layer.update()
    s.render.resolution_percentage=40 if PREVIEW else 100
    if PREVIEW:s.cycles.samples=16
    s.render.filepath=str(FIG/(('preview_' if PREVIEW else '')+j['key']+'.png'));start=time.perf_counter();bpy.ops.render.render(write_still=True)
    w,h=struct.unpack('>II',Path(s.render.filepath).read_bytes()[16:24]);stats.append({'key':j['key'],'engine':s.render.engine,'seconds':round(time.perf_counter()-start,3),'width':w,'height':h});print('DONE',j['key'],flush=True)
(WORK/('preview-stats.json' if PREVIEW else 'render-stats.json')).write_text(json.dumps(stats,indent=2),encoding='utf-8');print('LAB13_RENDER_OK',flush=True)
