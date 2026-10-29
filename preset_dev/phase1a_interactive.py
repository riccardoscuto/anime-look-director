"""Interactive Phase 1A Preview smoke test (graphical Blender).

Run in a GUI Blender with factory startup and the current add-on:

    blender --factory-startup --python preset_dev/phase1a_interactive.py -- \
        --out <dir>

The script uses a real 3D viewport, a real Properties area and the operator's
actual context overrides. It writes interactive.json and screenshots, then
quits. It never touches the user's open file (separate process and temp save).
"""

import json
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

OUT = os.path.join(HERE, "phase1a_shooting_stars", "interactive")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": OUT}
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
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def matrix(camera):
    bpy.context.view_layer.update()
    return [round(value, 6) for row in camera.matrix_world for value in row]


def view_direction(region):
    return (region.view_rotation @ Vector((0.0, 0.0, -1.0))).normalized()


def angle(a, b):
    return round(math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b))))), 3)


def screenshot(window, path):
    try:
        with bpy.context.temp_override(window=window, screen=window.screen):
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
            bpy.ops.screen.screenshot(filepath=path)
        return os.path.exists(path)
    except Exception:
        traceback.print_exc()
        return False


def run():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    build_hash = bpy.app.build_hash
    if isinstance(build_hash, bytes):
        build_hash = build_hash.decode("ascii", "replace")
    result = {"checks": {}, "screenshots": [],
              "blender": bpy.app.version_string, "hash": str(build_hash)}
    failures = []

    def check(name, ok, detail=""):
        result["checks"][name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)
        print("INTERACTIVE", name, "PASS" if ok else "FAIL", detail)

    def shot(name):
        path = os.path.join(out, name + ".png")
        if screenshot(window, path):
            result["screenshots"].append(os.path.basename(path))
        else:
            result["screenshots"].append("FAILED:" + os.path.basename(path))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import look, palette

    window = bpy.context.window_manager.windows[0]
    screen = window.screen
    area3d = next((area for area in screen.areas if area.type == "VIEW_3D"),
                  None)
    props = next((area for area in screen.areas
                  if area.type in {"PROPERTIES", "OUTLINER"}), None)
    if area3d is None:
        raise RuntimeError("No VIEW_3D area in the default workspace")
    region = next(item for item in area3d.regions
                  if item.type == "WINDOW")
    space = area3d.spaces.active
    view3d = space.region_3d
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.clouds = False
    palette.apply_palette(scene, "NEON_NIGHT")
    data = bpy.data.cameras.new("Interactive Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Interactive Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    aim(camera, 120.0, 40.0)
    scene.camera = camera
    event = scene.ald.shooting_star_events.add()
    event.name = "UI Star"
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 18.0
    event.start_frame = 10
    event.duration = 24
    event.trail = 0.55
    event.thickness = 0.0018
    event.brightness = 3.0
    event.glow = 0.8
    scene.ald.shooting_star_selected = 0
    look.apply_world(scene)
    space.shading.type = "RENDERED"
    space.shading.use_scene_world = True
    space.shading.use_scene_lights = True
    space.overlay.show_overlays = False
    space.show_gizmo = False
    view3d.view_perspective = "PERSP"
    view3d.view_location = (0.0, 0.0, 0.0)
    view3d.view_distance = 10.0
    view3d.view_rotation = look_direction(300.0, 10.0).to_track_quat(
        "-Z", "Y")
    bpy.context.view_layer.update()
    shot("viewport_before")

    # 1. Preview from the 3D viewport.
    camera_before = matrix(camera)
    with bpy.context.temp_override(window=window, screen=screen,
                                   area=area3d, region=region,
                                   space_data=space):
        preview = bpy.ops.ald.shooting_star_preview()
    bpy.context.view_layer.update()
    expected = look_direction(120.0, 40.0)
    framed = angle(view_direction(view3d), expected)
    check("preview_3d",
          list(preview) == ["FINISHED"] and scene.frame_current == 18
          and framed < 0.5 and matrix(camera) == camera_before,
          "frame %d, view error %.3f deg, camera %s" % (
              scene.frame_current, framed,
              "unchanged" if matrix(camera) == camera_before else "moved"))
    shot("viewport_after")
    # Re-capture the neutral view now that the viewport is warm; the first
    # screenshot can be taken before the Rendered shading has drawn the World.
    scene.frame_set(18)
    view3d.view_rotation = look_direction(300.0, 10.0).to_track_quat(
        "-Z", "Y")
    shot("viewport_before")

    # 2. Keyed camera.
    camera.animation_data_clear()
    scene.frame_set(1)
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
            values.extend(matrix(camera))
        return values

    before = keyed_matrices()
    scene.frame_set(20)
    with bpy.context.temp_override(window=window, screen=screen,
                                   area=area3d, region=region,
                                   space_data=space):
        preview = bpy.ops.ald.shooting_star_preview()
    preview_frame = scene.frame_current
    after = keyed_matrices()
    scene.frame_set(18)
    check("preview_keyed",
          list(preview) == ["FINISHED"] and preview_frame == 18
          and before == after,
          "frame %d, keyed camera %s" % (
              preview_frame,
              "unchanged" if before == after else "changed"))
    shot("preview_keyed")

    # 3. Preview from a non-3D editor (Properties if available).
    if props is None:
        check("preview_other_editor", False, "no Properties/Outliner area")
    else:
        scene.frame_set(18)
        view3d.view_rotation = look_direction(300.0, 10.0).to_track_quat(
            "-Z", "Y")
        neutral = [round(value, 6) for value in view3d.view_rotation]
        camera_before = matrix(camera)
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=props,
                                       region=next(item for item in props.regions
                                                   if item.type == "WINDOW")):
            preview = bpy.ops.ald.shooting_star_preview()
        current = [round(value, 6) for value in view3d.view_rotation]
        check("preview_other_editor",
              list(preview) == ["FINISHED"] and scene.frame_current == 18
              and current == neutral and matrix(camera) == camera_before,
              "editor %s, frame %d, viewport %s, camera %s" % (
                  props.type, scene.frame_current,
                  "unchanged" if current == neutral else "changed",
                  "unchanged" if matrix(camera) == camera_before
                  else "moved"))
        shot("preview_other_editor")

    # 4. No active camera.
    objects_before = [object.name for object in bpy.data.objects]
    cameras_before = len(bpy.data.cameras)
    scene.camera = None
    with bpy.context.temp_override(window=window, screen=screen,
                                   area=area3d, region=region,
                                   space_data=space):
        preview = bpy.ops.ald.shooting_star_preview()
    bpy.context.view_layer.update()
    check("preview_no_camera",
          list(preview) == ["FINISHED"] and scene.camera is None
          and [object.name for object in bpy.data.objects] == objects_before
          and len(bpy.data.cameras) == cameras_before,
          "frame %d, no camera created or transformed" % scene.frame_current)
    scene.camera = camera
    shot("preview_no_camera")

    # 5. Save/reopen after Preview.
    scene.frame_set(18)
    marker = bpy.data.node_groups.get("ALD | World Gradient")
    marker = marker.get("ald_build") if marker is not None else None
    camera_before_save = matrix(camera)
    saved = os.path.join(out, "interactive.blend")
    bpy.ops.wm.save_as_mainfile(filepath=saved)
    bpy.ops.wm.open_mainfile(filepath=saved)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.frame_set(18)
    camera = scene.camera
    events = scene.ald.shooting_star_events
    marker_after = bpy.data.node_groups.get("ALD | World Gradient")
    marker_after = (marker_after.get("ald_build")
                    if marker_after is not None else None)
    check("persistence",
          len(events) == 1 and events[0].name == "UI Star"
          and events[0].azimuth == 120.0 and events[0].elevation == 40.0
          and events[0].start_frame == 10 and events[0].duration == 24
          and marker == 34 and marker_after == 34 and camera is not None
          and matrix(camera) == camera_before_save,
          "%d event(s), marker %s->%s, camera %s" % (
              len(events), marker, marker_after, camera is not None))

    result["verdict"] = "PASS" if not failures else "FAIL"
    result["failures"] = failures
    with open(os.path.join(out, "interactive.json"), "w",
              encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("INTERACTIVE_RESULT", json.dumps(result))
    return 0


def main():
    try:
        run()
    except Exception:
        traceback.print_exc()
        try:
            os.makedirs(OUT, exist_ok=True)
            with open(os.path.join(OUT, "interactive.json"), "w",
                      encoding="utf-8") as handle:
                json.dump({"verdict": "FAIL", "error": traceback.format_exc()},
                          handle, indent=2)
        except Exception:
            pass
    finally:
        if hasattr(bpy.app.timers, "register"):
            bpy.app.timers.register(lambda: os._exit(0), first_interval=0.5)


if __name__ == "__main__":
    bpy.app.timers.register(main, first_interval=1.5)
