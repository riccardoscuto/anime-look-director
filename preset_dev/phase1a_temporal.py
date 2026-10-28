"""Reproduce the shooting-star lifecycle on a checkout (old or new code).

    blender -b --factory-startup --python preset_dev/phase1a_temporal.py -- \
        --out <dir> --tag master

Renders one event and reports the star pixels at frames around the start, the
end, with duration 2, and with the start at the beginning of the timeline.
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import look, palette  # noqa: E402

W, H = 960, 540
CASES = {
    "main": {"start": 10, "duration": 24,
             "frames": [9, 10, 11, 32, 33, 34, 35]},
    "short": {"start": 10, "duration": 2,
              "frames": [9, 10, 11, 12]},
    "timeline_start": {"start": 1, "duration": 24,
                       "frames": [0, 1, 2, 23, 24, 25]},
}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "phase1a_temporal"), "tag": "run"}
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


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    tag = args["tag"]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
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
    data = bpy.data.cameras.new("Temporal Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Temporal Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    a = math.radians(120.0)
    e = math.radians(40.0)
    direction = Vector((math.cos(e) * math.sin(a),
                        math.cos(e) * math.cos(a), math.sin(e)))
    camera.rotation_euler = (
        camera.location + direction * 100.0
        - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    events = scene.ald.shooting_star_events
    event = events.add()
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 18.0
    event.thickness = 0.0018
    event.brightness = 3.0
    event.glow = 0.8
    event.trail = 0.55
    event.enabled = False
    look.apply_world(scene)
    scene.frame_set(9)
    off_path = os.path.join(out, tag + "_off.png")
    scene.render.filepath = off_path
    bpy.ops.render.render(write_still=True)
    off = read_rgb(off_path)
    event.enabled = True
    result = {"tag": tag, "cases": {}}
    for name, case in CASES.items():
        event.start_frame = case["start"]
        event.duration = case["duration"]
        look.apply_world(scene)
        frames = {}
        for frame in case["frames"]:
            scene.frame_set(frame)
            path = os.path.join(out, "%s_%s_f%02d.png" % (tag, name, frame))
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            diff = np.abs(read_rgb(path) - off).max(axis=2)
            mask = diff > 0.02
            frames[str(frame)] = {
                "pixels": int(mask.sum()),
                "max": round(float(diff.max()), 3),
            }
        result["cases"][name] = {
            "start": case["start"], "duration": case["duration"],
            "frames": frames}
    with open(os.path.join(out, "%s_temporal.json" % tag), "w",
              encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("TEMPORAL " + json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
