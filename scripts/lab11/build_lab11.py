"""10 заданий лабораторной 11. Запуск установленным Blender в фоне."""
from pathlib import Path
import sys, math, json
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
import lab11_nodes as N
OUT=ROOT/'output/lab11';OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work/lab11';WORK.mkdir(parents=True,exist_ok=True)
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
    co.hide_set(True);s['Номер лабораторной']=11;s['Задание']=n;s['Источник']='11.docx; внутренний номер 16, результат оформлен как лабораторная 11 по имени файла'
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
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    if ob.type in ['MESH','CURVE','SURFACE']:
        me=ev.to_mesh();vs=[ob.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear()
    else:vs=[ob.matrix_world@Vector(v) for v in ev.bound_box]
    if not vs or max((v-vs[0]).length for v in vs)<1e-8:
        r=float(ob.get('Габаритный радиус',.6));vs=[ob.matrix_world@Vector((x*r,y*r,z*r)) for x in [-1,1] for y in [-1,1] for z in [-1,1]]
    return Vector(tuple(min(v[j] for v in vs) for j in range(3))),Vector(tuple(max(v[j] for v in vs) for j in range(3)))

def layout(items,gap=.25):
    x=0
    for ob in items:
        bpy.context.view_layer.update();lo,hi=bounds(ob);ob.location.x+=x-lo.x;ob.location.y-=(lo.y+hi.y)/2;ob.location.z-=(lo.z+hi.z)/2;x+=hi.x-lo.x+gap
    for ob in items:ob.location.x-=(x-gap)/2

def camera(s,items,view=(3,-6,3)):
    bpy.context.view_layer.update();bb=[bounds(o) for o in items];lo=Vector(tuple(min(a[j] for a,b in bb) for j in range(3)));hi=Vector(tuple(max(b[j] for a,b in bb) for j in range(3)));target=(lo+hi)/2
    direction=Vector(view).normalized();rotation=(-direction).to_track_quat('-Z','Y')
    s.camera.location=target+direction*max((hi-lo).length*3,5);s.camera.rotation_euler=rotation.to_euler()
    # Скрытая во вьюпорте камера может иметь старую matrix_world до обновления графа.
    # Размер кадра вычисляем непосредственно из её заданного вращения.
    pts=[rotation.inverted()@(Vector((x,y,z))-target) for low,high in bb for x in [low.x,high.x] for y in [low.y,high.y] for z in [low.z,high.z]]
    width=max(p.x for p in pts)-min(p.x for p in pts);height=max(p.y for p in pts)-min(p.y for p in pts)
    s.camera.data.ortho_scale=max(width,height*s.render.resolution_x/s.render.resolution_y)*1.22
    return target

def job(key,s,items,view=(3,-6,3)):
    JOBS.append({'key':key,'scene':s.name,'objects':[o.name for o in items],'view':view})

def finish(s,col,items,view=(3,-6,3)):
    camera(s,items,view);bpy.context.view_layer.layer_collection.children[col.name].exclude=True
    for ob in s.objects:ob.select_set(False)
    bpy.context.view_layer.objects.active=items[0];items[0].select_set(True)
    s.render.engine='BLENDER_EEVEE';s.render.filepath='//Лаба11_'+str(s['Задание'])+'.png'

# Выделение для иллюстраций — выбранный материал; это не имитация интерфейса.
SELECTED=mat('Оранжевый — выбранная область',(.95,.30,.035),.05,.48)
PUMPKIN=mat('Тыква — оранжевая кожица',(.75,.19,.018),.03,.32)
STEM=mat('Черешок',(.11,.055,.018),0,.65)
LEAF=mat('Лист',(.06,.24,.025),0,.6)
HAIR=mat('Тёплый мех',(.38,.19,.055),.02,.68)
HUMAN=[]

def bm_of(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table();return bm
def commit_bm(ob,bm):
    bm.normal_update();bm.to_mesh(ob.data);ob.data.update();bm.free()
def group_vertices(ob,name,indices):
    g=ob.vertex_groups.new(name=name);g.add(list(indices),1.,'REPLACE');return g
def highlight(ob,faces=(),vertices=()):
    if SELECTED.name not in ob.data.materials:ob.data.materials.append(SELECTED)
    mi=list(ob.data.materials).index(SELECTED)
    faces=set(faces);vertices=set(vertices)
    for p in ob.data.polygons:
        p.select=p.index in faces
        p.material_index=mi if p.index in faces or (vertices and all(v in vertices for v in p.vertices)) else 0
    for v in ob.data.vertices:v.select=v.index in vertices
def closest_faces(bm,target=(0,-.43,.18),count=4):
    return sorted([f for f in bm.faces if len(f.verts)==4],key=lambda f:(f.calc_center_median()-Vector(target)).length)[:count]
def bstats(ob):return {'vertices':len(ob.data.vertices),'edges':len(ob.data.edges),'faces':len(ob.data.polygons)}
def counts(ob,key,before):ob[key]=json.dumps({'before':before,'after':bstats(ob)},ensure_ascii=False)
def position_grid(items,columns=3,gap=1.45):
    rows=math.ceil(len(items)/columns)
    for k,ob in enumerate(items):ob.location=((k%columns-(columns-1)/2)*gap,0,((rows-1)/2-k//columns)*gap)
def point_arrow(s,name,start,direction,length=.25,color=None):
    direction=Vector(direction).normalized();start=Vector(start);end=start+direction*length
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=.007;curve.bevel_resolution=2;sp=curve.splines.new('POLY');sp.points.add(1)
    for p,co in zip(sp.points,[start,end]):p.co=(*co,1)
    ob=bpy.data.objects.new(name,curve);s.collection.objects.link(ob);curve.materials.append(color or SELECTED)
    bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=.022,radius2=0,depth=.055,location=end);tip=bpy.context.object;tip.name=name+' — наконечник';tip.rotation_euler=direction.to_track_quat('Z','Y').to_euler();tip.data.materials.append(color or SELECTED)
    return [ob,tip]

# 1 — Push по двум крайним уровням (полюс + соседнее кольцо с каждой стороны).
s,c=scene(1,'Выбор вершин и Push');ob=sphere('Сфера — Push полюсов',.5,32,0)
chosen=[v.index for v in ob.data.vertices if abs(v.co.z)>=.5*math.cos(math.pi/16)-1e-6]
group_vertices(ob,'Полюса',chosen);highlight(ob,vertices=chosen);raw=stage(ob,c,'01 — выбор двух крайних уровней');N.add(ob,N.push(),'Push — смещение на диаметр 1 м')
ob['Радиус']=.5;ob['Диаметр и Push']=1.;ob['Выбранных вершин']=len(chosen)
job('01_push_selection',s,[raw],(0,-6,0));job('02_push_final',s,[ob],(2,-6,1));finish(s,c,[ob],(2,-6,1))

# 2 — четыре радиальных сектора по маленькому рисунку из методички.
s,c=scene(2,'Выбор рёбер и Stretch');ob=sphere('Сфера — Stretch из рёбер',.5,32,1);selected_edges=[];indices=set()
for edge in ob.data.edges:edge.select=False
for e in ob.data.edges:
    vs=[ob.data.vertices[v].co for v in e.vertices];center=(vs[0]+vs[1])/2
    angle=math.atan2(center.y,center.x);near_axis=min(abs(math.atan2(math.sin(angle-k*math.pi/2),math.cos(angle-k*math.pi/2))) for k in range(4))
    if min(v.z for v in vs)>=.5*math.cos(3*math.pi/16)-1e-6 and near_axis<=math.pi/8+.01:
        selected_edges.append(e.index);indices.update(e.vertices);e.select=True
group_vertices(ob,'Рёбра — конечные вершины',indices);highlight(ob,vertices=indices);ob['Выделенные рёбра']=json.dumps(selected_edges);ob['Образец']='Четыре веерных сектора верхнего полюса, по низкоразрешённому рисунку; область явно сохранена.'
raw=stage(ob,c,'01 — выделенные рёбра Top');m=ob.modifiers.new('Stretch — только концы выбранных рёбер','SIMPLE_DEFORM');m.deform_method='STRETCH';m.deform_axis='Z';m.factor=1.2;m.vertex_group='Рёбра — конечные вершины'
job('03_edges_top',s,[raw],(0,0,7));job('04_edges_stretch',s,[ob],(3,-6,3));finish(s,c,[ob],(3,-6,3))

# 3 — и треугольники, и четырёхугольники верхней области; нижняя часть вне группы.
s,c=scene(3,'Грани полигоны и Taper');ob=sphere('Собственная модель — бутон',.5,32,5);bm=bm_of(ob)
tri=closest_faces(bm,(0,-.35,.33),2);bmesh.ops.triangulate(bm,faces=tri);commit_bm(ob,bm)
sel=[p.index for p in ob.data.polygons if p.center.z>.12];indices={v for p in ob.data.polygons if p.index in sel for v in p.vertices};group_vertices(ob,'Верхние грани',indices);highlight(ob,faces=sel);raw=stage(ob,c,'01 — верхние треугольники и полигоны')
m=ob.modifiers.new('Taper — верхняя часть бутона','SIMPLE_DEFORM');m.deform_method='TAPER';m.deform_axis='Z';m.factor=-1.1;m.vertex_group='Верхние грани'
job('05_faces_selection',s,[raw],(2,-6,3));job('06_taper_bud',s,[ob],(2,-6,2));finish(s,c,[ob],(2,-6,2))

def clip_half(poly,a,b,inside=True):
    def signed(p):return (b[0]-a[0])*(p.z-a[1])-(b[1]-a[1])*(p.x-a[0])
    out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp,dq=signed(p),signed(q);ip=dp>=-1e-10 if inside else dp<=1e-10;iq=dq>=-1e-10 if inside else dq<=1e-10
        if ip:out.append(p)
        if ip!=iq and abs(dp-dq)>1e-12:out.append(p+(q-p)*(dp/(dp-dq)))
    return out
def subtract_convex(poly,cutter):
    signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(cutter,cutter[1:]+cutter[:1]));cutter=cutter if signed>0 else cutter[::-1]
    remain=poly;parts=[]
    for a,b in zip(cutter,cutter[1:]+cutter[:1]):
        outside=clip_half(remain,a,b,False)
        if len(outside)>=3:parts.append(outside)
        remain=clip_half(remain,a,b,True)
        if len(remain)<3:break
    return parts
def hole_loops(ob):
    bm=bm_of(ob);edges=[e for e in bm.edges if e.is_boundary];pending=set(edges);n=0
    while pending:
        n+=1;todo=[pending.pop()]
        while todo:
            e=todo.pop()
            for v in e.verts:
                for linked in v.link_edges:
                    if linked in pending:pending.remove(linked);todo.append(linked)
    bm.free();return n

def repair_tjunctions(bm):
    # Согласование разрезов соседних исходных полигонов: вставить общие точки
    # на длинные рёбра, затем сварить совпавшие вершины. Иначе возникают T-стыки.
    for _ in range(2):
        boundary=[e for e in bm.edges if e.is_boundary];vertices={v for e in boundary for v in e.verts};splits=[]
        for edge in boundary:
            a,b=(v.co for v in edge.verts);d=b-a;length=d.length_squared
            if length<1e-12:continue
            for v in vertices:
                if v in edge.verts:continue
                t=(v.co-a).dot(d)/length
                if 1e-5<t<1-1e-5 and (v.co-a-t*d).length<2e-6:splits.append(v.co.copy())
        if not splits:break
        for co in splits:
            for edge in list(bm.edges):
                if not edge.is_boundary:continue
                a,b=edge.verts;d=b.co-a.co;length=d.length_squared
                if length<1e-12:continue
                t=(co-a.co).dot(d)/length
                if 1e-5<t<1-1e-5 and (co-a.co-t*d).length<2e-6:
                    bmesh.utils.edge_split(edge,a,t);break
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-6)

# 4 — реальные проёмы Create/Delete, затем толщина. Зуб соединён с границей рта.
s,c=scene(4,'Create Delete и тыква-светильник');ob=sphere('Тыква — исходная сфера',.65,96,0);ob.data.materials[0]=PUMPKIN
for v in ob.data.vertices:
    theta=math.atan2(v.co.y,v.co.x);v.co.x*=1+.10*math.cos(8*theta);v.co.y*=1+.10*math.cos(8*theta);v.co.z*=.8
ob.data.update();raw=stage(ob,c,'01 — сфера с восемью долями')
cutters=[[(-.36,.09),(-.09,.11),(-.18,.32)],[(.09,.11),(.36,.09),(.18,.32)],[(-.065,-.065),(.065,-.065),(0,.065)],[(-.38,-.13),(-.22,-.285),(.22,-.285),(.38,-.13)]]
verts=[];faces=[];lookup={}
for f in ob.data.polygons:
    polys=[[ob.data.vertices[v].co.copy() for v in f.vertices]]
    if f.center.y<-.04:
        for cutter in cutters:
            polys=[piece for poly in polys for piece in subtract_convex(poly,cutter)]
    for poly in polys:
        ids=[]
        for p in poly:
            key=tuple(round(float(x),7) for x in p)
            if key not in lookup:lookup[key]=len(verts);verts.append(tuple(p))
            if not ids or ids[-1]!=lookup[key]:ids.append(lookup[key])
        if len(ids)>2 and ids[-1]==ids[0]:ids.pop()
        if len(set(ids))>=3:faces.append(ids)
me=bpy.data.meshes.new('Тыква — вырезанные полигоны');me.from_pydata(verts,[],faces);me.update();ob.data=me;me.materials.append(PUMPKIN)
bm=bm_of(ob);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
degenerate=[f for f in bm.faces if f.calc_area()<1e-12]
if degenerate:bmesh.ops.delete(bm,geom=degenerate,context='FACES_ONLY')
repair_tjunctions(bm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for x in [-.075,.075]:
    edge=next(e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.13)<1e-5 and v.co.y<-.3 for v in e.verts) and min(v.co.x for v in e.verts)-1e-6<=x<=max(v.co.x for v in e.verts)+1e-6)
    v1,v2=edge.verts;factor=(x-v1.co.x)/(v2.co.x-v1.co.x);bmesh.utils.edge_split(edge,v1,factor)
