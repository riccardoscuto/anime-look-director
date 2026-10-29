"""Render and node-count invariance for the Phase 3 UI cleanup."""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

from anime_look_director import compositor, palette, look  # noqa: E402


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.abspath(argv[0])
    tag = argv[1]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.ald.palette = "NEON_NIGHT"
    scene.ald.clouds = False
    scene.ald.stars = True
    data = bpy.data.cameras.new("UI Invariance Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("UI Invariance Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    palette.apply_palette(scene, "NEON_NIGHT")
    scene.ald.clouds = False
    palette.apply_palette(scene, "NEON_NIGHT")
    path = os.path.join(out, tag + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    group = bpy.data.node_groups.get("ALD | World Gradient")
    world_nodes = len(group.nodes) if group is not None else 0
    compositor.build(scene)
    stack = getattr(compositor, "scene_stack", None)
    stack = stack(scene) if stack is not None else scene.compositing_node_group
    compositor_nodes = len(stack.nodes) if stack is not None else 0
    report = {
        "tag": tag, "image": path, "world_nodes": world_nodes,
        "compositor_nodes": compositor_nodes,
        "world_marker": group.get("ald_build") if group is not None else None,
        "compositor_stack": stack is not None,
        "use_compositing": bool(scene.render.use_compositing),
    }
    with open(os.path.join(out, tag + ".json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("PHASE3 INVARIANCE", json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
