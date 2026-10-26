"""P3: the full composite at four glow settings, same frame and camera.

The glow is a compositor node, so its effect must be judged on the final image,
not on the glow-only pass. The scene is the P0 baseline scene.

Run::

    blender -b --factory-startup --python preset_dev/glow_variants.py
"""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "calibration_p3")
VARIANTS = ((0.0, 0.35), (1.0, 0.35), (1.0, 0.7))


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx
    from mathutils import Vector

    settings = scene.ald
    settings.palette = "TWILIGHT_DUSK"
    settings.fx_age = 0.0
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.ink_lines = True
    settings.depth_near = 20.0
    settings.depth_far = 140.0
    settings.fx_gn_prototype = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    fx.create_fireworks(scene, 1, seed=baseline_fx.SEED,
                        distance=baseline_fx.DISTANCE, time=0.0,
                        family=baseline_fx.FAMILY)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * fps))
    camera.rotation_euler = (Vector(event.target)
                             - camera.location).to_track_quat(
                                 "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    try:
        for strength, size in VARIANTS:
            settings.fx_glow_threshold = 0.0
            settings.fx_glow_size = size
            settings.fx_glow_strength = strength
            name = "full_g%.2f_s%.2f.png" % (strength, size)
            baseline_fx.render(scene, os.path.join(OUT, name))
            print("P3 VARIANT", name)
    finally:
        fx.clear(scene)
    return 0


if __name__ == "__main__":
    sys.exit(main())
