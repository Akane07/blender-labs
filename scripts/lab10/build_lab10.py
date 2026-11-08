"""12 заданий лабораторной 10. Запуск установленным Blender в фоне."""
from pathlib import Path
import sys, math, json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
import lab10_nodes as N
OUT=ROOT/'output/lab10';OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work/lab10';WORK.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
JOBS=[];RECORD=[]

def mat(name,color,metal=0,rough=.3):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
MATS=[mat('Медь',(.52,.16,.055),.55),mat('Бирюзовый пластик',(.025,.32,.38),.2),mat('Синий металл',(.055,.15,.42),.5),mat('Золотистый',(.7,.39,.055),.45),mat('Серый этап',(.35,.38,.42),.1),mat('Зелёный',(.08,.38,.19),.1)]

def scene(n,name):
    s=bpy.data.scenes.new(f'{n:02d} — {name}');bpy.context.window.scene=s
    s.unit_settings.system='METRIC';s.unit_settings.length_unit='METERS';s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True
    s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100
    s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG'
    s.world=bpy.data.worlds.new('Фон — '+name);s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.045,.055,.08,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.55
    s.view_settings.view_transform='AgX';s.render.film_transparent=False
    stage=bpy.data.collections.new('Этапы '+str(n)+' (скрыто)');s.collection.children.link(stage);stage.hide_render=True
    cam=bpy.data.cameras.new('Камера');co=bpy.data.objects.new('Камера',cam);s.collection.objects.link(co);s.camera=co;cam.type='ORTHO';cam.clip_end=10000
    for name,rot,energy,size in [('Основной',(.35,-.55,-.5),3, .25),('Заполнение',(.9,.4,2.6),1.4,.4),('Контровой',(-.4,.2,.6),2,.2)]:
        d=bpy.data.lights.new(name,'SUN');d.energy=energy;d.angle=size;ob=bpy.data.objects.new(name,d);s.collection.objects.link(ob);ob.rotation_euler=rot;ob.hide_set(True)
    co.hide_set(True);s['Номер лабораторной']=10;s['Задание']=n;s['Источник']='10.docx; внутренний номер 15 заменён по указанию пользователя'
    RECORD.append({'number':n,'scene':s.name,'objects':[]});return s,stage

def register(ob,name,material=0):
    ob.name=name;ob.data.name=name+' — сетка'
    if hasattr(ob.data,'materials'):ob.data.materials.clear();ob.data.materials.append(MATS[material])
    if ob.type=='MESH':
        for p in ob.data.polygons:p.use_smooth=True
    RECORD[-1]['objects'].append(name);return ob

def mesh(name,verts,faces,material=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);register(ob,name,material);return ob

def cylinder(name,r=.08,h=1.4,segments=30,sides=48,bottom=0,material=0,caps=True):
    verts=[(r*math.cos(2*math.pi*j/sides),r*math.sin(2*math.pi*j/sides),bottom+h*k/segments) for k in range(segments+1) for j in range(sides)]
    faces=[(k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j) for k in range(segments) for j in range(sides)]
    if caps:faces.extend([tuple(reversed(range(sides))),tuple(segments*sides+j for j in range(sides))])
    ob=mesh(name,verts,faces,material);ob['Исходные размеры']=f'Радиус {r} м; высота {h} м; сегменты высоты {segments}; стороны {sides}';return ob

def sphere(name,r=.6,segments=128,material=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=segments//2,radius=r);ob=bpy.context.object;register(ob,name,material);ob['Исходные размеры']=f'Радиус {r} м; сегменты {segments}; кольца {segments//2}';return ob

def torus(name,r=1,tube=.2,material=0):
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=24,major_radius=r,minor_radius=tube);ob=bpy.context.object;register(ob,name,material);ob['Исходные размеры']=f'Большой радиус {r} м; малый {tube} м; сетка 48×24';return ob

def stage(ob,col,name):
    cp=ob.copy();cp.data=ob.data.copy();cp.name=name;col.objects.link(cp);return cp

