"""ЛР12: опыты с кадром и визуализацией на вестибюле пользователя из ЛР7."""
from pathlib import Path
import bpy,sys,json,hashlib,math
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/lab12';WORK=ROOT/'work/lab12';ASSET=ROOT/'assets/lab12/Вестибюль02_ЛР7.blend'
for p in [OUT,WORK,ASSET.parent]:p.mkdir(parents=True,exist_ok=True)
source_arg=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--source=')),None)
if source_arg:
    original=Path(source_arg);bpy.ops.wm.open_mainfile(filepath=str(original),use_scripts=False)
    src=next(s for s in bpy.data.scenes if s.name.startswith('3 ') and 'Вестибюль' in s.name);bpy.context.window.scene=src
    bpy.data.libraries.write(str(ASSET),{src},compress=True)
    (WORK/'source-provenance.json').write_text(json.dumps({'original_file':'Лаба7_Blender.blend','sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scene':src.name,'asset':str(ASSET.relative_to(ROOT))},ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.open_mainfile(filepath=str(ASSET),use_scripts=False)
src=next(s for s in bpy.data.scenes if 'Вестибюль' in s.name);bpy.context.window.scene=src;bpy.context.view_layer.update()
for other in list(bpy.data.scenes):
    if other!=src:bpy.data.scenes.remove(other)
if source_arg:bpy.ops.wm.save_as_mainfile(filepath=str(ASSET),compress=True)
source_world=src.world;source_camera=src.camera
geometry=[c for c in src.collection.children if c.name in ['Вестибюль (задание 3)','Портик — зеркальная копия (задание 13)','Деревья (задание 12)']]
assert len(geometry)==3
source_stages=next(c for c in src.collection.children if 'Этапы' in c.name)
ground=bpy.data.objects['Земля — вестибюль'];suns=[o for o in src.objects if o.type=='LIGHT']
selected=[bpy.data.objects[n] for n in ['Основание Box01','Цилиндр Cylinder01','Купол Sphere01']]
target=bpy.data.objects['Купол Sphere01']
original_objects=[o for c in geometry for o in c.objects]
def signature(ob):
    d={'name':ob.name,'type':ob.type,'matrix':[list(r) for r in ob.matrix_world],'modifiers':[{'name':m.name,'type':m.type} for m in ob.modifiers]}
    if ob.type=='MESH':
        payload={'vertices':[list(v.co) for v in ob.data.vertices],'polygons':[list(p.vertices) for p in ob.data.polygons]}
        d.update(vertices=len(ob.data.vertices),faces=len(ob.data.polygons),mesh_sha256=hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest())
    return d
baseline=[signature(o) for o in original_objects]
(WORK/'source-geometry.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
ground_col=bpy.data.collections.new('Земля из ЛР7');ground_col.objects.link(ground)
light_col=bpy.data.collections.new('Освещение из ЛР7')
for o in suns:light_col.objects.link(o)
SCENES=[];JOBS=[]
def scene(n,title,engine='CYCLES',lit=True,old_ground=True,isolated=False):
    s=bpy.data.scenes.new(f'{n:02d} — {title}');bpy.context.window.scene=s
    s.unit_settings.system='METRIC';s.render.engine=engine;s.render.resolution_x=1175;s.render.resolution_y=500;s.render.resolution_percentage=100
    s.render.pixel_aspect_x=s.render.pixel_aspect_y=1;s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    s.render.filepath='//Рендер_'+str(n)+'.png';s.render.film_transparent=False;s.frame_start=s.frame_end=1;s.frame_set(1)
    s.cycles.samples=40;s.cycles.preview_samples=16;s.cycles.use_denoising=True;s.cycles.seed=12
    s.world=source_world.copy();s.world.name='Мир — '+title
    if not lit:
        s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=0
    s.view_settings.view_transform='AgX';s.view_settings.exposure=0
    if isolated:
        c=bpy.data.collections.new('Только выбранные объекты');s.collection.children.link(c)
        for o in selected:c.objects.link(o)
        s.render.film_transparent=True
    else:
        for c in geometry:s.collection.children.link(c)
    if old_ground:s.collection.children.link(ground_col)
    if lit:s.collection.children.link(light_col)
    stage=bpy.data.collections.new('Этапы '+str(n)+' (скрыто)');stage.hide_render=True;stage.children.link(source_stages);s.collection.children.link(stage)
    s.view_layers[0].layer_collection.children[stage.name].exclude=True
    cam=source_camera.copy();cam.data=source_camera.data.copy();cam.name='Камера — '+title;cam.data.type='PERSP';cam.data.sensor_fit='HORIZONTAL';cam.data.sensor_width=36;cam.data.lens=40;cam.data.shift_x=cam.data.shift_y=0
    cam.matrix_world=source_camera.matrix_world.copy();s.collection.objects.link(cam);s.camera=cam
    cam.data.show_passepartout=True;cam.data.passepartout_alpha=.85;cam.data.clip_start=.01;cam.data.clip_end=1000
    for o in s.objects:o.select_set(False)
    target.select_set(True);s.view_layers[0].objects.active=target
    cam.hide_set(True)
    if 'Дерево (образец, American Elm)' in s.objects:bpy.data.objects['Дерево (образец, American Elm)'].hide_set(True)
    for o in suns:
        if o.name in s.objects:o.hide_set(True)
    s['Номер лабораторной']=12;s['Номер опыта']=n;s['Источник']='Вестибюль02 из сцены 3 лабораторной 7 пользователя';s['Методичка']='12.docx, внутренний №17'
    SCENES.append({'number':n,'scene':s.name,'engine':engine});return s
def job(key,s):JOBS.append({'key':key,'scene':s.name})
s1=scene(1,'Исходный кадр 4 к 3');s1.render.resolution_x=1000;s1.render.resolution_y=750;job('01_frame_43',s1)
s2=scene(2,'Широкий кадр 2.35 к 1');s2.render.image_settings.file_format='JPEG';s2.render.image_settings.color_mode='RGB';s2.render.image_settings.quality=95;s2.render.filepath='//Вестибюль_235.jpg';job('02_frame_235',s2)
s3=scene(3,'Selected — только выбранное',old_ground=False,isolated=True);job('03_selected',s3)
# Общая квадратная в нормированных координатах рамка, сохраняющая 2.35:1.
bpy.context.window.scene=s2;bpy.context.view_layer.update()
ev=target.evaluated_get(bpy.context.evaluated_depsgraph_get());points=[target.matrix_world@Vector(v) for v in ev.bound_box];uv=[world_to_camera_view(s2,s2.camera,p) for p in points]
cx=(min(p.x for p in uv)+max(p.x for p in uv))/2;cy=(min(p.y for p in uv)+max(p.y for p in uv))/2;f=.44
cx=max(f/2,min(1-f/2,cx));cy=max(f/2,min(1-f/2,cy));border=(cx-f/2,cx+f/2,cy-f/2,cy+f/2)
def set_border(s,box,crop=False):
    s.render.use_border=True;s.render.use_crop_to_border=crop;s.render.border_min_x,s.render.border_max_x,s.render.border_min_y,s.render.border_max_y=box
s4=scene(4,'Region — полный размер');set_border(s4,border);job('04_region',s4)
s5=scene(5,'Crop — размер области');set_border(s5,border,True);job('05_crop',s5)
s6=scene(6,'Blowup — крупный план')
# Подбираем lens и shift по реальной проекции камеры. Это новый рендер детали,
# а не увеличение готового растрового изображения.
frame=s2.camera.data.view_frame(scene=s2);local=Vector((min(v.x for v in frame)+cx*(max(v.x for v in frame)-min(v.x for v in frame)),min(v.y for v in frame)+cy*(max(v.y for v in frame)-min(v.y for v in frame)),frame[0].z))
pivot=s2.camera.matrix_world@local;s6.camera.data.lens=s2.camera.data.lens/f
for field,axis in [('shift_x',0),('shift_y',1)]:
    setattr(s6.camera.data,field,0);v0=world_to_camera_view(s6,s6.camera,pivot)[axis];setattr(s6.camera.data,field,.01);v1=world_to_camera_view(s6,s6.camera,pivot)[axis];setattr(s6.camera.data,field,.01*(.5-v0)/(v1-v0))
s6['Рамка в исходном кадре']=json.dumps(border);job('06_blowup',s6)
s7=scene(7,'Auto Region Selected')
auto=(max(0,min(p.x for p in uv)-.025),min(1,max(p.x for p in uv)+.025),max(0,min(p.y for p in uv)-.025),min(1,max(p.y for p in uv)+.025));set_border(s7,auto)
s7['Автоматическая область']='Габарит Купол Sphere01, спроецированный на камеру, плюс 0.025 с каждой стороны';job('07_auto_region',s7)
s8=scene(8,'Front — предпросмотр',engine='BLENDER_EEVEE')
s8.camera.data.type='ORTHO';s8.camera.data.ortho_scale=3.7;s8.camera.location=(0,-6,.4);s8.camera.rotation_euler=(Vector((0,0,.4))-s8.camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();job('08_front',s8)
s9=scene(9,'Без света — EEVEE',engine='BLENDER_EEVEE',lit=False);job('09_unlit_eevee',s9)
s10=scene(10,'Без света — Cycles без переотражений',lit=False);s10.cycles.max_bounces=0;s10.cycles.diffuse_bounces=0;job('10_unlit_direct',s10)
s11=scene(11,'Без света — Cycles с переотражениями',lit=False);s11.cycles.max_bounces=8;s11.cycles.diffuse_bounces=4;job('11_unlit_gi',s11)
s12=scene(12,'Вестибюль03 — Plane и студийный свет',engine='BLENDER_WORKBENCH',lit=False,old_ground=False)
bpy.context.window.scene=s12;bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,-.01));plane=bpy.context.object;plane.name='Plane — земля лабораторной 12';plane.data.materials.append(ground.data.materials[0]);plane['Назначение']='Новый стандартный Plane вместо старой земли ЛР7; старое основание сохранено в других сценах и исходнике'
sh=s12.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=True;sh.background_type='WORLD'
s12['Advanced Lighting']='Плагинов Radiosity/Light Tracer в Blender нет. Workbench Studio — аналог условного студийного освещения без объектов Light, не расчёт GI.';job('12_plane_studio',s12)
s13=scene(13,'Со светом — Cycles без переотражений');s13.cycles.max_bounces=0;s13.cycles.diffuse_bounces=0;job('13_lit_direct',s13)
s14=scene(14,'Со светом — Cycles с переотражениями');s14.cycles.max_bounces=8;s14.cycles.diffuse_bounces=4;job('14_lit_gi',s14)
# Чистый файл конечного этапа, как Вестибюль03 из методички.
bpy.context.window.scene=s12;bpy.data.libraries.write(str(OUT/'Вестибюль03_Blender.blend'),{s12},compress=True)
# Не включаем в лабораторную другие сцены исходной ЛР7.
bpy.data.scenes.remove(src)
txt=bpy.data.texts.new('ПРОЧТИ — лабораторная 12');txt.write('Лабораторная 12. Источник: сцена 3 — Вестибюль из ЛР7 пользователя.\n01/02 — один ракурс, разные пропорции 4:3 и 2.35:1.\n03 — Selected; 04/05 — одна рамка Region/Crop; 06 — крупный план новой камерой; 07 — область по габариту выбранного купола.\n08 — фронтальный предпросмотр; 09–11 — отсутствие света и чёрные результаты; 12 — новый Plane и Workbench Studio; 13/14 — дополнительное сравнение отражённого света.\nF12 — рендер активной камеры, F11 — последний результат. F9 не повторяет рендер, это параметры последней операции.\nИсходные два Солнца сохранены в освещённых опытах. В 09–12 объектов Light нет.\nRadiosity, Light Tracer и старый Raytracer 3ds Max здесь не запускались. Аналоги и ограничения описаны в отчёте.\nОткрытие не требует Auto Run Python Scripts.\n')
bpy.context.window.scene=s2
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_end=1000
        elif a.type=='PROPERTIES':a.spaces.active.context='OUTPUT'
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Лаба12_Blender.blend'),compress=True)
(WORK/'scenes.json').write_text(json.dumps(SCENES,ensure_ascii=False,indent=2),encoding='utf-8');(WORK/'render_jobs.json').write_text(json.dumps(JOBS,ensure_ascii=False,indent=2),encoding='utf-8');(WORK/'regions.json').write_text(json.dumps({'manual':border,'auto':auto,'selected':[o.name for o in selected],'source_camera_type':source_camera.data.type},ensure_ascii=False,indent=2),encoding='utf-8')
# Library write переносит зависимости, но не активное окно. Нормализуем конечный
# отдельный файл, чтобы двойной щелчок сразу открывал нужную сцену.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Вестибюль03_Blender.blend'),use_scripts=False)
final=next(s for s in bpy.data.scenes if s.name.startswith('12 '));bpy.context.window.scene=final
for other in list(bpy.data.scenes):
    if other!=final:bpy.data.scenes.remove(other)
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Вестибюль03_Blender.blend'),compress=True)
print('LAB12_BUILD_OK',len(SCENES),'scenes',flush=True)
