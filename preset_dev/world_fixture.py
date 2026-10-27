"""Lifecycle fixture for the World Sky Edition.

A World-only scene is saved and reloaded; a duplicated scene is repaired and
must own a different identity and World. No FX objects are allowed.

Run::

    blender -b --factory-startup --python-exit-code 1 --python preset_dev/world_fixture.py
"""

import os
import sys
import tempfile

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def check(condition, message):
    print("WORLD FIXTURE", "PASS" if condition else "FAIL", message)
    if not condition:
        raise SystemExit(1)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import identity, ownership, palette

    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("World Fixture Camera")
    camera = bpy.data.objects.new("World Fixture Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    scene.ald.palette = "AFTER_SCHOOL"
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.ald.custom_sky = (0.12, 0.2, 0.4)
    palette.sync_custom_colors(scene.ald, palette.preset(scene.ald.palette))
    palette.apply_palette(scene, scene.ald.palette)

    original_id = identity.scene_id(scene)
    original_world = scene.world
    path = os.path.join(tempfile.gettempdir(), "ald_world_fixture.blend")
    scene.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    check(scene.world is not None, "the World survived the reload")
    reloaded_world = scene.world
    from anime_look_director import palette as palette_module
    node = palette_module._gradient_node(scene.world.node_tree)
    check(node is not None, "the World gradient survived the reload")
    check(identity.scene_id(scene) == original_id,
          "the scene identity changed after the reload")
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the reload created an FX object")

    copy = scene.copy()
    copy.use_fake_user = True
    repaired = ownership.repair(copy)
    check(repaired == 1, "the scene copy was not repaired")
    check(identity.scene_id(copy) != identity.scene_id(scene),
          "the copy kept the original identity")
    check(copy.world is not scene.world,
          "the copy still shares the original World")
    palette.apply_palette(copy, "NEON_NIGHT")
    check(scene.world is reloaded_world,
          "the copy changed the original World")
    bpy.data.scenes.remove(copy)
    if os.path.exists(path):
        os.remove(path)
    print("WORLD FIXTURE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