root=sorted([v for v in bm.verts if abs(v.co.z+.13)<1e-5 and v.co.y<-.3 and -.075-1e-6<=v.co.x<=.075+1e-6],key=lambda v:v.co.x,reverse=True)
assert len(root)>=2
left,right=root[-1],root[0];vleft=bm.verts.new((left.co.x,left.co.y+.006,-.225));vright=bm.verts.new((right.co.x,right.co.y+.006,-.225));tooth=bm.faces.new(root+[vleft,vright]);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));commit_bm(ob,bm)
ob.name='Тыква — оболочка с созданным зубом';ob['Созданный полигон']='Зуб: новый n-угольник связан с верхней границей рта';ob['Проёмов до толщины']=hole_loops(ob)
for f in ob.data.polygons:f.use_smooth=True
cutstage=stage(ob,c,'02 — Create и Delete до толщины');m=ob.modifiers.new('Толщина оболочки 0.025 м','SOLIDIFY');m.thickness=.025;m.offset=-1
m=ob.modifiers.new('Мягкие кромки 0.004 м','BEVEL');m.width=.004;m.segments=2
curve=bpy.data.curves.new('Черешок','CURVE');curve.dimensions='3D';curve.resolution_u=16;curve.bevel_depth=.055;curve.bevel_resolution=4;sp=curve.splines.new('BEZIER');sp.bezier_points.add(2)
for p,co in zip(sp.bezier_points,[(0,0,.49),(.035,0,.65),(.11,.025,.76)]):p.co=co;p.handle_left_type=p.handle_right_type='AUTO'
stem=bpy.data.objects.new('Черешок',curve);s.collection.objects.link(stem);curve.materials.append(STEM)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.045,location=(0,-.06,-.25));flame=bpy.context.object;flame.name='Светящаяся сердцевина';flame.scale.z=1.7
em=mat('Свечение внутри',(1,.35,.025),0,.4);shader=em.node_tree.nodes.get('Principled BSDF');shader.inputs['Emission Color'].default_value=(1,.28,.012,1);shader.inputs['Emission Strength'].default_value=5;flame.data.materials.append(em)
d=bpy.data.lights.new('Тёплый свет внутри','POINT');d.energy=25;d.color=(1,.3,.035);d.shadow_soft_size=.06;light=bpy.data.objects.new('Тёплый свет внутри',d);s.collection.objects.link(light);light.location=(0,-.18,-.10);light.hide_set(True)
job('07_pumpkin_mesh',s,[cutstage],(2,-6,2));job('08_pumpkin_final',s,[ob,stem,flame],(1.4,-6,1.6));finish(s,c,[ob,stem,flame],(1.4,-6,1.6))

