"""Measure the 2.63.0 World baseline for the celestial work.

Renders two presets at three resolutions with clouds, stars and Milky Way
active, and reports node/link/socket counts plus group rebuild and render time.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/celestial_baseline.py -- --out preset_dev/celestial/baseline
"""

import json
import os
import statistics
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402

PRESETS = ("SUMMER_NOON", "MOONLIT_NIGHT")
RESOLUTIONS = ((1280, 720), (1920, 1080), (2560, 1440))


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(HERE, "celestial", "baseline")
    for index, item in enumerate(argv):
        if item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return os.path.abspath(out)


def remove_user_sun(scene):
    for obj in list(scene.objects):
        if obj.type == "LIGHT" and obj.data is not None and obj.data.type == "SUN":
            bpy.data.objects.remove(obj, do_unlink=True)


def group_stats():
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    if group is None:
        return {"nodes": 0, "links": 0, "sockets": 0}
    return {
        "nodes": len(group.nodes),
        "links": len(group.links),
        "sockets": len([item for item in group.interface.items_tree
                        if item.item_type == "SOCKET"]),
    }


def rebuild_time(scene, key):
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)
    start = time.perf_counter()
    palette.apply_palette(scene, key)
    return time.perf_counter() - start


def render_time(scene, path):
    scene.render.filepath = path
    values = []
    for _ in range(2):
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        values.append(time.perf_counter() - start)
    return statistics.median(values)


def main():
    out = parse_args()
    render_dir = os.path.join(out, "renders")
    os.makedirs(render_dir, exist_ok=True)
    lookdev.build_scene()
    lookdev.enable_addon()
    scene = bpy.context.scene
    remove_user_sun(scene)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_percentage = 100
    # JPEG keeps the reference set small enough to open from the repo;
    # the render itself is unaffected and can be reproduced exactly.
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    metrics = {"blender": bpy.app.version_string, "presets": {},
               "resolutions": [list(r) for r in RESOLUTIONS]}
    for key in PRESETS:
        scene.ald.palette = key
        bpy.ops.ald.apply_palette()
        build = rebuild_time(scene, key)
        stats = group_stats()
        entry = {"build_seconds": round(build, 4), **stats, "renders": {}}
        for width, height in RESOLUTIONS:
            scene.render.resolution_x = width
            scene.render.resolution_y = height
            name = "%s_%dx%d.jpg" % (key.lower(), width, height)
            path = os.path.join(render_dir, name)
            entry["renders"]["%dx%d" % (width, height)] = {
                "seconds": round(render_time(scene, path), 3),
                "file": name,
                "bytes": os.path.getsize(path),
            }
        metrics["presets"][key] = entry
        print("CELESTIAL BASELINE", key, json.dumps(entry))
    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print("CELESTIAL BASELINE DONE", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