def bounds(ob):
    dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);me=ev.to_mesh();vs=[ob.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear()
    if not vs:vs=[ob.matrix_world@Vector(v) for v in ob.bound_box]
    return Vector(tuple(min(v[j] for v in vs) for j in range(3))),Vector(tuple(max(v[j] for v in vs) for j in range(3)))

def layout(items,gap=.25):
    x=0
    for ob in items:
        bpy.context.view_layer.update();lo,hi=bounds(ob);ob.location.x+=x-lo.x;ob.location.y-=(lo.y+hi.y)/2;ob.location.z-=(lo.z+hi.z)/2;x+=hi.x-lo.x+gap
    for ob in items:ob.location.x-=(x-gap)/2

def camera(s,items,view=(3,-6,3)):
    bpy.context.view_layer.update();bb=[bounds(o) for o in items];lo=Vector(tuple(min(a[j] for a,b in bb) for j in range(3)));hi=Vector(tuple(max(b[j] for a,b in bb) for j in range(3)));target=(lo+hi)/2
    direction=Vector(view).normalized();s.camera.location=target+direction*max((hi-lo).length*3,5);s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler()
    inv=s.camera.matrix_world.inverted();bpy.context.view_layer.update();inv=s.camera.matrix_world.inverted();pts=[inv@(o.matrix_world@Vector(v)) for o in items for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).bound_box]
    width=max(p.x for p in pts)-min(p.x for p in pts);height=max(p.y for p in pts)-min(p.y for p in pts)
    s.camera.data.ortho_scale=max(width,height*s.render.resolution_x/s.render.resolution_y)*1.22
    return target

def job(key,s,items,view=(3,-6,3)):
    JOBS.append({'key':key,'scene':s.name,'objects':[o.name for o in items],'view':view})

def finish(s,col,items,view=(3,-6,3)):
    camera(s,items,view);bpy.context.view_layer.layer_collection.children[col.name].exclude=True
    for ob in s.objects:ob.select_set(False)
    bpy.context.view_layer.objects.active=items[0];items[0].select_set(True)
    s.render.engine='BLENDER_EEVEE';s.render.filepath='//Лаба10_'+str(s['Задание'])+'.png'

# 1 — собственная дуговая формула с физическими пределами в метрах.
s,c=scene(1,'Bend — два изгиба');ob=cylinder('Цилиндр — два Bend',bottom=-.7)
raw=stage(ob,c,'01 — исходный цилиндр');N.add(ob,N.bend(),'Bend 1 — 360° Z');ring=stage(ob,c,'02 — кольцо 360°')
N.set_input(ob.modifiers[0],'Пределы',True);N.add(ob,N.bend('X',angle=260,direction=90,limits=True),'Bend 2 — 260° X Direction 90°')
job('01_bend_start',s,[raw],(2,-6,2));job('02_bend_ring',s,[ring],(2,-6,1));job('03_bend_final',s,[ob]);finish(s,c,[ob])

# 2 — сохранены обе кривизны и ограниченный стек.
s,c=scene(2,'Taper — кривизна и симметрия');ob=cylinder('Цилиндр — два Taper',material=1);raw=stage(ob,c,'01 — исходный цилиндр')
N.add(ob,N.taper(),'Taper 1 — Amount 7 Curve 10');plus=stage(ob,c,'02 — Curve плюс 10');N.set_input(ob.modifiers[0],'Curve',-10.);minus=stage(ob,c,'03 — Curve минус 10')
N.set_input(ob.modifiers[0],'Пределы',True);limited=stage(ob,c,'04 — пределы 0.7…1 м');N.add(ob,N.taper('X','Y',5.,10.,sym=True,bounds=(-.64,.64)),'Taper 2 — X → Y Symmetry')
job('04_taper_plus',s,[plus]);job('05_taper_minus',s,[minus]);job('06_taper_limits',s,[limited]);job('07_taper_final',s,[ob],(3,-6,3));finish(s,c,[ob])

