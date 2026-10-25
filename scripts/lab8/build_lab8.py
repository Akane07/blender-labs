"""Лаба 8: простое моделирование — чашка из примитивов, лоскутные сетки, амортизатор (Damper),
пружина (Spring), ИДЗ «Дом» (стены, двери, окна, лестница, растения, изгородь).
Запуск: .venv/bin/python scripts/lab8/build_lab8.py"""
import bpy, bmesh, math, os, sys, re
from mathutils import Vector, Euler, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lab4_common import srgb_hex, new_collection, principled, add_camera, add_light, world

OUT_DIR = os.path.join(ROOT, "output", "lab8")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Лаба8_Blender.blend")
R = math.radians

bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- геометрия
def mesh_from(name, build):
    bm = bmesh.new()
    build(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return me


def obj(name, data, col, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), mat=None, smooth=False, parent=None):
    ob = bpy.data.objects.new(name, data)
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.location = loc
    ob.rotation_euler = Euler([R(a) for a in rot])
    ob.scale = scale
    if mat is not None and data is not None and hasattr(data, "materials"):
        for m in (mat if isinstance(mat, (list, tuple)) else [mat]):
            data.materials.append(m)
    if smooth and data is not None:
        for p in data.polygons:      # торцы цилиндров плоские, иначе «гладкое затенение» делает их выпуклыми на вид
            p.use_smooth = abs(p.normal.z) < 0.999
    return ob


def empty(name, col, loc=(0, 0, 0), kind='PLAIN_AXES', size=0.5, parent=None, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind; e.empty_display_size = size
    col.objects.link(e)
    if parent is not None:
        e.parent = parent
    e.location = loc
    e.rotation_euler = Euler([R(a) for a in rot])
    return e


def cylinder_mesh(name, sides, r, depth, z0=None, caps=True, r2=None):
    """z0 — где низ цилиндра (None — центр в нуле, как у Blender)."""
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=caps, segments=sides, radius1=r, radius2=r if r2 is None else r2, depth=depth)
        if z0 is not None:
            bmesh.ops.translate(bm, vec=(0, 0, z0 + depth / 2), verts=bm.verts)
    return mesh_from(name, b)


def box_mesh(name, dims, center=(0, 0, 0)):
    def b(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
        bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return mesh_from(name, b)


def box(name, col, dims, center, mat=None, rot=(0, 0, 0), parent=None):
    """Параллелепипед: куб со стороной 1 и «Размеры» через масштаб (как в лабе 7)."""
    return obj(name, box_mesh(name, (1, 1, 1)), col, loc=center, rot=rot, scale=dims, mat=mat, parent=parent)


def torus_mesh(name, R1, R2, n=48, m=16, keep=None):
    """Тор в плоскости XY. keep(угол) — оставить только часть кольца (аналог Slice в 3ds Max)."""
    def b(bm):
        rings = []
        idx = [i for i in range(n + 1 if keep else n) if keep is None or keep(2 * math.pi * i / n)]
        for i in idx:
            a = 2 * math.pi * i / n
            ring = []
            for j in range(m):
                t = 2 * math.pi * j / m
                ring.append(bm.verts.new(((R1 + R2 * math.cos(t)) * math.cos(a), (R1 + R2 * math.cos(t)) * math.sin(a), R2 * math.sin(t))))
            rings.append(ring)
        pairs = list(zip(range(len(rings)), list(range(1, len(rings))) + ([0] if keep is None else [])))
        for i, k in pairs:
            if k >= len(rings):
                continue
            for j in range(m):
                bm.faces.new((rings[i][j], rings[k][j], rings[k][(j + 1) % m], rings[i][(j + 1) % m]))
    return mesh_from(name, b)


def stage_collection(sc, name):
    col = new_collection(sc, name)
    col.hide_render = True
    sc.view_layers[0].layer_collection.children[col.name].hide_viewport = True
    return col


def setup_scene(sc, sky="BFD3E6", strength=0.9, frames=(1, 250)):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.unit_settings.system = 'METRIC'
    sc.frame_start, sc.frame_end = frames
    world(sc, "Мир — " + sc.name, sky, strength)


def ground(col, size, name, mat):
    me = mesh_from(name, lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2))
    return obj(name, me, col, mat=mat)


def keys(ob, path, frames_vals, interp='BEZIER'):
    for f, v in frames_vals:
        setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f)
    ad = ob.animation_data
    if ad and ad.action:
        for fc in _fcurves(ad):
            for kp in fc.keyframe_points:
                kp.interpolation = interp


def _fcurves(ad):
    act = ad.action
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return act.fcurves
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out


# ---------------------------------------------------------------- материалы
def ceramic(name, hexcol):
    return principled(name, hexcol, rough=0.25, coat=0.6, coat_rough=0.05)


M_GREY = principled("Серый", "A8A8AC", rough=0.6)
M_CUP = ceramic("Керамика (чашка)", "2F6DB5")
M_CUP_IN = ceramic("Керамика белая", "F2EFE8")
M_TABLE = principled("Стол (дерево)", "8A5A35", rough=0.55)
M_PATCH_Q = principled("Лоскут Quad", "4A90D9", rough=0.5)
M_PATCH_T = principled("Лоскут Tri", "E07B2A", rough=0.5)
M_PATCH_N = principled("NURBS-поверхность", "3D9B4F", rough=0.5)
M_METAL = principled("Металл (корпус)", "3A4A5C", rough=0.3, metallic=0.9)
M_CHROME = principled("Хром (шток)", "D8DCE0", rough=0.08, metallic=1.0)
M_RUBBER = principled("Резина (кожух)", "1E1E1E", rough=0.7)
M_RED = principled("Красный", "C0392B", rough=0.45)
M_YELLOW = principled("Жёлтый", "E0B020", rough=0.5)
M_SPRING = principled("Сталь пружины", "B8BCC2", rough=0.25, metallic=1.0)
M_WALL = principled("Стены (штукатурка)", "E9DFC9", rough=0.85)
M_BASE = principled("Цоколь (камень)", "8C8378", rough=0.9)
M_ROOF = principled("Кровля (черепица)", "9E3B26", rough=0.6)
M_FRAME = principled("Рамы (белые)", "F4F4F2", rough=0.4)
M_DOOR = principled("Дверь (дерево)", "6B3E1E", rough=0.5)
M_GLASS = principled("Стекло", "9CC3DA", rough=0.05, metallic=0.2, ior_level=1.0)
M_STEP = principled("Ступени (бетон)", "B5B0A8", rough=0.85)
M_GRASS = principled("Трава", "5E8A3A", rough=0.95)
M_PATH = principled("Дорожка", "B9AE98", rough=0.9)
M_BARK = principled("Кора", "5A3B22", rough=0.85)
M_LEAF = principled("Листва", "3C7A2E", rough=0.7)
M_FENCE = principled("Забор (дерево)", "A57A4B", rough=0.7)

