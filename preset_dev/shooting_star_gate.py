"""Controlled shooting-star gate.

One persistent event, rendered at four frames. The star must appear only in
its interval, follow one trajectory and leave no objects in the scene.

Run::

    blender -b --factory-startup --python preset_dev/shooting_star_gate.py
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "shooting_star")
FRAMES = (1, 8, 16, 25, 30)


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
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 24
    scene.ald.palette = "NEON_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = True
    scene.ald.shooting_star_events.clear()
    event = scene.ald.shooting_star_events.add()
    event.name = "Gate Star"
    event.start_frame = 1
    event.duration = 24
    event.azimuth = 120.0
    event.elevation = 35.0
    event.direction = -35.0
    event.length = 22.0
    event.trail = 0.40
    event.thickness = 0.005
    event.brightness = 0.9
    event.glow = 2.0
    event.color = (1.0, 0.9, 0.7)
    palette.apply_palette(scene, "NEON_NIGHT")

    data = bpy.data.cameras.new("Star Gate Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("Star Gate Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    azimuth = math.radians(120.0)
    elevation = math.radians(35.0)
    target = cam.location + Vector((
        math.cos(elevation) * math.sin(azimuth),
        math.cos(elevation) * math.cos(azimuth),
        math.sin(elevation))) * 100.0
    cam.rotation_euler = (target - cam.location).to_track_quat(
        "-Z", "Y").to_euler()
    scene.camera = cam
    bpy.context.view_layer.update()

    report = {"event": "Gate Star", "frames": [], "objects": len(scene.objects)}
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        path = os.path.join(OUT, "frame_%03d.png" % frame)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        rgb = read_rgb(path)
        report["frames"].append({
            "frame": frame, "file": os.path.basename(path),
            "max_luminance": round(float(rgb.max()), 4),
            "mean_luminance": round(float(rgb.mean()), 5),
        })
        print("STAR", frame, "max", report["frames"][-1]["max_luminance"])
    report["fx_objects"] = len([obj for obj in bpy.data.objects
                                if obj.get("ald_fx")])
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
