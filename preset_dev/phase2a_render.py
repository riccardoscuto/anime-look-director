"""Phase 2A renderer for the Cumulus morphology A/B.

Renders one candidate/view/amount/seed at 1280x720 with identical camera,
palette, Sun, exposure and samples. Candidate A is loaded from a temporary
package at b688ae5; candidate B is the working tree.

Run::

    blender -b --factory-startup --python preset_dev/phase2a_render.py -- \
        --out preset_dev/phase2a --candidate A --module ald_a \
        --module-path <temp-parent> --amount 0.78 --seed 17 --view main
"""

import json
import os
import sys
import time

import bpy

VIEWS = {
    "main": ((0.0, -12.0, 3.0), (1.75, 0.0, 0.45)),
    "alt": ((0.0, -12.0, 3.0), (1.62, 0.0, -0.35)),
}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/phase2a", "candidate": "B",
              "module": "anime_look_director", "module_path": "",
              "amount": "0.78", "seed": "17", "view": "main",
              "clouds": "on", "palette": "SUMMER_NOON",
              "family": "CUMULUS"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["amount"] = float(values["amount"])
    values["seed"] = int(values["seed"])
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
    data = bpy.data.cameras.new("Phase 2A Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2A Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    scene.camera = camera
    return scene


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene = build_scene(args["view"])
    enable(args["module"], args["module_path"])
    import importlib
    driver = importlib.import_module(args["module"])
    palette = importlib.import_module(args["module"] + ".palette")

    scene.ald.palette = args["palette"]
    palette.apply_palette(scene, args["palette"])
    clouds = args["clouds"] == "on"
    scene.ald.clouds = clouds
    scene.ald.cloud_type = args["family"]
    scene.ald.cloud_amount = args["amount"]
    scene.ald.cloud_seed = args["seed"]
    start = time.perf_counter()
    palette.apply_palette(scene, args["palette"])
    apply_ms = (time.perf_counter() - start) * 1000.0
    scene.render.use_compositing = False
    bpy.context.view_layer.update()

    suffix = ("off" if not clouds else
              "a%03d_s%02d" % (round(args["amount"] * 100), args["seed"]))
    family_tag = ("" if args["family"] == "CUMULUS"
                  else "_" + args["family"].lower())
    name = "%s_%s%s_%s_1280x720.png" % (
        args["candidate"], args["view"], family_tag, suffix)
    path = os.path.join(out, name)
    scene.render.filepath = path
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    render_ms = (time.perf_counter() - start) * 1000.0

    group = palette._gradient_node(scene.world.node_tree)
    metadata = {
        "candidate": args["candidate"],
        "module": args["module"],
        "module_version": tuple(driver.bl_info.get("version", ())),
        "view": args["view"],
        "camera": {"location": list(VIEWS[args["view"]][0]),
                   "rotation": list(VIEWS[args["view"]][1]),
                   "lens": 32.0},
        "palette": args["palette"],
        "clouds": clouds,
        "cloud_type": args["family"],
        "cloud_amount": args["amount"],
        "cloud_seed": args["seed"],
        "apply_ms": round(apply_ms, 2),
        "render_ms": round(render_ms, 1),
        "world_nodes": len(scene.world.node_tree.nodes),
        "group_nodes": len(group.node_tree.nodes) if group else 0,
        "file": name,
    }
    with open(os.path.join(out, "meta_%s_%s%s_%s.json" % (
            args["candidate"], args["view"], family_tag, suffix)), "w",
              encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("PHASE2A", args["candidate"], args["view"], suffix,
          "apply %.1fms render %.0fms nodes %d"
          % (apply_ms, render_ms, metadata["group_nodes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