# ================================================================ 1 — Чашка
s1 = bpy.context.scene
s1.name = "1 — Чашка (стандартные примитивы)"
setup_scene(s1, sky="E8E4DC", strength=0.8)
cc = new_collection(s1, "Чашка (Tube + Cylinder + 3 Torus)")
st = stage_collection(s1, "Этапы чашки (скрыто)")
env = new_collection(s1, "Стол, камера и свет")
TUBE_R1, TUBE_R2, TUBE_H = 4.0, 3.7, 9.0


def cup(col, stage, dx=0.0, suf=""):
    """stage 1: Tube; 2: + дно; 3: + ободок и кольцо у дна; 4: + ручка."""
    parts = []
    # Tube = цилиндр без оснований + «Объёмность» внутрь (R1 − R2 = толщина стенки)
    tube = obj("Стенка (Tube: R1 4, R2 3,7, H 9)" + suf, cylinder_mesh("Стенка" + suf, 48, TUBE_R1, TUBE_H, z0=0, caps=False),
               col, loc=(dx, 0, 0), mat=[M_CUP, M_CUP_IN], smooth=True)
    so = tube.modifiers.new("Объёмность (R1 − R2 = 0,3)", 'SOLIDIFY')
    so.thickness = TUBE_R1 - TUBE_R2; so.offset = -1.0; so.use_even_offset = True; so.material_offset = 1
    parts.append(tube)
    if stage >= 2:
        parts.append(obj("Дно (Cylinder: R 3,8, H 0,4)" + suf, cylinder_mesh("Дно" + suf, 48, 3.8, 0.4, z0=0), col, loc=(dx, 0, 0), mat=M_CUP_IN, smooth=True))
    if stage >= 3:
        parts.append(obj("Ободок (Torus 1: R1 3,85, R2 0,2)" + suf, torus_mesh("Ободок" + suf, 3.85, 0.2), col, loc=(dx, 0, TUBE_H), mat=M_CUP, smooth=True))
        parts.append(obj("Кольцо у дна (Torus 2: R1 3,85, R2 0,25)" + suf, torus_mesh("Кольцо у дна" + suf, 3.85, 0.25), col, loc=(dx, 0, 0.25), mat=M_CUP, smooth=True))
    if stage >= 4:
        # ручка — тор, у которого удалена половина, попадающая внутрь чашки (в 3ds Max — Slice)
        hm = torus_mesh("Ручка" + suf, 2.0, 0.4, n=48, m=16, keep=lambda a: math.cos(a) >= -1e-6)
        parts.append(obj("Ручка (Torus 3: R1 2, R2 0,4, половина)" + suf, hm, col, loc=(dx + 3.85, 0, 5.0), rot=(90, 0, 0), scale=(1, 1.15, 1), mat=M_CUP, smooth=True))
    return parts


cup(cc, 4)
for i in (1, 2, 3):
    for o in cup(st, i, dx=12.0 * i, suf=f" — этап {i}"):
        o.name = f"Этап {i} — " + o.name.split(" — этап")[0]
box("Столешница", env, (40, 26, 1.0), (6, 4, -0.5), M_TABLE)
add_light(env, "Солнце — чашка", 'SUN', (50, 0, 35), 3.0, angle_deg=4)
add_light(env, "Заполняющий — чашка", 'SUN', (65, 0, 200), 0.8, angle_deg=25)
add_camera(s1, env, "Камера — чашка", (13, -21, 15), (0.8, 0, 4.2), lens=50)

# ================================================================ 2 — Лоскутные сетки
s2 = bpy.data.scenes.new("2 — Лоскутные сетки (задание 1)")
setup_scene(s2)
cq = new_collection(s2, "Сетки и сглаживание (аналог Quad/Tri Patch + HSDS)")
cn = new_collection(s2, "NURBS-поверхность (лоскутная поверхность Blender)")
st = stage_collection(s2, "Этапы сеток (скрыто)")
env = new_collection(s2, "Камера и свет — сетки")
PATCH = 6.0


def patch_mesh(name, seg=4, raise_=2.0):
    def b(bm):
        bmesh.ops.create_grid(bm, x_segments=seg, y_segments=seg, size=PATCH / 2)
        for v in bm.verts:            # центральная вершина поднята — так видно, как сглаживание меняет форму
            if abs(v.co.x) < 1e-4 and abs(v.co.y) < 1e-4:
                v.co.z = raise_
    return mesh_from(name, b)


def patch(col, name, dx, mat, tri, subsurf):
    o = obj(name, patch_mesh(name), col, loc=(dx, 0, 0), mat=mat, smooth=True)
    if tri:
        t = o.modifiers.new("Триангулировать (Tri Patch)", 'TRIANGULATE')
        t.quad_method = 'FIXED'
    if subsurf:
        s = o.modifiers.new("Подразделение (аналог HSDS)", 'SUBSURF')
        s.levels = 2; s.render_levels = 2
    return o


patch(cq, "Quad Patch — сетка 4×4", -4.0, M_PATCH_Q, False, True)
patch(cq, "Tri Patch — сетка 4×4", 4.0, M_PATCH_T, True, True)
patch(st, "Этап — Quad Patch до сглаживания", -4.0, M_PATCH_Q, False, False)
patch(st, "Этап — Tri Patch до сглаживания", 4.0, M_PATCH_T, True, False)
# NURBS-поверхность создаётся оператором (в текущей сцене) — потом переносим в сцену 2
bpy.ops.surface.primitive_nurbs_surface_surface_add(radius=3.0, location=(0, 9.0, 0))
nu = bpy.context.active_object
nu.name = "NURBS-поверхность (лоскут 4×4 управляющих точки)"
for c in list(nu.users_collection):
    c.objects.unlink(nu)
cn.objects.link(nu)
pts = nu.data.splines[0].points
for i, p in enumerate(pts):                         # приподнять 4 внутренние точки — получится «холм»
    u, v = i % 4, i // 4
    if u in (1, 2) and v in (1, 2):
        p.co = (p.co[0], p.co[1], 2.5, p.co[3])
