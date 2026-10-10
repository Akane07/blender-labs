import bpy, bmesh, math, sys, importlib.util
from mathutils import Vector, Euler

SCRATCH = "/tmp/claude-0/-home-claude/6a29748f-df2d-5d65-9890-10e6f728fabc/scratchpad"
OUT = SCRATCH + "/Лаба3_Blender.blend"

spec = importlib.util.spec_from_file_location("rc", SCRATCH + "/rc.py")
rc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)

bpy.ops.wm.read_factory_settings()
scene = bpy.context.scene
bpy.data.objects.remove(bpy.data.objects["Cube"])
base_col = bpy.data.collections["Collection"]
base_col.name = "Камера и свет"


def new_collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


def move_to(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def srgb_hex(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def cut_vertical_edges(obj, cuts):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    vert = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-4
            and abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-4 and abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-4]
    bmesh.ops.subdivide_edges(bm, edges=vert, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(obj.data); bm.free()


# ---------- Задание 1: Bend ----------
col_bend = new_collection("Задание 1 — Изгиб (Bend)")
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=10, depth=30, location=(-150, 0, 0))
cyl = bpy.context.active_object
cyl.name = "Цилиндр_Bend"; cyl.data.name = "Цилиндр_Bend"
cut_vertical_edges(cyl, 9)
move_to(cyl, col_bend)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-150, 0, -15))
gizmo = bpy.context.active_object
gizmo.name = "Пустышка_Gizmo"; gizmo.empty_display_size = 8
move_to(gizmo, col_bend)

md = cyl.modifiers.new("Изгиб (Bend)", 'SIMPLE_DEFORM')
md.deform_method = 'BEND'; md.angle = math.radians(90); md.deform_axis = 'X'
md.limits = (0.0, 0.83); md.origin = gizmo

# ---------- Задание 1: Twist ----------
col_twist = new_collection("Задание 1 — Скручивание (Twist)")
bpy.ops.mesh.primitive_cube_add(size=2, location=(-210, 0, 0))
box = bpy.context.active_object
box.name = "Куб_Twist"; box.data.name = "Куб_Twist"
box.scale = (2.5, 2.5, 15)          # Размеры 5 x 5 x 30
cut_vertical_edges(box, 99)          # 100 сегментов по высоте
move_to(box, col_twist)
md = box.modifiers.new("Скручивание (Twist)", 'SIMPLE_DEFORM')
md.deform_method = 'TWIST'; md.angle = math.radians(120); md.deform_axis = 'Z'


# ---------- Задание 2: апельсин по этапам ----------
def ring(bm, z):
    return [v for v in bm.verts if abs(v.co.z - z) < 1e-3]


def orange_bmesh(stage):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=7, radius=40)
    if stage == 1:
        return bm
    zs = sorted({round(v.co.z, 4) for v in bm.verts}, reverse=True)
    top = max(bm.verts, key=lambda v: v.co.z)
    bot = min(bm.verts, key=lambda v: v.co.z)
    top.co.z -= 8
    if stage == 2:
        return bm
    for i, f in [(1, 0.6), (2, 0.9)]:
        for v in ring(bm, zs[i]):
            v.co.x *= f; v.co.y *= f
    if stage == 3:
        return bm
    bot.co.z += 5
    for i, f in [(-2, 0.7), (-3, 0.92)]:
        for v in ring(bm, zs[i]):
            v.co.x *= f; v.co.y *= f
    if stage == 4:
        return bm
    fan = [f for f in bm.faces if top in f.verts]
    fan.sort(key=lambda f: math.atan2(f.calc_center_median().y, f.calc_center_median().x))
    skip = {2, 6, 9, 12}
    heights = [0.76, 0.9, 0.65, 1.0, 0.8, 0.7, 0.95, 0.6, 0.85, 0.75]
    scales = [0.5, 0.45, 0.55, 0.4, 0.5, 0.6, 0.45, 0.55, 0.5, 0.4]
    k = 0
    for idx, f in enumerate(fan):
        if idx in skip:
            continue
        nf = bmesh.ops.extrude_discrete_faces(bm, faces=[f])["faces"][0]
        c = nf.calc_center_median(); n = nf.normal.copy()
        for v in nf.verts:
            v.co = c + (v.co - c) * scales[k] + n * heights[k]
        k += 1
    return bm


