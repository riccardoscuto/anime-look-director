"""Phase 2E diagnostic per-case coverage match.

For each seed/view, adjust Cloud Amount until coverage is near 0.42 using
local slope estimates (up to three adjustments). Diagnostic only; normal
Cloud Amount behavior is untouched.
"""

import json
import os
import sys
import time

import bpy
import numpy as np

VIEWS = {
    "main": ((0.0, -12.0, 3.0), (1.75, 0.0, 0.45)),
    "left": ((0.0, -12.0, 3.0), (1.62, 0.0, -0.35)),
    "right": ((0.0, -12.0, 3.0), (1.80, 0.0, 0.95)),
}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/phase2e", "candidate": "P",
              "module": "anime_look_director", "module_path": "",
              "view": "main", "seeds": "17", "target": "0.42",
              "slope": "0.72", "base": "0.78", "iterations": "3"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
    values["target"] = float(values["target"])
    values["slope"] = float(values["slope"])
    values["base"] = float(values["base"])
    values["iterations"] = int(values["iterations"])
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


def build_scene(view):
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
    location, rotation = VIEWS[view]
    data = bpy.data.cameras.new("Phase 2E Match Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2E Match Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    scene.camera = camera
    return scene


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def coverage(path, off):
    diff = np.abs(read_rgb(path) - read_rgb(off)).max(axis=2)
    return float((diff > 0.02).mean())


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    view = args["view"]
    off = os.path.join(out, "A_%s_off_1280x720.png" % view)
    scene = build_scene(view)
    enable(args["module"], args["module_path"])
    import importlib
    palette = importlib.import_module(args["module"] + ".palette")
    scene.ald.palette = "SUMMER_NOON"
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.ald.cloud_type = "CUMULUS"
    scene.ald.clouds = True
    records = []
    for seed in args["seeds"]:
        scene.ald.cloud_seed = seed
        amount = args["base"]
        history = []
        final_path = None
        for step in range(args["iterations"] + 1):
            scene.ald.cloud_amount = amount
            palette.apply_palette(scene, "SUMMER_NOON")
            bpy.context.view_layer.update()
            name = "%s_%s_iter%d_a%03d_s%02d_1280x720.png" % (
                args["candidate"], view, step, round(amount * 100), seed)
            path = os.path.join(out, name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            cov = coverage(path, off)
            history.append({"step": step, "amount": round(amount, 4),
                            "coverage": round(cov, 4), "file": name})
            final_path = path
            if abs(cov - args["target"]) <= 0.015:
                break
            if len(history) >= 2:
                prev = history[-2]
                delta_amount = amount - prev["amount"]
                if abs(delta_amount) > 1e-4:
                    slope = (cov - prev["coverage"]) / delta_amount
                else:
                    slope = args["slope"]
            else:
                slope = args["slope"]
            slope = max(0.15, min(2.0, slope))
            amount = max(0.0, min(1.0, amount
                                   + (args["target"] - cov) / slope))
        final_name = "%s_%s_matched_a%03d_s%02d_1280x720.png" % (
            args["candidate"], view, round(amount * 100), seed)
        final_dest = os.path.join(out, final_name)
        if final_path != final_dest:
            os.replace(final_path, final_dest)
        final_cov = coverage(final_dest, off)
        records.append({"seed": seed, "amount": round(amount, 4),
                        "coverage": round(final_cov, 4),
                        "iterations": len(history),
                        "file": final_name,
                        "history": history})
        print("PHASE2E MATCH", args["candidate"], view, seed,
              "iters", len(history), "cov %.3f @ %.3f"
              % (final_cov, amount))
    with open(os.path.join(out, "meta_%s_%s_matched.json" % (
            args["candidate"], view)), "w", encoding="utf-8") as f:
        json.dump({"candidate": args["candidate"], "view": view,
                   "target": args["target"], "records": records},
                  f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
