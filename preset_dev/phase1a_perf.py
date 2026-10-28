"""Measure the shooting-star World cost. Run on the branch and on master.

    blender -b --factory-startup --python preset_dev/phase1a_perf.py

Prints a JSON line with the group build/apply time, node count and render time.
"""

import json
import os
import statistics
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import palette  # noqa: E402

W, H = 1280, 720


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.clouds = False
    data = bpy.data.cameras.new("Perf Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Perf Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.2, 0.0, 0.2)
    scene.camera = camera
    event = scene.ald.shooting_star_events.add()
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 18.0
    event.start_frame = 10
    event.duration = 24
    palette.apply_palette(scene, "NEON_NIGHT")
    return scene


def timed(action, count=1):
    values = []
    for _ in range(count):
        start = time.perf_counter()
        action()
        values.append(time.perf_counter() - start)
    return round(statistics.median(values), 4)


def main():
    scene = build()
    # The first apply builds the group; rebuild it explicitly.
    start = time.perf_counter()
    palette.apply_palette(scene, "NEON_NIGHT")
    apply_warm = time.perf_counter() - start
    group = bpy.data.node_groups.get("ALD | World Gradient")
    nodes = len(group.nodes) if group is not None else 0
    bpy.data.node_groups.remove(group)
    start = time.perf_counter()
    palette.apply_palette(scene, "NEON_NIGHT")
    build_time = time.perf_counter() - start
    group = bpy.data.node_groups.get("ALD | World Gradient")
    nodes = len(group.nodes) if group is not None else 0
    apply_time = timed(lambda: palette.apply_palette(scene, "NEON_NIGHT"), 10)
    scene.render.filepath = os.path.join(bpy.app.tempdir, "perf.png")
    scene.frame_set(18)
    bpy.ops.render.render(write_still=True)
    render_720 = timed(lambda: bpy.ops.render.render(write_still=True), 5)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    bpy.ops.render.render(write_still=True)
    render_1080 = timed(lambda: bpy.ops.render.render(write_still=True), 3)
    print("PERF " + json.dumps({
        "build": round(apply_warm, 4),
        "rebuild": round(build_time, 4),
        "apply": apply_time,
        "nodes": nodes,
        "render_720": render_720,
        "render_1080": render_1080,
        "file": palette.__file__,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