# 5 — отделение верхней части в новый меш; границы не дублируют внутренние грани.
s,c=scene(5,'Detach — отделённая часть');ob=sphere('Сфера — нижняя часть',.5,32,1);raw=stage(ob,c,'01 — целая сфера');selected=[p.index for p in ob.data.polygons if p.center.z>.18]
def submesh(source,faces,name):
    chosen=[source.data.polygons[i] for i in faces];ids=sorted({v for p in chosen for v in p.vertices});mapping={v:i for i,v in enumerate(ids)}
    return mesh(name,[tuple(source.data.vertices[i].co) for i in ids],[[mapping[v] for v in p.vertices] for p in chosen],1)
cap=submesh(ob,selected,'Отделённый верх — самостоятельный объект');body=submesh(ob,[p.index for p in ob.data.polygons if p.index not in selected],'Сфера после Detach');bpy.data.objects.remove(ob,do_unlink=True)
body.location.x=-.55;cap.location.x=.65;cap.location.z=.15;body['Операция']='Выбранные грани удалены из исходника и записаны в самостоятельный меш; общие граничные координаты продублированы.'
job('09_detach',s,[body,cap],(2,-6,2));finish(s,c,[body,cap],(2,-6,2))

def extrude_patch(ob,distance=.18,mode='GROUP',scale=1.,faces=None):
    bm=bm_of(ob);region=closest_faces(bm) if faces is None else [bm.faces[i] for i in faces];normals={v:v.normal.copy() for f in region for v in f.verts};avg=sum((f.normal for f in region),Vector()).normalized()
    # Сохраняется связная область в обоих режимах. Local меняет направления по вершинам.
    result=bmesh.ops.extrude_face_region(bm,geom=region);new=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    origin={tuple(round(x,7) for x in v.co):normal for v,normal in normals.items()};center=sum((v.co for v in new),Vector())/len(new)
    for v in new:
        direction=avg if mode=='GROUP' else origin[tuple(round(x,7) for x in v.co)]
        v.co=center+(v.co-center)*scale+direction*distance
    tops=[f for f in result['geom'] if isinstance(f,bmesh.types.BMFace)]
    # extrude_face_region оставляет исходные грани; удаление только faces создаёт открытую основу выдавливания.
    bmesh.ops.delete(bm,geom=region,context='FACES_ONLY')
    for f in tops:f.material_index=1
    bm.faces.index_update();topids=[f.index for f in tops];commit_bm(ob,bm);return topids

