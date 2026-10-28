"""Render the A (v2.62) reference clouds with the prototype cameras.

Used only by the 2D cloud-distribution comparison: same seeds, views and
resolution as the prototype renders, Cloud Amount 0.78, no compositor.
"""

import json
import os
import sys
import time

import bpy

VIEWS = {
    "main": ((0.0, -12.0, 3.0), (1.75, 0.0, 0.45)),
    "right": ((0.0, -12.0, 3.0), (1.80, 0.0, 0.95)),
}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/cloud_distribution", "seeds": "3,17,42",
              "views": "main,right", "amount": "0.78"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
    values["views"] = [x for x in values["views"].split(",") if x]
    values["amount"] = float(values["amount"])
    return values


def scene(view):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import palette
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.eevee.taa_render_samples = 32
    s.render.resolution_x = 1280
    s.render.resolution_y = 720
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.film_transparent = False
    s.render.use_compositing = False
    s.render.fps = 24
    s.view_settings.view_transform = "AgX"
    s.view_settings.exposure = 0.0
    s.frame_set(1)
    location, rotation = VIEWS[view]
    data = bpy.data.cameras.new("Reference Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Reference Camera", data)
    s.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    s.camera = camera
    s.ald.palette = "SUMMER_NOON"
    palette.apply_palette(s, "SUMMER_NOON")
    s.ald.cloud_type = "CUMULUS"
    return s, palette


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    s, palette = scene(args["views"][0])
    report = {"amount": args["amount"], "renders": []}
    for view in args["views"]:
        location, rotation = VIEWS[view]
        camera = s.camera
        camera.location = location
        camera.rotation_euler = rotation
        s.ald.clouds = False
        palette.apply_palette(s, "SUMMER_NOON")
        name = "A_%s_off_1280x720.png" % view
        s.render.filepath = os.path.join(out, name)
        bpy.ops.render.render(write_still=True)
        s.ald.clouds = True
        for seed in args["seeds"]:
            s.ald.cloud_seed = seed
            s.ald.cloud_amount = args["amount"]
            palette.apply_palette(s, "SUMMER_NOON")
            bpy.context.view_layer.update()
            name = "A_%s_a%03d_s%02d_1280x720.png" % (
                view, round(args["amount"] * 100), seed)
            s.render.filepath = os.path.join(out, name)
            start = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            elapsed = (time.perf_counter() - start) * 1000.0
            report["renders"].append({"seed": seed, "view": view,
                                      "amount": args["amount"],
                                      "file": name,
                                      "render_ms": round(elapsed, 1)})
            print("REF", seed, view, "render %.0fms" % elapsed)
    with open(os.path.join(out, "reference_A.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
