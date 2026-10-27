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
import tempfile

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

    # An ordinary object and material shared by every scene copy: the fixture
    # checks that ALD never edits it from the copy.
    test_mesh = bpy.data.meshes.new("ALD Fixture Shared Mesh")
    test_mesh.from_pydata([(-1, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    test_mesh.update()
    test_material = bpy.data.materials.new("ALD Fixture Shared Material")
    test_material.use_nodes = True
    test_mesh.materials.append(test_material)
    test_object = bpy.data.objects.new("ALD Fixture Shared Object", test_mesh)
    scene.collection.objects.link(test_object)

    original_clouds = clouds._collection(scene)
    original_fx = fx._collection(scene)
    check(original_clouds is not None and original_fx is not None,
          "source collections exist")
    cloud_names = [obj.name for obj in original_clouds.objects]
    cloud_pointers = {obj.as_pointer() for obj in original_clouds.objects}
    fx_count = len(original_fx.objects)

    copy = scene.copy()
    check(clouds._collection(copy) is None,
          "the copy did not start with the shared collections")
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

        # A shared ordinary material is never edited from the copy: its slots
        # and datablock belong to the original scene too.
        from anime_look_director import materials, palette
        shared_material = next(
            (material for obj in automatic.objects
             if obj.data is not None and hasattr(obj.data, "materials")
             for material in obj.data.materials
             if material is not None
             and materials.material_is_shared(material, automatic)), None)
        check(shared_material is not None,
              "the fixture has no shared ordinary material")
        if shared_material is not None:
            nodes_before = len(shared_material.node_tree.nodes) \
                if shared_material.use_nodes and shared_material.node_tree else 0
            materials.sync_scene(automatic, (0.2, 0.3, 0.9), 0.5, 0.5)
            nodes_after = len(shared_material.node_tree.nodes) \
                if shared_material.use_nodes and shared_material.node_tree else 0
            check(nodes_before == nodes_after,
                  "a shared material was edited from the copy")

        # A sun shared with the copy never rotates the original.
        if sun is not None:
            rotation = tuple(sun.rotation_euler)
            palette.apply_sun_angles(automatic, 0.35, 1.1)
            check(tuple(sun.rotation_euler) == rotation,
                  "a shared sun was rotated from the copy")
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

    # The repaired identity survives a save and a reload. The first copy was
    # emptied by the removal test, so a fresh copy carries the clouds.
    bpy.data.scenes.remove(copy)
    reload_copy = scene.copy()
    reload_copy.use_fake_user = True
    ownership.repair(reload_copy)
    fixture = os.path.join(tempfile.gettempdir(),
                           "ald_duplicate_fixture.blend")
    original_name = scene.name
    copy_name = reload_copy.name
    bpy.ops.wm.save_as_mainfile(filepath=fixture)
    bpy.ops.wm.open_mainfile(filepath=fixture)
    scene = bpy.data.scenes.get(original_name)
    reload_copy = bpy.data.scenes.get(copy_name)
    check(scene is not None and reload_copy is not None,
          "both scenes survive the save/reload")
    check(scene.get(fx.ID_KEY) and reload_copy.get(fx.ID_KEY)
          and scene.get(fx.ID_KEY) != reload_copy.get(fx.ID_KEY),
          "the identities stay distinct after the save/reload")
    original_after = clouds._collection(scene)
    copy_after = clouds._collection(reload_copy)
    check(original_after is not None and copy_after is not None
          and original_after.as_pointer() != copy_after.as_pointer(),
          "the cloud collections stay separate after the save/reload")
    clouds.remove(reload_copy)
    check(clouds._collection(scene) is not None,
          "removing the reloaded copy keeps the original clouds")

    bpy.data.scenes.remove(reload_copy)
    clouds.remove(scene)
    fx.clear(scene)
    if os.path.exists(fixture):
        os.remove(fixture)
    print("DUP FIXTURE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
