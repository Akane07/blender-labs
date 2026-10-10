import bpy, math, sys, os
from mathutils import Vector

SCRATCH = "/tmp/claude-0/-home-claude/6a29748f-df2d-5d65-9890-10e6f728fabc/scratchpad"
FIG = SCRATCH + "/figs"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=SCRATCH + "/Лаба3_Blender.blend")
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1200, 900
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# stages collection must be renderable for figures
bpy.data.collections["Этапы апельсина (скрыто)"].hide_render = False
bpy.context.view_layer.layer_collection.children["Этапы апельсина (скрыто)"].hide_viewport = False


def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb + (1,)
    p.inputs["Roughness"].default_value = rough
    return m


GREY = mat("fig_grey", (0.55, 0.55, 0.57))
WIRE = mat("fig_wire", (0.01, 0.01, 0.012), 0.8)

cam_data = bpy.data.cameras.new("FigCam"); cam_data.clip_end = 3000
cam = bpy.data.objects.new("FigCam", cam_data); sc.collection.objects.link(cam)

temp = []


def wire_copy(obj, thickness):
    c = obj.copy(); c.name = obj.name + "_wire"
    sc.collection.objects.link(c)
    w = c.modifiers.new("wire", 'WIREFRAME'); w.thickness = thickness; w.use_even_offset = True
    temp.append(c)
    return c


def set_mat(obj, m):
    obj.data.materials.clear(); obj.data.materials.append(m)


hl_data = bpy.data.lights.new("HeadLight", 'SUN'); hl_data.energy = 3.2; hl_data.angle = 0.3
headlight = bpy.data.objects.new("HeadLight", hl_data); sc.collection.objects.link(headlight)
scene_light = bpy.data.objects["Light"]


def render(name, visible, eye, target, ortho=None, lens=50, res=(1200, 900), studio=True):
    if only and name not in only:
        return
    for o in sc.objects:
        o.hide_render = o.name not in visible and o.type == 'MESH'
    cam.location = Vector(eye)
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    # studio: light from the camera side, slightly from upper-left, like a viewport
    headlight.rotation_euler = cam.rotation_euler.copy()
    headlight.rotation_euler.rotate_axis('X', math.radians(-18))
    headlight.rotation_euler.rotate_axis('Y', math.radians(-18))
    headlight.hide_render = not studio
    scene_light.hide_render = studio
    if ortho:
        cam_data.type = 'ORTHO'; cam_data.ortho_scale = ortho
    else:
        cam_data.type = 'PERSP'; cam_data.lens = lens
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = f"{FIG}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


# ---- Bend ----
cyl = bpy.data.objects["Цилиндр_Bend"]; gizmo = bpy.data.objects["Пустышка_Gizmo"]
cyl_mats = list(cyl.data.materials)
set_mat(cyl, GREY)
cw = wire_copy(cyl, 0.25)
# wire copy shares mesh -> give it wire material via object-level slot
cw.material_slots[0].link = 'OBJECT'; cw.material_slots[0].material = WIRE
render("fig_bend", {cyl.name, cw.name}, eye=(-150 + 110, -35, 20), target=(-150, 8, -3), lens=65)
gizmo.location = (-150, 0, 0)
render("fig_bend_gizmo", {cyl.name, cw.name}, eye=(-150 + 110, -35, 20), target=(-150, 8, -3), lens=65)
gizmo.location = (-150, 0, -15)

# ---- Twist ----
box = bpy.data.objects["Куб_Twist"]
set_mat(box, GREY)
render("fig_twist", {box.name}, eye=(-210 + 38, -50, 20), target=(-210, 0, 0), lens=62, res=(900, 1100))

# ---- Stages (orthographic, like viewport figures) ----
views = {1: 'front', 2: 'above', 3: 'top', 4: 'below', 5: 'top'}
for i in range(1, 6):
    st = [o for o in sc.objects if o.name.startswith(f"Этап {i} ")][0]
    set_mat(st, GREY)
    sw = wire_copy(st, 0.45)
    sw.material_slots[0].link = 'OBJECT'; sw.material_slots[0].material = WIRE
    x = st.location.x
    if views[i] == 'front':
        render(f"fig_stage{i}", {st.name, sw.name}, eye=(x, -300, 0), target=(x, 0, 0), ortho=100, res=(1000, 900))
    elif views[i] == 'above':
        render(f"fig_stage{i}", {st.name, sw.name}, eye=(x, -170, 170), target=(x, 0, 6), lens=72, res=(1000, 900))
    elif views[i] == 'below':
        render(f"fig_stage{i}", {st.name, sw.name}, eye=(x, -170, -150), target=(x, 0, -4), lens=72, res=(1000, 900))
    else:
        render(f"fig_stage{i}", {st.name, sw.name}, eye=(x, 0, 300), target=(x, 0.001, 0), ortho=100, res=(1000, 900))

# ---- Orange: smoothed, no materials ----
orange = bpy.data.objects["Orange"]; stem = bpy.data.objects["Пупок"]
orig_orange_mat = orange.data.materials[0]; orig_stem_mat = stem.data.materials[0]
set_mat(orange, GREY)
render("fig_smooth", {orange.name}, eye=(0, -240, 75), target=(0, 0, 5), lens=50, res=(1200, 900), studio=False)

# ---- Stem placed (close-up, grey) ----
set_mat(stem, GREY)
render("fig_stem", {orange.name, stem.name}, eye=(0, -95, 70), target=(0, 0, 30), lens=50, res=(1200, 900))

# ---- Final with materials (scene camera framing) ----
set_mat(orange, orig_orange_mat); set_mat(stem, orig_stem_mat)
render("fig_final", {orange.name, stem.name}, eye=(0, -240, 75), target=(0, 0, 5.5), lens=50, res=(1200, 900), studio=False)
render("fig_stem_mat", {orange.name, stem.name}, eye=(0, -80, 62), target=(0, 0, 33), lens=50, res=(1200, 900), studio=False)
print("ALL DONE")
