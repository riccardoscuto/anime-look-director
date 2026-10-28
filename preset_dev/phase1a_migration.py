"""Legacy-scene migration test for the Phase 1A shooting stars.

Old mode builds a scene with four events on the old add-on and renders it.
New mode opens the same scene with the new code, checks the marker-30 rebuild,
the preserved properties, renders the same frames and saves/reloads.

    blender -b --factory-startup --python preset_dev/phase1a_migration.py -- \
        --mode old --out <dir> --blend <legacy.blend>
    blender -b --factory-startup --python preset_dev/phase1a_migration.py -- \
        --mode new --out <dir> --blend <legacy.blend>
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

W, H = 960, 540
FRAME = 26
EVENTS = [
    {"name": "Legacy A", "start_frame": 10, "duration": 24,
     "azimuth": 110.0, "elevation": 35.0, "direction": -35.0,
     "length": 18.0, "trail": 0.55, "thickness": 0.0018,
     "brightness": 3.0, "glow": 0.8, "color": (0.88, 0.94, 1.0)},
    {"name": "Legacy B", "start_frame": 15, "duration": 30,
     "azimuth": 125.0, "elevation": 50.0, "direction": 60.0,
     "length": 22.0, "trail": 0.40, "thickness": 0.0022,
     "brightness": 4.0, "glow": 1.2, "color": (1.0, 0.80, 0.60)},
    {"name": "Legacy C", "start_frame": 20, "duration": 12,
     "azimuth": 100.0, "elevation": 20.0, "direction": 120.0,
     "length": 16.0, "trail": 0.70, "thickness": 0.0015,
     "brightness": 2.0, "glow": 0.4, "color": (0.70, 0.90, 1.0)},
    {"name": "Legacy D", "start_frame": 25, "duration": 18,
     "azimuth": 140.0, "elevation": 60.0, "direction": -90.0,
     "length": 20.0, "trail": 0.50, "thickness": 0.0020,
     "brightness": 3.5, "glow": 1.0, "color": (1.0, 1.0, 0.90)},
]
FIELDS = ("name", "enabled", "start_frame", "duration", "azimuth",
          "elevation", "direction", "length", "trail", "thickness",
          "brightness", "glow")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"mode": "old", "out": "", "blend": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def event_properties(scene):
    values = []
    for event in scene.ald.shooting_star_events:
        item = {field: getattr(event, field) for field in FIELDS}
        item["color"] = list(event.color)
        values.append(item)
    return values


def sky_angles(vector):
    return [round(math.degrees(math.atan2(vector.x, vector.y)), 4),
            round(math.degrees(math.asin(max(-1.0, min(1.0, vector.z)))), 4)]


def endpoints(scene):
    values = []
    for event in scene.ald.shooting_star_events:
        if hasattr(palette, "_star_endpoints"):
            u0, v0, u1, v1 = palette._star_endpoints(event)
            start = Vector((u0, v0, 1.0)).normalized()
            end = Vector((u1, v1, 1.0)).normalized()
            values.append({
                "kind": "gnomonic",
                "start_u": round(u0, 6), "start_v": round(v0, 6),
                "end_u": round(u1, 6), "end_v": round(v1, 6),
                "start": sky_angles(start), "end": sky_angles(end)})
        else:
            start_az, start_el, end_az, end_el = palette._star_angles(event)
            az = math.radians(start_az)
            el = math.radians(start_el)
            start = Vector((math.cos(el) * math.sin(az),
                            math.cos(el) * math.cos(az),
                            math.sin(el))).normalized()
            az = math.radians(end_az)
            el = math.radians(end_el)
            end = Vector((math.cos(el) * math.sin(az),
                          math.cos(el) * math.cos(az),
                          math.sin(el))).normalized()
            values.append({
                "kind": "great_circle",
                "start": sky_angles(start), "end": sky_angles(end)})
    return values


def components(mask, scale=4, minimum=4):
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
    mode = args["mode"]
    out = os.path.abspath(args["out"])
    blend = os.path.abspath(args["blend"])
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    marker_before = None
    events_before = None
    if mode == "new":
        bpy.ops.wm.open_mainfile(filepath=blend)
        bpy.ops.preferences.addon_enable(module="anime_look_director")
        scene = bpy.context.scene
        group = bpy.data.node_groups.get("ALD | World Gradient")
        marker_before = group.get("ald_build") if group else None
        events_before = event_properties(scene)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.clouds = False
    if mode == "old":
        data = bpy.data.cameras.new("Migration Camera")
        data.lens = 24.0
        camera = bpy.data.objects.new("Migration Camera", data)
        scene.collection.objects.link(camera)
        camera.location = (0.0, -12.0, 3.0)
        a = math.radians(120.0)
        e = math.radians(40.0)
        direction = Vector((math.cos(e) * math.sin(a),
                            math.cos(e) * math.cos(a), math.sin(e)))
        camera.rotation_euler = (
            camera.location + direction * 100.0
            - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = camera
        scene.ald.shooting_star_events.clear()
        for values in EVENTS:
            event = scene.ald.shooting_star_events.add()
            for field, value in values.items():
                setattr(event, field, value)
    else:
        camera = scene.camera
    palette.apply_palette(scene, "NEON_NIGHT")
    result = {"mode": mode, "events": event_properties(scene),
              "endpoints": endpoints(scene), "renders": {}}

    def render(name, enabled_indices, frame=FRAME):
        events = scene.ald.shooting_star_events
        for index, event in enumerate(events):
            event.enabled = index in enabled_indices
        palette.apply_palette(scene, "NEON_NIGHT")
        scene.frame_set(frame)
        path = os.path.join(out, "%s_%s.png" % (mode, name))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        return path

    off = render("off", set())
    all_on = render("all", set(range(len(scene.ald.shooting_star_events))))
    diff = np.abs(read_rgb(all_on) - read_rgb(off)).max(axis=2)
    mask = diff > 0.02
    count, sizes = components(mask)
    result["wide"] = {"pixels": int(mask.sum()),
                      "max": round(float(diff.max()), 3),
                      "components": count, "sizes": sizes}
    result["renders"]["all"] = os.path.basename(all_on)
    result["renders"]["off"] = os.path.basename(off)
    for index in range(len(scene.ald.shooting_star_events)):
        path = render("event%d" % index, {index})
        stats = np.abs(read_rgb(path) - read_rgb(off)).max(axis=2) > 0.02
        result["renders"]["event%d" % index] = os.path.basename(path)
        result.setdefault("per_event", {})[str(index)] = {
            "pixels": int(stats.sum())}
    if mode == "old":
        for event in scene.ald.shooting_star_events:
            event.enabled = True
        palette.apply_palette(scene, "NEON_NIGHT")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        result["marker"] = bpy.data.node_groups.get(
            "ALD | World Gradient").get("ald_build")
        result["blend"] = os.path.basename(blend)
    else:
        result["marker_before"] = marker_before
        result["events_before"] = events_before
        group = bpy.data.node_groups.get("ALD | World Gradient")
        result["marker_after"] = group.get("ald_build")
        result["node_tree"] = bool(palette._gradient_node(
            scene.world.node_tree).node_tree)
        result["blend"] = os.path.basename(blend)
        pre_save = read_rgb(os.path.join(out, "%s_all.png" % mode))
        for event in scene.ald.shooting_star_events:
            event.enabled = True
        palette.apply_palette(scene, "NEON_NIGHT")
        save_path = os.path.splitext(blend)[0] + "_new.blend"
        bpy.ops.wm.save_as_mainfile(filepath=save_path)
        bpy.ops.wm.open_mainfile(filepath=save_path)
        bpy.ops.preferences.addon_enable(module="anime_look_director")
        scene = bpy.context.scene
        scene.ald.palette = "NEON_NIGHT"
        scene.ald.clouds = False
        palette.apply_palette(scene, "NEON_NIGHT")
        scene.frame_set(FRAME)
        persist = os.path.join(out, "new_persist.png")
        scene.render.filepath = persist
        bpy.ops.render.render(write_still=True)
        result["persistence"] = {
            "events": len(scene.ald.shooting_star_events),
            "identical": bool(np.array_equal(pre_save,
                                             read_rgb(persist))),
        }
        result["events_after"] = event_properties(scene)
    with open(os.path.join(out, "%s_migration.json" % mode), "w",
              encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("MIGRATION " + json.dumps(result))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
