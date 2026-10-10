import bpy, bmesh, math
from mathutils import Vector
from lab4_common import *

PATH = [(0, 0, 0), (70, 0, -3), (100, 0, 0), (120, 0, 9), (135, 0, 9)]
PROFILE_L, PROFILE_W = 12.0, 6.0      # Length = 2 x Width


def copy_obj(ob, name, col, loc):
    c = ob.copy(); c.data = ob.data.copy(); c.name = name; c.data.name = name
    col.objects.link(c); c.location = loc
    return c


def to_mesh_object(curve_ob, name, col, scene):
    scene.view_layers[0].update()
    dg = scene.view_layers[0].depsgraph
    me = bpy.data.meshes.new_from_object(curve_ob.evaluated_get(dg))
    me.name = name
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def nearest_path_index(co):
    return min(range(len(PATH)), key=lambda i: (Vector(PATH[i]) - Vector((co.x, 0, co.z))).length)


def build_handle_mesh(bm):
    """bm: converted curve mesh (rectangular sweep). Returns dict of stage snapshots."""
    snaps = {}
    bm.verts.ensure_lookup_table()
    # caps of the swept curve come triangulated: merge each end into one polygon
    bm.normal_update()
    for i_end, (a, b) in ((0, (1, 0)), (len(PATH) - 1, (len(PATH) - 2, len(PATH) - 1))):
        t = (Vector(PATH[b]) - Vector(PATH[a])).normalized()
        capf = [f for f in bm.faces if all(nearest_path_index(v.co) == i_end for v in f.verts)
                and abs(f.normal.dot(t)) > 0.9]
        if len(capf) > 1:
            bmesh.ops.dissolve_faces(bm, faces=capf)
    # 1) extra loops along each straight piece (so the handle can be decorated and smoothed)
    for i in range(len(PATH) - 1):
        seg = [e for e in bm.edges
               if {nearest_path_index(e.verts[0].co), nearest_path_index(e.verts[1].co)} == {i, i + 1}]
        ln = (Vector(PATH[i + 1]) - Vector(PATH[i])).length
        cuts = max(0, round(ln / 8) - 1)
        if cuts:
            bmesh.ops.subdivide_edges(bm, edges=seg, cuts=cuts, use_grid_fill=True)

    # 2) head: extrude the end cap three times (analog of Bevel on the end polygon)
    end = Vector(PATH[-1])
    cap = min(bm.faces, key=lambda f: (f.calc_center_median() - end).length)
    steps = [(5, 1.35, 1.5), (24, 1.0, 1.0), (5, 0.72, 0.85)]
    face = cap
    for dx, sy, sz in steps:
        ret = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.delete(bm, geom=[face], context='FACES')
        nv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
        nf = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)][0]
        c = Vector([(min(v.co[i] for v in nv) + max(v.co[i] for v in nv)) / 2 for i in range(3)])
        for v in nv:
            d = v.co - c
            v.co = Vector((c.x + dx + d.x, c.y + d.y * sy, c.z + d.z * sz))
        face = nf
    snaps["head"] = bm.copy()

    # 3) bristle platform: flatten the top of the head (View Align) + inset + lower
    bm.normal_update()
    top = [f for f in bm.faces if f.normal.z > 0.6 and f.calc_center_median().x > PATH[-1][0] + 2]
    zmax = max(v.co.z for f in top for v in f.verts)
    for f in top:
        for v in f.verts:
            v.co.z = zmax
    bm.normal_update()
    ret = bmesh.ops.inset_region(bm, faces=top, thickness=1.2, depth=0.0, use_even_offset=True)
    inner = top
    for v in {v for f in inner for v in f.verts}:
        v.co.z -= 0.8
    snaps["platform"] = bm.copy()
    platform = {"xmin": min(v.co.x for f in inner for v in f.verts), "xmax": max(v.co.x for f in inner for v in f.verts),
                "ymin": min(v.co.y for f in inner for v in f.verts), "ymax": max(v.co.y for f in inner for v in f.verts),
                "z": zmax - 0.8}

    # 4) decorative elements: chamfer (3 segments) of the edge loop at the bend + three ribs
    bm.verts.ensure_lookup_table()
    p2 = Vector(PATH[2])
    loop_v = [v for v in bm.verts if (Vector((v.co.x, 0, v.co.z)) - p2).length < 7.5 and abs(v.co.x - p2.x) < 3]
    loop_e = [e for e in bm.edges if e.verts[0] in loop_v and e.verts[1] in loop_v]
    bmesh.ops.bevel(bm, geom=loop_e, offset=1.2, segments=3, affect='EDGES', profile=0.5)

    bm.normal_update()
    bm.faces.ensure_lookup_table()
    side = [f for f in bm.faces if 42 < f.calc_center_median().x < 66 and abs(f.normal.x) < 0.3]
    rings = {}
    for f in side:
        rings.setdefault(round(f.calc_center_median().x), []).append(f)
    keys = sorted(rings)
    for k in keys[::2][:3]:
        faces = rings[k]
        ret = bmesh.ops.extrude_face_region(bm, geom=faces)
        bmesh.ops.delete(bm, geom=faces, context='FACES')
        nv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
        c = sum((v.co for v in nv), Vector()) / len(nv)
        for v in nv:
            v.co.y = c.y + (v.co.y - c.y) * 1.14
            v.co.z = c.z + (v.co.z - c.z) * 1.22
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    snaps["decor"] = bm.copy()
    return snaps, platform


