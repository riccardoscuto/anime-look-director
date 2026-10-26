"""P5-B: a foreign emissive surface must not contaminate the FX contribution.

The FX path uses the Emission pass multiplied by a binary presence mask; the
mask comes from the Cryptomatte of the FX materials. A bright emissive plane is
placed behind the burst (the FX must be unaffected) and in front of it (the FX
must be hidden). The differences are measured at the FX pixels.

Run::

    blender -b --factory-startup --python preset_dev/emission_isolation.py
"""

import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "emission_isolation")


def read(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def plane(scene, camera, name, distance, size=40.0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-size, -size, 0), (size, -size, 0),
                      (size, size, 0), (-size, size, 0)], [], [(0, 1, 2, 3)])
    mesh.update()
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    for node in list(tree.nodes):
        tree.nodes.remove(node)
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (40.0, 20.0, 4.0, 1.0)
    emission.inputs["Strength"].default_value = 3.0
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection = bpy.data.collections.get("Foreign Emissive")
    if collection is None:
        collection = bpy.data.collections.new("Foreign Emissive")
        scene.collection.children.link(collection)
    collection.objects.link(obj)
    from anime_look_director import fx
    origin, forward, up, right = fx._camera_basis(scene)
    obj.location = origin + forward * distance
    obj.rotation_euler = (origin - obj.location).to_track_quat(
        "Z", "Y").to_euler()
    return obj


def shot_matte(scene):
    """The Cryptomatte matte of the FX materials, for the pixel selection."""
    materials = [material.name for material in bpy.data.materials
                 if material.get("ald_fx_material") and material.users > 0]
    group = bpy.data.node_groups.new("P5B Matte", "CompositorNodeTree")
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
    previous = scene.compositing_node_group
    scene.compositing_node_group = group
    path = os.path.join(OUT, "matte.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    bpy.data.node_groups.remove(group)
    scene.compositing_node_group = previous
    return pixels[:, :, 0]


def shot_emission(scene):
    group = bpy.data.node_groups.new("P5B Emission", "CompositorNodeTree")
    group.interface.new_socket(name="Image", in_out="OUTPUT",
                               socket_type="NodeSocketColor")
    rl = group.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    only = scene.view_layers.get("ALD FX Only")
    rl.layer = only.name if only is not None else scene.view_layers[0].name
    output = group.nodes.new("NodeGroupOutput")
    group.links.new(rl.outputs["Emission"], output.inputs[0])
    previous = scene.compositing_node_group
    scene.compositing_node_group = group
    path = os.path.join(OUT, "emission.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    bpy.data.node_groups.remove(group)
    scene.compositing_node_group = previous
    return pixels[:, :, :3]


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = "NEON_NIGHT"
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    fx.clear(scene)
    fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    camera.rotation_euler = (Vector(event.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * 24))
    bpy.context.view_layer.update()

    def shot(name):
        path = os.path.join(OUT, name)
        baseline_fx.render(scene, path)
        return read(path)

    with_fx = shot("fx_only.png")
    emission_ref = shot_emission(scene)
    matte = shot_matte(scene)
    fx.clear(scene)
    bpy.ops.ald.build()
    sky = shot("sky.png")

    # Recreate the burst for the plane tests.
    fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * 24))
    bpy.context.view_layer.update()

    behind = plane(scene, camera, "Foreign Behind", 70.0)
    from anime_look_director import compositor
    compositor.sync_fx_layers(scene)
    emission_behind = shot_emission(scene)
    with_fx_and_behind = shot("fx_and_behind.png")
    fx.clear(scene)
    bpy.ops.ald.build()
    behind_only = shot("behind_only.png")
    bpy.data.objects.remove(behind, do_unlink=True)

    # Front plane: the FX must be hidden.
    fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    scene.frame_set(int(system.origin_frame
                        + (event.birth + event.rise_time + 0.4) * 24))
    front = plane(scene, camera, "Foreign Front", 20.0)
    compositor.sync_fx_layers(scene)
    with_fx_and_front = shot("fx_and_front.png")
    fx.clear(scene)
    bpy.ops.ald.build()
    front_only = shot("front_only.png")
    bpy.data.objects.remove(front, do_unlink=True)

    mask = matte > 0.5
    contribution_ref = with_fx - sky
    contribution_behind = with_fx_and_behind - behind_only
    delta = np.abs(contribution_ref - contribution_behind).max(axis=2)
    emission_delta = np.abs(emission_ref - emission_behind).max(axis=2)
    delta_front = np.abs(with_fx_and_front - front_only).max(axis=2)
    report = {
        "matte_pixels": int(mask.sum()),
        "behind_contrib_mean": round(float(delta[mask].mean()), 6),
        "behind_contrib_max": round(float(delta[mask].max()), 6),
        "emission_contamination_mean": round(float(emission_delta[mask].mean()), 6),
        "emission_contamination_max": round(float(emission_delta[mask].max()), 6),
        "front_fx_mean": round(float(delta_front[mask].mean()), 6),
        "front_fx_max": round(float(delta_front[mask].max()), 6),
        "verdict": "PASS" if float(emission_delta[mask].max()) < 0.03
        and float(delta_front[mask].max()) < 0.03 else "FAIL",
    }
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("P5B", report)
    fx.clear(scene)
    return 0


if __name__ == "__main__":
    sys.exit(main())
