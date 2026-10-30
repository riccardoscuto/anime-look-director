"""Phase 3 checks: defaults, size/light separation, styles, persistence.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/sun_phase3_check.py
"""

import json
import os
import sys
import tempfile
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402

OUT = os.path.join(HERE, "sun", "phase3")


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def lower_delta(a, b):
    left = lookdev.load_rgba(a).reshape(900, 900, 4)[450:, :, :3]
    right = lookdev.load_rgba(b).reshape(900, 900, 4)[450:, :, :3]
    return float(np.abs(left - right).max())


def main():
    os.makedirs(OUT, exist_ok=True)
    lookdev.build_scene()
    lookdev.enable_addon()
    scene = bpy.context.scene
    for obj in list(scene.objects):
        if obj.type == "LIGHT" and obj.data and obj.data.type == "SUN":
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    scene.ald.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.stars = False
    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = True
    scene.ald.sun_elevation = 25.0
    scene.ald.sun_azimuth = 0.0

    checks = {}
    sun = next((obj for obj in scene.objects if obj.type == "LIGHT"
                and obj.data and obj.data.type == "SUN"), None)
    energy = float(sun.data.energy)
    rotation = tuple(round(value, 5) for value in sun.rotation_euler)

    scene.ald.sun_disk_size = 1.0
    small = render(scene, "light_size_1")
    scene.ald.sun_disk_size = 12.0
    large = render(scene, "light_size_12")
    checks["light_independent"] = {
        "passed": (abs(float(sun.data.energy) - energy) < 1e-6
                   and tuple(round(value, 5) for value in sun.rotation_euler)
                   == rotation),
        "energy": energy, "rotation": rotation,
        "object_delta": round(lower_delta(small, large), 5),
    }

    scene.ald.sun_style = "ANIME_CINEMATIC"
    checks["cinematic"] = {
        "passed": (abs(scene.ald.sun_edge_softness - 0.6) < 1e-4
                   and abs(scene.ald.sun_glow_radius - 22.0) < 1e-4
                   and abs(scene.ald.sun_glow_gain - 0.65) < 1e-4
                   and abs(scene.ald.sun_limb_warmth - 0.35) < 1e-4),
        "edge": scene.ald.sun_edge_softness,
        "glow_radius": scene.ald.sun_glow_radius,
        "glow_gain": scene.ald.sun_glow_gain,
        "limb": scene.ald.sun_limb_warmth,
    }
    scene.ald.sun_style = "CLEAN"
    checks["clean"] = {
        "passed": (abs(scene.ald.sun_edge_softness - 0.25) < 1e-4
                   and abs(scene.ald.sun_glow_radius - 18.0) < 1e-4
                   and abs(scene.ald.sun_glow_gain - 1.0) < 1e-4),
        "edge": scene.ald.sun_edge_softness,
        "glow_radius": scene.ald.sun_glow_radius,
        "glow_gain": scene.ald.sun_glow_gain,
    }

    scene.ald.sun_disk_size = 4.0
    scene.ald.sun_elevation = -2.0
    below = render(scene, "horizon_below")
    scene.ald.sun_elevation = 0.5
    rising = render(scene, "horizon_rising")
    below_stats = lookdev.render_stats(below)
    rising_stats = lookdev.render_stats(rising)
    checks["horizon"] = {
        "passed": (rising_stats["luma"] > below_stats["luma"] + 0.01),
        "below_luma": below_stats["luma"],
        "rising_luma": rising_stats["luma"],
    }

    scene.ald.sun_elevation = 25.0
    scene.ald.sun_horizon_fade = 12.0
    scene.ald.sun_disk_color = (1.0, 0.9, 0.8)
    before = render(scene, "persist_before")
    path = os.path.join(tempfile.gettempdir(), "ald_sun_phase3.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    lookdev.enable_addon()
    after = render(scene, "persist_after")
    delta = float(np.abs(lookdev.load_rgba(before)
                         - lookdev.load_rgba(after)).max())
    checks["persistence"] = {
        "passed": (abs(scene.ald.sun_horizon_fade - 12.0) < 1e-4
                   and abs(scene.ald.sun_disk_color[0] - 1.0) < 1e-4
                   and delta < 0.005),
        "horizon_fade": scene.ald.sun_horizon_fade,
        "disk_color": tuple(round(value, 3)
                            for value in scene.ald.sun_disk_color),
        "pixel_delta": round(delta, 5),
    }

    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)
    start = time.perf_counter()
    palette.apply_palette(scene, "GOLDEN_HOUR")
    build = time.perf_counter() - start
    group = bpy.data.node_groups[palette.GRADIENT_GROUP]
    checks["cost"] = {"nodes": len(group.nodes),
                      "build_seconds": round(build, 3)}

    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("SUN PHASE3 CHECK", json.dumps(checks, sort_keys=True))
    passed = all(check.get("passed", True) for check in checks.values())
    print("SUN PHASE3 CHECK", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