def tuft_positions(pl):
    xs = [pl["xmin"] + 3.2 + i * (pl["xmax"] - pl["xmin"] - 6.4) / 7 for i in range(8)]
    ys = [pl["ymin"] + 2.4 + j * (pl["ymax"] - pl["ymin"] - 4.8) / 3 for j in range(4)]
    pos = [(x, y) for x in xs for y in ys]
    return pos


def tufts_bmesh(positions, z_center, r=1.0, depth=3.0):
    bm = bmesh.new()
    top_verts = []
    for (x, y) in positions:
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=depth,
                                    matrix=__import__("mathutils").Matrix.Translation((x, y, z_center)))
    ztop = z_center + depth / 2
    caps = [f for f in bm.faces if all(abs(v.co.z - ztop) < 1e-4 for v in f.verts)]
    bmesh.ops.split_edges(bm, edges=list({e for f in caps for e in f.edges}))
    top_verts = list({v for f in caps for v in f.verts})
    bm.verts.index_update()
    return bm, top_verts


def build_brush(scene):
    main = new_collection(scene, "Зубная щётка")
    stages = new_collection(scene, "Этапы щётки (скрыто)")
    helper = new_collection(scene, "Профиль сечения")

    # profile rectangle (Rendering: Rectangular, Length = 2 x Width)
    prof = curve_object("Профиль 12×6", [[(-PROFILE_L / 2, -PROFILE_W / 2), (PROFILE_L / 2, -PROFILE_W / 2),
                                         (PROFILE_L / 2, PROFILE_W / 2), (-PROFILE_L / 2, PROFILE_W / 2)]],
                        helper, dims='2D', fill='NONE')
    prof.location = (0, -60, 0)

    line = curve_object("Этап 1 — линия (контур ручки)", [PATH], stages, cyclic=False)
    line.location = (0, 60, 0)
    rect = curve_object("Этап 2 — прямоугольный профиль", [PATH], stages, cyclic=False)
    rect.data.bevel_mode = 'OBJECT'; rect.data.bevel_object = prof; rect.data.use_fill_caps = True
    rect.data.twist_mode = 'Z_UP'; line.data.twist_mode = 'Z_UP'
    rect.location = (0, 0, 0)
    base = to_mesh_object(rect, "tmp_base", stages, scene)
    bm = bmesh.new(); bm.from_mesh(base.data)
    print("converted base bbox:", [round(min(v.co[i] for v in bm.verts),1) for i in range(3)], [round(max(v.co[i] for v in bm.verts),1) for i in range(3)], "verts", len(bm.verts))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    rect.location = (0, 120, 0)
    snaps, platform = build_handle_mesh(bm)
    bpy.data.objects.remove(base)

    names = [("head", "Этап 3 — головка (выдавливание торца)"), ("platform", "Этап 4 — площадка под щетину"),
             ("decor", "Этап 5 — декоративные элементы")]
    for i, (key, nm) in enumerate(names):
        me = bpy.data.meshes.new(nm); snaps[key].to_mesh(me); me.shade_flat()
        ob = bpy.data.objects.new(nm, me); stages.objects.link(ob)
        ob.location = (0, 180 + 60 * i, 0)

    me = bpy.data.meshes.new("Ручка"); bm.to_mesh(me); bm.free()
    handle = bpy.data.objects.new("Ручка", me); main.objects.link(handle)
    me.shade_smooth()
    sub = handle.modifiers.new("Сглаживание (MeshSmooth)", 'SUBSURF'); sub.levels = 3; sub.render_levels = 3
    plastic = principled("Пластик ручки", "C58FD6", rough=0.3, coat=0.4, coat_rough=0.05)
    me.materials.append(plastic)

    # stage: one row of 8 cylinders via Array modifier (analog of Shift-copies)
    rb = bmesh.new(); bmesh.ops.create_cone(rb, cap_ends=True, segments=12, radius1=1.0, radius2=1.0, depth=3.0)
    rme = bpy.data.meshes.new("Этап 6 — ряд из 8 цилиндров (Массив)"); rb.to_mesh(rme); rb.free()
    row = bpy.data.objects.new(rme.name, rme); stages.objects.link(row); row.location = (0, 360, 0)
    arr = row.modifiers.new("Массив", 'ARRAY'); arr.count = 8; arr.relative_offset_displace = (1.6, 0, 0)

    # bristle bases: 4 rows x 8 + 2 pairs at the ends, placed on the SMOOTHED head surface
    from mathutils.bvhtree import BVHTree
    scene.view_layers[0].update()
    dg = scene.view_layers[0].depsgraph
    bvh = BVHTree.FromObject(handle, dg)
    cy = (platform["ymin"] + platform["ymax"]) / 2
    hw = (platform["ymax"] - platform["ymin"]) / 2
    xs = [platform["xmin"] + 4.5 + i * (platform["xmax"] - platform["xmin"] - 10.0) / 7 for i in range(8)]
    ys = [cy - hw * 0.6 + j * (hw * 1.2) / 3 for j in range(4)]
    grid = [(x, y) for x in xs for y in ys]
    grid += [(xs[0] - 3.2, ys[1]), (xs[0] - 3.2, ys[2]), (xs[-1] + 3.0, ys[1]), (xs[-1] + 3.0, ys[2])]
    placed = []
    for (x, y) in grid:
        hit = bvh.ray_cast(Vector((x, y, 200)), Vector((0, 0, -1)))
        low = bvh.ray_cast(Vector((x, y, -200)), Vector((0, 0, 1)))
        if hit[0] is None or low[0] is None or hit[1].z < 0.85:
            continue
        ztop, zbot = hit[0].z, low[0].z
        placed.append((x, y, ztop, zbot))
    depth = 3.0
    tb = bmesh.new(); top_verts = []
    for (x, y, ztop, zbot) in placed:
        zc = ztop + 0.35 - depth / 2
        part, tv = tufts_bmesh([(x, y)], zc, depth=depth)
        idx = [v.index for v in tv]
        tmp = bpy.data.meshes.new("tmp"); part.to_mesh(tmp); part.free()
        base_i = len(tb.verts)
        tb.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        top_verts += [base_i + i for i in idx]
    platform["tufts"] = len(placed)
    tme = bpy.data.meshes.new("Основания щетины"); tb.to_mesh(tme)
    top_idx = top_verts
    tb.free()
    tufts = bpy.data.objects.new("Основания щетины", tme); main.objects.link(tufts)
    vg = tufts.vertex_groups.new(name="Верх пучков"); vg.add(top_idx, 1.0, 'REPLACE')
    bristle_mat = principled("Щетина", "E4BCF2", rough=0.45)
    tme.materials.append(bristle_mat)

    mod = tufts.modifiers.new("Щетина (Hair and Fur)", 'PARTICLE_SYSTEM')
    psys = mod.particle_system
    psys.name = "Щетина"
    ps = psys.settings; ps.name = "Щетина"
    ps.type = 'HAIR'
    ps.count = 7000
    ps.hair_length = 11.0
    ps.emit_from = 'FACE'; ps.use_emit_random = True; ps.distribution = 'RAND'
    ps.child_type = 'SIMPLE'; ps.child_percent = 6; ps.rendered_child_count = 10
    ps.child_radius = 0.3
    ps.roughness_1 = 0.0            # Frizz Root = 0
    ps.roughness_endpoint = 0.05    # Frizz Tip (небольшая распушённость на концах)
    ps.length_random = 0.08         # Rand.Scale = 8
    ps.root_radius = 1.0; ps.tip_radius = 1.0; ps.radius_scale = 0.16   # Root Thick = Tip Thick
    ps.use_close_tip = False
    ps.render_step = 3; ps.display_step = 3
    ps.material_slot = "Щетина"
    psys.vertex_group_density = "Верх пучков"

    scene.render.hair_type = 'STRIP'; scene.render.hair_subdiv = 1

    world(scene, "Мир — чёрный фон", "000000", 1.0)
    add_light(main, "Солнце — основной", 'SUN', (45, 10, 25), 3.0, angle_deg=6)
    add_light(main, "Солнце — заполняющий", 'SUN', (65, 0, 160), 1.2, angle_deg=20)
    add_light(main, "Солнце — контровой", 'SUN', (-50, 0, 0), 2.0, angle_deg=10)
    hx = (platform["xmin"] + platform["xmax"]) / 2
    add_camera(scene, main, "Камера — щётка", (hx - 70, -85, 48), (hx - 22, 0, platform["z"] + 2), lens=50)
    return handle, tufts, stages, helper, platform
