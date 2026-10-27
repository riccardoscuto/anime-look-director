"""Persistent identity of a scene, independent of the FX systems.

The key is kept as ``ald_fx_id`` so existing files keep their identity (and the
sun owner tags keep working) after the World Sky reduction.
"""

import bpy
import uuid

ID_KEY = "ald_fx_id"
_CLAIMED = {}


def scene_id(scene):
    """Stable UUID of a scene; a duplicated scene receives a new one."""
    _prune()
    ident = scene.get(ID_KEY)
    if not ident:
        ident = uuid.uuid4().hex
        scene[ID_KEY] = ident
    owner = _CLAIMED.get(ident)
    if owner is not None and owner != scene.as_pointer():
        ident = uuid.uuid4().hex
        scene[ID_KEY] = ident
    _CLAIMED[ident] = scene.as_pointer()
    return ident


def same_identity(scene):
    """True when another scene still carries this scene's identity."""
    mine = scene.get(ID_KEY)
    if not mine:
        return False
    return any(other != scene and other.get(ID_KEY) == mine
               for other in bpy.data.scenes)


def _prune():
    alive = {scene.as_pointer() for scene in bpy.data.scenes}
    for ident, pointer in list(_CLAIMED.items()):
        if pointer not in alive:
            _CLAIMED.pop(ident, None)
