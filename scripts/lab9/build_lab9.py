"""Сборка лабораторной 9. Запуск через Blender 5.2 --background --python."""
import bpy, bmesh, math, sys, json, shutil
from pathlib import Path
from mathutils import Vector, Euler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(Path(__file__).parent))
from lab4_common import principled, add_camera, add_light, world, curve_object
from lab9_nodes import taper_group, struts_group, skew_group, add_nodes, set_input, link_property, reference_group

OUT=ROOT/'output/lab9';OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/'work/lab9';QA.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

BLUE=principled('Синий — исходная геометрия','277BB2',rough=.36,metallic=.12)
ORANGE=principled('Оранжевый — выбранная часть','EE9435',rough=.36,metallic=.08)
GREEN=principled('Бирюзовый — объект-ссылка','30A492',rough=.36,metallic=.15)
BRONZE=principled('Корзина — матовые стержни','AD7538',rough=.43,metallic=.32)
GREY=principled('Серый — этап','9BA4B0',rough=.6)
ROPE=principled('Подвесы — светлый шнур','E4CEAB',rough=.68)
PANEL=[principled('Оболочка — '+n,c,rough=.5) for n,c in [('красный','C9503D'),('золотой','E9B341'),('молочный','E5DDC9'),('синий','337FA3')]]

def collection(sc,name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);return c

def mesh(name,verts,faces,col,edges=()):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,edges,faces);me.update()
    ob=bpy.data.objects.new(name,me);col.objects.link(ob);return ob

def empty(name,col,location=(0,0,0)):
    ob=bpy.data.objects.new(name,None);ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.7;ob.location=location;col.objects.link(ob);return ob

def simple(ob,name,mode,factor,axis='Z',origin=None):
    m=ob.modifiers.new(name,'SIMPLE_DEFORM');m.deform_method=mode;m.deform_axis=axis;m.origin=origin
    if mode=='BEND':m.angle=factor
    else:m.factor=factor
    return m

def make_scene(name,index,target,ortho,eye):
    sc=bpy.context.scene if index==1 else bpy.data.scenes.new(name)
    sc.name=name;bpy.context.window.scene=sc
    main=collection(sc,'Задание '+str(index)+' — результат')
    stages=collection(sc,'Этапы задания '+str(index)+' (скрыто)')
    env=collection(sc,'Камера и свет — '+str(index))
    cam=add_camera(sc,env,'Камера — задание '+str(index),eye,target,lens=50)
    cam.data.type='ORTHO';cam.data.ortho_scale=ortho;cam.data.clip_end=5000
    world(sc,'Мир — задание '+str(index),'111B2B',.45)
    add_light(env,'Основной — '+str(index),'SUN',(28,-20,-30),2.8,angle_deg=12)
    add_light(env,'Заполняющий — '+str(index),'SUN',(70,0,140),1.3,angle_deg=20)
    add_light(env,'Контровой — '+str(index),'SUN',(-35,0,30),1.8,angle_deg=12)
    sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=1400;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
    sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
    sc.view_settings.view_transform='AgX'
    sc.unit_settings.system='METRIC';sc.unit_settings.length_unit='METERS'
    sc['Назначение']='Лабораторная работа 9 — принципы работы с модификаторами'
    return sc,main,stages,env

def snapshot(sc,ob,name,col,through=None):
    old=[m.show_viewport for m in ob.modifiers]
    try:
        if through is not None:
            for i,m in enumerate(ob.modifiers):m.show_viewport=i<through
        sc.view_layers[0].update();dg=sc.view_layers[0].depsgraph
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
        st=bpy.data.objects.new(name,me);col.objects.link(st);st.matrix_world=ob.matrix_world.copy()
        st['Этап']='Снимок геометрии. Основной объект сохраняет редактируемый стек.'
        return st
    finally:
        for m,state in zip(ob.modifiers,old):m.show_viewport=state
        sc.view_layers[0].update()

def hide_stages(sc,col):
    col.hide_render=True
    sc.view_layers[0].layer_collection.children[col.name].hide_viewport=True

