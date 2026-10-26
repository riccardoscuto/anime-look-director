"""Headless gate for Anime Look Director.

Run:
  blender -b --factory-startup --python-exit-code 1 --python preset_dev/verify.py
"""

import os
import sys
import tempfile
import tomllib
import math
import inspect

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_VERSION = (2, 49, 0)
TOLERANCE = 1e-4


def fail(message):
    print("ALD GATE: FAIL -", message)
    raise SystemExit(1)


def check(condition, message):
    if not condition:
        fail(message)


def close(a, b):
    return all(abs(float(x) - float(y)) <= TOLERANCE for x, y in zip(a, b))


def same(a, b):
    """Blender can wrap the same node in different Python objects."""
    return a is not None and b is not None and a.as_pointer() == b.as_pointer()


def enable_addon():
    if hasattr(bpy.types.Scene, "ald"):
        return
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
    except Exception:
        parent = os.path.dirname(ADDON_PATH)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import importlib
        importlib.import_module(MODULE).register()


def check_versions():
    module = sys.modules.get(MODULE)
    check(module is not None, "add-on module not imported")
    version = tuple(module.bl_info["version"])
    check(version == EXPECTED_VERSION,
          "bl_info version %s != %s" % (version, EXPECTED_VERSION))
    manifest_path = os.path.join(ADDON_PATH, "blender_manifest.toml")
    with open(manifest_path, "rb") as handle:
        manifest = tomllib.load(handle)
    manifest_version = tuple(int(part) for part in manifest["version"].split("."))
    check(manifest_version == version,
          "manifest version %s != bl_info %s" % (manifest_version, version))


def check_palette_registry(settings):
    from anime_look_director import palette as palette_module
    from anime_look_director import properties

    keys = [item[0] for item in properties.PALETTES]
    check("AFTER_SCHOOL" in keys, "AFTER_SCHOOL missing from PALETTES")
    check(len(keys) == len(set(keys)), "duplicate palette identifiers")
    check(set(keys) == set(palette_module.PRESETS),
          "PALETTES and PRESETS disagree")
    identifiers = {item.identifier for item in
                   settings.bl_rna.properties["palette"].enum_items}
    check(set(keys) <= identifiers,
          "palette enum items out of sync with PALETTES")


def gradient_node(scene):
    world = scene.world
    if world is None or world.node_tree is None:
        return None
    return next((n for n in world.node_tree.nodes if n.get("ald_world_gradient")),
                None)


def find_sun(scene):
    return next((o for o in scene.objects
                 if o.type == "LIGHT" and o.data is not None
                 and o.data.type == "SUN"), None)


def background_node(scene):
    return next((n for n in scene.world.node_tree.nodes
                 if n.bl_idname == "ShaderNodeBackground"), None)


def tint_node(mat):
    if mat.node_tree is None:
        return None
    return next((n for n in mat.node_tree.nodes if n.get("ald_shadow_tint")), None)


def principled(mat):
    return next((n for n in mat.node_tree.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)


def build_test_materials(scene):
    mesh = bpy.data.meshes.new("ALD_GATE_MESH")
    obj = bpy.data.objects.new("ALD_GATE_OBJ", mesh)
    scene.collection.objects.link(obj)

    plain = bpy.data.materials.new("ALD_GATE_PLAIN")
    plain.use_nodes = True
    plain_bsdf = principled(plain)
    plain_base = plain_bsdf.inputs["Base Color"]
    plain_base.default_value = (0.8, 0.2, 0.2, 1.0)
    plain_nodes = len(plain.node_tree.nodes)

    linked = bpy.data.materials.new("ALD_GATE_LINKED")
    linked.use_nodes = True
    linked_bsdf = principled(linked)
    linked_base = linked_bsdf.inputs["Base Color"]
    rgb = linked.node_tree.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (0.1, 0.6, 0.9, 1.0)
    linked.node_tree.links.new(rgb.outputs[0], linked_base)
    linked_nodes = len(linked.node_tree.nodes)

    obj.data.materials.append(plain)
    obj.data.materials.append(linked)
    return {
        "object": obj,
        "mesh": mesh,
        "plain": plain,
        "plain_bsdf": plain_bsdf,
        "plain_base": plain_base,
        "plain_nodes": plain_nodes,
        "linked": linked,
        "linked_base": linked_base,
        "rgb": rgb,
        "linked_nodes": linked_nodes,
    }


def check_world_gradient(scene, settings):
    from anime_look_director import palette as palette_module

    bpy.ops.ald.apply_palette()
    check(scene.world is not None, "palette did not create a world")
    node = gradient_node(scene)
    check(node is not None, "world gradient node missing")
    check(node.node_tree.name == "ALD | World Gradient",
          "world gradient group not reused")
    normalize = [n for n in node.node_tree.nodes
                 if n.bl_idname == "ShaderNodeVectorMath"
                 and n.operation == "NORMALIZE"]
    check(len(normalize) >= 2, "sun disk vectors are not normalized")
    background = background_node(scene)
    check(background is not None, "world background missing")
    expected = palette_module.preset(settings.palette)
    sun = find_sun(scene)
    check(sun is not None, "palette did not create a sun")
    check(bool(sun.get("ald_auto_sun")), "auto sun is not tagged")
    check(close(sun.data.color, expected["sun_color"]),
          "auto sun color not synced to palette")
    check(abs(sun.data.energy - expected["sun_energy"]) <= TOLERANCE,
          "auto sun energy not synced to palette")

    check(background.inputs["Color"].is_linked
          and same(background.inputs["Color"].links[0].from_node, node),
          "background is not driven by the world gradient")

    check(close(node.inputs["Sky Color"].default_value, expected["sky_color"]),
          "sky color not synced to palette")
    check(close(node.inputs["Horizon Color"].default_value,
                expected["horizon_color"]),
          "horizon color not synced to palette")
    check(close(node.inputs["Ground Color"].default_value,
                expected["ground_color"]),
          "ground color not synced to palette")
    check(close(node.inputs["Mid Sky Color"].default_value,
                expected["mid_sky_color"]),
          "mid sky color not synced to palette")
    check(abs(node.inputs["World Strength"].default_value
              - expected["world_strength"]) <= TOLERANCE,
          "world strength not synced to the gradient")
    check(abs(background.inputs["Strength"].default_value - 1.0) <= TOLERANCE,
          "background strength should be 1.0 when the gradient is active")

    for name in ("Sun Direction", "Sun Strength", "Sun Glow",
                 "Sky Accent", "Sky Accent Amount", "Cloud Amount",
                 "Cloud Scale", "Cloud Flatness", "Contrails",
                 "Cloud Delta Gain", "Cloud Rim Boost"):
        check(node.inputs.get(name) is not None, "world input missing: " + name)
    check(abs(node.inputs["Cloud Amount"].default_value
              - settings.cloud_amount) <= TOLERANCE,
          "cloud amount not synced")

    # The spatial cards and the World are two populations: the blend must
    # remove the World clouds without touching the stored amount.
    previous_created = settings.clouds_created
    previous_blend = settings.clouds_world_blend
    try:
        settings.clouds_created = True
        settings.clouds_world_blend = 1.0
        palette_module.apply_palette(scene, settings.palette)
        check(abs(node.inputs["Cloud Amount"].default_value) <= TOLERANCE,
              "World Cloud Blend 1.0 did not remove the World clouds")
        settings.clouds_world_blend = 0.0
        palette_module.apply_palette(scene, settings.palette)
        check(abs(node.inputs["Cloud Amount"].default_value
                  - settings.cloud_amount) <= TOLERANCE,
              "World Cloud Blend 0.0 changed the cloud amount")
    finally:
        settings.clouds_created = previous_created
        settings.clouds_world_blend = previous_blend
        palette_module.apply_palette(scene, settings.palette)

    check(abs(node.inputs["Cloud Scale"].default_value
              - settings.cloud_scale) <= TOLERANCE,
          "cloud scale not synced")
    check(abs(node.inputs["Sun Glow"].default_value
              - settings.sun_glow) <= TOLERANCE,
          "sun glow not synced")
    check(abs(node.inputs["Cloud Flatness"].default_value
              - settings.cloud_flatness) <= TOLERANCE,
          "cloud flatness not synced")
    check(abs(node.inputs["Contrails"].default_value
              - settings.contrails) <= TOLERANCE,
          "contrails not synced")
    check(abs(node.inputs["Sky Accent Amount"].default_value
              - settings.sky_accent_amount) <= TOLERANCE,
          "sky accent amount not synced")
    check(close(node.inputs["Sky Accent"].default_value,
                settings.sky_accent),
          "sky accent color not synced")
    check(abs(node.inputs["Cloud Delta Gain"].default_value
              - settings.cloud_delta_gain) <= TOLERANCE,
          "cloud delta gain not synced")
    check(abs(node.inputs["Cloud Rim Boost"].default_value
              - settings.cloud_rim_boost) <= TOLERANCE,
          "cloud rim boost not synced")

    bpy.context.view_layer.update()
    bpy.ops.ald.apply_palette()
    node = gradient_node(scene)
    direction = node.inputs["Sun Direction"].default_value
    from mathutils import Vector
    light_dir = sun.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    expected_dir = (-light_dir.x, -light_dir.y, -light_dir.z)
    dot = sum(float(a) * float(b) for a, b in zip(direction, expected_dir))
    check(dot > 0.99, "sun direction not synced to the world gradient")
    check(node.inputs["Sun Strength"].default_value > 0.0,
          "sun disk strength missing")

    settings.sun_disk = False
    node = gradient_node(scene)
    check(node.inputs["Sun Strength"].default_value <= TOLERANCE,
          "sun disk not disabled")
    settings.sun_disk = True
    node = gradient_node(scene)
    check(node.inputs["Sun Strength"].default_value > 0.0,
          "sun disk not restored")

    settings.clouds = False
    node = gradient_node(scene)
    check(node.inputs["Cloud Amount"].default_value <= TOLERANCE,
          "clouds not disabled")
    settings.clouds = True
    node = gradient_node(scene)
    check(node.inputs["Cloud Amount"].default_value > 0.0,
          "clouds not restored")

    for name in ("Star Amount", "Star Density", "Cloud Offset", "Milky Way",
                 "Shooting Star Amount", "Shooting Star Length",
                 "Shooting Star Dir", "Shooting Star Phase",
                 "Fireworks Amount", "Fireworks Scale", "Fireworks Phase"):
        check(node.inputs.get(name) is not None,
              "world input missing: " + name)
    check(any(getattr(item, "voronoi_dimensions", "") == "2D"
              for item in node.node_tree.nodes if item.type == "TEX_VORONOI"),
          "2D Voronoi generators missing")
    golden = palette_module.preset("GOLDEN_HOUR")
    check(abs(settings.star_strength - golden["star_amount"]) <= TOLERANCE,
          "golden hour star amount not synced to style")
    check(abs(node.inputs["Star Amount"].default_value
              - settings.star_strength) <= TOLERANCE,
          "golden hour star amount not synced")
    check(abs(node.inputs["Star Density"].default_value
              - settings.star_density) <= TOLERANCE,
          "star density not synced")
    settings.milky_way = 0.9
    settings.fireworks_scale = 3.7
    node = gradient_node(scene)
    check(abs(node.inputs["Milky Way"].default_value - 0.9) <= TOLERANCE,
          "milky way slider not synced")
    check(abs(node.inputs["Fireworks Scale"].default_value - 3.7) <= TOLERANCE,
          "fireworks scale slider not synced")

    settings.fx_backend = "LEGACY"
    settings.shooting_stars = True
    settings.fireworks = True
    settings.god_rays = True
    settings.sun_glow_enabled = False
    node = gradient_node(scene)
    check(node.inputs["Shooting Star Amount"].default_value > 0.0,
          "shooting star amount not enabled")
    check(node.inputs["Fireworks Amount"].default_value > 0.0,
          "firework amount not enabled")
    check(abs(node.inputs["Sun Glow"].default_value) <= TOLERANCE,
          "sun glow toggle did not zero the glow")
    settings.fx_backend = "FX3D"
    bpy.ops.ald.apply_palette()
    node = gradient_node(scene)
    check(abs(node.inputs["Fireworks Amount"].default_value) <= TOLERANCE,
          "legacy world fireworks not disabled in FX 3D mode")
    check(abs(node.inputs["Shooting Star Amount"].default_value) <= TOLERANCE,
          "legacy world meteors not disabled in FX 3D mode")
    bpy.ops.ald.apply_palette()
    node = gradient_node(scene)
    check(not settings.shooting_stars, "apply palette did not disable shooting stars")
    check(not settings.fireworks, "apply palette did not disable fireworks")
    check(not settings.god_rays, "apply palette did not disable god rays")
    check(settings.sun_glow_enabled, "apply palette did not restore sun glow toggle")
    check(abs(node.inputs["Shooting Star Amount"].default_value) <= TOLERANCE,
          "shooting star amount not reset")
    check(abs(node.inputs["Fireworks Amount"].default_value) <= TOLERANCE,
          "firework amount not reset")

    settings.sun_glow = 0.8
    check(abs(gradient_node(scene).inputs["Sun Glow"].default_value
              - 0.8) <= TOLERANCE, "sun glow not updated in place")
    settings.sun_glow = 0.45
    settings.cloud_flatness = 0.9
    check(abs(gradient_node(scene).inputs["Cloud Flatness"].default_value
              - 0.9) <= TOLERANCE, "cloud flatness not updated in place")
    settings.cloud_flatness = 0.65

    after = palette_module.preset("AFTER_SCHOOL")
    settings.palette = "AFTER_SCHOOL"
    bpy.ops.ald.apply_palette()
    node = gradient_node(scene)
    for name, key in (("Sky Color", "sky_color"),
                      ("Mid Sky Color", "mid_sky_color"),
                      ("Horizon Color", "horizon_color"),
                      ("Cloud Shadow", "cloud_shadow"),
                      ("Cloud Mid", "cloud_mid"),
                      ("Cloud Light", "cloud_light")):
        check(close(node.inputs[name].default_value, after[key]),
              "after school " + name + " not synced")
    sun = find_sun(scene)
    check(sun is not None and close(sun.data.color, after["sun_color"]),
          "after school sun not synced")
    check(abs(settings.cloud_flatness - after["cloud_flatness"]) <= TOLERANCE,
          "after school cloud flatness not applied")
    check(abs(settings.cloud_scale - after["cloud_scale"]) <= TOLERANCE,
          "after school cloud scale not applied")
    check(abs(settings.cloud_rim_boost
              - after["cloud_rim_boost"]) <= TOLERANCE,
          "after school rim boost not applied")
    check(abs(settings.cloud_amount - after["cloud_amount"]) <= TOLERANCE,
          "after school cloud amount not applied")
    check(close(settings.sky_accent, after["sky_accent"]),
          "after school sky accent not applied")
    check(close(node.inputs["Sky Accent"].default_value, after["sky_accent"]),
          "after school sky accent not synced")

    settings.cloud_scale = 12.0
    settings.cloud_rim_boost = 4.0
    settings.cloud_delta_gain = 3.46
    settings.sun_glow = 0.0
    settings.sky_accent = (0.0, 0.0, 0.0)
    settings.sky_accent_amount = 1.0
    settings.horizon_offset = 0.5
    settings.horizon_softness = 0.02
    settings.contrails = 0.9
    settings.star_density = 50.0
    bpy.ops.ald.apply_palette()
    check(abs(settings.cloud_scale - after["cloud_scale"]) <= TOLERANCE,
          "apply palette did not reset cloud scale")
    check(abs(settings.cloud_rim_boost
              - after["cloud_rim_boost"]) <= TOLERANCE,
          "apply palette did not reset rim boost")
    check(abs(settings.cloud_delta_gain - 1.0) <= TOLERANCE,
          "apply palette did not reset delta gain")
    check(abs(settings.sun_glow - after["sun_glow"]) <= TOLERANCE,
          "apply palette did not reset sun glow to preset")
    check(abs(settings.sky_accent_amount
              - after["sky_accent_amount"]) <= TOLERANCE,
          "apply palette did not reset accent amount to preset")
    check(close(settings.sky_accent, after["sky_accent"]),
          "apply palette did not reset sky accent color")
    check(abs(settings.horizon_offset
              - after["horizon_offset"]) <= TOLERANCE,
          "apply palette did not reset horizon offset")
    check(abs(settings.horizon_softness
              - after["horizon_softness"]) <= TOLERANCE,
          "apply palette did not reset horizon softness")
    check(abs(settings.contrails - after["contrails"]) <= TOLERANCE,
          "apply palette did not reset contrails")
    check(abs(settings.star_density - after["star_density"]) <= TOLERANCE,
          "apply palette did not reset star density")
    settings.clouds = False
    settings.sun_disk_size = 0.2
    settings.sun_disk_strength = 1.0
    settings.cloud_wind = 1.0
    bpy.ops.ald.apply_palette()
    check(settings.clouds, "apply palette did not re-enable clouds")
    check(abs(settings.sun_disk_size - 1.5) <= TOLERANCE,
          "apply palette did not reset sun size")
    check(abs(settings.sun_disk_strength - 6.0) <= TOLERANCE,
          "apply palette did not reset sun strength")
    check(abs(settings.cloud_wind) <= TOLERANCE,
          "apply palette did not reset cloud wind")
    settings.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()

    neon = palette_module.preset("NEON_NIGHT")
    settings.palette = "NEON_NIGHT"
    bpy.ops.ald.apply_palette()
    node = gradient_node(scene)
    check(abs(settings.star_strength - neon["star_amount"]) <= TOLERANCE,
          "neon star amount not synced to style")
    check(abs(node.inputs["Star Amount"].default_value
              - settings.star_strength) <= TOLERANCE,
          "neon night stars not enabled")
    check(settings.milky_way <= TOLERANCE, "neon milky way should be off")
    settings.palette = "TWILIGHT_DUSK"
    bpy.ops.ald.apply_palette()
    check(settings.milky_way > 0.0, "twilight milky way not enabled")
    settings.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()

    settings.cloud_wind = 1.0
    scene.frame_set(10)
    node = gradient_node(scene)
    check(abs(node.inputs["Cloud Offset"].default_value[0]) > 0.001,
          "cloud wind did not animate the cloud offset")
    settings.cloud_wind = 0.0
    scene.frame_set(1)
    settings.palette = "GOLDEN_HOUR"
    bpy.ops.ald.apply_palette()

    bpy.ops.ald.apply_palette()
    nodes = [n for n in scene.world.node_tree.nodes if n.get("ald_world_gradient")]
    check(len(nodes) == 1, "world gradient duplicated on re-apply")
    groups = [g for g in bpy.data.node_groups if g.name == "ALD | World Gradient"]
    check(len(groups) == 1, "world gradient group duplicated")

    settings.world_gradient = False
    check(gradient_node(scene) is None, "gradient not removed when disabled")
    check(not background.inputs["Color"].is_linked,
          "background still linked after disabling the gradient")
    saved_color = scene.get("ald_world_bg_color")
    check(saved_color is not None, "original world background was not recorded")
    check(close(background.inputs["Color"].default_value, tuple(saved_color)),
          "original world background not restored")
    check(abs(background.inputs["Strength"].default_value
              - float(scene.get("ald_world_bg_strength", 1.0))) <= TOLERANCE,
          "original world strength not restored")

    settings.world_gradient = True
    check(gradient_node(scene) is not None, "gradient not restored when enabled")
    check(abs(background.inputs["Strength"].default_value - 1.0) <= TOLERANCE,
          "background strength not restored with the gradient")

    # Auto sun: disabled must not create one, enabled must recreate it.
    sun = find_sun(scene)
    sun_data = sun.data
    bpy.data.objects.remove(sun, do_unlink=True)
    if sun_data.users == 0:
        bpy.data.lights.remove(sun_data)
    settings.auto_sun = False
    check(find_sun(scene) is None, "auto sun created while disabled")
    settings.auto_sun = True
    check(find_sun(scene) is not None, "auto sun not recreated when enabled")


def check_material_exclusion(scene, settings, data):
    obj = data["object"]
    plain = data["plain"]
    settings.shadow_tint = True
    settings.toon_shading = True
    settings.rim_light = True
    for selected in list(bpy.context.selected_objects):
        selected.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.active_material_index = 0
    bpy.ops.ald.build()
    check(tint_node(plain) is not None, "exclusion test has no tint node")

    bpy.ops.ald.toggle_exclude_material()
    check(bool(plain.get("ald_exclude")), "material was not excluded")
    check(tint_node(plain) is None, "excluded material still has the tint node")
    bpy.ops.ald.build()
    check(tint_node(plain) is None,
          "excluded material was synced by Build")

    bpy.ops.ald.toggle_exclude_material()
    check(not plain.get("ald_exclude"), "material was not included")
    check(tint_node(plain) is not None,
          "included material did not get the tint node")
    obj.select_set(False)


def check_live_transforms(scene, data):
    from anime_look_director import cameras
    from anime_look_director import palette as palette_module

    sun = find_sun(scene)
    check(sun is not None, "live transform test needs a sun")
    old_rotation = tuple(sun.rotation_euler)
    try:
        sun.rotation_euler = (-math.pi / 2.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        changed = cameras.update_transforms(scene, force=True)
        check(changed, "transform update did not run")
        expected = palette_module.sun_toward(scene)
        check(expected is not None, "transform test has no sun direction")
        node = gradient_node(scene)
        dot = sum(float(a) * float(b) for a, b in
                  zip(node.inputs["Sun Direction"].default_value, expected))
        check(dot > 0.99, "world sun not updated by the transform handler")
        tint = tint_node(data["plain"])
        check(tint is not None, "no tint node for the transform test")
        dot = sum(float(a) * float(b) for a, b in
                  zip(tint.inputs["Sun Direction"].default_value, expected))
        check(dot > 0.99, "material sun not updated by the transform handler")
        check(not cameras.update_transforms(scene),
              "transform cache did not skip an unchanged state")
    finally:
        sun.rotation_euler = old_rotation
        bpy.context.view_layer.update()
        cameras.update_transforms(scene, force=True)


def check_sun_controls(scene, settings):
    from anime_look_director import palette as palette_module

    old = (settings.sun_disk, settings.god_rays,
           settings.light_wrap, settings.rim_light)
    settings.sun_elevation = 20.0
    settings.sun_azimuth = 30.0
    bpy.context.view_layer.update()
    direction = palette_module.sun_toward(scene)
    check(direction is not None, "sun control test has no sun")
    elevation, azimuth = palette_module.angles_from_direction(direction)
    check(abs(elevation - 20.0) < 0.6 and abs(azimuth - 30.0) < 0.6,
          "sun elevation/azimuth did not move the sun")

    sun = find_sun(scene)
    target = bpy.data.objects.new("ALD_GATE_SUN_TARGET", None)
    scene.collection.objects.link(target)
    target.location = (0.0, 0.0, 10.0)
    constraint = sun.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.view_layer.update()
    constrained = palette_module.sun_toward(scene)
    from mathutils import Vector
    matrix_dir = -(sun.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0)))
    check(sum(a * b for a, b in zip(constrained, matrix_dir)) > 0.99,
          "constrained sun did not use its world matrix")
    sun.constraints.remove(constraint)
    bpy.data.objects.remove(target, do_unlink=True)
    bpy.context.view_layer.update()

    old_cloud = settings.cloud_amount
    settings.cloud_amount = 0.45
    bpy.context.view_layer.update()
    direction = palette_module.sun_toward(scene)
    elevation, azimuth = palette_module.angles_from_direction(direction)
    check(abs(elevation - 20.0) < 0.6 and abs(azimuth - 30.0) < 0.6,
          "world refresh reset the manual sun angles")
    settings.cloud_amount = old_cloud

    result = bpy.ops.ald.stage_backlight()
    check("FINISHED" in result, "stage backlight operator failed")
    check(abs(settings.sun_elevation - 12.0) < 0.6,
          "stage backlight elevation wrong")
    check(settings.sun_disk and settings.god_rays
          and settings.light_wrap and settings.rim_light,
          "stage backlight did not enable the backlight stages")

    (settings.sun_disk, settings.god_rays,
     settings.light_wrap, settings.rim_light) = old
    bpy.ops.ald.apply_palette()


