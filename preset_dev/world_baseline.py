"""World-only baseline comparison for the World Sky Edition.

Renders the same camera, frame, exposure and palettes with the World shader of
an installed Anime Look Director. Spatial clouds, 3D FX and the compositor are
disabled: the image is the World only.

The script is version-agnostic: it is copied next to each archived add-on and
run with an isolated BLENDER_USER_SCRIPTS. It never saves a .blend.

Run::

    blender -b --factory-startup --python preset_dev/world_baseline.py -- \
        --out DIR --tag v1.0.3 --res 1280x720
"""

import json
import os
import sys

import bpy

PALETTES = ("SUMMER_NOON", "AFTER_SCHOOL", "NEON_NIGHT")
RESOLUTIONS = ((1280, 720), (1920, 1080))


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = "world_baseline"
    tag = "current"
    resolutions = RESOLUTIONS
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    if "--tag" in argv:
        tag = argv[argv.index("--tag") + 1]
    if "--res" in argv:
        value = argv[argv.index("--res") + 1].lower()
        width, height = value.split("x")
        resolutions = ((int(width), int(height)),)
    return os.path.abspath(out), tag, resolutions


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


def build_scene(width, height):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)

    camera_data = bpy.data.cameras.new("World Baseline Camera")
    camera_data.lens = 32.0
    camera_data.clip_start = 0.1
    camera_data.clip_end = 1000.0
    camera = bpy.data.objects.new("World Baseline Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    return scene


def main():
    out, tag, resolutions = parse_args()
    os.makedirs(out, exist_ok=True)
    report = {"tag": tag, "palettes": list(PALETTES),
              "camera": {"location": [0.0, -12.0, 3.0],
                         "rotation": [1.75, 0.0, 0.45], "lens": 32.0},
              "frame": 1, "exposure": 0.0, "engine": "BLENDER_EEVEE",
              "view_transform": "AgX", "renders": []}
    for width, height in resolutions:
        for palette in PALETTES:
            scene = build_scene(width, height)
            enable_addon()
            if not hasattr(scene, "ald"):
                raise RuntimeError("Anime Look Director is not registered")
            scene.ald.palette = palette
            # World clouds and stars only: the spatial/3D systems do not exist
            # in the old tags and stay off in the current one.
            if hasattr(scene.ald, "clouds"):
                scene.ald.clouds = True
            if hasattr(scene.ald, "stars"):
                scene.ald.stars = True
            if hasattr(scene.ald, "clouds_created"):
                scene.ald.clouds_created = False
            if hasattr(scene.ald, "fx_backend"):
                scene.ald.fx_backend = "OFF"
            bpy.ops.ald.apply_palette()
            scene.render.use_compositing = False
            bpy.context.view_layer.update()
            name = "%s_%dx%d.png" % (palette.lower(), width, height)
            scene.render.filepath = os.path.join(out, name)
            bpy.ops.render.render(write_still=True)
            report["renders"].append({
                "file": name, "palette": palette,
                "resolution": [width, height],
                "world": scene.world.name if scene.world else None,
            })
            print("WORLD BASELINE", tag, name)
    with open(os.path.join(out, "world_baseline.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