# 3 — штатный Twist; абсолютные пределы преобразованы в доли габарита.
s,c=scene(3,'Twist — копия в стеке');ob=torus('Тор — Twist X затем Z',material=2);raw=stage(ob,c,'01 — исходный тор')
m=ob.modifiers.new('Twist — 180° Y','SIMPLE_DEFORM');m.deform_method='TWIST';m.deform_axis='Y';m.angle=math.pi;ystage=stage(ob,c,'02 — Twist Y 180°')
m.name='Twist 1 — 180° X пределы ±0.4 м';m.deform_axis='X';m.limits=(1/3,2/3);first=stage(ob,c,'03 — Twist X ограниченный')
m2=ob.modifiers.new('Twist 2 — независимая копия Z','SIMPLE_DEFORM');m2.deform_method='TWIST';m2.deform_axis='Z';m2.angle=math.pi
bpy.context.view_layer.update();lo,hi=bounds(ob);m2.limits=(max(0,min(1,(-.4-lo.z)/(hi.z-lo.z))),max(0,min(1,(.4-lo.z)/(hi.z-lo.z))))
ob['Пределы методички']='Оба Twist: Lower −0.4 м, Upper +0.4 м; в Blender доли соответствующего входного габарита';job('08_twist_y',s,[ystage]);job('09_twist_final',s,[ob],(2,-5,4));finish(s,c,[ob],(2,-5,4))

# 4 — три отдельные сферы, опечатка «вторая» в третьем пункте исправлена.
s,c=scene(4,'Noise — три сферы');items=[]
for k,(scale,rough,it,zv) in enumerate([(5.,.2,1,.1),(50.,.6,5,.1),(300.,1.,7,1.)]):
    ob=sphere(['Сфера 1 — игольчатая','Сфера 2 — плавный шум','Сфера 3 — фрактальная Z'][k],material=k)
    if k==0:stage(ob,c,'01 — исходная сфера Noise')
    N.add(ob,N.noise(scale,rough,it,zv));items.append(ob)
    if k==2:
        N.set_input(ob.modifiers[0],'Iterations',3);it3=stage(ob,c,'Сфера 3 — Iterations 3');N.set_input(ob.modifiers[0],'Iterations',7)
layout(items,.4);job('10_noise',s,items,(0,-7,2));job('11_noise_it3',s,[it3],(2,-6,2));finish(s,c,items,(0,-7,2))

# 5 — один ограниченный и один независимый неограниченный Stretch.
s,c=scene(5,'Stretch — два направления');ob=sphere('Сфера — Stretch Z и Y',material=0);raw=stage(ob,c,'01 — исходная сфера');N.add(ob,N.stretch(),'Stretch 1 — Z 1 Amplify 8');first=stage(ob,c,'02 — Stretch Z');N.add(ob,N.stretch('Y',.2,20.,False),'Stretch 2 — Y 0.2 Amplify 20')
job('12_stretch_first',s,[first]);job('13_stretch_final',s,[ob]);finish(s,c,[ob])

# 6 — пределы исходника переставлены местами; честный учебный профиль.
s,c=scene(6,'Squeeze — корпус фонарика');ob=torus('Корпус — учебный обжим',.5,.1,3);raw=stage(ob,c,'01 — исходный тор');N.add(ob,N.squeeze());ob['Исправление']='В исходнике Lower 1 > Upper 0; использован корректный порядок Lower 0, Upper 1 м.'
job('14_squeeze',s,[ob],(3,-6,2));finish(s,c,[ob],(3,-6,2))

# 7 — 128 сегментов по обеим сторонам; два сохранённых состояния.
s,c=scene(7,'Ripple и Wave — фаза');n=128;verts=[(-.7+1.4*x/n,-.5+y/n,0) for y in range(n+1) for x in range(n+1)];faces=[(y*(n+1)+x,y*(n+1)+x+1,(y+1)*(n+1)+x+1,(y+1)*(n+1)+x) for y in range(n) for x in range(n)]
ob=mesh('Плоскость — финальная Wave',verts,faces,1);stage(ob,c,'00 — исходная плоскость');N.add(ob,N.wave(True),'Ripple — этап');ripple=stage(ob,c,'01 — Ripple круговая');ob.modifiers.clear();m=N.add(ob,N.wave(False),'Wave — линейная')
for target in [ripple,ob]:
    mod=target.modifiers[0];sock=next(x for x in mod.node_group.interface.items_tree if x.item_type=='SOCKET' and x.in_out=='INPUT' and x.name=='Phase');path=mod.path_from_id()+'.properties.inputs.'+sock.identifier+'.value'
    for frame,value in [(1,0),(30,math.pi),(60,2*math.pi)]:N.set_input(mod,'Phase',value);target.keyframe_insert(data_path=path,frame=frame)
