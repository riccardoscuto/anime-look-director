"""Legacy ALD safety fixture for Phase 0.

Exercises Disable/Restore/Remove on clean files, v2.56-style tags, two
independent scenes, a shared collection, nested collections, user collections
with similar names, and the v2.5.0 owner-only FX collection.

Run::

    blender -b --factory-startup --python-exit-code 1 \
        --python preset_dev/legacy_fixture.py
"""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "legacy")
CHECKS = []


def check(name, condition, detail=""):
    passed = bool(condition)
    CHECKS.append({"name": name, "passed": passed, "detail": detail})
    print("LEGACY %-46s %s %s"
          % (name, "OK" if passed else "FAIL", detail))
    return passed


def reset():
    if bpy.context.window is not None:
        bpy.context.window.scene = bpy.data.scenes[0]
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for scene in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(scene)
    scene = bpy.data.scenes[0]
    scene.name = "Legacy Scene"
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    return scene


def new_scene(name):
    return bpy.data.scenes.new(name)


def activate(scene):
    if bpy.context.window is not None:
        bpy.context.window.scene = scene


def collection(scene, name, tag=None, owner=None, parent=None):
    coll = bpy.data.collections.new(name)
    if tag:
        coll[tag] = True
    if owner:
        coll["ald_fx_owner"] = owner
    (parent or scene.collection).children.link(coll)
    return coll


def object_in(coll, name, tag="ald_fx", tagged=True):
    mesh = bpy.data.meshes.new(name)
    if tagged:
        mesh[tag] = True
    obj = bpy.data.objects.new(name, mesh)
    if tagged:
        obj[tag] = True
    coll.objects.link(obj)
    return obj


def layer(scene, coll, view_layer=None):
    view_layer = view_layer or scene.view_layers[0]
    return legacy._layer_collection(view_layer, coll)


def op(scene, name, **kwargs):
    with bpy.context.temp_override(scene=scene,
                                   view_layer=scene.view_layers[0]):
        return getattr(bpy.ops.ald, name)(**kwargs)


def empty_plan():
    return {"collections": [], "objects": [], "skipped": []}


def test_clean():
    scene = reset()
    coll = collection(scene, "ALD | FX")
    obj = object_in(coll, "User Mesh", tagged=False)
    check("clean file finds no legacy data", legacy.plan(scene) == empty_plan())
    check("clean file disable is a no-op", legacy.disable(scene) == (0, 0))
    check("clean file has no saved state", not legacy.has_state(scene))
    check("similar user name is untouched",
          coll.name in bpy.data.collections and obj.name in bpy.data.objects)


def test_v256_tags():
    scene = reset()
    fx = collection(scene, "ALD | FX", "ald_fx_collection", owner="fx")
    clouds = collection(scene, "ALD | Spatial Clouds", "ald_clouds",
                        owner="clouds")
    smoke = collection(scene, "ALD | Smoke", "ald_smoke", owner="smoke")
    fx_obj = object_in(fx, "FX Mesh", "ald_fx")
    cloud_obj = object_in(clouds, "Cloud Mesh", "ald_clouds")
    smoke_obj = object_in(smoke, "Smoke Mesh", "ald_smoke")
    collections = (fx, clouds, smoke)
    objects = (fx_obj, cloud_obj, smoke_obj)
    collection_names = [c.name for c in collections]
    object_names = [o.name for o in objects]
    mesh_names = [o.data.name for o in objects]
    plan = legacy.plan(scene)
    check("v2.56 tags find three collections",
          sorted(plan["collections"]) == sorted(collection_names),
          str(plan["collections"]))
    check("v2.56 tags find three objects",
          sorted(plan["objects"]) == sorted(object_names),
          str(plan["objects"]))
    before = {c.name: layer(scene, c).exclude for c in collections}
    op(scene, "legacy_disable")
    check("Disable excludes every tagged collection",
          all(layer(scene, c).exclude for c in (fx, clouds, smoke)))
    check("Disable saves a scene state", legacy.has_state(scene))
    op(scene, "legacy_restore")
    check("Restore returns the previous visibility",
          all(layer(scene, c).exclude == before[c.name]
              for c in (fx, clouds, smoke)))
    check("Restore clears the saved state", not legacy.has_state(scene))
    op(scene, "legacy_disable")
    result = op(scene, "legacy_remove", confirm=True)
    check("Remove deletes tagged collections and objects",
          result == {"FINISHED"}
          and not any(bpy.data.collections.get(name)
                      for name in collection_names)
          and not any(bpy.data.objects.get(name)
                      for name in object_names))
    check("Remove leaves no tagged mesh",
          not any(bpy.data.meshes.get(name) for name in mesh_names))
    check("Remove clears the disable state", not legacy.has_state(scene))


