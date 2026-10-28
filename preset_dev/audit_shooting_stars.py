"""Phase 0 audit of the shooting-star system.

Reads/uses the existing implementation only. Produces renders and a JSON with
the measured lifecycle, multiple-event, positioning, preview and persistence
results. No add-on code is modified.

    blender -b --factory-startup --python preset_dev/audit_shooting_stars.py
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import look, palette  # noqa: E402

RW, RH = 1280, 720
STAR_FRAMES = (8, 9, 10, 11, 12, 18, 32, 33, 34, 35, 36)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "audit_shooting_stars")}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = RW
    scene.render.resolution_y = RH
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 60
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    palette.apply_palette(scene, "NEON_NIGHT")
    data = bpy.data.cameras.new("Audit Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Audit Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (math.pi / 2.0, 0.0, 0.3)
    scene.camera = camera
    return scene, camera


def render(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def star_stats(on_path, off_path):
    on = read_rgb(on_path)
    off = read_rgb(off_path)
    diff = np.abs(on - off).max(axis=2)
    mask = diff > 0.02
    if not mask.any():
        return {"pixels": 0, "max": 0.0, "bbox": None, "centroid": None}
    ys, xs = np.nonzero(mask)
    return {
        "pixels": int(mask.sum()),
        "max": round(float(diff.max()), 3),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        "centroid": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
    }


def set_event(scene, index, **values):
    event = scene.ald.shooting_star_events[index]
    for key, value in values.items():
        setattr(event, key, value)
    look.apply_world(scene)
    return event


def disable_all(scene):
    for event in scene.ald.shooting_star_events:
        event.enabled = False
    look.apply_world(scene)


def enable_all(scene):
    for event in scene.ald.shooting_star_events:
        event.enabled = True
    look.apply_world(scene)


def aim(scene, camera, azimuth, elevation):
    a = math.radians(azimuth)
    e = math.radians(elevation)
    direction = Vector((math.cos(e) * math.sin(a),
                        math.cos(e) * math.cos(a),
                        math.sin(e)))
    target = camera.location + direction * 100.0
    camera.rotation_euler = (
        target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def direction_from_pixel(scene, camera, centroid):
    x = (2.0 * centroid[0] / RW - 1.0) * (18.0 / 32.0)
    y = (1.0 - 2.0 * centroid[1] / RH) * (10.125 / 32.0)
    local = Vector((x, y, -1.0)).normalized()
    world = camera.matrix_world.to_quaternion() @ local
    return [round(math.degrees(math.asin(max(-1.0, min(1.0, world.z)))), 2),
            round(math.degrees(math.atan2(world.x, world.y)), 2)]


def rotation_quat(camera):
    return [round(value, 5) for value in camera.rotation_euler]


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene, camera = fixture()
    report = {"renders": [], "events": [], "checks": {}}

    def capture(name, frame, off=False):
        scene.frame_set(frame)
        path = os.path.join(out, name + ".png")
        render(scene, path)
        return path

    # --- A. Add at a camera looking at the horizon -----------------------
    scene.frame_set(20)
    capture("add_before", 20)
    result = bpy.ops.ald.shooting_star_add()
    add_event = scene.ald.shooting_star_events[0]
    report["checks"]["add"] = {
        "result": list(result),
        "azimuth": round(float(add_event.azimuth), 2),
        "elevation": round(float(add_event.elevation), 2),
        "start_frame": int(add_event.start_frame),
        "duration": int(add_event.duration),
        "frame": 20,
    }
    add_after = capture("add_after", 20)
    report["checks"]["add"]["star"] = star_stats(
        add_after, os.path.join(out, "add_before.png"))

    # --- B. Lifecycle of a single visible event --------------------------
    set_event(scene, 0, azimuth=120.0, elevation=40.0, direction=-35.0,
              length=18.0, start_frame=10, duration=24, trail=0.55,
              thickness=0.0018, brightness=3.0, glow=0.8)
    scene.ald.shooting_star_selected = 0
    bpy.ops.ald.shooting_star_preview()
    report["checks"]["preview"] = {
        "frame": scene.frame_current,
        "rotation": rotation_quat(camera),
        "location": [round(v, 3) for v in camera.location],
    }
    disable_all(scene)
    scene.frame_set(18)
    off_path = os.path.join(out, "lifecycle_off.png")
    render(scene, off_path)
    enable_all(scene)
    lifecycle = {}
    for frame in STAR_FRAMES:
        path = capture("lifecycle_f%02d" % frame, frame)
        stats = star_stats(path, off_path)
        lifecycle[str(frame)] = stats
        report["renders"].append({"name": "lifecycle_f%02d" % frame,
                                  "frame": frame, **stats})
    report["checks"]["lifecycle"] = lifecycle
    # backward/manual playhead: same frame must render identically
    back = capture("lifecycle_back_33", 33)
    back_again = capture("lifecycle_manual_33", 33)
    first = read_rgb(os.path.join(out, "lifecycle_f33.png"))
    report["checks"]["playhead"] = {
        "identical_33": bool(np.array_equal(
            first, read_rgb(back)) and np.array_equal(
                first, read_rgb(back_again))),
    }

    # --- C. Multiple events, duplicate, remove, limit -------------------
    scene.ald.shooting_star_selected = 0
    bpy.ops.ald.shooting_star_duplicate()
    set_event(scene, 1, azimuth=-120.0, elevation=25.0, direction=60.0,
              length=25.0, start_frame=15, duration=30)
    scene.ald.shooting_star_selected = 0
    bpy.ops.ald.shooting_star_add()
    set_event(scene, 2, azimuth=0.0, elevation=60.0, direction=120.0,
              length=12.0, start_frame=20, duration=20)
    scene.ald.shooting_star_selected = 2
    bpy.ops.ald.shooting_star_add()
    set_event(scene, 3, azimuth=180.0, elevation=70.0, direction=-90.0,
              length=30.0, start_frame=25, duration=24)
    events_before = [
        [event.azimuth, event.elevation, event.start_frame,
         event.duration, event.direction, event.length]
        for event in scene.ald.shooting_star_events]
    look.apply_world(scene)
    capture("multiple_4", 26)
    fifth = bpy.ops.ald.shooting_star_add()
    scene.ald.shooting_star_selected = 0
    dup_limit = bpy.ops.ald.shooting_star_duplicate()
    report["checks"]["multiple"] = {
        "events": len(scene.ald.shooting_star_events),
        "fifth_add": list(fifth),
        "duplicate_at_limit": list(dup_limit),
        "properties_before_remove": events_before,
        "properties_after_remove": None,
    }
    scene.ald.shooting_star_selected = 1
    bpy.ops.ald.shooting_star_remove()
    report["checks"]["multiple"]["properties_after_remove"] = [
        [event.azimuth, event.elevation, event.start_frame,
         event.duration, event.direction, event.length]
        for event in scene.ald.shooting_star_events]
    capture("multiple_3_after_remove", 26)

    # --- D. Positioning: horizon, zenith, camera rotation ---------------
    # reset to one event
    while len(scene.ald.shooting_star_events) > 1:
        scene.ald.shooting_star_selected = len(
            scene.ald.shooting_star_events) - 1
        bpy.ops.ald.shooting_star_remove()
    set_event(scene, 0, azimuth=120.0, elevation=5.0, direction=-35.0,
              length=18.0, start_frame=10, duration=24, enabled=True)
    # place the camera on the event start direction at the same frame
    scene.frame_set(18)
    aim(scene, camera, 120.0, 5.0)
    disable_all(scene)
    off_h5 = os.path.join(out, "horizon5_off.png")
    render(scene, off_h5)
    enable_all(scene)
    path = capture("horizon_elev5", 18)
    report["checks"]["horizon_5"] = star_stats(path, off_h5)
    set_event(scene, 0, elevation=1.0)
    aim(scene, camera, 120.0, 1.0)
    disable_all(scene)
    off_h1 = os.path.join(out, "horizon1_off.png")
    render(scene, off_h1)
    enable_all(scene)
    path = capture("horizon_elev1", 18)
    report["checks"]["horizon_1"] = star_stats(path, off_h1)
    set_event(scene, 0, elevation=85.0)
    aim(scene, camera, 120.0, 85.0)
    disable_all(scene)
    off_z = os.path.join(out, "zenith_off.png")
    render(scene, off_z)
    enable_all(scene)
    path = capture("zenith_elev85", 18)
    report["checks"]["zenith_85"] = star_stats(path, off_z)
    # camera rotation anchor: same world event, camera rotated
    set_event(scene, 0, elevation=40.0)
    aim(scene, camera, 120.0, 40.0)
    disable_all(scene)
    off_anchor_a = os.path.join(out, "anchor_a_off.png")
    render(scene, off_anchor_a)
    enable_all(scene)
    path_a = capture("anchor_a", 18)
    stats_a = star_stats(path_a, off_anchor_a)
    centroid_a = stats_a["centroid"]
    direction_a = direction_from_pixel(scene, camera, centroid_a) \
        if centroid_a else None
    camera.rotation_euler.z += math.radians(15.0)
    bpy.context.view_layer.update()
    disable_all(scene)
    off_anchor_b = os.path.join(out, "anchor_b_off.png")
    render(scene, off_anchor_b)
    enable_all(scene)
    path_b = capture("anchor_b", 18)
    stats_b = star_stats(path_b, off_anchor_b)
    centroid_b = stats_b["centroid"]
    report["checks"]["anchor"] = {
        "centroid_a": centroid_a,
        "centroid_b": centroid_b,
        "bbox_a": stats_a["bbox"],
        "bbox_b": stats_b["bbox"],
        "pixels_a": stats_a["pixels"],
        "pixels_b": stats_b["pixels"],
        "direction_a": direction_a,
        "direction_b": direction_from_pixel(scene, camera, centroid_b)
        if centroid_b else None,
    }

    # --- E. Preview camera modification ---------------------------------
    camera.rotation_euler = (math.radians(75.0), 0.0, 0.0)
    bpy.context.view_layer.update()
    capture("preview_before_view", 18)
    before_rot = rotation_quat(camera)
    before_frame = scene.frame_current
    scene.ald.shooting_star_selected = 0
    bpy.ops.ald.shooting_star_preview()
    report["checks"]["preview_camera"] = {
        "before_rotation": before_rot,
        "before_frame": before_frame,
        "after_rotation": rotation_quat(camera),
        "after_frame": scene.frame_current,
    }
    capture("preview_after_view", 18)

    # --- F. Persistence and duplicated scene ----------------------------
    scene.ald.shooting_star_selected = 0
    capture("persist_before", 26)
    blend = os.path.join(out, "audit_scene.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    camera = scene.camera
    scene.ald.palette = "NEON_NIGHT"
    palette.apply_palette(scene, "NEON_NIGHT")
    capture("persist_after", 26)
    report["checks"]["persistence"] = {
        "events_after_reopen": len(scene.ald.shooting_star_events),
        "identical_render": bool(np.array_equal(
            read_rgb(os.path.join(out, "persist_before.png")),
            read_rgb(os.path.join(out, "persist_after.png")))),
    }
    original = scene
    bpy.ops.scene.new(type="FULL_COPY")
    copy = bpy.context.scene
    copy.name = "Audit Copy"
    copy.ald.shooting_star_events[0].azimuth = -60.0
    copy.ald.shooting_star_events[0].elevation = 20.0
    look.apply_world(copy)
    copy_camera = copy.camera
    scene_camera = original.camera
    bpy.context.window.scene = original
    scene = original
    camera = scene_camera
    capture("persist_original", 26)
    bpy.context.window.scene = copy
    scene = copy
    camera = copy_camera
    capture("persist_copy", 26)
    report["checks"]["duplicated_scene"] = {
        "events_original": len(original.ald.shooting_star_events),
        "events_copy": len(copy.ald.shooting_star_events),
        "world_shared": bool(original.world == copy.world),
        "render_identical": bool(np.array_equal(
            read_rgb(os.path.join(out, "persist_original.png")),
            read_rgb(os.path.join(out, "persist_copy.png")))),
    }

    # --- G. Video frames of the lifecycle -------------------------------
    bpy.context.window.scene = original
    scene = original
    camera = scene.camera
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    aim(scene, camera, 120.0, 40.0)
    for frame in range(10, 35):
        capture("video_f%02d" % frame, frame)
    with open(os.path.join(out, "audit.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("AUDIT", json.dumps(report["checks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
