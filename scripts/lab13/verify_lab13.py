"""Повторное открытие и проверка геометрии, света, драйверов и связей ЛР13."""
from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'work/lab13';OUT=ROOT/'output/lab13'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Лаба13_Blender.blend'),use_scripts=False)
R={'version':bpy.app.version_string,'checks':[],'measurements':{}}
def check(name,ok,details=None):
    R['checks'].append({'check':name,'ok':bool(ok),'details':details})
    if not ok:print('FAILED',name,details,flush=True)
def sc(code):
    s=next(s for s in bpy.data.scenes if s.get('Код')==code);bpy.context.window.scene=s;bpy.context.view_layer.update();return s
def obj(s,original):return next(o for o in s.objects if o.get('Исходное имя')==original)
def light(s,name):return next(o for o in s.objects if o.get('Имя источника')==name)
def hash_mesh(o):
    p={'vertices':[list(v.co) for v in o.data.vertices],'polygons':[list(p.vertices) for p in o.data.polygons]};return hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()
check('18 опытов',len(bpy.data.scenes)==18,len(bpy.data.scenes));check('Все 10 заданий',sorted({s.get('Задание') for s in bpy.data.scenes})==list(range(1,11)))
baseline=json.loads((WORK/'source-geometry.json').read_text(encoding='utf-8'))
for s in sorted(bpy.data.scenes,key=lambda s:s.get('Код','')):
    bpy.context.window.scene=s;bpy.context.view_layer.update();code=s['Код'];dg=bpy.context.evaluated_depsgraph_get()
    check(code+' камера и относительный путь',s.camera and s.render.filepath.startswith('//') and s.camera.data.clip_end>=100)
    check(code+' один кадр и правильный номер',s.frame_start==s.frame_end==s.frame_current==1 and s.get('Номер лабораторной')==13)
    stage=next(c for c in s.collection.children if c.name.startswith('Этапы'))
    check(code+' скрытые этапы',stage.hide_render and s.view_layers[0].layer_collection.children[stage.name].exclude)
    for item in baseline:
        o=obj(s,item['name']);check(code+' '+item['name']+' матрица',max(abs(a-b) for ra,rb in zip(item['matrix'],o.matrix_world) for a,b in zip(ra,rb))<1e-7)
        if o.type=='MESH':check(code+' '+item['name']+' меш',hash_mesh(o)==item['mesh_sha256'])
    arch=[obj(s,x['name']) for x in baseline if x['type']=='MESH' and not x['name'].startswith(('Дерево','Plane'))]
    check(code+' единый серый материал строения',len({o.data.materials[0].name for o in arch})==1 and all(o.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value==0 for o in arch))
    path=obj(s,'П-образный путь (Line)');inst=[i for i in dg.object_instances if i.is_instance and i.parent and i.parent.original==path]
    check(code+' двенадцать деревьев без авто-скриптов',len(inst)==12,len(inst))
    check(code+' прототип скрыт',obj(s,'Дерево (образец, American Elm)').hide_get() and obj(s,'Дерево (образец, American Elm)').hide_render)
    for l in [o for o in s.objects if o.get('Основной источник')]:
        helper=next(o for o in s.objects if o.parent==l and o.type=='LIGHT');mult=l['Множитель'];density=l['Плотность тени']
        check(l.name+' распределение мощности',abs(l.data.energy-80*mult*density)<1e-4 and abs(helper.data.energy-80*mult*(1-density))<1e-4,[l.data.energy,helper.data.energy])
        check(l.name+' тень и компенсация',l.data.use_shadow and not helper.data.use_shadow and helper.hide_get())
        for n in l.data.node_tree.nodes:
            if n.type=='VALUE':check(l.name+' узел '+n.name,abs(n.outputs[0].default_value-l[n.name])<1e-5,n.outputs[0].default_value)
        if l.constraints:
            target=l.constraints[0].target;direction=l.evaluated_get(dg).matrix_world.to_quaternion()@Vector((0,0,-1));wanted=(target.matrix_world.translation-l.matrix_world.translation).normalized();check(l.name+' наведение на цель',direction.dot(wanted)>.99999)
        if 'Aspect прямоугольника' in l:
            check(l.name+' прямоугольная угловая маска',l['Aspect прямоугольника']==.5 and l['Внешний угол маски °']==90 and l['Внутренний угол маски °']==45 and 'Прямоугольная маска света' in l.data.node_tree.nodes)
        elif l.data.type=='SPOT' and l.constraints:
            outer=l.data.spot_size;inner=2*math.acos(math.cos(outer/2)+(1-math.cos(outer/2))*l.data.spot_blend);check(l.name+' внутренний угол вдвое меньше внешнего',abs(inner/outer-.5)<1e-5)
    R['measurements'][code]={'engine':s.render.engine,'trees':len(inst),'lights':[{ 'name':l.name,'kind':l.data.type,'power':l.data.energy,'multiplier':l['Множитель'],'density':l['Плотность тени']} for l in s.objects if l.get('Основной источник')]}