s.frame_end=60;s.frame_set(1);job('15_ripple',s,[ripple],(1,-3,2));job('16_wave',s,[ob],(1,-3,2));finish(s,c,[ob],(1,-3,2))

# 8 — полное смещение 3 м между уровнями ±0.2 м.
s,c=scene(8,'Skew — клемма');ob=sphere('Сфера — скос Z',material=3);stage(ob,c,'01 — исходная сфера Skew');N.add(ob,N.skew());job('17_skew',s,[ob],(2,-7,2));finish(s,c,[ob],(2,-7,2))

# 9 — оставлены четыре профиля вместо потери промежуточных состояний.
s,c=scene(9,'Affect Region — вмятина груша воронка');items=[]
for name,fall,pin,bub,start,end in [('Вмятина 20',20,0,0,(-.25,0,0),(-.05,0,0)),('Вмятина 8',8,0,0,(-.25,0,0),(-.08,0,0)),('Груша',25,3,0,(0,0,.25),(0,0,.6)),('Воздухозаборник — учебная воронка',25,-5,8,(-.25,0,0),(.12,0,0))]:
    ob=sphere(name,.25,64,material=len(items)%4)
    if not items:
        zero=stage(ob,c,'00 — Affect Region Falloff 0');N.add(zero,N.affect('Нулевой радиус',0,0,0,(-.25,0,0),(0,0,0)))
    N.add(ob,N.affect(name,fall,pin,bub,start,end));items.append(ob)
layout(items,.2);job('18_affect',s,items,(-2,-8,3));job('19_intake',s,[items[-1]],(-6,-3,2));finish(s,c,items,(-2,-8,3))

# 10 — исходные толстые распорки и собственная корзина с тонкими рёбрами.
s,c=scene(10,'Lattice — узлы и контейнер');ob=cylinder('Контейнер — Radius 0.06',.2,.5,5,24,material=1,caps=False);raw=stage(ob,c,'01 — исходная сетка цилиндра');N.add(ob,N.struts(.06),'Распорки — 0.06 м');thin=stage(ob,c,'02 — узлы радиус 0.02');thin.modifiers.clear();N.add(thin,N.struts(joints=True,jradius=.02));large=stage(thin,c,'03 — узлы радиус 0.2');N.set_input(large.modifiers[0],'Radius',.2)
own=cylinder('Собственная модель — корзина',.2,.5,5,24,material=3,caps=False);N.add(own,N.taper(amount=.4,curve=.25,bounds=(0,.5)),'Расширение корзины');N.add(own,N.struts(.009),'Тонкие распорки — 0.009 м')
# дно и ободки — самостоятельная детализация; меш остаётся раздельным и редактируемым.
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.2,depth=.015,location=(0,0,0));base=register(bpy.context.object,'Корзина — дно',3)
for z,r in [(0,.2),(.5,.28)]:
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,major_radius=r,minor_radius=.012,location=(0,0,z));register(bpy.context.object,'Корзина — обод '+str(z),3)
detail=[o for o in s.objects if o.name.startswith('Корзина —')];layout([ob,own],.3)
for item in detail:item.location+=own.location
job('20_lattice_joints',s,[thin],(2,-6,3));job('21_lattice_large',s,[large],(2,-6,3));job('22_lattice_final',s,[ob,own]+detail,(2,-6,3));finish(s,c,[ob,own]+detail,(2,-6,3))

