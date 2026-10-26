"""Ownership repair for duplicated scenes.

``Scene.copy()`` either shares the ALD collection datablocks with the original
or copies them while sharing the objects. In both cases the copy and the
source can destroy each other. The repair gives the copy a new scene identity,
detaches the shared collections (the original keeps them) and makes the copy's
own ALD objects independent (new object/mesh/material datablocks).
"""

import uuid

import bpy


def _walk(collection):
    yield collection
    for child in collection.children:
        yield from _walk(child)


def _ald_collections(scene):
    from . import fx
    return [collection for collection in _walk(scene.collection)
            if collection.get(fx.OWNER_KEY)]


def shared_collections(scene):
    """ALD collections linked to this scene and to another one."""
    others = [other for other in bpy.data.scenes if other != scene]
    foreign = set()
    for other in others:
        for collection in _walk(other.collection):
            foreign.add(collection.as_pointer())
    return [collection for collection in _ald_collections(scene)
            if collection.as_pointer() in foreign]


def same_identity(scene):
    """Another scene still carries this scene's identity (a copy)."""
    from . import fx
    mine = scene.get(fx.ID_KEY)
    if not mine:
        return False
    return any(other != scene and other.get(fx.ID_KEY) == mine
               for other in bpy.data.scenes)


def has_shared(scene):
    return bool(shared_collections(scene)) or same_identity(scene)


def _unlink(scene, target):
    def walk(parent):
        for child in list(parent.children):
            if child.as_pointer() == target.as_pointer():
                parent.children.unlink(target)
            else:
                walk(child)
    walk(scene.collection)


def _duplicate_objects(collection):
    """Make the objects, meshes and materials of the copy independent."""
    for obj in list(collection.objects):
        duplicate = obj.copy()
        if obj.data is not None:
            duplicate.data = obj.data.copy()
            for index, material in enumerate(duplicate.data.materials):
                if material is not None:
                    duplicate.data.materials[index] = material.copy()
        collection.objects.link(duplicate)
        collection.objects.unlink(obj)


def repair(scene):
    """Detach the shared ALD collections and make this scene's data its own."""
    from . import clouds, fx

    shared = shared_collections(scene)
    duplicated = same_identity(scene)
    if not shared and not duplicated:
        return 0
    for collection in shared:
        _unlink(scene, collection)
    new_id = uuid.uuid4().hex
    scene[fx.ID_KEY] = new_id
    scene["ald_fx_owner"] = scene.name
    settings = getattr(scene, "ald", None)
    if settings is not None and hasattr(settings, "fx_uid"):
        try:
            settings.fx_uid = new_id
        except Exception:
            pass

    if shared:
        # The copy pointed at the original's collections: rebuild from the
        # persistent data into new collections owned by the new identity.
        if len(scene.ald.cloud_layers):
            scene["ald_clouds_signature"] = ""
            clouds.rebuild(scene)
        for system in scene.ald.fx_systems:
            system.uid = uuid.uuid4().hex
            for event in system.events:
                event.uid = uuid.uuid4().hex
        for system in scene.ald.fx_systems:
            fx.compile_system(scene, system)
    else:
        # The collections were copied but the objects are shared: duplicate
        # them, retag the copy's collections and rebuild the runtime.
        for collection in _ald_collections(scene):
            _duplicate_objects(collection)
        fx._retag_scene(scene, new_id)
        fx.rebuild_registry(scene)
        clouds.sync(scene)
        clouds.update_flash(scene)
    return max(1, len(shared))
