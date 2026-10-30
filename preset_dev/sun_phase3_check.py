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


def crop_delta(a, b, rows=(300, 900), cols=(0, 900)):
    left = lookdev.load_rgba(a).reshape(900, 900, 4)[
        rows[0]:rows[1], cols[0]:cols[1], :3]
    right = lookdev.load_rgba(b).reshape(900, 900, 4)[
        rows[0]:rows[1], cols[0]:cols[1], :3]
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
    delta = crop_delta(small, large)

    # Second angle: a close-up with the ground and spheres, so shadows are
    # clearly visible in the comparison.
    close_data = bpy.data.cameras.new("Sun Close Camera")
    close_data.lens = 50.0
    close = bpy.data.objects.new("Sun Close Camera", close_data)
    scene.collection.objects.link(close)
    close.location = (4.0, -6.0, 3.0)
    from mathutils import Vector
    close.rotation_euler = (Vector((0.0, 0.0, 1.0)) - close.location).to_track_quat(
        "-Z", "Y").to_euler()
    original_camera = scene.camera
    scene.camera = close
    scene.ald.sun_disk_size = 1.0
    close_small = render(scene, "light_close_1")
    scene.ald.sun_disk_size = 12.0
    close_large = render(scene, "light_close_12")
    close_delta = crop_delta(close_small, close_large, rows=(250, 900))
    scene.camera = original_camera

    checks["light_independent"] = {
        "passed": (abs(float(sun.data.energy) - energy) < 1e-6
                   and tuple(round(value, 5) for value in sun.rotation_euler)
                   == rotation
                   and delta < 0.01 and close_delta < 0.01),
        "energy": energy, "rotation": rotation,
        "object_delta": round(delta, 5),
        "object_delta_close": round(close_delta, 5),
    }

    # Disk and glow toggles are independent, including the animated path.
    def node_values():
        node = palette._gradient_node(scene.world.node_tree)
        return (node.inputs["Sun Strength"].default_value,
                node.inputs["Sun Glow"].default_value)

    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = True
    palette.update_sun_controls(scene)
    glow_only = node_values()
    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = False
    palette.update_sun_controls(scene)
    disk_only = node_values()
    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = False
    palette.update_sun_controls(scene)
    both_off = node_values()
    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = True
    palette.update_sun_controls(scene)
    checks["toggle_independence"] = {
        "passed": (glow_only[0] == 0.0 and glow_only[1] > 0.0
                   and disk_only[0] > 0.0 and disk_only[1] == 0.0
                   and both_off == (0.0, 0.0)),
        "glow_only": [round(value, 4) for value in glow_only],
        "disk_only": [round(value, 4) for value in disk_only],
        "both_off": [round(value, 4) for value in both_off],
    }

    scene.ald.sun_style = "ANIME_CINEMATIC"
    checks["cinematic"] = {
        "passed": (abs(scene.ald.sun_edge_softness - 0.8) < 1e-4
                   and abs(scene.ald.sun_glow_radius - 26.0) < 1e-4
                   and abs(scene.ald.sun_glow_gain - 0.75) < 1e-4
                   and abs(scene.ald.sun_limb_warmth - 0.45) < 1e-4),
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
