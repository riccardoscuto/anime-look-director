"""Measure the real stack F with and without a foreign emitter.

The stack output is temporarily rewired to the `ALD | FX Emission` result, so
the rendered EXR is exactly the F the compositor adds. This avoids the temp
compositor used by emission_isolation.py, where render_pre never runs.

Run (after building the scene)::

    blender -b --factory-startup --python preset_dev/real_f_probe.py
"""

import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx


def read(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def render(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return read(path)


def main():
    out = os.path.join(HERE, "real_f_probe")
    os.makedirs(out, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = "NEON_NIGHT"
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    fx.clear(scene)
    fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    camera.rotation_euler = (Vector(event.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * 24))
    bpy.context.view_layer.update()
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"

    ng = scene.compositing_node_group
    output = next(node for node in ng.nodes
                  if node.bl_idname == "NodeGroupOutput")
    original = output.inputs[0].links[0].from_socket if output.inputs[0].links \
        else None
    fx_node = ng.nodes.get("ALD | FX Emission")
    result = next(socket for socket in fx_node.outputs
                  if socket.name == "Result" and socket.type == "RGBA")
    # A second link would leave the original output in place: remove it first.
    for link in list(output.inputs[0].links):
        ng.links.remove(link)
    ng.links.new(result, output.inputs[0])

    # Foreign emitter behind the burst, in a child collection.
    collection = bpy.data.collections.new("Foreign Test")
    scene.collection.children.link(collection)
    mesh = bpy.data.meshes.new("Foreign")
    mesh.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)],
                     [], [(0, 1, 2, 3)])
    mesh.update()
    material = bpy.data.materials.new("ForeignMat")
    material.use_nodes = True
    tree = material.node_tree
    for node in list(tree.nodes):
        tree.nodes.remove(node)
    output_node = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (40, 20, 4, 1)
    emission.inputs["Strength"].default_value = 3.0
    tree.links.new(emission.outputs[0], output_node.inputs["Surface"])
    mesh.materials.append(material)
    plane = bpy.data.objects.new("Foreign", mesh)
    collection.objects.link(plane)
    origin, forward, _up, _right = fx._camera_basis(scene)
    plane.location = origin + forward * 70.0
    plane.rotation_euler = (origin - plane.location).to_track_quat(
        "Z", "Y").to_euler()
    bpy.context.view_layer.update()

    with_plane = render(scene, os.path.join(out, "f_with_plane.exr"))
    plane.hide_render = True
    bpy.context.view_layer.update()
    without_plane = render(scene, os.path.join(out, "f_without_plane.exr"))
    delta = np.abs(with_plane - without_plane).max(axis=2)
    print("REAL F delta mean %.6f max %.6f lit %d"
          % (float(delta.mean()), float(delta.max()),
             int((delta > 0.03).sum())))

    if original is not None:
        ng.links.new(original, output.inputs[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
