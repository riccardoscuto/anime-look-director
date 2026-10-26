"""P5 evidence: 2.5D cloud cards and the fireworks behind them.

Renders the same show with and without the cloud layer at dusk, and once at
night. The clouds are real cards at 160-320 m with a dithered cutout: the
firework behind a card is hidden by the visible render itself.

Run::

    blender -b --factory-startup --python preset_dev/clouds.py
"""

import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "clouds")
AGE = 2.0


def scene_for(palette):
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
    settings.clouds_coverage = 0.5
    settings.clouds_layers = 3
    settings.clouds_altitude = 90.0
    settings.clouds_depth = 180.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    fx.create_fireworks(scene, 3, seed=17, distance=95.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    hero = system.events[0]
    camera.rotation_euler = (Vector(hero.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    camera.data.lens = 40.0
    bpy.context.view_layer.update()
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame + AGE * fps))
    bpy.context.view_layer.update()
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    return scene, camera


def main():
    os.makedirs(OUT, exist_ok=True)
    from anime_look_director import clouds, fx

    report = {"age": AGE, "renders": []}
    # Dusk: the same frame without and with the cloud layer.
    scene, camera = scene_for("TWILIGHT_DUSK")
    baseline_fx.render(scene, os.path.join(OUT, "dusk_off.png"))
    report["renders"].append({"palette": "TWILIGHT_DUSK", "clouds": False,
                              "file": "dusk_off.png"})
    layers = clouds.create(scene)
    baseline_fx.render(scene, os.path.join(OUT, "dusk_on.png"))
    report["renders"].append({"palette": "TWILIGHT_DUSK", "clouds": True,
                              "layers": layers, "file": "dusk_on.png"})
    fx.clear(scene)
    clouds.remove(scene)

    # Night: clouds and a five-burst show.
    scene, camera = scene_for("NEON_NIGHT")
    fx.clear(scene)
    fx.create_fireworks(scene, 5, seed=23, distance=95.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    camera.rotation_euler = (Vector(system.events[0].target)
                             - camera.location).to_track_quat(
                                 "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.frame_set(int(system.origin_frame + 2.0 * 24))
    clouds.create(scene)
    baseline_fx.render(scene, os.path.join(OUT, "night_on.png"))
    report["renders"].append({"palette": "NEON_NIGHT", "clouds": True,
                              "layers": 3, "file": "night_on.png"})
    fx.clear(scene)
    clouds.remove(scene)

    with open(os.path.join(OUT, "clouds.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    for entry in report["renders"]:
        print("P5", entry["palette"], "clouds", entry["clouds"],
              entry["file"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
