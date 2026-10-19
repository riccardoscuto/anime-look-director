"""Atmospheric palettes: world gradient, sun light and halation tint."""

import math

import bpy

GRADIENT_GROUP = "ALD | World Gradient"
AUTO_SUN_TAG = "ald_auto_sun"

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
        "shadow_tint": (0.44, 0.53, 1.0),
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
        "shadow_tint": (0.44, 0.60, 1.0),
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
        "shadow_tint": (0.38, 0.57, 1.0),
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
        "shadow_tint": (0.72, 0.19, 1.0),
    },
    "SAKURA_SPRING": {
        "world_color": (0.85, 0.65, 0.75),
        "world_strength": 0.75,
        "sky_color": (0.28, 0.42, 0.85),
        "horizon_color": (1.0, 0.60, 0.70),
        "ground_color": (0.43, 0.34, 0.32),
        "sun_color": (1.0, 0.82, 0.76),
        "sun_energy": 4.0,
        "glare_tint": (1.0, 0.78, 0.84, 1.0),
        "shadow_tint": (0.62, 0.46, 1.0),
    },
    "TWILIGHT_DUSK": {
        "world_color": (0.55, 0.25, 0.35),
        "world_strength": 0.65,
        "sky_color": (0.08, 0.10, 0.35),
        "horizon_color": (0.95, 0.42, 0.25),
        "ground_color": (0.10, 0.08, 0.12),
        "sun_color": (1.0, 0.55, 0.30),
        "sun_energy": 3.0,
        "glare_tint": (1.0, 0.55, 0.35, 1.0),
        "shadow_tint": (0.50, 0.38, 1.0),
    },
}


def preset(key):
    return PRESETS.get(key, PRESETS["GOLDEN_HOUR"])


def glare_tint(key):
    return preset(key)["glare_tint"]


def shadow_tint(key):
    return preset(key)["shadow_tint"]


def effective(scene, key):
    """Preset values with the scene's custom color overrides applied."""
    p = dict(preset(key))
    settings = getattr(scene, "ald", None)
    if settings is not None and settings.custom_colors:
        p["sky_color"] = tuple(settings.custom_sky)
        p["horizon_color"] = tuple(settings.custom_horizon)
        p["sun_color"] = tuple(settings.custom_sun)
        p["shadow_tint"] = tuple(settings.custom_shadow)
    return p


def shadow_tint_for(scene):
    settings = getattr(scene, "ald", None)
    if settings is None:
        return shadow_tint("GOLDEN_HOUR")
    return effective(scene, settings.palette)["shadow_tint"]


def _rgba(color):
    return tuple(color) + (1.0,) if len(color) == 3 else tuple(color)


