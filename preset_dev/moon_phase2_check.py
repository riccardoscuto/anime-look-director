"""Phase 2 checks: phase area, waxing side, Sun link, persistence.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_phase2_check.py
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

OUT = os.path.join(HERE, "moon", "phases", "check")
SIZE = 6.0
AZIMUTH = 0.0
ELEVATION = 22.0
PHASES = (0.0, 0.25, 0.5, 0.75, 1.0)


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def lit_stats(path, size=500):
    pixels = lookdev.load_rgba(path).reshape(size, size, 4)[:, :, :3].mean(axis=2)
    yy, xx = np.mgrid[0:size, 0:size]
    # Restrict to the disk: the halo is not part of the illuminated area.
    circle = ((xx - size * 0.5) ** 2 + (yy - size * 0.5) ** 2
              < (size * 0.205) ** 2)
    mask = (pixels > 0.45) & circle
    area = int(mask.sum())
    if area == 0:
        return 0, 0.5
    cols = np.nonzero(mask)[1]
    return area, float(cols.mean() / size)


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
    scene.render.resolution_x = 500
    scene.render.resolution_y = 500
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Moon Phase Check Camera")
    data.lens = 135.0
    camera = bpy.data.objects.new("Moon Phase Check Camera", data)
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
    scene.ald.moon_earthshine = 0.0
    scene.ald.moon_surface_contrast = 0.0
    scene.ald.moon_crater_strength = 0.0
    scene.ald.moon_surface_detail = 0.0

    checks = {}
    areas = {}
    for phase in PHASES:
        scene.ald.moon_phase = phase
        path = render(scene, "phase_%03d" % int(round(phase * 100)))
        areas[phase], _ = lit_stats(path)
    full_area = max(1, areas[1.0])
    fractions = {str(phase): round(areas[phase] / full_area, 3)
                 for phase in PHASES}
    checks["phase_area"] = {
        "passed": all(abs(fractions[str(phase)] - phase) <= 0.07
                      for phase in PHASES),
        "fractions": fractions,
    }

    # Compositing at intermediate alpha: a wide soft edge must not produce a
    # dark ring from a double attenuation.
    scene.ald.moon_phase = 1.0
    scene.ald.moon_earthshine = 0.0
    scene.ald.moon_edge_softness = 0.6
    edge_path = render(scene, "alpha_edge")
    edge_pixels = lookdev.load_rgba(edge_path).reshape(500, 500, 4)
    row = edge_pixels[250, 250:430, :3].mean(axis=1)
    sky = float(row[-10:].mean())
    disk = float(row[:10].mean())
    steps = np.diff(row)
    checks["alpha_edge"] = {
        "passed": (float(steps.max()) <= 0.01
                   and float(row.min()) >= min(disk, sky) - 0.01),
        "disk": round(disk, 3), "sky": round(sky, 3),
        "max_step_up": round(float(steps.max()), 4),
        "min": round(float(row.min()), 3),
    }
    scene.ald.moon_edge_softness = 0.04

    scene.ald.moon_phase = 0.25
    scene.ald.moon_waxing = True
    waxing_path = render(scene, "waxing_025")
    _, waxing_x = lit_stats(waxing_path)
    scene.ald.moon_waxing = False
    waning_path = render(scene, "waning_025")
    _, waning_x = lit_stats(waning_path)
    checks["waxing_side"] = {
        "passed": waxing_x > 0.52 and waning_x < 0.48,
        "waxing_x": round(waxing_x, 3), "waning_x": round(waning_x, 3),
    }

    # Sun-linked: a Sun 90 degrees away must give a quarter phase, lit toward
    # the Sun. With this azimuth convention +90 is screen-left.
    scene.ald.moon_phase_mode = "SUN_LINKED"
    scene.ald.sun_elevation = ELEVATION
    scene.ald.sun_azimuth = 90.0
    linked_path = render(scene, "sun_linked_90")
    linked_area, linked_x = lit_stats(linked_path)
    sun = Vector((math.cos(math.radians(ELEVATION)) * math.sin(math.radians(90.0)),
                  -math.cos(math.radians(ELEVATION)) * math.cos(math.radians(90.0)),
                  math.sin(math.radians(ELEVATION))))
    moon_dir = Vector(moon.direction(AZIMUTH, ELEVATION))
    separation = math.degrees(math.acos(max(-1.0, min(1.0, sun.dot(moon_dir)))))
    expected = 0.5 * (1.0 - math.cos(math.radians(separation)))
    checks["sun_linked"] = {
        "passed": (abs(linked_area / full_area - expected) <= 0.06
                   and linked_x < 0.48),
        "fraction": round(linked_area / full_area, 3),
        "expected": round(expected, 3),
        "separation_degrees": round(separation, 2),
        "centroid_x": round(linked_x, 3),
    }

    # Animation: phase keyframes must drive the disk through the frame handler.
    scene.ald.moon_phase_mode = "MANUAL"
    scene.ald.moon_waxing = True
    scene.ald.moon_phase = 0.0
    scene.frame_set(1)
    scene.keyframe_insert(data_path="ald.moon_phase", frame=1)
    scene.ald.moon_phase = 1.0
    scene.keyframe_insert(data_path="ald.moon_phase", frame=24)
    animated = []
    for frame in (1, 8, 16, 24):
        scene.frame_set(frame)
        path = render(scene, "anim_%02d" % frame)
        area, _ = lit_stats(path)
        animated.append(round(area / full_area, 3))
    scene.animation_data_clear()
    checks["animation"] = {
        "passed": (animated[0] <= 0.03 and animated[-1] >= 0.95
                   and animated[0] < animated[1] < animated[2] < animated[3]),
        "fractions": animated,
    }

    # Crescent in context: clouds and stars in front.
    scene.ald.moon_phase = 0.18
    scene.ald.moon_waxing = True
    scene.ald.moon_earthshine = 0.05
    scene.ald.clouds = True
    scene.ald.stars = True
    data.lens = 85.0
    camera.rotation_euler = Vector(
        moon.direction(0.0, 15.0)).to_track_quat("-Z", "Y").to_euler()
    scene.ald.moon_elevation = 15.0
    render(scene, "crescent_context")
    data.lens = 135.0
    camera.rotation_euler = Vector(
        moon.direction(AZIMUTH, ELEVATION)).to_track_quat("-Z", "Y").to_euler()
    scene.ald.moon_elevation = ELEVATION
    scene.ald.clouds = False
    scene.ald.stars = False

    # Persistence of the phase controls and the render.
    scene.ald.moon_phase_mode = "MANUAL"
    scene.ald.moon_phase = 0.25
    scene.ald.moon_waxing = True
    before = render(scene, "persist_before")
    path = os.path.join(tempfile.gettempdir(), "ald_moon_phase_check.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    lookdev.enable_addon()
    after = render(scene, "persist_after")
    delta = float(np.abs(lookdev.load_rgba(before)
                         - lookdev.load_rgba(after)).max())
    checks["persistence"] = {
        "passed": (abs(scene.ald.moon_phase - 0.25) < 1e-4
                   and scene.ald.moon_waxing
                   and scene.ald.moon_phase_mode == "MANUAL"
                   and delta < 0.005),
        "phase": scene.ald.moon_phase,
        "waxing": scene.ald.moon_waxing,
        "pixel_delta": round(delta, 5),
    }

    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    build = None
    if group is not None:
        bpy.data.node_groups.remove(group)
        start = time.perf_counter()
        palette.apply_palette(scene, "MOONLIT_NIGHT")
        build = time.perf_counter() - start
    checks["cost"] = {
        "nodes": len(bpy.data.node_groups[palette.GRADIENT_GROUP].nodes),
        "moon_nodes": len(bpy.data.node_groups[moon.GROUP].nodes),
        "build_seconds": round(build, 3) if build else None,
    }

    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("MOON PHASE CHECK", json.dumps(checks, sort_keys=True))
    passed = all(check.get("passed", True) for check in checks.values())
    print("MOON PHASE CHECK", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
