"""Version-agnostic Phase 1 Cumulus renderer.

Renders one SUMMER_NOON frame with the World clouds on or off, at a chosen
coverage, so the current and archived add-ons can be compared under identical
camera, Sun, palette, exposure and samples.

Run with the current add-on::

    blender -b --factory-startup --python preset_dev/phase1_render.py -- \
        --out preset_dev/baseline_2_63 --tag v2.62.0 --res 1280x720 \
        --clouds on --amount 0.70

For an archived add-on, pass ``--module v103 --module-path <parent>``.
"""

import json
import os
import sys

import bpy


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/baseline_2_63", "tag": "current",
              "res": "1280x720", "clouds": "on", "amount": "",
              "module": "anime_look_director", "module_path": "",
              "palette": "SUMMER_NOON"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    width, height = values["res"].lower().split("x")
    values["size"] = (int(width), int(height))
    values["amount"] = (float(values["amount"])
                        if values["amount"] not in ("", "native") else None)
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


def build_scene(width, height):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)

    camera_data = bpy.data.cameras.new("Phase 1 Camera")
    camera_data.lens = 32.0
    camera_data.clip_start = 0.1
    camera_data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 1 Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    return scene


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    tag = args["tag"]
    width, height = args["size"]
    clouds = args["clouds"] == "on"
    amount = args["amount"]
    palette_name = args["palette"]

    scene = build_scene(width, height)
    enable(args["module"], args["module_path"])
    import importlib
    driver = importlib.import_module(args["module"])
    palette = importlib.import_module(args["module"] + ".palette")

    scene.ald.palette = palette_name
    if hasattr(scene.ald, "clouds"):
        scene.ald.clouds = clouds
    palette.apply_palette(scene, palette_name)
    if hasattr(scene.ald, "clouds"):
        scene.ald.clouds = clouds
    if amount is not None and hasattr(scene.ald, "cloud_amount"):
        scene.ald.cloud_amount = amount
    palette.apply_palette(scene, palette_name)
    scene.render.use_compositing = False
    bpy.context.view_layer.update()

    suffix = "native" if amount is None else ("amount_%03d" % round(amount * 100))
    name = "%s_%s_%s_%s_%dx%d.png" % (
        palette_name.lower(), tag, args["clouds"], suffix, width, height)
    path = os.path.join(out, name)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

    metadata = {
        "tag": tag,
        "module": args["module"],
        "module_version": tuple(driver.bl_info.get("version", ())),
        "palette": palette_name,
        "clouds": clouds,
        "cloud_amount": (amount if amount is not None
                         else getattr(scene.ald, "cloud_amount", None)),
        "resolution": [width, height],
        "samples": 32,
        "camera": {"location": [0.0, -12.0, 3.0],
                   "rotation": [1.75, 0.0, 0.45], "lens": 32.0},
        "world": scene.world.name if scene.world else None,
        "file": name,
    }
    meta_path = os.path.join(out, "meta_%s_%s_%s_%dx%d.json" % (
        tag, args["clouds"], suffix, width, height))
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("PHASE1", tag, args["clouds"], suffix, name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
