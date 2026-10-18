"""Лаба 5: две шестерёнки, связанные драйверами. Запуск: .venv/bin/python scripts/lab5/build_lab5.py"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lab4_common import srgb_hex, new_collection, principled, add_camera, add_light

OUT_DIR = os.path.join(ROOT, "output", "lab5")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Лаба5_Blender.blend")

SEG = 24          # сторон у трубы = число зубьев
R1, R2, H = 60.0, 70.0, 9.0
DISK_R2, DISK_H = 9.1, 3.0
TOOTH_LEN, TOOTH_S = 12.0, 0.15
DIST = 154.0      # расстояние между центрами: 70 (основание) + 81,4 (вершина зуба) + зазор; проверено расчётом
HALF_STEP = 7.5   # половина шага зуба 360/24/2


def tube_bmesh(r_in, r_out, h, seg=SEG):
    """Аналог примитива Tube 3ds Max (Height Segments = 1), центр по высоте в нуле."""
    bm = bmesh.new()
    rings = []
    for r, z in ((r_out, -h / 2), (r_out, h / 2), (r_in, h / 2), (r_in, -h / 2)):
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                      for i in range(seg)])
    outer = []
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            if k == 0:
                outer.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, outer


def mesh_obj(name, bm, col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def ring_with_teeth(name, col, extrude=TOOTH_LEN, scale=TOOTH_S):
    """Кольцо → выделить кольцо наружных граней → «Экструдировать отдельные грани» → S с центром
    «Индивидуальные ориджины» (то, что пользователь делает руками в режиме редактирования)."""
    bm, outer = tube_bmesh(R1, R2, H)
    res = bmesh.ops.extrude_discrete_faces(bm, faces=outer)
    for f in res["faces"]:
        n = f.normal.copy()
        c = f.calc_center_median()
        for v in f.verts:
            v.co += n * extrude
            v.co = (c + n * extrude) + (v.co - (c + n * extrude)) * scale
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, col)


def wood_material():
    m = bpy.data.materials.new("Дерево")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1100, 300)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-900, 300)
    mp.inputs["Scale"].default_value = (0.012, 0.05, 0.05)
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.location = (-700, 300)
    wv.wave_type = 'BANDS'; wv.bands_direction = 'X'
    wv.inputs["Scale"].default_value = 2.0
    wv.inputs["Distortion"].default_value = 3.0
    wv.inputs["Detail"].default_value = 3.0
    wv.inputs["Detail Scale"].default_value = 1.0
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.location = (-450, 300)
    cr.color_ramp.elements[0].color = srgb_hex("5A3518")
    cr.color_ramp.elements[1].color = srgb_hex("C08A55")
    cr.color_ramp.elements[0].position = 0.15
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Color"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], p.inputs["Base Color"])
    m.diffuse_color = srgb_hex("9A6A3C")
    return m


def add_driver(dst, src, expr):
    fc = dst.driver_add("rotation_euler", 2)
    d = fc.driver
    d.type = 'SCRIPTED'
    v = d.variables.new(); v.name = "var"; v.type = 'SINGLE_PROP'
    v.targets[0].id_type = 'OBJECT'
    v.targets[0].id = src
    v.targets[0].data_path = "rotation_euler[2]"
    d.expression = expr
    assert d.is_simple_expression, expr
    return fc


def set_mat(ob, m):
    ob.data.materials.clear(); ob.data.materials.append(m)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.name = "Шестерёнки"

g1 = new_collection(sc, "Шестерёнка 1 (ведущая)")
g2 = new_collection(sc, "Шестерёнка 2")
env = new_collection(sc, "Камера и свет")
stages = new_collection(sc, "Этапы шестерёнки (скрыто)")

bronze = principled("Бронза", "C9803E", rough=0.32, metallic=1.0)
silver = principled("Серебро", "E4E6EA", rough=0.22, metallic=1.0)
wood = wood_material()
grey = principled("Серый (этапы)", "9A9A9E", rough=0.6)

# ---- шестерёнки
ring1 = ring_with_teeth("Кольцо 1", g1)
bm, _ = tube_bmesh(DISK_R2, R1, DISK_H)
disk1 = mesh_obj("Диск 1", bm, g1)
ring2 = ring_with_teeth("Кольцо 2", g2)
bm, _ = tube_bmesh(DISK_R2, R1, DISK_H)
disk2 = mesh_obj("Диск 2", bm, g2)
ring2.location = disk2.location = (DIST, 0, 0)
set_mat(ring1, bronze); set_mat(ring2, silver)
set_mat(disk1, wood); set_mat(disk2, wood)

# ---- этапы (скрыто): кольцо, кольцо+диск, после экструдирования, с зубьями
bm, _ = tube_bmesh(R1, R2, H)
s1 = mesh_obj("Этап 1 — кольцо (Tube 60/70/9)", bm, stages)
bm, _ = tube_bmesh(R1, R2, H)
s2a = mesh_obj("Этап 2 — кольцо", bm, stages)
bm, _ = tube_bmesh(DISK_R2, R1, DISK_H)
s2b = mesh_obj("Этап 2 — диск (R2 = 9,1, H = 3)", bm, stages)
s3 = ring_with_teeth("Этап 3 — грани экструдированы на 12", stages, scale=1.0)
s4 = ring_with_teeth("Этап 4 — грани сжаты (S 0,15) — зубья", stages)
for i, objs in enumerate([[s1], [s2a, s2b], [s3], [s4]]):
    for o in objs:
        o.location = (220 * i, 300, 0)
        set_mat(o, grey)

# ---- драйверы (аналог Wire Parameters)
add_driver(disk1, ring1, "var")
add_driver(ring2, ring1, "-var + radians(7.5)")
add_driver(disk2, ring2, "var")

# ---- анимация ведущего кольца: ключи только у «Кольцо 1»
sc.frame_start, sc.frame_end = 0, 100
for f, deg in ((0, 0), (24, 120), (41, 60), (71, 240), (100, 180)):
    ring1.rotation_euler[2] = math.radians(deg)
    ring1.keyframe_insert("rotation_euler", index=2, frame=f)
sc.frame_set(0)

# ---- окружение: градиентный «мир» даёт металлу отражения
w = bpy.data.worlds.new("Мир — студия")
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ")
cr = nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].position = 0.42; cr.color_ramp.elements[0].color = srgb_hex("0E1014")
cr.color_ramp.elements[1].position = 0.75; cr.color_ramp.elements[1].color = srgb_hex("7C838E")
nt.links.new(tc.outputs["Generated"], sx.inputs[0])
nt.links.new(sx.outputs["Z"], cr.inputs["Fac"])
nt.links.new(cr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
w.color = srgb_hex("1A1D22")[:3]
sc.world = w

add_light(env, "Солнце — основной", 'SUN', (45, 0, 35), 3.0, angle_deg=6)
add_light(env, "Солнце — заполняющий", 'SUN', (60, 0, -120), 1.0, angle_deg=20)
cam = add_camera(sc, env, "Камера", (DIST / 2, -270, 300), (DIST / 2, 6, 0), lens=38)

# ---- рендер и видео
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = 'VIDEO'
im.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'AVI'
sc.render.ffmpeg.codec = 'MPEG4'
sc.render.ffmpeg.constant_rate_factor = 'NONE'   # для MPEG-4 качество задаётся битрейтом
sc.render.ffmpeg.video_bitrate = 6000
sc.render.ffmpeg.maxrate = 9000
sc.render.filepath = "//Лаба5_анимация_"

stages.hide_render = True
sc.view_layers[0].layer_collection.children[stages.name].hide_viewport = True

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces[0]
            sp.clip_end = 5000
            sp.overlay.show_wireframes = True       # аналог Edged Faces
            r3d = sp.region_3d
            if r3d:
                r3d.view_location = Vector((DIST / 2, 0, 0))
                r3d.view_rotation = Euler((math.radians(50), 0, 0)).to_quaternion()
                r3d.view_distance = 420
                r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
