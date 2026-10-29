"""Render the shooting-star curvature sweep for the Phase 4 feature."""

import json
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


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.abspath(argv[0]) if argv else os.path.join(HERE, "curvature")
    os.makedirs(out, exist_ok=True)
    scene, camera = p1.fixture("eevee")
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    settings = scene.ald
    settings.clouds = False
    settings.stars = False
    settings.shooting_star_events.clear()
    event = settings.shooting_star_events.add()
    event.name = "Curvature Test"
    event.start_frame = 10
    event.duration = 24
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 30.0
    event.trail = 0.85
    event.thickness = 0.006
    event.brightness = 3.0
    event.glow = 0.8
    event.enabled = True
    settings.shooting_star_selected = 0
    p1.aim(camera, 120.0, 40.0)
    scene.frame_set(20)
    values = (0.0, 0.5, 1.0, -1.0)
    report = {"engine": "eevee", "frame": 20, "values": {}}
    for value in values:
        event.curvature = value
        look.apply_world(scene)
        path = os.path.join(out, "curvature_%s.png" % str(value).replace(".", "_"))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        report["values"][str(value)] = {
            "requested": value,
            "property": float(event.curvature),
            "path": path,
        }
    with open(os.path.join(out, "curvature.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("CURVATURE", json.dumps(report["values"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
