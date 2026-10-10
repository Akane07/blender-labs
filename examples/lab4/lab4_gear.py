import bpy, math
from lab4_common import *


def star_pts(n=50, r_out=50, r_in=45):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((math.cos(a) * r_out, math.sin(a) * r_out))
        a2 = a + math.pi / n
        pts.append((math.cos(a2) * r_in, math.sin(a2) * r_in))
    return pts


HOLE_DIST = 25


def holes(k_count):
    return [('CIRCLE', (math.cos(math.radians(90 + 72 * k)) * HOLE_DIST,
                        math.sin(math.radians(90 + 72 * k)) * HOLE_DIST), 11) for k in range(k_count)]


def build_gear(scene):
    main = new_collection(scene, "Шестерёнка")
    stages = new_collection(scene, "Этапы шестерёнки (скрыто)")

    star = star_pts()
    center = ('CIRCLE', (0, 0), 7)

    s1 = curve_object("Этап 1 — звезда", [star], stages, dims='2D', fill='NONE')
    s2 = curve_object("Этап 2 — звезда и окружности 7 и 11", [star, center] + holes(1), stages, dims='2D', fill='NONE')
    s3 = curve_object("Этап 3 — массив из 5 окружностей", [star, center] + holes(5), stages, dims='2D', fill='NONE')
    s4 = curve_object("Этап 4 — объединённая форма (Attach)", [star, center] + holes(5), stages, dims='2D', fill='BOTH')
    for i, s in enumerate([s1, s2, s3, s4]):
        s.location = (150 + 130 * i, 0, 0)

    gear = curve_object("Шестерёнка", [star, center] + holes(5), main, dims='2D', fill='BOTH')
    gear.data.extrude = 2.0          # толщина 4 (Blender выдавливает на 2 в обе стороны)
    gear.data.resolution_u = 16
    gear.location = (0, 0, 2)

    mat = principled("Позолота", "FFD781", rough=0.3, metallic=1.0, coat=0.6, coat_rough=0.06)
    gear.data.materials.append(mat)

    world(scene, "Мир — синий фон", "0B1633", 0.6)
    add_light(main, "Солнце — основной", 'SUN', (40, 0, 30), 3.2, angle_deg=8)
    add_light(main, "Солнце — заполняющий", 'SUN', (60, 0, 200), 1.5, angle_deg=15)
    add_light(main, "Солнце — контровой", 'SUN', (-55, 0, 170), 2.0, angle_deg=10)
    add_camera(scene, main, "Камера — шестерёнка", (0, -150, 120), (0, 0, 0), lens=50)
    return gear, stages
