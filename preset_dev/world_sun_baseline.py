"""Sun-disk baseline for the World Sky Edition.

The camera is aimed at the active sun so the disk, glow and horizon light are
visible. Same version-agnostic setup as ``world_baseline.py``.

Run::

    blender -b --factory-startup --python preset_dev/world_sun_baseline.py -- \
        --out DIR --tag v1.0.3
"""

import json
import os
import sys

import bpy
from mathutils import Vector

PALETTES = ("GOLDEN_HOUR", "AFTER_SCHOOL")
RESOLUTION = (1280, 720)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = "world_baseline/sun"
    tag = "current"
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    if "--tag" in argv:
        tag = argv[argv.index("--tag") + 1]
    return os.path.abspath(out), tag


def enable_addon():
    if hasattr(bpy.context.scene, "ald"):
        return
    try:
        bpy.ops.preferences.addon_enable(module="anime_look_director")
    except Exception:
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import importlib
        importlib.import_module("anime_look_director").register()


def main():
    out, tag = parse_args()
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    enable_addon()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)

    camera_data = bpy.data.cameras.new("World Sun Camera")
    camera_data.lens = 32.0
    camera_data.clip_start = 0.1
    camera_data.clip_end = 1000.0
    camera = bpy.data.objects.new("World Sun Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    scene.camera = camera

    from anime_look_director import palette
    report = {"tag": tag, "resolution": list(RESOLUTION), "renders": []}
    for key in PALETTES:
        scene.ald.palette = key
        if hasattr(scene.ald, "clouds"):
            scene.ald.clouds = True
        if hasattr(scene.ald, "clouds_created"):
            scene.ald.clouds_created = False
        if hasattr(scene.ald, "fx_backend"):
            scene.ald.fx_backend = "OFF"
        bpy.ops.ald.apply_palette()
        scene.render.use_compositing = False
        toward = palette.sun_toward(scene)
        if toward is not None:
            target = camera.location + Vector(toward) * 100.0
            camera.rotation_euler = (
                target - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        name = "sun_%s_1280x720.png" % key.lower()
        scene.render.filepath = os.path.join(out, name)
        bpy.ops.render.render(write_still=True)
        report["renders"].append({"file": name, "palette": key,
                                  "sun_toward": list(toward)
                                  if toward is not None else None})
        print("WORLD SUN", tag, name)
    with open(os.path.join(out, "world_sun_baseline.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
