"""P0-A: record the baseline of the add-on.

Writes ``preset_dev/baseline.json`` with the declared version, the hashes of
every Python file, the group schemas and the outcome of the public FX flows
(create, update, duplicate, remove).

The flows are the same ones the gate exercises; this script exists to keep a
machine-readable record of the state the plan calls "baseline", so a later
change can be compared against it.

Run (from the add-on directory)::

    blender -b --factory-startup --python-exit-code 1 --python preset_dev/baseline.py
"""

import hashlib
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.basename(HERE)


def enable_addon():
    import addon_utils

    addon_utils.enable(PACKAGE)


def file_hashes():
    hashes = {}
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(HERE, name)
        with open(path, "rb") as handle:
            hashes[name] = hashlib.sha256(handle.read()).hexdigest()
    return hashes


def group_schemas(scene):
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes
    from anime_look_director.properties import FX_SCHEMA

    data = {
        "data_schema": FX_SCHEMA,
        "group_schema": fx_nodes.SCHEMA,
        "groups": {},
    }
    for name in (fx_nodes.GROUP_NAME, fx_nodes.TRAIL_GROUP_NAME):
        group = bpy.data.node_groups.get(name)
        data["groups"][name] = {
            "exists": group is not None,
            "ald_schema": int(group.get("ald_schema", 0)) if group else 0,
        }
    # Force the groups to exist so the baseline records their real schema.
    fx_nodes.build_burst_group()
    fx_nodes.build_trail_group()
    for name in (fx_nodes.GROUP_NAME, fx_nodes.TRAIL_GROUP_NAME):
        group = bpy.data.node_groups.get(name)
        data["groups"][name] = {
            "exists": group is not None,
            "ald_schema": int(group.get("ald_schema", 0)) if group else 0,
        }
    # The FX collection of the scene, when one exists.
    collection = None
    for coll in bpy.data.collections:
        if coll.get(fx_module.OWNER_KEY) == fx_module._scene_id(scene):
            collection = coll
            break
    data["collection"] = collection.name if collection else None
    return data


def objects_of(uid):
    return [obj for obj in bpy.data.objects
            if obj.get("ald_fx") and obj.get("ald_fx_system") == uid]


def flows(scene):
    from anime_look_director import fx as fx_module

    out = {}
    fx_module.clear(scene)
    bpy.ops.ald.fx_fireworks(count=1, seed=13, distance=30.0)
    system = scene.ald.fx_systems[0]
    uid = system.uid
    out["create"] = {
        "records": len(scene.ald.fx_systems),
        "objects": len(objects_of(uid)),
        "uid": uid,
    }

    scene.ald.fx_selected_system = 0
    bpy.ops.ald.fx_update()
    out["update"] = {
        "records": len(scene.ald.fx_systems),
        "objects": len(objects_of(uid)),
        "uid_kept": bool(len(scene.ald.fx_systems)
                         and scene.ald.fx_systems[0].uid == uid),
    }

    bpy.ops.ald.fx_duplicate_system()
    copy = scene.ald.fx_systems[1] if len(scene.ald.fx_systems) > 1 else None
    copy_uid = copy.uid if copy is not None else ""
    out["duplicate"] = {
        "records": len(scene.ald.fx_systems),
        "objects": len(objects_of(copy_uid)) if copy_uid else 0,
        "uid_changed": bool(copy_uid and copy_uid != uid),
    }

    if copy is not None:
        scene.ald.fx_selected_system = 1
        bpy.ops.ald.fx_remove_system()
    out["remove"] = {
        "records": len(scene.ald.fx_systems),
        "objects_of_removed": len(objects_of(copy_uid)) if copy_uid else 0,
        "objects_of_kept": len(objects_of(uid)),
    }
    fx_module.clear(scene)
    return out


def main():
    enable_addon()
    module = sys.modules.get(PACKAGE)
    version = list(module.bl_info.get("version", ())) if module else []
    scene = bpy.context.scene

    data = {
        "version": version,
        "version_text": ".".join(str(part) for part in version),
        "blender": bpy.app.version_string,
        "hashes": file_hashes(),
        "schemas": group_schemas(scene),
        "flows": flows(scene),
    }

    target = os.path.join(HERE, "preset_dev", "baseline.json")
    with open(target, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("ALD BASELINE:", target)
    print(json.dumps(data["flows"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
