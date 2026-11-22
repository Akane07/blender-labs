"""Проверка сохранённых данных, проекции и неизменности геометрии ЛР7."""
from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab12';OUT=ROOT/'output/lab12'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Лаба12_Blender.blend'),use_scripts=False)
R={'version':bpy.app.version_string,'checks':[],'measurements':{}}
def check(name,ok,details=None):
    R['checks'].append({'check':name,'ok':bool(ok),'details':details})
    if not ok:print('FAILED',name,details,flush=True)
def sc(n):
    s=next(s for s in bpy.data.scenes if s.get('Номер опыта')==n);bpy.context.window.scene=s;bpy.context.view_layer.update();return s
check('14 опытов без лишней пустой сцены',len(bpy.data.scenes)==14,len(bpy.data.scenes))
for s in bpy.data.scenes:
    bpy.context.window.scene=s
    st=next(c for c in s.collection.children if c.name.startswith('Этапы'))
    check(s.name+' — этапы скрыты',st.hide_render and s.view_layers[0].layer_collection.children[st.name].exclude)
    check(s.name+' — камера и относительный путь',s.camera and s.camera.data.clip_end>=100 and s.render.filepath.startswith('//'))
    check(s.name+' — номер и один кадр',s.get('Номер лабораторной')==12 and s.frame_current==1 and s.frame_start==s.frame_end==1)
    check(s.name+' — нет текстовых драйверов',all(not o.animation_data or all(d.driver.is_simple_expression for d in o.animation_data.drivers) for o in s.objects))
baseline=json.loads((WORK/'source-geometry.json').read_text(encoding='utf-8'));sc(1)
check('Образец дерева скрыт в окне',bpy.data.objects['Дерево (образец, American Elm)'].hide_get())
for item in baseline:
    ob=bpy.data.objects[item['name']]
    check(ob.name+' — преобразования сохранены',max(abs(a-b) for row1,row2 in zip(item['matrix'],ob.matrix_world) for a,b in zip(row1,row2))<1e-7)
    if ob.type=='MESH':
        p={'vertices':[list(v.co) for v in ob.data.vertices],'polygons':[list(p.vertices) for p in ob.data.polygons]};h=hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()
        check(ob.name+' — исходный меш сохранён',h==item['mesh_sha256'],h)
        check(ob.name+' — конечная геометрия не пуста',len(ob.data.vertices)>0 and len(ob.data.polygons)>0)
path=bpy.data.objects['П-образный путь (Line)'];instances=[i for i in bpy.context.evaluated_depsgraph_get().object_instances if i.is_instance and i.parent and i.parent.original==path]
check('12 деревьев исходной сцены вычисляются без скриптов',len(instances)==12,len(instances));R['measurements']['trees']=len(instances)
a=sc(1);b=sc(2)
check('4 к 3',a.render.resolution_x/a.render.resolution_y==4/3)
check('2.35 к 1 и квадратные пиксели',b.render.resolution_x/b.render.resolution_y==2.35 and b.render.pixel_aspect_x==b.render.pixel_aspect_y==1)
check('JPEG RGB с качеством 95 сохранён в настройках',b.render.image_settings.file_format=='JPEG' and b.render.image_settings.color_mode=='RGB' and b.render.image_settings.quality==95 and b.render.filepath=='//Вестибюль_235.jpg')
check('Один ракурс и оптика у двух форматов',all(abs(x-y)<1e-7 for ra,rb in zip(a.camera.matrix_world,b.camera.matrix_world) for x,y in zip(ra,rb)) and a.camera.data.lens==b.camera.data.lens)
visible={o.name for o in sc(3).objects if o.type in ['MESH','CURVE'] and not o.hide_render and not any(c.hide_render for c in o.users_collection)}
check('Selected содержит только три выбранных меша',visible=={'Основание Box01','Цилиндр Cylinder01','Купол Sphere01'},list(visible));check('Selected создаёт прозрачный фон',sc(3).render.film_transparent)
r=sc(4);c=sc(5);box=lambda s:[s.render.border_min_x,s.render.border_max_x,s.render.border_min_y,s.render.border_max_y]
check('Region и Crop имеют одну рамку',box(r)==box(c));check('Region сохраняет холст, Crop обрезает',r.render.use_border and not r.render.use_crop_to_border and c.render.use_border and c.render.use_crop_to_border)
blow=sc(6);base=sc(2);border=box(r);fx=border[1]-border[0];fy=border[3]-border[2]
errors=[]
for name in ['Основание Box01','Цилиндр Cylinder01','Купол Sphere01']:
    ob=bpy.data.objects[name]
    for co in ob.bound_box:
        p=ob.matrix_world@Vector(co);uv=world_to_camera_view(base,base.camera,p);zoom=world_to_camera_view(blow,blow.camera,p);errors.extend([abs(zoom.x-(uv.x-border[0])/fx),abs(zoom.y-(uv.y-border[2])/fy)])
check('Blowup проецирует область на полный кадр',max(errors)<1e-4,max(errors));check('Blowup — новая оптика с прежним размером',blow.camera.data.lens>base.camera.data.lens and blow.render.resolution_x==base.render.resolution_x and not blow.render.use_border);R['measurements']['blowup_projection_error']=max(errors)
auto=sc(7);ob=bpy.data.objects['Купол Sphere01'];uv=[world_to_camera_view(auto,auto.camera,ob.matrix_world@Vector(v)) for v in ob.bound_box];bb=box(auto)
check('Auto Region покрывает выбранный купол с запасом',all(bb[0]<p.x<bb[1] and bb[2]<p.y<bb[3] for p in uv));R['measurements']['manual_border']=box(r);R['measurements']['auto_border']=bb
check('Front ортографический',sc(8).camera.data.type=='ORTHO')
for n in [9,10,11,12]:
    s=sc(n);check(s.name+' — нет объектов Light',not any(o.type=='LIGHT' for o in s.objects));check(s.name+' — World не излучает',s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value==0)
check('Контрольные режимы различаются',sc(9).render.engine=='BLENDER_EEVEE' and sc(10).cycles.max_bounces==0 and sc(11).cycles.diffuse_bounces==4)
check('Освещённые опыты сохраняют два источника ЛР7',all(len([o for o in sc(n).objects if o.type=='LIGHT'])==2 for n in [1,2,13,14]))
s=sc(12);plane=bpy.data.objects['Plane — земля лабораторной 12'];check('Новый Plane — стандартная плоскость из одной грани',len(plane.data.vertices)==4 and len(plane.data.polygons)==1 and abs(plane.location.z+.01)<1e-6);check('Две земли не накладываются',bpy.data.objects['Земля — вестибюль'].name not in s.objects);check('Workbench использует Studio',s.render.engine=='BLENDER_WORKBENCH' and s.display.shading.light=='STUDIO')
check('Внешние изображения упакованы',all(i.packed_file or i.source!='FILE' for i in bpy.data.images))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Вестибюль03_Blender.blend'),use_scripts=False)
check('Отдельный Вестибюль03 сразу открывается нужной сценой',len(bpy.data.scenes)==1 and bpy.context.scene.get('Номер опыта')==12)
check('Отдельный файл содержит Plane и камеру',bpy.context.scene.camera and 'Plane — земля лабораторной 12' in bpy.context.scene.objects)
R['passed']=all(x['ok'] for x in R['checks']);(WORK/'model-qa.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':R['passed'],'checks':len(R['checks']),'measurements':R['measurements']},ensure_ascii=False),flush=True)
if not R['passed']:raise RuntimeError('ЛР12: проверка не пройдена')
