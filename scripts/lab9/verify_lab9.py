"""Повторное открытие и проверки поведения, а не только существования файлов."""
import bpy, json, sys, math, runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'work/lab9';QA.mkdir(parents=True,exist_ok=True)
FILE=ROOT/'output/lab9/Лаба9_Blender.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE),use_scripts=False)
checks=[]

def check(label,condition,data=None):
    checks.append({'check':label,'ok':bool(condition),'data':data})
    if not condition:raise AssertionError(label+': '+str(data))

def coords(sc,ob):
    bpy.context.window.scene=sc;sc.view_layers[0].update()
    ev=ob.evaluated_get(sc.view_layers[0].depsgraph);me=ev.to_mesh()
    result=[tuple(v.co) for v in me.vertices];ev.to_mesh_clear();return result

def changed(a,b):return max((math.dist(x,y) for x,y in zip(a,b)),default=0)

try:
    check('Четыре сцены',len(bpy.data.scenes)==4)
    for sc in bpy.data.scenes:
        check(sc.name+' — камера и EEVEE',sc.camera is not None and sc.render.engine=='BLENDER_EEVEE')
        stages=next(c for c in sc.collection.children if c.name.startswith('Этапы'))
        check(sc.name+' — этапы скрыты',stages.hide_render and sc.view_layers[0].layer_collection.children[stages.name].hide_viewport)
    sc1=bpy.data.scenes['1 — Воздушный шар и стек'];ball=bpy.data.objects['Шар'];basket=bpy.data.objects['Корзина'];control=bpy.data.objects['Общий скос — параметры']
    drivers=[fc for ob in [ball,basket] for fc in ob.animation_data.drivers]
    coords(sc1,ball)
    check('Все общие драйверы простые и действующие',len(drivers)==10 and all(fc.driver.is_simple_expression and fc.driver.is_valid for fc in drivers),len(drivers))
    a=coords(sc1,ball);b=coords(sc1,basket)
    control['Скос']=.4;control.update_tag();sc1.frame_set(1)
    da=changed(a,coords(sc1,ball));db=changed(b,coords(sc1,basket))
    check('Общий скос меняет оба объекта',da>.01 and db>.01,{'ball_max_delta':da,'basket_max_delta':db})
    control['Скос']=.25;control.update_tag();sc1.frame_set(0)
    check('Свёрнутый стек сохранён отдельно',len(bpy.data.objects['04 — Шар со свёрнутым стеком'].modifiers)==0 and len(ball.modifiers)==3)
    sc2=bpy.data.scenes['2 — Часть цилиндра'];cyl=bpy.data.objects['Цилиндр — верхняя часть'];out=coords(sc2,cyl)
    lower=[v for v in cyl.data.vertices if v.co.z<.9999];upper=[v for v in cyl.data.vertices if v.co.z>=.9999]
    lower_delta=max(math.dist(tuple(v.co),out[v.index]) for v in lower)
    upper_delta=max(math.dist(tuple(v.co),out[v.index]) for v in upper)
    check('Нижняя часть цилиндра не деформируется',lower_delta<1e-6,lower_delta)
    check('Верхняя часть цилиндра деформируется',upper_delta>.05,upper_delta)
    check('Верхняя сетка стала плотнее',len(cyl.data.vertices)>352,len(cyl.data.vertices))
    tor=bpy.data.objects['Тор — сферизация правой части'];cast=tor.modifiers[0]
    check('Тор 48 x 48',len(tor.data.vertices)==48*48,len(tor.data.vertices))
    check('Cast 50% ограничен группой',cast.type=='CAST' and cast.factor==.5 and cast.vertex_group=='Правая часть')
    check('Клон фрагмента является отдельным мешем',bpy.data.objects['Клон — отдельный объект'].type=='MESH' and bpy.data.objects['Клон — отдельный объект'].data!=tor.data)
    sc4=bpy.data.scenes['4 — Объект-ссылка'];base=bpy.data.objects['База — Taper общий'];ref=bpy.data.objects['Ссылка — общий Taper и свой Bend']
    r1=coords(sc4,ref);base.modifiers[0].factor=-.1;sc4.view_layers[0].update();r2=coords(sc4,ref)
    check('Изменение базы передаётся ссылке',changed(r1,r2)>.01,changed(r1,r2))
    base.modifiers[0].factor=-.5
    check('Изгиб есть только у ссылки',not any(m.type=='SIMPLE_DEFORM' and m.deform_method=='BEND' for m in base.modifiers) and ref.modifiers[-1].deform_method=='BEND' and abs(ref.modifiers[-1].angle-math.pi/2)<1e-6)
    points=coords(sc4,ref);check('Ссылка содержит общую геометрию',len(points)==len(base.data.vertices),len(points))
    addon=runpy.run_path(str(Path(__file__).with_name('modifier_set_lab9.py')))
    addon['register']();check('Собственный набор содержит 10 кнопок',len(addon['ITEMS'])==10);addon['unregister']()
    check('Нет текстовых блоков автозапуска',not any(t.use_module for t in bpy.data.texts))
    bpy.context.window.scene=sc1
finally:
    (QA/'verification.json').write_text(json.dumps({'version':bpy.app.version_string,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))
