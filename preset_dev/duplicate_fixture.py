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

    bpy.data.scenes.remove(copy)
    clouds.remove(scene)
    fx.clear(scene)
    print("DUP FIXTURE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
