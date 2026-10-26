"""P2 evidence: the same burst at several ages, emission pass only.

The filament must stay continuous without any glow: these images are the
emission on a black world, so a dotted trail cannot hide behind Bloom.

Run::

    blender -b --factory-startup --python preset_dev/p2_age_strip.py
"""

import os
import struct
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

AGES = (0.12, 0.3, 0.6, 1.1)
OUT = os.path.join(HERE, "baseline_fx_p2")


def main():
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = "TWILIGHT_DUSK"
    settings.fx_age = 0.0
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
    from mathutils import Vector
    camera.rotation_euler = (Vector(event.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()

    scene.world = baseline_fx.black_world()
    scene.render.use_compositing = False
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    hidden = []
    baseline_fx.hide_non_fx(scene, hidden)
    try:
        for age in AGES:
            frame = int(system.origin_frame
                        + (event.birth + event.rise_time + age) * fps)
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            name = "age_%03d.png" % int(round(age * 100))
            baseline_fx.render(scene, os.path.join(OUT, name))
            image = bpy.data.images.load(os.path.join(OUT, name))
            pixels = list(image.pixels)
            bpy.data.images.remove(image)
            lit = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.02)
            print("P2 AGE %.2f frame=%d lit=%d" % (age, frame, lit))
    finally:
        baseline_fx.restore_hidden(hidden)
        fx.clear(scene)
    return 0


if __name__ == "__main__":
    sys.exit(main())