def basket_mesh(col):
    verts=[(x,y,-3.8+z) for z in [0,1,2,3] for x,y in [(1.5,1.5),(-1.5,1.5),(-1.5,-1.5),(1.5,-1.5)]]
    faces=[(3,2,1,0),(12,13,14,15)]
    for k in range(3):
        for j in range(4):faces.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
    return mesh('Корзина',verts,faces,col)

def envelope_mesh(col):
    r=5;bottom=-3.7;theta_max=math.acos(bottom/r)
    angles=sorted(set([theta_max*i/20 for i in range(1,21)]+[math.pi/2]),reverse=True)
    verts=[(r*math.sin(t)*math.cos(j*2*math.pi/32),r*math.sin(t)*math.sin(j*2*math.pi/32),r*math.cos(t)) for t in angles for j in range(32)]
    top=len(verts);verts.append((0,0,r));faces=[]
    for k in range(len(angles)-1):
        for j in range(32):faces.append((k*32+j,k*32+(j+1)%32,(k+1)*32+(j+1)%32,(k+1)*32+j))
    for j in range(32):faces.append(((len(angles)-1)*32+j,(len(angles)-1)*32+(j+1)%32,top))
    faces.append(tuple(reversed(range(32))))
    ob=mesh('Шар',verts,faces,col);ob.location.z=4
    for mat in PANEL:ob.data.materials.append(mat)
    for p in ob.data.polygons:p.material_index=(p.index%32//4)%4;p.use_smooth=False
    ob['Диаметр исходной сферы']=10.0;ob['Срез Hemisphere']=.13;ob['Smooth']=False
    ob['Примечание']='Удалены нижние 13% высоты исходной сферы. Аналог Hemisphere, а не параметр встроенного примитива Blender.'
    return ob

TAPER=taper_group();STRUTS=struts_group();SKEW=skew_group()

# 1. Воздушный шар, общий скос и работа со стеком.
sc1,c1,s1,e1=make_scene('1 — Воздушный шар и стек',1,(1,0,2.8),20.8,(20,-30,14))
ball=envelope_mesh(c1)
taper=add_nodes(ball,'01 — Taper: Amount 0.2, Curve 0.25',TAPER,Amount=.2,Curve=.25,**{'Низ Z':-3.7,'Верх Z':5.0})
origin=empty('Центр растяжения шара',e1,(0,0,4))
stretch=simple(ball,'02 — Stretch: 0.1','STRETCH',.1,origin=origin)
basket=basket_mesh(c1);basket.data.materials.append(BRONZE)
struts=add_nodes(basket,'01 — Lattice: стержни R 0.3',STRUTS,**{'Радиус':.3,'Стороны':12,'Материал':BRONZE})
btaper=add_nodes(basket,'02 — Taper: Amount 0.5',TAPER,Amount=.5,Curve=0.0,**{'Низ Z':-3.8,'Верх Z':-.8})
controller=empty('Общий скос — параметры',c1)
for key,val in [('Скос',.25),('Верхний предел',5.0),('Нижний предел',-2.3),('Пределы включены',True)]:
    controller[key]=val
    if isinstance(val,(int,float)) and not isinstance(val,bool):controller.id_properties_ui(key).update(description='Общее значение для шара и корзины')
controller['Как показать']='N → Элемент → Пользовательские свойства. Меняй Скос; оба объекта меняются. Затем верни 0.25.'
for ob,z in [(ball,4.0),(basket,0.0)]:
    m=add_nodes(ob,'03 — Общий Skew: предел 5 м',SKEW,**{'Z объекта':z})
    for key in ['Скос','Верхний предел','Нижний предел','Пределы включены']:link_property(m,key,controller,'["'+key+'"]')
    link_property(m,'Центр Z',controller,'location[2]')
borigin=empty('Центр растяжения корзины',e1,(0,0,-2.3))
copied=simple(basket,'04 — Stretch: независимая копия 0.1','STRETCH',.1,origin=borigin)

st_base=snapshot(sc1,ball,'01 — Оболочка после среза, до модификаторов',s1,0)
st_taper=snapshot(sc1,ball,'02 — После Taper',s1,1)
st_stretch=snapshot(sc1,ball,'03 — После Stretch, до общего Skew',s1,2)
st_final=snapshot(sc1,ball,'04 — Шар со свёрнутым стеком',s1)
st_final['Collapse All']='Геометрия зафиксирована, модификаторов нет. Основной Шар оставлен редактируемым для защиты.'
snapshot(sc1,basket,'05 — Корзина до Lattice',s1,0)
snapshot(sc1,basket,'06 — Корзина после Lattice',s1,1)
snapshot(sc1,basket,'07 — Корзина после Taper',s1,2)
snapshot(sc1,basket,'08 — Корзина после общего Skew',s1,3)
original_order=[m.name for m in ball.modifiers]
ball.modifiers.move(2,0)
snapshot(sc1,ball,'09 — Другой порядок: Skew перед Taper и Stretch',s1)
ball.modifiers.move(0,2)

# Стержни подвеса — оформление, не дополнительное требование методички.
sc1.view_layers[0].update();dg=sc1.view_layers[0].depsgraph
ball_eval=ball.evaluated_get(dg).to_mesh();lower=[ball.matrix_world@ball_eval.vertices[4+8*i].co for i in range(4)]
ball.evaluated_get(dg).to_mesh_clear()
temp=basket.copy();temp.data=basket.data.copy();temp.name='Временная проверка углов';c1.objects.link(temp)
temp.modifiers.remove(temp.modifiers[0]);sc1.view_layers[0].update();dg=sc1.view_layers[0].depsgraph
tmp_eval=temp.evaluated_get(dg).to_mesh();upper=[temp.matrix_world@tmp_eval.vertices[12+i].co for i in range(4)]
temp.evaluated_get(dg).to_mesh_clear()
for i,(a,b) in enumerate(zip(lower,upper),1):
    rope=curve_object('Подвес '+str(i)+' — оформление',[[a,b]],c1,cyclic=False)
    rope.data.bevel_depth=.045;rope.data.bevel_resolution=2;rope.data.materials.append(ROPE)
bpy.data.objects.remove(temp,do_unlink=True)
hide_stages(sc1,s1)

# 2. Тесселяция выбранной верхней половины цилиндра и симметричный Taper.
sc2,c2,s2,e2=make_scene('2 — Часть цилиндра',2,(0,0,1.0),3.25,(3,-5,2.8))
verts=[(.1*math.cos(j*math.tau/32),.1*math.sin(j*math.tau/32),k*.2) for k in range(11) for j in range(32)]
faces=[tuple(reversed(range(32))),tuple(range(320,352))]
for k in range(10):
    for j in range(32):faces.append((k*32+j,k*32+(j+1)%32,(k+1)*32+(j+1)%32,(k+1)*32+j))
cyl=mesh('Цилиндр — верхняя часть',verts,faces,c2);cyl.data.materials.append(BLUE);cyl.data.materials.append(ORANGE)
cyl['Радиус']=.1;cyl['Высота']=2.0;cyl['Область']='Вершины с z >= 1 м; нижняя часть исключена'
snapshot(sc2,cyl,'01 — Исходный цилиндр R 0.1, H 2',s2,0)
bm=bmesh.new();bm.from_mesh(cyl.data)
upper_faces=[f for f in bm.faces if all(v.co.z>=.99999 for v in f.verts)]
edges=list({e for f in upper_faces for e in f.edges})
bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bm.to_mesh(cyl.data);bm.free()
vg=cyl.vertex_groups.new(name='Верхняя часть');vg.add([v.index for v in cyl.data.vertices if v.co.z>=.99999],1.0,'REPLACE')
for p in cyl.data.polygons:p.material_index=1 if p.center.z>=.99999 else 0
snapshot(sc2,cyl,'02 — Верхняя половина уплотнена',s2,0)
ctaper=add_nodes(cyl,'Taper выбранной части: 3, 1, Symmetry',TAPER,Amount=3.0,Curve=1.0,Symmetry=True,**{'Низ Z':1.0,'Верх Z':2.0,'Только группа':True,'Группа вершин':'Верхняя часть'})
hide_stages(sc2,s2)

# 3. Torus 48 x 48, Cast 0.5 по правой половине и отдельный клон выбранных граней.
sc3,c3,s3,e3=make_scene('3 — Тор и клон фрагмента',3,(0,0,0),12.4,(6,-9,15))
bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=48,major_radius=2.0,minor_radius=.6)
torus=bpy.context.object;torus.name='Тор — сферизация правой части'
for col in list(torus.users_collection):col.objects.unlink(torus)
c3.objects.link(torus);torus.location.x=-3.0
torus.data.materials.append(BLUE);torus.data.materials.append(ORANGE)
selected=[v.index for v in torus.data.vertices if v.co.x>=-1e-6]
vg=torus.vertex_groups.new(name='Правая часть');vg.add(selected,1.0,'REPLACE')
for p in torus.data.polygons:p.material_index=1 if sum(torus.data.vertices[i].co.x for i in p.vertices)>=0 else 0;p.use_smooth=True
torus['Сегменты']=48;torus['Стороны']=48;torus['Радиусы выбраны']= 'Большой 2 м, малый 0.6 м: в методичке размеры не заданы'
snapshot(sc3,torus,'01 — Тор до сферизации',s3,0)
cast=torus.modifiers.new('Spherify 50% — Преобразование, Сфера','CAST')
cast.cast_type='SPHERE';cast.factor=.5;cast.vertex_group='Правая часть';cast.size=2.5;cast.use_radius_as_size=False
sc3.view_layers[0].update();dg=sc3.view_layers[0].depsgraph;ev=torus.evaluated_get(dg)
evaluated=ev.to_mesh();chosen=set(selected)
selected_faces=[p for p in torus.data.polygons if all(v in chosen for v in p.vertices)]
used=sorted({i for p in selected_faces for i in p.vertices});remap={old:i for i,old in enumerate(used)}
clone_verts=[evaluated.vertices[i].co.copy() for i in used]
clone_faces=[tuple(remap[i] for i in p.vertices) for p in selected_faces]
fragment=mesh('Клон — отдельный объект',clone_verts,clone_faces,c3);fragment.location.x=3.2;fragment.data.materials.append(ORANGE)
for p in fragment.data.polygons:p.use_smooth=True
fragment['Метод']='Геометрия выделенной деформированной части скопирована в отдельный объект; аналог Shift+D и P → Выделенное'
allverts=[v.co.copy() for v in evaluated.vertices]+[v+Vector((6.2,0,0)) for v in clone_verts]
allfaces=[tuple(p.vertices) for p in evaluated.polygons]+[tuple(i+len(evaluated.vertices) for i in face) for face in clone_faces]
element=mesh('02 — Клон как элемент внутри одного меша',allverts,allfaces,s3);element.location.x=-3;element.data.materials.append(GREY)
ev.to_mesh_clear();hide_stages(sc3,s3)