# 6 — все продолжения упражнения сохранены на отдельных копиях для сравнения.
s,c=scene(6,'Extrude Bevel Weld Tessellate');source=sphere('Исходная сфера упражнений',.5,32,0);source.data.materials.append(SELECTED);raw=stage(source,c,'00 — исходная сфера упражнений')
grouped=source;grouped.name='Extrude — Group';ids=extrude_patch(grouped,.18,'GROUP');group_stage=stage(grouped,c,'01 — только Group 0.18 м');grouped.name='Extrude — Group затем Local';extrude_patch(grouped,.18,'LOCAL',faces=ids)
bevels=[]
for sign,label in [(1,'выступ'),(-1,'впадина')]:
    ob=sphere('Bevel — '+label,.5,32,1);ob.data.materials.append(SELECTED);before=bstats(ob);extrude_patch(ob,sign*.16,'GROUP',scale=.65);counts(ob,'Операция Bevel',before);bevels.append(ob)
weld=sphere('Weld — три вершины кольца',.5,32,2);before=bstats(weld);bm=bm_of(weld);ring=sorted([v for v in bm.verts if abs(v.co.z-.5*math.cos(math.pi/16))<1e-6],key=lambda v:abs(math.atan2(math.sin(math.atan2(v.co.y,v.co.x)+math.pi/2),math.cos(math.atan2(v.co.y,v.co.x)+math.pi/2))))[:3]
weld.data.materials.append(SELECTED);weld_raw=stage(weld,c,'02 — до Weld');weld_raw['Контрольные вершины']=json.dumps([v.index for v in ring]);weld['Порог Weld']=.04;weld['Выбранных вершин']=3;bmesh.ops.remove_doubles(bm,verts=ring,dist=.04);commit_bm(weld,bm);counts(weld,'Weld — измерение',before)
tess=sphere('Tessellate — Edge сверху Face Center снизу',.5,32,3);before=bstats(tess);bm=bm_of(tess);upper=closest_faces(bm,(0,-.4,.26),4);lower=closest_faces(bm,(0,-.4,-.26),4)
tess.data.materials.append(SELECTED)
for f in upper+lower:f.material_index=1
lowerids=[f.index for f in lower];upperidx=[f.index for f in upper];tess_raw=stage(tess,c,'03 — четыре области до Tessellate')
# Перед Edge квадраты разделены диагоналями; на каждой треугольной грани вставлены середины рёбер.
tr=bmesh.ops.triangulate(bm,faces=upper)['faces'];edges=list({e for f in tr for e in f.edges});bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
bmesh.ops.poke(bm,faces=[f for f in lower if f.is_valid]);commit_bm(tess,bm);counts(tess,'Tessellate — измерение',before)
divide=stage(tess_raw,c,'04 — Divide одной грани');bm=bm_of(divide);f=closest_faces(bm,(.2,-.4,0),1)[0];new=bmesh.ops.poke(bm,faces=[f]);center=new['verts'][0];center.co+=Vector((.015,0,.015));commit_bm(divide,bm)
items=[grouped,*bevels,weld,tess];position_grid(items,3,1.45)
job('10_extrude_group',s,[group_stage],(2,-6,2));job('11_extrude_local',s,[grouped],(2,-6,2));job('12_bevel',s,bevels,(1,-7,2));job('13a_weld_before',s,[weld_raw],(0,-6,3));job('13_weld',s,[weld],(0,-6,3));job('14_tessellate',s,[tess],(0,-6,0));finish(s,c,items,(1,-9,2))