# 11 — штатная пространственная решётка Blender 10×10×10.
s,c=scene(11,'FFD — свободная деформация');ball=sphere('Сфера — FFD',.6,64,0);stage(ball,c,'01 — сфера до FFD')
bpy.ops.mesh.primitive_cube_add(size=1);cube=register(bpy.context.object,'Собственная модель — мягкий корпус',1);stage(cube,c,'02 — куб до FFD');sub=cube.modifiers.new('Сетка для FFD','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=4;sub.render_levels=4
for ob,size,kind in [(ball,1.25,'sphere'),(cube,1.05,'cube')]:
    lat=bpy.data.lattices.new('Решётка 10×10×10 '+kind);lat.points_u=lat.points_v=lat.points_w=10;lat.interpolation_type_u=lat.interpolation_type_v=lat.interpolation_type_w='KEY_BSPLINE'
    # После изменения разрешения Blender хранит опорную клетку в координатах
    # −4.5…+4.5, а не −0.5…+0.5. Физический габарит должен остаться size.
    cage=bpy.data.objects.new('FFD — '+kind,lat);s.collection.objects.link(cage);cage.scale=(size/9,)*3;cage.show_in_front=True
    for pt in lat.points:
        x,y,z=pt.co/9
        if kind=='sphere':
            w=max(0,(z+.5))**3;pt.co_deform=(9*(x+.5*w),9*y*(1-.18*w),9*(z+.22*w))
        else:
            t=z+.5;pt.co_deform=(9*(x*(.7+.65*t*t)+.25*t*t),9*y*(.7+.45*math.sin(math.pi*t)),9*z*1.3)
    m=ob.modifiers.new('FFD — решётка 10×10×10','LATTICE');m.object=cage;ob['Conform to Shape']='Прямого аналога нет: регулярная решётка по габариту, без проекции на поверхность.'
    if kind=='cube':
        sm=ob.modifiers.new('Сглаживание корпуса','SUBSURF');sm.levels=2;sm.render_levels=2
layout([ball,cube],.45)
for ob in [ball,cube]:next(m for m in ob.modifiers if m.type=='LATTICE').object.location=ob.location
job('23_ffd',s,[ball,cube],(2,-6,3));finish(s,c,[ball,cube],(2,-6,3))

# 12 — сравнение трёх углов Dissolve; Face Thresh не заменён процентом.
s,c=scene(12,'Optimize — число полигонов');items=[]
for angle in [0,5,10]:
    ob=sphere('Сфера — порог '+str(angle)+'°',.6,32,len(items))
    if angle==0:stage(ob,c,'01 — сфера до Optimize')
    m=ob.modifiers.new('Оптимизация — растворение '+str(angle)+'°','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(angle);m.use_dissolve_boundaries=False;items.append(ob)
layout(items,.25)
for ob in items:
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();ob['Граней исходно']=len(ob.data.polygons);ob['Граней после']=len(me.polygons);ob['Вершин после']=len(me.vertices);ev.to_mesh_clear()
job('24_optimize',s,items,(0,-7,2));finish(s,c,items,(0,-7,2))

text=bpy.data.texts.new('ПРОЧТИ — лабораторная 10');text.write('Лабораторная 10, несмотря на номер 15 внутри методички.\n12 сцен = 12 заданий. Меняй сцену в верхней панели. F12 — итоговый кадр.\nЭтапы: в Outliner включи исключённую коллекцию «Этапы N (скрыто)», затем верни её выключение.\nНоды — открытые учебные аналоги; формулы и отличия в отчёте и свойствах групп.\nИндивидуальный вариант преподавателем не выдавался. Собственные модели — корзина (10), мягкий корпус (11).\nМодели созданы через Python API; выполнение встроенного кода для открытия не требуется.\n')
if 'Scene' in bpy.data.scenes:bpy.data.scenes.remove(bpy.data.scenes['Scene'])
bpy.context.window.scene=bpy.data.scenes['01 — Bend — два изгиба']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=10000
        elif area.type=='PROPERTIES':area.spaces.active.context='MODIFIER'
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Лаба10_Blender.blend'),compress=True)
(WORK/'render_jobs.json').write_text(json.dumps(JOBS,ensure_ascii=False,indent=2),encoding='utf-8');(WORK/'scenes.json').write_text(json.dumps(RECORD,ensure_ascii=False,indent=2),encoding='utf-8')
print('LAB10_BUILD_OK',len(bpy.data.scenes),'scenes',len(JOBS),'renders')