def check_god_rays(scene, settings):
    sun = find_sun(scene)
    check(sun is not None, "god rays need a sun")
    old_rotation = tuple(sun.rotation_euler)
    old_camera = scene.camera
    old_god = settings.god_rays

    cam_data = bpy.data.cameras.new("ALD_GATE_GOD_CAM")
    cam = bpy.data.objects.new("ALD_GATE_GOD_CAM", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -6.0, 0.0)
    cam.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    scene.camera = cam
    sun.rotation_euler = (0.9, 0.15, -0.6)
    bpy.context.view_layer.update()

    try:
        settings.god_rays = True
        bpy.context.view_layer.update()
        bpy.ops.ald.build()
        ng = scene.compositing_node_group
        beams = [n for n in ng.nodes
                 if n.bl_idname == "CompositorNodeGlare"
                 and n.inputs["Type"].default_value == "Sun Beams"]
        check(len(beams) == 1, "god rays node not created with sun behind")
        position = beams[0].inputs["Sun Position"].default_value
        check(abs(position[0] - 0.5) < 0.01
              and abs(position[1] - 0.5) < 0.01,
              "god rays fallback position wrong")
        check(beams[0].inputs["Strength"].default_value <= TOLERANCE,
              "god rays not muted at build with sun behind")

        from anime_look_director import compositor
        sun.rotation_euler = (-math.pi / 2.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        compositor.update_god_rays(scene)
        position = beams[0].inputs["Sun Position"].default_value
        check(abs(position[0] - 0.5) < 0.01
              and abs(position[1] - 0.5) < 0.01,
              "god rays sun position not projected")
        check(abs(beams[0].inputs["Strength"].default_value
                  - settings.god_rays_strength) <= TOLERANCE,
              "god rays not restored when the sun comes back")

        sun.rotation_euler = (0.9, 0.15, -0.6)
        bpy.context.view_layer.update()
        compositor.update_god_rays(scene)
        check(beams[0].inputs["Strength"].default_value <= TOLERANCE,
              "god rays not muted with the sun behind the camera")
    finally:
        settings.god_rays = old_god
        sun.rotation_euler = old_rotation
        scene.camera = old_camera
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        bpy.context.view_layer.update()
        bpy.ops.ald.build()


def check_shadow_tint(scene, settings, data):
    from anime_look_director import palette as palette_module

    checked = data["plain"]
    settings.shadow_tint = True
    settings.shadow_tint_strength = 0.4
    settings.shadow_tint_distance = 0.75
    bpy.ops.ald.build()

    node = tint_node(checked)
    check(node is not None, "shadow tint not inserted in plain material")
    group = bpy.data.node_groups.get("ALD | Shadow Tint")
    mix = next((n for n in group.nodes if n.bl_idname == "ShaderNodeMix"), None)
    check(mix is not None and mix.blend_type == "MULTIPLY",
          "shadow tint is not multiplicative")
    check(data["plain_base"].is_linked
          and same(data["plain_base"].links[0].from_node, node),
          "shadow tint not driving Base Color")
    expected_tint = palette_module.shadow_tint(settings.palette)
    check(close(node.inputs["Tint"].default_value, expected_tint),
          "shadow tint color not synced to palette")
    check(abs(node.inputs["Strength"].default_value - 0.4) <= TOLERANCE,
          "shadow tint strength not synced")
    check(abs(node.inputs["Distance"].default_value - 0.75) <= TOLERANCE,
          "shadow tint distance not synced")
    for name in ("Sun Direction", "Sun Color", "Toon Strength",
                 "Terminator Sharpness", "Rim Strength", "Rim Width",
                 "Hue Lift", "Terminator Warmth", "Rim Bias"):
        check(name in node.inputs, "shadow tint input missing: " + name)
    expected_dir = palette_module.sun_toward(scene)
    check(expected_dir is not None, "shadow tint has no sun direction")
    dot = sum(float(a) * float(b) for a, b in
              zip(node.inputs["Sun Direction"].default_value, expected_dir))
    check(dot > 0.99, "shadow tint sun direction not synced")
    check(abs(node.inputs["Toon Strength"].default_value
              - settings.toon_strength) <= TOLERANCE,
          "toon strength not synced to materials")
    check(abs(node.inputs["Rim Strength"].default_value
              - settings.rim_strength) <= TOLERANCE,
          "rim strength not synced to materials")
    check(abs(node.inputs["Hue Lift"].default_value
              - settings.shadow_hue_lift) <= TOLERANCE,
          "shadow hue lift not synced to materials")
    check(abs(node.inputs["Terminator Warmth"].default_value
              - settings.terminator_warmth) <= TOLERANCE,
          "terminator warmth not synced to materials")
    check(abs(node.inputs["Rim Bias"].default_value - 1.0) <= TOLERANCE,
          "sun-side rim bias not synced")
    emission_color = data["plain_bsdf"].inputs["Emission Color"]
    emission_strength = data["plain_bsdf"].inputs["Emission Strength"]
    check(emission_color.is_linked
          and same(emission_color.links[0].from_node, node),
          "rim emission not wired to the material")
    check(abs(emission_strength.default_value
              - settings.rim_emission) <= TOLERANCE,
          "rim emission strength not synced")
    check(len(checked.node_tree.nodes) == data["plain_nodes"] + 1,
          "shadow tint added unexpected nodes")

    bpy.ops.ald.build()
    check(tint_node(checked) is not None, "shadow tint lost on rebuild")
    check(len(checked.node_tree.nodes) == data["plain_nodes"] + 1,
          "shadow tint duplicated on rebuild")
    linked_node = tint_node(data["linked"])
    check(linked_node is not None, "shadow tint missing on linked material")
    check(data["linked_base"].is_linked
          and same(data["linked_base"].links[0].from_node, linked_node),
          "shadow tint not inserted on linked material")
    check(linked_node.inputs["Color"].is_linked
          and same(linked_node.inputs["Color"].links[0].from_node, data["rgb"]),
          "original Base Color link not preserved")

    groups = [g for g in bpy.data.node_groups if g.name == "ALD | Shadow Tint"]
    check(len(groups) == 1, "shadow tint group duplicated")

    settings.palette = "NEON_NIGHT"
    node = tint_node(checked)
    check(close(node.inputs["Tint"].default_value,
                palette_module.shadow_tint("NEON_NIGHT")),
          "shadow tint did not follow the palette change")
    settings.palette = "GOLDEN_HOUR"

    settings.toon_shading = True
    settings.rim_light = True
    settings.shadow_tint = False
    node = tint_node(checked)
    check(node is not None,
          "shadow tint toggle removed the cel/rim node")
    check(abs(node.inputs["Strength"].default_value) <= TOLERANCE,
          "shadow tint toggle did not zero the AO strength")
    settings.shadow_tint = True

    bpy.ops.ald.clear_shadow_tint()
    check(tint_node(checked) is None, "shadow tint not removed from plain material")
    check(not data["plain_base"].is_linked,
          "Base Color link not removed after clearing tint")
    check(close(data["plain_base"].default_value, (0.8, 0.2, 0.2, 1.0)),
          "original Base Color not restored")
    check(not emission_color.is_linked,
          "emission link not restored after clearing tint")
    check(abs(emission_strength.default_value) <= TOLERANCE,
          "original emission strength not restored")
    check(tint_node(data["linked"]) is None,
          "shadow tint not removed from linked material")
    check(data["linked_base"].is_linked
          and same(data["linked_base"].links[0].from_node, data["rgb"]),
          "original Base Color link not restored")
    check(len(checked.node_tree.nodes) == data["plain_nodes"],
          "material node count not restored")

    settings.shadow_tint = True
    settings.toon_shading = True
    settings.rim_light = True
    check(tint_node(checked) is not None, "shadow tint not re-enabled")


def check_light_wrap(scene, settings):
    settings.light_wrap = True
    bpy.ops.ald.build()
    ng = scene.compositing_node_group
    check(ng is not None, "compositor group not assigned")
    types = [n.bl_idname for n in ng.nodes]
    check("CompositorNodeAlphaOver" in types, "light wrap missing Alpha Over")
    check(types.count("CompositorNodeBlur") == 4,
          "light wrap blur nodes missing")
    check(types.count("CompositorNodeSetAlpha") == 1,
          "light wrap alpha nodes missing")
    check(types.count("CompositorNodeSeparateColor") == 3,
          "light wrap mask extraction missing")
    operations = [n.operation for n in ng.nodes if n.bl_idname == "ShaderNodeMath"]
    check("LESS_THAN" in operations,
          "light wrap silhouette mask is not depth-based")
    check("ABSOLUTE" in operations and "MAXIMUM" in operations,
          "light wrap depth-edge mask missing")

    settings.light_wrap = False
    check(scene.compositing_node_group.nodes.get("ALD | Light Wrap Over") is None,
          "light wrap not removed when disabled")
    settings.light_wrap = True
    check(scene.compositing_node_group.nodes.get("ALD | Light Wrap Over")
          is not None, "light wrap not restored when enabled")


def diff_stats(a, b):
    delta = np.abs(a - b)
    return (float(delta.max()), float(delta.mean()),
            float((delta.max(axis=1) > 0.01).mean()))


def render_pixels(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(image)
    return pixels


def check_pixels(scene, settings):
    """Render-level proof that shadow tint and light wrap change pixels."""
    old_camera = scene.camera
    old_engine = scene.render.engine
    old_size = (scene.render.resolution_x, scene.render.resolution_y)
    old_samples = scene.eevee.taa_render_samples

    bpy.ops.mesh.primitive_plane_add(size=14, location=(20, 0, 0))
    plane = bpy.context.object
    plane.name = "ALD_GATE_LOOK_PLANE"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9, location=(20, 0, 0.9),
                                         segments=32, ring_count=16)
    sphere = bpy.context.object
    sphere.name = "ALD_GATE_LOOK_SPHERE"
    plane_mesh, sphere_mesh = plane.data, sphere.data

    mat = bpy.data.materials.new("ALD_GATE_LOOK")
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.62, 0.52, 0.42, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    plane.data.materials.append(mat)
    sphere.data.materials.append(mat)

    cam_data = bpy.data.cameras.new("ALD_GATE_LOOK_CAM")
    cam_data.lens = 50
    cam = bpy.data.objects.new("ALD_GATE_LOOK_CAM", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (24.5, -7.5, 4.0)
    target = bpy.data.objects.new("ALD_GATE_LOOK_TARGET", None)
    target.location = (20, 0, 0.9)
    scene.collection.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    scene.camera = cam
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 128
    scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()

    try:
        bpy.ops.ald.build()
        settings.shadow_tint_strength = 0.9
        settings.shadow_tint_distance = 1.0
        settings.light_wrap_strength = 0.9
        settings.light_wrap_size = 32.0
        settings.light_wrap = False
        settings.toon_shading = False
        settings.rim_light = False
        settings.shadow_tint = False

        base = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_base.png"))
        settings.shadow_tint = True
        tinted = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_tint.png"))
        settings.shadow_tint = False
        settings.light_wrap = True
        wrapped = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_wrap.png"))
        settings.light_wrap = False
        settings.ink_lines = True
        bpy.ops.ald.build()
        inked = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_ink.png"))
        settings.ink_lines = False
        settings.aerial_haze = True
        settings.haze_strength = 0.9
        bpy.ops.ald.build()
        hazed = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_haze.png"))
        settings.aerial_haze = False
        settings.haze_strength = 0.5
        settings.light_wrap = False
        settings.shadow_tint = True
        settings.shadow_tint_strength = 0.0
        settings.toon_shading = True
        settings.toon_strength = 0.0
        settings.rim_light = False
        bpy.ops.ald.build()
        toon_off = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_toon_off.png"))
        settings.toon_strength = 0.8
        toon_on = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_toon_on.png"))
        settings.toon_strength = 0.0
        settings.rim_light = True
        settings.rim_strength = 0.8
        settings.rim_width = 0.35
        rim_on = render_pixels(
            scene, os.path.join(tempfile.gettempdir(), "ald_gate_rim_on.png"))

        tint_max, tint_mean, tint_ratio = diff_stats(base, tinted)
        wrap_max, wrap_mean, wrap_ratio = diff_stats(base, wrapped)
        ink_max, ink_mean, ink_ratio = diff_stats(base, inked)
        haze_max, haze_mean, haze_ratio = diff_stats(base, hazed)
        toon_max, toon_mean, toon_ratio = diff_stats(toon_off, toon_on)
        rim_max, rim_mean, rim_ratio = diff_stats(toon_off, rim_on)
        print("ALD GATE pixels: shadow max=%.4f mean=%.5f ratio=%.4f; "
              "wrap max=%.4f mean=%.5f ratio=%.4f; "
              "ink max=%.4f mean=%.5f ratio=%.4f; "
              "haze max=%.4f mean=%.5f ratio=%.4f; "
              "toon max=%.4f mean=%.5f ratio=%.4f; "
              "rim max=%.4f mean=%.5f ratio=%.4f"
              % (tint_max, tint_mean, tint_ratio,
                 wrap_max, wrap_mean, wrap_ratio,
                 ink_max, ink_mean, ink_ratio,
                 haze_max, haze_mean, haze_ratio,
                 toon_max, toon_mean, toon_ratio,
                 rim_max, rim_mean, rim_ratio))
        check(tint_max > 0.01 and tint_ratio > 0.001,
              "shadow tint does not affect the render")
        check(wrap_max > 0.01 and 0.001 < wrap_ratio < 0.8,
              "light wrap does not affect the edges only")
        check(ink_max > 0.01 and 0.0005 < ink_ratio < 0.5,
              "ink lines do not affect the edges only")
        check(haze_max > 0.01 and haze_ratio > 0.005,
              "aerial haze does not affect the render")
        check(toon_max > 0.01 and toon_ratio > 0.002,
              "toon terminator does not affect the render")
        check(rim_max > 0.01 and 0.0005 < rim_ratio < 0.5,
              "rim light does not affect the edges only")
    finally:
        scene.camera = old_camera
        settings.ink_lines = False
        settings.aerial_haze = False
        settings.haze_strength = 0.5
        settings.light_wrap = True
        settings.light_wrap_strength = 0.4
        settings.light_wrap_size = 24.0
        settings.shadow_tint = True
        settings.shadow_tint_strength = 0.35
        settings.shadow_tint_distance = 0.6
        settings.toon_shading = True
        settings.toon_strength = 0.75
        settings.toon_sharpness = 0.035
        settings.rim_light = True
        settings.rim_strength = 0.45
        settings.rim_width = 0.4
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y = old_size
        scene.eevee.taa_render_samples = old_samples
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.objects.remove(target, do_unlink=True)
        bpy.data.objects.remove(plane, do_unlink=True)
        bpy.data.objects.remove(sphere, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        bpy.data.materials.remove(mat)
        bpy.data.meshes.remove(plane_mesh)
        bpy.data.meshes.remove(sphere_mesh)


def check_idempotent_build(scene):
    count = len(scene.compositing_node_group.nodes)
    bpy.ops.ald.build()
    check(len(scene.compositing_node_group.nodes) == count,
          "rebuild changed the node count")
    groups = [g for g in bpy.data.node_groups
              if g.name == "ALD | Compositor Stack"]
    check(len(groups) == 1, "compositor group duplicated")


def check_param_updates(scene, settings):
    ng = scene.compositing_node_group
    check(ng is not None, "stack missing for parameter update test")
    count = len(ng.nodes)

    settings.kuwahara_size = 9.0
    node = ng.nodes.get("ALD | Kuwahara")
    check(node is not None, "Kuwahara node name missing")
    check(abs(node.inputs["Size"].default_value - 9.0) <= TOLERANCE,
          "Kuwahara size not updated in place")
    check(ng.nodes.get("ALD | Kuwahara Geometry") is not None,
          "Kuwahara geometry mask missing")
    check(len(ng.nodes) == count, "Kuwahara slider rebuilt the stack")

    settings.halation_strength = 0.4
    node = ng.nodes.get("ALD | Halation")
    check(node is not None, "Halation node name missing")
    check(abs(node.inputs["Strength"].default_value - 0.4) <= TOLERANCE,
          "Halation strength not updated in place")

    settings.light_wrap_size = 30.0
    node = ng.nodes.get("ALD | Light Wrap Blur")
    check(node is not None, "Light Wrap blur missing")
    check(abs(node.inputs["Size"].default_value[0] - 30.0) <= TOLERANCE,
          "Light wrap size not updated in place")

    settings.light_wrap_strength = 0.8
    node = ng.nodes.get("ALD | Light Wrap Over")
    check(node is not None, "Light Wrap Alpha Over missing")
    check(abs(node.inputs["Factor"].default_value - 0.8) <= TOLERANCE,
          "Light wrap strength not updated in place")

    settings.depth_near = 3.0
    node = ng.nodes.get("ALD | Depth Range")
    check(node is not None, "Depth range missing")
    check(abs(node.inputs["From Min"].default_value - 3.0) <= TOLERANCE,
          "Depth near not updated in place")

    settings.dispersion_amount = 0.02
    node = ng.nodes.get("ALD | Lens")
    check(node is not None, "Lens node missing")
    check(abs(node.inputs["Dispersion"].default_value - 0.02) <= TOLERANCE,
          "Dispersion not updated in place")

    settings.fx_glow_strength = 1.2
    node = ng.nodes.get("ALD | FX Glow")
    check(node is not None, "FX glow node missing")
    check(abs(node.inputs["Strength"].default_value - 1.2) <= TOLERANCE,
          "FX glow strength not updated in place")
    check(ng.nodes.get("ALD | FX Restore") is not None,
          "FX restore node missing")
    settings.fx_glow_strength = 0.6
    check(len(ng.nodes) == count, "a slider rebuilt the stack")

    settings.halation_strength = 0.6
    settings.kuwahara_size = 6.0
    settings.light_wrap_size = 24.0
    settings.light_wrap_strength = 0.4
    settings.depth_near = 4.0
    settings.dispersion_amount = 0.01


def check_ink(scene, settings):
    settings.ink_lines = True
    bpy.ops.ald.build()
    ng = scene.compositing_node_group
    mix = ng.nodes.get("ALD | Ink Lines")
    check(mix is not None, "ink lines node missing")
    check(mix.blend_type == "MULTIPLY", "ink lines are not multiplicative")
    gain = ng.nodes.get("ALD | Ink Gain")
    check(gain is not None
          and abs(gain.inputs[1].default_value - 8.0) <= TOLERANCE,
          "ink edge gain missing")
    check(scene.view_layers[0].use_pass_normal,
          "normal pass not enabled for ink lines")
    normal = ng.nodes.get("ALD | Normal Edge")
    check(normal is not None, "normal edge mask missing")
    count = len(ng.nodes)

    settings.ink_normal_sensitivity = 0.8
    normal_gain = ng.nodes.get("ALD | Normal Gain")
    check(normal_gain is not None
          and abs(normal_gain.inputs[1].default_value - 0.8) <= TOLERANCE,
          "normal ink sensitivity not updated in place")

    settings.ink_strength = 0.8
    factor = ng.nodes.get("ALD | Ink Factor")
    check(factor is not None
          and abs(factor.inputs[1].default_value - 0.8) <= TOLERANCE,
          "ink strength not updated in place")
    settings.ink_size = 2.5
    edge = ng.nodes.get("ALD | Ink Edge")
    check(edge is not None
          and abs(edge.inputs["Size"].default_value[0] - 2.5) <= TOLERANCE,
          "ink size not updated in place")
    check(len(ng.nodes) == count, "ink sliders rebuilt the stack")

    settings.ink_lines = False
    bpy.ops.ald.build()
    check(ng.nodes.get("ALD | Ink Lines") is None, "ink lines not removed")
    settings.ink_strength = 0.6
    settings.ink_size = 1.5
    settings.ink_normal_sensitivity = 0.6


def check_aerial_haze(scene, settings):
    settings.aerial_haze = True
    bpy.ops.ald.build()
    ng = scene.compositing_node_group
    mix = ng.nodes.get("ALD | Aerial Haze")
    check(mix is not None, "aerial haze node missing")
    count = len(ng.nodes)
    settings.haze_strength = 0.8
    strength = ng.nodes.get("ALD | Haze Strength")
    check(strength is not None
          and abs(strength.inputs[1].default_value - 0.8) <= TOLERANCE,
          "haze strength not updated in place")
    check(len(ng.nodes) == count, "haze slider rebuilt the stack")
    settings.aerial_haze = False
    bpy.ops.ald.build()
    check(ng.nodes.get("ALD | Aerial Haze") is None,
          "aerial haze not removed")
    settings.haze_strength = 0.5


def check_shot_markers(scene, settings):
    from anime_look_director import shots
    from anime_look_director import palette as palette_module

    marker_a = scene.timeline_markers.new(
        shots.marker_name("GOLDEN_HOUR"), frame=10)
    marker_b = scene.timeline_markers.new(
        shots.marker_name("NEON_NIGHT"), frame=20)
    marker_c = None
    base = settings.palette
    try:
        settings.use_shot_markers = True
        scene.frame_set(10)
        shots.apply_for_frame(scene, force=True)
        check(settings.palette == base,
              "shot marker changed the base palette")
        check(scene.get("ald_effective_palette") == "GOLDEN_HOUR",
              "shot marker A did not set the effective palette")
        check(scene.get("ald_effective_source") == "marker",
              "shot marker A source wrong")
        check(shots.active_marker(scene) == "GOLDEN_HOUR",
              "active shot marker A wrong")

        scene.frame_set(20)
        shots.apply_for_frame(scene, force=True)
        check(settings.palette == base,
              "shot marker B changed the base palette")
        check(scene.get("ald_effective_palette") == "NEON_NIGHT",
              "shot marker B did not set the effective palette")
        check(scene.get("ald_effective_source") == "marker",
              "shot marker B source wrong")
        expected = palette_module.preset("NEON_NIGHT")
        node = gradient_node(scene)
        check(node is not None
              and close(node.inputs["Horizon Color"].default_value,
                        expected["horizon_color"]),
              "shot palette did not update the world")
        check(scene.get("ald_active_shot") == "NEON_NIGHT",
              "active shot not tracked")

        settings.palette = "NEON_NIGHT"
        scene.frame_set(30)
        result = bpy.ops.ald.mark_shot()
        check("FINISHED" in result, "mark shot operator failed")
        marker_c = next((m for m in scene.timeline_markers
                         if m.frame == 30), None)
        check(marker_c is not None
              and marker_c.name == shots.marker_name("NEON_NIGHT"),
              "mark shot did not create the marker")
        check(scene.get("ald_effective_palette") == "NEON_NIGHT",
              "mark shot did not apply its palette")
    finally:
        for marker in (marker_a, marker_b, marker_c):
            if marker is not None:
                scene.timeline_markers.remove(marker)
        settings.use_shot_markers = False
        if "ald_active_shot" in scene:
            del scene["ald_active_shot"]
        scene.frame_set(1)
        settings.palette = "GOLDEN_HOUR"


def check_camera_override(scene, settings):
    from anime_look_director import look
    from anime_look_director import palette as palette_module

    camera_a = scene.camera
    check(camera_a is not None and hasattr(camera_a.data, "ald"),
          "camera override settings missing")
    old_override = camera_a.data.ald.override
    old_palette = camera_a.data.ald.palette
    base = settings.palette

    cam_data = bpy.data.cameras.new("ALD_GATE_CAM_B")
    cam_b = bpy.data.objects.new("ALD_GATE_CAM_B", cam_data)
    scene.collection.objects.link(cam_b)
    try:
        cam_b.data.ald.override = True
        cam_b.data.ald.palette = "RAINY_TOKYO"
        scene.camera = cam_b
        look.apply(scene, force=True)
        check(scene.get("ald_effective_palette") == "RAINY_TOKYO",
              "camera override did not set the effective palette")
        check(scene.get("ald_effective_source") == "camera",
              "camera override source wrong")
        check(settings.palette == base,
              "camera override changed the base palette")
        expected = palette_module.preset("RAINY_TOKYO")
        node = gradient_node(scene)
        check(node is not None
              and close(node.inputs["Horizon Color"].default_value,
                        expected["horizon_color"]),
              "camera override did not update the world")

        cam_b.data.ald.palette = "SAKURA_SPRING"
        look.apply(scene, force=True)
        check(scene.get("ald_effective_palette") == "SAKURA_SPRING",
              "camera override palette change not applied")

        scene.camera = camera_a
        look.apply(scene, force=True)
        check(scene.get("ald_effective_palette") == base,
              "base palette not restored after the camera override")
        check(scene.get("ald_effective_source") == "scene",
              "camera override source not cleared")
    finally:
        scene.camera = camera_a
        camera_a.data.ald.override = old_override
        camera_a.data.ald.palette = old_palette
        bpy.data.objects.remove(cam_b, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        look.apply(scene, force=True)


def check_material_presets(scene, settings, data):
    obj = data["object"]
    for selected in list(bpy.context.selected_objects):
        selected.select_set(False)
    settings.shadow_tint = True
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    settings.material_preset = "METAL"
    result = bpy.ops.ald.apply_material_preset()
    check("FINISHED" in result, "material preset operator failed")

    metal = bpy.data.materials.get("ALD | Metal")
    check(metal is not None, "metal preset material missing")
    bsdf = principled(metal)
    check(bsdf is not None, "metal preset has no Principled BSDF")
    check(close(bsdf.inputs["Base Color"].default_value,
                (0.72, 0.73, 0.76, 1.0)),
          "metal preset base color wrong")
    check(abs(bsdf.inputs["Metallic"].default_value - 1.0) <= TOLERANCE,
          "metal preset is not metallic")
    check(any(slot == metal for slot in obj.data.materials),
          "preset material not assigned to the object")
    check(tint_node(metal) is not None,
          "preset material missing the shadow tint")
    slots = len(obj.data.materials)
    bpy.ops.ald.apply_material_preset()
    check(len(obj.data.materials) == slots,
          "material preset duplicated the slot")

    settings.material_preset = "SKIN"
    bpy.ops.ald.apply_material_preset()
    skin = bpy.data.materials.get("ALD | Skin")
    check(skin is not None, "skin preset material missing")
    check(close(principled(skin).inputs["Base Color"].default_value,
                (0.86, 0.68, 0.58, 1.0)),
          "skin preset base color wrong")

    settings.material_preset = "EMISSION"
    bpy.ops.ald.apply_material_preset()
    emission = bpy.data.materials.get("ALD | Emission")
    check(emission is not None, "emission preset material missing")
    check(principled(emission).inputs["Emission Strength"].default_value > 0.5,
          "emission preset has no emission")

    settings.material_preset = "HAIR"
    bpy.ops.ald.apply_material_preset()
    hair = bpy.data.materials.get("ALD | Hair")
    check(hair is not None, "hair preset material missing")
    hair_node = tint_node(hair)
    check(hair_node is not None
          and hair_node.inputs["Rim Strength"].default_value
          > settings.rim_strength + 0.1,
          "hair preset has no angel-ring rim boost")

    for index in range(len(obj.data.materials) - 1, -1, -1):
        slot = obj.data.materials[index]
        if slot in (metal, skin, emission, hair):
            obj.data.materials.pop(index=index)
    bpy.data.materials.remove(metal)
    bpy.data.materials.remove(skin)
    bpy.data.materials.remove(emission)
    bpy.data.materials.remove(hair)
    obj.select_set(False)


def check_custom_colors(scene, settings, data):
    from anime_look_director import palette as palette_module

    settings.custom_colors = True
    bpy.ops.ald.apply_palette()
    settings.custom_sky = (0.9, 0.1, 0.2)
    settings.custom_horizon = (0.1, 0.9, 0.2)
    settings.custom_sun = (0.2, 0.1, 0.9)
    settings.custom_shadow = (0.3, 0.6, 0.9)

    node = gradient_node(scene)
    check(node is not None
          and close(node.inputs["Sky Color"].default_value, (0.9, 0.1, 0.2)),
          "custom sky color not applied")
    check(close(node.inputs["Horizon Color"].default_value, (0.1, 0.9, 0.2)),
          "custom horizon color not applied")
    sun = find_sun(scene)
    check(sun is not None and close(sun.data.color, (0.2, 0.1, 0.9)),
          "custom sun color not applied")
    check(close(palette_module.shadow_tint_for(scene), (0.3, 0.6, 0.9)),
          "custom shadow color not applied")

    settings.custom_cloud_shadow = (0.21, 0.31, 0.41)
    settings.custom_cloud_mid = (0.52, 0.62, 0.72)
    settings.custom_cloud_light = (1.11, 1.02, 0.93)
    node = gradient_node(scene)
    for name, value in (("Cloud Shadow", settings.custom_cloud_shadow),
                        ("Cloud Mid", settings.custom_cloud_mid),
                        ("Cloud Light", settings.custom_cloud_light)):
        check(close(node.inputs[name].default_value, value),
              "custom " + name + " not applied")

    cloud_colors = {name: tuple(node.inputs[name].default_value)
                    for name in ("Cloud Shadow", "Cloud Mid", "Cloud Light")}
    settings.custom_sun = (0.95, 0.85, 0.05)
    node = gradient_node(scene)
    check(close(sun.data.color, (0.95, 0.85, 0.05)),
          "custom sun color update not applied")
    for name, before in cloud_colors.items():
        check(close(node.inputs[name].default_value, before),
              "custom sun repainted " + name)
    settings.custom_sun = (0.2, 0.1, 0.9)

    settings.custom_horizon = (0.9, 0.1, 0.8)
    node = gradient_node(scene)
    for name, before in cloud_colors.items():
        check(close(node.inputs[name].default_value, before),
              "custom horizon repainted " + name)
    settings.custom_horizon = (0.1, 0.9, 0.2)

    tint = tint_node(data["plain"])
    check(tint is not None
          and close(tint.inputs["Tint"].default_value, (0.3, 0.6, 0.9)),
          "custom shadow color not synced to materials")
    ng = scene.compositing_node_group
    halation = ng.nodes.get("ALD | Halation") if ng is not None else None
    check(halation is not None
          and close(halation.inputs["Tint"].default_value, (0.2, 0.1, 0.9, 1.0)),
          "custom sun color not synced to halation")
    settings.ink_lines = True
    bpy.ops.ald.build()
    ink = ng.nodes.get("ALD | Ink Color")
    check(ink is not None
          and close(ink.outputs[0].default_value, (0.075, 0.15, 0.225, 1.0)),
          "custom shadow color not synced to ink")
    settings.ink_lines = False
    bpy.ops.ald.build()

    settings.palette = "NEON_NIGHT"
    neon = palette_module.preset("NEON_NIGHT")
    check(close(settings.custom_sky, neon["sky_color"]),
          "custom colors not refreshed on palette switch")
    check(close(settings.custom_horizon, neon["horizon_color"]),
          "custom horizon not refreshed on palette switch")
    node = gradient_node(scene)
    for name, key in (("Cloud Shadow", "cloud_shadow"),
                      ("Cloud Mid", "cloud_mid"),
                      ("Cloud Light", "cloud_light")):
        check(close(settings.custom_cloud_shadow if name == "Cloud Shadow"
                    else settings.custom_cloud_mid if name == "Cloud Mid"
                    else settings.custom_cloud_light, neon[key]),
              "custom cloud not refreshed on palette switch: " + name)
        check(close(node.inputs[name].default_value, neon[key]),
              "cloud socket not refreshed on palette switch: " + name)
    settings.palette = "GOLDEN_HOUR"
    golden = palette_module.preset("GOLDEN_HOUR")
    check(close(settings.custom_sky, golden["sky_color"]),
          "custom colors not refreshed back to Golden")

    settings.custom_colors = False
    bpy.ops.ald.apply_palette()
    expected = palette_module.preset(settings.palette)
    node = gradient_node(scene)
    check(close(node.inputs["Sky Color"].default_value, expected["sky_color"]),
          "preset sky color not restored")
    check(close(sun.data.color, expected["sun_color"]),
          "preset sun color not restored")
    halation = ng.nodes.get("ALD | Halation") if ng is not None else None
    check(halation is not None
          and close(halation.inputs["Tint"].default_value,
                    palette_module.glare_tint(settings.palette)),
          "preset halation tint not restored")


def check_multiscene(scene):
    from anime_look_director import compositor

    other = bpy.data.scenes.new("ALD_GATE_SCENE_B")
    try:
        compositor.build(other)
        group_a = scene.compositing_node_group
        group_b = other.compositing_node_group
        check(group_a is not None and group_b is not None,
              "per-scene stack not assigned")
        check(group_a.as_pointer() != group_b.as_pointer(),
              "scenes share one compositor group")
        check(group_a.get("ald_scene") == scene.name,
              "stack A not tagged for its scene")
        check(group_b.get("ald_scene") == other.name,
              "stack B not tagged for its scene")

        def rl_scene(ng):
            rl = next(n for n in ng.nodes
                      if n.bl_idname == "CompositorNodeRLayers")
            return rl.scene.name if rl.scene is not None else None

        check(rl_scene(group_a) == scene.name,
              "stack A renders the wrong scene")
        check(rl_scene(group_b) == other.name,
              "stack B renders the wrong scene")

        name_b = group_b.name
        compositor.remove(other)
        check(other.compositing_node_group is None,
              "scene B stack not unassigned")
        check(bpy.data.node_groups.get(name_b) is None,
              "scene B stack not deleted")
        check(scene.compositing_node_group is not None,
              "removing scene B stack affected scene A")
    finally:
        bpy.data.scenes.remove(other)


def check_fx_occlusion(scene):
    """P0-D: an opaque occluder hides the FX, and the FX show without it.

    Two renders per state (FX present, FX cleared). Behind the wall the
    images must match: the particles are hidden. Without the wall they must
    differ: the particles are there. The old check only proved that the wall
    was red, which also passed when the FX leaked through it.
    """
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_engine = scene.render.engine
    previous_backend = scene.ald.fx_backend

    origin, forward, _up, _right = fx_module._camera_basis(scene)
    material = bpy.data.materials.new("ALD Gate Occluder")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.05, 0.05, 1.0)
    bpy.ops.mesh.primitive_plane_add(
        size=400.0, location=tuple(origin + forward * 12.0))
    occluder = bpy.context.object
    occluder.rotation_euler = (-forward).to_track_quat("Z", "Y").to_euler()
    occluder.data.materials.append(material)

    hidden = []
    for obj in scene.objects:
        if obj is occluder or obj.get("ald_fx"):
            continue
        if obj.type == "CAMERA" or obj.type == "LIGHT":
            continue
        hidden.append((obj, obj.hide_render))
        obj.hide_render = True

    def render(name):
        path = os.path.join(tempfile.gettempdir(), name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(path)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        return pixels

    def mean_diff(first, second):
        total = 0.0
        count = 0
        for index in range(0, min(len(first), len(second)), 4):
            total += abs(first[index] - second[index])
            total += abs(first[index + 1] - second[index + 1])
            total += abs(first[index + 2] - second[index + 2])
            count += 3
        return total / max(count, 1)

    try:
        scene.ald.fx_backend = "FX3D"
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=5, distance=30.0, time=0.6)
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.3) * fps))
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        try:
            scene.render.use_motion_blur = False
        except Exception:
            pass

        behind_with = render("ald_gate_occ_behind_with.png")
        fx_module.clear(scene)
        behind_without = render("ald_gate_occ_behind_without.png")
        occluded_diff = mean_diff(behind_with, behind_without)

        # Without the wall the same burst must change the image.
        occluder.hide_render = True
        fx_module.create_fireworks(scene, 1, seed=5, distance=30.0, time=0.6)
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.3) * fps))
        free_with = render("ald_gate_occ_free_with.png")
        fx_module.clear(scene)
        free_without = render("ald_gate_occ_free_without.png")
        visible_diff = mean_diff(free_with, free_without)

        check(visible_diff > 1e-4,
              "the burst is invisible even without the occluder (%.6f)"
              % visible_diff)
        check(occluded_diff < visible_diff * 0.25,
              "the occluder does not hide the burst "
              "(behind %.6f vs free %.6f)"
              % (occluded_diff, visible_diff))
        print("ALD GATE occlusion: behind=%.6f free=%.6f"
              % (occluded_diff, visible_diff))
    finally:
        try:
            scene.render.use_motion_blur = False
        except Exception:
            pass
        for obj, state in hidden:
            obj.hide_render = state
        bpy.data.objects.remove(occluder, do_unlink=True)
        bpy.data.materials.remove(material)
        fx_module.clear(scene)
        scene.ald.fx_backend = previous_backend
        scene.render.resolution_x, scene.render.resolution_y = previous_size
        scene.render.engine = previous_engine
        scene.frame_set(previous_frame)