nu.data.materials.append(M_PATCH_N)
nu.data.splines[0].use_smooth = True
nu.data.splines[0].use_endpoint_u = nu.data.splines[0].use_endpoint_v = True   # «Конечная точка»: поверхность доходит до крайних точек
add_light(env, "Солнце — сетки", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s2, env, "Камера — сетки", (0, -17, 12), (0, 2.5, 0.5), lens=40)

# ================================================================ 3 — Амортизатор (Damper)
s3 = bpy.data.scenes.new("3 — Амортизатор Damper (задание 2)")
setup_scene(s3, frames=(0, 80))
cd = new_collection(s3, "Амортизатор (Damper)")
cb = new_collection(s3, "Опорные объекты (Pick Base / Pick Piston)")
env = new_collection(s3, "Камера и свет — амортизатор")
ground(env, 20, "Пол — амортизатор", M_GREY)
BASE_D, BASE_H, MAIN_D, MAIN_H, PIST_D, PIST_L = 0.9, 0.2, 0.6, 2.2, 0.16, 2.4

# опорные объекты (их ориджины — точки крепления, как Pivot у 3ds Max)
bot = obj("Нижняя опора (Pick Base Object)", box_mesh("Нижняя опора", (1.2, 0.8, 0.4), (0, 0, -0.2)), cb, loc=(0, 0, 0.4), mat=M_RED)
top = obj("Верхняя опора (Pick Piston Object)", box_mesh("Верхняя опора", (1.6, 0.8, 0.4), (0, 0, 0.2)), cb, loc=(0.0, 0, 4.6), mat=M_YELLOW)
# анимация верхней опоры: поршень вдвигается/выдвигается, амортизатор наклоняется
keys(top, "location", [(0, Vector((0.0, 0, 4.6))), (20, Vector((0.6, 0, 3.6))), (40, Vector((-0.5, 0, 4.0))), (60, Vector((0.3, 0, 4.9))), (80, Vector((0.0, 0, 4.6)))])

# основание + корпус: ориджин в точке нижнего крепления, ось Z направлена на верхнюю опору
base = obj("Амортизатор — основание (Base)", cylinder_mesh("Основание", 32, BASE_D / 2, BASE_H, z0=0), cd, mat=M_METAL, smooth=True)
base.location = bot.location
c = base.constraints.new('DAMPED_TRACK'); c.target = top; c.track_axis = 'TRACK_Z'
main = obj("Амортизатор — корпус (Main)", cylinder_mesh("Корпус", 32, MAIN_D / 2, MAIN_H, z0=BASE_H), cd, mat=M_METAL, smooth=True, parent=base)
bv = main.modifiers.new("Фаска (Fillet 1, Fillet 2)", 'BEVEL')
bv.width = 0.06; bv.segments = 4; bv.limit_method = 'ANGLE'
main_top = empty("Верх корпуса (точка для кожуха)", cd, loc=(0, 0, BASE_H + MAIN_H), size=0.2, parent=base)
# поршень: ориджин в точке верхнего крепления, вытянут вниз (−Z), смотрит на нижнюю опору
piston = obj("Амортизатор — поршень (Piston)", cylinder_mesh("Поршень", 24, PIST_D / 2, PIST_L, z0=-PIST_L), cd, mat=M_CHROME, smooth=True)
piston.location = top.location
c = piston.constraints.new('COPY_LOCATION'); c.target = top
c = piston.constraints.new('DAMPED_TRACK'); c.target = bot; c.track_axis = 'TRACK_NEGATIVE_Z'
c = base.constraints.new('COPY_LOCATION'); c.target = bot
base.constraints.move(1, 0)
# кожух (Boot): гофра вдоль +Y, «Растяжение» до верха корпуса — длина меняется вместе с ходом поршня
BOOT_L = 4.6 - 0.4 - BASE_H - MAIN_H


def boot_mesh(name, L, r1=0.22, r2=0.3, folds=8, seg=24):
    def b(bm):
        rings = []
        n = folds * 2
        for k in range(n + 1):
            y = L * k / n
            r = r2 if k % 2 else r1
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), y, r * math.sin(2 * math.pi * j / seg))) for j in range(seg)])
        for k in range(n):
            for j in range(seg):
                bm.faces.new((rings[k][j], rings[k][(j + 1) % seg], rings[k + 1][(j + 1) % seg], rings[k + 1][j]))
    return mesh_from(name, b)


