"""Render the Phase 2 Moon phase board and a continuous phase sweep.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_phases.py -- --out preset_dev/moon/phases
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

PHASES = ("NEW", "WAXING_CRESCENT", "FIRST_QUARTER", "WAXING_GIBBOUS",
          "FULL", "WANING_GIBBOUS", "LAST_QUARTER", "WANING_CRESCENT")
SWEEP = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
SIZE = 4.0
AZIMUTH = 0.0
ELEVATION = 22.0


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "moon", "phases")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def main():
    out = parse_args()
    os.makedirs(os.path.join(out, "named"), exist_ok=True)
    os.makedirs(os.path.join(out, "sweep"), exist_ok=True)
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
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Moon Phase Camera")
    data.lens = 135.0
    camera = bpy.data.objects.new("Moon Phase Camera", data)
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

    named = []
    for name in PHASES:
        scene.ald.moon_phase_name = name
        path = os.path.join(out, "named", name.lower() + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        named.append({"name": name, "phase": scene.ald.moon_phase,
                      "waxing": scene.ald.moon_waxing,
                      "file": os.path.basename(path),
                      "metrics": lookdev.render_stats(path)})
        print("MOON PHASE", name, scene.ald.moon_phase, named[-1]["metrics"])

    sweep = []
    scene.ald.moon_phase_name = "CUSTOM"
    for index, phase in enumerate(SWEEP):
        scene.ald.moon_phase = phase
        name = "phase_%03d.png" % int(round(phase * 100))
        path = os.path.join(out, "sweep", name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        sweep.append({"phase": phase, "file": "sweep/" + name,
                      "metrics": lookdev.render_stats(path)})
        print("MOON SWEEP", phase, sweep[-1]["metrics"])

    # Sun-linked: the Sun 90 degrees away must produce a quarter phase.
    scene.ald.moon_phase_mode = "SUN_LINKED"
    scene.ald.sun_elevation = ELEVATION
    scene.ald.sun_azimuth = 90.0
    path = os.path.join(out, "sun_linked_quarter.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sun_linked = {"file": os.path.basename(path),
                  "metrics": lookdev.render_stats(path)}

    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"size": SIZE, "azimuth": AZIMUTH, "elevation": ELEVATION,
                   "named": named, "sweep": sweep, "sun_linked": sun_linked},
                  fh, indent=2)
    print("MOON PHASE BOARD DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
