"""P4 evidence: the directed show and its depth hierarchy.

Renders a 3-burst and a 5-burst show at dusk and one at night, and records the
per-event depth and screen position. The hero is the closest and the largest;
the secondary and distant bursts sit farther and are dimmed by the atmospheric
fade.

Run::

    blender -b --factory-startup --python preset_dev/composition.py
"""

import json
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "composition")
AGE = 2.0


def build(palette, count, name):
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = palette
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.ink_lines = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    camera.data.lens = 45.0
    fx.create_fireworks(scene, count, seed=17, distance=95.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    hero = system.events[0]
    camera.rotation_euler = (Vector(hero.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame + AGE * fps))
    bpy.context.view_layer.update()

    events = []
    for index, event in enumerate(system.events):
        target = Vector(event.target)
        projected = world_to_camera_view(scene, camera, target)
        fraction = fx.event_frame_fraction(scene, event)
        events.append({
            "index": index,
            "family": event.family,
            "birth": round(float(event.birth), 3),
            "size": round(float(event.size), 3),
            "distance": round((target - camera.location).length, 2),
            "screen": [round(projected.x, 3), round(projected.y, 3)],
            "in_frame": bool(fraction >= 0.95 and projected.z > 0.0),
            "frame_fraction": round(fraction, 3),
        })
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    baseline_fx.render(scene, os.path.join(OUT, name))
    fx.clear(scene)
    return {"palette": palette, "count": count, "age": AGE,
            "events": events}


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    report.append(build("TWILIGHT_DUSK", 3, "show_3_dusk.png"))
    report.append(build("NEON_NIGHT", 5, "show_5_night.png"))
    report.append(build("GOLDEN_HOUR", 3, "show_3_golden.png"))
    with open(os.path.join(OUT, "composition.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    for entry in report:
        print("P4", entry["palette"], entry["count"])
        for event in entry["events"]:
            print("  P4 event", event["index"], event["family"],
                  "birth", event["birth"], "dist", event["distance"],
                  "size", event["size"], "screen", event["screen"],
                  "in_frame", event["in_frame"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
