"""Лаба 6: космический пейзаж. Запуск: .venv/bin/python scripts/lab6/build_lab6.py
Перед этим: scripts/lab6/make_textures6.py (текстуры в output/lab6)."""
import bpy, math, os, sys
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lab4_common import srgb_hex, new_collection, add_camera

OUT_DIR = os.path.join(ROOT, "output", "lab6")
OUT = os.path.join(OUT_DIR, "Лаба6_Blender.blend")
SKY = os.path.join(OUT_DIR, "Звёздное_небо_6000x3000.png")
SKY_SQ = os.path.join(OUT_DIR, "Звёздное_небо_2500x2500.png")
PLANET = os.path.join(OUT_DIR, "Планета_2048x1024.png")

SUN_POS = Vector((-235.0, 280.0, 90.0))
PLANET_R = 60.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.name = "Космический пейзаж"

c_planet = new_collection(sc, "Планета")
c_sun = new_collection(sc, "Светило")
c_cam = new_collection(sc, "Камера")
stages = new_collection(sc, "Этапы (скрыто)")


def load(path):
    img = bpy.data.images.load(path)
    img.pack()
    return img


sky_img = load(SKY)
sky_sq = load(SKY_SQ)       # квадратная текстура из задания 1 (хранится в файле, не используется)
sky_sq.use_fake_user = True
planet_img = load(PLANET)

# ---------------- Мир: «Текстура окр. среды» → «Фон» (аналог Environment Map + Spherical Environment)
w = bpy.data.worlds.new("Мир — звёздное небо")
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.location = (-400, 300)
env.image = sky_img
env.projection = 'EQUIRECTANGULAR'
env.label = "Звёздное небо"
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
w.color = (0.0, 0.0, 0.0)
sc.world = w

# ---------------- Светило: точечный источник с радиусом + видимая излучающая сфера в той же точке
ld = bpy.data.lights.new("Светило — точечный источник", 'POINT')
ld.energy = 7.0e6
ld.shadow_soft_size = 8.0          # «Радиус»: мягкие тени, аналог mr Area Omni
ld.color = srgb_hex("FFF1DC")[:3]
light = bpy.data.objects.new("Светило — точечный источник", ld)
light.location = SUN_POS
c_sun.objects.link(light)

bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=9.0, location=SUN_POS)
sun = bpy.context.object
sun.name = "Светило — видимая сфера"
for c in list(sun.users_collection):
    c.objects.unlink(sun)
c_sun.objects.link(sun)
bpy.ops.object.shade_smooth()
sun.visible_shadow = False         # сфера не закрывает свет источника, который стоит внутри неё
m_sun = bpy.data.materials.new("Светило — излучение")
m_sun.use_nodes = True
n = m_sun.node_tree.nodes
n.remove(n["Principled BSDF"])
em = n.new("ShaderNodeEmission"); em.location = (0, 300)
em.inputs["Color"].default_value = srgb_hex("FFE9C8")
em.inputs["Strength"].default_value = 40.0
m_sun.node_tree.links.new(em.outputs[0], n["Material Output"].inputs["Surface"])
sun.data.materials.append(m_sun)

# ---------------- Планета: UV-сфера радиусом 60, 60 сегментов, гладкое затенение
bpy.ops.mesh.primitive_uv_sphere_add(segments=60, ring_count=30, radius=PLANET_R, location=(0, 0, 0))
planet = bpy.context.object
planet.name = "Планета"
planet.rotation_euler = (math.radians(12), math.radians(-8), math.radians(30))
for c in list(planet.users_collection):
    c.objects.unlink(planet)
c_planet.objects.link(planet)
bpy.ops.object.shade_smooth()

m = bpy.data.materials.new("Планета")
m.use_nodes = True
nt = m.node_tree
N = nt.nodes; Lk = nt.links.new
p = N["Principled BSDF"]; p.location = (300, 300)
p.inputs["Roughness"].default_value = 0.75
p.inputs["Specular IOR Level"].default_value = 0.3
N["Material Output"].location = (600, 300)

tex = N.new("ShaderNodeTexImage"); tex.location = (-500, 500); tex.image = planet_img; tex.label = "Текстура планеты"
Lk(tex.outputs["Color"], p.inputs["Base Color"])
bump = N.new("ShaderNodeBump"); bump.location = (-150, 150)
bump.inputs["Strength"].default_value = 0.5          # Bump = 50
bump.inputs["Distance"].default_value = 1.5          # под радиус 60 (по умолчанию 0,001 — рельефа не видно)
Lk(tex.outputs["Color"], bump.inputs["Height"])
Lk(bump.outputs["Normal"], p.inputs["Normal"])

# Self-Illumination = Mask( Falloff Fresnel чёрный→красный, маска Falloff Shadow/Light, Invert Mask)
lw = N.new("ShaderNodeLayerWeight"); lw.location = (-900, -150); lw.label = "Затухание (Френель)"
lw.inputs["Blend"].default_value = 0.35
rim = N.new("ShaderNodeValToRGB"); rim.location = (-700, -150); rim.label = "Чёрный → красный"
rim.color_ramp.elements[0].color = (0, 0, 0, 1)
rim.color_ramp.elements[0].position = 0.25
rim.color_ramp.elements[1].color = srgb_hex("FF1A0A")
Lk(lw.outputs["Fresnel"], rim.inputs["Fac"])

