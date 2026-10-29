"""Phase 2 atmosphere / horizon / Sun audit.

Four cloudless conditions, a second framing, a Sun-horizon sweep and the UI
elevation check. Same camera, exposure and color management for equivalent
images. No code changes in this script.

    blender -b --factory-startup --gpu-backend vulkan --python \
        preset_dev/phase2_audit.py -- --out <dir> --tag current
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import palette  # noqa: E402

W, H = 1280, 720
CONDITIONS = (
    ("noon", "SUMMER_NOON", 35.0, 25.0, 25.0, 25.0, False),
    ("golden", "AFTER_SCHOOL", 4.0, 25.0, 25.0, 4.0, False),
    ("twilight", "TWILIGHT_DUSK", -2.0, 25.0, 25.0, -1.0, False),
    ("night", "NEON_NIGHT", -18.0, 25.0, 120.0, 25.0, True),
)
SWEEP = (8.0, 4.0, 2.0, 0.0, -1.0, -2.0, -4.0, -8.0)
OFFSETS = (-0.5, 0.0, 0.5)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "phase2_audit"), "tag": "current"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def look_direction(azimuth, elevation):
    a = math.radians(azimuth)
    e = math.radians(elevation)
    return Vector((math.cos(e) * math.sin(a),
                   math.cos(e) * math.cos(a),
                   math.sin(e))).normalized()


def aim(camera, azimuth, elevation):
    direction = look_direction(azimuth, elevation)
    camera.rotation_euler = (
        camera.location + direction * 100.0
        - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def aim_sun(scene, camera):
    direction = palette.sun_toward(scene)
    if direction is None:
        return
    camera.rotation_euler = (
        camera.location + Vector(direction) * 100.0
        - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def sun_metrics(scene, camera, path):
    rgb = read_rgb(path)
    luminance = rgb.max(axis=2)
    y, x = np.unravel_index(np.argmax(luminance), luminance.shape)
    direction = palette.sun_toward(scene)
    expected = None
    distance = None
    if direction is not None:
        point = camera.location + Vector(direction) * 100.0
        coord = world_to_camera_view(scene, camera, point)
        expected = [round(coord.x * W, 1), round(coord.y * H, 1)]
        distance = round(math.hypot(coord.x * W - x,
                                    coord.y * H - y), 1)
    return {
        "mean": round(float(rgb.mean()), 5),
        "max": round(float(luminance.max()), 4),
        "brightest_px": [int(x), int(y)],
        "expected_px": expected,
        "distance_px": distance,
    }


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    tag = args["tag"]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    data = bpy.data.cameras.new("Phase 2 Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 2 Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    scene.camera = camera
    report = {"tag": tag, "conditions": {}, "sweep": [], "offsets": {},
              "ui": {}}

    def render(name, frame=1):
        scene.frame_set(frame)
        path = os.path.join(out, "%s_%s.png" % (tag, name))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        return path

    for name, key, elevation, azimuth, aim_az, aim_el, stars in CONDITIONS:
        scene.ald.palette = key
        scene.ald.clouds = False
        scene.ald.stars = stars
        palette.apply_palette(scene, key)
        scene.ald.clouds = False
        scene.ald.stars = stars
        palette.apply_palette(scene, key)
        palette.apply_sun_angles(scene, elevation, azimuth)
        if name == "night":
            aim(camera, aim_az, aim_el)
        else:
            aim_sun(scene, camera)
        path = render(name)
        report["conditions"][name] = {
            "palette": key, "sun_elevation": elevation,
            "sun_azimuth": azimuth, "stars": stars,
            **sun_metrics(scene, camera, path)}
        camera.data.lens = 50.0
        if name == "night":
            aim(camera, aim_az, aim_el)
        else:
            aim_sun(scene, camera)
        path = render(name + "_second")
        report["conditions"][name]["second"] = sun_metrics(
            scene, camera, path)
        camera.data.lens = 32.0

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds = False
    scene.ald.stars = False
    palette.apply_palette(scene, "AFTER_SCHOOL")
    for elevation in SWEEP:
        palette.apply_sun_angles(scene, elevation, 25.0)
        aim_sun(scene, camera)
        path = render("sweep_%+04.1f" % elevation)
        report["sweep"].append({
            "elevation": elevation, **sun_metrics(scene, camera, path)})

    for offset in OFFSETS:
        scene.ald.horizon_offset = offset
        palette.apply_palette(scene, "AFTER_SCHOOL")
        palette.apply_sun_angles(scene, 4.0, 25.0)
        aim_sun(scene, camera)
        path = render("offset_%+.1f" % offset)
        report["offsets"][str(offset)] = sun_metrics(scene, camera, path)

    # UI path: the property must accept the night elevation.
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.sun_elevation = -18.0
    bpy.context.view_layer.update()
    direction = palette.sun_toward(scene)
    elevation, azimuth = palette.angles_from_direction(direction) \
        if direction is not None else (None, None)
    node = palette._gradient_node(scene.world.node_tree)
    world = node.inputs["Sun Direction"].default_value         if node is not None else None
    world_elevation = palette.angles_from_direction(world)[0]         if world is not None else None
    ui = {
        "requested": -18.0,
        "property": round(float(scene.ald.sun_elevation), 2),
        "actual_elevation": round(float(elevation), 2)
        if elevation is not None else None,
        "actual_azimuth": round(float(azimuth), 2)
        if azimuth is not None else None,
        "world_elevation": round(float(world_elevation), 2)
        if world_elevation is not None else None,
    }
    scene.ald.sun_elevation = 10.0
    bpy.context.view_layer.update()
    sync_direction = palette.sun_toward(scene)
    sync_actual = palette.angles_from_direction(sync_direction)[0] \
        if sync_direction is not None else None
    sync_node = palette._gradient_node(scene.world.node_tree)
    sync_world = sync_node.inputs["Sun Direction"].default_value \
        if sync_node is not None else None
    sync_world = palette.angles_from_direction(sync_world)[0] \
        if sync_world is not None else None
    ui["sync_requested"] = 10.0
    ui["sync_actual"] = round(float(sync_actual), 2) \
        if sync_actual is not None else None
    ui["sync_world"] = round(float(sync_world), 2) \
        if sync_world is not None else None
    report["ui"] = ui

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds = False
    scene.ald.stars = False
    palette.apply_palette(scene, "AFTER_SCHOOL")
    scene.ald.clouds = False
    palette.apply_sun_angles(scene, 4.0, 25.0)
    aim(camera, 25.0, 4.0)
    report["softness"] = {}
    for softness in (0.15, 0.5, 0.9):
        scene.ald.horizon_softness = softness
        path = render("softness_%02d" % int(softness * 100))
        rgb = read_rgb(path)
        report["softness"][str(softness)] = {
            "mean": round(float(rgb.mean()), 5),
            "max": round(float(rgb.max()), 4)}
    scene.ald.palette = "TWILIGHT_DUSK"
    palette.apply_palette(scene, "TWILIGHT_DUSK")
    scene.ald.clouds = False
    palette.apply_sun_angles(scene, -2.0, 25.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    bpy.context.view_layer.update()
    report["accent"] = {}
    for amount in (0.0, 0.3, 0.6):
        scene.ald.sky_accent_amount = amount
        path = render("accent_%02d" % int(amount * 100))
        rgb = read_rgb(path)
        report["accent"][str(amount)] = {
            "mean": round(float(rgb.mean()), 5),
            "max": round(float(rgb.max()), 4)}
    with open(os.path.join(out, "%s_audit.json" % tag), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("PHASE2 AUDIT", tag, json.dumps(report["ui"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
