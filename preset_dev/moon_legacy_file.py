"""Create a 2.63.0 .blend for the Moon migration check.

Run with BLENDER_USER_SCRIPTS pointing at a folder that contains the 2.63.0
package under scripts/addons/anime_look_director.
"""

import math
import os
import sys

import bpy
from mathutils import Vector


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = argv[0] if argv else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "moon", "migration",
        "legacy_263.blend")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable("anime_look_director", default_set=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Legacy Camera")
    data.lens = 85.0
    camera = bpy.data.objects.new("Legacy Camera", data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = Vector((0.0, -1.0, 0.36)).normalized().to_track_quat(
        "-Z", "Y").to_euler()
    scene.camera = camera

    scene.ald.palette = "MOONLIT_NIGHT"
    scene.ald.stars = True
    scene.ald.clouds = False
    scene.ald.sun_disk = False
    scene.ald.sun_glow_enabled = False
    bpy.ops.ald.apply_palette()

    group = bpy.data.node_groups.get("ALD | World Gradient")
    marker = group.get("ald_build") if group is not None else None
    print("LEGACY FILE", out, "build", marker,
          "moon", "Moon Enabled" in {item.name for item in group.interface.items_tree})
    bpy.ops.wm.save_as_mainfile(filepath=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
