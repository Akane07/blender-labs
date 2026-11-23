"""ЛР13: редактируемые опыты со светом на исходном Вестибюле03 из ЛР12."""
from pathlib import Path
import bpy,math,json,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/lab13';WORK=ROOT/'work/lab13'
OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'output/lab12/Вестибюль03_Blender.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),use_scripts=False)
SRC=next(s for s in bpy.data.scenes if 'Вестибюль03' in s.name);bpy.context.window.scene=SRC
CAM=SRC.camera;SOURCE_CAMERA=CAM.matrix_world.copy()
GEOCOLS=[c for c in SRC.collection.children if not c.name.startswith('Этапы')]
GEO=[o for c in GEOCOLS for o in c.objects]
GEO+= [o for o in SRC.collection.objects if o.type in {'MESH','CURVE'}]
GEO=list(dict.fromkeys(GEO));assert len(GEO)==14
SOURCE_HIDDEN=bpy.data.collections.new('Исходный Вестибюль03 и этапы ЛР7')
for c in SRC.collection.children:SOURCE_HIDDEN.children.link(c)
for o in SRC.collection.objects:SOURCE_HIDDEN.objects.link(o)
POINT_POS=Vector((0,-1.3,1.25));D0=(POINT_POS-Vector((0,0,.4))).length
JOBS=[];SCENES=[]

