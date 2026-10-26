"""Final showcase: the whole stack together at 1920x1080.

A directed five-burst show, the 2.5D cloud bands and the full compositor
(Cryptomatte FX, painterly filters, ink, light wrap) in one frame, at night and
at dusk. This is the integration evidence: P1 and P3 (compositing and
shading), P4 (composition), P5 (clouds) in the same scene.

Run::

    blender -b --factory-startup --python preset_dev/showcase.py
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

OUT = os.path.join(HERE, "showcase")
AGE = 2.0


def build(palette, count, lens, name):
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx

    settings = scene.ald
    settings.palette = palette
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.ink_lines = True
    settings.depth_near = 20.0
    settings.depth_far = 320.0
    settings.fx_glow_strength = 1.0
    settings.fx_glow_threshold = 0.0
    settings.fx_glow_size = 0.35
    settings.clouds_amount = 0.65
    settings.clouds_height = 0.35
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()

    fx.create_fireworks(scene, count, seed=23, distance=120.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    hero = system.events[0]
    camera.rotation_euler = (Vector(hero.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    camera.data.lens = lens
    bpy.context.view_layer.update()
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame + AGE * fps))
    bpy.context.view_layer.update()

    # The cards are placed along the final camera basis.
    clouds.create(scene, float(settings.clouds_amount),
                  float(settings.clouds_height))
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    baseline_fx.render(scene, os.path.join(OUT, name))
    events = len(system.events)
    clouds_count = len(clouds._collection(scene).objects)
    fx.clear(scene)
    clouds.remove(scene)
    return {"file": name, "palette": palette, "bursts": events,
            "clouds": clouds_count, "age": AGE, "lens": lens}


def main():
    os.makedirs(OUT, exist_ok=True)
    report = [
        build("NEON_NIGHT", 5, 35.0, "night_5_bursts.png"),
        build("TWILIGHT_DUSK", 3, 40.0, "dusk_3_bursts.png"),
    ]
    with open(os.path.join(OUT, "showcase.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for entry in report:
        print("SHOWCASE", entry["file"], entry["bursts"], "bursts",
              entry["clouds"], "clouds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
