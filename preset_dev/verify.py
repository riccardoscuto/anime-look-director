"""Headless gate for Anime Look Director.

Run:
  blender -b --factory-startup --python-exit-code 1 --python preset_dev/verify.py
"""

import os
import sys
import tempfile
import tomllib
import math

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_VERSION = (2, 10, 0)
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
    """A building in front of the burst must hide the particles."""
    from anime_look_director import fx as fx_module

    previous_frame = scene.frame_current
    previous_size = (scene.render.resolution_x, scene.render.resolution_y)
    previous_engine = scene.render.engine
    path = os.path.join(tempfile.gettempdir(), "ald_gate_fx_occlusion.png")
    origin, forward, _up, _right = fx_module._camera_basis(scene)
    material = bpy.data.materials.new("ALD Gate Occluder")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.05, 0.05, 1.0)
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (0.8, 0.05, 0.05, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.0
    # The wall stands between the camera and the burst.
    bpy.ops.mesh.primitive_plane_add(size=400.0,
                                     location=tuple(origin + forward * 12.0))
    occluder = bpy.context.object
    occluder.rotation_euler = (-forward).to_track_quat("Z", "Y").to_euler()
    # The gate geometry must not hide the occluder.
    hidden = []
    for obj in scene.objects:
        if obj is occluder or obj.get("ald_fx"):
            continue
        if obj.type == "CAMERA" or obj.type == "LIGHT":
            continue
        hidden.append((obj, obj.hide_render))
        obj.hide_render = True
    occluder.data.materials.append(material)
    try:
        fx_module.clear(scene)
        fx_module.create_fireworks(scene, 1, seed=5, distance=30.0, time=0.6)
        scene.frame_set(12)
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if os.path.exists(path):
            image = bpy.data.images.load(path)
            width, height = image.size
            pixels = list(image.pixels)
            index = ((height // 2) * width + (width // 2)) * 4
            red = pixels[index]
            green = pixels[index + 1]
            blue = pixels[index + 2]
            check(red > 0.4 and red > green * 1.4 and red > blue * 1.4,
                  "the occluder does not hide the burst (%.3f, %.3f, %.3f)"
                  % (red, green, blue))
            bpy.data.images.remove(image)
    finally:
        for obj, state in hidden:
            obj.hide_render = state
        bpy.data.objects.remove(occluder, do_unlink=True)
        bpy.data.materials.remove(material)
        fx_module.clear(scene)
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
        mask = ng.nodes.get("ALD | FX Mask")
        restore = ng.nodes.get("ALD | FX Restore")
        check(mask is not None, "FX mask node missing")
        check(restore is not None, "FX restore node missing")
        if mask is not None and restore is not None:
            check(any(link.from_node == mask
                      for link in restore.inputs["Factor"].links),
                  "FX restore is not driven by the emission mask")

    fx_module.clear(scene)
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
    """The node group must reproduce the Python solver exactly."""
    from mathutils import Vector

    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    scene.frame_set(12)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    registry = fx_module.SYSTEMS[fx_module._scene_id(scene)]
    burst = registry["fireworks"]["bursts"][1]
    config = burst["config"]
    center = burst["center"]
    birth = burst["birth"]
    seed = burst["seed"]
    spoke_count = config["spokes"]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    age = 12 / fps + float(scene.ald.fx_age) - birth

    heads = bpy.data.objects.get("ALD FX GN Heads 1")
    check(heads is not None, "geometry nodes burst heads missing")
    if heads is not None:
        centers = fx_nodes.realized_centers(heads, depsgraph)
        check(len(centers) == spoke_count,
              "geometry nodes burst produced %d heads" % len(centers))
        worst = 0.0
        for spoke in range(spoke_count):
            life, v0 = fx_module._gn_star_data(seed, burst["index"], config,
                                               spoke, spoke_count)
            if not (0.0 < age <= life):
                continue
            expected = fx_module._position(center, v0, config["drag"], age)
            worst = max(worst, (expected - centers[spoke]).length)
        check(worst < 1e-3,
              "geometry nodes heads drift from the solver (%.6f m)" % worst)

    grains = bpy.data.objects.get("ALD FX GN Beads 1 0")
    check(grains is not None, "geometry nodes burst grains missing")
    if grains is not None:
        grain_centers = fx_nodes.realized_centers(grains, depsgraph)
        spokes = [s for s in range(spoke_count) if s % 3 == 0]
        check(len(grain_centers) == len(spokes) * fx_module.SAMPLES,
              "geometry nodes grains count mismatch")
        worst = 0.0
        for bead_index, spoke in enumerate(spokes):
            life, v0 = fx_module._gn_star_data(seed, burst["index"], config,
                                               spoke, spoke_count)
            alive = 0.0 <= age <= life
            trail_time = min(age, config["trail"]) if alive else 0.0
            for step in range(fx_module.SAMPLES):
                tau = trail_time * (1.0 - step / (fx_module.SAMPLES - 1.0))
                sample_age = max(0.0, age - tau)
                point = fx_module._position(center, v0, config["drag"],
                                            sample_age)
                profile = step / (fx_module.SAMPLES - 1.0)
                scatter = 0.10 * burst["size_scale"] * (1.0 - profile)
                jitter = Vector((
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 16 + step, 20, -scatter,
                                          scatter),
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 16 + step, 21, -scatter,
                                          scatter),
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 16 + step, 22, -scatter,
                                          scatter),
                ))
                expected = point + jitter
                actual = grain_centers[bead_index * fx_module.SAMPLES + step]
                worst = max(worst, (expected - actual).length)
        check(worst < 1e-3,
              "geometry nodes grains drift from the solver (%.6f m)" % worst)

    pistil = bpy.data.objects.get("ALD FX GN Pistil 1")
    check(pistil is not None, "geometry nodes pistil missing")
    if pistil is not None:
        centers = fx_nodes.realized_centers(pistil, depsgraph)
        pistil_count = config["pistil"]
        check(len(centers) == pistil_count,
              "geometry nodes pistil count mismatch")
        worst = 0.0
        for spoke in range(pistil_count):
            _direction, life, v0, alive = fx_module._star_state(
                seed, burst["index"], spoke, pistil_count, config, age,
                speed_scale=0.68, life_scale=0.85, hash_offset=500)
            if not alive:
                continue
            drag = config["drag"] * 1.2
            expected = fx_module._position(center, v0, drag, age)
            worst = max(worst, (expected - centers[spoke]).length)
        check(worst < 1e-3,
              "geometry nodes pistil drifts from the solver (%.6f m)" % worst)

    pistil_grains = bpy.data.objects.get("ALD FX GN Pistil Grains 1")
    check(pistil_grains is not None, "geometry nodes pistil grains missing")
    if pistil_grains is not None:
        centers = fx_nodes.realized_centers(pistil_grains, depsgraph)
        pistil_count = config["pistil"]
        check(len(centers) == pistil_count * fx_module.SAMPLES,
              "geometry nodes pistil grains count mismatch")
        worst = 0.0
        for spoke in range(pistil_count):
            _direction, life, v0, alive = fx_module._star_state(
                seed, burst["index"], spoke, pistil_count, config, age,
                speed_scale=0.68, life_scale=0.85, hash_offset=500)
            drag = config["drag"] * 1.2
            trail_time = min(age, config["trail"] * 0.6) if alive else 0.0
            for step in range(fx_module.SAMPLES):
                tau = trail_time * (1.0 - step / (fx_module.SAMPLES - 1.0))
                sample_age = max(0.0, age - tau)
                expected = fx_module._position(center, v0, drag, sample_age)
                index = spoke * fx_module.SAMPLES + step
                worst = max(worst, (expected - centers[index]).length)
        check(worst < 1e-3,
              "geometry nodes pistil grains drift (%.6f m)" % worst)

    sparks = bpy.data.objects.get("ALD FX GN Sparks 1")
    check(sparks is not None, "geometry nodes sparks missing")
    if sparks is not None:
        centers = fx_nodes.realized_centers(sparks, depsgraph)
        spark_count = spoke_count * config["sparks"]
        check(len(centers) == spark_count,
              "geometry nodes sparks count mismatch")
        worst = 0.0
        for spoke in range(spoke_count):
            life, v0 = fx_module._gn_star_data(seed, burst["index"], config,
                                               spoke, spoke_count)
            for child in range(config["sparks"]):
                emit = fx_module._hash_range(seed, burst["index"],
                                             spoke * 8 + child, 4, 0.05,
                                             life * 0.55)
                child_life = fx_module._hash_range(seed, burst["index"],
                                                  spoke * 8 + child, 5, 0.45,
                                                  1.5)
                child_age = age - emit
                if child_age <= 0.0 or child_age > child_life:
                    continue
                parent_pos = fx_module._position(center, v0, config["drag"],
                                                 emit)
                parent_vel = fx_module._velocity(v0, config["drag"], emit)
                perturb = Vector((
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 8 + child, 6, -1.6, 1.6),
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 8 + child, 7, -1.6, 1.6),
                    fx_module._hash_range(seed, burst["index"],
                                          spoke * 8 + child, 8, -1.6, 1.6),
                )) * 1.2
                child_v0 = parent_vel * 0.35 + perturb
                expected = fx_module._position(parent_pos, child_v0, 2.4,
                                              child_age)
                index = spoke * config["sparks"] + child
                worst = max(worst, (expected - centers[index]).length)
        check(worst < 1e-3,
              "geometry nodes sparks drift from the solver (%.6f m)" % worst)

    fx_module.clear(scene)
    scene.frame_set(previous_frame)
    check_fx_gn_meteors(scene)
    check_fx_gn_determinism(scene)
    check_fx_gn_limits(scene)
    check_fx_gn_children(scene)
    check_fx_occlusion(scene)

    # The Python solver stays available as a fallback.
    scene.ald.fx_gn_prototype = False
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 2, seed=5, distance=30.0, time=0.6)
    python_objects = [obj for obj in bpy.data.objects if obj.get("ald_fx")]
    python_heads = [obj for obj in python_objects
                    if obj.name.endswith(" Heads")]
    check(python_heads, "python fallback did not build the star heads")
    check(not any(mod.type == "NODES" for obj in python_objects
                  for mod in obj.modifiers),
          "python fallback still uses the node group")
    check(any(obj.type == "MESH" and len(obj.data.vertices) > 12
              for obj in python_objects),
          "python fallback did not write the particle geometry")
    fx_module.clear(scene)
    scene.ald.fx_gn_prototype = True


def check_fx_gn_meteors(scene):
    """The meteors must be evaluated by the node group as well."""
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes

    previous_frame = scene.frame_current
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 3, seed=21, distance=40.0, time=0.6)
    scene.frame_set(20)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    system = fx_module.SYSTEMS[fx_module._scene_id(scene)]["meteors"]
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
        radiant = system["radiant"]
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
            spread = fx_module.Vector((
                fx_module._hash_range(seed, index, 0, 3, -0.09, 0.09),
                fx_module._hash_range(seed, index, 0, 4, -0.06, 0.06),
                fx_module._hash_range(seed, index, 0, 5, -0.04, 0.04),
            ))
            direction = (radiant + spread).normalized()
            start = origin + direction * distance * 0.9
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
        # The last check: a new file must reinitialise the add-on.
        check_fx_new_file(scene)
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
