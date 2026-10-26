"""P2-B: comparable FX calibration renders.

Two atmospheres (night and sunset) times three glow settings (none, narrow
halo, wide halo) with a fixed camera, resolution, seed, exposure 0 and AgX.
The Standard view transform is rendered once as a diagnostic control: it does
not certify an AgX look. The Glare size is a fraction of the image (Blender
treats it as relative), so the same value means the same physical size at any
resolution.

Run (from the add-on directory)::

    blender -b --factory-startup --python-exit-code 1 --python preset_dev/calibrate_fx.py

Writes the PNGs and ``metrics.json`` under ``preset_dev/calibration/``.
"""

import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.basename(HERE)
OUT = os.path.join(HERE, "preset_dev", "calibration")

PALETTES = (("night", "TWILIGHT_DUSK"), ("sunset", "GOLDEN_HOUR"))
GLOWS = (("none", 0.0, 0.0), ("narrow", 0.45, 0.22),
         ("wide", 1.0, 0.72))


def enable_addon():
    import addon_utils
    addon_utils.enable(PACKAGE)


def clean_scene(scene):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def setup_scene(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 384
    scene.render.resolution_y = 216
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0

    cam_data = bpy.data.cameras.new("Calibration Camera")
    cam_data.lens = 35.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    camera = bpy.data.objects.new("Calibration Camera", cam_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((0.0, -9.0, 3.2))
    target = Vector((0.0, 8.0, 6.0))
    camera.rotation_euler = (target - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    scene.camera = camera

    # Ground: a neutral dark plane, it receives the palette light.
    bpy.ops.mesh.primitive_plane_add(size=400.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "Calibration Ground"
    material = bpy.data.materials.new("Calibration Ground")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.06, 0.06, 0.07, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    ground.data.materials.append(material)
    return camera


def metrics(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = list(image.pixels)
    lum_sum = 0.0
    lum_max = 0.0
    sat_sum = 0.0
    clipped = 0
    count = 0
    for index in range(0, len(pixels), 4):
        red, green, blue = pixels[index], pixels[index + 1], pixels[index + 2]
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        lum_sum += luminance
        lum_max = max(lum_max, luminance)
        sat_sum += max(red, green, blue) - min(red, green, blue)
        if luminance >= 0.99:
            clipped += 1
        count += 1
    bpy.data.images.remove(image)
    return {
        "size": [width, height],
        "mean_luminance": round(lum_sum / max(count, 1), 5),
        "max_luminance": round(lum_max, 5),
        "mean_saturation": round(sat_sum / max(count, 1), 5),
        "clipped_fraction": round(clipped / max(count, 1), 5),
    }


def main():
    enable_addon()
    from anime_look_director import fx, look, palette

    os.makedirs(OUT, exist_ok=True)
    scene = bpy.context.scene
    clean_scene(scene)
    setup_scene(scene)
    data = {"resolution": [384, 216], "engine": "BLENDER_EEVEE",
            "view_transform": "AgX", "exposure": 0.0, "seed": 13,
            "renders": []}

    scene.ald.fx_backend = "FX3D"
    scene.ald.fx_gn_prototype = True
    scene.ald.fx_age = 1.6

    for label, key in PALETTES:
        scene.ald.palette = key
        look.apply(scene, force=True)
        for glow_name, strength, size in GLOWS:
            scene.ald.fx_glow_strength = strength
            scene.ald.fx_glow_size = size
            scene.ald.fx_glow_threshold = 0.35
            scene.ald.fx_age = 0.0
            fx.clear(scene)
            fx.create_fireworks(scene, 1, seed=13, distance=28.0,
                                family="CHRYSANTHEMUM")
            bpy.ops.ald.build()
            # The burst is 0.4 s old at the fixed frame.
            system = scene.ald.fx_systems[0]
            event = system.events[0]
            fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
            scene.frame_set(int(system.origin_frame
                                + (event.birth + event.rise_time + 0.4) * fps))
            bpy.context.view_layer.update()
            name = "%s_%s.png" % (label, glow_name)
            path = os.path.join(OUT, name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            entry = {"palette": label, "palette_key": key,
                     "glow": glow_name, "glow_strength": strength,
                     "glow_size": size, "file": name}
            entry.update(metrics(path))
            data["renders"].append(entry)
            print("CALIBRATION:", name, entry["mean_luminance"],
                  entry["max_luminance"], entry["clipped_fraction"])

    # Diagnostic control: Standard is not an AgX certificate.
    scene.view_settings.view_transform = "Standard"
    scene.ald.palette = "GOLDEN_HOUR"
    look.apply(scene, force=True)
    scene.ald.fx_glow_strength = 0.45
    scene.ald.fx_glow_size = 0.22
    scene.ald.fx_age = 0.0
    fx.clear(scene)
    fx.create_fireworks(scene, 1, seed=13, distance=28.0,
                        family="CHRYSANTHEMUM")
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * fps))
    bpy.context.view_layer.update()
    path = os.path.join(OUT, "sunset_narrow_standard.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    entry = {"palette": "sunset", "palette_key": "GOLDEN_HOUR",
             "glow": "narrow", "glow_strength": 0.45, "glow_size": 0.22,
             "file": "sunset_narrow_standard.png",
             "note": "diagnostic control, not an AgX certificate"}
    entry.update(metrics(path))
    data["renders"].append(entry)

    target = os.path.join(OUT, "metrics.json")
    with open(target, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("ALD CALIBRATION:", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
