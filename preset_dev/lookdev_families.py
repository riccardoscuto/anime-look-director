"""Render the firework families for a shape comparison.

Usage:
  blender -b --factory-startup --python preset_dev/lookdev_families.py -- [--out DIR]

Every family is rendered with the same palette and the same camera, so the
shapes can be compared without relying on the colours (acceptance condition
of the phase 5 of the technical guide).

Outputs one PNG per family plus a contact sheet and a metadata file.
This is a development tool: it never saves a .blend.
"""

import json
import os
import sys
import tempfile

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 11
DISTANCE = 70.0
#: The burst happens at the end of the rise: the frame shows the expansion.
FRAME = 44


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(tempfile.gettempdir(), "ald_lookdev_families")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return out


def enable_addon():
    if hasattr(bpy.types.Scene, "ald"):
        return
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
    except Exception:
        parent = os.path.dirname(ADDON_PATH)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import importlib
        importlib.import_module(MODULE).register()


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass
    camera_data = bpy.data.cameras.new("Family Camera")
    camera_data.lens = 40.0
    camera = bpy.data.objects.new("Family Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 2.0)
    camera.rotation_euler = (1.92, 0.0, 0.0)
    scene.camera = camera
    return scene


def load_rgba(path):
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    bpy.data.images.remove(image)
    return pixels


def make_sheet(paths, out_path, size=640, columns=3):
    rows = max(1, (len(paths) + columns - 1) // columns)
    sheet = np.zeros((size * rows, size * columns, 4), dtype=np.float32)
    sheet[..., 3] = 1.0
    for index, path in enumerate(paths):
        pixels = load_rgba(path).reshape(size, size, 4)
        # Blender image rows start at the bottom: first row on top.
        row = rows - 1 - index // columns
        col = index % columns
        sheet[row * size:(row + 1) * size,
              col * size:(col + 1) * size] = pixels
    image = bpy.data.images.new("ALD Family Sheet", size * columns,
                                size * rows, alpha=True, float_buffer=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = out_path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def main():
    out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    scene = build_scene()
    enable_addon()
    from anime_look_director import fx as fx_module

    settings = scene.ald
    settings.palette = "TWILIGHT_DUSK"
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.ink_lines = True
    settings.depth_near = 25.0
    settings.depth_far = 130.0
    settings.fx_age = 0.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()

    paths = []
    for family in fx_module.FAMILIES:
        fx_module.create_fireworks(scene, 1, seed=SEED, distance=DISTANCE,
                                   time=0.0, family=family)
        scene.frame_set(FRAME)
        bpy.context.view_layer.update()
        path = os.path.join(out_dir, "%s.png" % family.lower())
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        config = fx_module.FAMILY_CONFIG[family]
        print("ALD FAMILY", family, "spokes", config["spokes"],
              "speed", config["speed"], "drag", config["drag"],
              "life", config["life"], "trail", config["trail"],
              "pistil", config["pistil"])

    sheet_path = os.path.join(out_dir, "sheet.png")
    make_sheet(paths, sheet_path)
    metadata = {
        "renderer": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "fps": scene.render.fps,
        "frame": FRAME,
        "view_transform": scene.view_settings.view_transform,
        "palette": scene.ald.palette,
        "seed": SEED,
        "distance": DISTANCE,
        "camera": {
            "location": [round(v, 4) for v in scene.camera.location],
            "rotation_euler": [round(v, 4)
                               for v in scene.camera.rotation_euler],
            "lens": scene.camera.data.lens,
        },
        "families": {family: dict(fx_module.FAMILY_CONFIG[family])
                     for family in fx_module.FAMILIES},
        "outputs": [os.path.basename(path) for path in paths],
    }
    meta_path = os.path.join(out_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print("ALD FAMILY SHEET", sheet_path)
    print("ALD FAMILY METADATA", meta_path)


if __name__ == "__main__":
    main()
