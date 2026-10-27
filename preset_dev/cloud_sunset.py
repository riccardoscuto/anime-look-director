"""Sunset gate for the approved Cumulus family (2.59.1).

Two views of the same Cumulus field:
- the fixed camera, sun on the side;
- the camera aimed at the sun, for the backlit rim.

Run::

    blender -b --factory-startup --python preset_dev/cloud_sunset.py
"""

import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "cloud_sunset")


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import palette
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    data = bpy.data.cameras.new("Sunset Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("Sunset Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = cam

    scene.ald.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = True
    scene.ald.stars = False
    scene.ald.cloud_type = "CUMULUS"
    scene.ald.cloud_amount = 0.50
    scene.ald.cloud_scale = 4.0
    scene.ald.cloud_flatness = 0.05
    scene.ald.cloud_vertical = 0.95
    scene.ald.cloud_breakup = 0.45
    scene.ald.cloud_detail = 0.25
    scene.ald.cloud_sun_lighting = 1.8
    scene.ald.cloud_rim_boost = 3.0
    scene.ald.cloud_delta_gain = 1.4
    palette.apply_palette(scene, scene.ald.palette)
    palette.apply_sun_angles(scene, 4.0, 25.0)
    bpy.context.view_layer.update()
    side_path = os.path.join(OUT, "sunset_side.png")
    scene.render.filepath = side_path
    bpy.ops.render.render(write_still=True)

    toward = palette.sun_toward(scene)
    if toward is not None:
        target = cam.location + Vector(toward) * 100.0
        cam.rotation_euler = (
            target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    back_path = os.path.join(OUT, "sunset_backlit.png")
    scene.render.filepath = back_path
    bpy.ops.render.render(write_still=True)

    report = {
        "palette": "GOLDEN_HOUR", "sun_elevation": 4.0,
        "sun_azimuth": 25.0, "resolution": [1280, 720],
        "cloud": "CUMULUS", "coverage": 0.50, "scale": 4.0,
        "views": [
            {"file": "sunset_side.png",
             "mean_luminance": round(float(read_rgb(side_path).mean()), 5)},
            {"file": "sunset_backlit.png",
             "mean_luminance": round(float(read_rgb(back_path).mean()), 5)},
        ],
    }
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("SUNSET", report["views"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
