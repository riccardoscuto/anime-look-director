"""Atmospheric palettes: world gradient, sun light and halation tint."""

import bpy

GRADIENT_GROUP = "ALD | World Gradient"

PRESETS = {
    "GOLDEN_HOUR": {
        "world_color": (1.0, 0.55, 0.25),
        "world_strength": 0.8,
        "sky_color": (0.22, 0.30, 0.62),
        "horizon_color": (1.0, 0.55, 0.28),
        "ground_color": (0.30, 0.18, 0.12),
        "sun_color": (1.0, 0.65, 0.35),
        "sun_energy": 4.0,
        "glare_tint": (1.0, 0.62, 0.38, 1.0),
        "shadow_tint": (0.30, 0.36, 0.68),
    },
    "SUMMER_NOON": {
        "world_color": (0.45, 0.65, 1.0),
        "world_strength": 0.85,
        "sky_color": (0.12, 0.36, 0.95),
        "horizon_color": (0.62, 0.80, 1.0),
        "ground_color": (0.52, 0.47, 0.34),
        "sun_color": (1.0, 0.95, 0.85),
        "sun_energy": 4.5,
        "glare_tint": (1.0, 0.96, 0.85, 1.0),
        "shadow_tint": (0.35, 0.48, 0.80),
    },
    "RAINY_TOKYO": {
        "world_color": (0.20, 0.30, 0.45),
        "world_strength": 0.6,
        "sky_color": (0.06, 0.10, 0.20),
        "horizon_color": (0.32, 0.42, 0.58),
        "ground_color": (0.07, 0.09, 0.13),
        "sun_color": (0.60, 0.75, 1.0),
        "sun_energy": 1.0,
        "glare_tint": (0.60, 0.80, 1.0, 1.0),
        "shadow_tint": (0.20, 0.30, 0.52),
    },
    "NEON_NIGHT": {
        "world_color": (0.25, 0.05, 0.35),
        "world_strength": 0.5,
        "sky_color": (0.03, 0.08, 0.26),
        "horizon_color": (0.85, 0.10, 0.55),
        "ground_color": (0.04, 0.02, 0.07),
        "sun_color": (1.0, 0.20, 0.60),
        "sun_energy": 2.0,
        "glare_tint": (1.0, 0.20, 0.60, 1.0),
        "shadow_tint": (0.45, 0.12, 0.62),
    },
}


def preset(key):
    return PRESETS.get(key, PRESETS["GOLDEN_HOUR"])


def glare_tint(key):
    return preset(key)["glare_tint"]


def shadow_tint(key):
    return preset(key)["shadow_tint"]


def _rgba(color):
    return tuple(color) + (1.0,) if len(color) == 3 else tuple(color)


def _rgba_sockets(mix):
    a = b = result = None
    for sock in mix.inputs:
        if sock.name == "A" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            a = sock
        elif sock.name == "B" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            b = sock
    for sock in mix.outputs:
        if sock.name == "Result" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            result = sock
    return a, b, result


def _gradient_group():
    """Return the shared world-gradient group, building it on first use."""
    ng = bpy.data.node_groups.get(GRADIENT_GROUP)
    if ng is not None and (ng.bl_idname != "ShaderNodeTree"
                           or ng.get("ald_build") != 2):
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GRADIENT_GROUP, "ShaderNodeTree")
        _build_gradient_group(ng)
        ng["ald_build"] = 2
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    types = {node.bl_idname for node in ng.nodes}
    if (not {"Sky Color", "Horizon Color", "Ground Color",
             "Horizon Offset", "Softness"} <= names
            or "ShaderNodeMix" not in types
            or "ShaderNodeValToRGB" in types):
        _build_gradient_group(ng)
        ng["ald_build"] = 2
    return ng


