"""Рисунки для отчёта по лабе 7 (Cycles CPU). Запуск: .venv/bin/python scripts/lab7/render_lab7.py [-- имена]"""
import bpy, bmesh, math, sys, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG = os.path.join(ROOT, "build", "figs7") + "/"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab7", "Лаба7_Blender.blend"))
SC = {s.name[0]: s for s in bpy.data.scenes}


def mat(name, rgb, rough=0.6, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb + (1,)
    p.inputs["Roughness"].default_value = rough
    if emit:
        p.inputs["Emission Color"].default_value = rgb + (1,)
        p.inputs["Emission Strength"].default_value = emit
    return m


WIRE = mat("fig_wire", (0.01, 0.01, 0.012), 0.8)
AX = [mat("fig_x", (0.85, 0.08, 0.08), emit=0.6), mat("fig_y", (0.1, 0.7, 0.1), emit=0.6), mat("fig_z", (0.1, 0.25, 0.9), emit=0.6)]

rigs = {}
for key, sc in SC.items():
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
    sc.render.resolution_percentage = 100
    for c in sc.collection.children:
        c.hide_render = False
        sc.view_layers[0].layer_collection.children[c.name].hide_viewport = False
    cd = bpy.data.cameras.new("FigCam" + key); cd.clip_end = 1000
    cam = bpy.data.objects.new("FigCam" + key, cd); sc.collection.objects.link(cam)
    rigs[key] = (cam, sc.camera)


def gizmo(sc, name, origin, rot=(0, 0, 0), L=0.6, t=0.03):
    """Оси ориджина для рисунка (в Blender ориджин на рендере не виден)."""
    from mathutils import Euler, Matrix
    obs = []
    for i, m in enumerate(AX):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        s = [t, t, t]; s[i] = L
        off = [0, 0, 0]; off[i] = L / 2
        bmesh.ops.scale(bm, vec=s, verts=bm.verts); bmesh.ops.translate(bm, vec=off, verts=bm.verts)
        me = bpy.data.meshes.new(name + str(i)); bm.to_mesh(me); bm.free(); me.materials.append(m)
        o = bpy.data.objects.new(name + "_" + "xyz"[i], me); sc.collection.objects.link(o)
        o.location = origin; o.rotation_euler = Euler([math.radians(a) for a in rot])
        obs.append(o.name)
    return obs


def wire_copy(sc, o, th=0.008):
    c = o.copy(); c.data = o.data.copy(); c.name = o.name + "_wire"
    for m in list(c.modifiers):
        if m.type == 'NODES':
            c.modifiers.remove(m)
    sc.collection.objects.link(c)
    w = c.modifiers.new("wire", 'WIREFRAME'); w.thickness = th; w.use_even_offset = True
    c.data.materials.clear(); c.data.materials.append(WIRE)
    for s in c.material_slots:
        s.link = 'OBJECT'; s.material = WIRE
    return c.name


def render(name, key, visible, eye=None, target=None, ortho=None, lens=50, res=(1400, 900), scene_cam=False):
    if only and name not in only:
        return
    sc = SC[key]; cam, scam = rigs[key]
    for o in sc.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = o.name.startswith("Дерево (образец") or not any(
                o.name == v or (v.endswith("*") and o.name.startswith(v[:-1])) for v in visible)
    if scene_cam:
        sc.camera = scam
    else:
        cam.location = Vector(eye)
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'; cam.data.lens = lens
        sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = FIG + name + ".png"
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print("RENDERED", name)


O = bpy.data.objects

# ---------------- 1: опорная точка
sc = SC["1"]
st = O["Этап — ориджин в центре (как создан)"]; st.location.x = 0
cy = O["Цилиндр 6 граней"]
g1 = gizmo(sc, "gz_center", st.location.copy())
g2 = gizmo(sc, "gz_top", cy.location.copy())
w1 = wire_copy(sc, st); w2 = wire_copy(sc, cy)
E = dict(eye=(2.2, -3.0, 2.0), target=(0, 0, 0.55), lens=50, res=(1000, 900))
render("l7_pivot_center", "1", {w1, *g1}, **E)
render("l7_pivot_top", "1", {w2, *g2}, **E)

# ---------------- 2: перемещение/вращение/масштаб
base = ["Параллелепипед", "Цилиндр — сцена 2", "Тор", "Пол — сцена 2"]
render("l7_s2_before", "2", set(base) | {"Этап — пирамида до поворота", "Этап — шар 1 до масштабирования", "Этап — шар 2 до масштабирования"}, scene_cam=True, res=(1500, 850))
render("l7_s2_after", "2", set(base) | {"Пирамида (повёрнута на 90°)", "Шар 1*", "Шар 2*", "Шар 3*"}, scene_cam=True, res=(1500, 850))

# ---------------- 3: вестибюль
sc = SC["3"]
for i in (1, 2, 3):
    objs = [o for o in sc.objects if o.name.startswith(f"Этап {i} — ")]
    ws = [wire_copy(sc, o, 0.003) for o in objs]
    x = objs[0].location.x
    solid = {o.name for o in objs if not (i == 1 and "Основание" in o.name)}   # на этапе 1 основание — только каркас
    render(f"l7_v_stage{i}", "3", solid | set(ws) | {"Земля — вестибюль"},
           eye=(x + 1.2, -1.6, 1.1), target=(x, 0, 0.15), lens=50, res=(1100, 800))
vest = {"Основание Box01", "Цилиндр Cylinder01", "Купол Sphere01", "Стойка Box02", "Стойка Box03", "Столб Box04", "Перекладина Box05", "Земля — вестибюль"}
mirror = {o.name for o in O if o.name.endswith("(зеркальная копия)") and "Box" in o.name}
render("l7_v_front", "3", vest, eye=(0.15, -5, 0.3), target=(0.15, 0, 0.3), ortho=2.0, res=(1300, 700))
render("l7_v_result", "3", vest, eye=(1.7, -2.2, 1.3), target=(0.15, 0.05, 0.15), lens=45, res=(1300, 900))
render("l7_trees_top", "3", vest | {"П-образный путь (Line)"}, eye=(0.1, 0.1, 10), target=(0.1, 0.1001, 0), ortho=3.6, res=(1100, 1000))
render("l7_trees", "3", vest | {"П-образный путь (Line)"}, scene_cam=True, res=(1500, 900))
render("l7_mirror_top", "3", vest | mirror, eye=(0.2, 0, 10), target=(0.2, 0.0001, 0), ortho=1.9, res=(1100, 1000))
render("l7_vest_final", "3", vest | mirror | {"П-образный путь (Line)"}, scene_cam=True, res=(1500, 900))

# ---------------- 4: ориентация
fl = "Пол — сцена 4"
render("l7_orient_before", "4", {fl, "Цилиндр 1 (создан в виде сверху, повёрнут)", "Этап — цилиндр 2 до выравнивания (горизонтальный)"}, scene_cam=True, res=(1400, 800))
render("l7_orient_after", "4", {fl, "Цилиндр 1 (создан в виде сверху, повёрнут)", "Цилиндр 2 (создан в виде слева, выровнен по цилиндру 1)"}, scene_cam=True, res=(1400, 800))

# ---------------- 5: копии и экземпляры
E = dict(eye=(1.6, -5.0, 3.0), target=(1.6, 0, 0.35), lens=45, res=(1400, 800))
render("l7_copy_src", "5", {"Пол — сцена 5", "Этап — исходный цилиндр (6 граней)"}, eye=(0.6, -3.2, 2.0), target=(0, 0, 0.45), lens=45, res=(1100, 800))
render("l7_copies", "5", {"Пол — сцена 5", "Копия*"}, **E)
E2 = dict(E); E2["eye"] = (1.6, -2.8, 3.0); E2["target"] = (1.6, 2.2, 0.3)
render("l7_instances", "5", {"Пол — сцена 5", "Экземпляр*"}, **E2)

# ---------------- 6: клонирование с выравниванием
sc = SC["6"]
gm = []
for e in [O["Метка 1"], O["Метка 2"]]:
    gm += gizmo(sc, "gz_" + e.name, e.location.copy(), [math.degrees(a) for a in e.rotation_euler], L=0.5, t=0.025)
render("l7_marks", "6", {"Пол — сцена 6", "Исходный цилиндр", *gm}, scene_cam=True, res=(1400, 800))
render("l7_clones", "6", {"Пол — сцена 6", "Исходный цилиндр", "Клон*", *gm}, scene_cam=True, res=(1400, 800))

# ---------------- 7: массивы
render("l7_array", "7", {"Пол — сцена 7", "Цилиндр — массив 10 × 2"}, eye=(2.2, -7.5, 2.2), target=(1.9, 0, 1.4), lens=40, res=(1500, 900))
render("l7_array_own", "7", {"Пол — сцена 7", "Куб — круговой массив 12 шт.", "Ступень — лестница (Массив)"}, eye=(-0.8, -10.0, 6.5), target=(-0.8, 3.0, 0.6), lens=28, res=(1500, 900))

# ---------------- 8: ИДЗ
render("l7_idz", "8", {"*"}, scene_cam=True, res=(1920, 1080))
render("l7_idz2", "8", {"*"}, eye=(0.0, -24.0, 2.0), target=(0, 2.0, 3.0), lens=32, res=(1920, 1080))
print("ALL DONE")
