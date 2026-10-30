"""Phase 3 Sun boards: sizes, styles and horizon fade.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/sun_phase3.py -- --out preset_dev/sun/phase3
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

SIZES = (0.5, 2.0, 6.0, 12.0)
STYLE_CASES = (("CLEAN", 3.0), ("ANIME_CINEMATIC", 3.0),
               ("CLEAN", 10.0), ("ANIME_CINEMATIC", 10.0))
HORIZON = (-2.0, 0.5, 3.0, 8.0)
AZIMUTH = 0.0
ELEVATION = 25.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "sun", "phase3")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def aim(camera, azimuth, elevation):
    camera.rotation_euler = Vector(
        moon.direction(azimuth, elevation)).to_track_quat(
            "-Z", "Y").to_euler()


def main():
    out = parse_args()
    os.makedirs(os.path.join(out, "sizes"), exist_ok=True)
    os.makedirs(os.path.join(out, "styles"), exist_ok=True)
    os.makedirs(os.path.join(out, "horizon"), exist_ok=True)
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

    data = bpy.data.cameras.new("Sun Phase Camera")
    data.lens = 24.0
    camera = bpy.data.objects.new("Sun Phase Camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    aim(camera, AZIMUTH, ELEVATION)

    scene.ald.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = False
    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = True
    scene.ald.sun_elevation = ELEVATION
    scene.ald.sun_azimuth = AZIMUTH

    sizes = []
    scene.ald.sun_style = "CLEAN"
    for size in SIZES:
        scene.ald.sun_disk_size = size
        path = os.path.join(out, "sizes", "size_%s.png"
                            % str(size).replace(".", "_"))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        sizes.append({"size": size, "file": os.path.basename(path),
                      "metrics": lookdev.render_stats(path)})
        print("SUN SIZE", size, sizes[-1]["metrics"])

    styles = []
    scene.ald.sun_disk_size = 3.0
    for style, size in STYLE_CASES:
        scene.ald.sun_style = style
        scene.ald.sun_disk_size = size
        name = "%s_%s.png" % (style.lower(), str(size).replace(".", "_"))
        path = os.path.join(out, "styles", name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        styles.append({"style": style, "size": size, "file": name,
                       "metrics": lookdev.render_stats(path)})
        print("SUN STYLE", style, size, styles[-1]["metrics"])

    horizon = []
    scene.ald.sun_style = "CLEAN"
    scene.ald.sun_disk_size = 4.0
    data.lens = 35.0
    aim(camera, AZIMUTH, 0.0)
    for elevation in HORIZON:
        scene.ald.sun_elevation = elevation
        name = "elev_%s.png" % str(elevation).replace(".", "_").replace(
            "-", "m")
        path = os.path.join(out, "horizon", name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        horizon.append({"elevation": elevation, "file": name,
                        "metrics": lookdev.render_stats(path)})
        print("SUN HORIZON", elevation, horizon[-1]["metrics"])

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"sizes": sizes, "styles": styles, "horizon": horizon,
                   "azimuth": AZIMUTH, "elevation": ELEVATION}, fh, indent=2)
    print("SUN PHASE3 DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
