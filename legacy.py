"""Scene-local handling of legacy ALD FX, Spatial Clouds and smoke data.

The 2.5x add-ons tagged their collections with ``ald_fx_collection``,
``ald_fx_owner``, ``ald_clouds`` and ``ald_smoke``. Names are never used to
identify data: a user collection called ``ALD | FX`` is untouched.

Disable is per view layer, so a collection shared with another scene keeps its
visibility there. The previous layer-collection state is stored in the scene
and restored by ``restore``. Remove is conservative: shared collections, user
collections nested inside a legacy collection, and objects linked outside the
legacy set block the deletion and are reported instead.
"""

import json

import bpy

OWNER_KEY = "ald_fx_owner"
STATE_KEY = "ald_legacy_disable_state"
COLLECTION_TAGS = ("ald_fx_collection", "ald_clouds", "ald_smoke")
OBJECT_TAGS = ("ald_fx", "ald_clouds", "ald_smoke", "ald_fx_anchor",
               "ald_fx_ground")


def _scene_collections(scene):
    """Every collection linked to the scene, at any depth."""
    found = []
    seen = set()

    def walk(collection):
        for child in collection.children:
            pointer = child.as_pointer()
            if pointer in seen:
                continue
            seen.add(pointer)
            found.append(child)
            walk(child)

    walk(scene.collection)
    return found


def is_legacy_collection(collection):
    if any(collection.get(tag) for tag in COLLECTION_TAGS):
        return True
    # v2.5.0 used only the owner UUID on the FX collection.
    return bool(collection.get(OWNER_KEY))


def is_legacy_object(obj):
    if any(obj.get(tag) for tag in OBJECT_TAGS):
        return True
    data = getattr(obj, "data", None)
    return data is not None and any(data.get(tag) for tag in OBJECT_TAGS)


def legacy_collections(scene):
    return [collection for collection in _scene_collections(scene)
            if is_legacy_collection(collection)]


def _shared_with_other_scene(collection, scene):
    for other in bpy.data.scenes:
        if other is not scene and collection in _scene_collections(other):
            return True
    return False


def _layer_collection(view_layer, collection):
    stack = [view_layer.layer_collection]
    while stack:
        layer = stack.pop()
        if layer.collection == collection:
            return layer
        stack.extend(layer.children)
    return None


def _read_state(scene):
    raw = scene.get(STATE_KEY)
    if not isinstance(raw, str):
        return {}
    try:
        state = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _write_state(scene, state):
    scene[STATE_KEY] = json.dumps(state, sort_keys=True)


def has_state(scene):
    """True when Disable has a stored visibility state in this scene."""
    return bool(_read_state(scene))


def has_legacy(scene):
    """True when the scene contains at least one tagged legacy collection."""
    return bool(legacy_collections(scene))


def disable(scene):
    """Exclude the legacy collections in this scene and remember the state."""
    state = _read_state(scene)
    collections = state.setdefault("collections", {})
    changed = 0
    found = 0
    for collection in legacy_collections(scene):
        found += 1
        entry = collections.setdefault(collection.name, {"views": {}})
        for view_layer in scene.view_layers:
            layer = _layer_collection(view_layer, collection)
            if layer is None:
                continue
            previous = entry["views"].get(view_layer.name)
            if previous is None:
                entry["views"][view_layer.name] = {
                    "exclude": bool(layer.exclude),
                    "hide_viewport": bool(layer.hide_viewport),
                }
            if not layer.exclude:
                layer.exclude = True
                changed += 1
    if found:
        _write_state(scene, state)
    return found, changed


def restore(scene):
    """Restore the layer-collection state saved by ``disable``."""
    state = _read_state(scene)
    restored = 0
    for name, entry in state.get("collections", {}).items():
        collection = bpy.data.collections.get(name)
        if collection is None:
            continue
        views = entry.get("views", {})
        for view_name, previous in views.items():
            view_layer = scene.view_layers.get(view_name)
            if view_layer is None:
                continue
            layer = _layer_collection(view_layer, collection)
            if layer is None:
                continue
            layer.exclude = bool(previous.get("exclude", False))
            layer.hide_viewport = bool(previous.get("hide_viewport", False))
            restored += 1
    if state:
        scene.pop(STATE_KEY, None)
    return restored


