"""Render the Phase 1B visual comparison set on any checkout.

Run on the current 1A code and on the v2.60.1 tag:

    blender -b --factory-startup --gpu-backend vulkan --python \
        preset_dev/phase1b_visual.py -- --out <dir> --tag current

Same camera, lens, resolution, exposure and color management for both.
Clouds off; no compositor; no code changes.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import palette  # noqa: E402

W, H = 1280, 720
EVENT = {
    "azimuth": 120.0, "elevation": 40.0, "direction": 35.0,
    "length": 18.0, "start_frame": 10, "duration": 24, "trail": 0.55,
    "thickness": 0.0018, "brightness": 3.0, "glow": 0.8,
    "color": (0.88, 0.94, 1.0),
}
FOUR = [
    {"azimuth": 105.0, "elevation": 30.0, "direction": -35.0, "length": 12.0,
     "color": (0.88, 0.94, 1.0)},
    {"azimuth": 114.0, "elevation": 38.0, "direction": 60.0, "length": 14.0,
     "color": (1.0, 0.80, 0.60)},
    {"azimuth": 126.0, "elevation": 42.0, "direction": 120.0, "length": 14.0,
     "color": (0.70, 0.90, 1.0)},
    {"azimuth": 135.0, "elevation": 34.0, "direction": -90.0, "length": 12.0,
     "color": (1.0, 1.0, 0.90)},
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "", "tag": "current"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def look_direction(azimuth, elevation):
    a = math.radians(azimuth)
    e = math.radians(elevation)
    return Vector((math.cos(e) * math.sin(a),
                   math.cos(e) * math.cos(a),
                   math.sin(e))).normalized()


def aim(camera, azimuth, elevation):
    direction = look_direction(azimuth, elevation)
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


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
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    data = bpy.data.cameras.new("Phase 1B Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 1B Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    scene.camera = camera
    events = scene.ald.shooting_star_events

    def set_palette(key):
        scene.ald.palette = key
        if hasattr(scene.ald, "clouds"):
            scene.ald.clouds = False
        palette.apply_palette(scene, key)

    def one(values):
        events.clear()
        event = events.add()
        merged = dict(EVENT)
        merged.update(values)
        for field, value in merged.items():
            setattr(event, field, value)
        return event

    def render(name, frame):
        scene.frame_set(frame)
        path = os.path.join(out, "%s_%s.png" % (tag, name))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        return path

    params = {
        "tag": tag, "base": "v2.60.1" if tag == "2601" else "phase-1a",
        "resolution": [W, H], "lens": 32.0, "camera": [0.0, -12.0, 3.0],
        "view_transform": "AgX", "look": "None", "exposure": 0.0,
        "gamma": 1.0, "clouds": False, "compositor": False,
        "event": EVENT, "four": FOUR,
    }
    set_palette("NEON_NIGHT")
    for elevation in (1.0, 5.0, 40.0, 85.0):
        one({"elevation": elevation})
        aim(camera, 120.0, elevation)
        render("night_elev_%g" % elevation, 18)

    one({})
    aim(camera, 120.0, 40.0)
    for frame in range(9, 35):
        render("life_f%02d" % frame, frame)

    events.clear()
    for values in FOUR:
        event = events.add()
        merged = dict(EVENT)
        merged.update(values)
        for field, value in merged.items():
            setattr(event, field, value)
    aim(camera, 120.0, 36.0)
    render("four_night", 20)

    set_palette("TWILIGHT_DUSK")
    one({"elevation": 20.0})
    aim(camera, 120.0, 20.0)
    render("twilight_20", 18)

    set_palette("NEON_NIGHT")
    one({"elevation": 40.0})
    aim(camera, 120.0, 40.0)
    render("night_40", 18)
    params["frames"] = {"elevations": 18, "four": 20, "twilight": 18,
                        "lifecycle": [9, 34]}
    with open(os.path.join(out, "%s_params.json" % tag), "w",
              encoding="utf-8") as handle:
        json.dump(params, handle, indent=2)
    print("PHASE1B", tag, "done", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
