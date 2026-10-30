"""Open a real 2.63.0 file, apply the current build and verify the Moon.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_migration_check.py -- <legacy.blend>
"""

import json
import os
import sys

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
from anime_look_director.shaders import moon  # noqa: E402

OUT = os.path.join(HERE, "moon", "migration")


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def center_luma(path):
    pixels = lookdev.load_rgba(path).reshape(900, 900, 4)[:, :, :3].mean(axis=2)
    return float(pixels[350:550, 350:550].mean())


def sockets(group):
    return {item.name for item in group.interface.items_tree
            if item.item_type == "SOCKET" and item.in_out == "INPUT"}


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if not argv:
        raise SystemExit("legacy .blend path required")
    legacy = os.path.abspath(argv[0])
    os.makedirs(OUT, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=legacy)
    lookdev.enable_addon()
    scene = bpy.context.scene
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    before = {
        "build": group.get("ald_build") if group is not None else None,
        "has_moon_socket": group is not None
        and "Moon Enabled" in sockets(group),
        "has_moon_group": "ALD | Moon" in bpy.data.node_groups,
    }
    before_path = render(scene, "legacy_before")

    bpy.ops.ald.apply_palette()
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    after = {
        "build": group.get("ald_build") if group is not None else None,
        "has_moon_socket": "Moon Enabled" in sockets(group),
        "moon_version": (bpy.data.node_groups[moon.GROUP].get("ald_moon_version")
                         if moon.GROUP in bpy.data.node_groups else None),
    }
    after_path = render(scene, "legacy_after")

    delta = float(np.abs(lookdev.load_rgba(before_path)
                         - lookdev.load_rgba(after_path)).max())

    # Enable the Moon in the migrated file and frame it.
    camera = scene.camera
    if camera is not None:
        from mathutils import Vector
        camera.rotation_euler = Vector(
            moon.direction(0.0, 20.0)).to_track_quat("-Z", "Y").to_euler()
    scene.ald.moon_enabled = True
    scene.ald.moon_azimuth = 0.0
    scene.ald.moon_elevation = 20.0
    moon_path = render(scene, "legacy_moon")
    moon_center = center_luma(moon_path)
    sky_center = center_luma(after_path)

    checks = {
        "legacy_before": before,
        "migrated_after": after,
        "rebuild_pixel_delta": round(delta, 5),
        "moon_visible": moon_center > sky_center + 0.01,
        "moon_center_luma": round(moon_center, 4),
        "sky_center_luma": round(sky_center, 4),
        "passed": (
            before["build"] == 35
            and not before["has_moon_socket"]
            and after["build"] != 35
            and after["has_moon_socket"]
            and after["moon_version"] == moon.MOON_VERSION
            and delta < 0.02
            and moon_center > sky_center + 0.01),
    }
    with open(os.path.join(OUT, "migration.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("MOON MIGRATION", json.dumps(checks, sort_keys=True))
    print("MOON MIGRATION", "PASS" if checks["passed"] else "FAIL")
    return 0 if checks["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
