"""Timeline markers as per-shot palette overrides."""

import bpy

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


def _apply(scene, key):
    from . import palette, materials, compositor

    settings = scene.ald
    if settings.palette != key:
        settings.palette = key
        return
    palette.apply_palette(scene, key)
    if settings.shadow_tint:
        materials.sync_scene(scene, palette.shadow_tint(key),
                             settings.shadow_tint_strength,
                             settings.shadow_tint_distance)
    if scene.compositing_node_group:
        compositor.build(scene)


def apply_for_frame(scene, force=False):
    """Apply the active marker palette; returns the key when it changed."""
    settings = getattr(scene, "ald", None)
    if settings is None or not settings.use_shot_markers:
        return None
    key = active_marker(scene)
    if key is None:
        return None
    if not force and scene.get("ald_active_shot") == key:
        return None
    scene["ald_active_shot"] = key
    _apply(scene, key)
    return key


def _on_frame_change(scene, *_args):
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
