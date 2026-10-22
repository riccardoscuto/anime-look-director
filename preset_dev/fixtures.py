"""Temporary fixtures for the diagnostics of the FX.

The fixtures are built in a scene that the caller owns: they never touch the
file of the user and they never save anything.

Three fixtures:

``single_meteor``
    one meteor, with a readable duration and a trajectory in the frame;
``single_firework``
    one firework with its launcher and its shell;
``user_scene``
    a scene with an HDRI like world, a custom compositor and an emissive
    material of the user: the removal must restore it.

Usage:
    blender -b --factory-startup --python preset_dev/fixtures.py -- [--kind NAME]
"""

import math
import os
import sys

import bpy
from mathutils import Vector


def _clean_scene(scene):
    """Remove the objects of the scene, keeping the camera."""
    for obj in list(scene.objects):
        if obj.type == "CAMERA":
            continue
        bpy.data.objects.remove(obj, do_unlink=True)


def _camera_at(scene, target, distance=60.0, lens=50.0):
    """A camera that frames the target."""
    camera = scene.camera
    if camera is None:
        data = bpy.data.cameras.new("ALD Fixture Cam")
        camera = bpy.data.objects.new("ALD Fixture Cam", data)
        scene.collection.objects.link(camera)
        scene.camera = camera
    camera.data.lens = lens
    camera.data.clip_start = 0.1
    camera.data.clip_end = 1000.0
    direction = Vector(target) - Vector(camera.location)
    if direction.length < 1e-3:
        direction = Vector((0.0, 1.0, 0.0))
    camera.location = Vector(target) - direction.normalized() * distance
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return camera


def single_meteor(scene, distance=90.0):
    """One meteor crossing the frame."""
    from anime_look_director import fx as fx_module

    _clean_scene(scene)
    camera = _camera_at(scene, Vector((0.0, 0.0, 40.0)), distance=distance)
    origin = camera.matrix_world.translation
    forward = (camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0)))
    right = (camera.matrix_world.to_quaternion() @ Vector((1.0, 0.0, 0.0)))
    start = origin + forward * distance - right * distance * 0.4
    fx_module.clear(scene)
    fx_module.create_meteors(scene, 1, seed=21, distance=distance, time=0.0,
                             replace=True)
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    event.target = tuple(start)
    event.direction = tuple(right)
    event.speed = 30.0
    event.life = 1.4
    event.birth = 0.0
    fx_module.update_system(scene, system)
    _camera_at(scene, start + right * distance * 0.4, distance=distance)
    return scene


def single_firework(scene, distance=60.0):
    """One firework with its launcher and its shell."""
    from anime_look_director import fx as fx_module

    _clean_scene(scene)
    target = Vector((0.0, 0.0, 45.0))
    _camera_at(scene, target, distance=distance)
    fx_module.clear(scene)
    fx_module.create_fireworks(scene, 1, seed=13, distance=distance, time=0.0,
                               replace=True)
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    event.target = tuple(target)
    event.launcher = tuple(target - Vector((0.0, 0.0, 26.0)))
    event.birth = 0.0
    event.rise_time = 1.2
    fx_module.update_system(scene, system)
    return scene


def user_scene(scene):
    """A scene with the state of the user: a world, a compositor, a material."""
    _clean_scene(scene)
    # A world with an image texture, like an HDRI.
    world = bpy.data.worlds.new("ALD Fixture HDRI")
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputWorld")
    background = tree.nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 1.0
    texture = tree.nodes.new("ShaderNodeTexEnvironment")
    image = bpy.data.images.new("ALD Fixture Sky", 4, 4)
    image.pixels = [0.2, 0.4, 0.8, 1.0] * 4
    texture.image = image
    tree.links.new(texture.outputs["Color"], background.inputs["Color"])
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    scene.world = world
    # An emissive material of the user.
    material = bpy.data.materials.new("ALD Fixture Sign")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.3, 0.1, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 4.0
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, 20.0, 10.0))
    sign = bpy.context.object
    sign.data.materials.append(material)
    # A custom compositor of the user.
    group = bpy.data.node_groups.new("ALD Fixture Compositor", "CompositorNodeTree")
    group.interface.new_socket(name="Image", in_out="OUTPUT",
                                socket_type="NodeSocketColor")
    layers = group.nodes.new("CompositorNodeRLayers")
    group_out = group.nodes.new("NodeGroupOutput")
    group.links.new(layers.outputs["Image"], group_out.inputs[0])
    scene.compositing_node_group = group
    scene.render.use_compositing = True
    _camera_at(scene, Vector((0.0, 20.0, 10.0)), distance=40.0)
    return scene


FIXTURES = {
    "meteor": single_meteor,
    "firework": single_firework,
    "user": user_scene,
}


def build(name, scene=None):
    """Build a fixture by name and return the scene."""
    scene = scene or bpy.context.scene
    if name not in FIXTURES:
        raise KeyError("unknown fixture: %s" % name)
    return FIXTURES[name](scene)


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    name = "meteor"
    if "--kind" in argv:
        name = argv[argv.index("--kind") + 1]
    build(name)
    print("ALD FIXTURE %s ready" % name)


if __name__ == "__main__":
    main()
