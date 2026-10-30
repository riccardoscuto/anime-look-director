"""Phase 2B board: earthshine candidates, final phases, cloud occlusion.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_phase2b.py -- --out preset_dev/moon/phases/2b
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
from anime_look_director.shaders import moon  # noqa: E402

EARTHSHINE = (0.12, 0.05, 0.02)
FINAL = ("NEW", "WAXING_CRESCENT", "FIRST_QUARTER", "FULL",
         "WANING_CRESCENT")
AZIMUTH = 0.0
ELEVATION = 22.0
SIZE = 4.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "moon", "phases", "2b")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def main():
    out = parse_args()
    os.makedirs(os.path.join(out, "earthshine"), exist_ok=True)
    os.makedirs(os.path.join(out, "final"), exist_ok=True)
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
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Moon 2B Camera")
    data.lens = 135.0
    camera = bpy.data.objects.new("Moon 2B Camera", data)
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
    scene.ald.moon_style = "DETAILED_MOON"
    scene.ald.moon_size = SIZE
    scene.ald.moon_azimuth = AZIMUTH
    scene.ald.moon_elevation = ELEVATION

    earthshine = []
    scene.ald.moon_phase_name = "WAXING_CRESCENT"
    for value in EARTHSHINE:
        scene.ald.moon_earthshine = value
        name = "e_%03d.png" % int(round(value * 100))
        path = os.path.join(out, "earthshine", name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        earthshine.append({"value": value, "file": name,
                           "metrics": lookdev.render_stats(path)})
        print("MOON EARTHSHINE", value, earthshine[-1]["metrics"])

    final = []
    for name in FINAL:
        scene.ald.moon_phase_name = name
        scene.ald.moon_earthshine = 0.05
        path = os.path.join(out, "final", name.lower() + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        final.append({"name": name, "file": name.lower() + ".png",
                      "metrics": lookdev.render_stats(path)})
        print("MOON FINAL", name, final[-1]["metrics"])

    # A cloud actually crossing the disk (seed 2 from the seed search).
    scene.ald.moon_phase_name = "WAXING_CRESCENT"
    scene.ald.moon_size = 6.0
    scene.ald.moon_elevation = 12.0
    scene.ald.clouds = True
    scene.ald.cloud_amount = 0.92
    scene.ald.cloud_type = "CUMULUS"
    scene.ald.cloud_seed = 2
    scene.ald.stars = True
    data.lens = 70.0
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, 12.0)).to_track_quat(
            "-Z", "Y").to_euler()
    cloud_path = os.path.join(out, "final", "crescent_clouds.png")
    scene.render.filepath = cloud_path
    bpy.ops.render.render(write_still=True)
    cloud = {"file": "crescent_clouds.png",
             "metrics": lookdev.render_stats(cloud_path)}
    print("MOON CLOUDS", cloud["metrics"])

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"earthshine": earthshine, "final": final,
                   "clouds": cloud}, fh, indent=2)
    print("MOON 2B DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
