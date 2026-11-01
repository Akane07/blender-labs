"""Иллюстрации отчёта: preview — EEVEE; итог — Cycles CPU, 40 сэмплов."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from lab4_common import principled,look_at
FIG=ROOT/'work/lab9/figures';FIG.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/lab9/Лаба9_Blender.blend'),use_scripts=False)
PREVIEW='--preview' in sys.argv
ONLY=next((set(arg.split('=',1)[1].split(',')) for arg in sys.argv if arg.startswith('--only=')),None)
BLACK=principled('Линии иллюстраций','131D27',rough=.85)
GREY=principled('Серый иллюстраций','ACB4BE',rough=.6)
CYAN=principled('Синий иллюстраций','367EAD',rough=.4)
ORANGE=principled('Оранжевый иллюстраций','DF953D',rough=.4)

def wire(sc,source,thickness):
    sc.view_layers[0].update();dg=sc.view_layers[0].depsgraph
    me=bpy.data.meshes.new_from_object(source.evaluated_get(dg),depsgraph=dg)
    me.materials.clear();me.materials.append(BLACK)
    ob=bpy.data.objects.new('Каркас рисунка — '+source.name,me);sc.collection.objects.link(ob);ob.matrix_world=source.matrix_world.copy()
    md=ob.modifiers.new('Каркас','WIREFRAME');md.thickness=thickness;md.offset=1;md.use_replace=True
    return ob

def render(sc,key,allowed,eye=None,target=None,ortho=None,res=(1400,1000),wires=()):
    if ONLY is not None and key not in ONLY:return
    bpy.context.window.scene=sc
    for c in sc.collection.children:
        c.hide_render=False
        sc.view_layers[0].layer_collection.children[c.name].hide_viewport=False
    for ob in sc.objects:
        if ob.type in ['MESH','CURVE','FONT']:ob.hide_render=ob.name not in allowed
    wire_objects=[]
    for name,thick in wires:
        w=wire(sc,bpy.data.objects[name],thick);w.hide_render=False;wire_objects.append(w)
    cam=sc.camera
    if eye is not None:look_at(cam,eye,target)
    if ortho is not None:cam.data.ortho_scale=ortho
    sc.render.resolution_x,sc.render.resolution_y=res;sc.render.resolution_percentage=100
    sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG'
    sc.render.engine='BLENDER_EEVEE' if PREVIEW else 'CYCLES'
    if not PREVIEW:sc.cycles.device='CPU';sc.cycles.samples=40;sc.cycles.use_denoising=True
    sc.render.filepath=str(FIG/(key+'.png'))
    bpy.ops.render.render(write_still=True)
    for w in wire_objects:bpy.data.objects.remove(w,do_unlink=True)
    print('FIGURE_DONE '+key,flush=True)

if PREVIEW:
    for sc in bpy.data.scenes:
        main=next(c for c in sc.collection.children if c.name.startswith('Задание'))
        render(sc,'preview_'+sc.name[0],{o.name for o in main.objects},res=(1000,750))
else:
    for scene in bpy.data.scenes:
        stages=next(c for c in scene.collection.children if c.name.startswith('Этапы'))
        for ob in stages.objects:
            if ob.type=='MESH':
                ob.data.materials.clear();ob.data.materials.append(GREY)
                for poly in ob.data.polygons:poly.material_index=0
    sc=bpy.data.scenes['1 — Воздушный шар и стек']
    render(sc,'01_balloon_start',{'01 — Оболочка после среза, до модификаторов','05 — Корзина до Lattice'},wires=[('01 — Оболочка после среза, до модификаторов',.015),('05 — Корзина до Lattice',.035)])
    render(sc,'02_balloon_stages',{'03 — После Stretch, до общего Skew','07 — Корзина после Taper'},wires=[('03 — После Stretch, до общего Skew',.015)])
    main=next(c for c in sc.collection.children if c.name.startswith('Задание'))
    render(sc,'03_balloon_final',{o.name for o in main.objects})
    first=bpy.data.objects['04 — Шар со свёрнутым стеком'];second=bpy.data.objects['09 — Другой порядок: Skew перед Taper и Stretch']
    first.location.x=-7.5;second.location.x=7.5
    first.data.materials.clear();first.data.materials.append(CYAN)
    for p in first.data.polygons:p.material_index=0
    second.data.materials.clear();second.data.materials.append(ORANGE)
    for p in second.data.polygons:p.material_index=0
    render(sc,'04_stack_order',{first.name,second.name},eye=(20,-35,12),target=(.5,0,4),ortho=30,res=(1600,900))
    sc=bpy.data.scenes['2 — Часть цилиндра']
    render(sc,'05_cylinder_before',{'01 — Исходный цилиндр R 0.1, H 2'},eye=(3,-5,2.7),target=(0,0,1.5),ortho=.7,res=(1000,1000),wires=[('01 — Исходный цилиндр R 0.1, H 2',.002)])
    render(sc,'06_cylinder_subdivide',{'02 — Верхняя половина уплотнена'},eye=(3,-5,2.7),target=(0,0,1.5),ortho=.7,res=(1000,1000),wires=[('02 — Верхняя половина уплотнена',.0017)])
    render(sc,'07_cylinder_taper',{'Цилиндр — верхняя часть'},eye=(3,-5,2.8),target=(0,0,1),ortho=3.25,wires=[('Цилиндр — верхняя часть',.002)])
    sc=bpy.data.scenes['3 — Тор и клон фрагмента']
    before=bpy.data.objects['01 — Тор до сферизации']
    before.data.materials.clear();before.data.materials.append(CYAN);before.data.materials.append(ORANGE)
    for poly in before.data.polygons:poly.material_index=int(sum(before.data.vertices[i].co.x for i in poly.vertices)>=0)
    render(sc,'08_torus_before',{'01 — Тор до сферизации'},eye=(-3,0,16),target=(-3,0,0),ortho=6.4,res=(1100,1100),wires=[('01 — Тор до сферизации',.008)])
    render(sc,'09_torus_cast',{'Тор — сферизация правой части'},eye=(-3,0,16),target=(-3,0,0),ortho=6.4,res=(1100,1100),wires=[('Тор — сферизация правой части',.008)])
    render(sc,'10_torus_clone',{'Тор — сферизация правой части','Клон — отдельный объект'},eye=(5,-9,15),target=(0,0,0),ortho=12.4,res=(1500,950))
    sc=bpy.data.scenes['4 — Объект-ссылка']
    render(sc,'11_reference',{'База — Taper общий','Ссылка — общий Taper и свой Bend'},wires=[('База — Taper общий',.012),('Ссылка — общий Taper и свой Bend',.012)])
    ref=bpy.data.objects['Ссылка — общий Taper и свой Bend'];ref.modifiers[-1].show_viewport=False;ref.modifiers[-1].show_render=False
    render(sc,'12_reference_common_base',{'База — Taper общий',ref.name},wires=[('База — Taper общий',.012),(ref.name,.012)])
print('ALL FIGURES DONE',flush=True)
