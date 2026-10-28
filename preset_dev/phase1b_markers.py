"""Open marker-29/30 scenes with the candidate and verify events + animation."""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

import anime_look_director  # noqa: E402
from anime_look_director import look  # noqa: E402

FIELDS = ("name", "enabled", "start_frame", "duration", "azimuth",
          "elevation", "direction", "length", "trail", "thickness",
          "brightness", "glow")


def properties(scene):
    values = []
    for event in scene.ald.shooting_star_events:
        item = {field: getattr(event, field) for field in FIELDS}
        item["color"] = list(event.color)
        values.append(item)
    return values


def matrices(scene, camera):
    values = []
    for frame in (1, 30, 60):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        values.extend(round(value, 6) for row in camera.matrix_world
                      for value in row)
    return values


def marker(scene):
    group = bpy.data.node_groups.get("ALD | World Gradient")
    return group.get("ald_build") if group is not None else None


def check(path, out, label):
    bpy.ops.wm.open_mainfile(filepath=path)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    camera = scene.camera
    before = {
        "marker": marker(scene),
        "events": properties(scene),
        "camera": matrices(scene, camera),
    }
    look.apply_world(scene)
    after = {
        "marker": marker(scene),
        "events": properties(scene),
        "camera": matrices(scene, camera),
    }
    saved = os.path.join(out, label + "_saved.blend")
    bpy.ops.wm.save_as_mainfile(filepath=saved)
    bpy.ops.wm.open_mainfile(filepath=saved)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    camera = scene.camera
    reopened = {
        "marker": marker(scene),
        "events": properties(scene),
        "camera": matrices(scene, camera),
    }
    result = {
        "label": label,
        "marker_before": before["marker"],
        "marker_after": after["marker"],
        "marker_reopened": reopened["marker"],
        "events_before": len(before["events"]),
        "events_after": len(after["events"]),
        "events_reopened": len(reopened["events"]),
        "properties_preserved": (before["events"] == after["events"]
                                 == reopened["events"]),
        "animation_preserved": (before["camera"] == after["camera"]
                                == reopened["camera"]),
        "camera_keyed": bool(camera.animation_data is not None),
    }
    print("MARKER", json.dumps(result))
    return result


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.abspath(argv[0])
    os.makedirs(out, exist_ok=True)
    results = []
    for source in argv[1:]:
        label = os.path.splitext(os.path.basename(source))[0]
        results.append(check(source, out, label))
    with open(os.path.join(out, "markers.json"), "w",
              encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print("MARKERS_DONE", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
