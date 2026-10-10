import bpy, sys, math
from mathutils import Vector, Euler
SCRATCH = "/tmp/claude-0/-home-claude/6a29748f-df2d-5d65-9890-10e6f728fabc/scratchpad"
sys.path.insert(0, SCRATCH)
OUT = SCRATCH + "/Лаба4_Blender.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
from lab4_gear import build_gear
from lab4_brush import build_brush
from lab4_pot import build_pot

s1 = bpy.context.scene
s1.name = "1 — Шестерёнка"
s2 = bpy.data.scenes.new("2 — Зубная щётка")
s3 = bpy.data.scenes.new("3 — Горшок с травой (самостоятельное)")

gear, gst = build_gear(s1)
handle, tufts, bst, helper, platform = build_brush(s2)
pot, soil, pst = build_pot(s3)
print("tufts placed:", platform["tufts"])

for sc, st in ((s1, gst), (s2, bst), (s3, pst)):
    sc.render.engine = 'BLENDER_EEVEE'
    st.hide_render = True
    sc.view_layers[0].layer_collection.children[st.name].hide_viewport = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
# profile rectangle stays visible but not rendered
helper.hide_render = True

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces[0]
            sp.clip_end = 5000
            r3d = sp.region_3d
            if r3d:
                r3d.view_location = Vector((0, 0, 0))
                r3d.view_rotation = Euler((math.radians(55), 0, math.radians(-15))).to_quaternion()
                r3d.view_distance = 260
                r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
