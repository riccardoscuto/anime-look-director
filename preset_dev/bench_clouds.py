"""Cloud benchmark: creation, colour, position, shape, render and memory.

Coverage 0.16 / 0.5 / 0.9 / 1.0 with 1 / 3 / 5 layers, five runs per scenario.
The first run is warm-up; the table records the median and every run. The
memory is the Python peak from tracemalloc, not the GPU memory.

Run::

    blender -b --factory-startup --python preset_dev/bench_clouds.py
"""

import json
import os
import platform
import sys
import time
import tracemalloc

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "clouds_bench")
REPEATS = 5
COLOR_ALT = "NEON_NIGHT"


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def shape_coverage(coverage):
    """A coverage far enough from the scenario to force a real rebuild."""
    return 0.2 if coverage >= 0.5 else 0.8


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
        "memory_kind": "python_peak (tracemalloc), not GPU",
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
            colors = []
            positions = []
            shapes = []
            renders = []
            polygons = 0
            path = os.path.join(OUT, "c%.2f_l%d.png" % (coverage, layers))
            previous_key = scene.get("ald_effective_palette", "AFTER_SCHOOL")
            for _ in range(REPEATS):
                scene.ald.clouds_depth = 180.0
                clouds.remove(scene)
                start = time.perf_counter()
                clouds.create(scene)
                creations.append(time.perf_counter() - start)

                scene["ald_effective_palette"] = COLOR_ALT
                start = time.perf_counter()
                clouds.sync(scene)
                colors.append(time.perf_counter() - start)
                scene["ald_effective_palette"] = previous_key
                clouds.sync(scene)

                # The property update itself performs the refresh; time the
                # update, not a no-op refresh after it.
                start = time.perf_counter()
                scene.ald.clouds_depth = 220.0
                positions.append(time.perf_counter() - start)
                scene.ald.clouds_depth = 180.0

                alternate = shape_coverage(coverage)
                start = time.perf_counter()
                scene.ald.clouds_coverage = alternate
                shapes.append(time.perf_counter() - start)
                scene.ald.clouds_coverage = coverage

                collection = clouds._collection(scene)
                polygons = sum(len(obj.data.polygons)
                               for obj in collection.objects)
                start = time.perf_counter()
                baseline_fx.render(scene, path)
                renders.append(time.perf_counter() - start)

            # The memory probe is separate: tracemalloc slows the creation 5-8x
            # and would corrupt the timing table.
            tracemalloc.start()
            clouds.remove(scene)
            clouds.create(scene)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            entry = {
                "coverage": coverage,
                "layers": layers,
                "polygons": polygons,
                "creation_s": round(median(creations), 4),
                "color_s": round(median(colors), 5),
                "position_s": round(median(positions), 5),
                "shape_s": round(median(shapes), 4),
                "render_s": round(median(renders), 3),
                "memory_mb": round(peak / (1024.0 * 1024.0), 2),
                "creation_runs": [round(value, 4) for value in creations],
                "color_runs": [round(value, 5) for value in colors],
                "position_runs": [round(value, 5) for value in positions],
                "shape_runs": [round(value, 4) for value in shapes],
                "render_runs": [round(value, 3) for value in renders],
            }
            report["renders"].append(entry)
            print("BENCH c=%.2f l=%d polys=%d create=%.3fs color=%.4fs "
                  "position=%.4fs shape=%.3fs render=%.2fs mem=%.1fMB "
                  "(median of %d)"
                  % (coverage, layers, polygons, entry["creation_s"],
                     entry["color_s"], entry["position_s"], entry["shape_s"],
                     entry["render_s"], entry["memory_mb"], REPEATS))
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
