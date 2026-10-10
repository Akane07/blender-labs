"""Рисунки для отчёта по лабе 5 (Cycles CPU). Запуск: .venv/bin/python scripts/lab5/render_lab5.py [-- имена]"""
import bpy, math, sys, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG = os.path.join(ROOT, "build", "figs5") + "/"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab5", "Лаба5_Blender.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
sc.render.resolution_percentage = 100
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = 'IMAGE'
im.file_format = 'PNG'
for c in sc.collection.children:
    c.hide_render = False
    sc.view_layers[0].layer_collection.children[c.name].hide_viewport = False


def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb + (1,)
    p.inputs["Roughness"].default_value = rough
    return m


WIRE = mat("fig_wire", (0.01, 0.01, 0.012), 0.8)
studio_world = bpy.data.worlds.new("fig_world"); studio_world.use_nodes = True
studio_world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)

cd = bpy.data.cameras.new("FigCam"); cd.clip_end = 5000
cam = bpy.data.objects.new("FigCam", cd); sc.collection.objects.link(cam)
hl = bpy.data.lights.new("Head", 'SUN'); hl.energy = 3.2; hl.angle = 0.3
head = bpy.data.objects.new("Head", hl); sc.collection.objects.link(head)
scene_cam, scene_world = sc.camera, sc.world


def render(name, visible, eye=None, target=None, ortho=None, lens=50, res=(1200, 900), studio=True, frame=0):
    if only and name not in only:
        return
    sc.frame_set(frame)
    for o in sc.objects:
        if o.type == 'MESH':
            o.hide_render = o.name not in visible
        if o.type == 'LIGHT' and o is not head:
            o.hide_render = studio
    head.hide_render = not studio
    if studio:
        cam.location = Vector(eye)
        cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
        if ortho:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'; cam.data.lens = lens
        head.rotation_euler = cam.rotation_euler.copy()
        head.rotation_euler.rotate_axis('X', math.radians(-18))
        head.rotation_euler.rotate_axis('Y', math.radians(-18))
        sc.camera = cam; sc.world = studio_world
    else:
        sc.camera = scene_cam; sc.world = scene_world
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = FIG + name + ".png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


def wire_copy(obj, thickness):
    c = obj.copy(); c.data = obj.data.copy(); c.name = obj.name + "_wire"
    c.animation_data_clear()
    sc.collection.objects.link(c)
    c.matrix_world = obj.matrix_world.copy()
    w = c.modifiers.new("wire", 'WIREFRAME'); w.thickness = thickness; w.use_even_offset = True
    c.data.materials.clear(); c.data.materials.append(WIRE)
    return c


def O(prefix):
    return [o for o in sc.objects if o.name.startswith(prefix)][0]


s1 = O("Этап 1 "); s2a = O("Этап 2 — кольцо"); s2b = O("Этап 2 — диск")
s3 = O("Этап 3 "); s4 = O("Этап 4 ")
w1 = wire_copy(s1, 0.8); w2 = wire_copy(s2a, 0.8); w2b = wire_copy(s2b, 0.8)
w3 = wire_copy(s3, 0.8); w4 = wire_copy(s4, 0.8)

x = s1.location.x
render("l5_ring", {s1.name, w1.name}, eye=(x, 300 - 170, 140), target=(x, 300, -5), lens=50)
x = s2a.location.x
render("l5_ring_disk", {s2a.name, s2b.name, w2.name, w2b.name}, eye=(x, 300 - 170, 140), target=(x, 300, -5), lens=50)
x = s3.location.x
render("l5_extruded", {s3.name, w3.name}, eye=(x, 300, 300), target=(x, 300.001, 0), ortho=180, res=(1000, 1000))
x = s4.location.x
render("l5_teeth_top", {s4.name, w4.name}, eye=(x, 300, 300), target=(x, 300.001, 0), ortho=180, res=(1000, 1000))
render("l5_teeth_persp", {s4.name, w4.name}, eye=(x, 300 - 190, 150), target=(x, 300, -8), lens=50)

gears = {"Кольцо 1", "Диск 1", "Кольцо 2", "Диск 2"}
render("l5_mesh_top", gears, eye=(77, 0, 400), target=(77, 0.001, 0), ortho=340, res=(1400, 800))
render("l5_mesh_zoom", gears, eye=(77, 0, 400), target=(77, 0.001, 0), ortho=60, res=(1000, 800), frame=33)
for f in (0, 24, 41, 71):
    render(f"l5_frame{f:03d}", gears, studio=False, res=(1280, 720), frame=f)
print("ALL DONE")
