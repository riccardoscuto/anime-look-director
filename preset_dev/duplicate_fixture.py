"""Dedicated fixture: a duplicated scene repaired into independent ALD data.

Runs in a fresh factory scene (no state from the gate), builds spatial clouds
and a firework, copies the scene, repairs the copy and checks that:

- the copy has its own cloud and FX collections (different datablocks);
- the copy rebuilds its cloud geometry;
- the original objects, collections and FX counts are untouched;
- removing the copy's clouds does not touch the original.

Exit code 1 on failure. No .blend is saved.

Run::

    blender -b --factory-startup --python preset_dev/duplicate_fixture.py
"""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx


def check(condition, message):
    print("DUP", "PASS" if condition else "FAIL", message)
    if not condition:
        raise SystemExit(1)


def world_values(world):
    if world is None or not world.use_nodes or world.node_tree is None:
        return None
    node = next((node for node in world.node_tree.nodes
                 if node.bl_idname == "ShaderNodeGroup" and node.node_tree
                 and node.node_tree.name.startswith("ALD | World")), None)
    if node is None:
        return None
    return [tuple(round(value, 4) for value in node.inputs[name].default_value)
            for name in ("Horizon Color", "Mid Sky Color", "Sun Color")]


def main():
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx, ownership

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds_coverage = 0.5
    scene.ald.clouds_layers = 2
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    clouds.remove(scene)
    fx.clear(scene)
    clouds.create(scene)
    fx.create_fireworks(scene, 1, seed=17, distance=55.0, time=0.0)
    bpy.ops.ald.build()

    original_clouds = clouds._collection(scene)
    original_fx = fx._collection(scene)
    check(original_clouds is not None and original_fx is not None,
          "source collections exist")
    cloud_names = [obj.name for obj in original_clouds.objects]
    cloud_pointers = {obj.as_pointer() for obj in original_clouds.objects}
    fx_count = len(original_fx.objects)

    copy = scene.copy()
    repaired = ownership.repair(copy)
    check(repaired > 0, "the copy is detected as shared")
    copy_clouds = clouds._collection(copy)
    copy_fx = fx._collection(copy)
    check(copy_clouds is not None
          and copy_clouds.as_pointer() != original_clouds.as_pointer(),
          "the copy owns a different cloud collection")
    check(copy_fx is not None
          and copy_fx.as_pointer() != original_fx.as_pointer(),
          "the copy owns a different FX collection")
    check(sum(len(obj.data.polygons) for obj in copy_clouds.objects) > 0,
          "the copy has cloud geometry")
    check(all(obj.as_pointer() not in cloud_pointers
              for obj in copy_clouds.objects),
          "the copy owns independent cloud objects")
    check(all(name in bpy.data.objects for name in cloud_names),
          "the original cloud objects survive")
    check(len(original_fx.objects) == fx_count,
          "the original FX objects survive")

    clouds.remove(copy)
    check(clouds._collection(scene) is not None,
          "the original cloud collection survives the copy removal")
    check(all(name in bpy.data.objects for name in cloud_names),
          "the original cloud objects survive the copy removal")

    # Build repairs a fresh copy without the manual button.
    automatic = scene.copy()
    try:
        with bpy.context.temp_override(scene=automatic):
            bpy.ops.ald.build()
        auto_clouds = clouds._collection(automatic)
        check(auto_clouds is not None
              and auto_clouds.as_pointer() != original_clouds.as_pointer(),
              "Build repairs the duplicated scene")
        check(all(obj.as_pointer() not in cloud_pointers
                  for obj in auto_clouds.objects),
              "Build makes the cloud objects independent")
        check(all(name in bpy.data.objects for name in cloud_names),
              "the original cloud objects survive the Build on a copy")

        # A palette on the copy must not change the original's world or sun.
        original_world = world_values(scene.world)
        check(original_world is not None,
              "the original world gradient exists")
        sun = next((obj for obj in scene.objects
                    if obj.get("ald_auto_sun")), None)
        sun_color = tuple(sun.data.color) if sun is not None else None
        sun_energy = sun.data.energy if sun is not None else None
        with bpy.context.temp_override(scene=automatic):
            automatic.ald.palette = "NEON_NIGHT"
            bpy.ops.ald.apply_palette()
        check(world_values(scene.world) == original_world,
              "applying a palette to the copy kept the original world")
        check(sun is None or (tuple(sun.data.color) == sun_color
                              and sun.data.energy == sun_energy),
              "applying a palette to the copy kept the original sun")
    finally:
        if bpy.data.scenes.get(automatic.name) is not None:
            clouds.remove(automatic)
            fx.clear(automatic)
            bpy.data.scenes.remove(automatic)

    # Removing ALD from a copy must not touch the original's data or world.
    removal = scene.copy()
    world = scene.world
    world_nodes = len(world.node_tree.nodes) if world and world.use_nodes else 0
    original_materials = {}
    for obj in scene.objects:
        data = obj.data
        if data is None or not hasattr(data, "materials"):
            continue
        for material in data.materials:
            if material is not None:
                original_materials[material.as_pointer()] = (
                    len(material.node_tree.nodes)
                    if material.use_nodes and material.node_tree else 0)
    try:
        with bpy.context.temp_override(scene=removal):
            bpy.ops.ald.remove_from_scene()

        def scene_materials():
            return [material for obj in scene.objects
                    if obj.data is not None
                    and hasattr(obj.data, "materials")
                    for material in obj.data.materials if material is not None]

        check(clouds._collection(scene) is not None,
              "removing ALD from the copy kept the original clouds")
        check(len(original_fx.objects) == fx_count,
              "removing ALD from the copy kept the original FX")
        check(all(material.as_pointer() in original_materials
                  for material in scene_materials()),
              "removing ALD from the copy kept the original materials")
        check(all((len(material.node_tree.nodes)
                   if material.use_nodes and material.node_tree else 0)
                  == original_materials[material.as_pointer()]
                  for material in scene_materials()),
              "removing ALD from the copy kept the original material nodes")
        check(all(name in bpy.data.objects for name in cloud_names),
              "removing ALD from the copy kept the original objects")
        check(scene.world is world
              and (not world.use_nodes
                   or len(world.node_tree.nodes) == world_nodes),
              "removing ALD from the copy kept the original world")
    finally:
        if bpy.data.scenes.get(removal.name) is not None:
            bpy.data.scenes.remove(removal)

    bpy.data.scenes.remove(copy)
    clouds.remove(scene)
    fx.clear(scene)
    print("DUP FIXTURE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
