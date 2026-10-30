"""Phase 4 checks: stars outside the band, Moon occlusion, persistence, cost.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/milky_way_phase4_check.py
"""

import json
import os
import sys
import tempfile
import time

import bpy
import numpy as np
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

OUT = os.path.join(HERE, "milky_way", "phase4", "check")
SIZE = 700


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def crop(path, rows, cols):
    return lookdev.load_rgba(path).reshape(SIZE, SIZE, 4)[
        rows[0]:rows[1], cols[0]:cols[1], :3]


def main():
    os.makedirs(OUT, exist_ok=True)
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
    scene.render.resolution_x = SIZE
    scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    scene.ald.palette = "MOONLIT_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = True
    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = False
    scene.ald.milky_way_style = "SCIENTIFIC"
    pole, core, cross = milky_way.axes(scene.ald)
    data = bpy.data.cameras.new("MW Check Camera")
    data.lens = 24.0
    camera = bpy.data.objects.new("MW Check Camera", data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = Vector(core).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera

    scene.ald.milky_way = 0.65
    on_path = render(scene, "mw_on")
    scene.ald.milky_way = 0.0
    off_path = render(scene, "mw_off")
    corner_on = crop(on_path, (0, 120), (0, 120))
    corner_off = crop(off_path, (0, 120), (0, 120))
    corner_delta = float(np.abs(corner_on - corner_off).max())

    # The Moon is drawn after the band: the disc must be identical with the
    # band on or off.
    scene.ald.milky_way = 0.65
    scene.ald.moon_enabled = True
    scene.ald.moon_style = "DETAILED_MOON"
    scene.ald.moon_size = 6.0
    scene.ald.moon_phase = 1.0
    scene.ald.moon_azimuth = 120.0
    scene.ald.moon_elevation = 45.0
    moon_on = render(scene, "moon_on")
    scene.ald.milky_way = 0.0
    moon_off = render(scene, "moon_off")
    disc_delta = float(np.abs(crop(moon_on, (335, 365), (335, 365))
                              - crop(moon_off, (335, 365), (335, 365))).max())
    scene.ald.moon_enabled = False

    scene.ald.milky_way = 0.65
    scene.ald.milky_way_style = "ANIME_CINEMATIC"
    scene.ald.milky_way_dust_contrast = 0.55
    before = render(scene, "persist_before")
    path = os.path.join(tempfile.gettempdir(), "ald_mw_phase4.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    lookdev.enable_addon()
    after = render(scene, "persist_after")
    persist_delta = float(np.abs(lookdev.load_rgba(before)
                                 - lookdev.load_rgba(after)).max())

    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)
    start = time.perf_counter()
    palette.apply_palette(scene, "MOONLIT_NIGHT")
    build = time.perf_counter() - start
    group = bpy.data.node_groups[palette.GRADIENT_GROUP]
    mw_nodes = len(bpy.data.node_groups[milky_way.GROUP].nodes)
    checks = {
        "off_band_stars": {"passed": corner_delta < 0.01,
                           "corner_delta": round(corner_delta, 5)},
        "moon_occlusion": {"passed": disc_delta < 0.005,
                           "disc_delta": round(disc_delta, 5)},
        "persistence": {
            "passed": (scene.ald.milky_way_style == "ANIME_CINEMATIC"
                       and abs(scene.ald.milky_way_dust_contrast - 0.55) < 1e-4
                       and persist_delta < 0.005),
            "style": scene.ald.milky_way_style,
            "dust": scene.ald.milky_way_dust_contrast,
            "pixel_delta": round(persist_delta, 5),
        },
        "cost": {"nodes": len(group.nodes), "mw_nodes": mw_nodes,
                 "build_seconds": round(build, 3)},
    }
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("MW PHASE4 CHECK", json.dumps(checks, sort_keys=True))
    passed = all(check.get("passed", True) for check in checks.values())
    print("MW PHASE4 CHECK", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
