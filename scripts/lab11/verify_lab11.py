"""Проверка геометрии и учебных операций после открытия без Auto Run."""
from pathlib import Path
import bpy,bmesh,sys,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent));import lab11_nodes as N
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab11/Лаба11_Blender.blend'),use_scripts=False)
REPORT={'version':bpy.app.version_string,'checks':[],'scenes':[],'measurements':{}}
def check(name,ok,details=None):
    REPORT['checks'].append({'check':name,'ok':bool(ok),'details':details})
    if not ok:print('FAILED',name,details,flush=True)
def mesh_data(ob):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();points=[tuple(v.co) for v in me.vertices];fc=len(me.polygons);ev.to_mesh_clear();return points,fc
def active_scene(n):
    s=next(s for s in bpy.data.scenes if s['Задание']==n);bpy.context.window.scene=s;return s
def params(m):return {s.name:getattr(m.properties.inputs,s.identifier).value for s in m.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry'}
check('10 сцен',len(bpy.data.scenes)==10)
for s in bpy.data.scenes:
    bpy.context.window.scene=s;entry={'scene':s.name,'objects':[]};stage=next(c for c in s.collection.children if c.name.startswith('Этапы'))
    check(s.name+' — этапы скрыты',stage.hide_render and s.view_layers[0].layer_collection.children[stage.name].exclude and len(stage.objects)>0)
    check(s.name+' — камера свет EEVEE',s.camera and s.camera.data.ortho_scale>0 and any(o.type=='LIGHT' for o in s.objects) and s.render.engine=='BLENDER_EEVEE')
    check(s.name+' — правильный номер и путь',s['Номер лабораторной']==11 and s.render.filepath.startswith('//Лаба11_'))
    for ob in s.collection.objects:
        if ob.type not in ['MESH','SURFACE','CURVES']:continue
        item={'name':ob.name,'type':ob.type,'modifiers':[{'name':m.name,'type':m.type,'params':params(m) if m.type=='NODES' else {}} for m in ob.modifiers]}
        if ob.type=='CURVES':
            bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());item['viewport_curves']=len(ev.data.curves);item['points']=len(ev.data.points);check(ob.name+' — настоящие кривые',len(ev.data.curves)>0)
        else:
            vertices,faces=mesh_data(ob);item.update({'vertices':len(vertices),'faces':faces});check(ob.name+' — непустая конечная геометрия',vertices and faces>0 and all(math.isfinite(v) for p in vertices for v in p))
        entry['objects'].append(item)
    REPORT['scenes'].append(entry)

# В трёх заданиях область вне vertex group должна остаться в точности исходной.
for n,name,group in [(1,'Сфера — Push полюсов','Полюса'),(2,'Сфера — Stretch из рёбер','Рёбра — конечные вершины'),(3,'Собственная модель — бутон','Верхние грани')]:
    active_scene(n);ob=bpy.data.objects[name];index=ob.vertex_groups[group].index;selected={v.index for v in ob.data.vertices if any(g.group==index and g.weight>0 for g in v.groups)};vs,_=mesh_data(ob)
    outside=max((Vector(vs[v.index])-v.co).length for v in ob.data.vertices if v.index not in selected);inside=max((Vector(vs[v.index])-v.co).length for v in ob.data.vertices if v.index in selected)
    check(name+' — выделение не пустое',len(selected)>0,len(selected));check(name+' — вне группы смещение нулевое',outside<1e-6,outside);check(name+' — выбранная область деформирована',inside>.01,inside)
    if n==1:
        displacement=[(Vector(vs[i])-ob.data.vertices[i].co).length for i in selected];check('Push равен диаметру 1 м',all(abs(x-1)<1e-5 for x in displacement));REPORT['measurements']['push']={'selected':len(selected),'outside_displacement':outside,'min_push':min(displacement),'max_push':max(displacement)}

s=active_scene(4);ob=bpy.data.objects['Тыква — оболочка с созданным зубом'];bm=bmesh.new();bm.from_mesh(ob.data);boundary={e for e in bm.edges if e.is_boundary};loops=0
while boundary:
    loops+=1;queue=[boundary.pop()]
    while queue:
        for v in queue.pop().verts:
            for e in v.link_edges:
                if e in boundary:boundary.remove(e);queue.append(e)
bm.free();check('Тыква — четыре настоящих проёма',loops==4,loops)
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());rays=[]
for x,z in [(-.20,.18),(.20,.18),(0,0),(-.20,-.20)]:
    hit,loc,norm,idx=ev.ray_cast(Vector((x,-2,z)),Vector((0,1,0)));rays.append({'x':x,'z':z,'hit':hit,'first_y':loc.y if hit else None})
check('Луч проходит через глаза нос и рот к задней стенке',all(r['hit'] and r['first_y']>0 for r in rays),rays);REPORT['measurements']['pumpkin']={'boundary_loops':loops,'hole_rays':rays}

active_scene(5);body=bpy.data.objects['Сфера после Detach'];cap=bpy.data.objects['Отделённый верх — самостоятельный объект'];check('Detach — разные меши',body.data!=cap.data and body.type==cap.type=='MESH')
check('Detach — 512 исходных граней распределены без дубликатов',len(body.data.polygons)+len(cap.data.polygons)==512);REPORT['measurements']['detach']={'body_faces':len(body.data.polygons),'cap_faces':len(cap.data.polygons)}