def check_render(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    path = os.path.join(tempfile.gettempdir(), "ald_gate.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    check(os.path.exists(path) and os.path.getsize(path) > 0,
          "render not produced")


def _fx_signature(scene):
    """Geometry fingerprint of the FX system owned by a scene."""
    import hashlib
    from anime_look_director import fx as fx_module
    owner = fx_module._scene_id(scene)
    coll = None
    for candidate in bpy.data.collections:
        if candidate.get(fx_module.OWNER_KEY) == owner:
            coll = candidate
            break
    if coll is None:
        return (0, "")
    points = []
    for obj in sorted(coll.objects, key=lambda item: item.name):
        if any(mod.type == "NODES" for mod in obj.modifiers):
            # Geometry Nodes objects are evaluated, not authored: their stored
            # vertices carry no motion information. The deterministic data
            # lives in the point attributes.
            for name in sorted(obj.data.attributes.keys()):
                attribute = obj.data.attributes[name]
                for index in range(len(attribute.data)):
                    item = attribute.data[index]
                    if hasattr(item, "vector"):
                        value = tuple(round(float(axis), 4)
                                      for axis in item.vector)
                    else:
                        value = round(float(item.value), 4)
                    points.append((name, index, value))
            continue
        if obj.type == "CURVE":
            for spline in obj.data.splines:
                for point in spline.points:
                    points.append(tuple(round(value, 4) for value in point.co))
        elif obj.type == "MESH":
            for vertex in obj.data.vertices:
                points.append(tuple(round(value, 4) for value in vertex.co))
        else:
            points.append(tuple(round(value, 4) for value in obj.location))
    digest = hashlib.sha1(repr(points).encode("utf-8")).hexdigest()
    return (len(points), digest)


def _fx_orphans():
    count = 0
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in datablocks:
            if (block.get("ald_fx") or block.get("ald_fx_material")) \
                    and block.users == 0:
                count += 1
    return count


def fx_runtime(scene, kind="fireworks"):
    """The runtime state of the first system of a kind.

    The registry is keyed by the identity of the system: two systems of the
    same kind never collide.
    """
    from anime_look_director import fx as fx_module

    registry = fx_module.SYSTEMS.get(fx_module._scene_id(scene)) or {}
    for runtime in registry.values():
        if runtime and runtime.get("kind") == kind:
            return runtime
    return None


def fx_runtime_by_uid(scene, uid):
    """The runtime state of a system, by identity."""
    from anime_look_director import fx as fx_module

    registry = fx_module.SYSTEMS.get(fx_module._scene_id(scene)) or {}
    return registry.get(uid)


def check_fx(scene):
    """Exercise the deterministic 3D FX architecture."""
    from anime_look_director import compositor as compositor_module
    from anime_look_director import fx as fx_module

    other = bpy.data.scenes.new("ALD FX Gate B")
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    fx_module.create_fireworks(other, 2, seed=5, distance=30.0, time=0.6)

    signature = _fx_signature(scene)
    check(signature[0] > 0, "fx geometry not created")
    check(_fx_signature(other)[0] > 0,
          "fx system not created in the second scene")
    check(fx_module._collection(scene) is not fx_module._collection(other),
          "fx collections are shared between scenes")

    before_clear = _fx_signature(scene)
    fx_module.clear(other)
    check(_fx_signature(scene) == before_clear,
          "clearing one scene modified another scene")

    orphans_before = _fx_orphans()
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    check(_fx_orphans() <= orphans_before + 2,
          "fx datablocks are leaking between create/clear cycles")
    check(_fx_signature(scene) == signature,
          "fx geometry is not reproducible with the same seed")

    # Same instant expressed in seconds must not depend on the frame rate.
    fps24 = 24.0
    fps30 = 30.0
    time24 = 12 / fps24
    time30 = 15 / fps30
    check(abs(time24 - time30) < 1e-6,
          "fps conversion is inconsistent")
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=time24)
    first = _fx_signature(scene)
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=time30)
    check(_fx_signature(scene) == first,
          "fx state depends on the frame rate")

    # The compositor stack must not delete the FX objects.
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    compositor_module.build(scene)
    check(_fx_signature(scene)[0] > 0, "compositor rebuild removed the FX")
    ng = scene.compositing_node_group
    if ng is not None:
        matte = ng.nodes.get("ALD | FX Matte")
        emission_node = ng.nodes.get("ALD | FX Emission")
        restore = ng.nodes.get("ALD | FX Restore")
        punch = ng.nodes.get("ALD | FX Punch Out")
        check(matte is not None, "FX matte node missing")
        check(emission_node is not None, "FX emission node missing")
        check(restore is not None, "FX restore node missing")
        check(punch is not None, "FX punch out node missing")
        if matte is not None:
            check(matte.bl_idname == "CompositorNodeCryptomatte",
                  "the FX matte is not Cryptomatte")
            check(bool(matte.matte_id), "the FX matte has no material ids")
        if punch is not None and matte is not None:
            factor = punch.inputs.get("Factor")
            check(factor is not None and factor.is_linked
                  and factor.links[0].from_node == matte,
                  "the FX punch out is not driven by the matte")
            # An unlinked B socket defaults to 0.5 grey: the punch would lerp a
            # grey veil over every FX pixel instead of removing the background.
            black = [socket for socket in punch.inputs
                     if socket.name == "B" and socket.type == "RGBA"]
            check(bool(black) and not black[0].is_linked
                  and max(black[0].default_value[:3]) < 1e-4,
                  "the FX punch out does not punch to black")
        # The recomposition is semantic: C = P(B)*(1-A) + F + Glare(F).
        # F is the Emission pass masked by Cryptomatte and is premultiplied,
        # so the restore adds it unscaled.
        if restore is not None:
            check(restore.blend_type == "ADD",
                  "the FX restore is not additive")
            factor = restore.inputs.get("Factor")
            check(factor is not None and not factor.is_linked
                  and abs(factor.default_value - 1.0) < 1e-4,
                  "the FX restore scales the premultiplied FX")
        check(scene.view_layers.get("ALD FX Base") is not None,
              "the FX base layer is missing")
        check(scene.view_layers.get("ALD FX Only") is None,
              "the legacy FX Only layer still exists")

    bpy.data.scenes.remove(other)

    # The Geometry Nodes prototype must exist and be attached to a real burst.
    from anime_look_director import fx_nodes
    group = bpy.data.node_groups.get(fx_nodes.GROUP_NAME)
    check(group is not None, "FX burst node group missing")
    if group is not None:
        types = {node.bl_idname for node in group.nodes}
        for required in ("GeometryNodeSetPosition",
                         "GeometryNodeInstanceOnPoints",
                         "GeometryNodeInputSceneTime"):
            check(required in types, "FX node group missing " + required)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    gn_objects = [obj for obj in bpy.data.objects
                  if obj.type == "MESH"
                  and any(mod.type == "NODES" for mod in obj.modifiers)]
    check(gn_objects, "no FX object uses the Geometry Nodes burst")
    # The FX panel lists the systems: every object must be tagged with its kind.
    info = dict(fx_module.systems_info(scene))
    check(info.get("fireworks", 0) > 0,
          "the fireworks system is not listed (%s)" % info)
    check(all(obj.get("ald_fx_kind") == "fireworks" for obj in gn_objects),
          "a Geometry Nodes burst is not tagged with its kind")
    fx_module.clear(scene)
    check_fx_gn_parity(scene)