# 7 — локальное сглаживание; настоящее расширение/сужение выделения; остальные инструменты.
s,c=scene(7,'Edit Poly — локальные инструменты');smooth=sphere('MSmooth — один полигон',.5,32,0);before=bstats(smooth);bm=bm_of(smooth);f=closest_faces(bm,(0,-.4,.23),1)[0]
smooth.data.materials.append(SELECTED);f.material_index=1;smooth_raw=stage(smooth,c,'00 — один полигон до MSmooth');highlight(smooth_raw,faces=[f.index]);original=list(f.verts);edgefaces=bmesh.ops.subdivide_edges(bm,edges=list(f.edges),cuts=1,use_grid_fill=True);verts=[v for v in ({v for key in ['geom_inner','geom_split'] for v in edgefaces.get(key,[]) if isinstance(v,bmesh.types.BMVert)}|set(original)) if v.is_valid]
for v in verts:
    if v.co.length>1e-8:v.co=v.co.normalized()*.5
commit_bm(smooth,bm);counts(smooth,'Локальное MSmooth',before)
grow=sphere('Grow и Shrink — выделение',.5,32,1);grow.data.materials.append(SELECTED);bpy.context.view_layer.objects.active=grow
for ob2 in s.objects:ob2.select_set(False)
grow.select_set(True);bpy.context.tool_settings.mesh_select_mode=(False,False,True)
for p in grow.data.polygons:p.select=False
bm=bm_of(grow);idx=closest_faces(bm,(0,-.43,.18),1)[0].index;bm.free();grow.data.polygons[idx].select=True
grow_counts=[];grow_stages=[]
for index,op in enumerate(['initial','more','more','less']):
    bpy.ops.object.mode_set(mode='EDIT')
    if op=='more':bpy.ops.mesh.select_more()
    elif op=='less':bpy.ops.mesh.select_less()
    bm=bmesh.from_edit_mesh(grow.data);n=sum(f.select for f in bm.faces);grow_counts.append(n);bpy.ops.object.mode_set(mode='OBJECT');selection=[p.index for p in grow.data.polygons if p.select];highlight(grow,faces=selection)
    grow_stages.append(stage(grow,c,f'Grow {index} — {n} граней'))
