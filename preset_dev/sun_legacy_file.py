"""Create and render a 2.63.0 Sun reference for the default-composition test.

Run with BLENDER_USER_SCRIPTS pointing at the 2.63.0 package.
"""

import os
import sys

import bpy
from mathutils import Vector


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out_blend = argv[0]
    out_png = argv[1]
    os.makedirs(os.path.dirname(out_blend), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable("anime_look_director", default_set=True)
    scene = bpy.context.scene
    for obj in list(scene.objects):
        if obj.type == "MESH":
            obj.hide_render = True
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"

    data = bpy.data.cameras.new("Sun Legacy Camera")
    data.lens = 85.0
    camera = bpy.data.objects.new("Sun Legacy Camera", data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = Vector((0.0, -1.0, 0.36)).normalized().to_track_quat(
        "-Z", "Y").to_euler()
    scene.camera = camera

    scene.ald.palette = "GOLDEN_HOUR"
    scene.ald.stars = False
    scene.ald.clouds = False
    scene.ald.sun_disk = True
    scene.ald.sun_glow_enabled = True
    scene.ald.sun_disk_size = 1.0
    scene.ald.sun_disk_strength = 4.0
    scene.ald.sun_glow = 0.5
    scene.ald.sun_elevation = 20.0
    scene.ald.sun_azimuth = 0.0
    bpy.ops.ald.apply_palette()

    group = bpy.data.node_groups.get("ALD | World Gradient")
    print("SUN LEGACY build", group.get("ald_build"), out_blend)
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
