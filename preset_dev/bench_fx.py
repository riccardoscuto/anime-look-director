"""P3 benchmarks for the FX pipeline.

Measures five distinct costs, because they fail for different reasons:
creation, parameter update (recompile), clock refresh, frame evaluation and
render. Memory is reported as the real object/vertex/attribute counts of the
scene plus the Python peak of the creation.

The budgets are declared together with the scenario and the hardware in the
JSON, so a result is never compared against an unmeasured claim.

Run (from the add-on directory)::

    blender -b --factory-startup --python-exit-code 1 --python preset_dev/bench_fx.py
"""

import json
import os
import platform
import sys
import time
import tracemalloc

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.basename(HERE)
OUT = os.path.join(HERE, "preset_dev", "benchmarks.json")

#: Soft budgets for this machine and scenario (seconds unless stated).
BUDGETS = {
    "creation_fireworks_5_s": 1.0,
    "creation_meteors_5_s": 1.0,
    "update_system_s": 0.5,
    "clock_refresh_s": 0.05,
    "frame_eval_gn_24_frames_s": 0.5,
    "frame_eval_python_24_frames_s": 4.0,
    "render_128x72_s": 15.0,
}


def enable_addon():
    import addon_utils
    addon_utils.enable(PACKAGE)


def clean_scene(scene):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def setup(scene):
    clean_scene(scene)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 8
    scene.render.resolution_x = 128
    scene.render.resolution_y = 72
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"

    cam_data = bpy.data.cameras.new("Bench Camera")
    cam_data.lens = 35.0
    camera = bpy.data.objects.new("Bench Camera", cam_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((0.0, -9.0, 3.0))
    camera.rotation_euler = (Vector((0.0, 8.0, 6.0)) - camera.location
                             ).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    bpy.ops.mesh.primitive_plane_add(size=300.0)
    scene.ald.fx_backend = "FX3D"
    scene.ald.fx_gn_prototype = True


def count_memory(scene):
    objects = [obj for obj in bpy.data.objects if obj.get("ald_fx")]
    vertices = 0
    attributes = 0
    for obj in objects:
        if obj.type == "MESH" and obj.data is not None:
            vertices += len(obj.data.vertices)
            attributes += len(obj.data.attributes)
    return {"objects": len(objects), "vertices": vertices,
            "attributes": attributes}


def main():
    enable_addon()
    from anime_look_director import fx

    scene = bpy.context.scene
    setup(scene)
    data = {
        "scenario": {
            "resolution": [128, 72],
            "engine": "BLENDER_EEVEE",
            "samples": 8,
            "seed": 13,
            "firework_count": 5,
            "meteor_count": 5,
            "frame_samples": 24,
            "view_transform": "AgX",
        },
        "hardware": {
            "blender": bpy.app.version_string,
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "budgets": BUDGETS,
        "timings": {},
        "memory": {},
        "checks": {},
    }

    def timed(name, function):
        start = time.perf_counter()
        result = function()
        data["timings"][name] = round(time.perf_counter() - start, 5)
        return result

    # Creation.
    fx.clear(scene)
    timed("creation_fireworks_5_s",
          lambda: fx.create_fireworks(scene, 5, seed=13, distance=60.0))
    created_memory = count_memory(scene)
    fx.clear(scene)
    timed("creation_meteors_5_s",
          lambda: fx.create_meteors(scene, 5, seed=21, distance=80.0))

    # Parameter update (recompile) and clock refresh (no rebuild).
    system = scene.ald.fx_systems[0]
    timed("update_system_s", lambda: fx.update_system(scene, system))
    timed("clock_refresh_s", lambda: fx.set_age(scene, 1.2))

    # Frame evaluation on the Python writer (the geometry is authored).
    fx.clear(scene)
    scene.ald.fx_gn_prototype = False
    fx.create_fireworks(scene, 3, seed=5, distance=40.0)
    system = scene.ald.fx_systems[0]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)

    def evaluate_frames():
        base = int(system.origin_frame)
        for step in range(24):
            scene.frame_set(base + int((1.2 + step / fps) * fps))

    timed("frame_eval_python_24_frames_s", evaluate_frames)

    # The production backend: the node group evaluates the same data.
    fx.clear(scene)
    scene.ald.fx_gn_prototype = True
    fx.create_fireworks(scene, 3, seed=5, distance=40.0)
    system = scene.ald.fx_systems[0]

    def evaluate_gn_frames():
        base = int(system.origin_frame)
        for step in range(24):
            scene.frame_set(base + int((1.2 + step / fps) * fps))

    timed("frame_eval_gn_24_frames_s", evaluate_gn_frames)

    # Memory of a full system, plus the Python peak of one creation.
    fx.clear(scene)
    scene.ald.fx_gn_prototype = True
    tracemalloc.start()
    fx.create_fireworks(scene, 5, seed=13, distance=60.0)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    data["memory"] = count_memory(scene)
    data["memory"]["python_peak_bytes"] = int(peak)
    data["memory"]["creation_fireworks_5"] = created_memory

    # Render once at the benchmark resolution.
    bpy.ops.ald.build()
    scene.render.filepath = os.path.join(
        os.path.dirname(OUT), "bench_render.png")
    timed("render_128x72_s", lambda: bpy.ops.render.render(write_still=True))

    for name, budget in BUDGETS.items():
        value = data["timings"].get(name)
        data["checks"][name] = {
            "value": value,
            "budget": budget,
            "pass": bool(value is not None and value <= budget),
        }

    with open(OUT, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("ALD BENCHMARKS:", OUT)
    for name in sorted(data["timings"]):
        print("  %-28s %.5f s" % (name, data["timings"][name]))
    print("  objects=%d vertices=%d attributes=%d python_peak=%.1f MB"
          % (data["memory"]["objects"], data["memory"]["vertices"],
             data["memory"]["attributes"],
             data["memory"]["python_peak_bytes"] / (1024 * 1024)))
    failed = [name for name, item in data["checks"].items() if not item["pass"]]
    if failed:
        print("BUDGET FAILED:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
