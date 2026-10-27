"""Three World cloud families under the same day sky.

Renders Cumulus, Stratocumulus and Cirrus with the same camera, palette,
resolution and Sun. The purpose is the first Phase 3 gate: the families must be
distinguishable before any sunset or shooting-star work.

Run::

    blender -b --factory-startup --python preset_dev/cloud_families.py
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "cloud_families")
FAMILIES = (
    ("cumulus", "CUMULUS", 0.48, 0.15, 0.90, 0.28, 3.4),
    ("stratocumulus", "STRATOCUMULUS", 0.75, 0.95, 0.10, 0.20, 3.8),
    ("cirrus", "CIRRUS", 0.38, 0.30, 0.10, 0.02, 11.0),
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
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    data = bpy.data.cameras.new("Cloud Family Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("Cloud Family Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = cam
    scene.ald.palette = "SUMMER_NOON"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = True
    scene.ald.stars = False
    report = {"palette": "SUMMER_NOON", "resolution": [1280, 720],
              "families": []}
    for name, key, amount, flatness, vertical, breakup, scale in FAMILIES:
        scene.ald.cloud_type = key
        scene.ald.cloud_amount = amount
        scene.ald.cloud_flatness = flatness
        scene.ald.cloud_vertical = vertical
        scene.ald.cloud_breakup = breakup
        scene.ald.cloud_scale = scale
        scene.ald.cloud_sun_lighting = 1.4
        palette.apply_palette(scene, scene.ald.palette)
        bpy.context.view_layer.update()
        path = os.path.join(OUT, name + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        rgb = read_rgb(path)
        report["families"].append({
            "file": name + ".png", "type": key,
            "amount": amount, "flatness": flatness, "vertical": vertical,
            "breakup": breakup, "scale": scale,
            "mean_luminance": round(float(rgb.mean()), 5),
        })
        print("FAMILY", name, key)
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
