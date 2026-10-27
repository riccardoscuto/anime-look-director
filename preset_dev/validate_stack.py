"""Full-stack validation: World + spatial clouds + strict FX pass + composite.

Three palettes, two camera views each, 800x450. Unlike ``validate_matrix.py``
this matrix renders through the real UI path: the FX pass is generated first,
``Require FX Pass`` is on and the composite consumes only a READY pass.

Run::

    blender -b --factory-startup --python preset_dev/validate_stack.py
"""

import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "validation_stack")
PALETTES = ("TWILIGHT_DUSK", "NEON_NIGHT", "GOLDEN_HOUR")
AGE = 1.4


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def metrics(path):
    rgb = read_rgb(path)
    maximum = np.maximum(rgb.max(axis=2), 1e-4)
    return {
        "mean_luminance": round(float(rgb.mean()), 5),
        "max_luminance": round(float(rgb.max()), 4),
        "clipped_fraction": round(float((maximum > 0.98).mean()), 5),
        "mean_saturation": round(
            float(((rgb.max(axis=2) - rgb.min(axis=2)) / maximum).mean()), 4),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    from anime_look_director import clouds, compositor, fx

    report = {"resolution": [800, 450], "age": AGE, "strict": True,
              "cells": []}
    for palette in PALETTES:
        scene, camera = baseline_fx.build_scene(None)
        baseline_fx.enable_addon()
        settings = scene.ald
        settings.palette = palette
        settings.fx_gn_prototype = True
        settings.fx_glow_strength = 1.0
        settings.fx_glow_threshold = 0.0
        settings.fx_glow_size = 0.35
        settings.clouds_coverage = 0.5
        settings.clouds_layers = 3
        settings.clouds_altitude = 90.0
        settings.clouds_depth = 180.0
        settings.clouds_flash = True
        bpy.ops.ald.apply_palette()
        bpy.ops.ald.build()
        fx.create_fireworks(scene, 3, seed=23, distance=120.0, time=0.0)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        hero = system.events[0]
        camera.rotation_euler = (
            Vector(hero.target) - camera.location).to_track_quat(
                "-Z", "Y").to_euler()
        camera.data.lens = 35.0
        bpy.context.view_layer.update()
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame + AGE * fps))
        bpy.context.view_layer.update()
        clouds.create(scene)
        scene.render.resolution_x = 800
        scene.render.resolution_y = 450
        scene.render.resolution_percentage = 100

        for view, offset in (("fixed", 0.0), ("travelling", 9.0)):
            if offset:
                _origin, forward, _up, right = fx._camera_basis(scene)
                camera.location = camera.location + right * offset
                camera.rotation_euler = (
                    Vector(hero.target) - camera.location).to_track_quat(
                        "-Z", "Y").to_euler()
                bpy.context.view_layer.update()
            start = time.perf_counter()
            compositor.render_fx_pass(scene)
            pass_s = time.perf_counter() - start
            settings.fx_pass_required = True
            bpy.ops.ald.build()
            state, text = compositor.fx_pass_state(scene)
            if state != "ready":
                raise SystemExit("STACK: pass not ready (%s: %s)"
                                 % (state, text))
            path = os.path.join(
                OUT, "%s_%s.png" % (palette.lower(), view))
            render_s = baseline_fx.render(scene, path)
            entry = {"file": os.path.basename(path), "palette": palette,
                     "view": view, "pass_state": state,
                     "pass_s": round(pass_s, 3),
                     "render_s": round(render_s, 3)}
            entry.update(metrics(path))
            report["cells"].append(entry)
            print("STACK", entry["file"], "pass", entry["pass_s"],
                  "render", entry["render_s"], state)
        clouds.remove(scene)
        fx.clear(scene)

    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
