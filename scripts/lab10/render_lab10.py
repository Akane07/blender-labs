"""Действительные рендеры сохранённого .blend; временный каркас не меняет файл."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab10';FIG=WORK/'figures';FIG.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab10/Лаба10_Blender.blend'),use_scripts=False)
ONLY=next((set(a.split('=',1)[1].split(',')) for a in sys.argv if a.startswith('--only=')),None)
PREVIEW='--preview' in sys.argv
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1);return m
grey=material('Серый материал иллюстрации',(.42,.45,.5));black=material('Чёрный каркас',(.012,.02,.03))
def fit(s,items,view):
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[ob.matrix_world@Vector(v) for ob in items for v in ob.evaluated_get(dg).bound_box]
 lo=Vector([min(p[j] for p in points) for j in range(3)]);hi=Vector([max(p[j] for p in points) for j in range(3)]);target=(lo+hi)/2
 s.camera.location=target+Vector(view).normalized()*max((hi-lo).length*3,5);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 inv=s.camera.matrix_world.inverted();local=[inv@p for p in points];width=max(p.x for p in local)-min(p.x for p in local);height=max(p.y for p in local)-min(p.y for p in local);s.camera.data.ortho_scale=max(width,height*1.4)*1.18
 if len(items)==1 and 'узлы радиус' in items[0].name:
  target=items[0].location+Vector((0,0,.25));s.camera.location=target+Vector(view).normalized()*5;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=1.9 if items[0].name.startswith('03') else 1.35
 return max((hi-lo).length,.1)
for job in json.loads((WORK/'render_jobs.json').read_text(encoding='utf-8')):
 if ONLY and job['key'] not in ONLY:continue
 s=bpy.data.scenes[job['scene']];bpy.context.window.scene=s;s.frame_set(1)
 for c in s.collection.children:c.hide_render=False;s.view_layers[0].layer_collection.children[c.name].exclude=False
 allowed=set(job['objects']);items=[bpy.data.objects[x] for x in allowed]
 for ob in s.objects:
  if ob.type in ['MESH','CURVE','FONT']:ob.hide_render=ob.name not in allowed
 dim=fit(s,items,job['view']);temporary=[]
 for ob in items:
  is_stage=any(c.name.startswith('Этапы') for c in ob.users_collection)
  if is_stage and 'узлы' not in ob.name:
   ob.data.materials.clear();ob.data.materials.append(grey)
   for p in ob.data.polygons:p.material_index=0
  if (is_stage and 'узлы' not in ob.name and 'Iterations' not in ob.name) or job['key']=='24_optimize':
   dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
   if len(me.vertices)<20000:
    me.materials.clear();me.materials.append(black);wire=bpy.data.objects.new('Каркас рисунка',me);s.collection.objects.link(wire);wire.matrix_world=ob.matrix_world.copy();md=wire.modifiers.new('Каркас','WIREFRAME');md.thickness=dim*.0007;md.offset=1;temporary.append(wire)
 s.render.engine='BLENDER_EEVEE' if PREVIEW else 'CYCLES';s.cycles.device='CPU';s.cycles.samples=40;s.cycles.use_denoising=True
 s.render.resolution_x=1000 if PREVIEW else 1400;s.render.resolution_y=714 if PREVIEW else 1000;s.render.resolution_percentage=100
 s.render.filepath=str(FIG/(('preview_' if PREVIEW else '')+job['key']+'.png'));bpy.ops.render.render(write_still=True)
 for ob in temporary:bpy.data.objects.remove(ob,do_unlink=True)
 print('DONE',job['key'],flush=True)
print('LAB10_RENDER_OK',flush=True)
