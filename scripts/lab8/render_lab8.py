"""Рисунки для отчёта по лабе 8 (Cycles CPU). Запуск: .venv/bin/python scripts/lab8/render_lab8.py [-- имена]"""
import bpy, math, sys, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG = os.path.join(ROOT, "build", "figs8") + "/"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab8", "Лаба8_Blender.blend"))
SC = {s.name[0]: s for s in bpy.data.scenes}
O = bpy.data.objects


def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb + (1,)
    p.inputs["Roughness"].default_value = rough
    return m


WIRE = mat("fig_wire", (0.01, 0.01, 0.012), 0.8)
GREY = mat("fig_grey", (0.55, 0.55, 0.57), 0.6)

rigs = {}
for key, sc in SC.items():
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
    sc.render.resolution_percentage = 100
    for c in sc.collection.children:
        c.hide_render = False
        sc.view_layers[0].layer_collection.children[c.name].hide_viewport = False
    cd = bpy.data.cameras.new("FigCam" + key); cd.clip_end = 2000
    cam = bpy.data.objects.new("FigCam" + key, cd); sc.collection.objects.link(cam)
    rigs[key] = (cam, sc.camera)


def to_grey(o):
    for s in o.material_slots:
        s.link = 'OBJECT'; s.material = GREY


def wire_copy(sc, o, th=0.03):
    c = o.copy(); c.data = o.data.copy(); c.name = o.name + "_wire"
    sc.collection.objects.link(c)
    w = c.modifiers.new("wire", 'WIREFRAME'); w.thickness = th; w.use_even_offset = True
    for s in c.material_slots:
        s.link = 'OBJECT'; s.material = WIRE
    if not c.material_slots:
        c.data.materials.append(WIRE)
    return c.name


def studio(sc, eye, target, energy=3.0):
    """Студийный свет со стороны камеры (для рисунков этапов)."""
    ld = bpy.data.lights.new("fig_key_" + sc.name[0], 'SUN'); ld.energy = energy; ld.angle = math.radians(10)
    o = bpy.data.objects.new("fig_key_" + sc.name[0], ld); sc.collection.objects.link(o)
    d = Vector(target) - Vector(eye)
    o.rotation_euler = (d + Vector((0.3, 0.3, -0.4)) * d.length).to_track_quat('-Z', 'Y').to_euler()
    return o


def render(name, key, visible, eye=None, target=None, ortho=None, lens=50, res=(1400, 900), scene_cam=False, frame=None):
    if only and name not in only:
        return
    sc = SC[key]; cam, scam = rigs[key]
    for o in sc.objects:
        if o.type in ('MESH', 'CURVE', 'SURFACE'):
            o.hide_render = not ("*" in visible or any(
                o.name == v or (v.endswith("*") and o.name.startswith(v[:-1])) for v in visible))
            if "*" in visible and (o.name.startswith("Этап") or o.name.startswith("Образец") or o.name.startswith("Вырез")):
                o.hide_render = True
    bpy.context.window.scene = sc
    if frame is not None:
        sc.frame_set(frame)
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


# ---------------- 1: чашка
sc = SC["1"]
E = dict(eye=(4.5, -7.5, 22), target=(0, 0, 2.0), lens=40, res=(1000, 900))
key1 = studio(sc, E["eye"], E["target"])
for i in (1, 2, 3):
    objs = [o for o in sc.objects if o.name.startswith(f"Этап {i} — ")]
    for o in objs:
        to_grey(o); o.location.x -= 12.0 * i
    ws = [wire_copy(sc, o, 0.025) for o in objs]
    render(f"l8_cup_s{i}", "1", {o.name for o in objs} | set(ws) | {"Столешница"}, **E)
final = [o for o in sc.objects if any(o.name.startswith(p) for p in ("Стенка", "Дно", "Ободок", "Кольцо", "Ручка"))]
key1.hide_render = True
render("l8_cup", "1", {o.name for o in final} | {"Столешница"}, scene_cam=True, res=(1400, 1000))

# ---------------- 2: лоскутные сетки
sc = SC["2"]
Q, T = "Quad Patch — сетка 4×4", "Tri Patch — сетка 4×4"
QS, TS = "Этап — Quad Patch до сглаживания", "Этап — Tri Patch до сглаживания"
ws_before = [wire_copy(sc, O[n], 0.04) for n in (QS, TS)]
ws_after = [wire_copy(sc, O[n], 0.025) for n in (Q, T)]
render("l8_patch_before", "2", {QS, TS, *ws_before}, eye=(0, -0.01, 30), target=(0, 0, 0), ortho=15, res=(1500, 700))
render("l8_patch_after_top", "2", {Q, T, *ws_after}, eye=(0, -0.01, 30), target=(0, 0, 0), ortho=15, res=(1500, 700))
render("l8_patch_after", "2", {Q, T, *ws_after}, eye=(0, -12.5, 7.5), target=(0, 0, 0.4), lens=40, res=(1500, 750))
# управляющие точки NURBS — шарики и рёбра управляющей сетки (на рендере их иначе не видно)
nu = O["NURBS-поверхность (лоскут 4×4 управляющих точки)"]
PM = mat("fig_pts", (0.9, 0.55, 0.05), 0.4)
import bmesh
bm = bmesh.new()
cps = [nu.matrix_basis @ Vector(p.co[:3]) for p in nu.data.splines[0].points]   # matrix_world после загрузки ещё не посчитан
for c in cps:
    r = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.12)
    bmesh.ops.translate(bm, vec=c, verts=r["verts"])
