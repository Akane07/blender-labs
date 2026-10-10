import bpy, bmesh, math
from mathutils import Matrix
from lab4_common import *

PROFILE = [(0, 0, 0), (16, 0, 0), (22, 0, 32), (25, 0, 33), (25, 0, 37), (21.5, 0, 37), (19.3, 0, 4), (0, 0, 4)]


def build_pot(scene):
    main = new_collection(scene, "Горшок с травой")
    stages = new_collection(scene, "Этапы горшка (скрыто)")

    st = curve_object("Этап 1 — профиль горшка (кривая)", [PROFILE], stages, cyclic=False)
    st.location = (80, 0, 0)

    pot = curve_object("Горшок", [PROFILE], main, cyclic=False)
    scr = pot.modifiers.new("Вращение профиля (Lathe)", 'SCREW')
    scr.angle = math.radians(360); scr.steps = 48; scr.render_steps = 48
    scr.axis = 'Z'; scr.use_merge_vertices = True; scr.merge_threshold = 0.01
    scr.use_normal_calculate = True; scr.use_smooth_shade = True
    pot.data.materials.append(principled("Керамика", "B5552E", rough=0.65))

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=21.0, radius2=21.0, depth=2.0,
                          matrix=Matrix.Translation((0, 0, 29)))
    caps = [f for f in bm.faces if all(abs(v.co.z - 30) < 1e-4 for v in f.verts)]
    bmesh.ops.split_edges(bm, edges=list({e for f in caps for e in f.edges}))
    top = list({v for f in caps for v in f.verts})
    bm.verts.index_update()
    top_idx = [v.index for v in top]
    me = bpy.data.meshes.new("Земля"); bm.to_mesh(me); bm.free()
    soil = bpy.data.objects.new("Земля", me); main.objects.link(soil)
    vg = soil.vertex_groups.new(name="Поверхность земли"); vg.add(top_idx, 1.0, 'REPLACE')
    me.materials.append(principled("Земля", "3B2616", rough=1.0))
    me.materials.append(principled("Трава", "4C9A2A", rough=0.5))

    mod = soil.modifiers.new("Трава (Hair and Fur)", 'PARTICLE_SYSTEM')
    psys = mod.particle_system; psys.name = "Трава"
    ps = psys.settings; ps.name = "Трава"
    ps.type = 'HAIR'; ps.count = 1400; ps.hair_length = 18.0
    ps.factor_random = 0.35          # разброс направления травинок
    ps.emit_from = 'FACE'; ps.use_emit_random = True; ps.distribution = 'RAND'
    ps.child_type = 'INTERPOLATED'; ps.child_percent = 10; ps.rendered_child_count = 14
    ps.clump_factor = 0.45
    ps.roughness_1 = 0.3; ps.roughness_endpoint = 0.7; ps.roughness_2 = 0.25
    ps.length_random = 0.6
    ps.root_radius = 1.0; ps.tip_radius = 0.0; ps.radius_scale = 0.35
    ps.render_step = 4; ps.display_step = 3
    ps.material_slot = "Трава"
    psys.vertex_group_density = "Поверхность земли"

    scene.render.hair_type = 'STRIP'; scene.render.hair_subdiv = 1
    world(scene, "Мир — светлый фон", "CFCFCF", 0.7)
    add_light(main, "Солнце — основной", 'SUN', (45, 0, 35), 3.5, angle_deg=6)
    add_light(main, "Солнце — заполняющий", 'SUN', (60, 0, 200), 1.0, angle_deg=20)
    add_camera(scene, main, "Камера — горшок", (0, -140, 72), (0, 0, 21), lens=50)
    return pot, soil, stages
