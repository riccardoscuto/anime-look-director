"""Headless gate for the World Sky Edition.

Run::

    blender -b --factory-startup --python-exit-code 1 --python preset_dev/verify.py
"""

import os
import sys
import tempfile
import tomllib

import bpy

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_VERSION = (2, 60, 1)


def fail(message):
    print("ALD GATE: FAIL -", message)
    raise SystemExit(1)


def check(condition, message):
    if not condition:
        fail(message)


def enable_addon():
    if hasattr(bpy.context.scene, "ald"):
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module=MODULE)
    check(hasattr(bpy.context.scene, "ald"),
          "the add-on did not register the settings")


def check_versions():
    module = sys.modules.get(MODULE)
    check(module is not None, "add-on module not imported")
    version = tuple(module.bl_info["version"])
    check(version == EXPECTED_VERSION,
          "bl_info version %s != %s" % (version, EXPECTED_VERSION))
    with open(os.path.join(ADDON_PATH, "blender_manifest.toml"), "rb") as handle:
        manifest = tomllib.load(handle)
    check(tuple(int(part) for part in manifest["version"].split(".")) == version,
          "manifest and bl_info versions disagree")


def camera(scene):
    data = bpy.data.cameras.new("ALD World Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    cam = bpy.data.objects.new("ALD World Camera", data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -12.0, 3.0)
    cam.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = cam
    return cam


def gradient(scene):
    from anime_look_director import palette
    return palette._gradient_node(scene.world.node_tree)


def sun(scene):
    return next((obj for obj in scene.objects
                 if obj.type == "LIGHT" and obj.data is not None
                 and obj.data.type == "SUN"), None)


def check_palettes():
    from anime_look_director import palette, properties
    keys = [item[0] for item in properties.PALETTES]
    check(keys and len(keys) == len(set(keys)), "palette identifiers")
    check(set(keys) == set(palette.PRESETS),
          "PALETTES and PRESETS disagree")


def check_world_and_sun(scene):
    from anime_look_director import palette
    scene.ald.palette = "AFTER_SCHOOL"
    bpy.ops.ald.apply_palette()
    check(scene.world is not None, "no World was created")
    check(scene.compositing_node_group is None,
          "applying the World required the compositor")
    node = gradient(scene)
    check(node is not None and node.node_tree is not None,
          "the World gradient group is missing")
    check("Horizon Offset" in node.inputs, "Horizon Offset is missing")
    check("Softness" in node.inputs, "Horizon Softness is missing")
    check("Cloud Amount" in node.inputs, "World clouds are missing")
    check("Star Amount" in node.inputs, "World stars are missing")
    light = sun(scene)
    check(light is not None, "the auto Sun was not created")
    check(light.get("ald_auto_sun"), "the auto Sun is not tagged")
    check(light.get("ald_sun_owner") is not None,
          "the auto Sun has no scene owner")
    first = light.name
    bpy.ops.ald.apply_palette()
    check(sum(1 for obj in scene.objects
              if obj.type == "LIGHT" and obj.data.type == "SUN") == 1,
          "applying the palette created a second Sun")

    palette.apply_sun_angles(scene, 24.0, 35.0)
    toward = palette.sun_toward(scene)
    check(toward is not None, "the Sun has no direction")
    check(abs(light.rotation_euler.x - palette.rotation_from_angles(24, 35)[0])
          < 1e-4, "the elevation was not applied")
    check(light.name == first, "the Sun was replaced by the angle update")

    palette.apply_palette(scene, scene.ald.palette)
    node = gradient(scene)
    check(node.inputs["Sun Strength"].default_value > 0.1,
          "the Sun disk is dark above the horizon")
    palette.apply_sun_angles(scene, -8.0, 35.0)
    palette.apply_palette(scene, scene.ald.palette)
    node = gradient(scene)
    check(node.inputs["Sun Strength"].default_value < 0.01,
          "the Sun disk is visible below the horizon")
    check(node.inputs["Sun Glow"].default_value < 0.1,
          "the Sun glow is too strong below the horizon")


def check_controls(scene):
    from anime_look_director import palette
    s = scene.ald
    node = gradient(scene)
    s.clouds = False
    palette.apply_palette(scene, s.palette)
    node = gradient(scene)
    check(abs(node.inputs["Cloud Amount"].default_value) < 1e-5,
          "Clouds off still renders World clouds")
    s.clouds = True
    s.stars = False
    palette.apply_palette(scene, s.palette)
    node = gradient(scene)
    check(abs(node.inputs["Star Amount"].default_value) < 1e-5,
          "Stars off still renders stars")
    s.stars = True
    s.horizon_offset = 0.35
    palette.apply_palette(scene, s.palette)
    node = gradient(scene)
    check(abs(node.inputs["Horizon Offset"].default_value - 0.35) < 1e-5,
          "Horizon Offset is not wired")
    s.custom_colors = True
    s.custom_sky = (0.1, 0.2, 0.4)
    palette.sync_custom_colors(s, palette.preset(s.palette))
    palette.apply_palette(scene, s.palette)
    node = gradient(scene)
    check(all(abs(a - b) < 1e-4 for a, b in
              zip(node.inputs["Sky Color"].default_value[:3],
                  s.custom_sky)),
          "Custom Sky is not wired")
    s.custom_colors = False
    s.horizon_offset = 0.0
    # Cloud families are real group inputs, one hot.
    for family, socket in (("CUMULUS", "Cloud Cumulus"),
                           ("STRATOCUMULUS", "Cloud Stratocumulus"),
                           ("CIRRUS", "Cloud Cirrus")):
        s.cloud_type = family
        palette.apply_palette(scene, s.palette)
        node = gradient(scene)
        check(abs(node.inputs[socket].default_value - 1.0) < 1e-5,
              "the %s family is not selected" % family)
        check(all(abs(node.inputs[name].default_value) < 1e-5
                  for name in ("Cloud Cumulus", "Cloud Stratocumulus",
                               "Cloud Cirrus") if name != socket),
              "two cloud families are active at once")
    s.cloud_seed = 23
    palette.apply_palette(scene, s.palette)
    offset = tuple(gradient(scene).inputs["Cloud Offset"].default_value)
    s.cloud_seed = 24
    palette.apply_palette(scene, s.palette)
    moved = tuple(gradient(scene).inputs["Cloud Offset"].default_value)
    check(offset != moved, "Cloud Seed does not change the field")
    s.cloud_type = "CUMULUS"
    s.cloud_seed = 17
    palette.apply_palette(scene, s.palette)

    # A controlled shooting star is a World slot, not an object.
    s.shooting_star_events.clear()
    star = s.shooting_star_events.add()
    star.name = "Gate Star"
    star.start_frame = scene.frame_current
    star.duration = 24
    star.brightness = 2.0
    palette.apply_palette(scene, s.palette)
    node = gradient(scene)
    check(node.inputs["Star0 Enabled"].default_value > 0.5,
          "the shooting star slot is not enabled")
    check(node.inputs["Star0 Brightness"].default_value > 0.0,
          "the shooting star has no brightness")
    check(node.inputs["Star0 Duration"].default_value == 24.0,
          "the shooting star duration is not wired")
    s.shooting_star_events.clear()
    palette.apply_palette(scene, s.palette)


def check_effective_palette(scene):
    from anime_look_director import cameras, look, shots
    scene.ald.palette = "SUMMER_NOON"
    scene.ald.use_shot_markers = False
    check(look.effective_palette(scene)[0] == "SUMMER_NOON",
          "base palette precedence")
    scene.ald.use_shot_markers = True
    marker = scene.timeline_markers.new("ALD:NEON_NIGHT",
                                        frame=scene.frame_current)
    check(look.effective_palette(scene)[0] == "NEON_NIGHT",
          "marker palette precedence")
    scene.timeline_markers.remove(marker)
    scene.ald.use_shot_markers = False
    scene.camera.data.ald.override = True
    scene.camera.data.ald.palette = "TWILIGHT_DUSK"
    check(look.effective_palette(scene)[0] == "TWILIGHT_DUSK",
          "camera palette precedence")
    scene.camera.data.ald.override = False
    check(cameras.camera_override(scene) is None,
          "camera override did not clear")


def check_compositor(scene):
    from anime_look_director import compositor
    bpy.ops.ald.build()
    ng = scene.compositing_node_group
    check(ng is not None, "the compositor stack was not assigned")
    check(all(not node.name.startswith("ALD | FX") for node in ng.nodes),
          "the compositor still contains FX nodes")
    check(not any(layer.name.startswith("ALD FX")
                  for layer in scene.view_layers),
          "the compositor still contains FX view layers")
    check(any(node.bl_idname == "NodeGroupOutput" for node in ng.nodes),
          "the compositor has no output")
    bpy.ops.ald.remove()
    check(scene.compositing_node_group is None,
          "the compositor stack was not removed")


def check_no_fx(scene):
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the World created an FX object")
    check(not [coll for coll in bpy.data.collections if coll.get("ald_fx")],
          "the World created an FX collection")
    check(not [coll for coll in bpy.data.collections if coll.get("ald_clouds")],
          "the World created a Spatial Clouds collection")
    check(not [coll for coll in bpy.data.collections if coll.get("ald_smoke")],
          "the World created a smoke collection")


def check_legacy(scene):
    collection = bpy.data.collections.new("ALD Legacy Gate")
    collection["ald_fx"] = True
    scene.collection.children.link(collection)
    mesh = bpy.data.meshes.new("ALD Legacy Gate Mesh")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    mesh.update()
    obj = bpy.data.objects.new("ALD Legacy Gate Object", mesh)
    collection.objects.link(obj)
    bpy.ops.ald.legacy_disable()
    check(collection.hide_render and collection.hide_viewport,
          "legacy disable did not hide the collection")
    bpy.ops.ald.legacy_remove()
    check(bpy.data.collections.get("ALD Legacy Gate") is None,
          "legacy remove did not delete the collection")
    check(bpy.data.objects.get("ALD Legacy Gate Object") is None,
          "legacy remove did not delete the object")


def check_render(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    path = os.path.join(tempfile.gettempdir(), "ald_world_gate.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    check(os.path.exists(path) and os.path.getsize(path) > 0,
          "the World render was not written")
    if os.path.exists(path):
        os.remove(path)


def check_ownership(scene):
    from anime_look_director import materials, ownership, palette
    bpy.ops.ald.apply_palette()
    original_world = scene.world
    copy = scene.copy()
    try:
        repaired = ownership.repair(copy)
        check(repaired == 1, "the copied scene was not repaired")
        check(copy.get("ald_fx_id") != scene.get("ald_fx_id"),
              "the copy kept the original identity")
        check(copy.world is not original_world,
              "the copy still shares the original World")
        color = tuple(copy.world.node_tree.nodes["Background"].inputs[
            "Color"].default_value)
        palette.apply_palette(copy, "NEON_NIGHT")
        check(tuple(scene.world.node_tree.nodes["Background"].inputs[
            "Color"].default_value) == color,
              "a palette on the copy changed the original World")
        material = next((mat for obj in copy.objects
                         if obj.data is not None and hasattr(obj.data, "materials")
                         for mat in obj.data.materials if mat is not None), None)
        if material is not None and materials.material_is_shared(material, copy):
            before = len(material.node_tree.nodes)
            materials.sync_scene(copy, (0.2, 0.3, 0.9), 0.5, 0.5)
            check(len(material.node_tree.nodes) == before,
                  "a shared material was edited from the copy")
        light = sun(scene)
        if light is not None:
            rotation = tuple(light.rotation_euler)
            palette.apply_sun_angles(copy, 30.0, 80.0)
            check(tuple(light.rotation_euler) == rotation,
                  "a shared Sun was rotated from the copy")
    finally:
        bpy.data.scenes.remove(copy)


def check_snapshot(scene):
    from anime_look_director import palette, snapshot
    test = bpy.data.scenes.new("ALD Snapshot Gate")
    try:
        world = bpy.data.worlds.new("ALD Snapshot User World")
        world.use_nodes = True
        background = next(node for node in world.node_tree.nodes
                          if node.bl_idname == "ShaderNodeBackground")
        background.inputs["Color"].default_value = (0.12, 0.2, 0.3, 1.0)
        background.inputs["Strength"].default_value = 2.2
        test.world = world
        snapshot.ensure(test)
        check(snapshot.SNAPSHOT_KEY in test, "the snapshot was not saved")
        palette.apply_palette(test, "NEON_NIGHT")
        check(test.world.name == world.name, "the palette replaced the World")
        check(snapshot.restore(test), "the snapshot restore failed")
        background = next(node for node in test.world.node_tree.nodes
                          if node.bl_idname == "ShaderNodeBackground")
        check(abs(background.inputs["Strength"].default_value - 2.2) < 1e-4,
              "the World strength was not restored")
        check(test.get(snapshot.REMOVED_KEY) is True,
              "the removed state is not reported")
    finally:
        if test.name in bpy.data.scenes:
            bpy.data.scenes.remove(test)
def main():
    enable_addon()
    check_versions()
    scene = bpy.context.scene
    check_palettes()
    camera(scene)
    check_world_and_sun(scene)
    check_controls(scene)
    check_effective_palette(scene)
    check_compositor(scene)
    check_no_fx(scene)
    check_legacy(scene)
    check_render(scene)
    check_ownership(scene)
    check_snapshot(scene)
    print("ALD GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
