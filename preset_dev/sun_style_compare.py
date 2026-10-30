"""Clean vs Anime Cinematic on Golden Hour and Summer Noon.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/sun_style_compare.py -- --out preset_dev/sun/style_compare
"""

import json
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

PALETTES = ("GOLDEN_HOUR", "SUMMER_NOON")
CASES = (("CLEAN", 3.0), ("ANIME_CINEMATIC", 3.0),
         ("CLEAN", 10.0), ("ANIME_CINEMATIC", 10.0))
AZIMUTH = 0.0
ELEVATION = 25.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "sun", "style_compare")
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
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Sun Style Camera")
    data.lens = 24.0
    camera = bpy.data.objects.new("Sun Style Camera", data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat(
            "-Z", "Y").to_euler()
    scene.camera = camera

    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = True
    scene.ald.sun_elevation = ELEVATION
    scene.ald.sun_azimuth = AZIMUTH

    cases = []
    for palette_key in PALETTES:
        scene.ald.palette = palette_key
        bpy.ops.ald.apply_palette()
        scene.ald.clouds = False
        scene.ald.stars = False
        for style, size in CASES:
            scene.ald.sun_style = style
            scene.ald.sun_disk_size = size
            name = "%s_%s_%s.png" % (
                palette_key.lower(), style.lower(), str(size).replace(".", "_"))
            path = os.path.join(out, name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            cases.append({"palette": palette_key, "style": style,
                          "size": size, "file": name,
                          "metrics": lookdev.render_stats(path)})
            print("SUN STYLE COMPARE", palette_key, style, size,
                  cases[-1]["metrics"])

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"palettes": PALETTES, "cases": cases}, fh, indent=2)
    print("SUN STYLE COMPARE DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