def _removable(collection, scene, seen=None):
    """Conservative bottom-up check for a tagged collection."""
    seen = seen or set()
    pointer = collection.as_pointer()
    if pointer in seen:
        return False
    seen.add(pointer)
    if _shared_with_other_scene(collection, scene):
        return False
    for obj in collection.objects:
        if not is_legacy_object(obj):
            return False
    for child in collection.children:
        if not is_legacy_collection(child):
            return False
        if not _removable(child, scene, seen):
            return False
    return True


def _object_removable(obj, removable, scene):
    if len(obj.users_scene) > 1 and any(other is not scene
                                        for other in obj.users_scene):
        return False
    return all(collection in removable for collection in obj.users_collection)


def _standalone_objects(scene, removable_collections):
    """Tagged objects outside the removable collections (anchors, ground)."""
    objects = []
    skipped = []
    for obj in scene.objects:
        if not is_legacy_object(obj):
            continue
        if any(collection in removable_collections
               for collection in obj.users_collection):
            continue
        if any(other is not scene for other in obj.users_scene):
            skipped.append((obj.name, "shared with another scene"))
            continue
        if any(is_legacy_collection(collection)
               and collection not in removable_collections
               for collection in obj.users_collection):
            skipped.append((obj.name, "inside a blocked legacy collection"))
            continue
        objects.append(obj)
    return objects, skipped


def plan(scene):
    """Return the removable collections/objects and the skipped ones."""
    tagged = legacy_collections(scene)
    candidate = set(tagged)
    safe = {collection for collection in candidate
            if _removable(collection, scene)}
    # A collection holding an object that is linked to a collection outside
    # the safe set must stay, and so must its parents.
    changed = True
    while changed:
        changed = False
        for collection in list(safe):
            for obj in collection.objects:
                if not _object_removable(obj, safe, scene):
                    safe.discard(collection)
                    changed = True
                    break
            if collection not in safe:
                continue
            for child in collection.children:
                if child in candidate and child not in safe:
                    safe.discard(collection)
                    changed = True
                    break

    removable = safe
    objects = []
    seen = set()
    for collection in removable:
        for obj in collection.objects:
            if obj.as_pointer() in seen:
                continue
            if _object_removable(obj, removable, scene):
                seen.add(obj.as_pointer())
                objects.append(obj)
    standalone, standalone_skipped = _standalone_objects(scene, removable)
    for obj in standalone:
        if obj.as_pointer() not in seen:
            seen.add(obj.as_pointer())
            objects.append(obj)

    skipped = list(standalone_skipped)
    for collection in tagged:
        if collection in removable:
            continue
        if _shared_with_other_scene(collection, scene):
            reason = "shared with another scene"
        elif any(not is_legacy_object(obj) for obj in collection.objects):
            reason = "contains a non-legacy object"
        elif any(not is_legacy_collection(child)
                 for child in collection.children):
            reason = "contains a non-legacy collection"
        else:
            reason = "contains a blocked object or child"
        skipped.append((collection.name, reason))
    return {
        "collections": [c.name for c in removable],
        "objects": [o.name for o in objects],
        "skipped": skipped,
    }


def _remove_orphans():
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.metaballs,
                   bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for block in list(blocks):
            if block.users == 0 and any(block.get(tag) for tag in OBJECT_TAGS):
                blocks.remove(block)


def remove(scene, chosen=None):
    """Delete the planned legacy collections/objects. Returns counts."""
    chosen = chosen or plan(scene)
    object_names = set(chosen.get("objects", []))
    objects = []
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            objects.append(obj)
    data_blocks = []
    for obj in objects:
        data = getattr(obj, "data", None)
        if data is not None:
            data_blocks.append(data)
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in data_blocks:
        if data.users == 0:
            bpy.data.batch_remove(ids=(data,))

    names = set(chosen.get("collections", []))
    collections = [bpy.data.collections.get(name) for name in names]
    collections = [collection for collection in collections
                   if collection is not None]
    removed_collections = 0
    while collections:
        leaf = next((collection for collection in collections
                     if not any(child in collections
                                for child in collection.children)), None)
        if leaf is None:
            break
        collections.remove(leaf)
        bpy.data.collections.remove(leaf)
        removed_collections += 1

    _remove_orphans()
    state = _read_state(scene)
    if state:
        stored = state.get("collections", {})
        for name in names:
            stored.pop(name, None)
        if stored:
            _write_state(scene, state)
        else:
            scene.pop(STATE_KEY, None)
    return len(objects), removed_collections
