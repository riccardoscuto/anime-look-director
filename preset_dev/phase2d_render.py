"""Phase 2D diagnostic renderer: A, P, R, PR.

One process per variant so the World group is built with the diagnostic
switch fixed. The variant only affects Cumulus; sky, Sun, palette, lighting
and compositor stay identical.
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
    values = {"out": "preset_dev/phase2d", "variant": "A",
              "amount": "0.78", "seed": "17", "view": "main",
              "clouds": "on"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["amount"] = float(values["amount"])
    values["seed"] = int(values["seed"])
    return values


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
    data = bpy.data.cameras.new("Phase 2D Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2D Camera", data)
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
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    import importlib
    palette = importlib.import_module("anime_look_director.palette")
    palette.CLOUD_DIAG = args["variant"]
    scene.ald.palette = "SUMMER_NOON"
    palette.apply_palette(scene, "SUMMER_NOON")
    clouds = args["clouds"] == "on"
    scene.ald.clouds = clouds
    scene.ald.cloud_type = "CUMULUS"
    scene.ald.cloud_amount = args["amount"]
    scene.ald.cloud_seed = args["seed"]
    start = time.perf_counter()
    palette.apply_palette(scene, "SUMMER_NOON")
    apply_ms = (time.perf_counter() - start) * 1000.0
    scene.render.use_compositing = False
    bpy.context.view_layer.update()
    suffix = "off" if not clouds else "a%03d_s%02d" % (
        round(args["amount"] * 100), args["seed"])
    name = "%s_%s_%s_1280x720.png" % (
        args["variant"], args["view"], suffix)
    path = os.path.join(out, name)
    scene.render.filepath = path
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    render_ms = (time.perf_counter() - start) * 1000.0
    group = palette._gradient_node(scene.world.node_tree)
    metadata = {
        "variant": args["variant"], "view": args["view"],
        "amount": args["amount"], "seed": args["seed"],
        "clouds": clouds,
        "apply_ms": round(apply_ms, 2),
        "render_ms": round(render_ms, 1),
        "group_nodes": len(group.node_tree.nodes) if group else 0,
        "file": name,
    }
    with open(os.path.join(out, "meta_%s_%s_%s.json" % (
            args["variant"], args["view"], suffix)), "w",
              encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("PHASE2D", args["variant"], args["view"], suffix,
          "render %.0fms nodes %d" % (render_ms, metadata["group_nodes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
