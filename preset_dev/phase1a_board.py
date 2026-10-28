"""Render the same shooting-star elevations on any checkout (before/after).

    blender -b --factory-startup --python preset_dev/phase1a_board.py -- \
        --out <dir> --tag before

Run it on master for the "before" images and on the branch for "after".
"""

import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import palette  # noqa: E402

W, H = 1280, 720


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "phase1a_board"), "tag": "after"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def stats(on_path, off_path):
    diff = np.abs(read_rgb(on_path) - read_rgb(off_path)).max(axis=2)
    mask = diff > 0.02
    if not mask.any():
        return {"pixels": 0, "max": 0.0, "bbox": None}
    ys, xs = np.nonzero(mask)
    return {"pixels": int(mask.sum()), "max": round(float(diff.max()), 3),
            "bbox": [int(xs.min()), int(ys.min()),
                     int(xs.max()), int(ys.max())]}


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    tag = args["tag"]
    os.makedirs(out, exist_ok=True)
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
    palette.apply_palette(scene, "NEON_NIGHT")
    data = bpy.data.cameras.new("Board Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Board Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    scene.camera = camera
    events = scene.ald.shooting_star_events
    result = {"tag": tag, "elevations": {}}

    def aim(azimuth, elevation):
        a = math.radians(azimuth)
        e = math.radians(elevation)
        direction = (math.cos(e) * math.sin(a),
                     math.cos(e) * math.cos(a), math.sin(e))
        from mathutils import Vector
        target = camera.location + Vector(direction) * 100.0
        camera.rotation_euler = (
            target - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

    def pair(name, frame):
        events[0].enabled = False
        palette.apply_palette(scene, "NEON_NIGHT")
        off = os.path.join(out, "%s_%s_off.png" % (tag, name))
        scene.frame_set(frame)
        scene.render.filepath = off
        bpy.ops.render.render(write_still=True)
        events[0].enabled = True
        palette.apply_palette(scene, "NEON_NIGHT")
        on = os.path.join(out, "%s_%s_on.png" % (tag, name))
        scene.frame_set(frame)
        scene.render.filepath = on
        bpy.ops.render.render(write_still=True)
        values = stats(on, off)
        values["on"] = os.path.basename(on)
        values["off"] = os.path.basename(off)
        return values

    for elevation in (1.0, 5.0, 40.0, 85.0):
        events.clear()
        event = events.add()
        event.azimuth = 120.0
        event.elevation = elevation
        event.direction = 35.0
        event.length = 18.0
        event.start_frame = 10
        event.duration = 24
        event.trail = 0.55
        event.thickness = 0.0018
        event.brightness = 3.0
        event.glow = 0.8
        aim(120.0, elevation)
        result["elevations"][str(elevation)] = pair(
            "elev_%g" % elevation, 18)

    events.clear()
    event = events.add()
    event.azimuth = 120.0
    event.elevation = 3.0
    event.direction = -20.0
    event.length = 12.0
    event.start_frame = 10
    event.duration = 24
    event.trail = 0.55
    event.thickness = 0.0018
    event.brightness = 3.0
    event.glow = 0.8
    aim(120.0, 3.0)
    result["horizon"] = pair("horizon", 33)
    with open(os.path.join(out, "%s_metrics.json" % tag), "w",
              encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("BOARD", tag, json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
