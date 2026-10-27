"""Phase 6 release matrix for the World Sky Edition.

3 cloud families x 3 Sun directions at noon, 3 palettes, coverage steps,
camera views, wind and shooting-star cases. 640x360, no compositor.

Run::

    blender -b --factory-startup --python preset_dev/phase6_matrix.py
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "phase6")
FAMILIES = (
    ("cumulus", "CUMULUS", 0.50, 0.05, 0.95, 0.45, 4.0),
    ("stratocumulus", "STRATOCUMULUS", 0.75, 0.95, 0.10, 0.20, 3.8),
    ("cirrus", "CIRRUS", 0.38, 0.30, 0.10, 0.02, 11.0),
)
SUNS = (("front", 15.0, 180.0), ("side", 15.0, 90.0),
        ("back", 15.0, 0.0))
PALETTES = (("day", "SUMMER_NOON"), ("sunset", "GOLDEN_HOUR"),
            ("night", "NEON_NIGHT"))


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def make_sheet(paths, out_path):
    width, height = 640, 360
    columns = 4
    rows = max(1, (len(paths) + columns - 1) // columns)
    sheet = np.zeros((height * rows, width * columns, 4), dtype=np.float32)
    sheet[..., 3] = 1.0
    for index, path in enumerate(paths):
        image = bpy.data.images.load(path)
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
            height, width, 4)
        bpy.data.images.remove(image)
        row = rows - 1 - index // columns
        col = index % columns
        sheet[row * height:(row + 1) * height,
              col * width:(col + 1) * width] = pixels
    image = bpy.data.images.new("Phase6 Sheet", width * columns,
                                height * rows, alpha=True, float_buffer=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = out_path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import palette
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    data = bpy.data.cameras.new("Phase6 Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("Phase6 Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = cam

    report = {"resolution": [640, 360], "cells": []}
    paths = []

    def setup_family(family):
        name, key, amount, flat, vertical, breakup, scale = family
        scene.ald.cloud_amount = amount
        scene.ald.cloud_flatness = flat
        scene.ald.cloud_vertical = vertical
        scene.ald.cloud_breakup = breakup
        scene.ald.cloud_scale = scale
        scene.ald.cloud_type = key
        palette.apply_palette(scene, scene.ald.palette)

    def render(name, label, extra=None):
        path = os.path.join(OUT, name + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        rgb = read_rgb(path)
        entry = {"file": name + ".png", "label": label,
                 "mean_luminance": round(float(rgb.mean()), 5),
                 "max_luminance": round(float(rgb.max()), 4)}
        if extra:
            entry.update(extra)
        report["cells"].append(entry)
        print("P6", name, label)

    # 3 families x 3 sun directions at noon.
    scene.ald.palette = "SUMMER_NOON"
    bpy.ops.ald.apply_palette()
    for family_name, family in zip(("cumulus", "stratocumulus", "cirrus"),
                                   FAMILIES):
        setup_family(family)
        for sun_name, elevation, azimuth in SUNS:
            palette.apply_sun_angles(scene, elevation, azimuth)
            label = "%s / %s" % (family_name, sun_name)
            render("family_%s_%s" % (family_name, sun_name), label,
                   {"family": family_name, "sun": sun_name,
                    "palette": "SUMMER_NOON"})

    # Three palettes with the approved Cumulus.
    setup_family(FAMILIES[0])
    for palette_name, palette_key in PALETTES:
        scene.ald.palette = palette_key
        bpy.ops.ald.apply_palette()
        setup_family(FAMILIES[0])
        palette.apply_sun_angles(scene, 15.0, 90.0)
        render("palette_%s" % palette_name, "palette / %s" % palette_name,
               {"palette": palette_key, "family": "cumulus", "sun": "side"})

    # Coverage steps.
    scene.ald.palette = "SUMMER_NOON"
    bpy.ops.ald.apply_palette()
    setup_family(FAMILIES[0])
    for coverage in (0.0, 0.25, 0.5, 1.0):
        scene.ald.cloud_amount = coverage
        palette.apply_palette(scene, "SUMMER_NOON")
        render("coverage_%03d" % int(coverage * 100),
               "coverage %.2f" % coverage, {"coverage": coverage})

    # Horizon and elevated cameras.
    for name, rotation in (("camera_horizon", (1.55, 0.0, 0.45)),
                           ("camera_elevated", (1.95, 0.0, 0.45))):
        cam.rotation_euler = rotation
        bpy.context.view_layer.update()
        render(name, name, {"camera": list(rotation)})

    # Wind continuity.
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.ald.cloud_amount = 0.5
    scene.ald.cloud_wind = 1.0
    palette.apply_palette(scene, "SUMMER_NOON")
    for frame in (1, 12):
        scene.frame_set(frame)
        render("wind_%02d" % frame, "wind frame %d" % frame,
               {"frame": frame})

    # Shooting stars: single and two simultaneous events.
    scene.ald.palette = "NEON_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = True
    scene.ald.shooting_star_events.clear()
    for index in range(2):
        event = scene.ald.shooting_star_events.add()
        event.name = "Matrix Star %d" % (index + 1)
        event.start_frame = 1
        event.duration = 24
        event.azimuth = -26.0 + index * 8.0
        event.elevation = 20.0
        event.direction = -35.0
        event.brightness = 3.0
        event.thickness = 0.0018
        event.color = (0.88, 0.94, 1.0)
    palette.apply_palette(scene, "NEON_NIGHT")
    for index, frame in enumerate((8, 16)):
        scene.frame_set(frame)
        render("stars_%02d" % frame, "shooting stars frame %d" % frame,
               {"frame": frame, "events": 2})

    make_sheet(paths, os.path.join(OUT, "contact.png"))
    report["sheet"] = "contact.png"
    report["order"] = [entry["file"] for entry in report["cells"]]
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("P6 SHEET", os.path.join(OUT, "contact.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