def _smooth(node):
    try:
        items = [item.identifier for item in
                 node.bl_rna.properties["interpolation_type"].enum_items]
        if "SMOOTHSTEP" in items:
            node.interpolation_type = "SMOOTHSTEP"
    except Exception:
        pass


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
                           or ng.get("ald_build") != 3):
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GRADIENT_GROUP, "ShaderNodeTree")
        _build_gradient_group(ng)
        ng["ald_build"] = 3
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    types = {node.bl_idname for node in ng.nodes}
    if (not {"Sky Color", "Horizon Color", "Ground Color",
             "Horizon Offset", "Softness", "Sun Direction",
             "Cloud Amount"} <= names
            or "ShaderNodeMix" not in types
            or "ShaderNodeValToRGB" in types):
        _build_gradient_group(ng)
        ng["ald_build"] = 3
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

    sun_dir = ng.interface.new_socket(name="Sun Direction", in_out="INPUT",
                                      socket_type="NodeSocketVector")
    sun_dir.default_value = (0.0, 0.0, 1.0)
    sun_inner = ng.interface.new_socket(name="Sun Inner", in_out="INPUT",
                                        socket_type="NodeSocketFloat")
    sun_inner.default_value = 0.999
    sun_outer = ng.interface.new_socket(name="Sun Outer", in_out="INPUT",
                                        socket_type="NodeSocketFloat")
    sun_outer.default_value = 0.9995
    sun_color = ng.interface.new_socket(name="Sun Color", in_out="INPUT",
                                        socket_type="NodeSocketColor")
    sun_color.default_value = (1.0, 0.9, 0.8, 1.0)
    sun_strength = ng.interface.new_socket(name="Sun Strength", in_out="INPUT",
                                           socket_type="NodeSocketFloat")
    sun_strength.min_value = 0.0
    sun_strength.max_value = 50.0
    sun_strength.default_value = 0.0
    cloud_shadow = ng.interface.new_socket(name="Cloud Shadow", in_out="INPUT",
                                           socket_type="NodeSocketColor")
    cloud_shadow.default_value = (0.15, 0.15, 0.22, 1.0)
    cloud_mid = ng.interface.new_socket(name="Cloud Mid", in_out="INPUT",
                                        socket_type="NodeSocketColor")
    cloud_mid.default_value = (0.6, 0.6, 0.7, 1.0)
    cloud_light = ng.interface.new_socket(name="Cloud Light", in_out="INPUT",
                                          socket_type="NodeSocketColor")
    cloud_light.default_value = (1.0, 0.9, 0.8, 1.0)
    cloud_amount = ng.interface.new_socket(name="Cloud Amount", in_out="INPUT",
                                           socket_type="NodeSocketFloat")
    cloud_amount.min_value = 0.0
    cloud_amount.max_value = 1.0
    cloud_amount.default_value = 0.0
    cloud_scale = ng.interface.new_socket(name="Cloud Scale", in_out="INPUT",
                                          socket_type="NodeSocketFloat")
    cloud_scale.min_value = 0.5
    cloud_scale.max_value = 12.0
    cloud_scale.default_value = 3.0

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

    sky_color = mix_sky.outputs["Result"]

    dot = nodes.new("ShaderNodeVectorMath")
    dot.location = (520, 320)
    dot.operation = "DOT_PRODUCT"
    links.new(texcoord.outputs["Generated"], dot.inputs[0])
    links.new(group_in.outputs["Sun Direction"], dot.inputs[1])

    disk = nodes.new("ShaderNodeMapRange")
    disk.location = (700, 320)
    disk.clamp = True
    _smooth(disk)
    links.new(dot.outputs["Value"], disk.inputs["Value"])
    links.new(group_in.outputs["Sun Outer"], disk.inputs["From Min"])
    links.new(group_in.outputs["Sun Inner"], disk.inputs["From Max"])
    disk.inputs["To Min"].default_value = 0.0
    disk.inputs["To Max"].default_value = 1.0

    disk_scale = nodes.new("ShaderNodeMath")
    disk_scale.location = (880, 320)
    disk_scale.operation = "MULTIPLY"
    links.new(disk.outputs["Result"], disk_scale.inputs[0])
    links.new(group_in.outputs["Sun Strength"], disk_scale.inputs[1])

    disk_color = nodes.new("ShaderNodeVectorMath")
    disk_color.location = (1060, 320)
    disk_color.operation = "SCALE"
    links.new(group_in.outputs["Sun Color"], disk_color.inputs["Vector"])
    links.new(disk_scale.outputs[0], disk_color.inputs["Scale"])

    sun_add = nodes.new("ShaderNodeMix")
    sun_add.location = (1240, 220)
    sun_add.data_type = "RGBA"
    sun_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(sun_add)
    links.new(sky_color, a_sock)
    links.new(disk_color.outputs["Vector"], b_sock)
    sun_add.inputs["Factor"].default_value = 1.0
    sky_color = result_sock

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (1440, -120)
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.55
    noise.inputs["Distortion"].default_value = 0.35
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(group_in.outputs["Cloud Scale"], noise.inputs["Scale"])

    detail_scale = nodes.new("ShaderNodeMath")
    detail_scale.location = (1260, -420)
    detail_scale.operation = "MULTIPLY"
    detail_scale.inputs[1].default_value = 2.5
    links.new(group_in.outputs["Cloud Scale"], detail_scale.inputs[0])

    detail = nodes.new("ShaderNodeTexNoise")
    detail.location = (1440, -420)
    detail.inputs["Detail"].default_value = 2.0
    detail.inputs["Roughness"].default_value = 0.5
    detail.inputs["Distortion"].default_value = 0.1
    links.new(texcoord.outputs["Generated"], detail.inputs["Vector"])
    links.new(detail_scale.outputs[0], detail.inputs["Scale"])

    base_weight = nodes.new("ShaderNodeMath")
    base_weight.location = (1440, -160)
    base_weight.operation = "MULTIPLY"
    base_weight.inputs[1].default_value = 0.75
    links.new(noise.outputs["Fac"], base_weight.inputs[0])

    detail_weight = nodes.new("ShaderNodeMath")
    detail_weight.location = (1440, -320)
    detail_weight.operation = "MULTIPLY"
    detail_weight.inputs[1].default_value = 0.25
    links.new(detail.outputs["Fac"], detail_weight.inputs[0])

    combined = nodes.new("ShaderNodeMath")
    combined.location = (1620, -240)
    combined.operation = "ADD"
    combined.use_clamp = True
    links.new(base_weight.outputs[0], combined.inputs[0])
    links.new(detail_weight.outputs[0], combined.inputs[1])

    coverage = nodes.new("ShaderNodeMapRange")
    coverage.location = (1440, -520)
    coverage.clamp = True
    _smooth(coverage)
    coverage.inputs["From Min"].default_value = 0.48
    coverage.inputs["From Max"].default_value = 0.56
    coverage.inputs["To Min"].default_value = 0.0
    coverage.inputs["To Max"].default_value = 1.0
    links.new(combined.outputs[0], coverage.inputs["Value"])

    step_mid = nodes.new("ShaderNodeMapRange")
    step_mid.location = (1440, -680)
    step_mid.clamp = True
    _smooth(step_mid)
    step_mid.inputs["From Min"].default_value = 0.46
    step_mid.inputs["From Max"].default_value = 0.48
    step_mid.inputs["To Min"].default_value = 0.0
    step_mid.inputs["To Max"].default_value = 1.0
    links.new(combined.outputs[0], step_mid.inputs["Value"])

    step_light = nodes.new("ShaderNodeMapRange")
    step_light.location = (1440, -840)
    step_light.clamp = True
    _smooth(step_light)
    step_light.inputs["From Min"].default_value = 0.57
    step_light.inputs["From Max"].default_value = 0.59
    step_light.inputs["To Min"].default_value = 0.0
    step_light.inputs["To Max"].default_value = 1.0
    links.new(combined.outputs[0], step_light.inputs["Value"])

    mix_shadow = nodes.new("ShaderNodeMix")
    mix_shadow.location = (1620, -620)
    mix_shadow.data_type = "RGBA"
    mix_shadow.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_shadow)
    links.new(group_in.outputs["Cloud Shadow"], a_sock)
    links.new(group_in.outputs["Cloud Mid"], b_sock)
    links.new(step_mid.outputs[0], mix_shadow.inputs["Factor"])

    mix_light = nodes.new("ShaderNodeMix")
    mix_light.location = (1820, -580)
    mix_light.data_type = "RGBA"
    mix_light.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_light)
    links.new(mix_shadow.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)
    links.new(step_light.outputs[0], mix_light.inputs["Factor"])

    horizon = nodes.new("ShaderNodeMapRange")
    horizon.location = (1440, 700)
    horizon.clamp = True
    _smooth(horizon)
    horizon.inputs["From Min"].default_value = 0.02
    horizon.inputs["From Max"].default_value = 0.25
    horizon.inputs["To Min"].default_value = 0.0
    horizon.inputs["To Max"].default_value = 1.0
    links.new(separate.outputs["Z"], horizon.inputs["Value"])

    cloud_mask = nodes.new("ShaderNodeMath")
    cloud_mask.location = (1640, 660)
    cloud_mask.operation = "MULTIPLY"
    cloud_mask.use_clamp = True
    links.new(coverage.outputs["Result"], cloud_mask.inputs[0])
    links.new(horizon.outputs["Result"], cloud_mask.inputs[1])

    cloud_amount_node = nodes.new("ShaderNodeMath")
    cloud_amount_node.location = (1820, 620)
    cloud_amount_node.operation = "MULTIPLY"
    cloud_amount_node.use_clamp = True
    links.new(cloud_mask.outputs[0], cloud_amount_node.inputs[0])
    links.new(group_in.outputs["Cloud Amount"], cloud_amount_node.inputs[1])

    cloud_mix = nodes.new("ShaderNodeMix")
    cloud_mix.location = (2020, 0)
    cloud_mix.data_type = "RGBA"
    cloud_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(cloud_mix)
    links.new(sky_color, a_sock)
    links.new(mix_light.outputs["Result"], b_sock)
    links.new(cloud_amount_node.outputs[0], cloud_mix.inputs["Factor"])
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


