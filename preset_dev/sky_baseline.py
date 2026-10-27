"""Cloudless sky matrix for Phase 2.

Four conditions with the World clouds off: noon, sunset, dusk and night. The
same camera, exposure, resolution and palette defaults are used; only the Sun
elevation/azimuth changes. The night condition keeps the stars.

Run::

    blender -b --factory-startup --python preset_dev/sky_baseline.py
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def parse_out():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "sky")
    if "--out" in argv:
        value = argv[argv.index("--out") + 1]
        out = value if os.path.isabs(value) else os.path.join(HERE, value)
    return out


OUT = parse_out()
CONDITIONS = (
    ("noon", "SUMMER_NOON", 35.0, -25.0, False),
    ("sunset", "AFTER_SCHOOL", 4.0, 25.0, False),
    ("dusk", "TWILIGHT_DUSK", -6.0, 25.0, False),
    ("night", "NEON_NIGHT", -18.0, 25.0, True),
)


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
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    data = bpy.data.cameras.new("Sky Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("Sky Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = cam

    report = {"resolution": [1280, 720], "clouds": False, "cells": []}
    for name, key, elevation, azimuth, stars in CONDITIONS:
        scene.ald.palette = key
        bpy.ops.ald.apply_palette()
        # apply_palette restores the preset style; the cloudless test must
        # switch the clouds off afterwards.
        scene.ald.clouds = False
        scene.ald.stars = stars
        palette.apply_palette(scene, key)
        palette.apply_sun_angles(scene, elevation, azimuth)
        bpy.context.view_layer.update()
        path = os.path.join(OUT, name + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        rgb = read_rgb(path)
        report["cells"].append({
            "file": name + ".png", "palette": key,
            "sun_elevation": elevation, "sun_azimuth": azimuth,
            "clouds": False, "stars": stars,
            "mean_luminance": round(float(rgb.mean()), 5),
            "max_luminance": round(float(rgb.max()), 4),
        })
        print("SKY", name, key, elevation, azimuth)
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