grow['Grow и Shrink']=json.dumps(grow_counts)
flip=sphere('Flip — одна обратная нормаль',.5,32,2);bm=bm_of(flip);f=closest_faces(bm,(0,-.48,0),1)[0];flip.data.materials.append(SELECTED);f.material_index=1;f.normal_flip();commit_bm(flip,bm)
collapse=sphere('Collapse — четыре вершины в центр',.5,32,3);before=bstats(collapse);bm=bm_of(collapse);f=closest_faces(bm,(0,-.43,.18),1)[0];chosen=list(f.verts);co=sum((v.co for v in chosen),Vector())/len(chosen);bmesh.ops.pointmerge(bm,verts=chosen,merge_co=co);commit_bm(collapse,bm);counts(collapse,'Collapse — измерение',before)
planars=[]
for axis in 'XYZ':
    ob=sphere('Make Planar — '+axis,.5,32,len(planars));bm=bm_of(ob);faces=closest_faces(bm,(.25,-.37,.22),4);vs={v for f in faces for v in f.verts};a='XYZ'.index(axis);average=sum(v.co[a] for v in vs)/len(vs)
    ob.data.materials.append(SELECTED)
    for f in faces:f.material_index=1
    for v in vs:v.co[a]=average
    indices=[v.index for v in vs];commit_bm(ob,bm);group_vertices(ob,'Плоская область',indices);ob['Ось плоскости']=axis;ob['Координата плоскости']=average;planars.append(ob)
