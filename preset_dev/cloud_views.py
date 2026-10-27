"""Spatial cards from the shot camera and from the side.

Evidence for the C4.5/C4.6 point: the cards are vertical billboards. The shot
camera sees the intended band; a side camera sees the planes. `Camera Facing`
re-aims the cards at the active camera without moving them.

Every render uses the same scene, palette, card layer and resolution. The World
clouds are off so only the spatial cards are visible.

Run::

    blender -b --factory-startup --python preset_dev/cloud_views.py
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "cloud_views")


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx, look

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds_coverage = 0.5
    scene.ald.clouds_layers = 3
    scene.ald.clouds_altitude = 90.0
    scene.ald.clouds_depth = 180.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.ald.clouds = False
    look.apply_world(scene)
    clouds.remove(scene)
    clouds.create(scene)
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    bpy.context.view_layer.update()

    original = camera.rotation_euler.copy()
    origin, forward, up, right = fx._camera_basis(scene)
    card_center = (origin + forward * 180.0
                   + fx._anchor(scene)[0] * 90.0)
    side = camera.copy()
    side.name = "ALD Side Camera"
    scene.collection.objects.link(side)
    side.location = origin + right * 180.0
    side.rotation_euler = (card_center - side.location).to_track_quat(
        "-Z", "Y").to_euler()

    report = {"resolution": [1280, 720], "coverage": 0.5, "layers": 3,
              "views": []}

    def shot(name, mode):
        scene.ald.clouds_mode = mode
        clouds.refresh(scene)
        bpy.context.view_layer.update()
        path = os.path.join(OUT, name)
        baseline_fx.render(scene, path)
        report["views"].append({"file": name, "mode": mode})
        print("CLOUD VIEW", name, mode)

    shot("shot_locked.png", "SHOT_LOCKED")
    scene.camera = side
    bpy.context.view_layer.update()
    shot("side_locked.png", "SHOT_LOCKED")
    shot("side_facing.png", "CAMERA_FACING")

    scene.camera = camera
    camera.rotation_euler = original
    scene.ald.clouds_mode = "SHOT_LOCKED"
    bpy.data.objects.remove(side, do_unlink=True)
    clouds.remove(scene)
    with open(os.path.join(OUT, "views.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
