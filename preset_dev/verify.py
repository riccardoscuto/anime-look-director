"""Headless gate for Anime Look Director.

Run:
  blender -b --factory-startup --python-exit-code 1 --python preset_dev/verify.py
"""

import os
import sys
import tempfile
import tomllib

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_VERSION = (0, 2, 0)
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
    check(background.inputs["Color"].is_linked
          and same(background.inputs["Color"].links[0].from_node, node),
          "background is not driven by the world gradient")

    expected = palette_module.preset(settings.palette)
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

    sun_data = bpy.data.lights.new("ALD_GATE_SUN", "SUN")
    sun = bpy.data.objects.new("ALD_GATE_SUN", sun_data)
    scene.collection.objects.link(sun)
    data = build_test_materials(scene)

    try:
        check_world_gradient(scene, settings)
        check_shadow_tint(scene, settings, data)
        check_light_wrap(scene, settings)

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

        bpy.ops.ald.remove()
        check(scene.compositing_node_group is None, "stack not removed")
        check(bpy.data.node_groups.get("ALD | Compositor Stack") is None,
              "compositor group not deleted")
    finally:
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.objects.remove(data["object"], do_unlink=True)
        bpy.data.meshes.remove(data["mesh"])
        for mat in (data["plain"], data["linked"]):
            bpy.data.materials.remove(mat)

    print("ALD GATE: PASS")


if __name__ == "__main__":
    main()
