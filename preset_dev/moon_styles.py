"""Render the Phase 1 Moon style board.

Four styles at three apparent sizes, same sky, same camera, sky only.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_styles.py -- --out preset_dev/moon/styles
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402
from anime_look_director.shaders import moon  # noqa: E402

STYLES = ("ANIME_CLEAN", "ANIME_PAINTERLY", "DETAILED_MOON", "ETHEREAL_MOON")
SIZES = (1.2, 3.0, 6.0)
AZIMUTH = 0.0
ELEVATION = 22.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "moon", "styles")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def main():
    out = parse_args()
    os.makedirs(out, exist_ok=True)
    lookdev.build_scene()
    lookdev.enable_addon()
    scene = bpy.context.scene

    for obj in list(scene.objects):
        if obj.type == "LIGHT" and obj.data and obj.data.type == "SUN":
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.hide_render = True

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Moon Style Camera")
    data.lens = 135.0
    camera = bpy.data.objects.new("Moon Style Camera", data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat(
            "-Z", "Y").to_euler()
    scene.camera = camera

    scene.ald.palette = "MOONLIT_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = False
    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = False
    scene.ald.moon_enabled = True
    scene.ald.moon_azimuth = AZIMUTH
    scene.ald.moon_elevation = ELEVATION

    cases = []
    for style in STYLES:
        scene.ald.moon_style = style
        for size in SIZES:
            scene.ald.moon_size = size
            name = "%s_%sdeg.png" % (style.lower(), str(size).replace(".", "_"))
            path = os.path.join(out, name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            cases.append({"style": style, "size": size, "file": name,
                          "metrics": lookdev.render_stats(path)})
            print("MOON STYLE", style, size, cases[-1]["metrics"])

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"styles": STYLES, "sizes": SIZES,
                   "azimuth": AZIMUTH, "elevation": ELEVATION,
                   "cases": cases}, fh, indent=2)
    print("MOON BOARD DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