for ids in [bpy.data.objects,bpy.data.lights,bpy.data.cameras,bpy.data.node_groups]:
    for data in ids:
        ad=data.animation_data
        if ad:
            for fc in ad.drivers:check('Простой рабочий драйвер '+data.name+' '+fc.data_path,fc.driver.is_simple_expression and fc.driver.is_valid)
        nt=getattr(data,'node_tree',None)
        if nt and nt.animation_data:
            for fc in nt.animation_data.drivers:check('Простой рабочий узловой драйвер '+data.name,fc.driver.is_simple_expression and fc.driver.is_valid)
s=sc('01c');l=light(s,'Omni01');tree=obj(s,'П-образный путь (Line)');check('Исключение дерева только из блокирования',l.light_linking.blocker_collection and l.light_linking.blocker_collection.collection_objects[0].light_linking.link_state=='EXCLUDE' and l.light_linking.receiver_collection is None)
s=sc('03');l=light(s,'Omni01');check('Плотность 0.7',abs(l['Плотность тени']-.7)<1e-6)
s=sc('04b');l=light(s,'Omni01');check('Синий RGB 140 140 240 и Specular0',json.loads(l['RGB sRGB 0 255'])==[140,140,240] and l.data.specular_factor==0 and not l.visible_glossy and l['Спад степень']==1)
s=sc('05');l=light(s,'Omni01');check('Дальний диапазон 1.6–2.35',l['Дальнее включено']==1 and l['Дальнее Start м']==1.6 and l['Дальнее End м']==2.35)
s=sc('06');l=light(s,'Omni01');check('Planet заменён редактируемыми нодами',len([n for n in l.data.node_tree.nodes if n.type=='TEX_NOISE'])==1 and len([n for n in l.data.node_tree.nodes if n.type=='VALTORGB'])==1)
s=sc('07');l=light(s,'FreeSpot01');check('Свободный Spot без цели',l.data.type=='SPOT' and not l.constraints)
s=sc('08c');cyl=obj(s,'Цилиндр Cylinder01')
for name in ['Spot01','Spot02']:
    l=light(s,name);col=l.light_linking.receiver_collection;check(name+' Cylinder исключён из света и оставлен затеняющим',col and cyl.name in col.objects and col.collection_objects[0].light_linking.link_state=='EXCLUDE' and l.light_linking.blocker_collection is None and cyl.visible_shadow)
s=sc('09');l=light(s,'Spot03');check('Только Spot03 и цветное небо',all(light(s,name)['Множитель']==0 for name in ['Omni01','Spot01','Spot02']) and l['Множитель']==.5 and json.loads(s['RGB неба'])==[200,70,40] and json.loads(s['RGB фона'])==[120,80,70])
check('Ближнее и дальнее затухание Spot03',l['Ближнее включено']==l['Дальнее включено']==1 and 0<l['Ближнее End м']==l['Дальнее Start м']<l['Дальнее End м'])
s=sc('10');l=light(s,'Spot03');cam=s.camera;check('Ракурс следует за Spot03',cam.constraints[0].target==l and max(abs(a-b) for ra,rb in zip(cam.matrix_world,l.matrix_world) for a,b in zip(ra,rb))<1e-5)
check('Угол камеры соответствует Spot03',abs(cam.data.angle-l.data.spot_size)<1e-5,[cam.data.angle,l.data.spot_size])
old=l.data.spot_size;l.data.spot_size=math.radians(60);bpy.context.view_layer.update();check('Драйвер угла работает при изменении',abs(cam.data.angle-l.data.spot_size)<1e-5);l.data.spot_size=old;bpy.context.view_layer.update()
check('Нет внешних неупакованных картинок',all(im.packed_file or im.source in {'GENERATED','VIEWER'} for im in bpy.data.images))
for code,name in [('06','Вестибюль04_Blender.blend'),('07','Вестибюль05_Blender.blend'),('08c','Вестибюль06_Blender.blend'),('09','Вестибюль07_Blender.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/name),use_scripts=False);check(name+' открывается одной активной сценой',len(bpy.data.scenes)==1 and bpy.context.scene.get('Код')==code)
R['passed']=all(x['ok'] for x in R['checks']);(WORK/'model-qa.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'passed':R['passed'],'checks':len(R['checks'])},ensure_ascii=False),flush=True)
assert R['passed']
