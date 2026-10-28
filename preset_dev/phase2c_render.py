"""Phase 2C 20-seed renderer for candidates A and C.

Builds the same scene once, renders the clouds-off reference and seeds 0..19
at the calibrated amount, and records per-seed timing.
"""

import json
import os
import sys
import time

import bpy


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/phase2c", "candidate": "C",
              "module": "anime_look_director", "module_path": "",
              "amount": "0.78", "count": "20"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["amount"] = float(values["amount"])
    values["count"] = int(values["count"])
    return values


def enable(module, module_path):
    if hasattr(bpy.context.scene, "ald"):
        return
    if module_path and module_path not in sys.path:
        sys.path.insert(0, module_path)
    try:
        bpy.ops.preferences.addon_enable(module=module)
    except Exception:
        import importlib
        importlib.import_module(module).register()


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    data = bpy.data.cameras.new("Phase 2C Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2C Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    return scene


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene = build_scene()
    enable(args["module"], args["module_path"])
    import importlib
    driver = importlib.import_module(args["module"])
    palette = importlib.import_module(args["module"] + ".palette")
    scene.ald.palette = "SUMMER_NOON"
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.ald.clouds = False
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.render.filepath = os.path.join(
        out, "%s_off_1280x720.png" % args["candidate"])
    bpy.ops.render.render(write_still=True)

    scene.ald.clouds = True
    scene.ald.cloud_type = "CUMULUS"
    scene.ald.cloud_amount = args["amount"]
    report = {"candidate": args["candidate"], "module": args["module"],
              "module_version": tuple(driver.bl_info.get("version", ())),
              "amount": args["amount"], "seeds": []}
    for seed in range(args["count"]):
        scene.ald.cloud_seed = seed
        start = time.perf_counter()
        palette.apply_palette(scene, "SUMMER_NOON")
        apply_ms = (time.perf_counter() - start) * 1000.0
        scene.render.use_compositing = False
        bpy.context.view_layer.update()
        path = os.path.join(
            out, "%s_s%02d_1280x720.png" % (args["candidate"], seed))
        scene.render.filepath = path
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        render_ms = (time.perf_counter() - start) * 1000.0
        report["seeds"].append({"seed": seed, "file": os.path.basename(path),
                                "apply_ms": round(apply_ms, 2),
                                "render_ms": round(render_ms, 1)})
        print("PHASE2C", args["candidate"], seed,
              "render %.0fms" % render_ms)
    group = palette._gradient_node(scene.world.node_tree)
    report["group_nodes"] = len(group.node_tree.nodes) if group else 0
    report["world_nodes"] = len(scene.world.node_tree.nodes)
    with open(os.path.join(out, "meta_%s.json" % args["candidate"]), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
