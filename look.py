"""Resolve and apply the effective palette for a scene.

Precedence: camera override > shot marker > scene base palette.
"""


def effective_palette(scene):
    from . import cameras, shots

    override = cameras.camera_override(scene)
    if override is not None:
        return override, "camera"

    settings = getattr(scene, "ald", None)
    if settings is not None and settings.use_shot_markers:
        marker = shots.active_marker(scene)
        if marker is not None:
            return marker, "marker"

    key = settings.palette if settings is not None else "GOLDEN_HOUR"
    return key, "scene"


def apply_world(scene):
    """Apply the effective palette to world/sun only (cheap UI updates)."""
    key, source = effective_palette(scene)
    from . import palette
    palette.apply_palette(scene, key)
    scene["ald_effective_palette"] = key
    scene["ald_effective_source"] = source
    return key


def apply(scene, force=False):
    """Apply the effective palette, materials and stack."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return None
    key, source = effective_palette(scene)
    if not force and scene.get("ald_effective_palette") == key:
        scene["ald_effective_source"] = source
        return key

    from . import palette, materials, compositor

    palette.apply_palette(scene, key)
    if settings.shadow_tint or settings.toon_shading or settings.rim_light:
        strength = (settings.shadow_tint_strength
                    if settings.shadow_tint else 0.0)
        materials.sync_scene(scene, palette.shadow_tint_for(scene),
                             strength,
                             settings.shadow_tint_distance)
    else:
        materials.clear_scene(scene)
    if scene.compositing_node_group:
        compositor.build(scene)

    scene["ald_effective_palette"] = key
    scene["ald_effective_source"] = source
    scene["ald_active_shot"] = key if source == "marker" else ""
    return key
