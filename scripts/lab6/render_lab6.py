"""Рисунки для отчёта по лабе 6 (Cycles CPU). Запуск: .venv/bin/python scripts/lab6/render_lab6.py [-- имена]"""
import bpy, sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG = os.path.join(ROOT, "build", "figs6") + "/"
os.makedirs(FIG, exist_ok=True)
only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab6", "Лаба6_Blender.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40; sc.cycles.use_denoising = True
sc.render.resolution_percentage = 100
for c in sc.collection.children:
    c.hide_render = False

O = bpy.data.objects
planet, low, sun = O["Планета"], O["Этап — сфера 12 сегментов (ломаный контур)"], O["Светило — видимая сфера"]
mat = planet.data.materials[0]
N = mat.node_tree.nodes
P = N["Principled BSDF"]
bump_link = [l for l in mat.node_tree.links if l.to_socket == P.inputs["Normal"]][0]
bump_node = bump_link.from_node
emis_strength = P.inputs["Emission Strength"].default_value
ng = sc.compositing_node_group
glares = [n for n in ng.nodes if n.bl_idname == "CompositorNodeGlare"]

grey = bpy.data.materials["Серый (этап)"]


def setup(show, comp=None, bump=True, emis=True, tex=True, grey_planet=False):
    for o in (planet, low, sun):
        o.hide_render = o not in show
    sc.render.use_compositing = comp is not None
    for i, g in enumerate(glares):
        g.mute = comp is None or i not in comp
    bump_node.inputs["Strength"].default_value = 0.5 if bump else 0.0
    P.inputs["Emission Strength"].default_value = emis_strength if emis else 0.0
    planet.material_slots[0].link = 'OBJECT' if grey_planet else 'DATA'
    if grey_planet:
        planet.material_slots[0].material = grey


def render(name, res=(1280, 960), border=None, **kw):
    if only and name not in only:
        return
    setup(**kw)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_border = border is not None
    sc.render.use_crop_to_border = border is not None
    if border:
        sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = border
    sc.render.filepath = FIG + name + ".png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


render("f_env", show=set())
render("f_lowpoly", show={low, sun})
render("f_smooth", show={planet, sun}, grey_planet=True)
render("f_tex", show={planet, sun}, bump=False, emis=False)
crop = (0.55, 0.85, 0.35, 0.80)
render("f_nobump_crop", show={planet, sun}, bump=False, emis=False, border=crop)
render("f_bump_crop", show={planet, sun}, bump=True, emis=False, border=crop)
render("f_emis", show={planet, sun})
render("f_glow", show={planet, sun}, comp={0})
render("f_ghosts", show={planet, sun}, comp={0, 1})
render("f_all", show={planet, sun}, comp={0, 1, 2, 3})
print("ALL DONE")