def linear(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def rgb(values):return tuple(linear(v/255) for v in values)
def signature(o):
    q={'name':o.name,'type':o.type,'matrix':[list(r) for r in o.matrix_world]}
    if o.type=='MESH':
        payload={'vertices':[list(v.co) for v in o.data.vertices],'polygons':[list(p.vertices) for p in o.data.polygons]}
        q['mesh_sha256']=hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
    return q
(WORK/'source-geometry.json').write_text(json.dumps([signature(o) for o in GEO],ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'source-provenance.json').write_text(json.dumps({'source':str(SOURCE.relative_to(ROOT)),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()},indent=2),encoding='utf-8')

def drv(owner,path,control,prop,expression='v',index=None):
    f=owner.driver_add(path) if index is None else owner.driver_add(path,index)
    d=f.driver;d.type='SCRIPTED';d.expression=expression;v=d.variables.new();v.name='v';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='['+json.dumps(prop,ensure_ascii=False)+']'
    return d
def energy_drv(data,control,unblocked=False):
    d=data.driver_add('energy').driver;d.type='SCRIPTED';d.expression='80*m*(1-d)' if unblocked else '80*m*d'
    for v in list(d.variables):d.variables.remove(v)
    for var,key in [('m','Множитель'),('d','Плотность тени')]:
        v=d.variables.new();v.name=var;v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='['+json.dumps(key,ensure_ascii=False)+']'
def look(o,at):o.rotation_euler=(Vector(at)-o.location).to_track_quat('-Z','Y').to_euler()
def set_world(s,ambient=0,sky=None,background=(0,0,0)):
    w=bpy.data.worlds.new('Мир '+s['Код']);w.use_nodes=True;nt=w.node_tree;nt.nodes.clear()
    b=nt.nodes.new('ShaderNodeBackground');b.name='Освещение окружением';b.inputs['Color'].default_value=(*(rgb(sky) if sky else rgb((ambient,)*3)),1);b.inputs['Strength'].default_value=1
    cam=nt.nodes.new('ShaderNodeBackground');cam.name='Фон для камеры';cam.inputs['Color'].default_value=(*rgb(background),1);cam.inputs['Strength'].default_value=1
    lp=nt.nodes.new('ShaderNodeLightPath');mix=nt.nodes.new('ShaderNodeMixShader');out=nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(lp.outputs['Is Camera Ray'],mix.inputs[0]);nt.links.new(b.outputs[0],mix.inputs[1]);nt.links.new(cam.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs[0]);s.world=w
    s['Ambient исходный Value']=ambient;s['RGB неба']=json.dumps(sky);s['RGB фона']=json.dumps(background)

def scene(code,title,task,ambient=0,top=False,engine='CYCLES'):
    s=bpy.data.scenes.new(code+' — '+title);bpy.context.window.scene=s;s['Код']=code;s['Задание']=task;s['Номер лабораторной']=13
    s.render.engine=engine;s.render.resolution_x=1000;s.render.resolution_y=1000 if top else 750;s.render.resolution_percentage=100;s.render.pixel_aspect_x=s.render.pixel_aspect_y=1
    s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.filepath='//Рендер_'+code+'.png';s.render.film_transparent=False
    s.frame_start=s.frame_end=1;s.frame_set(1);s.unit_settings.system='METRIC'
    s.cycles.samples=40;s.cycles.preview_samples=16;s.cycles.use_denoising=True;s.cycles.seed=13;s.cycles.max_bounces=0;s.cycles.diffuse_bounces=0;s.cycles.transparent_max_bounces=8
    s.view_settings.view_transform='AgX';s.view_settings.exposure=0
    gc=bpy.data.collections.new(code+' Геометрия');lc=bpy.data.collections.new(code+' Освещение');s.collection.children.link(gc);s.collection.children.link(lc)
    stage=bpy.data.collections.new('Этапы '+code+' (скрыто)');stage.children.link(SOURCE_HIDDEN);stage.hide_render=True;s.collection.children.link(stage);s.view_layers[0].layer_collection.children[stage.name].exclude=True
    objs={}
    stone=bpy.data.materials.new(code+' Единый серый материал строения');stone.use_nodes=True;bs=stone.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb((180,180,180)),1);bs.inputs['Roughness'].default_value=.52;bs.inputs['Metallic'].default_value=0;stone.diffuse_color=(*rgb((180,180,180)),1)
    for old in GEO:
        o=old.copy();o.data=old.data.copy();o.name=code+' '+old.name;o['Исходное имя']=old.name;gc.objects.link(o);objs[old.name]=o
        if old.type=='MESH' and not old.name.startswith(('Дерево','Plane')):o.data.materials.clear();o.data.materials.append(stone)
    for old in GEO:
        o=objs[old.name]
        if old.parent in GEO:o.parent=objs[old.parent.name];o.matrix_world=old.matrix_world.copy()
        for mod in o.modifiers:
            if mod.type=='NODES' and mod.node_group:
                mod.node_group=mod.node_group.copy()
                for node in mod.node_group.nodes:
                    for sock in node.inputs:
                        if sock.type=='OBJECT' and sock.default_value and sock.default_value.name in objs:sock.default_value=objs[sock.default_value.name]
    proto=objs['Дерево (образец, American Elm)'];proto.hide_set(True)
    cam=CAM.copy();cam.data=CAM.data.copy();cam.name='Камера '+code;cam.matrix_world=SOURCE_CAMERA.copy();gc.objects.link(cam);s.camera=cam;cam.data.lens=40;cam.data.sensor_fit='HORIZONTAL';cam.data.shift_x=cam.data.shift_y=0;cam.data.clip_start=.01;cam.data.clip_end=1000;cam.hide_set(True)
    if top:cam.data.type='ORTHO';cam.data.ortho_scale=5.2;cam.location=(0,0,6);look(cam,(0,0,0))
    set_world(s,ambient)
    s['Описание']='Настройки и иллюстрации созданы Python API; исходные меши и преобразования ЛР12 сохранены.'
    s['Сравнение теней']='Cycles direct, без диффузных переотражений; EEVEE используется в отдельном опыте карты теней.'
    SCENES.append({'code':code,'scene':s.name,'task':task,'objects':{k:v.name for k,v in objs.items()}})
    JOBS.append({'key':code,'scene':s.name});return s,objs,lc

def node_math(nt,op,a,b=None,name=None):
    n=nt.nodes.new('ShaderNodeMath');n.operation=op
    if name:n.name=n.label=name
    for i,x in enumerate([a,b]):
        if x is None:continue
        if hasattr(x,'node'):nt.links.new(x,n.inputs[i])
        else:n.inputs[i].default_value=x
    return n.outputs[0]
def value(nt,ctrl,key,x):
    n=nt.nodes.new('ShaderNodeValue');n.name=n.label=key;n.outputs[0].default_value=x;drv(n.outputs[0],'default_value',ctrl,key);return n.outputs[0]
def shader(data,ctrl,planet=False,rectangle=False):
    data.use_nodes=True;nt=data.node_tree;nt.nodes.clear()
    emit=nt.nodes.new('ShaderNodeEmission');emit.name='Излучение';out=nt.nodes.new('ShaderNodeOutputLight');nt.links.new(emit.outputs[0],out.inputs[0])
    lp=nt.nodes.new('ShaderNodeLightPath');lp.name='Расстояние луча';r=lp.outputs['Ray Length']
    p=value(nt,ctrl,'Спад степень',0);d0=value(nt,ctrl,'Начало Decay м',D0)
    d0safe=node_math(nt,'MAXIMUM',d0,.0001);ratio=node_math(nt,'DIVIDE',d0safe,node_math(nt,'MAXIMUM',r,d0safe));decay=node_math(nt,'POWER',ratio,p,'Плато до Start и спад после')
    fall=nt.nodes.new('ShaderNodeLightFalloff');fall.name='Компенсация физического спада';fall.inputs['Strength'].default_value=1;constant=fall.outputs['Constant']
    norm=node_math(nt,'DIVIDE',constant,node_math(nt,'MULTIPLY',d0safe,d0safe));strength=node_math(nt,'MULTIPLY',norm,decay)
    for label,near in [('Ближнее',True),('Дальнее',False)]:
        enabled=value(nt,ctrl,label+' включено',0);start=value(nt,ctrl,label+' Start м',0);end=value(nt,ctrl,label+' End м',1)
        mp=nt.nodes.new('ShaderNodeMapRange');mp.name=label+' затухание';mp.clamp=True;mp.interpolation_type='LINEAR';nt.links.new(r,mp.inputs['Value']);nt.links.new(start,mp.inputs['From Min']);nt.links.new(end,mp.inputs['From Max']);mp.inputs['To Min'].default_value=0 if near else 1;mp.inputs['To Max'].default_value=1 if near else 0
        gate=node_math(nt,'ADD',node_math(nt,'SUBTRACT',1,enabled),node_math(nt,'MULTIPLY',enabled,mp.outputs['Result']));strength=node_math(nt,'MULTIPLY',strength,gate)
    if rectangle:
        tc=nt.nodes.new('ShaderNodeTexCoord');tc.name='Направление прямоугольного прожектора';xyz=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(tc.outputs['Normal'],xyz.inputs[0])
        z=node_math(nt,'MAXIMUM',node_math(nt,'ABSOLUTE',xyz.outputs['Z']),.00001)
        aspect=value(nt,ctrl,'Aspect прямоугольника',.5);outer=value(nt,ctrl,'Внешний угол маски °',90);inner=value(nt,ctrl,'Внутренний угол маски °',45)
        tan_outer=node_math(nt,'TANGENT',node_math(nt,'MULTIPLY',outer,math.pi/360));tan_inner=node_math(nt,'TANGENT',node_math(nt,'MULTIPLY',inner,math.pi/360))
        x=node_math(nt,'DIVIDE',node_math(nt,'ABSOLUTE',xyz.outputs['X']),node_math(nt,'MULTIPLY',z,node_math(nt,'MULTIPLY',tan_outer,aspect)))
        y=node_math(nt,'DIVIDE',node_math(nt,'ABSOLUTE',xyz.outputs['Y']),node_math(nt,'MULTIPLY',z,tan_outer));q=node_math(nt,'MAXIMUM',x,y,'Прямоугольная граница max X Y')
        mp=nt.nodes.new('ShaderNodeMapRange');mp.name='Переход Hotspot к Falloff';mp.clamp=True;mp.interpolation_type='SMOOTHSTEP';nt.links.new(q,mp.inputs['Value']);nt.links.new(node_math(nt,'DIVIDE',tan_inner,tan_outer),mp.inputs['From Min']);mp.inputs['From Max'].default_value=1;mp.inputs['To Min'].default_value=1;mp.inputs['To Max'].default_value=0
        strength=node_math(nt,'MULTIPLY',strength,mp.outputs['Result'],'Прямоугольная маска света')
    nt.links.new(strength,emit.inputs['Strength'])
    if planet:
        tc=nt.nodes.new('ShaderNodeTexCoord');tc.name='Направление в системе источника';noise=nt.nodes.new('ShaderNodeTexNoise');noise.name='Шум вместо Planet';noise.inputs['Scale'].default_value=5.5;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7;noise.inputs['Distortion'].default_value=.55;nt.links.new(tc.outputs['Normal'],noise.inputs['Vector'])
        ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.name='Цветной светофильтр';cols=[(.42,(40,90,240)),(.47,(60,220,90)),(.52,(240,190,45)),(.57,(220,40,180))]
        for el,(pos,col) in zip(ramp.color_ramp.elements,cols[:2]):el.position=pos;el.color=(*rgb(col),1)
        for pos,col in cols[2:]:el=ramp.color_ramp.elements.new(pos);el.color=(*rgb(col),1)
        nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],emit.inputs['Color'])
    for i,n in enumerate(nt.nodes):n.location=((i%6)*210,-(i//6)*165)

def light(s,lc,name,kind='POINT',loc=POINT_POS,mult=1,density=1,decay=0,radius=.005,color=(255,255,255),target=None,planet=False,specular=1,square=False,aspect=1):
    d=bpy.data.lights.new(s['Код']+' '+name,kind);o=bpy.data.objects.new(d.name,d);lc.objects.link(o);o.location=loc;o['Имя источника']=name;o['Основной источник']=True
    settings={'Множитель':mult,'Плотность тени':density,'Спад степень':decay,'Начало Decay м':D0,'Ближнее включено':0.,'Ближнее Start м':0.,'Ближнее End м':1.,'Дальнее включено':0.,'Дальнее Start м':1.6,'Дальнее End м':2.35}
    if square:settings.update({'Aspect прямоугольника':aspect,'Внешний угол маски °':90.,'Внутренний угол маски °':45.})
    for k,v in settings.items():o[k]=float(v);o.id_properties_ui(k).update(min=0,max=179 if 'угол' in k else (2 if ('включено' in k or k in {'Плотность тени','Спад степень'}) else 10))
    o['Мощность при Множитель 1 Вт']=80.;o['RGB sRGB 0 255']=json.dumps(color);o['Примечание']='Пара источников делит полную мощность на затенённую и незатенённую доли. Плотность 0.7 сохраняет 30% незатенённого прямого света.'
    d.color=rgb(color);d.normalize=True;d.shadow_soft_size=radius;d.specular_factor=specular;d.use_shadow=True;o.visible_glossy=bool(specular)
    if kind=='SPOT':
        d.spot_size=math.radians(120 if square else 90);d.spot_blend=0 if square else (.5 if target is None else (math.cos(math.radians(22.5))-math.cos(math.radians(45)))/(1-math.cos(math.radians(45))));d.use_square=False;d.show_cone=False
    if target is not None:
        t=bpy.data.objects.new(s['Код']+' '+name+'.Target',None);lc.objects.link(t);t.location=target;t.empty_display_type='SPHERE';t.empty_display_size=.035
        c=o.constraints.new('TRACK_TO');c.name='Наведение на цель';c.target=t;c.track_axis='TRACK_NEGATIVE_Z';c.up_axis='UP_Y'
    elif kind=='SPOT':look(o,(0,0,.18))
    shader(d,o,planet,rectangle=square);energy_drv(d,o)
    helper_data=d.copy();helper_data.name=d.name+' — без тени';helper=bpy.data.objects.new(helper_data.name,helper_data);lc.objects.link(helper);helper.parent=o;helper.matrix_basis=Matrix.Identity(4);helper['Вспомогательная доля без тени']=True;helper_data.use_shadow=False;helper.visible_glossy=bool(specular);energy_drv(helper_data,o,True);helper.hide_set(True)
    # Data.copy keeps node drivers aimed at the common controller; native linking remains independent.
    for ob in s.objects:ob.select_set(False)
    o.select_set(True);s.view_layers[0].objects.active=o
    return o,helper
def light_pair_settings(pair,**kwargs):
    for o in pair:
        for k,v in kwargs.items():setattr(o.data,k,v)
def linking(light_ob,objects,kind='receiver'):
    c=bpy.data.collections.new(light_ob.name+' '+('Не освещать' if kind=='receiver' else 'Без тени'))
    for o in objects:c.objects.link(o);c.collection_objects[-1].light_linking.link_state='EXCLUDE'
    setattr(light_ob.light_linking,kind+'_collection',c)
def guides(s,lc,ctrl):
    for key in ['Начало Decay м','Дальнее Start м','Дальнее End м']:
        o=bpy.data.objects.new(s['Код']+' Граница '+key,None);lc.objects.link(o);o.empty_display_type='SPHERE';o.parent=ctrl;o.empty_display_size=1;drv(o,'empty_display_size',ctrl,key);o.hide_set(True)
def job_scene(code):return next(s for s in bpy.data.scenes if s.get('Код')==code)

s,ob,lc=scene('01a','Omni — начальная яркость',1);light(s,lc,'Omni01')
s,ob,lc=scene('01b','Omni — Множитель 1.5',1);light(s,lc,'Omni01',mult=1.5)
s,ob,lc=scene('01c','Деревья не отбрасывают тени',1);pair=light(s,lc,'Omni01',mult=1.5)
for l in pair:linking(l,[ob['П-образный путь (Line)']],kind='blocker')
for code,title,engine,radius in [('02a','Cycles — резкая тень','CYCLES',.005),('02b','EEVEE — карта теней','BLENDER_EEVEE',.005),('02c','Cycles — малый размер источника','CYCLES',.07),('02d','Cycles — площадная тень','CYCLES',.22)]:
    s,ob,lc=scene(code,title,2,top=True,engine=engine);pair=light(s,lc,'Omni01',mult=1.5,radius=radius,decay=2);pair[0]['Начало Decay м']=.001
    if engine=='BLENDER_EEVEE':light_pair_settings(pair,shadow_filter_radius=1.,use_shadow_jitter=False)
s,ob,lc=scene('03','Плотность 0.7 и Ambient 70',3,ambient=70);light(s,lc,'Omni01',density=.7,radius=.07)
s,ob,lc=scene('04a','Белый свет — Inverse Square',4,ambient=50);pair=light(s,lc,'Omni01',decay=2,radius=.07);guides(s,lc,pair[0])
s,ob,lc=scene('04b','Синий свет — Inverse и без бликов',4,ambient=50);pair=light(s,lc,'Omni01',mult=1.5,decay=1,radius=.07,color=(140,140,240),specular=0);guides(s,lc,pair[0])
s,ob,lc=scene('05','Дальнее затухание',5,ambient=50);pair=light(s,lc,'Omni01');pair[0]['Дальнее включено']=1.;guides(s,lc,pair[0])
s,ob,lc=scene('06','Цветной светофильтр',6,ambient=150);light(s,lc,'Omni01',mult=1.3,radius=.15,planet=True)
s,ob,lc=scene('07','FreeSpot01 над куполом',7,ambient=50);light(s,lc,'FreeSpot01',kind='SPOT',loc=(0,0,1.35))

def setup_spots(code,title,final=False,exclude=False,sky=False):
    s,ob,lc=scene(code,title,8 if not sky else 9,ambient=50)
    if final:omni=light(s,lc,'Omni01')
    else:omni=light(s,lc,'FreeSpot01',kind='SPOT',loc=(0,0,1.35))
    z=.09 if final else .18;x=.22 if final else .48
    pairs=[]
    for name,side in [('Spot01',-1),('Spot02',1)]:
        pair=light(s,lc,name,kind='SPOT',loc=(side*1.05,-.75,.8),color=(255,240,165),target=(side*x,-.18,z),square=True,aspect=.5);pairs.append(pair)
        if exclude:
            for l in pair:linking(l,[ob['Цилиндр Cylinder01']])
    if final:
        third=light(s,lc,'Spot03',kind='SPOT',loc=(0,1.45,1.55),target=(0,.5,.18))
        for l in third:l.data.spot_size=math.radians(75);l.data.spot_blend=(math.cos(math.radians(18.75))-math.cos(math.radians(37.5)))/(1-math.cos(math.radians(37.5)))
        if sky:
            for pair in [omni,*pairs]:pair[0]['Множитель']=0.
            ctrl=third[0];ctrl['Множитель']=.5;light_pair_settings(third,shadow_soft_size=.16)
            direction=(Vector((0,.5,.18))-ctrl.location).normalized();start=(.8375-ctrl.location.z)/direction.z;end=(-.01-ctrl.location.z)/direction.z
            ctrl['Ближнее включено']=1.;ctrl['Ближнее Start м']=0.;ctrl['Ближнее End м']=start;ctrl['Дальнее включено']=1.;ctrl['Дальнее Start м']=start;ctrl['Дальнее End м']=end;guides(s,lc,ctrl)
            set_world(s,sky=(200,70,40),background=(120,80,70))
    return s,ob,lc,third[0] if final else pairs[0][0]
setup_spots('08a','Два жёлтых прямоугольных прожектора')
setup_spots('08b','Omni и три Spot — до исключения',final=True)
setup_spots('08c','Вестибюль06 — Cylinder не получает Spot01 и Spot02',final=True,exclude=True)
setup_spots('09','Вестибюль07 — цвет неба и Spot03',final=True,exclude=True,sky=True)
s,ob,lc,spot=setup_spots('10','Ракурс с позиции Spot03',final=True,exclude=True,sky=True);s['Задание']=10;SCENES[-1]['task']=10;s.render.resolution_y=1000
cam=s.camera;cam.hide_set(False);cam.constraints.clear();c=cam.constraints.new('COPY_TRANSFORMS');c.name='Ракурс следует за Spot03';c.target=spot;cam.data.type='PERSP';cam.data.sensor_fit='HORIZONTAL';cam.data.angle=spot.data.spot_size
# Store a simple driver so changing the spot's outer angle also changes the view.
d=cam.data.driver_add('lens').driver;d.type='SCRIPTED';d.expression='18/tan(a/2)';v=d.variables.new();v.name='a';v.type='SINGLE_PROP';v.targets[0].id_type='LIGHT';v.targets[0].id=spot.data;v.targets[0].data_path='spot_size'
s['Ракурс']='Камера с Copy Transforms на Spot03 и простым драйвером lens от spot_size. Num0 показывает связанный ракурс.'

# Remove the source scene but preserve its objects in the excluded stage collection.
for old in list(bpy.data.scenes):
    if not old.get('Код'):bpy.data.scenes.remove(old)
bpy.context.window.scene=job_scene('09');bpy.context.view_layer.update()
for s in bpy.data.scenes:
    bpy.context.window.scene=s;bpy.context.view_layer.update()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL'
            if area.type=='PROPERTIES':area.spaces.active.context='DATA'
    s['Исходник']='Вестибюль03_Blender.blend лабораторной 12, геометрия пользовательской ЛР7';s['Исторические режимы']='mental ray и старые алгоритмы Shadow Map/Adv Ray Traced не запускались. Подписи показывают реальные методы Blender.'
bpy.context.window.scene=job_scene('09')
(WORK/'scenes.json').write_text(json.dumps(SCENES,ensure_ascii=False,indent=2),encoding='utf-8');(WORK/'render_jobs.json').write_text(json.dumps(JOBS,ensure_ascii=False,indent=2),encoding='utf-8')
MAIN=OUT/'Лаба13_Blender.blend';bpy.ops.wm.save_as_mainfile(filepath=str(MAIN),compress=True)
for code,filename in [('06','Вестибюль04_Blender.blend'),('07','Вестибюль05_Blender.blend'),('08c','Вестибюль06_Blender.blend'),('09','Вестибюль07_Blender.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(MAIN),use_scripts=False);s=job_scene(code);bpy.context.window.scene=s;path=OUT/filename;bpy.data.libraries.write(str(path),{s},compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False);s=job_scene(code);bpy.context.window.scene=s
    for other in list(bpy.data.scenes):
        if other!=s:bpy.data.scenes.remove(other)
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print('LAB13_BUILD_OK',len(SCENES),'scenes; 4 separate stages',flush=True)
