import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler


def srgb_hex(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def new_collection(scene, name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(col)
    return col


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def curve_object(name, splines, col, dims='3D', fill='FULL', cyclic=True, kind='POLY'):
    """splines: list of point lists; kind POLY or ('CIRCLE', center, radius)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = dims
    if dims == '2D':
        cu.fill_mode = fill
    for sp in splines:
        if isinstance(sp, tuple) and sp[0] == 'CIRCLE':
            _, c, r = sp
            s = cu.splines.new('BEZIER')
            s.bezier_points.add(3)
            k = 0.5523 * r
            pts = [(c[0] + r, c[1]), (c[0], c[1] + r), (c[0] - r, c[1]), (c[0], c[1] - r)]
            tang = [(0, k), (-k, 0), (0, -k), (k, 0)]
            for bp, p, t in zip(s.bezier_points, pts, tang):
                bp.co = (p[0], p[1], 0)
                bp.handle_left = (p[0] - t[0], p[1] - t[1], 0)
                bp.handle_right = (p[0] + t[0], p[1] + t[1], 0)
                bp.handle_left_type = bp.handle_right_type = 'ALIGNED'
            s.use_cyclic_u = True
        else:
            s = cu.splines.new('POLY')
            s.points.add(len(sp) - 1)
            for p, co in zip(s.points, sp):
                p.co = (co[0], co[1], co[2] if len(co) > 2 else 0.0, 1.0)
            s.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    return ob


def principled(name, hexcol, rough=0.5, metallic=0.0, coat=0.0, coat_rough=0.03, ior_level=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = srgb_hex(hexcol)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = coat_rough
    p.inputs["Specular IOR Level"].default_value = ior_level
    m.diffuse_color = srgb_hex(hexcol)
    return m


def look_at(obj, eye, target):
    obj.location = Vector(eye)
    obj.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()


def add_camera(scene, col, name, eye, target, lens=50):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 2000
    ob = bpy.data.objects.new(name, cd)
    col.objects.link(ob)
    look_at(ob, eye, target)
    scene.camera = ob
    return ob


def add_light(col, name, kind, rot_deg, energy, angle_deg=5, size=None, loc=(0, 0, 50), color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'SUN':
        ld.angle = math.radians(angle_deg)
    if kind == 'AREA' and size:
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    ob.rotation_euler = Euler([math.radians(a) for a in rot_deg])
    col.objects.link(ob)
    return ob


def world(scene, name, hexcol, strength=1.0):
    w = bpy.data.worlds.new(name)
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = srgb_hex(hexcol)
    bg.inputs[1].default_value = strength
    w.color = srgb_hex(hexcol)[:3]
    scene.world = w
    return w
