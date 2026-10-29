"""Render the cloud Sun Scatter before/after sweep."""

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
from anime_look_director import look, palette  # noqa: E402


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.abspath(argv[0]) if argv else os.path.join(HERE, "cloud_scatter")
    os.makedirs(out, exist_ok=True)
    scene, camera = p1.fixture("eevee")
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    settings = scene.ald
    settings.palette = "GOLDEN_HOUR"
    palette.apply_palette(scene, "GOLDEN_HOUR")
    settings.clouds = True
    settings.cloud_type = "CUMULUS"
    settings.cloud_amount = 0.78
    settings.cloud_scale = 3.2
    settings.cloud_breakup = 0.35
    settings.cloud_sun_lighting = 1.25
    settings.sun_elevation = 12.0
    settings.sun_azimuth = 120.0
    settings.sun_disk = True
    settings.sun_glow = 0.65
    import math
    sun_dir = palette.sun_toward(scene)
    sun_az = math.degrees(math.atan2(sun_dir[0], sun_dir[1]))
    sun_el = math.degrees(math.asin(max(-1.0, min(1.0, sun_dir[2]))))
    p1.aim(camera, sun_az, sun_el)
    scene.frame_set(1)
    values = (0.0, 0.5, 1.0)
    report = {"engine": "eevee", "values": {}}
    for value in values:
        settings.cloud_sun_scatter = value
        look.apply_world(scene)
        path = os.path.join(out, "scatter_%s.png" % str(value).replace(".", "_"))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        report["values"][str(value)] = {"requested": value,
                                        "property": float(settings.cloud_sun_scatter),
                                        "path": path}
    with open(os.path.join(out, "scatter.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("SCATTER", json.dumps(report["values"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
