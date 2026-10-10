import bpy, math, sys, os
from mathutils import Vector

S = "/tmp/claude-0/-home-claude/6a29748f-df2d-5d65-9890-10e6f728fabc/scratchpad/"
FIG = S + "figs4/"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=S + "Лаба4_Blender.blend")
SC = {s.name[0]: s for s in bpy.data.scenes}


def mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb + (1,)
    p.inputs["Roughness"].default_value = rough
    return m


GREY = mat("fig_grey", (0.55, 0.55, 0.57))
LINE = mat("fig_line", (0.85, 0.85, 0.85), 0.5)
WIRE = mat("fig_wire", (0.01, 0.01, 0.012), 0.8)

studio_world = bpy.data.worlds.new("fig_world"); studio_world.use_nodes = True
studio_world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)

rigs = {}
for key, sc in SC.items():
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
    sc.render.resolution_percentage = 100
    for c in sc.collection.children:
        c.hide_render = False
        sc.view_layers[0].layer_collection.children[c.name].hide_viewport = False
    cd = bpy.data.cameras.new("FigCam" + key); cd.clip_end = 5000
    cam = bpy.data.objects.new("FigCam" + key, cd); sc.collection.objects.link(cam)
    hl = bpy.data.lights.new("Head" + key, 'SUN'); hl.energy = 3.2; hl.angle = 0.3
    head = bpy.data.objects.new("Head" + key, hl); sc.collection.objects.link(head)
    rigs[key] = (cam, head, sc.camera, sc.world)


def render(name, key, visible, eye=None, target=None, ortho=None, lens=50, res=(1200, 900), studio=True):
    if only and name not in only:
        return
    sc = SC[key]; cam, head, scene_cam, scene_world = rigs[key]
    for o in sc.objects:
        if o.type in ('MESH', 'CURVE'):
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
    bpy.ops.render.render(write_still=True, scene=sc.name)
    print("RENDERED", name)


def set_mat(obj, m):
    obj.data.materials.clear(); obj.data.materials.append(m)


def wire_copy(obj, sc, thickness):
    c = obj.copy(); c.name = obj.name + "_wire"
    sc.collection.objects.link(c)
    w = c.modifiers.new("wire", 'WIREFRAME'); w.thickness = thickness; w.use_even_offset = True
    c.material_slots[0].link = 'OBJECT'; c.material_slots[0].material = WIRE
    return c


def O(name_start, key):
    return [o for o in SC[key].objects if o.name.startswith(name_start)][0]


# ---------------- Scene 1: gear ----------------
for i in range(1, 5):
    st = O(f"Этап {i} ", "1")
    set_mat(st, LINE)
    if i < 4:
        st.data.bevel_depth = 0.6
    x = st.location.x
    render(f"g_stage{i}", "1", {st.name}, eye=(x, 0, 300), target=(x, 0.001, 0), ortho=112, res=(1000, 1000))
gear = O("Шестерёнка", "1")
gold = gear.data.materials[0]
set_mat(gear, GREY)
render("g_extruded", "1", {gear.name}, eye=(0, -150, 120), target=(0, 0, 0), lens=50)
set_mat(gear, gold)
render("g_final", "1", {gear.name}, studio=False, res=(1200, 900))

# ---------------- Scene 2: toothbrush ----------------
line = O("Этап 1 ", "2"); set_mat(line, LINE); line.data.bevel_depth = 0.8
render("b_line", "2", {line.name}, eye=(68, 60 - 300, 5), target=(68, 60, 5), ortho=160, res=(1400, 600))
rect = O("Этап 2 ", "2"); set_mat(rect, GREY)
render("b_rect", "2", {rect.name}, eye=(10, 120 - 150, 90), target=(75, 120, 3), lens=45)
for i, (nm, eye_off, tgt_off, lens) in enumerate([
        ("Этап 3 ", (60, -110, 80), (120, 0, 6), 45),
        ("Этап 4 ", (125, -45, 55), (152, 0, 10), 55),
        ("Этап 5 ", (40, -70, 45), (80, 0, 2), 45)]):
    st = O(nm, "2"); set_mat(st, GREY)
    sw = wire_copy(st, SC["2"], 0.12)
    y = st.location.y
    render(f"b_stage{i + 3}", "2", {st.name, sw.name}, eye=(eye_off[0], y + eye_off[1], eye_off[2]),
           target=(tgt_off[0], y + tgt_off[1], tgt_off[2]), lens=lens)
handle = O("Ручка", "2"); plastic = handle.data.materials[0]
set_mat(handle, GREY)
render("b_smooth", "2", {handle.name}, eye=(40, -150, 90), target=(85, 0, 4), lens=45)
row = O("Этап 6 ", "2"); set_mat(row, GREY)
rw = wire_copy(row, SC["2"], 0.05)
render("b_row", "2", {row.name, rw.name}, eye=(11.2, 360 - 36, 18), target=(11.2, 360, 0), lens=40, res=(1200, 700))
tufts = O("Основания щетины", "2"); bristle = tufts.data.materials[0]
tufts.modifiers[0].show_render = False
set_mat(tufts, mat("fig_pink", (0.9, 0.35, 0.55), 0.5))
render("b_tufts", "2", {handle.name, tufts.name}, eye=(125, -45, 55), target=(152, 0, 10), lens=55)
tufts.modifiers[0].show_render = True
set_mat(tufts, bristle); set_mat(handle, plastic)
render("b_final", "2", {handle.name, tufts.name}, studio=False, res=(1200, 800))

# ---------------- Scene 3: pot ----------------
prof = O("Этап 1 ", "3"); set_mat(prof, LINE); prof.data.bevel_depth = 0.35
render("p_profile", "3", {prof.name}, eye=(80 + 12, -200, 19), target=(80 + 12, 0, 19), ortho=48, res=(900, 1000))
pot = O("Горшок", "3"); soil = O("Земля", "3")
soil.modifiers[0].show_render = False
render("p_lathe", "3", {pot.name, soil.name}, eye=(0, -110, 70), target=(0, 0, 18), lens=50, studio=True)
soil.modifiers[0].show_render = True
render("p_final", "3", {pot.name, soil.name}, studio=False, res=(1200, 900))
print("ALL DONE")