items=[smooth,grow,flip,collapse,*planars];position_grid(items,3,1.45)
job('15a_msmooth_before',s,[smooth_raw],(0,-6,1));job('15_msmooth',s,[smooth],(0,-6,1));job('16_grow',s,[grow_stages[0]],(0,-6,1));job('17_grow9',s,[grow_stages[1]],(0,-6,1));job('18_grow25',s,[grow_stages[2]],(0,-6,1));job('19_flip_collapse',s,[flip,collapse],(0,-6,1));job('20_planar',s,planars,(1,-7,2));finish(s,c,items,(1,-9,2))

# 8 — неправильный многоугольник внутри верхней грани Box, редактируемый Extrude.
s,c=scene(8,'Cut и Extrude области');outer=[(-.6,-.5),(0,-.5),(.6,-.5),(.6,0),(.6,.5),(0,.5),(-.6,.5),(-.6,0)];inner=[(-.35,-.26),(-.08,-.34),(.3,-.2),(.12,-.02),(.35,.24),(.02,.35),(-.36,.16),(-.22,-.03)]
verts=[(x,y,z) for z in [-.4,.4] for x,y in outer]+[(x,y,.4) for x,y in inner]
faces=[tuple(reversed(range(8)))]+[(j,(j+1)%8,(j+1)%8+8,j+8) for j in range(8)]+[(8+j,8+(j+1)%8,16+(j+1)%8,16+j) for j in range(8)]+[tuple(16+j for j in range(8))]
ob=mesh('Box — неправильная область Cut',verts,faces,1);chosen=len(faces)-1;attr=ob.data.attributes.new('Область Cut','BOOLEAN','FACE');attr.data[chosen].value=True;highlight(ob,faces=[chosen]);raw=stage(ob,c,'01 — разрезанная верхняя грань');N.add(ob,N.cut_extrude(),'Extrude — 0.35 м')
for p in ob.data.polygons:p.use_smooth=False
for kind in ['Hide Selected','Hide Unselected','Unhide All']:
    cp=stage(raw,c,kind+' — учебное состояние')
    for f in cp.data.polygons:f.hide=(f.index==chosen) if kind=='Hide Selected' else (f.index!=chosen) if kind=='Hide Unselected' else False
job('21_cut',s,[raw],(2,-3,4));job('22_cut_extrude',s,[ob],(2,-4,3));finish(s,c,[ob],(2,-4,3))

# 9 — редактируемая бикубическая NURBS-поверхность, а не притворный Edit Patch.
s,c=scene(9,'Editable Patch — собственный навес');bpy.ops.surface.primitive_nurbs_surface_surface_add();surface=bpy.context.object;surface.name='Навес — поверхность 4×4';sp=surface.data.splines[0];sp.use_endpoint_u=sp.use_endpoint_v=True;sp.order_u=sp.order_v=4;surface.data.resolution_u=surface.data.resolution_v=24;surface.data.materials.append(MATS[0])
for point in sp.points:
    x,y,z,w=point.co;x*=.55;y*=.4;point.co=(x,y,1.15+.35*(x/.825)**2-.28*(y/.6)**2+.12*x*y,1)
base=stage(surface,c,'01 — опорная NURBS-поверхность')
for p in base.data.splines[0].points:p.co.z=1.15
solid=surface.modifiers.new('Толщина навеса 0.018 м','SOLIDIFY');solid.thickness=.018
legs=[]
for point in [sp.points[i] for i in [0,3,12,15]]:
    x,y,z,w=point.co;leg=cylinder('Опора навеса',.026,z,1,16,bottom=0,material=2);leg.location.x=x;leg.location.y=y;legs.append(leg)