def mesh_object(name, bm, col, location=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(name, me)
    obj.location = location
    col.objects.link(obj)
    return obj


col_orange = new_collection("Задание 2 — Апельсин")
orange = mesh_object("Orange", orange_bmesh(5), col_orange)
orange.data.shade_smooth()
sub = orange.modifiers.new("Сглаживание (NURMS)", 'SUBSURF')
sub.levels = 3; sub.render_levels = 3

verts, faces = rc.round_cube(radius=3, arcdiv=4, lindiv=0, size=(6, 6, 8))
me = bpy.data.meshes.new("Пупок")
me.from_pydata(verts, [], faces)
stem = bpy.data.objects.new("Пупок", me)
stem.location = (0, 0, 35)
col_orange.objects.link(stem)
bm = bmesh.new(); bm.from_mesh(me)
topv = max(bm.verts, key=lambda v: v.co.z - 0.01 * (v.co.x ** 2 + v.co.y ** 2))
topv.co.z -= 1
bm.to_mesh(me); bm.free()
me.shade_smooth()
sub = stem.modifiers.new("Сглаживание (NURMS)", 'SUBSURF')
sub.levels = 3; sub.render_levels = 3

col_stages = new_collection("Этапы апельсина (скрыто)")
stage_names = ["Этап 1 — исходная сфера", "Этап 2 — вдавлена верхняя вершина",
               "Этап 3 — сужены кольца сверху", "Этап 4 — обработан низ",
               "Этап 5 — выдавлены полигоны"]
for i, name in enumerate(stage_names, start=1):
    mesh_object(name, orange_bmesh(i), col_stages, location=(150 + (i - 1) * 100, 0, 0))

# ---------- Материалы ----------
mat = bpy.data.materials.new("Апельсин"); mat.use_nodes = True
nt = mat.node_tree; pr = nt.nodes["Principled BSDF"]; out = nt.nodes["Material Output"]
pr.location = (0, 0); out.location = (320, 0)
pr.inputs["Base Color"].default_value = srgb_hex("FF7A00")
pr.inputs["Roughness"].default_value = 0.55
pr.inputs["Specular IOR Level"].default_value = 0.35
noise = nt.nodes.new("ShaderNodeTexNoise"); noise.location = (-640, -260)
noise.inputs["Scale"].default_value = 80; noise.inputs["Detail"].default_value = 2
bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-320, -300)
bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 1.0
nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], pr.inputs["Normal"])
orange.data.materials.append(mat)

sm = bpy.data.materials.new("Пупок"); sm.use_nodes = True
nt = sm.node_tree; pr = nt.nodes["Principled BSDF"]; out = nt.nodes["Material Output"]
pr.location = (0, 0); out.location = (320, 0)
grad = nt.nodes.new("ShaderNodeTexGradient"); grad.location = (-640, 120)
grad.gradient_type = 'SPHERICAL'
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-400, 120)
ramp.color_ramp.interpolation = 'CONSTANT'
e0, e1 = ramp.color_ramp.elements
e0.position = 0.0; e0.color = srgb_hex("A78C5C")
e1.position = 0.5; e1.color = srgb_hex("2D2912")
nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], pr.inputs["Base Color"])
stem.data.materials.append(sm)

# ---------- Камера и свет ----------
cam = bpy.data.objects["Camera"]
cam.location = (0, -240, 75); cam.rotation_euler = (math.radians(74), 0, 0)
cam.data.clip_end = 1000
light = bpy.data.objects["Light"]
light.data.type = 'SUN'; light.data.energy = 4

# ---------- Видимость и вид ----------
lc = bpy.context.view_layer.layer_collection.children[col_stages.name]
lc.hide_viewport = True
col_stages.hide_render = True

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces[0]
            sp.clip_end = 2000
            r3d = sp.region_3d
            if r3d:
                r3d.view_location = Vector((-80, 0, 0))
                r3d.view_rotation = Euler((math.radians(70), 0, math.radians(-12))).to_quaternion()
                r3d.view_distance = 420
                r3d.view_perspective = 'PERSP'

for o in bpy.context.view_layer.objects:
    o.select_set(False)
orange.select_set(True)
bpy.context.view_layer.objects.active = orange

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