active_scene(6)
for name,key in [('Weld — три вершины кольца','Weld — измерение'),('Tessellate — Edge сверху Face Center снизу','Tessellate — измерение')]:
    ob=bpy.data.objects[name];value=json.loads(ob[key]);REPORT['measurements'][key]=value
    check(name+' — записано фактическое число вершин',value['after']['vertices']==len(ob.data.vertices))
check('Weld уменьшает число вершин на две',REPORT['measurements']['Weld — измерение']['before']['vertices']-REPORT['measurements']['Weld — измерение']['after']['vertices']==2)
check('Tessellate увеличил число граней',REPORT['measurements']['Tessellate — измерение']['after']['faces']>512)

active_scene(7);grow=bpy.data.objects['Grow и Shrink — выделение'];seq=json.loads(grow['Grow и Shrink']);check('Grow/Shrink 1 → 9 → 25 → 9',seq==[1,9,25,9],seq);REPORT['measurements']['grow']=seq
flip=bpy.data.objects['Flip — одна обратная нормаль'];inward=sum(p.normal.dot(p.center)<0 for p in flip.data.polygons);check('Flip — ровно одна обратная грань',inward==1,inward)
collapse=bpy.data.objects['Collapse — четыре вершины в центр'];d=json.loads(collapse['Collapse — измерение']);check('Collapse — минус три вершины',d['before']['vertices']-len(collapse.data.vertices)==3);REPORT['measurements']['collapse']=d
for axis in 'XYZ':
    ob=bpy.data.objects['Make Planar — '+axis];index=ob.vertex_groups['Плоская область'].index;coords=[v.co['XYZ'.index(axis)] for v in ob.data.vertices if any(g.group==index for g in v.groups)];check('Make Planar '+axis+' — одна координата',max(coords)-min(coords)<1e-6)

s=active_scene(8);ob=bpy.data.objects['Box — неправильная область Cut'];before=[tuple(v.co) for v in ob.data.vertices];after,faces=mesh_data(ob);check('Cut — восьмиугольник в одной грани',sum(bool(d.value) for d in ob.data.attributes['Область Cut'].data)==1 and len(ob.data.polygons[-1].vertices)==8)
check('Extrude — верх на Z 0.75 м',abs(max(v[2] for v in after)-.75)<1e-5)
stage=next(c for c in s.collection.children if c.name.startswith('Этапы'))
for name,expected in [('Hide Selected — учебное состояние',1),('Hide Unselected — учебное состояние',17),('Unhide All — учебное состояние',0)]:
    cp=bpy.data.objects[name];count=sum(p.hide for p in cp.data.polygons);check(name,count==expected,count)

active_scene(9);ob=bpy.data.objects['Навес — поверхность 4×4'];sp=ob.data.splines[0];check('Навес — редактируемая SURFACE 4×4',ob.type=='SURFACE' and sp.point_count_u==sp.point_count_v==4 and len(sp.points)==16)
check('Навес — бикубическая зажатая поверхность с единичными весами',sp.order_u==sp.order_v==4 and sp.use_endpoint_u and sp.use_endpoint_v and all(abs(p.co.w-1)<1e-6 for p in sp.points))

s=active_scene(10);stage=next(c for c in s.collection.children if c.name.startswith('Этапы'));s.view_layers[0].layer_collection.children[stage.name].exclude=False;hairstats=[]
for name,count,length in [('Щетина — 250000 волос',250000,.06),('02 — мех 500000 волос',500000,.3)]:
    ob=bpy.data.objects[name];m=ob.modifiers[0];p=params(m);bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());view_count=len(ev.data.curves);check(name+' — Max Hairs 100000',view_count==100000 and p['Max Hairs']==100000,view_count)
    N.set_input(m,'Полное количество',True);ob.update_tag();bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());curves=len(ev.data.curves);points=len(ev.data.points);check(name+' — полное реальное число кривых',curves==count and points==4*count,{'curves':curves,'points':points})
    root_dist=[ev.data.points[i*4].position.length for i in range(min(curves,100))];check(name+' — корни на сфере R 0.5',all(abs(r-.5)<1e-4 for r in root_dist))
    hairstats.append({'name':name,'viewport_count':view_count,'full_curves':curves,'points':points,'base_axial_length':p['Длина основы']*p['Scale']*.01*p['Cut Length']*.01,'params':p});N.set_input(m,'Полное количество',False);ob.update_tag()
REPORT['measurements']['hair']=hairstats
check('Внешние изображения упакованы или отсутствуют',all(im.packed_file or im.source not in ['FILE','TILED'] for im in bpy.data.images))
REPORT['passed']=all(x['ok'] for x in REPORT['checks']);target=ROOT/'work/lab11/model-qa.json';target.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':REPORT['passed'],'checks':len(REPORT['checks']),'measurements':REPORT['measurements']},ensure_ascii=False),flush=True);assert REPORT['passed'],str(target)