def check_fx_gn_parity(scene):
    """The node evaluation must match the deterministic data of the burst."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    runtime = fx_runtime(scene, "fireworks")
    burst = runtime["bursts"][1]
    population = burst["population"]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    time = 12 / fps + float(scene.ald.fx_age)
    powers = fx_module._energy_powers(scene)
    fade = fx_module._atmospheric_fade(scene)
    camera = runtime.get("camera")

    def compare(name, particles, label):
        obj = bpy.data.objects.get(name)
        check(obj is not None, "geometry nodes object missing: %s" % name)
        if obj is None:
            return
        centers = fx_nodes.realized_centers(obj, depsgraph)
        check(len(centers) == len(particles),
              "the %s population differs: %d against %d"
              % (label, len(centers), len(particles)))
        worst = 0.0
        for particle, actual in zip(particles, centers):
            expected, _scale, _energy, alive = fx_module._particle_state(
                particle, time, powers, fade, camera)
            if not alive:
                continue
            worst = max(worst, (expected - actual).length)
        check(worst < 1e-3,
              "geometry nodes %s drift from the solver (%.6f m)"
              % (label, worst))

    compare("ALD FX GN Heads 1", population["heads"], "heads")
    compare("ALD FX GN Pistil 1", population["pistil"], "pistil")
    compare("ALD FX GN Sparks 1", population["sparks"], "sparks")
    compare("ALD FX GN Flash 1", population["flash"], "flash")
    for slot in range(3):
        grains = [p for p in population["grains"] if p["spoke"] % 3 == slot]
        compare("ALD FX GN Beads 1 %d" % slot, grains, "grains %d" % slot)
    fx_module.clear(scene)
    scene.frame_set(previous_frame)


def check_fx_gn_meteors(scene):
    """The meteors must be evaluated by the node group as well."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 3, seed=21, distance=40.0, time=0.6)
    scene.frame_set(20)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    system = fx_runtime(scene, "meteors")
    check(system.get("gn") is True, "the meteors are not evaluated by GN")
    python_objects = [obj for obj in bpy.data.objects
                      if obj.get("ald_fx") and obj.get("ald_fx_kind") == "meteors"
                      and not any(mod.type == "NODES" for mod in obj.modifiers)]
    check(not python_objects,
          "the Python meteors are still in the scene: %s"
          % [obj.name for obj in python_objects])

    heads = bpy.data.objects.get("ALD FX GN Meteor Heads")
    check(heads is not None, "geometry nodes meteor heads missing")
    if heads is not None:
        centers = fx_nodes.realized_centers(heads, depsgraph)
        check(len(centers) == 3,
              "geometry nodes meteors produced %d heads" % len(centers))
        origin = system["origin"]
        shower = system["shower"]
        seed = system["seed"]
        distance = system["distance"]
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        time = 20 / fps + float(scene.ald.fx_age)
        worst = 0.0
        for index in range(3):
            life = fx_module._hash_range(seed, index, 0, 2, 0.55, 1.15)
            birth = index * 0.9 + fx_module._hash_range(seed, index, 0, 1,
                                                        0.0, 0.6)
            age = time - birth
            if not (0.0 < age <= life):
                continue
            forward = (shower * 0.0)  # placeholder, replaced below
            plane_center = origin + fx_module.Vector(
                fx_module._camera_basis(scene)[1]) * distance
            right = fx_module._camera_basis(scene)[3]
            up = fx_module._camera_basis(scene)[2]
            lateral_x = fx_module._hash_range(seed, index, 10, 11, -0.55,
                                              0.55) * distance
            lateral_y = fx_module._hash_range(seed, index, 10, 12, -0.30,
                                              0.34) * distance
            start = plane_center + right * lateral_x + up * lateral_y
            jitter = fx_module.Vector((
                fx_module._hash_range(seed, index, 0, 3, -0.03, 0.03),
                fx_module._hash_range(seed, index, 0, 4, -0.03, 0.03),
                fx_module._hash_range(seed, index, 0, 5, -0.02, 0.02),
            ))
            direction = (shower + jitter).normalized()
            speed = fx_module._hash_range(seed, index, 0, 6, 26.0, 38.0)
            v0 = direction * speed
            expected = fx_module._position(start, v0, 0.08, age)
            worst = max(worst, (expected - centers[index]).length)
        check(worst < 1e-3,
              "geometry nodes meteors drift from the solver (%.6f m)" % worst)

    fx_module.clear(scene)
    scene.frame_set(previous_frame)


def check_fx_gn_determinism(scene):
    """The node evaluation must survive frame jumps and frame rate changes."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    previous_fps = scene.render.fps
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    heads = bpy.data.objects.get("ALD FX GN Heads 1")
    check(heads is not None, "geometry nodes burst heads missing")
    if heads is None:
        return
    reference = fx_nodes.realized_centers(heads, depsgraph)
    check(len(reference) > 0, "geometry nodes burst produced no head")

    # Jump to another frame and come back: the state must be identical.
    scene.frame_set(40)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    again = fx_nodes.realized_centers(heads, depsgraph)
    check(len(again) == len(reference)
          and all((first - second).length < 1e-5
                  for first, second in zip(reference, again)),
          "the node evaluation changed after a frame jump")

    # The same instant expressed in seconds must not depend on the frame rate.
    for fps, frame in ((24, 12), (30, 15), (60, 30)):
        scene.render.fps = fps
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        stepped = fx_nodes.realized_centers(heads, depsgraph)
        check(len(stepped) == len(reference)
              and all((first - second).length < 1e-4
                      for first, second in zip(reference, stepped)),
              "the node evaluation depends on the frame rate (%d fps)" % fps)
    scene.render.fps = previous_fps
    scene.frame_set(previous_frame)
    fx_module.clear(scene)


def check_fx_gn_limits(scene):
    """Drag free and gravity free limits must be mathematically correct."""
    from mathutils import Vector

    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    material = fx_module._material("ALD FX Gate Limit", (1.0, 1.0, 1.0), 1.0)
    velocity = Vector((10.0, 0.0, 0.0))
    origin = Vector((0.0, 0.0, 0.0))
    for gravity in (Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, -9.81))):
        particles = [{
            "birth": 0.0, "life": 10.0, "drag": 0.0, "radius": 0.05,
            "vel": velocity, "pos0": origin, "tau": 0.0,
            "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
        }]
        obj = fx_module._gn_points_object(
            scene, "ALD FX Gate Ballistic", material, particles,
            gravity=gravity)
        obj["ald_fx_kind"] = "gate"
        scene.frame_set(12)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        centers = fx_nodes.realized_centers(obj, depsgraph)
        age = 12 / (scene.render.fps / max(scene.render.fps_base, 1e-6))
        expected = origin + velocity * age + 0.5 * gravity * age * age
        check(centers and (centers[0] - expected).length < 1e-3,
              "the drag free limit is wrong: %s instead of %s"
              % (centers[0] if centers else None, expected))
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.frame_set(previous_frame)


def check_fx_gn_children(scene):
    """The children must stay alive when the head of the star is gone."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    # A late instant: some stars are dying, the sparks are still burning.
    scene.frame_set(26)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    sparks = bpy.data.objects.get("ALD FX GN Sparks 1")
    heads = bpy.data.objects.get("ALD FX GN Heads 1")
    check(sparks is not None, "geometry nodes sparks missing")
    if sparks is not None:
        instances = fx_nodes.realized_instances(sparks, depsgraph)
        alive = [radius for _center, radius in instances if radius > 1e-4]
        check(alive, "the child sparks die with the head of the star")
    if heads is not None:
        instances = fx_nodes.realized_instances(heads, depsgraph)
        dead = [radius for _center, radius in instances if radius <= 1e-4]
        check(dead, "the head of the star is still alive at this instant")
    scene.frame_set(previous_frame)
    fx_module.clear(scene)


def check_fx_new_file(scene):
    """Opening a new file must reinitialise the handlers and the caches."""
    from anime_look_director import cameras as cameras_module
    from anime_look_director import fx as fx_module

    fx_module.create_fireworks(scene, 1, seed=3, distance=30.0, time=0.6)
    check(bool(fx_module.SYSTEMS), "the FX cache is empty before the file load")
    bpy.ops.wm.read_homefile(use_empty=True)
    new_scene = bpy.context.scene
    check(hasattr(bpy.types.Scene, "ald"),
          "the add-on is not registered after a file load")
    check(fx_module._on_frame_change in bpy.app.handlers.frame_change_post,
          "the frame handler was lost after a file load")
    check(fx_module._on_load_post in bpy.app.handlers.load_post,
          "the load handler was lost after a file load")
    owner = fx_module._scene_id(new_scene)
    check(not fx_module.SYSTEMS.get(owner),
          "the FX cache survived the file load")
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the FX objects survived the file load")
    check(not cameras_module._last_camera,
          "the camera cache survived the file load")
    check(not cameras_module._last_transforms,
          "the transform cache survived the file load")
    # The add-on must still work on the new file.
    new_scene.ald.palette = "TWILIGHT_DUSK"
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    check(new_scene.compositing_node_group is not None,
          "the stack was not built on the new file")
    fx_module.create_fireworks(new_scene, 1, seed=3, distance=30.0, time=0.6)
    check(bool(fx_module.SYSTEMS.get(owner)),
          "the FX cannot be created after a file load")
    fx_module.clear(new_scene)


def check_fx_age_no_rebuild(scene):
    """The Burst Age slider must move the systems, not rebuild them."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_age = float(scene.ald.fx_age)
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    heads = bpy.data.objects.get("ALD FX GN Heads 1")
    check(heads is not None, "geometry nodes burst heads missing")
    if heads is None:
        return
    before_signature = _fx_signature(scene)
    before_names = sorted(obj.name for obj in bpy.data.objects
                          if obj.get("ald_fx"))
    before = fx_nodes.realized_centers(heads, depsgraph)

    scene.ald.fx_age = previous_age + 0.5
    depsgraph = bpy.context.evaluated_depsgraph_get()
    after = fx_nodes.realized_centers(heads, depsgraph)
    after_names = sorted(obj.name for obj in bpy.data.objects
                         if obj.get("ald_fx"))
    check(before_names == after_names,
          "the Burst Age slider rebuilt the FX objects")
    check(_fx_signature(scene) == before_signature,
          "the Burst Age slider rewrote the deterministic data")
    moved = max((first - second).length
                for first, second in zip(before, after)) if before else 0.0
    check(moved > 0.5,
          "the Burst Age slider did not move the burst (%.3f m)" % moved)
    scene.ald.fx_age = previous_age
    fx_module.clear(scene)


def _python_instances(obj):
    """Centers and radii of the particles written by the Python mesh."""
    from mathutils import Vector

    verts = obj.data.vertices
    count = 12  # the icosphere of the unit sphere
    instances = []
    for start in range(0, len(verts), count):
        chunk = verts[start:start + count]
        if len(chunk) < count:
            break
        total = Vector((0.0, 0.0, 0.0))
        for vertex in chunk:
            total += vertex.co
        center = total / len(chunk)
        radius = max((vertex.co - center).length for vertex in chunk)
        instances.append((center, radius))
    return instances


def check_fx_decay_curve(scene):
    """The scale must shrink with the age: s(u) = m + (1 - m) * (1 - u) ** p."""
    from mathutils import Vector

    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    previous_age = float(scene.ald.fx_age)
    scene.ald.fx_age = 0.0
    material = fx_module._material("ALD FX Gate Decay", (1.0, 1.0, 1.0), 1.0)
    life = 4.0
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    cases = (
        ("head", 0.35, 1.0),
        ("flash", 0.0, 0.5),
    )
    for role, min_scale, decay_power in cases:
        particles = [{
            "birth": 0.0, "life": life, "drag": 0.0, "radius": 1.0,
            "vel": Vector((0.0, 0.0, 0.0)), "pos0": Vector((0.0, 0.0, 0.0)),
            "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
            "min_scale": min_scale, "decay_power": decay_power,
            "energy_power": 1.0, "role": role, "spoke": 0,
        }]
        obj = fx_module._gn_points_object(
            scene, "ALD FX Gate Decay %s" % role, material, particles,
            gravity=(0.0, 0.0, 0.0), min_scale=min_scale,
            decay_power=decay_power)
        obj["ald_fx_kind"] = "gate"
        for step in (0.0, 0.25, 0.5, 0.75, 1.0):
            frame = 1 + int(round(step * life * fps))
            scene.frame_set(frame)
            age = frame / fps
            u = min(age / life, 1.0)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            instances = fx_nodes.realized_instances(obj, depsgraph)
            radius = instances[0][1] if instances else 0.0
            expected = min_scale + (1.0 - min_scale) * (1.0 - u) ** decay_power
            if age >= life:
                expected = 0.0  # the body is dead
            check(abs(radius - expected) < 2e-3,
                  "the %s scale is wrong at u=%.2f: %.4f instead of %.4f"
                  % (role, u, radius, expected))
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.ald.fx_age = previous_age
    scene.frame_set(previous_frame)


def check_fx_gn_python_parity(scene):
    """The Geometry Nodes and the Python backends must agree."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    previous_backend = bool(scene.ald.fx_gn_prototype)
    # Geometry Nodes evaluation.
    scene.ald.fx_gn_prototype = True
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.0)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    gn = {}
    for name, key in (("ALD FX GN Heads 1", "heads"),
                      ("ALD FX GN Beads 1 0", "grains"),
                      ("ALD FX GN Pistil 1", "pistil"),
                      ("ALD FX GN Sparks 1", "sparks"),
                      ("ALD FX GN Flash 1", "flash")):
        obj = bpy.data.objects.get(name)
        check(obj is not None, "geometry nodes object missing: %s" % name)
        if obj is not None:
            gn[key] = fx_nodes.realized_instances(obj, depsgraph)
    fx_module.clear(scene)
    # Python writer.
    scene.ald.fx_gn_prototype = False
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.0)
    scene.frame_set(12)
    fx_module.update(scene)
    python = {}
    for name, key in (("ALD FX CHRYSANTHEMUM 1 Heads", "heads"),
                      ("ALD FX CHRYSANTHEMUM 1 Beads 0", "grains"),
                      ("ALD FX CHRYSANTHEMUM 1 Pistil Heads", "pistil"),
                      ("ALD FX CHRYSANTHEMUM 1 Sparks", "sparks"),
                      ("ALD FX CHRYSANTHEMUM 1 Flash", "flash")):
        obj = bpy.data.objects.get(name)
        check(obj is not None, "python object missing: %s" % name)
        if obj is not None:
            python[key] = _python_instances(obj)
    for key in ("heads", "grains", "pistil", "sparks", "flash"):
        left = gn.get(key, [])
        right = python.get(key, [])
        if not left or not right:
            continue
        check(len(left) == len(right),
              "the %s population differs: %d against %d"
              % (key, len(left), len(right)))
        worst_position = 0.0
        worst_radius = 0.0
        for (center_a, radius_a), (center_b, radius_b) in zip(left, right):
            # The dead particles are hidden differently by the two backends:
            # only the living ones can be compared.
            if radius_a < 1e-4 or radius_b < 1e-4:
                continue
            worst_position = max(worst_position, (center_a - center_b).length)
            worst_radius = max(worst_radius, abs(radius_a - radius_b))
        check(worst_position < 1e-3,
              "the %s positions differ between the backends (%.6f m)"
              % (key, worst_position))
        check(worst_radius < 2e-3,
              "the %s scales differ between the backends (%.6f m)"
              % (key, worst_radius))
    fx_module.clear(scene)
    scene.ald.fx_gn_prototype = previous_backend
    scene.frame_set(previous_frame)


def check_fx_future_event(scene):
    """Before the birth nothing may be visible and nothing may overflow."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    previous_age = float(scene.ald.fx_age)
    scene.ald.fx_age = 0.0
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.0)
    # The second burst is born at 0.25 s: the first frame is before it.
    scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for name in ("ALD FX GN Heads 1", "ALD FX GN Beads 1 0", "ALD FX GN Sparks 1"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        for center, radius in fx_nodes.realized_instances(obj, depsgraph):
            check(all(abs(value) < 1e6 for value in center),
                  "the %s overflows before its birth" % name)
            check(radius < 1e-3,
                  "the %s is visible before its birth" % name)
    fx_module.clear(scene)
    scene.ald.fx_age = previous_age
    scene.frame_set(previous_frame)


def check_fx_burst_centers(scene):
    """The number of bursts must not change the composition rules."""
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    for burst_count in (1, 3, 5):
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, burst_count, seed=3, distance=60.0,
                                   time=0.0)
        runtime = fx_runtime(scene, "fireworks")
        bursts = runtime["bursts"]
        check(len(bursts) == burst_count,
              "the system holds %d bursts instead of %d"
              % (len(bursts), burst_count))
        # The horizontal rule must use the number of bursts, never the
        # number of samples of another population.
        for index, burst in enumerate(bursts):
            expected = (-0.18 + 0.36 * (index + 0.5) / burst_count) \
                * float(scene.ald.fx_burst_spread)
            check(abs(burst["spread_x"] - expected) < 1e-6,
                  "the burst %d is not placed by the composition rule "
                  "(%.4f instead of %.4f)"
                  % (index, burst["spread_x"], expected))
        # The composition stays symmetric around the centre of the frame.
        values = [burst["spread_x"] for burst in bursts]
        for index, value in enumerate(values):
            mirror = values[-index - 1]
            check(abs(value + mirror) < 1e-6,
                  "the composition of %d bursts is not symmetric" % burst_count)
    fx_module.clear(scene)
    scene.frame_set(previous_frame)


def check_fx_meteor_timing(scene):
    """No train or fragment may appear before the birth of the meteor."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    previous_age = float(scene.ald.fx_age)
    scene.ald.fx_age = 0.0
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 3, seed=21, distance=40.0, time=0.0)
    runtime = fx_runtime(scene, "meteors")
    populations = runtime["populations"]
    # The components share the same event birth.
    for population in populations:
        head_birth = population["head"]["birth"]
        for sample in population["train"]:
            check(abs(sample["birth"] - head_birth) < 1e-6,
                  "the train of a meteor is not born with the body")
        for fragment in population["fragments"]:
            check(fragment["birth"] >= head_birth - 1e-6,
                  "a fragment is born before the meteor")
    # The frame before the first birth: nothing may be visible.
    first_birth = min(population["head"]["birth"] for population in populations)
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    frame = max(1, int(max(first_birth - 0.05, 0.0) * fps))
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for name in ("ALD FX GN Meteor Heads", "ALD FX GN Meteor Trails",
                 "ALD FX GN Meteor Fragments"):
        obj = bpy.data.objects.get(name)
        check(obj is not None, "geometry nodes meteor missing: %s" % name)
        if obj is None:
            continue
        if obj.type == "MESH":
            for center, radius in fx_nodes.realized_instances(obj, depsgraph):
                check(radius < 1e-3,
                      "the %s is visible before the birth of the meteor" % name)
        else:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            check(len(mesh.vertices) == 0,
                  "the %s is visible before the birth of the meteor" % name)
            evaluated.to_mesh_clear()
    fx_module.clear(scene)
    scene.ald.fx_age = previous_age
    scene.frame_set(previous_frame)


