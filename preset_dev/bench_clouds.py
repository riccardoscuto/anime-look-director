"""Cloud benchmark: creation, refresh, polygons and render at 720p.

Coverage 0.16 / 0.5 / 0.9 / 1.0 with 1 / 3 / 5 layers, three runs per scenario.
Writes metrics.json with the medians and the machine/Build identifiers.

Run::

    blender -b --factory-startup --python preset_dev/bench_clouds.py
"""

import json
import os
import platform
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "clouds_bench")
REPEATS = 3


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


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

    report = {
        "resolution": [1280, 720],
        "engine": "EEVEE",
        "blender": bpy.app.version_string,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "repeats": REPEATS,
        "renders": [],
    }
    try:
        import gpu
        report["gpu"] = gpu.platform.renderer_get()
    except Exception:
        report["gpu"] = "unavailable in background"
    for layers in (1, 3, 5):
        for coverage in (0.16, 0.5, 0.9, 1.0):
            scene.ald.clouds_layers = layers
            scene.ald.clouds_coverage = coverage
            creations = []
            refreshes = []
            renders = []
            polygons = 0
            path = os.path.join(OUT, "c%.2f_l%d.png" % (coverage, layers))
            for _ in range(REPEATS):
                scene.ald.clouds_depth = 180.0
                clouds.remove(scene)
                start = time.perf_counter()
                clouds.create(scene)
                creations.append(time.perf_counter() - start)
                collection = clouds._collection(scene)
                polygons = sum(len(obj.data.polygons)
                               for obj in collection.objects)
                start = time.perf_counter()
                baseline_fx.render(scene, path)
                renders.append(time.perf_counter() - start)
                start = time.perf_counter()
                scene.ald.clouds_depth = 220.0
                clouds.refresh(scene)
                refreshes.append(time.perf_counter() - start)
                scene.ald.clouds_depth = 180.0
            entry = {
                "coverage": coverage,
                "layers": layers,
                "polygons": polygons,
                "creation_s": round(median(creations), 4),
                "refresh_s": round(median(refreshes), 4),
                "render_s": round(median(renders), 3),
                "creation_runs": [round(value, 4) for value in creations],
                "refresh_runs": [round(value, 4) for value in refreshes],
                "render_runs": [round(value, 3) for value in renders],
            }
            report["renders"].append(entry)
            print("BENCH c=%.2f l=%d polys=%d create=%.3fs "
                  "refresh=%.3fs render=%.2fs (median of %d)"
                  % (coverage, layers, polygons, entry["creation_s"],
                     entry["refresh_s"], entry["render_s"], REPEATS))
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
