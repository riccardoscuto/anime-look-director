"""A/B evidence for the directional cloud rim.

The same cloud layer and camera under two sun azimuths. The rim is measured as
the luminance difference between the left and right halves of the upper frame;
a directional rim must change side with the sun, a uniform outline must not.

Run::

    blender -b --factory-startup --python preset_dev/cloud_rim.py
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "cloud_rim")
VIEWS = ((90.0, "sun_left.png"), (270.0, "sun_right.png"))


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, look, palette

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds_coverage = 0.5
    scene.ald.clouds_layers = 2
    scene.ald.clouds_altitude = 90.0
    scene.ald.clouds_depth = 180.0
    scene.ald.clouds_quality = "FINAL"
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.ald.clouds = False
    look.apply_world(scene)
    clouds.remove(scene)
    clouds.create(scene)
    camera.rotation_euler = (1.95, 0.0, 0.0)
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()

    report = {"resolution": [800, 450], "palette": "AFTER_SCHOOL",
              "views": []}
    for azimuth, name in VIEWS:
        palette.apply_sun_angles(scene, 18.0, azimuth)
        clouds.update_flash(scene)
        bpy.context.view_layer.update()
        path = os.path.join(OUT, name)
        baseline_fx.render(scene, path)
        rgb = read_rgb(path)
        top = rgb[: int(rgb.shape[0] * 0.6)]
        left = float(top[:, : top.shape[1] // 2].mean())
        right = float(top[:, top.shape[1] // 2:].mean())
        entry = {"file": name, "azimuth": azimuth,
                 "left": round(left, 5), "right": round(right, 5),
                 "asymmetry": round(left - right, 5)}
        report["views"].append(entry)
        print("RIM", name, entry["asymmetry"])
    clouds.remove(scene)
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
