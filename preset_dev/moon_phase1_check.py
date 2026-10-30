"""Phase 1 Moon technical checks: geometry, horizon, persistence, cost.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_phase1_check.py
"""

import json
import math
import os
import statistics
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
from anime_look_director.shaders import moon  # noqa: E402

OUT = os.path.join(HERE, "moon", "checks")
SIZE = 6.0
AZIMUTH = 0.0
ELEVATION = 22.0


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def blend_time(scene, key):
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)
    start = time.perf_counter()
    palette.apply_palette(scene, key)
    return time.perf_counter() - start


def median_render(scene, path, count=3):
    values = []
    for _ in range(count):
        scene.render.filepath = path
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        values.append(time.perf_counter() - start)
    return statistics.median(values)


def disk_aspect(path):
    pixels = lookdev.load_rgba(path).reshape(-1, 4)[:, :3]
    luma = pixels.mean(axis=1)
    mask = luma > 0.60
    height = int(round(math.sqrt(len(luma))))
    rows = np.nonzero(mask.reshape(height, height).any(axis=1))[0]
    cols = np.nonzero(mask.reshape(height, height).any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return 0.0, 0, 0
    width = int(cols[-1] - cols[0] + 1)
    height_px = int(rows[-1] - rows[0] + 1)
    return width / height_px, width, height_px


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
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    data = bpy.data.cameras.new("Moon Check Camera")
    data.lens = 135.0
    camera = bpy.data.objects.new("Moon Check Camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    scene.ald.palette = "MOONLIT_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.stars = False
    scene.ald.clouds = False
    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = False
    scene.ald.moon_enabled = True
    scene.ald.moon_style = "DETAILED_MOON"
    scene.ald.moon_size = SIZE
    scene.ald.moon_azimuth = AZIMUTH
    scene.ald.moon_elevation = ELEVATION
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat("-Z", "Y").to_euler()

    checks = {}
    disk_path = render(scene, "disk_6deg")
    aspect, width, height = disk_aspect(disk_path)
    checks["disk_circular"] = {
        "passed": abs(aspect - 1.0) <= 0.03,
        "aspect": round(aspect, 3), "width": width, "height": height}

    # Same disk high in the sky and at another azimuth: no projection skew.
    scene.ald.moon_azimuth = 120.0
    scene.ald.moon_elevation = 60.0
    camera.rotation_euler = Vector(
        moon.direction(120.0, 60.0)).to_track_quat("-Z", "Y").to_euler()
    high_path = render(scene, "disk_6deg_high")
    high_aspect, high_w, high_h = disk_aspect(high_path)
    checks["disk_circular_high"] = {
        "passed": abs(high_aspect - 1.0) <= 0.03,
        "aspect": round(high_aspect, 3), "width": high_w, "height": high_h}
    scene.ald.moon_azimuth = AZIMUTH
    scene.ald.moon_elevation = ELEVATION
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat("-Z", "Y").to_euler()

    # Below the horizon the Moon must not change the image at all.
    data.lens = 24.0
    camera.rotation_euler = Vector(
        moon.direction(0.0, 0.0)).to_track_quat("-Z", "Y").to_euler()
    scene.ald.moon_elevation = -6.0
    hidden_on = render(scene, "horizon_below_on")
    scene.ald.moon_enabled = False
    hidden_off = render(scene, "horizon_below_off")
    scene.ald.moon_enabled = True
    delta = float(np.abs(lookdev.load_rgba(hidden_on)
                         - lookdev.load_rgba(hidden_off)).max())
    checks["below_horizon_hidden"] = {"passed": delta < 0.01,
                                      "max_delta": round(delta, 5)}

    # A rising Moon is partially faded by the horizon blend.
    scene.ald.moon_elevation = 2.0
    rising = render(scene, "horizon_rising")
    rising_luma = lookdev.render_stats(rising)["luma"]
    checks["rising_visible"] = {"passed": rising_luma > 0.20,
                                "luma": rising_luma}

    # Clouds and stars in front: visual evidence.
    data.lens = 85.0
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, 15.0)).to_track_quat("-Z", "Y").to_euler()
    scene.ald.moon_elevation = 15.0
    scene.ald.stars = True
    scene.ald.clouds = True
    render(scene, "context_clouds_stars")
    scene.ald.stars = False
    scene.ald.clouds = False

    # Persistence: save, reopen, verify the controls and the pixels.
    data.lens = 135.0
    scene.ald.moon_elevation = ELEVATION
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat("-Z", "Y").to_euler()
    before = render(scene, "persist_before")
    path = os.path.join(tempfile.gettempdir(), "ald_moon_check.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    after = render(scene, "persist_after")
    delta = float(np.abs(lookdev.load_rgba(before)
                         - lookdev.load_rgba(after)).max())
    checks["persistence"] = {
        "passed": (scene.ald.moon_enabled
                   and scene.ald.moon_style == "DETAILED_MOON"
                   and abs(scene.ald.moon_size - SIZE) < 1e-4
                   and delta < 0.005),
        "max_pixel_delta": round(delta, 5),
        "style": scene.ald.moon_style,
        "size": scene.ald.moon_size,
        "seed": scene.ald.moon_seed,
    }

    # Cost: group size, rebuild and render time with the Moon on and off.
    build = blend_time(scene, "MOONLIT_NIGHT")
    group = bpy.data.node_groups[palette.GRADIENT_GROUP]
    moon_nodes = len(bpy.data.node_groups[moon.GROUP].nodes)
    count = {"nodes": len(group.nodes), "links": len(group.links),
             "moon_nodes": moon_nodes}
    off_path = os.path.join(OUT, "perf_off.png")
    scene.ald.moon_enabled = False
    off_time = median_render(scene, off_path)
    scene.ald.moon_enabled = True
    on_time = median_render(scene, off_path)
    checks["cost"] = {
        "group": count,
        "build_seconds": round(build, 3),
        "render_off_seconds": round(off_time, 3),
        "render_on_seconds": round(on_time, 3),
        "render_delta_pct": round((on_time / off_time - 1.0) * 100.0, 1),
    }

    with open(os.path.join(OUT, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("MOON CHECKS", json.dumps(checks, sort_keys=True))
    passed = all(check.get("passed", True) for check in checks.values())
    print("MOON CHECK", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