me = bpy.data.meshes.new("fig_cp"); bm.to_mesh(me); bm.free(); me.materials.append(PM)
cpo = bpy.data.objects.new("fig_cp", me); SC["2"].collection.objects.link(cpo)
cu = bpy.data.curves.new("fig_cage", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.03
for i in range(4):
    for line in ([cps[i * 4 + j] for j in range(4)], [cps[j * 4 + i] for j in range(4)]):
        sp = cu.splines.new('POLY'); sp.points.add(3)
        for pt, c in zip(sp.points, line):
            pt.co = (c.x, c.y, c.z, 1.0)
cu.materials.append(PM)
cage = bpy.data.objects.new("fig_cage", cu); SC["2"].collection.objects.link(cage)
render("l8_nurbs", "2", {"NURBS-поверхность*", "fig_cp", "fig_cage"}, eye=(10.0, -3.0, 9.0), target=(0, 9.0, 0.6), lens=32, res=(1200, 850))

# ---------------- 3: амортизатор
DE, DT = (3.0, -7.6, 3.8), (0.1, 0, 2.55)
for f in (0, 20, 40):
    render(f"l8_damper_f{f}", "3", {"*"}, eye=DE, target=DT, lens=45, res=(900, 1000), frame=f)
render("l8_damper_noboot", "3", {"Пол — амортизатор", "Нижняя*", "Верхняя*", "Амортизатор — основание (Base)",
                                 "Амортизатор — корпус (Main)", "Амортизатор — поршень (Piston)"}, eye=DE, target=DT, lens=45, res=(900, 1000), frame=20)

# ---------------- 4: пружина
main = {"Пол — пружина", "Основание (Pick Bottom Object)", "Груз (Pick Top Object)", "Пружина (круглое сечение, против часовой)"}
for f in (0, 20, 40):
    render(f"l8_spring_f{f}", "4", main, eye=(3.5, -12.0, 4.5), target=(0.2, 0, 2.6), lens=45, res=(900, 1000), frame=f)
render("l8_spring_shapes", "4", {"Пол — пружина", "Пружина — *"}, eye=(8.6, -6.0, 3.6), target=(8.6, 3.0, 1.5), lens=35, res=(1500, 800), frame=0)

# ---------------- 5: дом
sc = SC["5"]
E = dict(eye=(-9.0, -17.0, 11.0), target=(5.0, 3.5, 1.5), lens=35, res=(1500, 950))
key5 = studio(sc, E["eye"], E["target"], 2.0)
for n in ("Этап 1 — стены без проёмов", "Этап 2 — стены с проёмами"):
    to_grey(O[n])
w1 = wire_copy(sc, O["Этап 1 — стены без проёмов"], 0.03)
w2 = wire_copy(sc, O["Этап 2 — стены с проёмами"], 0.03)
render("l8_house_s1", "5", {"Земля — дом", "Этап 1 — стены без проёмов", w1, "Фундамент (цоколь)"}, **E)
render("l8_house_s2", "5", {"Земля — дом", "Этап 2 — стены с проёмами", w2, "Фундамент (цоколь)"}, **E)
key5.hide_render = True
house = {"Земля — дом", "Стены дома (Wall)", "Фундамент (цоколь)", "Дверь*", "Окно*", "Лестница*", "Дорожка к дому"}
render("l8_house_open", "5", house, **E)
render("l8_house", "5", {"*"}, scene_cam=True, res=(1920, 1080))
render("l8_house_front", "5", {"*"}, eye=(5.0, -12.0, 2.6), target=(5.0, 0, 2.3), lens=35, res=(1600, 900))
render("l8_house_top", "5", {"*"}, eye=(5.0, 3.75, 60), target=(5.0, 3.7501, 0), ortho=30, res=(1400, 1050))
render("l8_trees", "5", {"Земля — дом", "Образец растения*"}, eye=(42.0, -27.0, 5.0), target=(42.0, 0, 3.2), lens=30, res=(1700, 650))
render("l8_fence", "5", {"*"}, eye=(-11.0, -9.0, 2.2), target=(-6.0, -2.0, 0.9), lens=35, res=(1400, 850))
print("ALL DONE")