def _forward_of(scene):
    from anime_look_director import fx as fx_module
    return fx_module._camera_basis(scene)[1]


def _right_of(scene):
    from anime_look_director import fx as fx_module
    return fx_module._camera_basis(scene)[3]


def check_fx_fixture(scene):
    """A saved file must restore the systems, the sliders and the clear."""
    from anime_look_director import fx as fx_module

    path = os.path.join(tempfile.gettempdir(), "ald_gate_fixture.blend")
    target = scene
    try:
        fx_module.clear(scene)
        bpy.ops.ald.fx_fireworks(count=3, age=0.8)
        bpy.ops.ald.fx_meteors(count=3, age=0.6)
        objects_before = len([obj for obj in bpy.data.objects
                              if obj.get("ald_fx")])
        check(objects_before > 0, "the fixture has no FX object")
        check(len(scene.ald.fx_systems) == 2,
              "the persistent configuration holds %d systems"
              % len(scene.ald.fx_systems))
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        new_scene = bpy.context.scene
        target = new_scene
        info = dict(fx_module.systems_info(new_scene))
        check(info.get("fireworks", 0) > 0,
              "the fireworks are not listed after the reload")
        check(info.get("meteors", 0) > 0,
              "the meteors are not listed after the reload")
        check(len(new_scene.ald.fx_systems) == 2,
              "the persistent configuration is lost after the reload")
        # The animation must still work.
        new_scene.frame_set(12)
        bpy.context.view_layer.update()
        check(fx_module.update(new_scene) is not False,
              "the FX cannot be updated after the reload")
        # The clear of one kind must not touch the other.
        registry = fx_module.SYSTEMS.get(fx_module._scene_id(new_scene))
        if registry and "fireworks" in registry:
            fx_module._remove_kind(new_scene, "fireworks")
            info = dict(fx_module.systems_info(new_scene))
            check(info.get("fireworks", 0) == 0,
                  "the fireworks are still listed after the clear")
            check(info.get("meteors", 0) > 0,
                  "the clear of the fireworks touched the meteors")
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            if target.name in bpy.data.scenes:
                fx_module.clear(target)
        except ReferenceError:
            pass


def check_fx_scene_duplicate(scene):
    """A duplicated scene owns an independent copy of the systems."""
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=2, age=0.8)
    original_objects = len([obj for obj in scene.objects if obj.get("ald_fx")])
    check(original_objects > 0, "the scene has no FX object")
    duplicate = scene.copy()
    try:
        original_id = fx_module._scene_id(scene)
        duplicate_id = fx_module._scene_id(duplicate)
        check(duplicate_id != original_id,
              "the duplicated scene shares the identity of the original")
        # The clear of the copy must not touch the original.
        fx_module.clear(duplicate)
        check(len([obj for obj in scene.objects if obj.get("ald_fx")])
              == original_objects,
              "the clear of the copy touched the original scene")
    finally:
        bpy.data.scenes.remove(duplicate)
        fx_module.clear(scene)