tc = N.new("ShaderNodeTexCoord"); tc.location = (-1300, -500); tc.object = sun; tc.label = "Координаты относительно светила"
neg = N.new("ShaderNodeVectorMath"); neg.location = (-1100, -500); neg.operation = 'SCALE'; neg.label = "Направление на светило"
neg.inputs["Scale"].default_value = -1.0
nrm = N.new("ShaderNodeVectorMath"); nrm.location = (-920, -500); nrm.operation = 'NORMALIZE'
geo = N.new("ShaderNodeNewGeometry"); geo.location = (-920, -700)
dot = N.new("ShaderNodeVectorMath"); dot.location = (-740, -550); dot.operation = 'DOT_PRODUCT'; dot.label = "Свет / тень"
Lk(tc.outputs["Object"], neg.inputs[0]); Lk(neg.outputs["Vector"], nrm.inputs[0])
Lk(nrm.outputs["Vector"], dot.inputs[0]); Lk(geo.outputs["Normal"], dot.inputs[1])
mask = N.new("ShaderNodeMapRange"); mask.location = (-560, -550); mask.label = "Маска: тень чёрная, свет белый"
mask.inputs["From Min"].default_value = -0.15; mask.inputs["From Max"].default_value = 0.35
Lk(dot.outputs["Value"], mask.inputs["Value"])
inv = N.new("ShaderNodeInvert"); inv.location = (-380, -550); inv.label = "Invert Mask"
Lk(mask.outputs["Result"], inv.inputs["Color"])
mix = N.new("ShaderNodeMix"); mix.location = (-150, -300); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
mix.label = "Mask"
mix.inputs["Factor"].default_value = 1.0
Lk(rim.outputs["Color"], mix.inputs["A"]); Lk(inv.outputs["Color"], mix.inputs["B"])
Lk(mix.outputs["Result"], p.inputs["Emission Color"])
p.inputs["Emission Strength"].default_value = 1.2
planet.data.materials.append(m)

# ---------------- Этап: сфера с малым числом сегментов («ломаный контур», рис. 1 методички)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=PLANET_R, location=(0, 0, 0))
low = bpy.context.object
low.name = "Этап — сфера 12 сегментов (ломаный контур)"
for c in list(low.users_collection):
    c.objects.unlink(low)
stages.objects.link(low)
m_grey = bpy.data.materials.new("Серый (этап)")
m_grey.use_nodes = True
m_grey.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = srgb_hex("B0B0B0")
low.data.materials.append(m_grey)

# ---------------- Камера
cam = add_camera(sc, c_cam, "Камера", (-150, -300, 25), (-95, 0, 12), lens=40)

# ---------------- Композитинг: Lens Effects → узлы «Блики»
ng = bpy.data.node_groups.new("Композитинг — эффекты линзы", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
G = ng.nodes
rl = G.new("CompositorNodeRLayers"); rl.location = (-900, 0)
out = G.new("NodeGroupOutput"); out.location = (700, 0)


def glare(name, typ, x, **vals):
    g = G.new("CompositorNodeGlare"); g.name = g.label = name; g.location = (x, 0)
    g.inputs["Type"].default_value = typ
    for k, v in vals.items():
        g.inputs[k].default_value = v
    return g


g1 = glare("Glow (Size 180) — Туманное свечение", "Fog Glow", -650, Threshold=1.0, Size=0.9, Strength=0.6)
g2 = glare("Auto Secondary — Призраки", "Ghosts", -350, Threshold=1.5, Iterations=4, **{"Color Modulation": 0.6, "Strength": 0.25})
g3 = glare("Glow (Size 50) — Свечение", "Bloom", -50, Threshold=1.0, Size=0.5, Strength=0.25)
g4 = glare("Star (Qty 16) — Полосы", "Streaks", 250, Threshold=2.0, Streaks=16, Fade=0.93, Strength=0.15, **{"Streaks Angle": math.radians(10)})
prev = rl.outputs["Image"]
for g in (g1, g2, g3, g4):
    ng.links.new(prev, g.inputs["Image"]); prev = g.outputs["Image"]
ng.links.new(prev, out.inputs[0])
sc.compositing_node_group = ng

# ---------------- Рендер
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 960
sc.view_settings.view_transform = 'AgX'
stages.hide_render = True
sc.view_layers[0].layer_collection.children[stages.name].hide_viewport = True

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces[0]
            sp.clip_end = 10000
            sp.shading.type = 'MATERIAL'                 # «Предпросмотр материала»
            sp.shading.use_scene_world = True            # «Окружение сцены» — звёздный фон в окне (аналог Viewport Background)
            sp.shading.use_scene_lights = True
            sp.shading.use_compositor = 'CAMERA'         # «Композитор» — аналог флажка Interactive
            r3d = sp.region_3d
            if r3d:
                r3d.view_location = Vector((-100, 60, 20))
                r3d.view_rotation = cam.rotation_euler.to_quaternion()
                r3d.view_distance = 520
                r3d.view_perspective = 'PERSP'

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT)