boot = obj("Амортизатор — кожух (Boot)", boot_mesh("Кожух", BOOT_L), cd, mat=M_RUBBER, smooth=True)
c = boot.constraints.new('COPY_LOCATION'); c.target = top
c = boot.constraints.new('STRETCH_TO'); c.target = main_top
c.rest_length = BOOT_L; c.volume = 'NO_VOLUME'
add_light(env, "Солнце — амортизатор", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_light(env, "Заполняющий — амортизатор", 'SUN', (60, 0, 200), 0.8, angle_deg=20)
add_camera(s3, env, "Камера — амортизатор", (4.2, -10.2, 5.0), (0.1, 0, 2.55), lens=50)

# ================================================================ 4 — Пружина (Spring)
s4 = bpy.data.scenes.new("4 — Пружина Spring (задание 3)")
setup_scene(s4, frames=(0, 80))
cs = new_collection(s4, "Пружина между объектами")
cw = new_collection(s4, "Формы сечения и направление витков (Wire Shape, CCW/CW)")
env = new_collection(s4, "Камера и свет — пружина")
ground(env, 30, "Пол — пружина", M_GREY)
SP_R, TURNS = 0.8, 8


def profile(name, shape, r_wire=0.1, R=SP_R):
    """Сечение витка в плоскости XZ, сдвинутое от оси на радиус пружины."""
    def b(bm):
        if shape == 'ROUND':
            pts = [(r_wire * math.cos(2 * math.pi * k / 12), r_wire * math.sin(2 * math.pi * k / 12)) for k in range(12)]
        elif shape == 'RECT':
            a, h = r_wire * 0.9, r_wire * 1.3
            pts = [(-a, -h), (a, -h), (a, h), (-a, h)]
        else:   # D-section: полукруг, плоская сторона внутрь
            pts = [(0.0, -r_wire)] + [(r_wire * math.sin(math.pi * k / 10), -r_wire * math.cos(math.pi * k / 10)) for k in range(1, 10)] + [(0.0, r_wire)]
        vs = [bm.verts.new((R + x, 0, z)) for x, z in pts]
        for i in range(len(vs)):
            bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
    return mesh_from(name, b)


def spring(name, col, shape, turns, height, cw=False, loc=(0, 0, 0)):
    o = obj(name, profile(name, shape), col, loc=loc, mat=M_SPRING)
    m = o.modifiers.new("Винт (Turns = Итераций)", 'SCREW')
    m.axis = 'Z'; m.angle = R(-360 if cw else 360); m.steps = 32; m.render_steps = 32
    m.iterations = turns; m.screw_offset = height / turns; m.use_smooth_shade = True; m.use_merge_vertices = True
    return o, m


# основание и груз — ориджины на поверхностях, к которым крепится пружина
plate = obj("Основание (Pick Bottom Object)", box_mesh("Основание", (2.6, 2.6, 0.3), (0, 0, -0.15)), cs, loc=(0, 0, 0.3), mat=M_RED)
weight = obj("Груз (Pick Top Object)", box_mesh("Груз", (2.2, 2.2, 1.2), (0, 0, 0.6)), cs, loc=(0, 0, 4.3), mat=M_YELLOW)
keys(weight, "location", [(0, Vector((0, 0, 4.3))), (20, Vector((0, 0, 2.4))), (40, Vector((0.6, 0, 5.2))), (60, Vector((0, 0, 3.0))), (80, Vector((0, 0, 4.3)))])
sp, m = spring("Пружина (круглое сечение, против часовой)", cs, 'ROUND', TURNS, 4.0)
c = sp.constraints.new('COPY_LOCATION'); c.target = plate
c = sp.constraints.new('DAMPED_TRACK'); c.target = weight; c.track_axis = 'TRACK_Z'
fc = m.driver_add("screw_offset"); d = fc.driver; d.type = 'SCRIPTED'
v = d.variables.new(); v.name = "dist"; v.type = 'LOC_DIFF'; v.targets[0].id = plate; v.targets[1].id = weight
v = d.variables.new(); v.name = "turns"; v.type = 'SINGLE_PROP'; v.targets[0].id = sp
v.targets[0].data_path = 'modifiers["Винт (Turns = Итераций)"].iterations'
d.expression = "dist / turns"
assert d.is_simple_expression
for i, (shape, cwise, nm) in enumerate([('ROUND', False, "круглое (Round Wire), против часовой (CCW)"),
                                        ('RECT', False, "прямоугольное (Rectangular Wire), против часовой (CCW)"),
                                        ('DSEC', False, "полукруглое (D-Section Wire), против часовой (CCW)"),
                                        ('ROUND', True, "круглое, по часовой стрелке (CW)")]):
    spring("Пружина — " + nm, cw, shape, 6, 3.0, cw=cwise, loc=(5.0 + 2.4 * i, 3.0, 0))
add_light(env, "Солнце — пружина", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_light(env, "Заполняющий — пружина", 'SUN', (60, 0, 200), 0.8, angle_deg=20)
add_camera(s4, env, "Камера — пружина", (6.5, -14.0, 6.0), (4.6, 1.5, 2.0), lens=35)

# ================================================================ 5 — ИДЗ «Дом»
s5 = bpy.data.scenes.new("5 — ИДЗ «Дом» (AEC-объекты, растения, изгородь)")
setup_scene(s5, sky="9EC6E8", strength=1.0)
cwall = new_collection(s5, "Стены (Wall)")
ccut = new_collection(s5, "Проёмы — вырезы для дверей и окон (скрыто)")
cdoor = new_collection(s5, "Двери (Door)")
cwin = new_collection(s5, "Окна (Window)")
cstair = new_collection(s5, "Лестница (Stair)")
croof = new_collection(s5, "Фундамент и крыша")
ctree = new_collection(s5, "Растения (Foliage)")
cfence = new_collection(s5, "Изгородь (Railing)")
st = stage_collection(s5, "Этапы дома и образцы растений (скрыто)")
env = new_collection(s5, "Камера, свет, земля — дом")
ccut.hide_render = True
s5.view_layers[0].layer_collection.children[ccut.name].hide_viewport = True
ground(env, 120, "Земля — дом", M_GRASS)

HX, HY = 10.0, 7.0          # дом по осям стен
FOUND = 0.45                # высота цоколя
WALL_H, WALL_W = 3.0, 0.3
box("Фундамент (цоколь)", croof, (HX + 0.7, HY + 0.7, FOUND), (HX / 2, HY / 2, FOUND / 2), M_BASE)


def wall_object(name, col, pts, cutters=None, closed=True):
    """Аналог Wall: контур из рёбер → «Винт» (угол 0 = вытягивание вверх, Height) → «Объёмность» (Width, Justification)
    → «Логический» (вычитание проёмов)."""
    def b(bm):
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        for i in range(len(vs) - (0 if closed else 1)):
            bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
    o = obj(name, mesh_from(name, b), col, loc=(0, 0, FOUND), mat=M_WALL)
    h = o.modifiers.new("Винт — высота (Height 3)", 'SCREW')
    h.angle = 0; h.screw_offset = WALL_H; h.steps = 1; h.render_steps = 1; h.iterations = 1; h.axis = 'Z'
    h.use_smooth_shade = False
    w = o.modifiers.new("Объёмность — Width, Justification", 'SOLIDIFY')
    w.thickness = WALL_W; w.offset = 0.0; w.use_even_offset = True
    if cutters:
        bl = o.modifiers.new("Логический — проёмы", 'BOOLEAN')
        bl.operation = 'DIFFERENCE'; bl.operand_type = 'COLLECTION'; bl.collection = cutters; bl.solver = 'EXACT'
    return o


OUTLINE = [(0, 0), (HX, 0), (HX, HY), (0, HY)]
wall_object("Стены дома (Wall)", cwall, OUTLINE, ccut)
wall_object("Этап 1 — стены без проёмов", st, OUTLINE)

FY = 0.0                    # фасад — стена y = 0
Z0 = FOUND


def cutter(name, x, y, z, w, h, axis='Y'):
    d = (w, 1.0, h) if axis == 'Y' else (1.0, w, h)
    return box("Вырез — " + name, ccut, d, (x, y, z + h / 2))


def frame(name, col, cx, cy, z, w, h, axis='Y', t=0.08, depth=0.12, mat=M_FRAME, sill=True):
    """Коробка проёма (рама): 4 бруска вокруг отверстия w × h в стене, ось нормали — Y (фасад) или X (бок)."""
    parts = []
    def add(nm, dx, dz, sx, sz):
        dims = (sx, depth, sz) if axis == 'Y' else (depth, sx, sz)
        ctr = (cx + dx, cy, z + dz) if axis == 'Y' else (cx, cy + dx, z + dz)
        parts.append(box(f"{name} — {nm}", col, dims, ctr, mat))
    add("рама левая", -w / 2 + t / 2, h / 2, t, h)
    add("рама правая", w / 2 - t / 2, h / 2, t, h)
    add("рама верх", 0, h - t / 2, w - 2 * t, t)     # между стойками — без наложения граней в углах
    if sill:
        add("рама низ", 0, t / 2, w - 2 * t, t)
    return parts


# --- дверь (Pivot Door): коробка + полотно на петле, «Открыто» = поворот петли
DX, DW, DH = 3.0, 1.0, 2.2
cutter("дверь", DX, FY, Z0, DW, DH)
frame("Дверь поворотная (Pivot Door)", cdoor, DX, FY, Z0, DW, DH, sill=False, depth=WALL_W + 0.04)
hinge = empty("Дверь — петля (поворот = Open, 70°)", cdoor, loc=(DX - DW / 2 + 0.08, FY - WALL_W / 2, Z0), size=0.3, rot=(0, 0, -70))
leaf = box("Дверь — полотно", cdoor, (DW - 0.16, 0.05, DH - 0.1), ((DW - 0.16) / 2, -0.025, (DH - 0.1) / 2 + 0.02), M_DOOR, parent=hinge)
box("Дверь — ручка", cdoor, (0.12, 0.06, 0.03), ((DW - 0.16) - 0.12, -0.08, 1.0), M_CHROME, parent=hinge)


# --- окна четырёх типов
def window(kind, cx, cy, w=1.4, h=1.4, sill_z=0.9, axis='Y', where=""):
    z = Z0 + sill_z
    names = {"FIXED": "Окно глухое (Fixed)", "CASE": "Окно распашное (Casement)", "SLIDE": "Окно раздвижное (Sliding)", "PIVOT": "Окно среднеповоротное (Pivoted)"}
    nm = names[kind] + f" — {where}"
    cutter(nm, cx, cy, z, w, h, axis)
    frame(nm, cwin, cx, cy, z, w, h, axis, depth=WALL_W + 0.04)
    sgn = -1 if (axis == 'Y' and cy < 1) or (axis == 'X' and cx < 1) else 1   # наружу
    def pane(n, dx, dz, pw, ph, off=0.0, parent=None, local=False):
        dims = (pw, 0.03, ph) if axis == 'Y' else (0.03, pw, ph)
        if local:
            return box(f"{nm} — {n}", cwin, dims, (dx, off, dz) if axis == 'Y' else (off, dx, dz), M_GLASS, parent=parent)
        ctr = (cx + dx, cy + off, z + dz) if axis == 'Y' else (cx + off, cy + dx, z + dz)
        return box(f"{nm} — {n}", cwin, dims, ctr, M_GLASS)
    iw, ih = w - 0.16, h - 0.16
    if kind == "FIXED":
        pane("стекло", 0, h / 2, iw, ih)
    elif kind == "SLIDE":       # две створки в разных плоскостях, одна сдвинута (Open %)
        pane("створка неподвижная", -iw / 4, h / 2, iw / 2, ih, off=0.04)
        pane("створка сдвинута на 40 %", -iw / 4 + 0.4 * iw / 2, h / 2, iw / 2, ih, off=-0.04)
    elif kind == "CASE":        # створка на вертикальной петле
        hx = (cx - w / 2 + 0.08, cy + sgn * WALL_W / 2, z + 0.08) if axis == 'Y' else (cx + sgn * WALL_W / 2, cy - w / 2 + 0.08, z + 0.08)
        hg = empty(f"{nm} — петля (Open 35°)", cwin, loc=hx, size=0.2, rot=(0, 0, sgn * 35 if axis == 'Y' else -sgn * 35 + 0))
        pane("створка", iw / 2, ih / 2, iw, ih, parent=hg, local=True)
    else:                       # PIVOT: ось вращения горизонтальная, через середину
        ax = (cx, cy, z + h / 2)
        rot = (25, 0, 0) if axis == 'Y' else (0, 25, 0)
        hg = empty(f"{nm} — ось поворота (Open 25°)", cwin, loc=ax, size=0.2, rot=rot)
        pane("створка", 0, 0, iw, ih, parent=hg, local=True)
    # подоконник снаружи
    sd = (w + 0.2, 0.25, 0.05) if axis == 'Y' else (0.25, w + 0.2, 0.05)
    sc_ = (cx, cy + sgn * (WALL_W / 2 + 0.08), z - 0.025) if axis == 'Y' else (cx + sgn * (WALL_W / 2 + 0.08), cy, z - 0.025)
    box(f"{nm} — отлив", cwin, sd, sc_, M_FRAME)


window("CASE", 6.0, FY, where="фасад")
window("SLIDE", 8.4, FY, w=1.6, where="фасад")
window("FIXED", 0.0, 3.5, axis='X', w=1.2, where="левая стена")
window("PIVOT", HX, 3.5, axis='X', where="правая стена")
window("FIXED", 3.0, HY, w=2.0, where="задняя стена")
window("CASE", 7.0, HY, where="задняя стена")

# --- лестница (Straight Stair): ступень + «Массив» (Количество 3, шаг = ступень по Y и Z)
STEP_H = FOUND / 3
step = box("Лестница прямая (Straight Stair) — ступень", cstair, (1.8, 0.35, STEP_H), (DX, FY - WALL_W / 2 - 0.35 * 3 + 0.175, STEP_H / 2), M_STEP)
a = step.modifiers.new("Массив — ступени (Count 3)", 'ARRAY')
a.count = 3; a.use_relative_offset = True; a.relative_offset_displace = (0, 1, 1)

# --- крыша (двускатная) и фронтоны
RO, RH = 0.5, 2.4


def roof_mesh(name):
    def b(bm):
        x0, x1 = -RO, HX + RO
        y0, y1, ym = -RO - WALL_W / 2, HY + RO + WALL_W / 2, HY / 2
        t = 0.18
        v = lambda x, y, z: bm.verts.new((x, y, z))
        for (ya, yb) in ((y0, ym), (y1, ym)):
            a0, a1 = v(x0, ya, 0), v(x1, ya, 0)
            b0, b1 = v(x0, yb, RH), v(x1, yb, RH)
            a0t, a1t = v(x0, ya, t), v(x1, ya, t)
            b0t, b1t = v(x0, yb, RH + t), v(x1, yb, RH + t)
            for f in ((a0, a1, b1, b0), (a0t, b0t, b1t, a1t), (a0, a0t, a1t, a1), (a0, b0, b0t, a0t), (a1, a1t, b1t, b1)):
                bm.faces.new(f)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_from(name, b)


obj("Крыша двускатная", roof_mesh("Крыша"), croof, loc=(0, 0, FOUND + WALL_H - 0.35), mat=M_ROOF)


def gable_mesh(name):
    def b(bm):
        z0 = 0
        ys = [-WALL_W / 2 + 0.05, HY + WALL_W / 2 - 0.05]
        hh = RH * (HY / 2 - ys[0]) / (HY / 2 + RO + WALL_W / 2)
        for x in (0.0, HX):
            vs = [bm.verts.new((x - WALL_W / 2, ys[0], z0)), bm.verts.new((x - WALL_W / 2, ys[1], z0)), bm.verts.new((x - WALL_W / 2, HY / 2, z0 + hh))]
            ws = [bm.verts.new((x + WALL_W / 2, ys[0], z0)), bm.verts.new((x + WALL_W / 2, ys[1], z0)), bm.verts.new((x + WALL_W / 2, HY / 2, z0 + hh))]
            bm.faces.new(vs); bm.faces.new(ws[::-1])
            for i in range(3):
                bm.faces.new((vs[i], ws[i], ws[(i + 1) % 3], vs[(i + 1) % 3]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_from(name, b)


obj("Фронтоны (треугольные стены)", gable_mesh("Фронтоны"), croof, loc=(0, 0, FOUND + WALL_H), mat=M_WALL)
box("Труба", croof, (0.6, 0.6, 2.0), (7.5, HY * 0.7, FOUND + WALL_H + 1.6), M_BASE)


# --- растения: геометрические ноды «Дерево (аналог Foliage)»: Высота, Плотность, Обрезка, Вариация, Листва, Ствол
def tree_group():
    ng = bpy.data.node_groups.new("Дерево (аналог Foliage)", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    I.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    def sock(name, typ, val, lo=None, hi=None):
        s = I.new_socket(name, in_out='INPUT', socket_type=typ); s.default_value = val
        if lo is not None: s.min_value = lo
        if hi is not None: s.max_value = hi
    sock("Высота (Height)", 'NodeSocketFloat', 6.0, 0.5, 50)
    sock("Плотность кроны (Density)", 'NodeSocketFloat', 0.8, 0.0, 1.0)
    sock("Обрезка снизу (Pruning)", 'NodeSocketFloat', 0.2, 0.0, 1.0)
    sock("Вариация (Seed)", 'NodeSocketInt', 0)
    sock("Листва (Leaves)", 'NodeSocketBool', True)
    sock("Ствол (Trunk)", 'NodeSocketBool', True)
    N = ng.nodes; L = ng.links.new
    gi = N.new("NodeGroupInput"); gi.location = (-1400, 0)
    go = N.new("NodeGroupOutput"); go.location = (900, 0)
    H, DEN, PR, SEED, LEAVES, TRUNK = (gi.outputs[i] for i in range(1, 7))

    def math_(op, a, b=None, loc=(0, 0)):
        n = N.new("ShaderNodeMath"); n.operation = op; n.location = loc
        (L(a, n.inputs[0]) if not isinstance(a, (int, float)) else n.inputs[0].__setattr__("default_value", a))
        if b is not None:
            (L(b, n.inputs[1]) if not isinstance(b, (int, float)) else n.inputs[1].__setattr__("default_value", b))
        return n.outputs[0]

    def xyz(x=0.0, y=0.0, z=0.0, loc=(0, 0)):
        n = N.new("ShaderNodeCombineXYZ"); n.location = loc
        for i, v in enumerate((x, y, z)):
            (L(v, n.inputs[i]) if not isinstance(v, (int, float)) else n.inputs[i].__setattr__("default_value", v))
        return n.outputs[0]

    crown_r = math_('MULTIPLY', H, 0.3, (-1200, -200))
    # ствол: цилиндр высотой 0,7·H, радиус 0,035·H, низ на земле
    trunk_h = math_('MULTIPLY', H, 0.7, (-1200, 200))
    cyl = N.new("GeometryNodeMeshCylinder"); cyl.location = (-1000, 300)
    cyl.inputs["Vertices"].default_value = 10
    L(math_('MULTIPLY', H, 0.035, (-1200, 350)), cyl.inputs["Radius"]); L(trunk_h, cyl.inputs["Depth"])
    tr = N.new("GeometryNodeTransform"); tr.location = (-800, 300)
    L(cyl.outputs["Mesh"], tr.inputs["Geometry"]); L(xyz(z=math_('MULTIPLY', trunk_h, 0.5, (-1000, 150)), loc=(-900, 150)), tr.inputs["Translation"])
    smt = N.new("GeometryNodeSetMaterial"); smt.location = (-600, 300); smt.inputs["Material"].default_value = M_BARK
    L(tr.outputs[0], smt.inputs["Geometry"])
    sw_t = N.new("GeometryNodeSwitch"); sw_t.input_type = 'GEOMETRY'; sw_t.location = (-400, 300)
    L(TRUNK, sw_t.inputs["Switch"]); L(smt.outputs[0], sw_t.inputs["True"])
    # крона: икосфера (Сфера кроны) → точки на гранях (Плотность, Вариация) → обрезка снизу → шарики листвы
    ico = N.new("GeometryNodeMeshIcoSphere"); ico.location = (-1000, -200); ico.inputs["Subdivisions"].default_value = 2
    L(crown_r, ico.inputs["Radius"])
    tc = N.new("GeometryNodeTransform"); tc.location = (-800, -200)
    L(ico.outputs["Mesh"], tc.inputs["Geometry"])
    L(xyz(z=math_('SUBTRACT', H, crown_r, (-1000, -400)), loc=(-900, -400)), tc.inputs["Translation"])
    tc.inputs["Scale"].default_value = (1.0, 1.0, 1.15)
    dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.location = (-600, -200)
    L(tc.outputs[0], dist.inputs["Mesh"])
    L(math_('DIVIDE', math_('MULTIPLY', DEN, 6.0, (-800, -500)), math_('MULTIPLY', crown_r, crown_r, (-800, -600)), (-700, -550)), dist.inputs["Density"])
    L(SEED, dist.inputs["Seed"])
    pos = N.new("GeometryNodeInputPosition"); pos.location = (-600, -500)
    sep = N.new("ShaderNodeSeparateXYZ"); sep.location = (-450, -500); L(pos.outputs[0], sep.inputs[0])
    # порог: низ кроны + Pruning · диаметр кроны
    low = math_('SUBTRACT', H, math_('MULTIPLY', crown_r, 2.3, (-650, -700)), (-500, -700))
    thr = math_('ADD', low, math_('MULTIPLY', PR, math_('MULTIPLY', crown_r, 2.3, (-650, -800)), (-500, -800)), (-350, -700))
    cmp_ = math_('LESS_THAN', sep.outputs["Z"], thr, (-250, -550))
    dele = N.new("GeometryNodeDeleteGeometry"); dele.location = (-200, -200); dele.domain = 'POINT'
    L(dist.outputs["Points"], dele.inputs["Geometry"]); L(cmp_, dele.inputs["Selection"])
    leaf = N.new("GeometryNodeMeshIcoSphere"); leaf.location = (-400, -400); leaf.inputs["Subdivisions"].default_value = 2
    L(math_('MULTIPLY', crown_r, 0.42, (-600, -900)), leaf.inputs["Radius"])
    sml = N.new("GeometryNodeSetMaterial"); sml.location = (-250, -400); sml.inputs["Material"].default_value = M_LEAF
    ssm = N.new("GeometryNodeSetShadeSmooth"); ssm.location = (-300, -300)
    L(leaf.outputs["Mesh"], ssm.inputs["Geometry"]); L(ssm.outputs[0], sml.inputs["Geometry"])
    rnd = N.new("FunctionNodeRandomValue"); rnd.data_type = 'FLOAT'; rnd.location = (-200, -650)
    rnd.inputs["Min"].default_value = 0.6; rnd.inputs["Max"].default_value = 1.1
    L(SEED, rnd.inputs["Seed"])
    iop = N.new("GeometryNodeInstanceOnPoints"); iop.location = (0, -200)
    L(dele.outputs[0], iop.inputs["Points"]); L(sml.outputs[0], iop.inputs["Instance"])
    L(rnd.outputs["Value"], iop.inputs["Scale"])
    sw_l = N.new("GeometryNodeSwitch"); sw_l.input_type = 'GEOMETRY'; sw_l.location = (250, -200)
    L(LEAVES, sw_l.inputs["Switch"]); L(iop.outputs[0], sw_l.inputs["True"])
    j = N.new("GeometryNodeJoinGeometry"); j.location = (500, 0)
    L(sw_l.outputs[0], j.inputs[0]); L(sw_t.outputs[0], j.inputs[0])
    L(j.outputs[0], go.inputs[0])
    return ng


TREE_NG = tree_group()


def tree(name, col, loc, height=6.0, density=0.8, pruning=0.2, seed=0, leaves=True, trunk=True):
    o = obj(name, bpy.data.meshes.new(name), col, loc=loc)
    m = o.modifiers.new("Дерево (Foliage)", 'NODES'); m.node_group = TREE_NG
    ids = [i.identifier for i in TREE_NG.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'INPUT']
    for k, v in zip(ids[1:], (height, density, pruning, seed, leaves, trunk)):
        m[k] = v
    return o


for i, (x, y, h, s) in enumerate([(-4.5, 2.0, 7.5, 3), (-5.0, 9.5, 6.0, 11), (15.0, 9.0, 8.0, 5), (14.5, 1.5, 5.5, 8),
                                  (4.0, 13.0, 6.5, 21), (9.5, 13.5, 5.0, 17), (-2.5, -6.0, 4.0, 2)]):
    tree(f"Дерево {i + 1} (Высота {h:g}, Вариация {s})".replace(".", ","), ctree, (x, y, 0), height=h, seed=s)
for i, (dens, pr, sd, lv, trk, nm) in enumerate([(0.2, 0.0, 1, True, True, "Плотность 0,2"), (0.8, 0.0, 1, True, True, "Плотность 0,8"),
                                                 (0.8, 0.6, 1, True, True, "Обрезка 0,6"), (0.8, 0.2, 7, True, True, "Вариация 7"),
                                                 (0.8, 0.2, 1, False, True, "Листва выкл.")]):
    tree(f"Образец растения — {nm}", st, (30.0 + 6.0 * i, 0, 0), height=6.0, density=dens, pruning=pr, seed=sd, leaves=lv, trunk=trk)


# --- изгородь: геометрические ноды «Изгородь (аналог Railing)» на кривой-пути (Pick Railing Path)
def railing_group():
    ng = bpy.data.node_groups.new("Изгородь (аналог Railing)", "GeometryNodeTree")
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    I.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    def sock(name, typ, val, lo=None):
        s = I.new_socket(name, in_out='INPUT', socket_type=typ); s.default_value = val
        if lo is not None: s.min_value = lo
    sock("Высота (Top Rail Height)", 'NodeSocketFloat', 1.2, 0.2)
    sock("Шаг столбов (Post Spacing)", 'NodeSocketFloat', 2.5, 0.3)
    sock("Шаг штакетника (Picket Spacing)", 'NodeSocketFloat', 0.22, 0.05)
    sock("Сплошной щит (Solid Fill)", 'NodeSocketBool', False)
    sock("Материал", 'NodeSocketMaterial', M_FENCE)
    N = ng.nodes; L = ng.links.new
    gi = N.new("NodeGroupInput"); gi.location = (-1400, 0)
    go = N.new("NodeGroupOutput"); go.location = (1100, 0)
    CURVE, H, PS, KS, SOLID, MAT = (gi.outputs[i] for i in range(6))

    def math_(op, a, b, loc=(0, 0)):
        n = N.new("ShaderNodeMath"); n.operation = op; n.location = loc
        for i, x in enumerate((a, b)):
            (L(x, n.inputs[i]) if not isinstance(x, (int, float)) else n.inputs[i].__setattr__("default_value", x))
        return n.outputs[0]

    def xyz(x=0.0, y=0.0, z=0.0, loc=(0, 0)):
        n = N.new("ShaderNodeCombineXYZ"); n.location = loc
        for i, v in enumerate((x, y, z)):
            (L(v, n.inputs[i]) if not isinstance(v, (int, float)) else n.inputs[i].__setattr__("default_value", v))
        return n.outputs[0]

    def posts(spacing, size_x, size_y, height_factor, loc):
        c2p = N.new("GeometryNodeCurveToPoints"); c2p.mode = 'LENGTH'; c2p.location = loc
        L(CURVE, c2p.inputs["Curve"]); L(spacing, c2p.inputs["Length"])
        hh = math_('MULTIPLY', H, height_factor, (loc[0], loc[1] - 200))
        cube = N.new("GeometryNodeMeshCube"); cube.location = (loc[0] + 200, loc[1] - 200)
        L(xyz(size_x, size_y, hh, (loc[0] + 100, loc[1] - 300)), cube.inputs["Size"])
        tr = N.new("GeometryNodeTransform"); tr.location = (loc[0] + 400, loc[1] - 200)
        L(cube.outputs["Mesh"], tr.inputs["Geometry"]); L(xyz(z=math_('MULTIPLY', hh, 0.5, (loc[0] + 200, loc[1] - 400)), loc=(loc[0] + 300, loc[1] - 400)), tr.inputs["Translation"])
        iop = N.new("GeometryNodeInstanceOnPoints"); iop.location = (loc[0] + 600, loc[1])
        L(c2p.outputs["Points"], iop.inputs["Points"]); L(tr.outputs[0], iop.inputs["Instance"])   # квадратные — поворот не нужен
        return iop.outputs[0]

    post_geo = posts(PS, 0.14, 0.14, 1.1, (-1100, 400))
    picket_geo = posts(KS, 0.06, 0.06, 0.95, (-1100, -100))
    # сплошной щит: рёбра пути → «Экструдировать меш» вверх
    c2m0 = N.new("GeometryNodeCurveToMesh"); c2m0.location = (-900, -600); L(CURVE, c2m0.inputs["Curve"])
    ext = N.new("GeometryNodeExtrudeMesh"); ext.mode = 'EDGES'; ext.location = (-700, -600)
    L(c2m0.outputs[0], ext.inputs["Mesh"]); ext.inputs["Offset"].default_value = (0, 0, 1)
    L(math_('MULTIPLY', H, 0.85, (-900, -800)), ext.inputs["Offset Scale"])
    trp = N.new("GeometryNodeTransform"); trp.location = (-500, -600); L(ext.outputs["Mesh"], trp.inputs["Geometry"])
    L(xyz(z=math_('MULTIPLY', H, 0.08, (-700, -850)), loc=(-600, -850)), trp.inputs["Translation"])
    sol = N.new("GeometryNodeSwitch"); sol.input_type = 'GEOMETRY'; sol.location = (-200, -300)
    L(SOLID, sol.inputs["Switch"]); L(picket_geo, sol.inputs["False"]); L(trp.outputs[0], sol.inputs["True"])
    # брусья: путь → «Кривую в меш» с профилем-прямоугольником, на двух высотах
    rails = []
    for k, f in enumerate((0.85, 0.3)):
        q = N.new("GeometryNodeCurvePrimitiveQuadrilateral"); q.location = (-900, -1000 - 250 * k)
        q.inputs["Width"].default_value = 0.08; q.inputs["Height"].default_value = 0.12
        c2m = N.new("GeometryNodeCurveToMesh"); c2m.location = (-700, -1000 - 250 * k)
        L(CURVE, c2m.inputs["Curve"]); L(q.outputs[0], c2m.inputs["Profile Curve"]); c2m.inputs["Fill Caps"].default_value = True
        tr = N.new("GeometryNodeTransform"); tr.location = (-500, -1000 - 250 * k)
        L(c2m.outputs[0], tr.inputs["Geometry"]); L(xyz(z=math_('MULTIPLY', H, f, (-700, -1150 - 250 * k)), loc=(-600, -1150 - 250 * k)), tr.inputs["Translation"])
        rails.append(tr.outputs[0])
    j = N.new("GeometryNodeJoinGeometry"); j.location = (300, 0)
    for g in [post_geo, sol.outputs[0]] + rails:
        L(g, j.inputs[0])
    smat = N.new("GeometryNodeSetMaterial"); smat.location = (600, 0)
    L(j.outputs[0], smat.inputs["Geometry"]); L(MAT, smat.inputs["Material"])
    L(smat.outputs[0], go.inputs[0])
    return ng


def poly_curve(name, col, pts, cyclic=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    s = cu.splines.new('POLY'); s.points.add(len(pts) - 1)
    for p, c in zip(s.points, pts):
        p.co = (c[0], c[1], 0.0, 1.0)
    s.use_cyclic_u = cyclic
    return obj(name, cu, col)


RAIL_NG = railing_group()
fpath = poly_curve("Путь изгороди (Pick Railing Path)", cfence, [(2.0, -5.0), (-7.5, -5.0), (-7.5, 12.5), (17.5, 12.5), (17.5, -5.0), (4.0, -5.0)])
m = fpath.modifiers.new("Изгородь (Railing)", 'NODES'); m.node_group = RAIL_NG
# дорожка к калитке и крыльцу
box("Дорожка к дому", env, (1.6, 6.2, 0.03), (DX, -3.4, 0.015), M_PATH)

# этапы: стены → стены с проёмами (без окон и дверей) → + двери и окна → + крыша (готово)
wall_object("Этап 2 — стены с проёмами", st, OUTLINE, ccut)
add_light(env, "Солнце — дом", 'SUN', (50, 0, 35), 4.0, angle_deg=2)
add_light(env, "Заполняющий — дом", 'SUN', (70, 0, 200), 0.6, angle_deg=30)
add_camera(s5, env, "Камера — дом", (-12.0, -24.0, 11.0), (5.0, 3.5, 2.0), lens=35)

# ---------------------------------------------------------------- одинаковые имена коллекций → без «.001»
for sc in bpy.data.scenes:
    for c in sc.collection.children:
        if re.search(r"\.\d{3}$", c.name):
            c.name = re.sub(r"\.\d{3}$", "", c.name) + " — сцена " + sc.name[0]

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp_ = area.spaces[0]
            sp_.clip_end = 2000
            r3d = sp_.region_3d
            if r3d:
                r3d.view_location = Vector((0, 0, 4))
                r3d.view_rotation = Euler((R(60), 0, R(30))).to_quaternion()
                r3d.view_distance = 30
                r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
