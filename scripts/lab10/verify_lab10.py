"""Проверка сохранённого файла без встроенных Python-скриптов."""
from pathlib import Path
import bpy,sys,json,math,hashlib
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent));import lab10_nodes as N
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab10/Лаба10_Blender.blend'),use_scripts=False)
report={'version':bpy.app.version_string,'checks':[],'scenes':[],'optimize':[]}
def check(label,ok,detail=None):
    report['checks'].append({'check':label,'ok':bool(ok),'detail':detail})
    if not ok:print('FAILED',label,detail,flush=True)
def coords(ob):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();vs=[tuple(v.co) for v in me.vertices];faces=len(me.polygons);ev.to_mesh_clear();return vs,faces
def params(m):
    return {x.name:getattr(m.properties.inputs,x.identifier).value for x in m.node_group.interface.items_tree if x.item_type=='SOCKET' and x.in_out=='INPUT' and x.socket_type!='NodeSocketGeometry'}
check('Ровно 12 сцен',len(bpy.data.scenes)==12)
for s in bpy.data.scenes:
    bpy.context.window.scene=s;s.frame_set(1);layer=s.view_layers[0]
    stage=next(c for c in s.collection.children if c.name.startswith('Этапы'));check(s.name+' — скрытые этапы',layer.layer_collection.children[stage.name].exclude and stage.hide_render and len(stage.objects)>0)
    check(s.name+' — камера и свет',s.camera and s.camera.data.ortho_scale>0 and any(o.type=='LIGHT' for o in s.objects))
    check(s.name+' — EEVEE',s.render.engine=='BLENDER_EEVEE')
    entry={'scene':s.name,'objects':[]}
    for ob in s.collection.objects:
        if ob.type!='MESH':continue
        vs,faces=coords(ob);check(s.name+' / '+ob.name+' — геометрия',len(vs)>0 and faces>0 and all(math.isfinite(x) for v in vs for x in v))
        entry['objects'].append({'name':ob.name,'base_vertices':len(ob.data.vertices),'base_faces':len(ob.data.polygons),'evaluated_vertices':len(vs),'evaluated_faces':faces,'modifiers':[{'name':m.name,'type':m.type,'params':params(m) if m.type=='NODES' else {}} for m in ob.modifiers]})
        if s['Задание']==12:report['optimize'].append({'name':ob.name,'before_faces':len(ob.data.polygons),'after_faces':faces,'after_vertices':len(vs)})
    report['scenes'].append(entry)
    if s['Задание']==7:
        ob=bpy.data.objects['Плоскость — финальная Wave'];keys=[];zvalues=[]
        for f in [1,16,30,45,60]:
            s.frame_set(f);vs,_=coords(ob);keys.append(hashlib.sha256(repr(vs).encode()).hexdigest());zvalues.append((min(v[2] for v in vs),max(v[2] for v in vs)))
        check('Wave меняет фазу в промежуточных кадрах',len(set(keys))>=4,{'frames':[1,16,30,45,60],'z_ranges':zvalues})
        s.frame_set(1)
    if s['Задание']==11:
        for ob in [o for o in s.objects if o.type=='LATTICE']:
            lat=ob.data;check(ob.name+' — 10×10×10',lat.points_u==lat.points_v==lat.points_w==10 and len(lat.points)==1000)
            span=(lat.points[-1].co-lat.points[0].co).x*ob.scale.x
            check(ob.name+' — физический размер клетки',1.0<span<1.3,span)
            report.setdefault('ffd',[]).append({'name':ob.name,'first_co':list(lat.points[0].co),'last_co':list(lat.points[-1].co),'moved_points':sum((p.co-p.co_deform).length>1e-5 for p in lat.points)})
    # Проверка динамического изменения существенного параметра с восстановлением.
    if s['Задание'] in [1,2,4,5,6,8,9]:
        ob=next(o for o in s.collection.objects if o.type=='MESH' and any(m.type=='NODES' for m in o.modifiers));m=next(m for m in ob.modifiers if m.type=='NODES');pv=params(m)
        name=next(k for k in ['Angle','Amount','Strength X','Stretch','Axial Amount','Falloff'] if k in pv);before,_=coords(ob);old=pv[name];N.set_input(m,name,old*.7 if old else .1);ob.update_tag();after,_=coords(ob);N.set_input(m,name,old);ob.update_tag();check(s.name+' — редактируемый параметр '+name,any((Vector(a)-Vector(b)).length>1e-6 for a,b in zip(before,after)))
for ob in bpy.data.objects:
    if ob.animation_data:
        for fc in ob.animation_data.drivers:check(ob.name+' — простой драйвер',fc.driver.is_simple_expression and fc.is_valid)
check('Внешних изображений нет либо они упакованы',all(im.packed_file or im.source not in ['FILE','TILED'] for im in bpy.data.images))
check('Относительные пути вывода',all(s.render.filepath.startswith('//') for s in bpy.data.scenes))
s=next(s for s in bpy.data.scenes if s['Задание']==9);bpy.context.window.scene=s
stage=next(c for c in s.collection.children if c.name.startswith('Этапы'));s.view_layers[0].layer_collection.children[stage.name].exclude=False
ob=bpy.data.objects['00 — Affect Region Falloff 0'];vs,_=coords(ob);check('Falloff 0 не меняет сферу',all((Vector(v)-p.co).length<1e-6 for v,p in zip(vs,ob.data.vertices)))
s=next(s for s in bpy.data.scenes if s['Задание']==10);bpy.context.window.scene=s
stage=next(c for c in s.collection.children if c.name.startswith('Этапы'));s.view_layers[0].layer_collection.children[stage.name].exclude=False;bpy.context.view_layer.update()
instances=[x for x in bpy.context.evaluated_depsgraph_get().object_instances if x.is_instance];check('Узлы Lattice существуют как экземпляры',len(instances)>=288,len(instances))
report['passed']=all(x['ok'] for x in report['checks']);target=ROOT/'work/lab10/model-qa.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'optimize':report['optimize'],'ffd':report.get('ffd')},ensure_ascii=False),flush=True)
assert report['passed'],'Проверки модели не пройдены: '+str(target)
