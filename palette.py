"""Atmospheric palettes: world, sun light and halation tint."""

import bpy

PRESETS = {
    "GOLDEN_HOUR": {
        "world_color": (1.0, 0.55, 0.25),
        "world_strength": 0.8,
        "sun_color": (1.0, 0.65, 0.35),
        "sun_energy": 4.0,
        "glare_tint": (1.0, 0.62, 0.38, 1.0),
    },
    "SUMMER_NOON": {
        "world_color": (0.45, 0.65, 1.0),
        "world_strength": 1.0,
        "sun_color": (1.0, 0.95, 0.85),
        "sun_energy": 5.0,
        "glare_tint": (1.0, 0.96, 0.85, 1.0),
    },
    "RAINY_TOKYO": {
        "world_color": (0.20, 0.30, 0.45),
        "world_strength": 0.6,
        "sun_color": (0.60, 0.75, 1.0),
        "sun_energy": 1.0,
        "glare_tint": (0.60, 0.80, 1.0, 1.0),
    },
    "NEON_NIGHT": {
        "world_color": (0.25, 0.05, 0.35),
        "world_strength": 0.5,
        "sun_color": (1.0, 0.20, 0.60),
        "sun_energy": 2.0,
        "glare_tint": (1.0, 0.20, 0.60, 1.0),
    },
}


def preset(key):
    return PRESETS.get(key, PRESETS["GOLDEN_HOUR"])


def glare_tint(key):
    return preset(key)["glare_tint"]


def apply_palette(scene, key):
    """Apply world + sun values for a palette. Returns the preset dict."""
    p = preset(key)
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("ALD | Atmosphere")
        scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    background = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBackground"), None)
    if background is None:
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputWorld")
        background = nt.nodes.new("ShaderNodeBackground")
        nt.links.new(background.outputs["Background"], out.inputs["Surface"])
    background.inputs["Color"].default_value = (*p["world_color"], 1.0)
    background.inputs["Strength"].default_value = p["world_strength"]

    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data.type == "SUN"), None)
    if sun is not None:
        sun.data.color = p["sun_color"]
        sun.data.energy = p["sun_energy"]

    scene["ald_last_palette"] = key
    return p
