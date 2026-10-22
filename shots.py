"""Timeline markers as per-shot palette overrides."""

import bpy
from bpy.app.handlers import persistent

from .properties import PALETTES

MARKER_PREFIX = "ALD:"
PALETTE_KEYS = {key for key, _label, _desc in PALETTES}


def marker_name(key):
    return MARKER_PREFIX + key


def palette_from_marker(name):
    if not name.startswith(MARKER_PREFIX):
        return None
    key = name[len(MARKER_PREFIX):].strip().upper()
    return key if key in PALETTE_KEYS else None


def active_marker(scene):
    """Palette of the last valid marker at or before the current frame."""
    frame = scene.frame_current
    best_frame = None
    best_key = None
    for marker in scene.timeline_markers:
        key = palette_from_marker(marker.name)
        if key is None or marker.frame > frame:
            continue
        if best_frame is None or marker.frame > best_frame:
            best_frame = marker.frame
            best_key = key
    return best_key


def apply_for_frame(scene, force=False):
    """Apply the effective palette resolved from camera/marker/base."""
    settings = getattr(scene, "ald", None)
    if settings is None or not settings.use_shot_markers:
        return None
    from . import look
    return look.apply(scene, force=force)


@persistent
def _on_frame_change(scene, *_args):
    from . import snapshot
    if snapshot.is_inactive(scene):
        return
    try:
        apply_for_frame(scene)
    except Exception:
        pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(_on_frame_change)
