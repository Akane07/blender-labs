"""Действительные рендеры сохранённого .blend; временный каркас не меняет файл."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab11';FIG=WORK/'figures';FIG.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab11/Лаба11_Blender.blend'),use_scripts=False)
ONLY=next((set(a.split('=',1)[1].split(',')) for a in sys.argv if a.startswith('--only=')),None)
PREVIEW='--preview' in sys.argv
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1);return m
grey=material('Серый материал иллюстрации',(.42,.45,.5));black=material('Чёрный каркас',(.012,.02,.03));orange=material('Маркеры выделения',(.95,.15,.025))
def fit(s,items,view):
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[ob.matrix_world@Vector(v) for ob in items for v in ob.evaluated_get(dg).bound_box]
 lo=Vector([min(p[j] for p in points) for j in range(3)]);hi=Vector([max(p[j] for p in points) for j in range(3)]);target=(lo+hi)/2
 s.camera.location=target+Vector(view).normalized()*max((hi-lo).length*3,5);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 inv=s.camera.matrix_world.inverted();local=[inv@p for p in points];width=max(p.x for p in local)-min(p.x for p in local);height=max(p.y for p in local)-min(p.y for p in local);s.camera.data.ortho_scale=max(width,height*1.4)*1.18
 return max((hi-lo).length,.1)
WIRE={'01_push_selection','03_edges_top','05_faces_selection','07_pumpkin_mesh','09_detach','10_extrude_group','11_extrude_local','12_bevel','13a_weld_before','13_weld','14_tessellate','15a_msmooth_before','15_msmooth','16_grow','17_grow9','18_grow25','19_flip_collapse','20_planar','21_cut','22_cut_extrude'}
for job in json.loads((WORK/'render_jobs.json').read_text(encoding='utf-8')):
 if ONLY and job['key'] not in ONLY:continue
 s=bpy.data.scenes[job['scene']];bpy.context.window.scene=s;s.frame_set(1)
 for c in s.collection.children:c.hide_render=False;s.view_layers[0].layer_collection.children[c.name].exclude=False
 allowed=set(job['objects']);items=[bpy.data.objects[x] for x in allowed]
 items=[bpy.data.objects[x] for x in job['objects']]
 if job['key'] in ['19_flip_collapse','20_planar']:
  for k,ob in enumerate(items):ob.location=((k-(len(items)-1)/2)*1.25,0,0)
 for ob in s.objects:
  if ob.type in ['MESH','CURVE','FONT','SURFACE','CURVES']:ob.hide_render=ob.name not in allowed
 dim=fit(s,items,job['view']);temporary=[]
 if job['key']=='14_tessellate':
  # Нижний опыт Face Center должен читаться так же ясно, как верхний Edge.
  light=bpy.data.lights.new('Фронтальный свет сетки','SUN');light.energy=1.5;light.angle=.4
  lamp=bpy.data.objects.new('Фронтальный свет сетки',light);s.collection.objects.link(lamp);lamp.rotation_euler=s.camera.rotation_euler.copy();temporary.append(lamp)
  items[0].data.materials[0]=grey
 if job['key'] in ['25_fur_dense','26_hair_bristle']:
  target=Vector((0,0,0));s.camera.location=target+Vector(job['view']).normalized()*5;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=2.9 if job['key']=='25_fur_dense' else 1.8
 if job['key']=='23_patch_controls':
  target=Vector((0,0,1.2));s.camera.location=target+Vector(job['view']).normalized()*5;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=2.6
  surface=next(o for o in items if o.type=='SURFACE')
  for point in surface.data.splines[0].points:
   bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.018,location=surface.matrix_world@point.co.xyz);marker=bpy.context.object;marker.data.materials.append(orange);temporary.append(marker)
 if job['key'].startswith(('13','15')):
  target=items[0].location+Vector((0,-.1,.49) if job['key'].startswith('13') else (0,-.43,.23));s.camera.location=target+Vector(job['view']).normalized()*4;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=.3 if job['key'].startswith('13') else .36;dim=.45
 for ob in items:
  is_stage=any(c.name.startswith('Этапы') for c in ob.users_collection)
  if is_stage and ob.type=='MESH' and job['key']!='25_fur_dense':
   if ob.data.materials:ob.data.materials[0]=grey
   else:ob.data.materials.append(grey)
  if ob.type=='MESH' and job['key'] in WIRE:
   dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
   if len(me.vertices)<20000:
    me.materials.clear();me.materials.append(black);wire=bpy.data.objects.new('Каркас рисунка',me);s.collection.objects.link(wire);wire.matrix_world=ob.matrix_world.copy();md=wire.modifiers.new('Каркас','WIREFRAME');md.thickness=dim*.0007;md.offset=1;temporary.append(wire)
  if job['key']=='03_edges_top':
   selected=json.loads(ob['Выделенные рёбра']);cv=bpy.data.curves.new('Выбранные рёбра','CURVE');cv.dimensions='3D';cv.bevel_depth=.002;cv.bevel_resolution=2
   for index in selected:
    sp=cv.splines.new('POLY');sp.points.add(1)
    for point,vid in zip(sp.points,ob.data.edges[index].vertices):point.co=(*(ob.data.vertices[vid].co*1.005),1)
   marker=bpy.data.objects.new('Цвет выбранных рёбер',cv);s.collection.objects.link(marker);marker.matrix_world=ob.matrix_world.copy();cv.materials.append(orange);temporary.append(marker)
  if job['key'].startswith('13'):
   ids=json.loads(ob['Контрольные вершины']) if 'Контрольные вершины' in ob else [min(ob.data.vertices,key=lambda v:(v.co-Vector((0,-.0975,.4904))).length).index]
   for index in ids:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.0045,location=ob.matrix_world@ob.data.vertices[index].co);marker=bpy.context.object;marker.data.materials.append(orange);temporary.append(marker)
  if job['key']=='01_push_selection':
   for vertex in ob.data.vertices:
    if vertex.select:
     bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.007,location=ob.matrix_world@vertex.co);marker=bpy.context.object;marker.data.materials.append(orange);temporary.append(marker)
 s.render.engine='BLENDER_EEVEE' if PREVIEW else 'CYCLES';s.cycles.device='CPU';s.cycles.samples=40;s.cycles.use_denoising=True
 s.render.resolution_x=1000 if PREVIEW else 1400;s.render.resolution_y=714 if PREVIEW else 1000;s.render.resolution_percentage=100
 s.render.filepath=str(FIG/(('preview_' if PREVIEW else '')+job['key']+'.png'));bpy.ops.render.render(write_still=True)
 for ob in temporary:bpy.data.objects.remove(ob,do_unlink=True)
 print('DONE',job['key'],flush=True)
print('LAB11_RENDER_OK',flush=True)