def test_two_scenes():
    scene_a = reset()
    scene_b = new_scene("Legacy B")
    coll_a = collection(scene_a, "ALD | FX A", "ald_fx_collection",
                        owner="a")
    coll_b = collection(scene_b, "ALD | FX B", "ald_fx_collection",
                        owner="b")
    obj_a = object_in(coll_a, "FX A", "ald_fx")
    obj_b = object_in(coll_b, "FX B", "ald_fx")
    names_a = (coll_a.name, obj_a.name)
    names_b = (coll_b.name, obj_b.name)
    activate(scene_a)
    op(scene_a, "legacy_disable")
    check("independent scenes: only the active scene is disabled",
          layer(scene_a, coll_a).exclude
          and not layer(scene_b, coll_b).exclude)
    check("independent scenes: state stays in the active scene",
          legacy.has_state(scene_a) and not legacy.has_state(scene_b))
    op(scene_a, "legacy_restore")
    check("independent scenes: restore leaves the other scene visible",
          not layer(scene_a, coll_a).exclude
          and not layer(scene_b, coll_b).exclude)
    op(scene_a, "legacy_remove", confirm=True)
    check("independent scenes: Remove only touches the active scene",
          bpy.data.collections.get(names_a[0]) is None
          and bpy.data.objects.get(names_a[1]) is None
          and bpy.data.collections.get(names_b[0]) is coll_b
          and bpy.data.objects.get(names_b[1]) is obj_b)


def test_shared_collection():
    scene_a = reset()
    scene_b = new_scene("Legacy Shared")
    shared = collection(scene_a, "ALD | Shared", "ald_fx_collection",
                        owner="shared")
    scene_b.collection.children.link(shared)
    obj = object_in(shared, "Shared FX", "ald_fx")
    activate(scene_a)
    op(scene_a, "legacy_disable")
    check("shared collection is disabled only in the active scene",
          layer(scene_a, shared).exclude
          and not layer(scene_b, shared).exclude)
    plan = legacy.plan(scene_a)
    check("shared collection is reported as skipped",
          not plan["collections"]
          and any(name == shared.name for name, _reason in plan["skipped"]))
    result = op(scene_a, "legacy_remove", confirm=True)
    check("Remove refuses a shared collection",
          result == {"CANCELLED"}
          and bpy.data.collections.get(shared.name) is shared
          and bpy.data.objects.get(obj.name) is obj)
    op(scene_a, "legacy_restore")
    check("shared collection restores without touching the other scene",
          not layer(scene_a, shared).exclude
          and not layer(scene_b, shared).exclude)


def test_nested():
    scene = reset()
    parent = collection(scene, "ALD | FX Root", "ald_fx_collection",
                        owner="root")
    child = collection(scene, "ALD | Clouds Child", "ald_clouds",
                       owner="child", parent=parent)
    obj = object_in(child, "Nested Cloud", "ald_clouds")
    names = (parent.name, child.name, obj.name)
    plan = legacy.plan(scene)
    check("nested legacy collections are found",
          sorted(plan["collections"]) == ["ALD | Clouds Child",
                                          "ALD | FX Root"]
          and plan["objects"] == ["Nested Cloud"])
    op(scene, "legacy_disable")
    check("nested legacy collections are disabled",
          layer(scene, parent).exclude and layer(scene, child).exclude)
    op(scene, "legacy_remove", confirm=True)
    check("nested legacy collections are removed",
          bpy.data.collections.get(names[0]) is None
          and bpy.data.collections.get(names[1]) is None
          and bpy.data.objects.get(names[2]) is None)


def test_nested_user_child():
    scene = reset()
    parent = collection(scene, "ALD | FX Root", "ald_fx_collection",
                        owner="root")
    user_child = collection(scene, "My Props", parent=parent)
    user_obj = object_in(user_child, "User Prop", tagged=False)
    tagged = object_in(parent, "FX In Root", "ald_fx")
    plan = legacy.plan(scene)
    check("a user child blocks the parent",
          not plan["collections"]
          and any(name == parent.name for name, _reason in plan["skipped"]))
    result = op(scene, "legacy_remove", confirm=True)
    check("Remove keeps a parent with user children",
          result == {"CANCELLED"}
          and bpy.data.collections.get(parent.name) is parent
          and bpy.data.collections.get(user_child.name) is user_child
          and bpy.data.objects.get(user_obj.name) is user_obj
          and bpy.data.objects.get(tagged.name) is tagged)


