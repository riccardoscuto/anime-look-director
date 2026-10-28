"""Phase 1A technical gate for the shooting-star system.

Renders and measures the World-shader star: great-circle trajectory, angular
thickness at 1/5/40/85 degrees, horizon crossing, lifecycle, four events in one
frame, Preview on a keyed camera, persistence, scene duplicate, removal and
scrubbing.

    blender -b --factory-startup --python preset_dev/phase1a_shooting_stars.py \
        -- --out <dir>

Prints ``ALD PHASE1A: PASS`` when every check passes and writes metrics.json
into the output directory.
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
from anime_look_director import look, palette  # noqa: E402

W, H = 1280, 720
FPS = 24
EVENT = {
    "azimuth": 120.0, "elevation": 40.0, "direction": -35.0,
    "length": 18.0, "start_frame": 10, "duration": 24, "trail": 0.55,
    "thickness": 0.0018, "brightness": 3.0, "glow": 0.8,
}
ELEVATIONS = (1.0, 5.0, 40.0, 85.0)


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "phase1a"), "engine": "eevee"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def fixture(engine="eevee"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 60
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.clouds = False
    palette.apply_palette(scene, "NEON_NIGHT")
    data = bpy.data.cameras.new("Phase 1A Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Phase 1A Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    scene.camera = camera
    return scene, camera


def look_direction(azimuth, elevation):
    a = math.radians(azimuth)
    e = math.radians(elevation)
    return Vector((math.cos(e) * math.sin(a),
                   math.cos(e) * math.cos(a),
                   math.sin(e))).normalized()


def aim(camera, azimuth, elevation):
    direction = look_direction(azimuth, elevation)
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def arc(event):
    """Independent great-circle arc: start, tangent, end, theta."""
    azimuth = math.radians(event["azimuth"])
    elevation = math.radians(event["elevation"])
    direction = math.radians(event["direction"])
    length = math.radians(event["length"])
    start = look_direction(event["azimuth"], event["elevation"])
    east = Vector((math.cos(azimuth), -math.sin(azimuth), 0.0)).normalized()
    north = Vector((-math.sin(azimuth) * math.sin(elevation),
                    -math.cos(azimuth) * math.sin(elevation),
                    math.cos(elevation))).normalized()
    tangent = (east * math.cos(direction) + north * math.sin(direction))
    tangent.normalize()
    theta = length
    return start, tangent, (start * math.cos(theta) + tangent * math.sin(theta)), theta


def set_events(scene, items):
    events = scene.ald.shooting_star_events
    events.clear()
    for index, values in enumerate(items):
        event = events.add()
        event.name = "Test %d" % (index + 1)
        merged = dict(EVENT)
        merged.update(values)
        for key, value in merged.items():
            setattr(event, key, value)
    scene.ald.shooting_star_selected = 0
    look.apply_world(scene)
    return events


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def render(scene, path, frame):
    scene.frame_set(frame)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return read_rgb(path)


def mask_stats(on, off):
    diff = np.abs(on - off).max(axis=2)
    mask = diff > 0.02
    if not mask.any():
        return {"pixels": 0, "max": 0.0, "bbox": None, "mask": mask,
                "diff": diff}
    ys, xs = np.nonzero(mask)
    return {"pixels": int(mask.sum()), "max": round(float(diff.max()), 3),
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "mask": mask, "diff": diff}


def ray_direction(camera, x, y):
    tan_x = math.tan(camera.data.angle_x * 0.5)
    tan_y = tan_x * H / W
    local = Vector(((2.0 * (x + 0.5) / W - 1.0) * tan_x,
                    (2.0 * (y + 0.5) / H - 1.0) * tan_y, -1.0))
    return (camera.matrix_world.to_3x3() @ local).normalized()


def direction_angles(direction):
    return (math.degrees(math.atan2(direction.x, direction.y)),
            math.degrees(math.asin(max(-1.0, min(1.0, direction.z)))))


def angular_distance(a, b):
    dot = max(-1.0, min(1.0, a.dot(b)))
    return math.degrees(math.acos(dot))


def back_project(camera, mask, start, tangent, head_angle=18.0,
                 width_range=(10.0, 16.0)):
    ys, xs = np.nonzero(mask)
    normal = start.cross(tangent).normalized()
    along = []
    width = []
    heads = []
    for x, y in zip(xs, ys):
        direction = ray_direction(camera, x, y)
        phi = math.degrees(math.atan2(direction.dot(tangent),
                                      direction.dot(start)))
        plane = math.degrees(math.asin(max(-1.0, min(
            1.0, abs(direction.dot(normal))))))
        along.append(phi)
        if width_range[0] <= phi <= width_range[1]:
            width.append(plane)
        if phi > head_angle - 0.8:
            heads.append(direction)
    along = np.array(along)
    width = np.array(width)
    head = None
    if heads:
        summed = Vector((0.0, 0.0, 0.0))
        for direction in heads:
            summed += direction
        head = summed.normalized()
    return {"along_min": round(float(along.min()), 2),
            "along_max": round(float(along.max()), 2),
            "width_p50": round(float(np.percentile(width, 50)), 3)
            if len(width) else 0.0,
            "width_p95": round(float(np.percentile(width, 95)), 3)
            if len(width) else 0.0,
            "head": head}


def head_at(start, tangent, angle):
    return (start * math.cos(angle) + tangent * math.sin(angle)).normalized()


def screen_point(scene, camera, direction):
    point = camera.location + direction * 100.0
    coord = world_to_camera_view(scene, camera, point)
    return coord.x * W, coord.y * H


def components(mask, scale=2, minimum=8):
    small = mask[::scale, ::scale]
    seen = np.zeros(small.shape, dtype=bool)
    sizes = []
    for y, x in zip(*np.nonzero(small)):
        if seen[y, x]:
            continue
        stack = [(y, x)]
        seen[y, x] = True
        size = 0
        while stack:
            cy, cx = stack.pop()
            size += 1
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if (0 <= ny < small.shape[0] and 0 <= nx < small.shape[1]
                            and small[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        if size >= minimum:
            sizes.append(size)
    return len(sizes), sorted(sizes, reverse=True)


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene, camera = fixture(args["engine"])
    settings = scene.ald
    report = {"checks": {}, "renders": {}, "metrics": {}}
    failures = []

    def check(name, ok, detail=""):
        report["checks"][name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)
        print("CHECK", name, "PASS" if ok else "FAIL", detail)

    def render_pair(name, frame, suffix=".png"):
        events = scene.ald.shooting_star_events
        for event in events:
            event.enabled = False
        look.apply_world(scene)
        off = render(scene, os.path.join(out, name + "_off" + suffix), frame)
        for event in events:
            event.enabled = True
        look.apply_world(scene)
        on = render(scene, os.path.join(out, name + "_on" + suffix), frame)
        report["renders"][name] = {
            "on": os.path.join(out, name + "_on" + suffix),
            "off": os.path.join(out, name + "_off" + suffix)}
        return mask_stats(on, off)

    def capture_event(name, frame, items, azimuth, elevation, suffix=".png"):
        set_events(scene, items)
        aim(camera, azimuth, elevation)
        return render_pair(name, frame, suffix)

    # --- SS-03: Add from a horizon camera -------------------------------
    scene.frame_set(20)
    aim(camera, 100.0, 0.0)
    bpy.ops.ald.shooting_star_add()
    added = scene.ald.shooting_star_events[0]
    add_stats = render_pair("add_horizon", 20)
    check("add.horizon",
          added.start_frame == 20 and abs(added.elevation - 1.0) < 0.01
          and added.direction > 0.0 and add_stats["pixels"] > 20,
          "el %.2f dir %.1f %d px" % (added.elevation, added.direction,
                                       add_stats["pixels"]))
    bpy.ops.ald.shooting_star_remove()

    # --- SS-02: geometry at four elevations -----------------------------
    geometry = {}
    for elevation in ELEVATIONS:
        item = dict(EVENT)
        item.update({"azimuth": 120.0, "elevation": elevation,
                     "direction": 35.0})
        stats = capture_event("elev_%g" % elevation, 33, [item],
                              120.0, elevation)
        geometry[str(elevation)] = stats
        start, tangent, end, theta = arc(item)
        maybe = back_project(camera, stats["mask"], start, tangent)
        stats["back"] = {key: value for key, value in maybe.items()
                         if key != "head"}
        stats["head"] = None
        if maybe["head"] is not None:
            head_angles = direction_angles(maybe["head"])
            end_angles = direction_angles(end)
            stats["head"] = {
                "angles": [round(head_angles[0], 2),
                           round(head_angles[1], 2)],
                "expected": [round(end_angles[0], 2),
                             round(end_angles[1], 2)],
                "error": round(angular_distance(maybe["head"], end), 2),
            }
        print("GEOMETRY", elevation, json.dumps(
            {key: value for key, value in stats.items()
             if key in ("pixels", "max", "bbox", "back", "head")}))
    report["metrics"]["geometry"] = {
        key: {name: value for name, value in item.items()
              if name != "mask" and name != "diff"}
        for key, item in geometry.items()}
    widths = [geometry[str(item)]["back"]["width_p95"] for item in ELEVATIONS]
    check("geometry.width_constant",
          max(widths) <= 0.45 and min(widths) >= 0.04
          and max(widths) / min(widths) <= 3.0,
          "p95 width deg %s" % widths)
    for elevation in ELEVATIONS:
        item = geometry[str(elevation)]
        check("geometry.visible_%g" % elevation,
              item["pixels"] > 80 and item["max"] > 0.2,
              "%d px, max %.3f" % (item["pixels"], item["max"]))
        check("geometry.length_%g" % elevation,
              abs(item["back"]["along_max"] - 18.0) < 1.2
              and abs(item["back"]["along_min"] - 8.1) < 1.6,
              "along %.2f..%.2f" % (item["back"]["along_min"],
                                    item["back"]["along_max"]))
        check("geometry.head_%g" % elevation,
              item["head"] is not None and item["head"]["error"] < 1.3,
              "head %s expected %s error %s" % (
                  item["head"]["angles"] if item["head"] else None,
                  item["head"]["expected"] if item["head"] else None,
                  item["head"]["error"] if item["head"] else None))

    # Horizon-crossing trajectory: from 3 deg down through the horizon.
    crossing = dict(EVENT)
    crossing.update({"azimuth": 120.0, "elevation": 3.0, "direction": -20.0,
                     "length": 12.0, "start_frame": 10, "duration": 24})
    stats = capture_event("horizon_cross", 33, [crossing], 120.0, 3.0)
    start, tangent, end, theta = arc(crossing)
    back = back_project(camera, stats["mask"], start, tangent, 12.0,
                        (4.5, 8.5))
    report["metrics"]["horizon_cross"] = {
        key: value for key, value in stats.items()
        if key not in ("mask", "diff")}
    check("horizon.visible", stats["pixels"] > 20 and stats["max"] > 0.1,
          "%d px, max %.3f" % (stats["pixels"], stats["max"]))
    check("horizon.continuous", 0.04 <= back["width_p95"] <= 0.45,
          "width p95 %.3f" % back["width_p95"])
    check("horizon.head_below", 7.0 < back["along_max"] < 10.5,
          "along max %.2f" % back["along_max"])

    # --- SS-01: lifecycle ------------------------------------------------
    item = dict(EVENT)
    item.update({"azimuth": 120.0, "elevation": 40.0, "direction": 35.0})
    events = set_events(scene, [item])
    aim(camera, 120.0, 40.0)
    off = render(scene, os.path.join(out, "life_off.png"), 9)
    lifecycle = {}
    first_on = None
    for frame in (9, 10, 11, 18, 32, 33, 34, 35):
        image = render(scene, os.path.join(out, "life_%d.png" % frame), frame)
        stats = mask_stats(image, off)
        lifecycle[str(frame)] = {
            key: value for key, value in stats.items()
            if key not in ("mask", "diff")}
        if frame == 10:
            first_on = stats
    report["metrics"]["lifecycle"] = lifecycle
    check("lifecycle.before", lifecycle["9"]["pixels"] == 0,
          "%d px at 9" % lifecycle["9"]["pixels"])
    check("lifecycle.start_visible", lifecycle["10"]["pixels"] > 20,
          "%d px at 10" % lifecycle["10"]["pixels"])
    check("lifecycle.last_visible", lifecycle["33"]["pixels"] > 20,
          "%d px at 33" % lifecycle["33"]["pixels"])
    check("lifecycle.after", lifecycle["34"]["pixels"] == 0
          and lifecycle["35"]["pixels"] == 0,
          "%d px at 34, %d px at 35" % (
              lifecycle["34"]["pixels"], lifecycle["35"]["pixels"]))
    start, tangent, end, theta = arc(item)
    head = back_project(camera, first_on["mask"], start, tangent, 0.0)
    check("lifecycle.head_at_start",
          head["head"] is not None
          and angular_distance(head["head"], start) < 0.8,
          "head error %.2f" % (angular_distance(head["head"], start)
                                if head["head"] else -1.0))

    # Duration 2: frames 10 and 11 only.
    short = dict(item)
    short.update({"duration": 2})
    set_events(scene, [short])
    aim(camera, 120.0, 40.0)
    off = render(scene, os.path.join(out, "short_off.png"), 9)
    short_result = {}
    for frame in (9, 10, 11, 12):
        image = render(scene, os.path.join(out, "short_%d.png" % frame), frame)
        short_result[str(frame)] = mask_stats(image, off)["pixels"]
    report["metrics"]["duration2"] = short_result
    check("duration2",
          short_result["9"] == 0 and short_result["10"] > 10
          and short_result["11"] > 10 and short_result["12"] == 0,
          json.dumps(short_result))

    # Scrubbing: same frame rendered after seeking around.
    set_events(scene, [item])
    aim(camera, 120.0, 40.0)
    fresh = render(scene, os.path.join(out, "scrub_a.png"), 33)
    render(scene, os.path.join(out, "scrub_b.png"), 10)
    render(scene, os.path.join(out, "scrub_c.png"), 18)
    seek = render(scene, os.path.join(out, "scrub_d.png"), 33)
    check("scrubbing", bool(np.array_equal(fresh, seek)),
          "frame 33 identical after seeking away and back")

    # --- SS-05 / multiple events ---------------------------------------
    four = [
        {"azimuth": 105.0, "elevation": 30.0, "direction": -35.0,
         "length": 12.0, "start_frame": 8, "duration": 30},
        {"azimuth": 114.0, "elevation": 38.0, "direction": 60.0,
         "length": 14.0, "start_frame": 8, "duration": 30},
        {"azimuth": 126.0, "elevation": 42.0, "direction": 120.0,
         "length": 14.0, "start_frame": 8, "duration": 30},
        {"azimuth": 135.0, "elevation": 34.0, "direction": -90.0,
         "length": 12.0, "start_frame": 8, "duration": 30},
    ]
    events = set_events(scene, four)
    aim(camera, 120.0, 36.0)
    at_limit = bpy.ops.ald.shooting_star_duplicate()
    check("duplicate.limit", list(at_limit) == ["CANCELLED"]
          and len(events) == 4, str(list(at_limit)))
    four_stats = render_pair("four", 20)
    count, sizes = components(four_stats["mask"])
    report["metrics"]["four_events"] = {
        "pixels": four_stats["pixels"], "components": count, "sizes": sizes}
    check("four.visible", four_stats["pixels"] > 100 and count == 4,
          "%d px, components %s" % (four_stats["pixels"], sizes))
    for index, item in enumerate(four):
        start, tangent, end, theta = arc(item)
        progress = (20 - item["start_frame"]) / (item["duration"] - 1)
        head = head_at(start, tangent, progress * theta)
        x, y = screen_point(scene, camera, head)
        gx, gy = int(min(W - 1, max(0, x))), int(min(H - 1, max(0, y)))
        local = four_stats["mask"][max(0, gy - 12):gy + 12,
                                   max(0, gx - 12):gx + 12]
        check("four.event_%d" % (index + 1), bool(local.any()),
              "head at %.0f, %.0f" % (x, y))

    before = [[event.azimuth, event.elevation, event.start_frame,
               event.duration, event.direction, event.length]
              for event in events]
    settings.shooting_star_selected = 1
    bpy.ops.ald.shooting_star_remove()
    after = [[event.azimuth, event.elevation, event.start_frame,
              event.duration, event.direction, event.length]
             for event in events]
    three_stats = render_pair("three", 20)
    count3, sizes3 = components(three_stats["mask"])
    check("remove.independent",
          after == [before[0], before[2], before[3]] and count3 == 3,
          "components %s" % sizes3)

    settings.shooting_star_selected = 0
    duplicated = bpy.ops.ald.shooting_star_duplicate()
    copy = events[-1]
    source = events[0]
    check("duplicate.copy", list(duplicated) == ["FINISHED"]
          and len(events) == 4
          and copy.azimuth == source.azimuth
          and copy.start_frame == source.start_frame + 12,
          "start %d, source %d" % (copy.start_frame, source.start_frame))
    settings.shooting_star_selected = len(events) - 1
    bpy.ops.ald.shooting_star_remove()

    # --- SS-04: Preview on a keyed camera -------------------------------
    set_events(scene, [item])
    aim(camera, 120.0, 40.0)
    camera.keyframe_insert("rotation_euler", frame=1)
    camera.keyframe_insert("location", frame=1)
    camera.rotation_euler = (1.0, 0.2, -0.5)
    camera.location = (2.0, -10.0, 4.0)
    camera.keyframe_insert("rotation_euler", frame=60)
    camera.keyframe_insert("location", frame=60)

    def keyed_matrices():
        values = []
        for frame in (1, 20, 60):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            values.extend(round(value, 6) for row in camera.matrix_world
                          for value in row)
        return values

    before_matrix = keyed_matrices()
    scene.frame_set(20)
    settings.shooting_star_selected = 0
    preview = bpy.ops.ald.shooting_star_preview()
    preview_frame = scene.frame_current
    after_matrix = keyed_matrices()
    check("preview.non_destructive",
          list(preview) == ["FINISHED"] and before_matrix == after_matrix
          and preview_frame == 18,
          "frame %d, camera unchanged %s" % (
              preview_frame, before_matrix == after_matrix))
    camera.animation_data_clear()
    scene.frame_set(20)

    # --- World anchor under camera rotation ----------------------------
    set_events(scene, [item])
    aim(camera, 120.0, 40.0)
    start, tangent, end, theta = arc(item)
    a = render_pair("anchor_a", 10)
    head_a = back_project(camera, a["mask"], start, tangent, 0.0)["head"]
    camera.rotation_euler.z += math.radians(15.0)
    bpy.context.view_layer.update()
    b = render_pair("anchor_b", 10)
    head_b = back_project(camera, b["mask"], start, tangent, 0.0)["head"]
    camera.rotation_euler.z -= math.radians(15.0)
    bpy.context.view_layer.update()
    anchor = (angular_distance(head_a, head_b)
              if head_a is not None and head_b is not None else -1.0)
    check("anchor.camera_rotation", 0.0 <= anchor < 0.8,
          "world error %.2f deg" % anchor)

    # --- Persistence ----------------------------------------------------
    set_events(scene, four)
    aim(camera, 120.0, 36.0)
    before_save = render(scene, os.path.join(out, "persist_before.png"), 20)
    blend = os.path.join(out, "phase1a.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    camera = scene.camera
    after_load = render(scene, os.path.join(out, "persist_after.png"), 20)
    restored = [[event.azimuth, event.elevation, event.start_frame,
                 event.duration, event.direction, event.length]
                for event in scene.ald.shooting_star_events]
    check("persistence", bool(np.array_equal(before_save, after_load))
          and len(restored) == 4,
          "render identical, %d events" % len(restored))

    # --- Duplicated scene ----------------------------------------------
    original = scene
    original_values = [[event.azimuth, event.elevation]
                       for event in original.ald.shooting_star_events]
    bpy.ops.scene.new(type="FULL_COPY")
    copy = bpy.context.scene
    copy.name = "Phase 1A Copy"
    copy.ald.shooting_star_events[0].azimuth = -60.0
    copy.ald.shooting_star_events[0].elevation = 20.0
    look.apply_world(copy)
    bpy.context.window.scene = original
    scene = original
    camera = scene.camera
    original_render = render(scene, os.path.join(out, "scene_original.png"),
                             20)
    bpy.context.window.scene = copy
    copied_render = render(copy, os.path.join(out, "scene_copy.png"), 20)
    check("scene.duplicate",
          original.world != copy.world
          and [[event.azimuth, event.elevation]
               for event in original.ald.shooting_star_events]
          == original_values
          and not np.array_equal(original_render, copied_render),
          "world independent, originals unchanged")
    bpy.context.window.scene = original
    scene = original
    camera = scene.camera

    # --- Test animation -------------------------------------------------
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    set_events(scene, [item])
    aim(camera, 120.0, 40.0)
    video = []
    for frame in range(10, 35):
        path = os.path.join(out, "video_f%02d.png" % frame)
        scene.frame_set(frame)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        video.append(path)
    report["video"] = video

    # Linear (EXR) brightness: the star's own contribution, independent of the
    # display-referred sky behind it. Clouds are already off. Kept after the
    # save/reopen because loading EXR images can upset a mid-session reload.
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.image_settings.file_format = "OPEN_EXR"
    linear = {}
    for elevation in (5.0, 40.0):
        item = dict(EVENT)
        item.update({"azimuth": 120.0, "elevation": elevation,
                     "direction": 35.0})
        linear[str(elevation)] = capture_event(
            "linear_%g" % elevation, 33, [item], 120.0, elevation,
            ".exr")["max"]
    scene.render.image_settings.file_format = "PNG"
    report["metrics"]["linear_brightness"] = linear
    brightness_ratio = (max(linear.values()) / min(linear.values())
                        if min(linear.values()) > 0 else 0.0)
    check("brightness.linear", 0.85 <= brightness_ratio <= 1.15,
          "EXR peak 5/40: %s (ratio %.3f)" % (linear, brightness_ratio))

    report["status"] = "PASS" if not failures else "FAIL"
    report["failures"] = failures
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    if failures:
        print("ALD PHASE1A: FAIL", ", ".join(failures))
        return 1
    print("ALD PHASE1A: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