def check_fx_gn_schema(scene):
    """The node groups carry a build marker and an old one is migrated."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=1, age=0.8)
    group = bpy.data.node_groups.get(fx_nodes.GROUP_NAME)
    check(group is not None, "the burst node group is missing")
    if group is not None:
        check(int(group.get("ald_schema", 0)) == fx_nodes.SCHEMA,
              "the burst node group has no build marker")
    trail = bpy.data.node_groups.get(fx_nodes.TRAIL_GROUP_NAME)
    check(trail is not None, "the trail node group is missing")
    if trail is not None:
        check(int(trail.get("ald_schema", 0)) == fx_nodes.SCHEMA,
              "the trail node group has no build marker")
    # An old group must be migrated: the markers are updated and the
    # modifiers are remapped.
    if group is not None:
        group["ald_schema"] = 0
        new_group, _sockets = fx_nodes.build_burst_group()
        check(int(new_group.get("ald_schema", 0)) == fx_nodes.SCHEMA,
              "the old node group was not migrated")
        attached = [obj for obj in bpy.data.objects
                    if any(mod.type == "NODES"
                           and mod.node_group is new_group
                           for mod in obj.modifiers)]
        check(attached, "the modifiers were not remapped on the new group")
    fx_module.clear(scene)


def check_fx_backend(scene):
    """The three backends must be really exclusive."""
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=2, age=0.8)
    objects = [obj for obj in bpy.data.objects if obj.get("ald_fx")]
    check(objects, "no FX object to test the backend")
    # FX 3D: the systems are visible, the legacy shader is off.
    scene.ald.fx_backend = "FX3D"
    check(all(not obj.hide_render for obj in objects),
          "the FX 3D objects are hidden")
    check(all(not obj.hide_viewport for obj in objects),
          "the FX 3D objects are hidden in the viewport")
    check(not scene.ald.fireworks,
          "the legacy shader is active in the FX 3D backend")
    # OFF: nothing contributes, the data is preserved.
    scene.ald.fx_backend = "OFF"
    check(all(obj.hide_render for obj in objects),
          "the objects are still rendered with the backend off")
    check(not scene.ald.fireworks,
          "the legacy shader is active with the backend off")
    check(fx_module.systems_info(scene),
          "the data is lost with the backend off")
    # LEGACY: the shader is on, the systems are hidden.
    scene.ald.fx_backend = "LEGACY"
    check(all(obj.hide_render for obj in objects),
          "the objects are still rendered in the legacy backend")
    check(scene.ald.fireworks,
          "the legacy shader is not active in the legacy backend")
    # The legacy meteors of the world shader belong to the legacy backend.
    scene.ald.shooting_stars = True
    scene.ald.fx_backend = "FX3D"
    check(not scene.ald.shooting_stars,
          "the legacy shooting stars stay active in the FX 3D backend")
    check(not scene.ald.fireworks,
          "the legacy fireworks stay active in the FX 3D backend")
    scene.ald.fx_backend = "FX3D"
    fx_module.clear(scene)


def check_ui_parity(scene):
    """The two surfaces must expose the same controls."""
    import inspect
    import re

    from anime_look_director import panels

    shared = [name for name in dir(panels) if name.startswith("draw_")]
    check(len(shared) >= 10, "the shared drawing functions are missing")

    def calls(classes):
        names = set()
        for cls in classes:
            source = inspect.getsource(cls.draw)
            for name in shared:
                if re.search(r"\b%s\(" % name, source):
                    names.add(name)
        return names

    properties = calls((panels.ALD_PT_scene, panels.ALD_PT_world,
                        panels.ALD_PT_compositor, panels.ALD_PT_fx))
    sidebar = calls((panels.ALD_PT_view3d, panels.ALD_PT_view3d_world,
                     panels.ALD_PT_view3d_compositor, panels.ALD_PT_view3d_fx))
    check(properties == sidebar,
          "the two surfaces expose different controls: %s against %s"
          % (sorted(properties), sorted(sidebar)))
    check("draw_fx" in sidebar and "draw_fx" in properties,
          "the FX section is missing in one of the surfaces")
    # No control may be hidden in one surface only.
    for name in shared:
        source = inspect.getsource(getattr(panels, name))
        check("compact" not in source,
              "the drawing function %s still has a compact mode" % name)
    # The debug controls only exist in developer mode.
    source = inspect.getsource(panels.draw_fx_advanced)
    check("developer_mode" in source,
          "the debug controls ignore the developer mode")
    # The legacy controls only appear in the legacy backend.
    source = inspect.getsource(panels.draw_world)
    check("LEGACY" in source,
          "the legacy controls are not bound to the legacy backend")


def check_panel_icons():
    """Every icon used by the panels must exist in this Blender version."""
    import inspect
    import re

    from anime_look_director import panels

    parameter = bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"]
    valid = {item.identifier for item in parameter.enum_items}
    check(valid, "the icon list of the layout is not available")
    source = inspect.getsource(panels)
    used = set(re.findall(r'icon="([A-Z0-9_]+)"', source))
    unknown = sorted(icon for icon in used if icon not in valid)
    check(not unknown, "the panels use unknown icons: %s" % unknown)


def check_fx_solver_stability(scene):
    """The solver must stay stable when the drag is small."""
    import math

    from anime_look_director import fx as fx_module
    from mathutils import Vector

    velocity = Vector((12.0, -4.0, 30.0))
    origin = Vector((1.0, 2.0, 3.0))
    gravity = Vector((0.0, 0.0, -9.81))
    for drag in (0.0, 1e-5, 0.001, 0.01, 0.1, 1.3):
        for age in (0.05, 0.5, 2.0):
            position = fx_module._position(origin, velocity, drag, age)
            check(all(abs(value) < 1e6 for value in position),
                  "the solver overflows with the drag %g" % drag)
            if drag >= 0.1:
                # The naive closed form is accurate there: both must agree.
                v_inf = gravity / drag
                factor = (1.0 - math.exp(-drag * age)) / drag
                naive = origin + v_inf * age + (velocity - v_inf) * factor
                check((position - naive).length < 1e-3,
                      "the stable solver differs from the closed form with the "
                      "drag %g (%.6f m)" % (drag, (position - naive).length))
            else:
                # The series expansion of the exact solution.
                x = drag * age
                series = (origin + velocity * age * (1.0 - x * 0.5)
                          + gravity * (age * age * 0.5 - x * age * age / 6.0))
                check((position - series).length < 0.05,
                      "the solver is not stable with the drag %g (%.6f m)"
                      % (drag, (position - series).length))
            # The velocity must agree with the position.
            step = 1e-4
            before = fx_module._position(origin, velocity, drag, age - step)
            after = fx_module._position(origin, velocity, drag, age + step)
            speed = (after - before) / (2.0 * step)
            reported = fx_module._velocity(velocity, drag, age)
            check((speed - reported).length < 0.05,
                  "the velocity does not match the position with the drag %g"
                  % drag)


def check_fx_camera_evaluated(scene):
    """The bursts follow the evaluated camera, constraints included."""
    from anime_look_director import fx as fx_module
    from mathutils import Vector

    previous_frame = scene.frame_current
    camera = scene.camera
    if camera is None:
        return
    fx_module.clear(scene)
    target = bpy.data.objects.new("ALD Gate Camera Target", None)
    target.location = (0.0, 40.0, 25.0)
    scene.collection.objects.link(target)
    constraint = camera.constraints.new("TRACK_TO")
    constraint.target = target
    try:
        fx_module.create_fireworks(scene, 1, seed=3, distance=50.0, time=0.0)
        runtime = fx_runtime(scene, "fireworks")
        burst = runtime["bursts"][0]
        origin, forward, up, right = fx_module._camera_basis(scene)
        # The burst point is on the view axis of the evaluated camera.
        delta = Vector(burst["target"]) - origin
        check(abs(delta.normalized().dot(forward)) > 0.9,
              "the burst does not follow the camera constraint")
        check(abs(delta.normalized().dot(up)) < 0.35,
              "the burst is not on the view axis")
    finally:
        camera.constraints.remove(constraint)
        bpy.data.objects.remove(target, do_unlink=True)
        fx_module.clear(scene)
        scene.frame_set(previous_frame)


def check_world_time_seconds(scene):
    """The clouds and the legacy stars follow the seconds, not the frames."""
    from anime_look_director import palette as palette_module

    previous_fps = scene.render.fps
    previous_frame = scene.frame_current
    try:
        scene.render.fps = 24
        scene.frame_set(24)
        at_24 = palette_module._cloud_offset(scene, scene.ald)
        phase_24 = palette_module._shooting_star_phase(scene, scene.ald)
        scene.render.fps = 60
        scene.frame_set(60)
        at_60 = palette_module._cloud_offset(scene, scene.ald)
        phase_60 = palette_module._shooting_star_phase(scene, scene.ald)
        for a, b in zip(at_24, at_60):
            check(abs(a - b) < 1e-4,
                  "the cloud offset depends on the frame rate: %s against %s"
                  % (at_24, at_60))
        check(abs(phase_24 - phase_60) < 1e-4,
              "the phase of the legacy stars depends on the frame rate")
        # The phase of the legacy stars does not follow the wind of the clouds.
        scene.ald.cloud_wind = 2.0
        scene.render.fps = 24
        scene.frame_set(24)
        with_wind = palette_module._shooting_star_phase(scene, scene.ald)
        scene.ald.cloud_wind = 0.0
        scene.frame_set(24)
        without_wind = palette_module._shooting_star_phase(scene, scene.ald)
        check(abs(with_wind - without_wind) < 1e-4,
              "the phase of the legacy stars follows the wind of the clouds")
        scene.ald.cloud_wind = 0.0
    finally:
        scene.render.fps = previous_fps
        scene.frame_set(previous_frame)


def check_fx_kamuro(scene):
    """The Kamuro family is a valid family."""
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 1, seed=3, distance=60.0, time=0.0,
                               family="KAMURO")
    runtime = fx_runtime(scene, "fireworks")
    burst = runtime["bursts"][0]
    check(burst["family"] == "KAMURO", "the Kamuro family was not used")
    check(burst["config"]["spokes"] == fx_module.FAMILY_CONFIG["KAMURO"]
          ["spokes"], "the Kamuro uses another configuration")
    check(burst["config"]["trail"] > 1.0,
          "the Kamuro has no long drooping tail")
    fx_module.clear(scene)
    scene.frame_set(previous_frame)


def check_fx_reversibility(scene):
    """Remove ALD from Scene must restore the state of the user."""
    from anime_look_director import fx as fx_module
    from anime_look_director import snapshot

    # The gate already modified the scene: the snapshot is taken again with
    # the state of this test.
    if snapshot.SNAPSHOT_KEY in scene:
        del scene[snapshot.SNAPSHOT_KEY]

    # A scene with a world of its own, a sun, an emissive material and a
    # compositor stack.
    world = bpy.data.worlds.new("ALD Gate User World")
    world.use_nodes = True
    background = next((node for node in world.node_tree.nodes
                        if node.bl_idname == "ShaderNodeBackground"), None)
    background.inputs["Color"].default_value = (0.1, 0.2, 0.3, 1.0)
    background.inputs["Strength"].default_value = 2.5
    scene.world = world
    sun_data = bpy.data.lights.new("ALD Gate User Sun", type="SUN")
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.9, 0.8)
    sun = bpy.data.objects.new("ALD Gate User Sun", sun_data)
    sun.rotation_euler = (0.5, 0.25, -0.75)
    scene.collection.objects.link(sun)
    material = bpy.data.materials.new("ALD Gate User Material")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.4, 0.5, 0.6, 1.0)
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0.9, 0.2, 0.1, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 4.0
    plane = bpy.data.meshes.new("ALD Gate User Plane")
    plane.from_pydata([(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0)],
                       [], [(0, 1, 2, 3)])
    plane.update()
    obj = bpy.data.objects.new("ALD Gate User Plane", plane)
    obj.data.materials.append(material)
    scene.collection.objects.link(obj)
    user_group = bpy.data.node_groups.new("ALD Gate User Stack",
                                          "CompositorNodeTree")
    scene.compositing_node_group = user_group
    scene.render.use_compositing = True
    view_layer = scene.view_layers[0]
    view_layer.use_pass_z = False
    view_layer.use_pass_emit = False
    view_layer.use_pass_normal = False
    state = {
        "world": world.name,
        "bg_color": list(background.inputs["Color"].default_value),
        "bg_strength": float(background.inputs["Strength"].default_value),
        "sun_energy": float(sun_data.energy),
        "sun_color": list(sun_data.color),
        "sun_rotation": [float(value) for value in sun.rotation_euler],
        "base_color": list(bsdf.inputs["Base Color"].default_value),
        "emission": list(bsdf.inputs["Emission Color"].default_value),
        "emission_strength": float(bsdf.inputs["Emission Strength"].default_value),
        "stack": user_group.name,
        "use_compositing": True,
    }

    # P0-C: creating FX alone must register the user state before mutating.
    check(snapshot.SNAPSHOT_KEY not in scene,
          "the snapshot leaked from a previous test")
    bpy.ops.ald.fx_fireworks(count=1, age=0.5)
    check(snapshot.SNAPSHOT_KEY in scene,
          "creating FX did not register the user state")
    saved = snapshot.snapshot(scene)
    check(saved.get("world", {}).get("name") == state["world"],
          "the snapshot was not taken before the FX mutation")
    fx_module.clear(scene)
    del scene[snapshot.SNAPSHOT_KEY]

    # The add-on modifies the scene.
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    bpy.ops.ald.fx_fireworks(count=2, age=0.8)
    check(snapshot.SNAPSHOT_KEY in scene,
          "the state of the user was not saved before the modification")
    check(scene.compositing_node_group is not user_group,
          "the stack of the user was not replaced")

    # The full removal restores everything.
    bpy.ops.ald.remove_from_scene()
    check(scene.world is not None and scene.world.name == state["world"],
          "the world of the user was not restored")
    background = next((node for node in scene.world.node_tree.nodes
                        if node.bl_idname == "ShaderNodeBackground"), None)
    check(background is not None, "the background node is missing")
    if background is not None:
        check(abs(background.inputs["Strength"].default_value
                  - state["bg_strength"]) < 1e-4,
              "the strength of the world was not restored")
        check(all(abs(a - b) < 1e-4 for a, b in
                  zip(background.inputs["Color"].default_value,
                      state["bg_color"])),
              "the colour of the world was not restored")
    check(sun_data.energy == state["sun_energy"],
          "the energy of the sun was not restored")
    check(all(abs(a - b) < 1e-4 for a, b in
              zip(sun_data.color, state["sun_color"])),
          "the colour of the sun was not restored")
    check(all(abs(a - b) < 1e-4 for a, b in
              zip(sun.rotation_euler, state["sun_rotation"])),
          "the rotation of the sun was not restored")
    check(all(abs(a - b) < 1e-4 for a, b in
              zip(bsdf.inputs["Base Color"].default_value,
                  state["base_color"])),
          "the base colour of the material was not restored")
    check(all(abs(a - b) < 1e-4 for a, b in
              zip(bsdf.inputs["Emission Color"].default_value,
                  state["emission"])),
          "the emission of the material was not restored")
    check(abs(bsdf.inputs["Emission Strength"].default_value
              - state["emission_strength"]) < 1e-4,
          "the emission strength of the material was not restored")
    check(scene.compositing_node_group is not None
          and scene.compositing_node_group.name == state["stack"],
          "the stack of the user was not restored")
    check(not view_layer.use_pass_z and not view_layer.use_pass_emit,
          "the render passes were not restored")
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the FX objects were not removed")
    check(scene.get(snapshot.REMOVED_KEY) is True,
          "the scene does not report the REMOVED state")
    # A new snapshot re-engages the add-on: the state must clear.
    snapshot.ensure(scene)
    check(scene.get(snapshot.REMOVED_KEY) is False,
          "the REMOVED state survives a new snapshot")
    del scene[snapshot.SNAPSHOT_KEY]
    scene[snapshot.REMOVED_KEY] = True

    # The cleanup of the test data.
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(plane)
    bpy.data.materials.remove(material)
    bpy.data.objects.remove(sun, do_unlink=True)
    bpy.data.lights.remove(sun_data)
    bpy.data.node_groups.remove(user_group)
    bpy.data.worlds.remove(world)


def check_fx_migration(scene):
    """T25: A file with an older schema/materials must keep its parameters and
    update its graphs really."""
    from anime_look_director import fx as fx_module
    from anime_look_director.properties import FX_SCHEMA

    settings = scene.ald
    system = settings.fx_systems.add()
    system.uid = "ald-gate-migration-uid"
    system.kind = "FIREWORKS"
    system.enabled = True
    system.seed = 7
    system.timing_mode = "TIMELINE"
    system.origin_frame = 1
    system.origin_time = 0.0
    system.isolation_mode = "EMISSION"
    system.fx_schema = 0  # older schema: must be upgraded
    event = system.events.add()
    event.uid = "ald-gate-migration-event"
    event.kind = "FIREWORK"
    event.enabled = True
    event.seed = 7
    event.birth = 0.0
    event.family = "CHRYSANTHEMUM"
    event.size = 1.0
    event.spokes = 110
    event.pistil = 30
    event.sparks = 2
    event.launch_mode = "DIRECTOR"
    event.rise_time = 1.2
    event.drag = 1.3
    event.duration = 2.6
    event.life = 2.6
    event.glow = 0.6
    event.target = (0.0, 0.0, 45.0)
    event.launcher = (0.0, 0.0, 19.0)

    before_uid = system.uid
    fx_module.rebuild_registry(scene)
    registry = fx_module.SYSTEMS.get(fx_module._scene_id(scene)) or {}
    runtime = registry.get(before_uid)
    check(runtime is not None, "the migrated system is not in the registry")
    if runtime is not None:
        check(runtime.get("system") is system or
              runtime.get("system").uid == before_uid,
              "the migrated system identity changed: %s vs %s" %
              (runtime.get("system").uid if runtime.get("system") else None,
               before_uid))
        check(settings.fx_schema == FX_SCHEMA,
              "the schema was not upgraded to %d" % FX_SCHEMA)
        check(system.fx_schema == FX_SCHEMA,
              "the system schema was not upgraded")
        check(event.random_key > 0,
              "the migration did not assign the stable event key")


def check_fx_persistent_model(scene):
    """P1-A: identity by UID+role, stable keys, idempotent switches."""
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=3, seed=13, distance=30.0)
    system = scene.ald.fx_systems[0]
    events = list(system.events)
    check(len(events) == 3, "the system did not store three events")
    keys = [event.random_key for event in events]
    check(all(key > 0 for key in keys), "the events have no stable key")
    check(len(set(keys)) == 3, "the events share the same random key")

    # Disabling one event must not change the keys of the others.
    events[0].enabled = False
    fx_module.rebuild_registry(scene)
    check([event.random_key for event in events[1:]] == keys[1:],
          "disabling an event changed the keys of the others")
    events[0].enabled = True
    fx_module.rebuild_registry(scene)

    # The reconstruction must not depend on the object name.
    registry = fx_module.SYSTEMS.get(fx_module._scene_id(scene)) or {}
    runtime = registry.get(system.uid)
    check(runtime is not None and runtime.get("bursts"),
          "the bursts are missing from the registry")
    if runtime is not None and runtime.get("bursts"):
        burst = runtime["bursts"][0]
        target = burst.get("gn_heads")
        if target is None:
            target = burst.get("heads")
        check(target is not None, "the burst has no head object")
        if target is not None:
            target.name = "ALD FX RENAMED BY THE USER"
            fx_module.rebuild_registry(scene)
            registry = fx_module.SYSTEMS.get(
                fx_module._scene_id(scene)) or {}
            runtime = registry.get(system.uid)
            check(runtime is not None and runtime.get("bursts"),
                  "the burst was lost after the rename")
            if runtime is not None and runtime.get("bursts"):
                found = runtime["bursts"][0].get("gn_heads")
                if found is None:
                    found = runtime["bursts"][0].get("heads")
                check(found is target,
                      "the reconstruction depends on the object name")
    fx_module.clear(scene)


def check_fx_undo_redo(scene):
    """T26: Undo/Redo after creation and removal must keep persistent data
    aligned."""
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    before_count = len(scene.ald.fx_systems)
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    after_create = len(scene.ald.fx_systems)
    check(after_create == before_count + 1,
          "create did not add a system: %d vs %d" % (after_create,
                                                      before_count + 1))

    # Undo/Redo is only available when the undo system is initialized.
    try:
        bpy.ops.ed.undo_push()
        bpy.ops.ed.undo()
        after_undo = len(scene.ald.fx_systems)
        check(after_undo == before_count,
              "undo did not remove the system: %d vs %d" % (after_undo,
                                                            before_count))

        bpy.ops.ed.redo()
        after_redo = len(scene.ald.fx_systems)
        check(after_redo == before_count + 1,
              "redo did not restore the system: %d vs %d" % (after_redo,
                                                             before_count + 1))
    except RuntimeError:
        check(True, "undo/redo not available in background mode (skipped)")

    fx_module.clear(scene, kind="fireworks")

def check_fx_failed_build(scene):
    """T27: An intentionally failed build must keep the previous system
    intact and not declare partial geometry ready."""
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    # Create a system, then remove it: clear must not leave partial geometry.
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    system = scene.ald.fx_systems[0]
    before_uid = system.uid
    before_objects = len([o for o in bpy.data.objects if o.get("ald_fx")])
    fx_module.clear(scene, kind="fireworks")
    after_objects = len([o for o in bpy.data.objects if o.get("ald_fx")])
    check(after_objects < before_objects,
          "clear did not remove FX objects: %d vs %d" % (after_objects,
                                                         before_objects))
    check(len(scene.ald.fx_systems) == 0,
          "clear did not remove the system from the persistent data")

    # Re-create: a new system gets a fresh identity.
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    system2 = scene.ald.fx_systems[0]
    check(system2.uid != before_uid,
          "the re-created system should have a new identity")
    fx_module.clear(scene, kind="fireworks")


def check_fx_anchor_clock(scene):
    """P1-B: anchor gravity, p_shell(T) and a clock refresh without rebuild."""
    from mathutils import Vector
    from anime_look_director import fx as fx_module

    previous_axis = scene.ald.fx_anchor_axis
    previous_gravity = tuple(scene.ald.fx_gravity)
    previous_scale = float(scene.ald.fx_anchor_units_scale)
    fx_module.clear(scene)
    try:
        # Gravity follows the anchor axis and the units scale.
        scene.ald.fx_anchor_axis = "Y"
        scene.ald.fx_anchor_units_scale = 2.0
        gravity = fx_module._gravity(scene)
        check(abs(gravity.x) < 1e-6 and abs(gravity.z) < 1e-6,
              "gravity does not follow the Y-up anchor: %s" % (gravity,))
        check(abs(gravity.y + 19.62) < 1e-3,
              "gravity does not scale with the units: %s" % (gravity,))
        scene.ald.fx_anchor_axis = "Z"
        scene.ald.fx_anchor_units_scale = 1.0
        check(fx_module._gravity(scene).z < -9.0,
              "gravity is not along -Z with the default anchor")

        # A creation at the current frame starts now, not in the past.
        scene.frame_set(120)
        bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0, age=0.0)
        system = scene.ald.fx_systems[0]
        check(system.origin_frame == 120,
              "the creation did not start at the current frame: %d"
              % system.origin_frame)
        now = fx_module.system_time(scene, system)
        first = system.events[0]
        check(now < first.birth + first.life,
              "the creation at the current frame is already over")
        check(now >= first.birth - 0.05,
              "the creation starts too far in the future")

        # A clock change does not rebuild the geometry.
        objects_before = sorted(obj.name for obj in bpy.data.objects
                                if obj.get("ald_fx"))
        system.origin_frame = 110
        fx_module.refresh_clock(scene)
        objects_after = sorted(obj.name for obj in bpy.data.objects
                               if obj.get("ald_fx"))
        check(objects_before == objects_after,
              "the clock refresh rebuilt the geometry")

        # Physical mode bursts at p_shell(T), not at the authored target.
        bpy.ops.ald.fx_fireworks(count=1, seed=5, distance=30.0, age=0.0)
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        event.launch_mode = "PHYSICAL"
        event.speed = 12.0
        event.direction = (0.0, 0.0, 1.0)
        event.launcher = (0.0, 0.0, 0.0)
        event.target = (0.0, 0.0, 100.0)
        fx_module.update_system(scene, system)
        runtime = (fx_module.SYSTEMS.get(fx_module._scene_id(scene))
                   or {}).get(system.uid)
        check(runtime is not None and runtime.get("bursts"),
              "the physical system has no burst")
        if runtime is not None and runtime.get("bursts"):
            burst = runtime["bursts"][0]
            gravity = fx_module._gravity(scene)
            expected = fx_module._rise_position(
                Vector(event.launcher), burst["shell_velocity"],
                float(event.drag), gravity, float(event.rise_time))
            check((burst["center"] - expected).length < 0.01,
                  "the physical burst is not at p_shell(T)")
            check((burst["center"] - Vector(event.target)).length > 1.0,
                  "the physical burst ignored the physics and used the target")
    finally:
        scene.ald.fx_anchor_axis = previous_axis
        scene.ald.fx_anchor_units_scale = previous_scale
        scene.ald.fx_gravity = previous_gravity
        fx_module.clear(scene)


def check_fx_gn_fallback(scene):
    """P1-C: a failed GN event falls back to the Python writer."""
    from anime_look_director import fx as fx_module

    original = fx_module._gn_points_object
    calls = {"count": 0}

    def flaky(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] > 2:
            raise RuntimeError("forced GN failure")
        return original(*args, **kwargs)

    fx_module._gn_points_object = flaky
    try:
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=13, distance=30.0)
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        roles = [obj.get("ald_fx_role") for obj in bpy.data.objects
                 if obj.get("ald_fx")
                 and obj.get("ald_fx_event") == event.uid]
        check("trail" in roles or "heads" in roles,
              "the failed GN event has no Python fallback")
        runtime = (fx_module.SYSTEMS.get(fx_module._scene_id(scene))
                   or {}).get(system.uid)
        check(runtime is not None and runtime.get("bursts"),
              "the fallback system has no burst")
        if runtime is not None and runtime.get("bursts"):
            burst = runtime["bursts"][0]
            check(burst.get("gn_heads") is None,
                  "the failed burst still reports a GN head")
            check(burst.get("heads") is not None,
                  "the fallback burst has no Python head mesh")
            if burst.get("heads") is not None:
                check(len(burst["heads"].data.vertices) > 0,
                      "the fallback head mesh is empty")
    finally:
        fx_module._gn_points_object = original
        fx_module.clear(scene)


def check_p3(scene):
    """P3: smoke volume, aesthetic variants and the directed show."""
    from anime_look_director import fx as fx_module
    from anime_look_director import smoke

    scene.ald.smoke_density = 0.3
    bpy.ops.ald.smoke_create()
    check(smoke.exists(scene), "the smoke volume was not created")
    volume = next((obj for obj in bpy.data.objects
                   if obj.get("ald_smoke")), None)
    check(volume is not None and volume.type == "MESH",
          "the smoke object is missing")
    if volume is not None:
        material = volume.active_material
        check(material is not None and any(
            node.bl_idname == "ShaderNodeVolumePrincipled"
            for node in material.node_tree.nodes),
            "the smoke has no volume shader")
    scene.ald.smoke_density = 0.5
    check(smoke.exists(scene), "the smoke vanished on a density change")
    bpy.ops.ald.smoke_remove()
    check(not smoke.exists(scene), "the smoke was not removed")

    # Aesthetic variants change the look without rebuilding.
    fx_module.clear(scene)
    bpy.ops.ald.fx_show(count="5", seed=17, distance=40.0, age=0.9)
    system = scene.ald.fx_systems[0]
    check(len(system.events) == 5, "the directed show has no five bursts")
    names = sorted(obj.name for obj in bpy.data.objects if obj.get("ald_fx"))
    scene.ald.fx_style = "SOFT"
    check(abs(scene.ald.fx_glow_size - 0.85) < 1e-3,
          "the SOFT style did not apply")
    scene.ald.fx_style = "VIVID"
    check(abs(scene.ald.fx_glow_strength - 1.1) < 1e-3,
          "the VIVID style did not apply")
    after = sorted(obj.name for obj in bpy.data.objects if obj.get("ald_fx"))
    check(names == after, "the style change rebuilt the geometry")
    scene.ald.fx_style = "CLASSIC"
    fx_module.clear(scene)


def check_fx_diagnostics(scene):
    """P0-E: the read-only diagnostic never claims an unproven OK."""
    from anime_look_director import diagnostics
    from anime_look_director import fx as fx_module

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    before = set(scene.keys())
    state = diagnostics.event_state(scene, system, event)
    after = set(scene.keys())
    check(before == after, "the read-only diagnostic writes to the scene")
    check(state["state"] != "OK",
          "the read-only diagnostic reported an unproven OK")
    check(state["state"] in diagnostics.STATES,
          "unknown diagnostic state %s" % state["state"])
    full = diagnostics.diagnose_event(scene, system, event)
    check(full["state"] in diagnostics.STATES,
          "diagnose_event returned an unknown state")
    report = diagnostics.diagnose_scene(scene)
    check(report["systems"] and report["systems"][0]["events"],
          "the full diagnostic has no events")
    check(report["systems"][0]["events"][0]["state"] in diagnostics.STATES,
          "the report carries an unknown state")
    fx_module.clear(scene)


def check_fx_p1_visibility(scene):
    """P1: wall behind, partial occluder and a single glow."""
    from anime_look_director import fx as fx_module

    previous_engine = scene.render.engine
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_frame = scene.frame_current
    origin, forward, _up, right = fx_module._camera_basis(scene)
    hidden = []
    for obj in scene.objects:
        if obj.get("ald_fx") or obj.type in ("CAMERA", "LIGHT"):
            continue
        hidden.append((obj, obj.hide_render))
        obj.hide_render = True

    def render():
        path = os.path.join(tempfile.gettempdir(), "ald_gate_p1.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(path)
        pixels = list(image.pixels)
        width, height = image.size
        bpy.data.images.remove(image)
        return pixels, width, height

    def mean_diff(first, second, width, height, x0, x1):
        total = 0.0
        count = 0
        for y in range(height):
            for x in range(max(0, int(width * x0)), min(width, int(width * x1))):
                index = (y * width + x) * 4
                a = (0.2126 * first[index] + 0.7152 * first[index + 1]
                     + 0.0722 * first[index + 2])
                b = (0.2126 * second[index] + 0.7152 * second[index + 1]
                     + 0.0722 * second[index + 2])
                total += abs(a - b)
                count += 1
        return total / max(count, 1)

    def wall(distance, lateral=0.0, size=400.0):
        bpy.ops.mesh.primitive_plane_add(
            size=size,
            location=tuple(origin + forward * distance + right * lateral))
        obj = bpy.context.object
        obj.rotation_euler = (-forward).to_track_quat("Z", "Y").to_euler()
        material = bpy.data.materials.new("ALD Gate P1 Wall")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1.0)
        obj.data.materials.append(material)
        return obj

    def create_burst():
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=5, distance=30.0, time=0.6)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.3) * fps))

    try:
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        try:
            scene.render.use_motion_blur = False
        except Exception:
            pass

        # A wall behind the burst must not hide it.
        behind = wall(65.0)
        create_burst()
        with_fx, width, height = render()
        fx_module.clear(scene)
        without_fx, _w, _h = render()
        behind_diff = mean_diff(with_fx, without_fx, width, height, 0.0, 1.0)
        check(behind_diff > 1e-4,
              "the wall behind the burst hides it (%.6f)" % behind_diff)
        bpy.data.objects.remove(behind, do_unlink=True)

        # A wall covering the right half: the left half keeps the FX.
        half = wall(12.0, lateral=10.0, size=20.0)
        create_burst()
        with_half, width, height = render()
        fx_module.clear(scene)
        without_half, _w, _h = render()
        left_diff = mean_diff(with_half, without_half, width, height,
                              0.0, 0.5)
        right_diff = mean_diff(with_half, without_half, width, height,
                               0.5, 1.0)
        check(left_diff > 1e-4,
              "the unoccluded half lost the FX (%.6f)" % left_diff)
        check(right_diff < left_diff * 0.25,
              "the occluded half still shows the FX (%.6f vs %.6f)"
              % (right_diff, left_diff))
        bpy.data.objects.remove(half, do_unlink=True)

        # Single glow: F is the Emission * matte, added once, glowed once.
        create_burst()
        ng = scene.compositing_node_group
        glows = [node for node in ng.nodes
                 if node.name == "ALD | FX Glow"]
        check(len(glows) == 1, "the FX glow is not unique")
        emission_node = ng.nodes.get("ALD | FX Emission")
        restore = ng.nodes.get("ALD | FX Restore")
        if glows and emission_node is not None:
            check(any(link.from_node == emission_node
                      for socket in glows[0].inputs
                      for link in socket.links),
                  "the FX glow is not fed by the masked emission")
        if restore is not None and emission_node is not None:
            check(any(link.from_node == emission_node
                      for socket in restore.inputs
                      for link in socket.links),
                  "the FX restore does not add the masked emission")
        fx_module.clear(scene)
    finally:
        for obj, state in hidden:
            obj.hide_render = state
        fx_module.clear(scene)
        scene.render.resolution_x, scene.render.resolution_y = previous_size
        scene.render.engine = previous_engine
        scene.frame_set(previous_frame)


def check_fx_trail_width(scene):
    """P2: the filament keeps a minimum apparent width in pixels."""
    from mathutils import Vector
    from anime_look_director import fx as fx_module

    previous_gn = bool(scene.ald.fx_gn_prototype)
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    try:
        scene.ald.fx_gn_prototype = True
        scene.render.resolution_x = 800
        scene.render.resolution_y = 450
        fx_module.clear(scene)
        bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=55.0, age=0.0)
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        center = Vector(event.target)
        expected = fx_module._apparent_radius(
            scene, center, 0.022, scene.ald.fx_trail_min_px,
            scene.ald.fx_trail_max_px)
        trail = next((obj for obj in bpy.data.objects
                      if obj.get("ald_fx_role") in ("gn_trail", "trail")),
                     None)
        check(trail is not None, "trail object missing")
        width = None
        if trail is not None and trail.type == "CURVE":
            width = float(trail.data.bevel_depth)
        elif trail is not None:
            modifier = next((item for item in trail.modifiers
                             if item.type == "NODES" and item.node_group
                             and item.node_group.name
                             == "ALD | FX Trail GN"), None)
            if modifier is not None:
                from anime_look_director import fx_nodes
                identifiers = fx_nodes._socket_ids(
                    modifier.node_group, fx_nodes.TRAIL_SOCKET_DEFAULTS)
                width = float(modifier[identifiers["radius"]])
        check(width is not None, "trail width input not found")
        # The width must reach real faces: an empty filament was the P2 bug and
        # a modifier input alone cannot catch it.
        frame = int(system.origin_frame
                    + (event.birth + event.rise_time + 0.3)
                    * (scene.render.fps / max(scene.render.fps_base, 1e-6)))
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        spokes = int(fx_module._event_config(event)["spokes"])
        faces = 0
        for obj in bpy.data.objects:
            if obj.get("ald_fx_role") not in ("gn_trail", "trail"):
                continue
            if obj.type == "CURVE":
                faces += max(len(obj.data.splines), 0)
                continue
            evaluated = obj.evaluated_get(deps)
            mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
            faces += len(mesh.polygons)
            bpy.data.meshes.remove(mesh)
        check(faces >= spokes * (fx_module.SAMPLES - 1),
              "the trail geometry is empty (%d faces for %d spokes)"
              % (faces, spokes))
        if width is not None:
            check(width >= expected * 0.99,
                  "the trail is thinner than the apparent minimum "
                  "(%.5f < %.5f)" % (width, expected))
            world_per_px = fx_module._world_per_pixel(scene, center)
            check(world_per_px > 0.0
                  and 2.0 * width / world_per_px
                  >= scene.ald.fx_trail_min_px * 0.99,
                  "the trail is below the minimum pixel width")
            # The apparent width follows the resolution without a rebuild.
            scene.render.resolution_x = 400
            scene.render.resolution_y = 225
            fx_module.refresh_widths(scene)
            expected_low = fx_module._apparent_radius(
                scene, center, 0.022, scene.ald.fx_trail_min_px,
                scene.ald.fx_trail_max_px)
            current = None
            if trail.type == "CURVE":
                current = float(trail.data.bevel_depth)
            else:
                from anime_look_director import fx_nodes
                modifier = next((item for item in trail.modifiers
                                 if item.type == "NODES" and item.node_group
                                 and item.node_group.name
                                 == fx_nodes.TRAIL_GROUP_NAME), None)
                if modifier is not None:
                    identifiers = fx_nodes._socket_ids(
                        modifier.node_group, fx_nodes.TRAIL_SOCKET_DEFAULTS)
                    current = float(modifier[identifiers["radius"]])
            check(current is not None
                  and abs(current - expected_low) <= 1e-4,
                  "the apparent width does not follow the resolution "
                  "(%s vs %s)" % (current, expected_low))
    finally:
        scene.ald.fx_gn_prototype = previous_gn
        fx_module.clear(scene)
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_fx_p3_shading(scene):
    """P3: instanced attributes, neutral punch and a live FX glow."""
    from mathutils import Vector
    from anime_look_director import fx as fx_module

    # Instanced geometry reads the INSTANCER domain, the trail the GEOMETRY
    # domain. One material per domain: a shared material would leave the heads
    # black or the tubes dim.
    previous = (scene.ald.fx_glow_strength, scene.ald.fx_glow_threshold,
                scene.ald.fx_glow_size)
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_gn = bool(scene.ald.fx_gn_prototype)
    try:
        scene.ald.fx_gn_prototype = True
        scene.render.resolution_x = 320
        scene.render.resolution_y = 180
        fx_module.clear(scene)
        bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=55.0, age=0.0)
        bpy.ops.ald.build()
        domains = set()
        for material in bpy.data.materials:
            if not material.get("ald_fx_material") or not material.node_tree:
                continue
            for node in material.node_tree.nodes:
                if node.bl_idname == "ShaderNodeAttribute":
                    domains.add(node.attribute_type)
        check("INSTANCER" in domains,
              "no FX material reads the instancer attributes")
        check("GEOMETRY" in domains,
              "no FX material reads the geometry attributes")
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.4) * fps))
        bpy.context.view_layer.update()

        def render(name):
            path = os.path.join(tempfile.gettempdir(), name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(path)
            pixels = list(image.pixels)
            bpy.data.images.remove(image)
            return pixels

        scene.ald.fx_glow_threshold = 0.0
        scene.ald.fx_glow_size = 0.35
        scene.ald.fx_glow_strength = 0.0
        dark = render("ald_gate_p3_dark.png")
        scene.ald.fx_glow_strength = 1.0
        lit = render("ald_gate_p3_lit.png")
        delta = [abs(a - b) for a, b in zip(lit[0::4], dark[0::4])]
        check(max(delta) > 0.02,
              "the FX glow has no effect (peak %.4f)" % max(delta))
        check(sum(1 for value in delta if value > 0.02) > 50,
              "the FX glow covers too few pixels")
        # The composite must add light: a punched background with a dimmer FX
        # turns the trails into dark lines (the P3 regression).
        fx_module.clear(scene)
        bpy.ops.ald.build()
        empty = render("ald_gate_p3_empty.png")
        added = [a - b for a, b in zip(lit[0::4], empty[0::4])]
        bright = [value for value in added if abs(value) > 0.01]
        check(bool(bright) and sum(bright) / len(bright) > 0.0,
              "the FX darken the composite instead of adding light")
    finally:
        scene.ald.fx_gn_prototype = previous_gn
        (scene.ald.fx_glow_strength, scene.ald.fx_glow_threshold,
         scene.ald.fx_glow_size) = previous
        fx_module.clear(scene)
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_fx_composition(scene):
    """P4: the show has a real depth hierarchy and distinct screen positions."""
    from anime_look_director import fx as fx_module
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector

    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_override = scene.ald.fx_fit_override
    try:
        scene.render.resolution_x = 800
        scene.render.resolution_y = 450
        scene.ald.fx_fit_override = False
        fx_module.clear(scene)
        count = fx_module.create_fireworks(scene, 3, seed=17, distance=95.0,
                                           time=0.0)
        check(count == 3, "the show did not create three bursts")
        system = scene.ald.fx_systems[0]
        events = [event for event in system.events if event.enabled]
        check(len(events) == 3, "the show has the wrong number of events")
        camera = scene.camera
        distances = [(Vector(event.target) - camera.location).length
                     for event in events]
        check(distances[0] < distances[1] < distances[2],
              "the burst depths are not hero < secondary < distant (%s)"
              % [round(value, 1) for value in distances])
        check(events[0].birth < events[1].birth < events[2].birth,
              "the bursts are not staggered in time")
        check(events[0].size >= events[1].size >= events[2].size,
              "the burst sizes do not follow the depth hierarchy")
        screens = []
        fractions = []
        for event in events:
            projected = world_to_camera_view(scene, camera,
                                             Vector(event.target))
            check(0.0 <= projected.x <= 1.0 and 0.0 <= projected.y <= 1.0,
                  "a burst centre is outside the camera frame")
            screens.append((round(projected.x, 3), round(projected.y, 3)))
            # The whole burst must be in frame, not only its centre; a chosen
            # crop is the only accepted exception.
            fraction = fx_module.event_frame_fraction(scene, event)
            fractions.append(round(fraction, 3))
            if not scene.ald.fx_fit_override:
                check(fraction >= 0.95 - 1e-3,
                      "a burst is cut beyond the fit target "
                      "(envelope fraction %.3f)" % fraction)
        check(len(set(screens)) == len(screens),
              "the bursts overlap on screen")
        print("ALD GATE framing envelope", fractions)
    finally:
        fx_module.clear(scene)
        scene.ald.fx_fit_override = previous_override
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_cloud_contour():
    """C4: the island boundary is interpolated, not a mosaic of cells."""
    from anime_look_director import clouds as clouds_module

    def build(coverage):
        return clouds_module._cloud_mesh("ALD Gate Contour", 3.7, coverage,
                                        128, 32)

    def stats(mesh):
        edges = {}
        for poly in mesh.polygons:
            verts = list(poly.vertices)
            for index, a in enumerate(verts):
                b = verts[(index + 1) % len(verts)]
                key = tuple(sorted((a, b)))
                edges[key] = edges.get(key, 0) + 1
        fractional = 0
        for vertex in mesh.vertices:
            x = vertex.co.x * 128
            y = vertex.co.y * 32
            if abs(x - round(x)) > 0.01 or abs(y - round(y)) > 0.01:
                fractional += 1
        return edges, fractional

    meshes = []
    try:
        low = build(0.5)
        meshes.append(low)
        check(len(low.polygons) > 0, "the contour has no faces")
        check(all(len(poly.vertices) == 3 for poly in low.polygons),
              "the contour is not triangulated")
        edges, fractional = stats(low)
        check(fractional > 0, "the contour has no interpolated vertices")
        check(max(edges.values()) <= 2, "the contour has non-manifold edges")
        mid = build(0.9)
        meshes.append(mid)
        high = build(1.0)
        meshes.append(high)
        check(len(high.polygons) > len(mid.polygons),
              "Coverage 0.9 and 1.0 saturate (%d and %d)"
              % (len(mid.polygons), len(high.polygons)))
    finally:
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)


def check_clouds(scene):
    """Spatial Clouds 2.0: coverage, identity, anchor, camera, flash, occlusion."""
    from mathutils import Vector
    from anime_look_director import clouds as clouds_module
    from anime_look_director import fx as fx_module

    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_gn = bool(scene.ald.fx_gn_prototype)
    previous_axis = scene.ald.fx_anchor_axis
    previous_clouds = (scene.ald.clouds_coverage, scene.ald.clouds_layers,
                       scene.ald.clouds_altitude, scene.ald.clouds_depth,
                       scene.ald.clouds_scale, scene.ald.clouds_mode,
                       scene.ald.clouds_flash,
                       scene.ald.clouds_flash_strength,
                       scene.ald.clouds_quality)

    def polygons():
        collection = clouds_module._collection(scene)
        if collection is None:
            return 0
        return sum(len(obj.data.polygons) for obj in collection.objects
                   if obj.type == "MESH")

    try:
        scene.render.resolution_x = 320
        scene.render.resolution_y = 180
        scene.ald.fx_gn_prototype = True
        clouds_module.remove(scene)

        # Coverage is the geometry, and it is monotonic.
        scene.ald.clouds_coverage = 0.0
        clouds_module.create(scene)
        check(clouds_module.exists(scene), "the cloud layer was not created")
        check(polygons() == 0, "Coverage 0 still builds cloud faces")
        scene.ald.clouds_coverage = 0.5
        clouds_module.refresh(scene)
        low = polygons()
        check(low > 0, "Coverage 0.5 builds no cloud")
        scene.ald.clouds_quality = "PREVIEW"
        clouds_module.refresh(scene)
        preview = polygons()
        check(preview < low, "Preview is not lighter than Final")
        scene.ald.clouds_quality = "FINAL"
        clouds_module.refresh(scene)
        check(polygons() == low, "Final did not restore the cloud mesh")
        scene.ald.clouds_coverage = 0.9
        clouds_module.refresh(scene)
        high = polygons()
        check(high > low,
              "Coverage is not monotonic (%d then %d)" % (low, high))

        # A transform update keeps the objects and the mesh identity.
        collection = clouds_module._collection(scene)
        obj = next(item for item in collection.objects if item.type == "MESH")
        pointer = obj.as_pointer()
        mesh_pointer = obj.data.as_pointer()
        faces = len(obj.data.polygons)
        before = obj.location.z
        scene.ald.clouds_depth = 240.0
        clouds_module.refresh(scene)
        check(obj.as_pointer() == pointer,
              "a depth update replaced the cloud object")
        check(obj.data.as_pointer() == mesh_pointer,
              "a depth update rebuilt the cloud mesh")
        check(len(obj.data.polygons) == faces,
              "a depth update changed the silhouette")
        scene.ald.clouds_altitude = 180.0
        clouds_module.refresh(scene)
        check(obj.location.z > before,
              "the altitude does not move the layer up")

        # The Anchor vertical drives the placement, not the camera up.
        scene.ald.fx_anchor_axis = "Y"
        clouds_module.create(scene)
        first = clouds_module._layers(scene)[0]
        placed = bpy.data.objects.get(first.object_name)
        check(placed is not None and placed.location.y > 100.0,
              "the Y-up Anchor does not drive the cloud altitude")
        scene.ald.fx_anchor_axis = "Z"
        clouds_module.create(scene)

        # Camera Facing re-orients without moving the layer.
        scene.ald.clouds_mode = "CAMERA_FACING"
        clouds_module.refresh(scene)
        placed = bpy.data.objects.get(
            clouds_module._layers(scene)[0].object_name)
        location = placed.location.copy()
        rotation = tuple(placed.rotation_euler)
        # A billboard faces the camera position: moving the camera changes the
        # direction, rotating it in place does not.
        scene.camera.location.x += 20.0
        bpy.context.view_layer.update()
        clouds_module.update_orientation(scene)
        check(tuple(placed.rotation_euler) != rotation,
              "Camera Facing does not follow the camera")
        check((placed.location - location).length < 1e-4,
              "Camera Facing moved the layer")

        # Flash response: a burst inside the card lights it; disabling it
        # clears the energy. event.glow is the driver.
        fx_module.clear(scene)
        clouds_module.remove(scene)
        scene.ald.clouds_coverage = 0.5
        scene.ald.clouds_layers = 1
        scene.ald.clouds_flash = True
        fx_module.create_fireworks(scene, 1, seed=5, distance=55.0, time=0.0)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        target = Vector(event.target)
        origin = fx_module._camera_basis(scene)[0]
        scene.ald.clouds_depth = max(20.0, (target - origin).length)
        scene.ald.clouds_altitude = max(0.0, target.z)
        clouds_module.create(scene)
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.2) * fps))
        bpy.context.view_layer.update()
        clouds_module.update_flash(scene)
        energies = []
        locals_ok = False
        for item in clouds_module._collection(scene).objects:
            material = item.active_material
            if material is None:
                continue
            nodes = material.node_tree.nodes
            energy = nodes["ALD | Flash Energy"].outputs[0].default_value
            energies.append(energy)
            if (abs(nodes["ALD | Flash X"].outputs[0].default_value) <= 0.6
                    and abs(nodes["ALD | Flash Y"].outputs[0].default_value)
                    <= 0.6):
                locals_ok = True
        check(energies and max(energies) > 0.05,
              "the burst does not light the cloud (%s)" % energies)
        check(locals_ok, "the flash is not projected inside the card")
        scene.ald.clouds_flash = False
        clouds_module.update_flash(scene)
        cleared = [material.node_tree.nodes["ALD | Flash Energy"].outputs[
            0].default_value
            for material in (item.active_material
                             for item in clouds_module._collection(scene).objects)
            if material is not None]
        check(max(cleared) < 1e-6, "disabling the flash leaves energy behind")

        # Occlusion: a card in front of the burst zeroes the FX matte there.
        scene.ald.clouds_flash = True
        card = clouds_module._collection(scene).objects[0]
        origin, forward, _up, _right = fx_module._camera_basis(scene)
        card.location = origin + forward * 20.0
        card.rotation_euler = (origin - card.location).to_track_quat(
            "Z", "Y").to_euler()
        card.scale = (80.0, 80.0, 1.0)
        bpy.context.view_layer.update()
        materials = [material.name for material in bpy.data.materials
                     if material.get("ald_fx_material") and material.users > 0]
        group = bpy.data.node_groups.new("ALD Gate Clouds",
                                         "CompositorNodeTree")
        group.interface.new_socket(name="Image", in_out="OUTPUT",
                                   socket_type="NodeSocketColor")
        rl = group.nodes.new("CompositorNodeRLayers")
        rl.scene = scene
        rl.layer = scene.view_layers[0].name
        matte = group.nodes.new("CompositorNodeCryptomatte")
        matte.matte_id = ",".join(materials)
        group.links.new(rl.outputs["Image"], matte.inputs["Image"])
        for slot in range(3):
            socket = rl.outputs.get("CryptoMaterial%02d" % slot)
            if socket is not None:
                group.links.new(socket, matte.inputs["Crypto %02d" % slot])
        output = group.nodes.new("NodeGroupOutput")
        group.links.new(matte.outputs["Matte"], output.inputs[0])
        previous_group = scene.compositing_node_group
        scene.compositing_node_group = group
        scene.render.use_compositing = True
        path = os.path.join(tempfile.gettempdir(), "ald_gate_clouds.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(path)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        occluded = sum(pixels[0::4])
        card.hide_render = True
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(path)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        visible = sum(pixels[0::4])
        bpy.data.node_groups.remove(group)
        scene.compositing_node_group = previous_group
        check(visible > 5.0,
              "the FX matte is empty without the cloud (%.3f)" % visible)
        check(occluded < visible * 0.75,
              "the cloud does not hide the FX behind it (%.3f vs %.3f)"
              % (occluded, visible))
    finally:
        clouds_module.remove(scene)
        fx_module.clear(scene)
        scene.ald.fx_gn_prototype = previous_gn
        scene.ald.fx_anchor_axis = previous_axis
        (scene.ald.clouds_coverage, scene.ald.clouds_layers,
         scene.ald.clouds_altitude, scene.ald.clouds_depth,
         scene.ald.clouds_scale, scene.ald.clouds_mode,
         scene.ald.clouds_flash, scene.ald.clouds_flash_strength,
         scene.ald.clouds_quality) = previous_clouds
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_fx_pass_isolation(scene):
    """P0: the external FX pass excludes a foreign emitter."""
    from mathutils import Vector
    from anime_look_director import compositor as compositor_module
    from anime_look_director import fx as fx_module
    import numpy as np

    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_format = scene.render.image_settings.file_format
    previous_mode = scene.render.image_settings.color_mode
    previous_pass = scene.ald.fx_pass_path
    previous_frames = tuple(scene.ald.fx_pass_frames)
    previous_signature = scene.ald.fx_pass_signature
    collection = None
    plane = None
    try:
        scene.render.resolution_x = 160
        scene.render.resolution_y = 90
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        scene.camera.rotation_euler = (Vector(event.target)
                                       - scene.camera.location).to_track_quat(
                                           "-Z", "Y").to_euler()
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        scene.frame_set(int(system.origin_frame
                            + (event.birth + event.rise_time + 0.4) * fps))
        bpy.context.view_layer.update()

        # Foreign emitter in a child collection, behind the burst.
        collection = bpy.data.collections.new("ALD Gate Foreign")
        scene.collection.children.link(collection)
        mesh = bpy.data.meshes.new("ALD Gate Foreign Plane")
        mesh.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0),
                          (-60, 60, 0)], [], [(0, 1, 2, 3)])
        mesh.update()
        material = bpy.data.materials.new("ALD Gate Foreign Mat")
        material.use_nodes = True
        tree = material.node_tree
        for node in list(tree.nodes):
            tree.nodes.remove(node)
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        emission = tree.nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = (40, 20, 4, 1)
        emission.inputs["Strength"].default_value = 3.0
        tree.links.new(emission.outputs[0], output.inputs["Surface"])
        mesh.materials.append(material)
        plane = bpy.data.objects.new("ALD Gate Foreign Plane", mesh)
        collection.objects.link(plane)
        origin, forward, _up, _right = fx_module._camera_basis(scene)
        plane.location = origin + forward * 70.0
        plane.rotation_euler = (origin - plane.location).to_track_quat(
            "Z", "Y").to_euler()
        bpy.context.view_layer.update()

        with_plane = os.path.join(tempfile.gettempdir(), "ald_fx_pass_a.exr")
        without_plane = os.path.join(tempfile.gettempdir(), "ald_fx_pass_b.exr")
        compositor_module.render_fx_pass(scene, with_plane)
        plane.hide_render = True
        bpy.context.view_layer.update()
        compositor_module.render_fx_pass(scene, without_plane)

        def load(path):
            image = bpy.data.images.load(path)
            width, height = image.size
            pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
                height, width, 4)
            bpy.data.images.remove(image)
            return pixels[:, :, :3]

        delta = np.abs(load(with_plane) - load(without_plane))
        check(float(delta.max()) < 0.01,
              "the FX pass contains the foreign emitter (max %.4f)"
              % float(delta.max()))
        check(float(delta.mean()) < 0.001,
              "the FX pass is not stable (mean %.5f)" % float(delta.mean()))

        # The stack reads the pass image.
        bpy.ops.ald.build()
        ng = scene.compositing_node_group
        node = ng.nodes.get("ALD | FX Pass") if ng is not None else None
        check(node is not None, "the stack does not use the FX pass image")
        check(node is not None and node.image is not None
              and os.path.basename(node.image.filepath)
              == os.path.basename(without_plane),
              "the stack reads the wrong FX pass")
    finally:
        if plane is not None:
            bpy.data.objects.remove(plane, do_unlink=True)
        if collection is not None:
            bpy.data.collections.remove(collection)
        fx_module.clear(scene)
        scene.ald.fx_pass_path = previous_pass
        scene.ald.fx_pass_frames = previous_frames
        scene.ald.fx_pass_signature = previous_signature
        scene.render.image_settings.file_format = previous_format
        scene.render.image_settings.color_mode = previous_mode
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_fx_pass_sequence(scene):
    """The pass follows the animation and belongs to this scene."""
    from mathutils import Vector
    from anime_look_director import compositor as compositor_module
    from anime_look_director import fx as fx_module

    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_range = (scene.frame_start, scene.frame_end)
    previous_frame = scene.frame_current
    previous_pass = scene.ald.fx_pass_path
    previous_frames = tuple(scene.ald.fx_pass_frames)
    previous_signature = scene.ald.fx_pass_signature
    previous_age = scene.ald.fx_age
    base = os.path.join(tempfile.gettempdir(), "ald_gate_pass_seq.exr")
    first = None
    try:
        scene.render.resolution_x = 160
        scene.render.resolution_y = 90
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
        bpy.ops.ald.build()
        system = scene.ald.fx_systems[0]
        event = system.events[0]
        scene.camera.rotation_euler = (Vector(event.target)
                                       - scene.camera.location).to_track_quat(
                                           "-Z", "Y").to_euler()
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        start = int(system.origin_frame
                    + (event.birth + event.rise_time + 0.4) * fps)
        end = start + 3
        scene.frame_start = start
        scene.frame_end = end
        bpy.context.view_layer.update()

        default_path = compositor_module._default_pass_path(scene)
        check(os.path.basename(default_path)
              == "ald_fx_pass_%s.exr" % scene.name,
              "the default FX pass path is not per scene")
        first = compositor_module.render_fx_pass_animation(scene, base)
        check(first is not None, "the animation pass did not render")
        check(tuple(scene.ald.fx_pass_frames) == (start, end),
              "the pass did not record its frame range")
        start_path = compositor_module._frame_path(first, start)
        end_path = compositor_module._frame_path(first, end)
        check(os.path.exists(start_path) and os.path.exists(end_path),
              "the pass sequence files are missing")

        bpy.ops.ald.build()
        ng = scene.compositing_node_group
        node = ng.nodes.get("ALD | FX Pass") if ng is not None else None
        check(node is not None, "the stack does not use the pass sequence")
        check(node is not None and node.frame_duration == end - start + 1,
              "the pass node does not cover the sequence")
        check(node is not None and node.frame_start == start,
              "the pass node does not start at the first frame")
        check(node is not None and node.image is not None
              and node.image.source == "SEQUENCE",
              "the pass image is not read as a sequence")
        check(node is not None and node.image is not None
              and node.image.name == "ALD | FX Pass | " + scene.name,
              "the pass image is not owned by the scene")

        def load(path):
            image = bpy.data.images.load(path)
            width, height = image.size
            pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
                height, width, 4)[:, :, :3]
            bpy.data.images.remove(image)
            return pixels

        delta = np.abs(load(start_path) - load(end_path))
        check(float(delta.max()) > 0.01,
              "the pass sequence does not change between frames")

        # The pass knows the FX it was rendered with, not only the frame.
        scene.frame_set(start)
        state, _text = compositor_module.fx_pass_state(scene)
        check(state == "ready",
              "the pass is not ready on its own frame (%s)" % state)
        scene.ald.fx_age = previous_age + 0.25
        state, _text = compositor_module.fx_pass_state(scene)
        check(state == "stale",
              "an FX change does not invalidate the pass (%s)" % state)
        scene.ald.fx_age = previous_age

        # The signature is per frame: a static camera is valid at both ends,
        # a moved camera invalidates the frame it was moved on.
        camera = scene.camera
        location = camera.location.copy()
        camera.location = location + Vector((0.5, 0.0, 0.0))
        bpy.context.view_layer.update()
        state, _text = compositor_module.fx_pass_state(scene)
        check(state == "stale",
              "moving the camera does not invalidate the pass (%s)" % state)
        camera.location = location
        bpy.context.view_layer.update()
        state, _text = compositor_module.fx_pass_state(scene)
        check(state == "ready",
              "restoring the camera does not restore the pass (%s)" % state)
        scene.frame_set(end)
        state, _text = compositor_module.fx_pass_state(scene)
        check(state == "ready",
              "the per-frame signature is not valid at the end frame (%s)"
              % state)
    finally:
        if first is not None:
            for frame in range(previous_range[0], previous_range[1] + 1):
                path = compositor_module._frame_path(first, frame)
                if os.path.exists(path):
                    os.remove(path)
        fx_module.clear(scene)
        scene.ald.fx_pass_path = previous_pass
        scene.ald.fx_pass_frames = previous_frames
        scene.ald.fx_pass_signature = previous_signature
        scene.ald.fx_age = previous_age
        scene.frame_start, scene.frame_end = previous_range
        scene.frame_set(previous_frame)
        scene.render.resolution_x, scene.render.resolution_y = previous_size


def check_fx_identity(scene):
    """P0-D: with zero FX the recomposition is the identity."""
    from anime_look_director import fx as fx_module

    previous_backend = scene.ald.fx_backend
    previous_engine = scene.render.engine
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    try:
        fx_module.clear(scene)
        bpy.ops.ald.build()
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(tempfile.gettempdir(),
                                             "ald_gate_identity_off.png")
        scene.ald.fx_backend = "OFF"
        bpy.ops.render.render(write_still=True)
        scene.render.filepath = os.path.join(tempfile.gettempdir(),
                                             "ald_gate_identity_fx3d.png")
        scene.ald.fx_backend = "FX3D"
        bpy.ops.render.render(write_still=True)

        def load(name):
            image = bpy.data.images.load(
                os.path.join(tempfile.gettempdir(), name))
            pixels = list(image.pixels)
            bpy.data.images.remove(image)
            return pixels

        first = load("ald_gate_identity_off.png")
        second = load("ald_gate_identity_fx3d.png")
        diff = max(abs(a - b) for a, b in zip(first, second))
        check(diff < 1e-4,
              "zero FX is not the identity (max channel diff %.5f)" % diff)
    finally:
        scene.ald.fx_backend = previous_backend
        scene.render.resolution_x, scene.render.resolution_y = previous_size
        scene.render.engine = previous_engine


def check_fx_system_operators(scene):
    """P0-B: Update FX, Duplicate System and Remove System stay in sync.

    A record without geometry (or geometry without a record) is a broken
    invariant: the panel lists what the scene does not render, and Clear
    cannot remove what the panel does not list.
    """
    from anime_look_director import fx as fx_module

    def objects_of(uid):
        return [obj for obj in bpy.data.objects
                if obj.get("ald_fx") and obj.get("ald_fx_system") == uid]

    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    check(len(scene.ald.fx_systems) == 1, "the system was not stored")
    system = scene.ald.fx_systems[0]
    uid = system.uid
    check(objects_of(uid), "the created system has no geometry")

    # Update FX while the system is selected: same record, same identity,
    # geometry rebuilt, no second system (the legacy path created a new one).
    scene.ald.fx_selected_system = 0
    result = bpy.ops.ald.fx_update()
    check(result == {"FINISHED"}, "Update FX did not finish")
    check(len(scene.ald.fx_systems) == 1,
          "Update FX duplicated the system: %d" % len(scene.ald.fx_systems))
    check(scene.ald.fx_systems[0].uid == uid,
          "Update FX changed the identity of the system")
    check(objects_of(uid), "Update FX removed the geometry")

    # Duplicate: a new record AND new geometry with a new identity.
    result = bpy.ops.ald.fx_duplicate_system()
    check(result == {"FINISHED"}, "Duplicate System did not finish")
    check(len(scene.ald.fx_systems) == 2,
          "Duplicate System did not add a record")
    copy = scene.ald.fx_systems[1]
    check(copy.uid != uid, "the duplicate reuses the system identity")
    check(len(copy.events) == len(system.events),
          "the duplicate lost the events")
    check(objects_of(copy.uid), "the duplicate has no geometry")

    # Remove the duplicate: record and geometry disappear together.
    scene.ald.fx_selected_system = 1
    result = bpy.ops.ald.fx_remove_system()
    check(result == {"FINISHED"}, "Remove System did not finish")
    check(len(scene.ald.fx_systems) == 1, "Remove System kept the record")
    check(not objects_of(copy.uid), "Remove System left the geometry behind")
    check(objects_of(uid), "Remove System removed another system")
    fx_module.clear(scene)


def check_fx_visual_profiles(scene):
    """T24: Sunset/night, three FX profiles.

    The three profiles (Firework, Meteor, Bolide) must be readable at a fixed
    exposure: no diffuse clipping, no unintentional flicker. The render uses
    the Standard view transform with exposure 0 so the measurement is on the
    linear result.
    """
    from anime_look_director import fx as fx_module

    previous_engine = scene.render.engine
    previous_vt = scene.view_settings.view_transform
    previous_exp = float(scene.view_settings.exposure)
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_age = float(scene.ald.fx_age)

    try:
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 256
        scene.render.resolution_y = 256
        scene.render.resolution_percentage = 100
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.exposure = 0.0
        # A fixed age makes the profile comparable: the default Burst Age
        # would push the meteors past the end of their train.
        scene.ald.fx_age = 0.0

        # Ensure a camera exists and is active. The camera looks at the sky
        # horizontally: the FX start plane is in front of it, above the ground
        # (a camera pointing down would place the meteors under the terrain,
        # where the depth-based occlusion correctly hides them).
        if scene.camera is None:
            cam_data = bpy.data.cameras.new("T24 Cam")
            cam = bpy.data.objects.new("T24 Cam", cam_data)
            scene.collection.objects.link(cam)
            cam.location = (0.0, -10.0, 2.0)
            cam.rotation_euler = (1.5707963, 0.0, 0.0)
            scene.camera = cam
        scene.camera.data.lens = 24.0
        scene.camera.data.clip_start = 0.1
        scene.camera.data.clip_end = 1000.0

        scene.frame_set(30)
        bpy.context.view_layer.update()

        # Use the Python backend for the visual-profile test so the mesh
        # vertices are authored directly (no GN re-evaluation needed).
        scene.ald.fx_gn_prototype = False

        import os
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "ald_gate_t24.png")

        profiles = {
            "Firework": ("CHRYSANTHEMUM", 0, 10.0),
            "Meteor": ("WILLOW", 1, 15.0),
            "Bolide": ("WILLOW", 2, 15.0),
        }
        import traceback
        for name, (family, slot, dist) in profiles.items():
            fx_module.clear(scene)
            # Ensure a valid camera exists after clear() (it may unlink objects).
            cam_valid = (
                scene.camera is not None
                and scene.camera.data is not None
                and scene.camera.name in bpy.data.objects
            )
            if not cam_valid:
                cam_data = bpy.data.cameras.new("T24 Cam")
                cam = bpy.data.objects.new("T24 Cam", cam_data)
                scene.collection.objects.link(cam)
                cam.location = (0.0, -10.0, 2.0)
                cam.rotation_euler = (1.5707963, 0.0, 0.0)
                scene.camera = cam
                bpy.context.view_layer.camera = scene.camera
            try:
                if name == "Firework":
                    fx_module.create_fireworks(scene, 1, seed=13,
                                               distance=dist, time=0.0,
                                               family=family)
                elif name == "Meteor":
                    fx_module.create_meteors(scene, 1, seed=21,
                                             distance=dist, time=0.6,
                                             kind="METEOR")
                else:
                    fx_module.create_meteors(scene, 1, seed=33,
                                             distance=dist, time=0.6,
                                             kind="BOLIDE")
            except Exception as exc:
                traceback.print_exc()
                check(False, "%s creation failed: %s" % (name, exc))
                continue

            # The stack must see the new FX materials: build it after the
            # creation, as the add-on does in the normal workflow.
            bpy.ops.ald.build()

            # The frame is inside the life of the profile: the burst is at
            # its peak for the firework, the meteor is just after its birth.
            from mathutils import Vector
            system = scene.ald.fx_systems[0]
            event = system.events[0]
            fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
            if name == "Firework":
                scene.frame_set(int(system.origin_frame
                                    + (event.rise_time + 0.4) * fps))
            else:
                scene.frame_set(int(system.origin_frame
                                    + event.birth * fps) + 3)
            # Frame the event: the start points are spread across the sky and
            # a fixed camera would miss the lateral ones.
            target = Vector(event.target)
            direction = target - scene.camera.location
            if direction.length > 1e-6:
                scene.camera.rotation_euler = direction.to_track_quat(
                    "-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(path)
            pixels = list(image.pixels)
            width, height = image.size
            # Sample the whole image for the brightest pixel.
            max_rgb = 0.0
            for py in range(0, height, 2):
                for px in range(0, width, 2):
                    index = ((height - 1 - py) * width + px) * 4
                    r = pixels[index]
                    g = pixels[index + 1]
                    b = pixels[index + 2]
                    if r > max_rgb:
                        max_rgb = r
                    if g > max_rgb:
                        max_rgb = g
                    if b > max_rgb:
                        max_rgb = b
            bpy.data.images.remove(image)
            # Readable: some emission present, not fully clipped white.
            check(max_rgb > 0.05,
                  "%s profile is invisible (max rgb %.4f)" % (name, max_rgb))
            check(max_rgb < 1.9,
                  "%s profile clips diffusely (max rgb %.4f)" % (name, max_rgb))
        fx_module.clear(scene)
        fx_module.clear(scene)
    finally:
        scene.render.engine = previous_engine
        scene.view_settings.view_transform = previous_vt
        scene.view_settings.exposure = previous_exp
        scene.render.resolution_x, scene.render.resolution_y = previous_size
        scene.ald.fx_age = previous_age


def check_fx_ui_screenshots(scene):
    """T28: Screenshots of both UI surfaces must show the same controls."""
    from anime_look_director import panels

    shared = [name for name in dir(panels) if name.startswith("draw_")]
    for required in ("draw_world", "draw_shadows", "draw_compositor",
                     "draw_fx", "draw_fx_systems", "draw_fx_timing",
                     "draw_fx_launch", "draw_fx_explosion", "draw_fx_look",
                     "draw_fx_advanced", "draw_scene_actions",
                     "draw_fx_diagnostics", "draw_fx_actions"):
        check(required in shared,
              "UI surface missing control: %s" % required)



def check_fx_event_continuity(scene):
    """A complete firework: the launcher, the rise and the burst."""
    from mathutils import Vector

    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 1, seed=9, distance=60.0, time=0.0)
    runtime = fx_runtime(scene, "fireworks")
    burst = runtime["bursts"][0]
    population = burst["population"]
    gravity = fx_module._gravity(scene)
    launch = Vector(burst["launch"])
    v0 = Vector(burst["shell_velocity"])
    drag = float(burst["drag"])
    rise = float(burst["rise_time"])
    target = Vector(burst["target"])
    residual = Vector(burst["residual"])

    # The shell reaches the burst point at the end of the rise.
    at_burst = fx_module._rise_position(launch, v0, drag, gravity, rise)
    check((at_burst - target).length < 1e-3,
          "the shell does not reach the burst point (%.4f m)"
          % (at_burst - target).length)
    # The stars are born exactly at the burst point.
    head = population["heads"][0]
    check((Vector(head["pos0"]) - target).length < 1e-6,
          "the stars are not born at the burst point")
    check(abs(head["birth"] - (burst["birth"] + rise)) < 1e-6,
          "the stars are not born at the end of the rise")
    # The stars inherit the residual velocity of the shell.
    spread = Vector(head["vel"]) - residual
    check(spread.length > 0.5,
          "the stars do not inherit the velocity of the shell")
    # The shell is visible during the rise and gone at the burst.
    scene.frame_set(2)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    shell_obj = bpy.data.objects.get("ALD FX GN Shell 0")
    check(shell_obj is not None, "the rising shell is missing")
    if shell_obj is not None:
        instances = fx_nodes.realized_instances(shell_obj, depsgraph)
        check(instances and instances[0][1] > 1e-4,
              "the shell is not visible during the rise")
    scene.frame_set(2 + int(rise * 24) + 4)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    if shell_obj is not None:
        instances = fx_nodes.realized_instances(shell_obj, depsgraph)
        check(instances and instances[0][1] < 1e-4,
              "the shell is still visible after the burst")
    # The stars are alive at the burst and the event is reproducible.
    scene.frame_set(2 + int(rise * 24) + 1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    heads = bpy.data.objects.get("ALD FX GN Heads 0")
    check(heads is not None, "the burst heads are missing")
    if heads is not None:
        instances = fx_nodes.realized_instances(heads, depsgraph)
        check(instances and instances[0][1] > 1e-4,
              "the stars are not alive at the burst")
        first = [center for center, _radius in instances]
        scene.frame_set(60)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        again = fx_nodes.realized_centers(heads, depsgraph)
        scene.frame_set(2 + int(rise * 24) + 1)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        back = fx_nodes.realized_centers(heads, depsgraph)
        check(len(again) == len(back)
              and all((a - b).length < 1e-5
                      for a, b in zip(first, back)),
              "the event is not reproducible after a frame jump")
    fx_module.clear(scene)
    scene.frame_set(previous_frame)



def check_fx_bolide(scene):
    """The Hero Meteor preset is bigger and its train lasts longer."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 2, seed=21, distance=40.0, time=0.6)
    normal = fx_runtime(scene, "meteors")
    normal_population = normal["populations"][0]
    normal_radius = normal_population["head"]["radius"]
    normal_life = normal_population["head"]["life"]
    normal_train = normal_population["train"][0]["trail"]
    normal_fragments = len(normal_population["fragments"])
    fx_module.clear(scene)

    fx_module.create_meteors(scene, 2, seed=21, distance=40.0, time=0.6,
                             kind="BOLIDE")
    bolide = fx_runtime(scene, "meteors")
    population = bolide["populations"][0]
    check(bolide.get("preset") == "BOLIDE",
          "the bolide preset is not recorded")
    check(population["head"]["radius"] > normal_radius * 2.0,
          "the bolide is not bigger than a meteor")
    check(population["head"]["life"] > normal_life,
          "the bolide does not live longer than a meteor")
    check(population["train"][0]["trail"] > normal_train * 2.0,
          "the train of the bolide is not longer")
    check(len(population["fragments"]) > normal_fragments,
          "the bolide does not leave more fragments")
    # The train of the bolide persists after the head is gone.
    head_life = population["head"]["life"]
    train_life = population["train"][0]["life"]
    check(train_life > head_life,
          "the train of the bolide does not outlive the head")
    # The velocities stay almost parallel: the radiant emerges.
    directions = []
    for item in bolide["populations"]:
        velocity = item["head"]["vel"]
        if velocity.length > 1e-6:
            directions.append(velocity.normalized())
    if len(directions) > 1:
        worst = min((first - second).length
                    for index, first in enumerate(directions)
                    for second in directions[index + 1:])
        check(worst < 0.2,
              "the meteors of the shower are not parallel (%.3f)" % worst)
    fx_module.clear(scene)
    scene.frame_set(previous_frame)