def test_similar_names():
    scene = reset()
    names = ("ALD | FX", "ALD | Smoke", "ALD | Spatial Clouds")
    collections = [collection(scene, name) for name in names]
    objects = [object_in(coll, "User %d" % index, tagged=False)
               for index, coll in enumerate(collections)]
    check("similar user names are not legacy data",
          legacy.plan(scene) == empty_plan()
          and not legacy.has_legacy(scene))
    result = op(scene, "legacy_remove", confirm=True)
    check("Remove ignores similar user names",
          result == {"CANCELLED"}
          and all(bpy.data.collections.get(coll.name) is coll
                  for coll in collections)
          and all(bpy.data.objects.get(obj.name) is obj
                  for obj in objects))


def test_owner_only_fx():
    scene = reset()
    coll = collection(scene, "ALD | FX Old", owner="v250-owner")
    obj = object_in(coll, "Old FX", "ald_fx")
    names = (coll.name, obj.name)
    check("owner-only v2.5 collection is detected",
          legacy.plan(scene)["collections"] == [names[0]])
    op(scene, "legacy_remove", confirm=True)
    check("owner-only v2.5 collection is removed",
          bpy.data.collections.get(names[0]) is None
          and bpy.data.objects.get(names[1]) is None)


def test_shared_object():
    scene = reset()
    legacy_coll = collection(scene, "ALD | FX", "ald_fx_collection",
                             owner="fx")
    user_coll = collection(scene, "My Props")
    obj = object_in(legacy_coll, "Shared Prop", "ald_fx")
    user_coll.objects.link(obj)
    plan = legacy.plan(scene)
    check("an object linked to a user collection blocks removal",
          not plan["collections"] and not plan["objects"]
          and any(name == legacy_coll.name
                  for name, _reason in plan["skipped"]))
    result = op(scene, "legacy_remove", confirm=True)
    check("Remove keeps the shared object and both collections",
          result == {"CANCELLED"}
          and bpy.data.collections.get(legacy_coll.name) is legacy_coll
          and bpy.data.collections.get(user_coll.name) is user_coll
          and bpy.data.objects.get(obj.name) is obj)


def test_standalone_fx():
    scene = reset()
    user = collection(scene, "My Scene Helpers")
    anchor = bpy.data.objects.new("ALD Sky/FX Anchor", None)
    anchor["ald_fx_anchor"] = True
    user.objects.link(anchor)
    mesh = bpy.data.meshes.new("ALD FX Ground")
    ground = bpy.data.objects.new("ALD FX Ground", mesh)
    ground["ald_fx_ground"] = True
    user.objects.link(ground)
    plan = legacy.plan(scene)
    check("standalone FX anchor and ground are planned",
          sorted(plan["objects"]) == ["ALD FX Ground", "ALD Sky/FX Anchor"])
    result = op(scene, "legacy_remove", confirm=True)
    check("Remove deletes standalone FX helpers only",
          result == {"FINISHED"}
          and bpy.data.objects.get("ALD Sky/FX Anchor") is None
          and bpy.data.objects.get("ALD FX Ground") is None
          and bpy.data.meshes.get("ALD FX Ground") is None
          and bpy.data.collections.get(user.name) is user)


def test_view_layers():
    scene = reset()
    second = scene.view_layers.new("Second")
    coll = collection(scene, "ALD | FX", "ald_fx_collection", owner="fx")
    object_in(coll, "FX Mesh", "ald_fx")
    op(scene, "legacy_disable")
    check("Disable covers every view layer",
          layer(scene, coll, scene.view_layers[0]).exclude
          and layer(scene, coll, second).exclude)
    op(scene, "legacy_restore")
    check("Restore covers every view layer",
          not layer(scene, coll, scene.view_layers[0]).exclude
          and not layer(scene, coll, second).exclude)


def main():
    global legacy
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import legacy as module
    legacy = module

    test_clean()
    test_v256_tags()
    test_two_scenes()
    test_shared_collection()
    test_nested()
    test_nested_user_child()
    test_similar_names()
    test_owner_only_fx()
    test_shared_object()
    test_standalone_fx()
    test_view_layers()

    report = {"checks": CHECKS,
              "passed": sum(1 for item in CHECKS if item["passed"]),
              "total": len(CHECKS)}
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    ok = report["passed"] == report["total"]
    print("ALD LEGACY %d/%d %s"
          % (report["passed"], report["total"], "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