def sun_toward(scene):
    """Unit vector from the scene toward the sun, or None."""
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    if sun is None:
        return None
    from mathutils import Vector
    direction = sun.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    return (-direction.x, -direction.y, -direction.z)


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
    node.inputs["Sun Color"].default_value = _rgba(p["sun_color"])
    node.inputs["Cloud Shadow"].default_value = _rgba(
        tuple(component * 0.45 for component in p["shadow_tint"]))
    node.inputs["Cloud Mid"].default_value = _rgba(p["horizon_color"])
    node.inputs["Cloud Light"].default_value = _rgba(p["sun_color"])
    if settings is not None:
        node.inputs["Horizon Offset"].default_value = settings.horizon_offset
        node.inputs["Softness"].default_value = settings.horizon_softness

    direction = sun_toward(scene)
    if direction is not None:
        node.inputs["Sun Direction"].default_value = direction
    sun_disk = getattr(settings, "sun_disk", True) if settings else True
    sun_strength = (getattr(settings, "sun_disk_strength", 6.0)
                    if settings else 6.0)
    node.inputs["Sun Strength"].default_value = (
        sun_strength if sun_disk and direction is not None else 0.0)
    radius = max(0.1, getattr(settings, "sun_disk_size", 1.5)
                 if settings else 1.5)
    softness = max(0.2, radius * 0.25)
    node.inputs["Sun Inner"].default_value = math.cos(math.radians(radius))
    node.inputs["Sun Outer"].default_value = math.cos(
        math.radians(radius + softness))

    clouds = getattr(settings, "clouds", True) if settings else False
    node.inputs["Cloud Amount"].default_value = (
        getattr(settings, "cloud_amount", 0.6) if clouds else 0.0)
    node.inputs["Cloud Scale"].default_value = (
        getattr(settings, "cloud_scale", 3.0) if settings else 3.0)

    for link in list(background.inputs["Color"].links):
        nt.links.remove(link)
    nt.links.new(node.outputs["Color"], background.inputs["Color"])