def _build_gradient_group(ng):
    ng.nodes.clear()
    if hasattr(ng.interface, "clear"):
        ng.interface.clear()

    ng.interface.new_socket(name="Sky Color", in_out="INPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Horizon Color", in_out="INPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Ground Color", in_out="INPUT",
                            socket_type="NodeSocketColor")
    offset = ng.interface.new_socket(name="Horizon Offset", in_out="INPUT",
                                     socket_type="NodeSocketFloat")
    offset.min_value = -0.9
    offset.max_value = 0.9
    offset.default_value = 0.0
    softness = ng.interface.new_socket(name="Softness", in_out="INPUT",
                                       socket_type="NodeSocketFloat")
    softness.min_value = 0.02
    softness.max_value = 1.0
    softness.default_value = 0.5
    ng.interface.new_socket(name="Color", in_out="OUTPUT",
                            socket_type="NodeSocketColor")

    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1200, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (700, 0)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-1200, 320)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-1000, 360)
    links.new(texcoord.outputs["Generated"], separate.inputs["Vector"])

    # Z direction (-1..1) -> 0..1, then warp around the horizon.
    to_unit = nodes.new("ShaderNodeMapRange")
    to_unit.location = (-1000, 180)
    to_unit.clamp = True
    to_unit.inputs["From Min"].default_value = -1.0
    to_unit.inputs["From Max"].default_value = 1.0
    to_unit.inputs["To Min"].default_value = 0.0
    to_unit.inputs["To Max"].default_value = 1.0
    links.new(separate.outputs["Z"], to_unit.inputs["Value"])

    half = nodes.new("ShaderNodeMath")
    half.location = (-780, 120)
    half.operation = "MULTIPLY"
    half.inputs[1].default_value = 0.25
    links.new(group_in.outputs["Softness"], half.inputs[0])

    center = nodes.new("ShaderNodeMath")
    center.location = (-780, 320)
    center.operation = "ADD"
    center.inputs[1].default_value = 0.5
    links.new(group_in.outputs["Horizon Offset"], center.inputs[0])

    below = nodes.new("ShaderNodeMath")
    below.location = (-580, 380)
    below.operation = "SUBTRACT"
    links.new(center.outputs[0], below.inputs[0])
    links.new(half.outputs[0], below.inputs[1])

    above = nodes.new("ShaderNodeMath")
    above.location = (-580, 200)
    above.operation = "ADD"
    links.new(center.outputs[0], above.inputs[0])
    links.new(half.outputs[0], above.inputs[1])

    warp = nodes.new("ShaderNodeMapRange")
    warp.location = (-360, 120)
    warp.clamp = True
    warp.inputs["To Min"].default_value = 0.0
    warp.inputs["To Max"].default_value = 1.0
    links.new(to_unit.outputs["Result"], warp.inputs["Value"])
    links.new(below.outputs[0], warp.inputs["From Min"])
    links.new(above.outputs[0], warp.inputs["From Max"])

    # 0 = ground, 0.5 = horizon, 1 = sky, blended with socket-driven colors.
    low = nodes.new("ShaderNodeMapRange")
    low.location = (-130, 260)
    low.clamp = True
    if "SMOOTHSTEP" in [item.identifier for item in
                        low.bl_rna.properties["interpolation_type"].enum_items]:
        low.interpolation_type = "SMOOTHSTEP"
    low.inputs["From Min"].default_value = 0.0
    low.inputs["From Max"].default_value = 0.5
    low.inputs["To Min"].default_value = 0.0
    low.inputs["To Max"].default_value = 1.0
    links.new(warp.outputs["Result"], low.inputs["Value"])

    high = nodes.new("ShaderNodeMapRange")
    high.location = (-130, 20)
    high.clamp = True
    if "SMOOTHSTEP" in [item.identifier for item in
                        high.bl_rna.properties["interpolation_type"].enum_items]:
        high.interpolation_type = "SMOOTHSTEP"
    high.inputs["From Min"].default_value = 0.5
    high.inputs["From Max"].default_value = 1.0
    high.inputs["To Min"].default_value = 0.0
    high.inputs["To Max"].default_value = 1.0
    links.new(warp.outputs["Result"], high.inputs["Value"])

    mix_ground = nodes.new("ShaderNodeMix")
    mix_ground.location = (110, 160)
    mix_ground.data_type = "RGBA"
    mix_ground.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_ground)
    links.new(group_in.outputs["Ground Color"], a_sock)
    links.new(group_in.outputs["Horizon Color"], b_sock)
    links.new(low.outputs["Result"], mix_ground.inputs["Factor"])

    mix_sky = nodes.new("ShaderNodeMix")
    mix_sky.location = (370, 100)
    mix_sky.data_type = "RGBA"
    mix_sky.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_sky)
    links.new(mix_ground.outputs["Result"], a_sock)
    links.new(group_in.outputs["Sky Color"], b_sock)
    links.new(high.outputs["Result"], mix_sky.inputs["Factor"])
    links.new(result_sock, group_out.inputs["Color"])


def _ensure_world(scene):
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("ALD | Atmosphere")
        scene.world = world
    world.use_nodes = True
    return world


def _world_nodes(world):
    nt = world.node_tree
    out = next((n for n in nt.nodes
                if n.bl_idname == "ShaderNodeOutputWorld"), None)
    background = next((n for n in nt.nodes
                       if n.bl_idname == "ShaderNodeBackground"), None)
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputWorld")
    if background is None:
        background = nt.nodes.new("ShaderNodeBackground")
        background.location = (-300, 300)
    if not out.inputs["Surface"].is_linked:
        nt.links.new(background.outputs["Background"], out.inputs["Surface"])
    return nt, background


def _gradient_node(nt):
    return next((n for n in nt.nodes if n.get("ald_world_gradient")), None)


def _apply_gradient(scene, settings, nt, background, p):
    enabled = settings.world_gradient if settings is not None else True
    node = _gradient_node(nt)

    if not enabled:
        if node is not None:
            nt.nodes.remove(node)
        for link in list(background.inputs["Color"].links):
            nt.links.remove(link)
        background.inputs["Color"].default_value = _rgba(p["world_color"])
        return

    group = _gradient_group()
    if node is None or node.node_tree != group:
        if node is not None:
            nt.nodes.remove(node)
        node = nt.nodes.new("ShaderNodeGroup")
        node.node_tree = group
        node["ald_world_gradient"] = True
        node.name = "ALD | World Gradient"
        node.location = (-600, 300)

    node.inputs["Sky Color"].default_value = _rgba(p["sky_color"])
    node.inputs["Horizon Color"].default_value = _rgba(p["horizon_color"])
    node.inputs["Ground Color"].default_value = _rgba(p["ground_color"])
    if settings is not None:
        node.inputs["Horizon Offset"].default_value = settings.horizon_offset
        node.inputs["Softness"].default_value = settings.horizon_softness

    for link in list(background.inputs["Color"].links):
        nt.links.remove(link)
    nt.links.new(node.outputs["Color"], background.inputs["Color"])


def apply_palette(scene, key):
    """Apply world gradient + sun values for a palette. Returns the preset."""
    p = preset(key)
    settings = getattr(scene, "ald", None)
    world = _ensure_world(scene)
    nt, background = _world_nodes(world)
    _apply_gradient(scene, settings, nt, background, p)
    background.inputs["Strength"].default_value = p["world_strength"]

    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data.type == "SUN"), None)
    if sun is not None:
        sun.data.color = p["sun_color"]
        sun.data.energy = p["sun_energy"]

    scene["ald_last_palette"] = key
    return p
