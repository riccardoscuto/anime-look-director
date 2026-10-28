"""Phase 2E renderer for A and P.

Renders a Cloud Amount curve at one seed or a seed set at one amount, with a
fixed camera view. One process builds the World group once.
"""

import json
import os
import sys
import time

import bpy

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
              "view": "main", "amounts": "", "seeds": "17",
              "clouds": "on", "family": "CUMULUS"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["amounts"] = [float(x) for x in values["amounts"].split(",")
                         if x]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
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
    data = bpy.data.cameras.new("Phase 2E Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2E Camera", data)
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
    scene.ald.palette = "SUMMER_NOON"
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.ald.cloud_type = args["family"]
    clouds = args["clouds"] == "on"
    if not clouds:
        scene.ald.clouds = False
        palette.apply_palette(scene, "SUMMER_NOON")
        scene.render.filepath = os.path.join(
            out, "%s_%s_off_1280x720.png" % (args["candidate"], args["view"]))
        bpy.ops.render.render(write_still=True)
        print("PHASE2E OFF", args["candidate"], args["view"])
        return 0

    amounts = args["amounts"] or [0.78]
    seeds = args["seeds"]
    records = []
    for amount in amounts:
        for seed in seeds:
            scene.ald.clouds = True
            scene.ald.cloud_amount = amount
            scene.ald.cloud_seed = seed
            start = time.perf_counter()
            palette.apply_palette(scene, "SUMMER_NOON")
            apply_ms = (time.perf_counter() - start) * 1000.0
            bpy.context.view_layer.update()
            name = "%s_%s_a%03d_s%02d_1280x720.png" % (
                args["candidate"], args["view"], round(amount * 100), seed)
            scene.render.filepath = os.path.join(out, name)
            start = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            render_ms = (time.perf_counter() - start) * 1000.0
            records.append({"amount": amount, "seed": seed, "file": name,
                            "apply_ms": round(apply_ms, 2),
                            "render_ms": round(render_ms, 1)})
            print("PHASE2E", args["candidate"], args["view"], amount, seed,
                  "render %.0fms" % render_ms)
    group = palette._gradient_node(scene.world.node_tree)
    report = {"candidate": args["candidate"], "view": args["view"],
              "module": args["module"],
              "module_version": tuple(driver.bl_info.get("version", ())),
              "group_nodes": len(group.node_tree.nodes) if group else 0,
              "world_nodes": len(scene.world.node_tree.nodes),
              "family": args["family"], "renders": records}
    with open(os.path.join(out, "meta_%s_%s.json" % (
            args["candidate"], args["view"])), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
