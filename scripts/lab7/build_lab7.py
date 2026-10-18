"""Лаба 7: трансформации, выравнивание, клонирование, массивы, расстановка по кривой, зеркало + ИДЗ.
Запуск: .venv/bin/python scripts/lab7/build_lab7.py"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Euler, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lab4_common import srgb_hex, new_collection, principled, add_camera, add_light, world

OUT_DIR = os.path.join(ROOT, "output", "lab7")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Лаба7_Blender.blend")
R = math.radians

bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- геометрия без операторов (работает в любой сцене)
def mesh_from(name, build):
    bm = bmesh.new()
    build(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return me


def obj(name, data, col, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), mat=None, smooth=False):
    ob = bpy.data.objects.new(name, data)
    col.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = Euler([R(a) for a in rot])
    ob.scale = scale
    if mat is not None and data is not None and hasattr(data, "materials"):
        for m in (mat if isinstance(mat, (list, tuple)) else [mat]):
            data.materials.append(m)
    if smooth and data is not None:
        for p in data.polygons:
            p.use_smooth = True
    return ob


def cylinder_mesh(name, sides, r, depth, z_shift=0.0, r2=None):
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r if r2 is None else r2, depth=depth)
        bmesh.ops.translate(bm, vec=(0, 0, z_shift), verts=bm.verts)
    return mesh_from(name, b)


def cube_mesh(name):
    return mesh_from(name, lambda bm: bmesh.ops.create_cube(bm, size=1.0))


def sphere_mesh(name, r, seg=32, rings=16):
    return mesh_from(name, lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r))


def hemisphere_mesh(name, r, hemi, seg=32, rings=16):
    """Аналог Sphere с параметром Hemisphere: отрезана нижняя часть, высота остатка = 2r·(1 − hemi), низ закрыт."""
    def b(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
        cut = r - 2 * r * (1 - hemi)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True)
        boundary = [e for e in bm.edges if e.is_boundary]
        bmesh.ops.contextual_create(bm, geom=boundary)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_from(name, b)


def box(name, col, dims, center, mat=None, rot=(0, 0, 0)):
    """Параллелепипед как в 3ds Max: размеры задаются полем «Размеры» (масштаб куба со стороной 1)."""
    return obj(name, cube_mesh(name), col, loc=center, rot=rot, scale=dims, mat=mat)


def tree_mesh(name, height=0.8, crown=0.25):
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=crown * 0.16, radius2=crown * 0.12, depth=height * 0.45)
        bmesh.ops.translate(bm, vec=(0, 0, height * 0.225), verts=bm.verts)
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=crown)
        crown_verts = set(res["verts"])
        bmesh.ops.scale(bm, vec=(1, 1, 1.25), verts=res["verts"])
        bmesh.ops.translate(bm, vec=(0, 0, height - crown * 1.1), verts=res["verts"])
        for f in bm.faces:
            if all(v in crown_verts for v in f.verts):
                f.material_index = 1
                f.smooth = True
    return mesh_from(name, b)


def stage_collection(sc, name):
    col = new_collection(sc, name)
    col.hide_render = True
    sc.view_layers[0].layer_collection.children[col.name].hide_viewport = True
    return col


def setup_scene(sc, sky="BFD3E6", strength=0.9):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.unit_settings.system = 'METRIC'
    world(sc, "Мир — " + sc.name, sky, strength)


def spacing_group():
    """Аналог Spacing Tool: «Кривую в точки» (Количество) → «Экземпляр на точки» (объект-образец)."""
    ng = bpy.data.node_groups.new("Расстановка по кривой (Spacing Tool)", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    s = ng.interface.new_socket("Количество (Count)", in_out='INPUT', socket_type='NodeSocketInt')
    s.default_value = 12; s.min_value = 2
    ng.interface.new_socket("Образец", in_out='INPUT', socket_type='NodeSocketObject')
    N = ng.nodes; L = ng.links.new
    gi = N.new("NodeGroupInput"); gi.location = (-500, 0)
    go = N.new("NodeGroupOutput"); go.location = (400, 0)
    c2p = N.new("GeometryNodeCurveToPoints"); c2p.mode = 'COUNT'; c2p.location = (-250, 100)
    oi = N.new("GeometryNodeObjectInfo"); oi.location = (-250, -150)
    iop = N.new("GeometryNodeInstanceOnPoints"); iop.location = (100, 0)
    L(gi.outputs[0], c2p.inputs["Curve"]); L(gi.outputs[1], c2p.inputs["Count"])
    L(gi.outputs[2], oi.inputs["Object"])
    L(c2p.outputs["Points"], iop.inputs["Points"]); L(oi.outputs["Geometry"], iop.inputs["Instance"])
    L(iop.outputs["Instances"], go.inputs[0])
    return ng


def spacing_modifier(curve_ob, ng, sample, count):
    m = curve_ob.modifiers.new("Расстановка по кривой (Spacing Tool)", 'NODES')
    m.node_group = ng
    ids = [i.identifier for i in ng.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'INPUT']
    m[ids[1]] = count
    m[ids[2]] = sample
    return m


def poly_curve(name, col, pts):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    s = cu.splines.new('POLY'); s.points.add(len(pts) - 1)
    for p, c in zip(s.points, pts):
        p.co = (c[0], c[1], c[2] if len(c) > 2 else 0.0, 1.0)
    return obj(name, cu, col)


# ---------------------------------------------------------------- материалы
M_GREY = principled("Серый", "A8A8AC", rough=0.6)
M_STONE = principled("Камень (бежевый)", "D9C9A0", rough=0.7)
M_ROOF = principled("Кровля", "6F7F8F", rough=0.45, metallic=0.6)
M_DOME = principled("Купол (медь)", "6FA58C", rough=0.35, metallic=0.7)
M_WOOD = principled("Кора", "5A3B22", rough=0.8)
M_LEAF = principled("Листва", "2F6B2A", rough=0.7)
M_GRASS = principled("Трава", "5E8A3A", rough=0.95)
M_ROAD = principled("Дорожка", "B9AE98", rough=0.9)
M_WATER = principled("Вода", "3F7FB0", rough=0.05, ior_level=0.8)
M_RED = principled("Красный", "C0392B", rough=0.5)
M_BLUE = principled("Синий", "2E6FB7", rough=0.5)
M_YELLOW = principled("Жёлтый", "E0B020", rough=0.5)
M_GREEN = principled("Зелёный", "3D9B4F", rough=0.5)
M_ORANGE = principled("Оранжевый", "E07B2A", rough=0.5)


def ground(sc, col, size, name, mat=M_GRASS):
    me = mesh_from(name, lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2))
    return obj(name, me, col, mat=mat)


# ================================================================ 1 — опорная точка
s1 = bpy.context.scene
s1.name = "1 — Опорная точка (задание 1)"
setup_scene(s1)
c = new_collection(s1, "Цилиндр")
st = stage_collection(s1, "Этапы (скрыто)")
env = new_collection(s1, "Камера и свет")
# В Blender ориджин цилиндра по умолчанию в центре; в 3ds Max — в центре нижнего основания.
obj("Этап — ориджин в центре (как создан)", cylinder_mesh("Цилиндр 6 граней (этап)", 6, 0.5, 1.0), st, loc=(0, 0, 0.5), mat=M_GREY)
obj("Цилиндр 6 граней", cylinder_mesh("Цилиндр 6 граней", 6, 0.5, 1.0, z_shift=-0.5), c, loc=(0, 0, 1.0), mat=M_GREY)
add_light(env, "Солнце", 'SUN', (45, 0, 30), 3.0, angle_deg=5)
add_camera(s1, env, "Камера", (2.6, -3.4, 2.4), (0, 0, 0.5), lens=50)

# ================================================================ 2 — перемещение, вращение, масштаб
s2 = bpy.data.scenes.new("2 — Перемещение, вращение, масштаб (задание 2, ЛР_5 и ЛР_7_1)")
setup_scene(s2)
c = new_collection(s2, "Сцена ЛР_5 (примитивы)")
c_sc = new_collection(s2, "Масштабирование (ЛР_7_1)")
st = stage_collection(s2, "Этапы (скрыто)")
env = new_collection(s2, "Камера и свет")
ground(s2, env, 12, "Пол — сцена 2", M_GREY)
box("Параллелепипед", c, (0.8, 0.8, 0.8), (-2.2, 1.2, 0.4), M_BLUE)
obj("Цилиндр — сцена 2", cylinder_mesh("Цилиндр — сцена 2", 32, 0.4, 1.0), c, loc=(-0.8, 1.6, 0.5), mat=M_GREEN, smooth=True)
def _torus(bm, R1=0.45, R2=0.15, n=32, m=16):
    verts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ring = []
        for j in range(m):
            b = 2 * math.pi * j / m
            ring.append(bm.verts.new(((R1 + R2 * math.cos(b)) * math.cos(a), (R1 + R2 * math.cos(b)) * math.sin(a), R2 * math.sin(b))))
        verts.append(ring)
    for i in range(n):
        for j in range(m):
            bm.faces.new((verts[i][j], verts[(i + 1) % n][j], verts[(i + 1) % n][(j + 1) % m], verts[i][(j + 1) % m]))
torus = obj("Тор", mesh_from("Тор", _torus), c, loc=(0.8, 1.8, 0.15), mat=M_YELLOW, smooth=True)
pyr = cylinder_mesh("Пирамида", 4, 0.6, 1.0, r2=0.0)
obj("Этап — пирамида до поворота", pyr.copy(), st, loc=(2.2, 1.2, 0.5), rot=(0, 0, 45), mat=M_RED)
obj("Пирамида (повёрнута на 90°)", pyr, c, loc=(2.2, 1.2, 0.42), rot=(90, 0, 45), mat=M_RED)
# шары: исходные — в этапах; диск и торпеда — масштабированием
for i, x in enumerate((-2.6, 0.4)):
    obj(f"Этап — шар {i + 1} до масштабирования", sphere_mesh(f"Шар этап {i + 1}", 0.5), st, loc=(x, -1.2, 0.5), mat=M_ORANGE, smooth=True)
obj("Шар 1 → диск (S Z 0.2)", sphere_mesh("Шар 1", 0.5), c_sc, loc=(-2.6, -1.4, 0.1), scale=(1.4, 1.4, 0.2), mat=M_ORANGE, smooth=True)
obj("Шар 2 → торпеда (S X 3, S Y Z 0.5)", sphere_mesh("Шар 2", 0.5), c_sc, loc=(0.4, -1.4, 0.25), scale=(3.0, 0.5, 0.5), mat=M_ORANGE, smooth=True)
sq = obj("Шар 3 — растяжение с сохранением объёма (аналог Squash)", sphere_mesh("Шар 3", 0.5, 32, 24), c_sc, loc=(2.9, -1.4, 0.5), mat=M_ORANGE, smooth=True)
md = sq.modifiers.new("Простая деформация — Растяжение (Squash)", 'SIMPLE_DEFORM')
md.deform_method = 'STRETCH'; md.factor = 0.8; md.deform_axis = 'Z'
sq.location.z = 0.5 * 1.8
add_light(env, "Солнце — сцена 2", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s2, env, "Камера — сцена 2", (0.2, -7.6, 4.6), (0.1, 0.1, 0.3), lens=35)

# ================================================================ 3 — вестибюль
s3 = bpy.data.scenes.new("3 — Вестибюль (задания 3, 12, 13)")
setup_scene(s3)
cv = new_collection(s3, "Вестибюль (задание 3)")
cp = new_collection(s3, "Портик — зеркальная копия (задание 13)")
ct = new_collection(s3, "Деревья (задание 12)")
st = stage_collection(s3, "Этапы выравнивания (скрыто)")
env = new_collection(s3, "Камера, свет, земля")
ground(s3, env, 8, "Земля — вестибюль", M_GRASS)


def vestibule(col, dx=0.0, stage=3, suffix=""):
    """stage 1: цилиндр выровнен по центрам (внутри основания); 2: на верхней грани; 3: + купол."""
    b = box("Основание Box01" + suffix, col, (1.0, 1.0, 0.18), (dx, 0, 0.09), M_STONE)
    cz = 0.09 if stage == 1 else 0.18 + 0.06
    cy = obj("Цилиндр Cylinder01" + suffix, cylinder_mesh("Cylinder01" + suffix, 32, 0.3, 0.12), col, loc=(dx, 0, cz), mat=M_STONE, smooth=True)
    d = None
    if stage >= 3:
        d = obj("Купол Sphere01" + suffix, hemisphere_mesh("Sphere01" + suffix, 0.5, 0.8), col, loc=(dx, 0, 0.0), mat=M_DOME, smooth=True)
    return b, cy, d


vestibule(cv)
PORTICO = [  # имя, размеры X Y Z (Width, Length, Height), центр
    ("Стойка Box02", (0.015, 0.05, 0.16), (0.60, 0.25, 0.08)),
    ("Стойка Box03", (0.015, 0.05, 0.16), (0.70, 0.25, 0.08)),
    ("Столб Box04", (0.05, 0.05, 0.18), (0.825, 0.25, 0.09)),
    ("Перекладина Box05", (0.3, 0.05, 0.02), (0.65, 0.25, 0.17)),
]
for n, dims, ctr in PORTICO:
    box(n, cv, dims, ctr, M_STONE)
    # Отразить по Y относительно 3D-курсора в начале координат (= «Mirror, смещение −0,5» от центра портика)
    box(n + " (зеркальная копия)", cp, (dims[0], -dims[1], dims[2]), (ctr[0], -ctr[1], ctr[2]), M_STONE)
for i, stg in enumerate((1, 2, 3)):
    vestibule(st, dx=3.0 * (i + 1), stage=stg, suffix=f" — этап {stg}")
for o in st.objects:
    o.name = "Этап " + o.name.split("— этап ")[-1] + " — " + o.name.split(" — этап")[0]

tm = tree_mesh("Дерево")
tm.materials.append(M_WOOD); tm.materials.append(M_LEAF)
tree = obj("Дерево (образец, American Elm)", tm, ct, loc=(-1.3, -1.1, 0))
path = poly_curve("П-образный путь (Line)", ct, [(-1.3, -1.1), (-1.3, 1.3), (1.5, 1.3), (1.5, -1.1)])
spacing_modifier(path, spacing_group(), tree, 12)
tree.hide_render = True        # образец стоит в начале пути; на рендере — только расставленные копии
add_light(env, "Солнце — вестибюль", 'SUN', (50, 0, 35), 3.0, angle_deg=5)
add_light(env, "Солнце — заполняющий", 'SUN', (65, 0, 210), 0.8, angle_deg=20)
add_camera(s3, env, "Камера — вестибюль", (1.9, -4.2, 2.7), (0.1, 0.1, 0.15), lens=40)

# ================================================================ 4 — выравнивание ориентации
s4 = bpy.data.scenes.new("4 — Выравнивание ориентации (задание 4)")
setup_scene(s4)
c = new_collection(s4, "Цилиндры")
st = stage_collection(s4, "Этапы (скрыто)")
env = new_collection(s4, "Камера и свет")
ground(s4, env, 10, "Пол — сцена 4", M_GREY)
ROT_A = (35, 25, 30)
obj("Цилиндр 1 (создан в виде сверху, повёрнут)", cylinder_mesh("Цилиндр 1", 32, 0.25, 1.6), c, loc=(-1.0, 0, 1.2), rot=ROT_A, mat=M_BLUE, smooth=True)
obj("Цилиндр 2 (создан в виде слева, выровнен по цилиндру 1)", cylinder_mesh("Цилиндр 2", 32, 0.25, 1.6), c, loc=(1.0, 0, 1.2), rot=ROT_A, mat=M_ORANGE, smooth=True)
obj("Этап — цилиндр 2 до выравнивания (горизонтальный)", cylinder_mesh("Цилиндр 2 этап", 32, 0.25, 1.6), st, loc=(1.0, 0, 1.2), rot=(0, 90, 0), mat=M_ORANGE, smooth=True)
add_light(env, "Солнце — сцена 4", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s4, env, "Камера — сцена 4", (0, -6.0, 2.6), (0, 0, 1.1), lens=45)

# ================================================================ 5 — копии и экземпляры
s5 = bpy.data.scenes.new("5 — Копии и экземпляры (задания 5, 6)")
setup_scene(s5)
cc = new_collection(s5, "Копии — Shift+D (задание 5)")
ci = new_collection(s5, "Экземпляры — Alt+D (задание 6)")
st = stage_collection(s5, "Этапы (скрыто)")
env = new_collection(s5, "Камера и свет")
ground(s5, env, 14, "Пол — сцена 5", M_GREY)
obj("Этап — исходный цилиндр (6 граней)", cylinder_mesh("Исходный цилиндр", 6, 0.5, 1.0), st, loc=(0, 0, 0.5), mat=M_GREY)
obj("Копия 0 — исходный (стало 3 грани)", cylinder_mesh("Копия 0", 3, 0.5, 1.0), cc, loc=(0, 0, 0.5), mat=M_BLUE)
obj("Копия 1 — высота / 1,75", cylinder_mesh("Копия 1", 6, 0.5, 1.0 / 1.75), cc, loc=(1.6, 0, 0.5 / 1.75), mat=M_BLUE)
obj("Копия 2 — радиус / 1,75", cylinder_mesh("Копия 2", 6, 0.5 / 1.75, 1.0), cc, loc=(3.2, 0, 0.5), mat=M_BLUE)
shared = cylinder_mesh("Общий меш экземпляров", 3, 0.5 / 1.75, 1.0 / 1.75)
for i in range(3):
    obj(f"Экземпляр {i}", shared, ci, loc=(1.6 * i, 2.2, 0.5 / 1.75), mat=M_ORANGE if i == 0 else None)
add_light(env, "Солнце — сцена 5", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s5, env, "Камера — сцена 5", (1.6, -5.2, 3.6), (1.6, 1.0, 0.3), lens=40)

# ================================================================ 6 — клонирование с выравниванием
s6 = bpy.data.scenes.new("6 — Клонирование с выравниванием (задание 7)")
setup_scene(s6)
c = new_collection(s6, "Исходный объект")
cm = new_collection(s6, "Метки (эталонные объекты)")
cl = new_collection(s6, "Клоны, выровненные по меткам")
env = new_collection(s6, "Камера и свет")
ground(s6, env, 10, "Пол — сцена 6", M_GREY)
src = cylinder_mesh("Исходный цилиндр 7", 6, 0.35, 1.0)
obj("Исходный цилиндр", src, c, loc=(-1.6, 0, 0.5), mat=M_BLUE)
MARKS = [((0.4, 0.3, 0.9), (0, 35, 20)), ((2.0, -0.2, 0.9), (-30, 0, 60))]
for i, (loc, rot) in enumerate(MARKS):
    e = bpy.data.objects.new(f"Метка {i + 1}", None)
    e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.5
    cm.objects.link(e); e.location = loc; e.rotation_euler = Euler([R(a) for a in rot])
    obj(f"Клон {i + 1} (по метке {i + 1})", src.copy(), cl, loc=loc, rot=rot, mat=None)
add_light(env, "Солнце — сцена 6", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s6, env, "Камера — сцена 6", (0.2, -5.6, 2.8), (0.2, 0, 0.7), lens=40)

# ================================================================ 7 — массивы
s7 = bpy.data.scenes.new("7 — Массивы (задание 11, ЛР_7_2)")
setup_scene(s7)
c = new_collection(s7, "Массив 10 × 2 (задание 11)")
co = new_collection(s7, "Свои варианты массивов")
env = new_collection(s7, "Камера и свет")
ground(s7, env, 30, "Пол — сцена 7", M_GREY)
cyl = obj("Цилиндр — массив 10 × 2", cylinder_mesh("Цилиндр массива", 6, 0.25, 0.5), c, loc=(0, 0, 2.6), mat=M_BLUE)
step = bpy.data.objects.new("Шаг массива: X 0,6 м, поворот X 10°, масштаб 90 %", None)
step.empty_display_type = 'PLAIN_AXES'; step.empty_display_size = 0.2
c.objects.link(step); step.parent = cyl
step.location = (0.6, 0, 0); step.rotation_euler = (R(10), 0, 0); step.scale = (0.9, 0.9, 0.9)
a = cyl.modifiers.new("Массив — ряд из 10 (Count 10, Incremental)", 'ARRAY')
a.count = 10; a.use_relative_offset = False; a.use_object_offset = True; a.offset_object = step
b = cyl.modifiers.new("Массив — 2 ряда (2D, Z = −2 м)", 'ARRAY')
b.count = 2; b.use_relative_offset = False; b.use_constant_offset = True; b.constant_offset_displace = (0, 0, -2.0)
# свой вариант 1 — круговой массив кубов
kub = obj("Куб — круговой массив 12 шт.", mesh_from("Куб круга", lambda bm: (bmesh.ops.create_cube(bm, size=0.5), bmesh.ops.translate(bm, vec=(2.0, 0, 0.25), verts=bm.verts))), co, loc=(-6, 5, 0), mat=M_YELLOW)
rot = bpy.data.objects.new("Поворот круга: 30° по Z", None)
rot.empty_display_type = 'PLAIN_AXES'; co.objects.link(rot); rot.parent = kub; rot.rotation_euler = (0, 0, R(30))
m = kub.modifiers.new("Массив — по кругу (Count 12, Rotate Z 30°)", 'ARRAY')
m.count = 12; m.use_relative_offset = False; m.use_object_offset = True; m.offset_object = rot
# свой вариант 2 — лестница
stp = box("Ступень — лестница (Массив)", co, (1.6, 0.4, 0.2), (6.0, 1.0, 0.1), M_RED, rot=(0, 0, 90))
m = stp.modifiers.new("Массив — ступени (Count 8)", 'ARRAY')
m.count = 8; m.use_relative_offset = True; m.relative_offset_displace = (0, 1, 1)   # шаг = размер ступени
add_light(env, "Солнце — сцена 7", 'SUN', (50, 0, 30), 3.0, angle_deg=5)
add_camera(s7, env, "Камера — сцена 7", (0.5, -9.5, 6.5), (0.0, 2.0, 1.0), lens=28)

# ================================================================ 8 — ИДЗ «Архитектурный пейзаж»
s8 = bpy.data.scenes.new("8 — ИДЗ «Архитектурный пейзаж»")
setup_scene(s8, sky="9EC6E8", strength=1.0)
cb = new_collection(s8, "Главное здание (выравнивание)")
ccol = new_collection(s8, "Колоннада (массив)")
cw = new_collection(s8, "Крыло левое")
cwm = new_collection(s8, "Крыло правое (зеркальная копия)")
calley = new_collection(s8, "Аллея (расстановка по кривой)")
cpark = new_collection(s8, "Площадь и фонтан")
env = new_collection(s8, "Камера, свет, земля")
ground(s8, env, 60, "Земля — ИДЗ", M_GRASS)
road = box("Дорожка", cpark, (3.0, 17.0, 0.04), (0, -14.5, 0.02), M_ROAD)
square = box("Площадь перед зданием", cpark, (16.0, 5.0, 0.06), (0, -3.5, 0.03), M_ROAD)
# главное здание: каждый блок поставлен на предыдущий («Положительные стороны» по Z + подъём)
box("Подиум", cb, (8.0, 5.0, 0.6), (0, 2.5, 0.3), M_STONE)
box("Корпус", cb, (6.4, 3.6, 3.0), (0, 3.0, 0.6 + 1.5), M_STONE)
box("Карниз", cb, (6.8, 4.0, 0.25), (0, 3.0, 3.6 + 0.125), M_STONE)
obj("Барабан купола", cylinder_mesh("Барабан", 32, 1.4, 1.0), cb, loc=(0, 3.0, 3.85 + 0.5), mat=M_STONE, smooth=True)
obj("Купол", hemisphere_mesh("Купол ИДЗ", 1.6, 0.5, 48, 24), cb, loc=(0, 3.0, 4.85), mat=M_DOME, smooth=True)
obj("Шпиль", cylinder_mesh("Шпиль", 12, 0.12, 1.2, r2=0.0), cb, loc=(0, 3.0, 4.85 + 1.6 + 0.6), mat=M_DOME)
for i in range(4):
    box(f"Ступень {i + 1}", cb, (4.0, 0.35, 0.15), (0, -0.175 - 0.35 * i, 0.6 - 0.075 - 0.15 * i), M_STONE)
col_mesh = cylinder_mesh("Колонна", 24, 0.18, 2.8)
column = obj("Колонна — массив 8 шт. (шаг 0,9 м)", col_mesh, ccol, loc=(-3.15, 0.45, 0.6 + 1.4), mat=M_STONE, smooth=True)
m = column.modifiers.new("Массив — колоннада (Count 8)", 'ARRAY')
m.count = 8; m.use_relative_offset = False; m.use_constant_offset = True; m.constant_offset_displace = (0.9, 0, 0)
box("Архитрав", ccol, (6.8, 0.6, 0.3), (0, 0.45, 3.4 + 0.15), M_STONE)
box("Фронтон-основание", ccol, (6.8, 0.6, 0.12), (0, 0.45, 3.7 + 0.06), M_STONE)
# левое крыло и его зеркальная копия (Объект → Отразить → X относительно 3D-курсора в начале координат)
WING = [
    ("Крыло — корпус", (4.0, 3.0, 2.4), (-6.5, 3.0, 1.2), M_STONE),
    ("Крыло — карниз", (4.3, 3.3, 0.2), (-6.5, 3.0, 2.5), M_STONE),
    ("Крыло — кровля", (4.0, 3.0, 0.5), (-6.5, 3.0, 2.85), M_ROOF),
    ("Переход к крылу", (0.9, 2.4, 2.0), (-4.05, 3.0, 1.0), M_STONE),
]
for n, d, ctr, mt in WING:
    box(n + " (левое)", cw, d, ctr, mt)
    box(n + " (правое, зеркало)", cwm, (-d[0], d[1], d[2]), (-ctr[0], ctr[1], ctr[2]), mt)
# аллея: образец дерева + кривая слева + зеркальная копия кривой справа
tm2 = tree_mesh("Дерево ИДЗ", height=2.6, crown=0.75)
tm2.materials.append(M_WOOD); tm2.materials.append(M_LEAF)
tree2 = obj("Дерево (образец для аллеи)", tm2, calley, loc=(-3.4, -21.0, 0))
tree2.hide_render = True
ng = spacing_group()
alley_l = poly_curve("Аллея — путь слева", calley, [(-3.4, -21.0), (-3.4, -7.5), (-10.0, -6.8)])
spacing_modifier(alley_l, ng, tree2, 9)
alley_r = poly_curve("Аллея — путь справа (зеркальная копия)", calley, [(-3.4, -21.0), (-3.4, -7.5), (-10.0, -6.8)])
alley_r.scale = (-1, 1, 1)
spacing_modifier(alley_r, ng, tree2, 9)
# фонтан
obj("Фонтан — чаша", cylinder_mesh("Чаша", 48, 1.6, 0.5), cpark, loc=(0, -9.0, 0.25), mat=M_STONE, smooth=True)
obj("Фонтан — вода", cylinder_mesh("Вода", 48, 1.45, 0.05), cpark, loc=(0, -9.0, 0.5), mat=M_WATER, smooth=True)
obj("Фонтан — колонна", cylinder_mesh("Колонна фонтана", 24, 0.25, 1.3), cpark, loc=(0, -9.0, 1.15), mat=M_STONE, smooth=True)
obj("Фонтан — верхняя чаша", hemisphere_mesh("Верхняя чаша", 0.7, 0.5, 32, 16), cpark, loc=(0, -9.0, 1.9), rot=(180, 0, 0), mat=M_STONE, smooth=True)
obj("Фонтан — вода в верхней чаше", cylinder_mesh("Вода верх", 32, 0.69, 0.03), cpark, loc=(0, -9.0, 1.915), mat=M_WATER, smooth=True)
# фонари вдоль дорожки — массив
lamp = obj("Фонарь — массив 6 шт.", cylinder_mesh("Фонарь", 12, 0.06, 2.2), cpark, loc=(1.8, -18.0, 1.1), mat=M_ROOF)
m = lamp.modifiers.new("Массив — фонари (Count 6)", 'ARRAY')
m.count = 6; m.use_relative_offset = False; m.use_constant_offset = True; m.constant_offset_displace = (0, 2.0, 0)
lamp_m = obj("Фонарь — зеркальная копия ряда", lamp.data, cpark, loc=(-1.8, -18.0, 1.1), mat=None)
lamp_m.scale = (-1, 1, 1)
m2 = lamp_m.modifiers.new("Массив — фонари (Count 6)", 'ARRAY')
m2.count = 6; m2.use_relative_offset = False; m2.use_constant_offset = True; m2.constant_offset_displace = (0, 2.0, 0)
add_light(env, "Солнце — ИДЗ", 'SUN', (48, 0, 35), 4.0, angle_deg=2)
add_light(env, "Солнце — заполняющий ИДЗ", 'SUN', (70, 0, 200), 0.6, angle_deg=30)
add_camera(s8, env, "Камера — ИДЗ", (13.0, -25.0, 11.0), (0, -2.5, 2.0), lens=35)

# ---------------------------------------------------------------- одинаковые имена коллекций → с номером сцены (без «.001»)
import re
for sc in bpy.data.scenes:
    for c in sc.collection.children:
        if re.search(r"\.\d{3}$", c.name) or c.name in ("Этапы (скрыто)", "Камера и свет"):
            c.name = re.sub(r"\.\d{3}$", "", c.name) + " — сцена " + sc.name[0]

# ---------------------------------------------------------------- окна 3D: удобный вид
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces[0]
            sp.clip_end = 1000
            r3d = sp.region_3d
            if r3d:
                r3d.view_location = Vector((0, 0, 0.5))
                r3d.view_rotation = Euler((R(60), 0, R(30))).to_quaternion()
                r3d.view_distance = 6
                r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
