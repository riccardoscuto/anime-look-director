"""Phase 4 Milky Way boards: presets, styles, structure and clouds."""

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
from anime_look_director.shaders import milky_way, moon  # noqa: E402

AZIMUTH = 120.0
ELEVATION = 45.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "milky_way", "phase4")
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
    scene.eevee.taa_render_samples = 48
    scene.render.resolution_x = 900
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    data = bpy.data.cameras.new("Milky Way Camera")
    data.lens = 16.0
    camera = bpy.data.objects.new("Milky Way Camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    def aim(azimuth, elevation, lens=16.0):
        data.lens = lens
        camera.rotation_euler = Vector(
            moon.direction(azimuth, elevation)).to_track_quat(
                "-Z", "Y").to_euler()

    def setup(key):
        scene.ald.palette = key
        bpy.ops.ald.apply_palette()
        scene.ald.clouds = False
        scene.ald.stars = True
        scene.ald.sun_disk = False
        scene.ald.sun_glow_enabled = False
        aim(AZIMUTH, ELEVATION)

    def shot(name, label):
        path = os.path.join(out, name + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        cases.append({"label": label, "file": name + ".png",
                      "metrics": lookdev.render_stats(path)})
        print("MW CASE", name, cases[-1]["metrics"])

    cases = []
    setup("MOONLIT_NIGHT")
    scene.ald.milky_way_style = "SCIENTIFIC"
    shot("moonlit_scientific", "Moonlit Night, Scientific")
    scene.ald.milky_way_style = "ANIME_CINEMATIC"
    shot("moonlit_cinematic", "Moonlit Night, Cinematic")
    setup("BLUE_HOUR")
    scene.ald.milky_way_style = "SCIENTIFIC"
    shot("blue_hour", "Blue Hour, Scientific")
    setup("TWILIGHT_DUSK")
    scene.ald.milky_way_style = "SCIENTIFIC"
    shot("twilight", "Twilight Dusk, Scientific")

    setup("MOONLIT_NIGHT")
    scene.ald.milky_way_style = "SCIENTIFIC"
    scene.ald.milky_way_dust_contrast = 0.20
    shot("dust_low", "Dust contrast 0.20")
    scene.ald.milky_way_dust_contrast = 0.95
    shot("dust_high", "Dust contrast 0.95")

    setup("MOONLIT_NIGHT")
    scene.ald.milky_way_style = "SCIENTIFIC"
    pole, core, cross = milky_way.axes(scene.ald)
    data.lens = 50.0
    camera.rotation_euler = Vector(core).to_track_quat("-Z", "Y").to_euler()
    shot("core_close", "Core close-up (50 mm)")

    setup("MOONLIT_NIGHT")
    scene.ald.milky_way_style = "SCIENTIFIC"
    scene.ald.clouds = True
    scene.ald.cloud_amount = 0.55
    scene.ald.cloud_seed = 2
    shot("clouds", "Band behind clouds")

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"cases": cases, "azimuth": AZIMUTH,
                   "elevation": ELEVATION}, fh, indent=2)
    print("MW PHASE4 DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
