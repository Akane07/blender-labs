"""Проверка .blend лабы 8 повторным открытием: .venv/bin/python scripts/lab8/verify_lab8.py"""
import bpy, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab8", "Лаба8_Blender.blend"))
for sc in bpy.data.scenes:
    print("СЦЕНА", sc.name, "| движок", sc.render.engine, "| кадры", sc.frame_start, sc.frame_end, "| камера", sc.camera.name if sc.camera else None,
          "| clip_end", sc.camera.data.clip_end if sc.camera else None)
    for c in sc.collection.children:
        lc = sc.view_layers[0].layer_collection.children[c.name]
        print("   коллекция", c.name, "| объектов", len(c.objects), "| скрыта" if lc.hide_viewport else "")
O = bpy.data.objects
dups = [o.name for o in O if o.name[-4:-3] == "." and o.name[-3:].isdigit()]
print("ДУБЛИ ИМЁН:", dups)
for o in O:
    if o.modifiers or o.constraints:
        print(" ", o.name, "| мод.:", [m.name for m in o.modifiers], "| огр.:", [c.name for c in o.constraints])
for o in O:
    ad = o.animation_data
    if ad:
        for d in ad.drivers:
            print("ДРАЙВЕР", o.name, d.data_path, d.driver.expression, "simple =", d.driver.is_simple_expression, "valid =", d.driver.is_valid)
        if ad.action:
            print("АНИМАЦИЯ", o.name, ad.action.name)
print("материалов", len(bpy.data.materials), "| групп нод", [g.name for g in bpy.data.node_groups])
long = [(m.name, len(m.name.encode())) for o in bpy.data.objects for m in list(o.modifiers) + list(o.constraints) if len(m.name.encode()) >= 62]
print("ИМЕНА МОДИФИКАТОРОВ/ОГРАНИЧИТЕЛЕЙ НА ГРАНИЦЕ 63 БАЙТ (могли обрезаться):", long)