def ensure_sun(scene, p):
    """Tint the scene sun, creating one when none exists (auto_sun)."""
    settings = getattr(scene, "ald", None)
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    created = False
    if sun is None and (settings is None or settings.auto_sun):
        data = bpy.data.lights.new("ALD | Sun", "SUN")
        data.angle = 0.05
        sun = bpy.data.objects.new("ALD | Sun", data)
        sun[AUTO_SUN_TAG] = True
        sun.rotation_euler = (0.9, 0.15, -0.6)
        scene.collection.objects.link(sun)
        created = True

    if sun is not None and sun.data is not None:
        if sun.library is None and sun.data.library is None:
            sun.data.color = p["sun_color"]
            sun.data.energy = p["sun_energy"]
    return sun, created


def apply_palette(scene, key):
    """Apply world gradient + sun values for a palette. Returns the preset."""
    p = effective(scene, key)
    settings = getattr(scene, "ald", None)
    world = _ensure_world(scene)
    ensure_sun(scene, p)
    nt, background = _world_nodes(world)
    _apply_gradient(scene, settings, nt, background, p)
    background.inputs["Strength"].default_value = p["world_strength"]
    scene["ald_last_palette"] = key
    return p


def update_sun_controls(scene):
    """Keep the sun disk direction/color in sync during animation."""
    world = scene.world
    if world is None or world.node_tree is None:
        return
    node = _gradient_node(world.node_tree)
    if node is None:
        return
    settings = getattr(scene, "ald", None)
    direction = sun_toward(scene)
    if direction is None:
        node.inputs["Sun Strength"].default_value = 0.0
        return
    node.inputs["Sun Direction"].default_value = direction
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    if sun is not None and sun.data is not None:
        node.inputs["Sun Color"].default_value = _rgba(sun.data.color)
        node.inputs["Cloud Light"].default_value = _rgba(sun.data.color)
    if settings is not None and settings.sun_disk:
        node.inputs["Sun Strength"].default_value = settings.sun_disk_strength
    else:
        node.inputs["Sun Strength"].default_value = 0.0


def _on_frame_change(scene, *_args):
    try:
        update_sun_controls(scene)
    except Exception:
        pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
