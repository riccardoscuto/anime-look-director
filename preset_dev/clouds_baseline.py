"""P0 baseline for Spatial Clouds 2.0.

Reproduces the slab and the broken Cloud Amount: the same scene, palette and
camera, with Cloud Amount 0 / 0.16 / 0.5 / 1.0 and Cloud Height 0.35 / 1.5,
seen from the final camera and from an oblique diagnostic view. One optional
Chrysanthemum is rendered for the second camera only.

The metrics record the object count, the polygon count, the world bounding
box, the build time and the render time, plus the cloud coverage measured
against the same frame without clouds.

Run::

    blender -b --factory-startup --python preset_dev/clouds_baseline.py
"""

import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "clouds_baseline")
AMOUNTS = (0.0, 0.16, 0.5, 1.0)
HEIGHTS = (0.35, 1.5)
SIZE = (640, 360)


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def cloud_stats(scene):
    from anime_look_director import clouds
    collection = clouds._collection(scene)
    if collection is None:
        return {"objects": 0, "polygons": 0, "bounds": [0.0] * 3}
    objects = [obj for obj in collection.objects if obj.type == "MESH"]
    polygons = sum(len(obj.data.polygons) for obj in objects)
    points = []
    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return {"objects": 0, "polygons": 0, "bounds": [0.0] * 3}
    low = Vector((min(p.x for p in points), min(p.y for p in points),
                  min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points),
                   max(p.z for p in points)))
    return {"objects": len(objects), "polygons": polygons,
            "bounds": [round(v, 2) for v in (high - low)]}


def build_scene(palette):
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx

    settings = scene.ald
    settings.palette = palette
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    settings.clouds_amount = 0.5
    settings.clouds_height = 0.35
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.render.resolution_x = SIZE[0]
    scene.render.resolution_y = SIZE[1]
    camera.data.lens = 40.0
    camera.rotation_euler = (1.20, 0.0, 0.0)  # sky, the bands in frame
    fx.clear(scene)
    clouds.remove(scene)
    return scene, camera


def oblique_camera(scene):
    camera = scene.camera
    camera.location = (70.0, -80.0, 55.0)
    camera.rotation_euler = (Vector((0.0, 150.0, 70.0))
                             - camera.location).to_track_quat(
                                 "-Z", "Y").to_euler()
    camera.data.lens = 50.0
    bpy.context.view_layer.update()


def main():
    os.makedirs(OUT, exist_ok=True)
    from anime_look_director import clouds, fx

    scene, camera = build_scene("AFTER_SCHOOL")
    # Reference without clouds, both cameras.
    references = {}
    for view in ("final", "oblique"):
        if view == "oblique":
            oblique_camera(scene)
        path = os.path.join(OUT, "reference_%s.png" % view)
        baseline_fx.render(scene, path)
        references[view] = read_rgb(path)
    # Back to the final camera for the matrix.
    scene, camera = build_scene("AFTER_SCHOOL")

    report = {"commit": baseline_fx.commit_hash(), "palette": "AFTER_SCHOOL",
              "size": list(SIZE), "renders": []}
    for height in HEIGHTS:
        for amount in AMOUNTS:
            scene, camera = build_scene("AFTER_SCHOOL")
            settings = scene.ald
            settings.clouds_amount = amount
            settings.clouds_height = height
            start = time.perf_counter()
            clouds.create(scene, amount, height)
            build_s = time.perf_counter() - start
            stats = cloud_stats(scene)
            for view in ("final", "oblique"):
                if view == "oblique":
                    oblique_camera(scene)
                name = "h%.2f_a%.2f_%s.png" % (height, amount, view)
                path = os.path.join(OUT, name)
                start = time.perf_counter()
                baseline_fx.render(scene, path)
                render_s = time.perf_counter() - start
                rgb = read_rgb(path)
                delta = np.abs(rgb - references[view]).max(axis=2)
                coverage = float((delta > 0.02).mean())
                report["renders"].append({
                    "height": height, "amount": amount, "view": view,
                    "file": name, "build_s": round(build_s, 4),
                    "render_s": round(render_s, 3),
                    "coverage": round(coverage, 5),
                    **stats,
                })
                print("P0 h=%.2f amount=%.2f %-8s objects=%d polys=%d "
                      "coverage=%.4f build=%.3fs render=%.2fs"
                      % (height, amount, view, stats["objects"],
                         stats["polygons"], coverage, build_s, render_s))
            fx.clear(scene)
            clouds.remove(scene)
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