# Отдельная копия контрольной сетки для реального геометрического рисунка этапа.
net=[]
for i in range(4):
    for ids in [[i*4+j for j in range(4)],[j*4+i for j in range(4)]]:
        cv=bpy.data.curves.new('Контрольная линия','CURVE');cv.dimensions='3D';cv.bevel_depth=.006;cv.bevel_resolution=1;sp2=cv.splines.new('POLY');sp2.points.add(3)
        for p,index in zip(sp2.points,ids):p.co=surface.data.splines[0].points[index].co
        co=bpy.data.objects.new('Контрольная сетка 4×4',cv);c.objects.link(co);cv.materials.append(SELECTED);net.append(co)
surface['Аналог']='Бикубическая NURBS-поверхность 4×4, порядок 4, единичные веса и зажатые концы. Это отдельный тип Blender, не Editable Patch Autodesk.'
job('23_patch_controls',s,[surface]+net,(3,-5,3));job('24_patch_canopy',s,[surface]+legs,(3,-5,3));finish(s,c,[surface]+legs,(3,-5,3))

def make_hair(s,body,name,count,cut,scale,rand,col=None):
    data=bpy.data.hair_curves.new(name+' — кривые');ob=bpy.data.objects.new(name,data);(col or s.collection).objects.link(ob);data.surface=body;data.materials.append(HAIR);N.add(ob,N.hair(HAIR,count,cut,scale,rand),'Волосы — параметры методички');ob['Габаритный радиус']=1.;return ob

# 10 — полные 500000 и 250000 кривых, отдельный лимит только для viewport.
s,c=scene(10,'Hair and Fur — мех и щетина');body=sphere('Сфера — щетина R 0.5 м',.5,64,0);body.data.materials[0]=HAIR
hair=make_hair(s,body,'Щетина — 250000 волос',250000,100.,10.,10.)
densebody=stage(body,c,'01 — сфера густого меха');densehair=make_hair(s,densebody,'02 — мех 500000 волос',500000,50.,100.,40.,c)
job('25_fur_dense',s,[densebody,densehair],(2,-6,2));job('26_hair_bristle',s,[body,hair],(2,-6,2));finish(s,c,[body,hair],(2,-6,2))

if 'Scene' in bpy.data.scenes:bpy.data.scenes.remove(bpy.data.scenes['Scene'])
text=bpy.data.texts.new('ПРОЧТИ — лабораторная 11');text.write('Лабораторная 11, исходная методичка имеет внутренний номер 16.\n10 сцен = 10 заданий. F12 — итог сцены. Этапы находятся в исключённых коллекциях.\nОперации Edit Mesh/Edit Poly Blender хранит как редактируемые меши и копии этапов; это не одноимённые модификаторы.\nВолосы: в окне не больше Max Hairs 100000; рендер использует Hair Count целиком. «Полное количество» временно показывает все кривые и в окне.\nSurface 4×4 — аналог лоскутной поверхности; редактируется Tab, не конвертирован в меш.\nОтдельный вариант ИДЗ не выдавался. Собственные модели: бутон, тыква, навес.\nОткрытие не требует Auto Run Python. Сценарии построения нужны только для повторной сборки.\n')
bpy.context.window.scene=bpy.data.scenes['04 — Create Delete и тыква-светильник']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.clip_end=10000
        elif area.type=='PROPERTIES':area.spaces.active.context='MODIFIER'
for sc in bpy.data.scenes:sc.tool_settings.mesh_select_mode=(True,False,False) if sc['Задание']==1 else (False,True,False) if sc['Задание']==2 else (False,False,True)
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Лаба11_Blender.blend'),compress=True)
for record in RECORD:record['objects']=[o.name for o in bpy.data.scenes[record['scene']].collection.objects if o.type in ['MESH','CURVE','SURFACE','CURVES']]
(WORK/'render_jobs.json').write_text(json.dumps(JOBS,ensure_ascii=False,indent=2),encoding='utf-8');(WORK/'scenes.json').write_text(json.dumps(RECORD,ensure_ascii=False,indent=2),encoding='utf-8')
print('LAB11_BUILD_OK',len(bpy.data.scenes),'scenes',len(JOBS),'renders',flush=True)

