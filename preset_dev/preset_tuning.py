"""Targeted preset identity experiments.

Renders:
  after / sakura: baseline, sun -15%, world -10%
  twilight: horizon_softness 0.32 vs 0.26 (sky/horizon)
  seeds: Golden 17, Neon 17->43, Twilight 17->71, Stormy 17->97
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "preset_identity", "tuning")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def remove_sun(scene):
    for obj in list(scene.objects):
        if obj.type == "LIGHT" and obj.data and obj.data.type == "SUN":
            bpy.data.objects.remove(obj, do_unlink=True)


def gradient_node(scene):
    return palette._gradient_node(scene.world.node_tree)


def sun_obj(scene):
    return next((o for o in scene.objects if o.type == "LIGHT"
                 and o.data and o.data.type == "SUN"), None)


def aim(camera, azimuth, elevation):
    az, el = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.cos(el) * math.sin(az),
                        math.cos(el) * math.cos(az),
                        math.sin(el))).normalized()
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_sky_camera(scene, lens=16.0, location=(0.0, -10.0, 2.0),
                    elevation=45.0):
    data = bpy.data.cameras.new("Preset Identity Sky Camera")
    data.lens = lens
    camera = bpy.data.objects.new("Preset Identity Sky Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    aim(camera, 120.0, elevation)
    scene.camera = camera
    return camera


def hide_meshes(scene, hidden):
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.hide_render = hidden


def setting(scene, key):
    scene.ald.palette = key
    bpy.ops.ald.apply_palette()


def render(scene, out, name):
    path = os.path.join(out, name + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def main():
    out = parse_args()
    os.makedirs(out, exist_ok=True)
    lookdev.build_scene()
    lookdev.enable_addon()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    remove_sun(scene)
    lookdev_camera = scene.camera
    sky_camera = None
    cases = []

    # After School and Sakura: baseline, sun energy -15%, world strength -10%.
    for key in ("AFTER_SCHOOL", "SAKURA_SPRING"):
        setting(scene, key)
        base_sun = float(sun_obj(scene).data.energy)
        base_world = float(palette.PRESETS[key]["world_strength"])
        node = gradient_node(scene)
        for label, mode in (("baseline", None), ("sun_minus_15", "sun"),
                            ("world_minus_10", "world")):
            setting(scene, key)
            if mode == "sun":
                sun_obj(scene).data.energy = base_sun * 0.85
            elif mode == "world":
                node.inputs["World Strength"].default_value = base_world * 0.90
            path = render(scene, out, "%s_%s" % (key.lower(), label))
            cases.append({"group": key, "label": label, "path": path})

    # Twilight horizon softness.
    hide_meshes(scene, True)
    if sky_camera is None:
        sky_camera = make_sky_camera(scene, lens=24.0,
                                     location=(0.0, -20.0, 5.0),
                                     elevation=5.0)
    for softness in (0.32, 0.26):
        setting(scene, "TWILIGHT_DUSK")
        scene.ald.clouds = False
        scene.ald.stars = False
        scene.ald.contrails = 0.0
        scene.ald.sun_disk = False
        scene.ald.sun_glow_enabled = False
        node = gradient_node(scene)
        node.inputs["Cloud Amount"].default_value = 0.0
        node.inputs["Star Amount"].default_value = 0.0
        node.inputs["Contrails"].default_value = 0.0
        node.inputs["Sun Strength"].default_value = 0.0
        node.inputs["Sun Glow"].default_value = 0.0
        node.inputs["Softness"].default_value = softness
        path = render(scene, out, "twilight_soft_%s" % str(softness).replace(".", "_"))
        cases.append({"group": "TWILIGHT_DUSK", "label": "softness_%s" % softness,
                      "path": path})
    hide_meshes(scene, False)
    scene.camera = lookdev_camera

    # Cloud seed variants on the full lookdev scene.
    seeds = (("GOLDEN_HOUR", 17, 17), ("NEON_NIGHT", 17, 43),
             ("TWILIGHT_DUSK", 17, 71), ("STORMY_SUNSET", 17, 97))
    for key, before, after in seeds:
        setting(scene, key)
        for label, seed in (("before", before), ("after", after)):
            scene.ald.cloud_seed = seed
            node = gradient_node(scene)
            wind = palette._cloud_offset(scene, scene.ald)
            node.inputs["Cloud Offset"].default_value = (
                wind[0] + seed * 0.017, wind[1] + seed * 0.011, 0.0)
            path = render(scene, out, "%s_seed_%s_%s" % (key.lower(), label, seed))
            cases.append({"group": key, "label": "seed_%s_%s" % (label, seed),
                          "path": path})

    with open(os.path.join(out, "cases.json"), "w", encoding="utf-8") as handle:
        json.dump(cases, handle, indent=2)
    print("PRESET TUNING", len(cases), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