# 4. Общая вычисленная база + отдельный Bend только у ссылки.
sc4,c4,s4,e4=make_scene('4 — Объект-ссылка',4,(0,0,1.4),12.2,(10,-20,11))
v=[(x,y,k*.2) for k in range(21) for x,y in [(-.8,-.8),(.8,-.8),(.8,.8),(-.8,.8)]]
f=[(3,2,1,0),(80,81,82,83)]
for k in range(20):
    for j in range(4):f.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
base=mesh('База — Taper общий',v,f,c4);base.location.x=-3;base.data.materials.append(BLUE)
base['Размеры исходного Box']='1.6 x 1.6 x 4 м. Размеры выбраны: в методичке не заданы.'
base_origin=empty('Центр Taper базы',e4,(-3,0,2))
native_taper=simple(base,'Общий Taper: -0.5','TAPER',-.5,origin=base_origin)
snapshot(sc4,base,'01 — Box до Taper',s4,0)
snapshot(sc4,base,'02 — Общая база после Taper',s4)
reference=mesh('Ссылка — общий Taper и свой Bend',[],[],c4);reference.location.x=3
refgroup=reference_group(base)
add_nodes(reference,'01 — Ссылка на вычисленную базу',refgroup)
reforigin=empty('Центр Bend ссылки',e4,(3,0,0))
bend=simple(reference,'02 — Только у ссылки: Bend 90°','BEND',math.pi/2,axis='X',origin=reforigin)
reference['Как проверить']='Поменяй коэффициент Общего Taper на Базе: меняются оба объекта. Bend 90° расположен только у Ссылки.'
snapshot(sc4,reference,'03 — Ссылка с зафиксированным результатом',s4)
hide_stages(sc4,s4)

