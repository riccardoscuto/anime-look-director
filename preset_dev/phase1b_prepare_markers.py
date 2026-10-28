"""Prepare marker-29 and marker-30 scenes with a keyed camera (no add-on)."""

import os
import sys

import bpy


def prepare(source, target, marker_expected):
    bpy.ops.wm.open_mainfile(filepath=source)
    scene = bpy.context.scene
    group = bpy.data.node_groups.get("ALD | World Gradient")
    marker = group.get("ald_build") if group is not None else None
    camera = scene.camera
    scene.frame_set(1)
    camera.keyframe_insert("location", frame=1)
    camera.keyframe_insert("rotation_euler", frame=1)
    camera.location = (2.0, -10.0, 4.0)
    camera.rotation_euler = (1.0, 0.2, -0.5)
    camera.keyframe_insert("location", frame=60)
    camera.keyframe_insert("rotation_euler", frame=60)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=target)
    print("PREP", os.path.basename(target), "marker", marker,
          "expected", marker_expected, "events",
          len(scene.ald.shooting_star_events) if hasattr(scene, "ald") else "?")


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    source29, target29, source30, target30 = argv[:4]
    prepare(source29, target29, 29)
    prepare(source30, target30, 30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
