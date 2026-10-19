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
EXPECTED_VERSION = (0, 3, 1)
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

    bpy.ops.ald.apply_palette()
    nodes = [n for n in scene.world.node_tree.nodes if n.get("ald_world_gradient")]
    check(len(nodes) == 1, "world gradient duplicated on re-apply")
    groups = [g for g in bpy.data.node_groups if g.name == "ALD | World Gradient"]
    check(len(groups) == 1, "world gradient group duplicated")

    settings.world_gradient = False
    check(gradient_node(scene) is None, "gradient not removed when disabled")
    check(not background.inputs["Color"].is_linked,
          "background still linked after disabling the gradient")
    check(close(background.inputs["Color"].default_value,
                expected["world_color"] + (1.0,)),
          "flat world color not restored")

    settings.world_gradient = True
    check(gradient_node(scene) is not None, "gradient not restored when enabled")

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
    sun.rotation_euler = (-math.pi / 2.0, 0.0, 0.0)
    bpy.context.view_layer.update()

    try:
        settings.god_rays = True
        bpy.context.view_layer.update()
        bpy.ops.ald.build()
        ng = scene.compositing_node_group
        beams = [n for n in ng.nodes
                 if n.bl_idname == "CompositorNodeGlare"
                 and n.inputs["Type"].default_value == "Sun Beams"]
        check(len(beams) == 1, "god rays node missing")
        position = beams[0].inputs["Sun Position"].default_value
        check(abs(position[0] - 0.5) < 0.01
              and abs(position[1] - 0.5) < 0.01,
              "god rays sun position not projected")

        from anime_look_director import compositor
        sun.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        compositor.update_god_rays(scene)
        check(beams[0].inputs["Strength"].default_value <= TOLERANCE,
              "god rays not muted with the sun behind the camera")
        sun.rotation_euler = (-math.pi / 2.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        compositor.update_god_rays(scene)
        check(abs(beams[0].inputs["Strength"].default_value
                  - settings.god_rays_strength) <= TOLERANCE,
              "god rays not restored when the sun comes back")
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

    bpy.ops.ald.clear_shadow_tint()
    check(tint_node(checked) is None, "shadow tint not removed from plain material")
    check(not data["plain_base"].is_linked,
          "Base Color link not removed after clearing tint")
    check(close(data["plain_base"].default_value, (0.8, 0.2, 0.2, 1.0)),
          "original Base Color not restored")
    check(tint_node(data["linked"]) is None,
          "shadow tint not removed from linked material")
    check(data["linked_base"].is_linked
          and same(data["linked_base"].links[0].from_node, data["rgb"]),
          "original Base Color link not restored")
    check(len(checked.node_tree.nodes) == data["plain_nodes"],
          "material node count not restored")

    settings.shadow_tint = True
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
    types = [n.bl_idname for n in scene.compositing_node_group.nodes]
    check("CompositorNodeAlphaOver" not in types,
          "light wrap not removed when disabled")
    settings.light_wrap = True
    types = [n.bl_idname for n in scene.compositing_node_group.nodes]
    check("CompositorNodeAlphaOver" in types,
          "light wrap not restored when enabled")


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

        tint_max, tint_mean, tint_ratio = diff_stats(base, tinted)
        wrap_max, wrap_mean, wrap_ratio = diff_stats(base, wrapped)
        print("ALD GATE pixels: shadow max=%.4f mean=%.5f ratio=%.4f; "
              "wrap max=%.4f mean=%.5f ratio=%.4f"
              % (tint_max, tint_mean, tint_ratio,
                 wrap_max, wrap_mean, wrap_ratio))
        check(tint_max > 0.01 and tint_ratio > 0.001,
              "shadow tint does not affect the render")
        check(wrap_max > 0.01 and 0.001 < wrap_ratio < 0.8,
              "light wrap does not affect the edges only")
    finally:
        scene.camera = old_camera
        settings.light_wrap = True
        settings.light_wrap_strength = 0.4
        settings.light_wrap_size = 24.0
        settings.shadow_tint = True
        settings.shadow_tint_strength = 0.35
        settings.shadow_tint_distance = 0.6
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


def check_shot_markers(scene, settings):
    from anime_look_director import shots
    from anime_look_director import palette as palette_module

    marker_a = scene.timeline_markers.new(
        shots.marker_name("GOLDEN_HOUR"), frame=10)
    marker_b = scene.timeline_markers.new(
        shots.marker_name("NEON_NIGHT"), frame=20)
    marker_c = None
    try:
        settings.use_shot_markers = True
        scene.frame_set(10)
        shots.apply_for_frame(scene, force=True)
        check(settings.palette == "GOLDEN_HOUR",
              "shot marker A did not apply its palette")
        check(shots.active_marker(scene) == "GOLDEN_HOUR",
              "active shot marker A wrong")

        scene.frame_set(20)
        shots.apply_for_frame(scene, force=True)
        check(settings.palette == "NEON_NIGHT",
              "shot marker B did not apply its palette")
        expected = palette_module.preset("NEON_NIGHT")
        node = gradient_node(scene)
        check(node is not None
              and close(node.inputs["Horizon Color"].default_value,
                        expected["horizon_color"]),
              "shot palette did not update the world")
        check(scene.get("ald_active_shot") == "NEON_NIGHT",
              "active shot not tracked")

        scene.frame_set(30)
        result = bpy.ops.ald.mark_shot()
        check("FINISHED" in result, "mark shot operator failed")
        marker_c = next((m for m in scene.timeline_markers
                         if m.frame == 30), None)
        check(marker_c is not None
              and marker_c.name == shots.marker_name("NEON_NIGHT"),
              "mark shot did not create the marker")
    finally:
        for marker in (marker_a, marker_b, marker_c):
            if marker is not None:
                scene.timeline_markers.remove(marker)
        settings.use_shot_markers = False
        if "ald_active_shot" in scene:
            del scene["ald_active_shot"]
        scene.frame_set(1)
        settings.palette = "GOLDEN_HOUR"


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

    for index in range(len(obj.data.materials) - 1, -1, -1):
        slot = obj.data.materials[index]
        if slot == metal or slot == skin or slot == emission:
            obj.data.materials.pop(index=index)
    bpy.data.materials.remove(metal)
    bpy.data.materials.remove(skin)
    bpy.data.materials.remove(emission)
    obj.select_set(False)


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


def main():
    enable_addon()
    check_versions()
    scene = bpy.context.scene
    check(hasattr(scene, "ald"), "settings not registered")
    settings = scene.ald
    check(find_sun(scene) is None, "gate must start without a sun")
    data = build_test_materials(scene)

    try:
        check_world_gradient(scene, settings)
        check_god_rays(scene, settings)
        check_shadow_tint(scene, settings, data)
        check_light_wrap(scene, settings)
        check_shot_markers(scene, settings)
        check_material_presets(scene, settings, data)

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
    finally:
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

    print("ALD GATE: PASS")


if __name__ == "__main__":
    main()