# Общий стартовый вид, подсказки и выбранные объекты.
for sc,obj,target,distance in [(sc1,ball,(1,0,2.8),23),(sc2,cyl,(0,0,1),4),(sc3,torus,(0,0,0),16),(sc4,reference,(0,0,1.5),16)]:
    bpy.context.window.scene=sc
    for ob in sc.objects:ob.select_set(False)
    obj.select_set(True);sc.view_layers[0].objects.active=obj
    for ob in sc.objects:
        if ob.type in ['LIGHT','CAMERA']:ob.hide_set(True)
    for area in bpy.context.screen.areas:
        if area.type=='PROPERTIES':area.spaces.active.context='MODIFIER'
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.clip_end=5000;sp.overlay.show_floor=False
            sp.shading.type='SOLID';sp.shading.color_type='MATERIAL'
            sp.region_3d.view_location=Vector(target);sp.region_3d.view_distance=distance
            sp.region_3d.view_rotation=sc.camera.rotation_euler.to_quaternion();sp.region_3d.view_perspective='PERSP'
    sc.render.filepath='//Задание_'+sc.name[0]+'.png'

bpy.context.window.scene=sc1
readme=bpy.data.texts.new('НАЧНИТЕ ЗДЕСЬ — Лаба 9')
readme.write('ЛАБОРАТОРНАЯ 9. Принципы работы с модификаторами.\n\nЧетыре сцены: переключатель Сцена вверху справа.\nF12 — рендер; Home — показать всё; Numpad . — выбранное.\nВ каждой сцене есть Этапы задания N (скрыто). Глаз включает их, hide_render оставляет этапы вне рендера.\n\n1. Шар: узловой Taper с Amount/Curve, обычный Stretch, общий Skew.\nОбщий скос — параметры: N → Элемент → Пользовательские свойства.\n2. Цилиндр: группа Верхняя часть и узловой Taper 3/1/Symmetry.\n3. Тор: Преобразование (Cast), Сфера, 0.5, группа Правая часть; справа отдельный клон.\n4. База — общий Taper; Ссылка получает её геометрию и имеет собственный Bend 90°.\n\nСобственный набор 10 кнопок поставляется отдельным Python-файлом. Для основного .blend он не нужен. Встроенного запуска Python при открытии нет. Все драйверы — простые выражения.\n\nТочные отличия от 3ds Max и шаги защиты — в отчёте и шпаргалке рядом с файлом.\n')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Лаба9_Blender.blend'),compress=True)
shutil.copy2(Path(__file__).with_name('modifier_set_lab9.py'),OUT/'Набор_модификаторов_Лаба9.py')
summary={'version':bpy.app.version_string,'scenes':[{ 'name':sc.name,'objects':[o.name for o in sc.objects], 'engine':sc.render.engine} for sc in [sc1,sc2,sc3,sc4]],'main':{'ball':ball.name,'basket':basket.name,'controller':controller.name,'cylinder':cyl.name,'torus':torus.name,'clone':fragment.name,'base':base.name,'reference':reference.name},'torus_vertices':len(torus.data.vertices),'cylinder_vertices':len(cyl.data.vertices)}
(QA/'build.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(OUT/'Лаба9_Blender.blend'),'scenes':len(bpy.data.scenes)},ensure_ascii=False))
