"""Видео анимации лабы 5 (Cycles CPU, 960×540) в output/lab5. Запуск: .venv/bin/python scripts/lab5/render_video5.py"""
import bpy, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "output", "lab5", "Лаба5_Blender.blend"))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 960, 540, 100
sc.render.filepath = os.path.join(ROOT, "output", "lab5", "Лаба5_анимация_")
bpy.ops.render.render(animation=True)
print("VIDEO DONE")