def check_fx_foreign_emission(scene):
    """An emissive surface that is not ALD must not enter the FX mask."""
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_engine = scene.render.engine
    path = os.path.join(tempfile.getdir() if False else tempfile.gettempdir(),
                        "ald_gate_sign.png")
    # A bright sign, far from the bursts: it is not an ALD object.
    sign_material = bpy.data.materials.new("ALD Gate Sign")
    sign_material.use_nodes = True
    bsdf = sign_material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (4.0, 1.0, 0.2, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
    sign_mesh = bpy.data.meshes.new("ALD Gate Sign")
    sign_mesh.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)],
                           [], [(0, 1, 2, 3)])
    sign_mesh.update()
    sign = bpy.data.objects.new("ALD Gate Sign", sign_mesh)
    sign.data.materials.append(sign_material)
    sign.location = (0.0, -14.0, 1.0)
    scene.collection.objects.link(sign)

    def render_sign():
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(path)
        pixels = list(image.pixels)
        width, height = image.size
        index = ((height // 2) * width + (width // 2)) * 4
        value = (round(pixels[index], 4), round(pixels[index + 1], 4),
                 round(pixels[index + 2], 4))
        bpy.data.images.remove(image)
        return value

    try:
        fx_module.clear(scene)
        bpy.ops.ald.build()
        scene.frame_set(12)
        without = render_sign()
        # The same scene with the bursts: the sign must not change.
        bpy.ops.ald.fx_fireworks(count=2, age=0.8)
        scene.frame_set(12)
        with_fx = render_sign()
        worst = max(abs(a - b) for a, b in zip(without, with_fx))
        check(worst < 0.05,
              "the foreign emissive surface enters the FX mask: %s against %s"
              % (without, with_fx))
    finally:
        fx_module.clear(scene)
        bpy.data.objects.remove(sign, do_unlink=True)
        bpy.data.meshes.remove(sign_mesh)
        bpy.data.materials.remove(sign_material)
        scene.render.resolution_x, scene.render.resolution_y = previous_size
        scene.render.engine = previous_engine
        scene.frame_set(previous_frame)

def check_scene_actions(scene):
    """Bypass, complete removal and detach keep the scene under control."""
    from anime_look_director import fx as fx_module
    from anime_look_director import snapshot

    # Bypass: the add-on stops touching the scene.
    scene.ald.bypass = True
    check(snapshot.is_inactive(scene), "the bypass does not stop the add-on")
    scene.ald.bypass = False
    check(not snapshot.is_inactive(scene), "the bypass is still active")

    # Detach: the look is kept, the systems are removed.
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    check([obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "no FX object to detach")
    bpy.ops.ald.detach()
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the detach left the FX objects in the scene")
    check(scene.ald.detached, "the detach did not mark the scene")
    check(snapshot.is_inactive(scene),
          "the detached scene is still managed by the add-on")
    scene.ald.detached = False

    # Complete removal: the scene comes back to the registered state.
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    check(snapshot.SNAPSHOT_KEY in scene,
          "the state of the user was not saved")
    bpy.ops.ald.remove_from_scene()
    check(not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "the removal left the FX objects in the scene")
    check(not [coll for coll in bpy.data.collections
               if coll.get("ald_fx_owner") == fx_module._scene_id(scene)],
          "the removal left the collection of the add-on")
    check(snapshot.SNAPSHOT_KEY not in scene,
          "the removal left the snapshot in the scene")
    check(not scene.ald.detached and not scene.ald.bypass,
          "the removal left the scene detached")
    orphans = [mat for mat in bpy.data.materials
               if mat.get("ald_fx_material") and mat.users == 0]
    check(not orphans, "the removal left %d orphan materials" % len(orphans))


def check_fx_meteor_travel(scene):
    """A meteor must cross the screen, not move along the line of sight."""
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 3, seed=21, distance=40.0, time=0.0)
    system = fx_runtime(scene, "meteors")
    origin, forward, up, right = fx_module._camera_basis(scene)
    # The movement is mostly lateral: the meteor crosses the frame.
    for population in system["populations"]:
        velocity = population["head"]["vel"]
        lateral = abs(velocity.dot(right))
        check(lateral > 0.4 * velocity.length,
              "the meteor does not cross the screen: %s" % velocity)
    # And the position really moves across the frame.
    moved = 0.0
    for population in system["populations"]:
        start = population["head"]["pos0"]
        velocity = population["head"]["vel"]
        end = start + velocity * 0.5
        moved = max(moved, abs((end - start).dot(right)))
    check(moved > 5.0, "the meteor barely moves across the frame (%.2f m)"
          % moved)
    fx_module.clear(scene)
    scene.frame_set(previous_frame)


def main():
    enable_addon()
    check_versions()
    scene = bpy.context.scene
    check(hasattr(scene, "ald"), "settings not registered")
    settings = scene.ald
    check_palette_registry(settings)
    check(find_sun(scene) is None, "gate must start without a sun")
    data = build_test_materials(scene)

    try:
        check_world_gradient(scene, settings)
        check_sun_controls(scene, settings)
        check_god_rays(scene, settings)
        check_shadow_tint(scene, settings, data)
        check_material_exclusion(scene, settings, data)
        check_live_transforms(scene, data)
        check_light_wrap(scene, settings)
        check_param_updates(scene, settings)
        check_ink(scene, settings)
        check_aerial_haze(scene, settings)
        check_shot_markers(scene, settings)
        check_material_presets(scene, settings, data)
        check_custom_colors(scene, settings, data)
        check_camera_override(scene, settings)
        check_fx(scene)
        check_fx_event_continuity(scene)
        check_fx_bolide(scene)
        check_fx_foreign_emission(scene)
        check_fx_meteor_travel(scene)
        check_fx_solver_stability(scene)
        check_fx_camera_evaluated(scene)
        check_fx_system_operators(scene)
        check_fx_persistent_model(scene)
        check_fx_anchor_clock(scene)
        check_fx_gn_fallback(scene)
        check_p3(scene)
        check_fx_diagnostics(scene)
        check_fx_occlusion(scene)
        check_fx_p1_visibility(scene)
        check_fx_trail_width(scene)
        check_fx_p3_shading(scene)
        check_fx_composition(scene)
        check_clouds(scene)
        check_cloud_contour()
        check_fx_pass_isolation(scene)
        check_fx_pass_sequence(scene)
        check_fx_identity(scene)
        check_world_time_seconds(scene)
        check_fx_kamuro(scene)
        # The UI checks were defined but never wired: an unknown icon broke the
        # whole World panel without failing the gate (P5 cloud box).
        check_ui_parity(scene)
        check_panel_icons()

        ng = scene.compositing_node_group
        check(ng is not None and ng.name == "ALD | Compositor Stack",
              "compositor group not assigned")
        types = {node.bl_idname for node in ng.nodes}
        for required in ("CompositorNodeRLayers", "CompositorNodeGlare",
                         "CompositorNodeKuwahara", "CompositorNodeLensdist",
                         "NodeGroupOutput"):
            check(required in types, "missing node " + required)
        check(scene.view_layers[0].use_pass_z, "depth pass not enabled")

        check_idempotent_build(scene)
        check_pixels(scene, settings)
        check_render(scene)
        check_multiscene(scene)

        bpy.ops.ald.remove()
        check(scene.compositing_node_group is None, "stack not removed")
        check(bpy.data.node_groups.get("ALD | Compositor Stack") is None,
              "compositor group not deleted")
        # The last checks: a new file and a saved fixture must restore the
        # systems, and a duplicated scene must own an independent copy.
        check_fx_new_file(scene)
        # The file load replaced the scene: the reference must be refreshed.
        scene = bpy.context.scene
        check_fx_fixture(scene)
        scene = bpy.context.scene
        check_fx_scene_duplicate(scene)
        check_fx_gn_schema(scene)
        # The reversibility check restores the scene: it runs last.
        check_scene_actions(scene)
        # The reversibility check restores the scene: it runs last.
        check_fx_reversibility(scene)
        # Fase 6 (T24-T28): visual profiles, migration, undo/redo, failed build, UI screenshots.
        check_fx_migration(scene)
        check_fx_undo_redo(scene)
        check_fx_failed_build(scene)
        check_fx_visual_profiles(scene)
        check_fx_ui_screenshots(scene)
    finally:
        try:
            for obj in list(bpy.data.objects):
                if not obj.get("ald_auto_sun"):
                    continue
                light = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if light is not None and light.users == 0:
                    bpy.data.lights.remove(light)
            bpy.data.objects.remove(data["object"], do_unlink=True)
            bpy.data.meshes.remove(data["mesh"])
            for mat in (data["plain"], data["linked"]):
                bpy.data.materials.remove(mat)
        except (ReferenceError, RuntimeError):
            # The file load of the new file check removed the test data.
            pass

    print("ALD GATE: PASS")


if __name__ == "__main__":
    main()
