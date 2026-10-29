"""Render the shooting-star thickness sweep for the Phase 4 fix.

Run on the current tree:

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/star_thickness.py -- --out <dir>

Run the same script on the base 4db6718 worktree for the before set.
"""

import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import phase1a_shooting_stars as p1  # noqa: E402
from anime_look_director import look  # noqa: E402


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.abspath(argv[0]) if argv else os.path.join(HERE, "thickness")
    return out


def main():
    out = parse_args()
    os.makedirs(out, exist_ok=True)
    scene, camera = p1.fixture("eevee")
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    settings = scene.ald
    settings.clouds = False
    settings.stars = False
    settings.shooting_star_events.clear()
    event = settings.shooting_star_events.add()
    event.name = "Thickness Test"
    event.start_frame = 10
    event.duration = 24
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 18.0
    event.trail = 0.55
    event.brightness = 3.0
    event.glow = 0.8
    event.enabled = True
    settings.shooting_star_selected = 0
    p1.aim(camera, 120.0, 40.0)
    scene.frame_set(20)
    values = (0.0018, 0.005, 0.01, 0.05)
    report = {"engine": "eevee", "frame": 20, "values": {}}
    paths = {}
    for value in values:
        event.thickness = value
        look.apply_world(scene)
        group = bpy.data.node_groups.get("ALD | World Gradient")
        actual = None
        if group is not None and scene.world is not None:
            tree = scene.world.node_tree
            node = next((n for n in tree.nodes
                         if n.bl_idname == "ShaderNodeGroup"
                         and n.node_tree == group), None) if tree else None
            if node is not None and "Star0 Thickness" in node.inputs:
                actual = node.inputs["Star0 Thickness"].default_value
        path = os.path.join(out, "thickness_%s.png" % str(value).replace(".", "_"))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths[str(value)] = path
        report["values"][str(value)] = {
            "requested": value,
            "property": float(event.thickness),
            "shader_socket": actual,
        }
    report["paths"] = paths
    with open(os.path.join(out, "thickness.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("THICKNESS", json.dumps(report["values"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
