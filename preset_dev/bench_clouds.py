"""Cloud benchmark: creation, refresh, polygons and render at 720p.

Coverage 0.16 / 0.5 / 0.9 / 1.0 with 1 / 3 / 5 layers. Writes metrics.json.

Run::

    blender -b --factory-startup --python preset_dev/bench_clouds.py
"""

import json
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "clouds_bench")


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds_altitude = 90.0
    scene.ald.clouds_depth = 180.0
    scene.ald.clouds_scale = 1.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    camera.rotation_euler = (1.95, 0.0, 0.0)
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    bpy.context.view_layer.update()

    report = {"resolution": [1280, 720], "engine": "EEVEE", "renders": []}
    for layers in (1, 3, 5):
        for coverage in (0.16, 0.5, 0.9, 1.0):
            scene.ald.clouds_layers = layers
            scene.ald.clouds_coverage = coverage
            clouds.remove(scene)
            start = time.perf_counter()
            clouds.create(scene)
            creation = time.perf_counter() - start
            collection = clouds._collection(scene)
            polygons = sum(len(obj.data.polygons)
                           for obj in collection.objects)
            start = time.perf_counter()
            scene.ald.clouds_depth = 220.0
            clouds.refresh(scene)
            refresh = time.perf_counter() - start
            path = os.path.join(OUT, "c%.2f_l%d.png" % (coverage, layers))
            start = time.perf_counter()
            baseline_fx.render(scene, path)
            render = time.perf_counter() - start
            entry = {"coverage": coverage, "layers": layers,
                     "polygons": polygons,
                     "creation_s": round(creation, 4),
                     "refresh_s": round(refresh, 4),
                     "render_s": round(render, 3)}
            report["renders"].append(entry)
            print("BENCH c=%.2f l=%d polys=%d create=%.3fs "
                  "refresh=%.3fs render=%.2fs"
                  % (coverage, layers, polygons, creation, refresh, render))
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
