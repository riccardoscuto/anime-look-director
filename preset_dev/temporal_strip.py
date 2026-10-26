"""P6 extension: a temporal strip for two families.

The validation matrix samples three ages per family. This strip renders six
ages for the Chrysanthemum and the Willow and builds a 6x2 sheet, so the life
of a burst can be judged frame by frame: birth, growth, falloff and death.

Run::

    blender -b --factory-startup --python preset_dev/temporal_strip.py
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

import baseline_fx

OUT = os.path.join(HERE, "temporal")
FAMILIES = ("CHRYSANTHEMUM", "WILLOW")
AGES = (0.10, 0.35, 0.70, 1.10, 1.60, 2.20)
THUMB = (480, 270)


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def contact_sheet(entries):
    columns = len(AGES)
    rows = len(FAMILIES)
    canvas = np.zeros((rows * THUMB[1], columns * THUMB[0], 4),
                      dtype=np.float32)
    canvas[:, :, 3] = 1.0
    for index, entry in enumerate(entries):
        rgb = read_rgb(entry["path"])
        step_y = max(1, rgb.shape[0] // THUMB[1])
        step_x = max(1, rgb.shape[1] // THUMB[0])
        thumb = rgb[::step_y, ::step_x][:THUMB[1], :THUMB[0]]
        row = index // columns
        column = index % columns
        top = canvas.shape[0] - (row + 1) * THUMB[1]
        left = column * THUMB[0]
        canvas[top:top + thumb.shape[0], left:left + thumb.shape[1],
               :3] = thumb
    image = bpy.data.images.new("ALD Temporal Sheet",
                                width=canvas.shape[1],
                                height=canvas.shape[0], alpha=True)
    image.pixels = canvas.ravel().tolist()
    image.filepath_raw = os.path.join(OUT, "sheet.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return os.path.join(OUT, "sheet.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = "TWILIGHT_DUSK"
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.ink_lines = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    fps = 24.0

    entries = []
    for family in FAMILIES:
        fx.clear(scene)
        fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0,
                            family=family)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        camera.rotation_euler = (Vector(event.target)
                                 - camera.location).to_track_quat(
                                     "-Z", "Y").to_euler()
        camera.data.lens = 32.0
        shots = []
        for age in AGES:
            scene.frame_set(int(system.origin_frame
                                + (event.birth + event.rise_time + age) * fps))
            bpy.context.view_layer.update()
            name = "%s_%03d.png" % (family.lower(), int(age * 100))
            path = os.path.join(OUT, name)
            baseline_fx.render(scene, path)
            shots.append((age, path))
        # One background for the family: the sky is static, the camera and the
        # resolution are fixed, so every frame can be measured against it.
        fx.clear(scene)
        bpy.ops.ald.build()
        background_path = os.path.join(OUT, "%s_bg.png" % family.lower())
        baseline_fx.render(scene, background_path)
        background = read_rgb(background_path)
        os.remove(background_path)
        for age, path in shots:
            rgb = read_rgb(path)
            delta = np.abs(rgb - background).max(axis=2)
            entries.append({
                "family": family, "age": age, "path": path,
                "max_luminance": round(float(rgb.max()), 4),
                "coverage": round(float((delta > 0.02).mean()), 5),
            })
            print("P6T %-14s %.2f max %.3f coverage %.4f"
                  % (family, age, entries[-1]["max_luminance"],
                     entries[-1]["coverage"]))

    sheet = contact_sheet(entries)
    with open(os.path.join(OUT, "temporal.json"), "w", encoding="utf-8") as f:
        json.dump({"families": list(FAMILIES), "ages": list(AGES),
                   "layout": "6 columns of ages, one row per family",
                   "renders": entries,
                   "sheet": os.path.relpath(sheet, HERE)}, f, indent=2)
    fx.clear(scene)
    return 0


if __name__ == "__main__":
    sys.exit(main())
