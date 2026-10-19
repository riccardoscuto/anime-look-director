"""Atmospheric palettes: world gradient, sun light and halation tint."""

import math

import bpy

GRADIENT_GROUP = "ALD | World Gradient"
AUTO_SUN_TAG = "ald_auto_sun"

PRESETS = {
    "GOLDEN_HOUR": {
        "world_color": (0.85, 0.38, 0.14),
        "world_strength": 0.9,
        "sky_color": (0.015, 0.042, 0.28),
        "mid_sky_color": (0.28, 0.09, 0.24),
        "horizon_color": (1.15, 0.32, 0.06),
        "ground_color": (0.12, 0.06, 0.05),
        "cloud_shadow": (0.07, 0.05, 0.16),
        "cloud_mid": (0.62, 0.18, 0.16),
        "cloud_light": (1.25, 0.55, 0.16),
        "sun_color": (1.0, 0.48, 0.18),
        "sun_energy": 4.2,
        "sun_rotation": (1.22, 0.12, -0.55),
        "glare_tint": (1.0, 0.52, 0.22, 1.0),
        "shadow_tint": (0.26, 0.34, 0.92),
    },
    "SUMMER_NOON": {
        "world_color": (0.32, 0.55, 0.95),
        "world_strength": 0.95,
        "sky_color": (0.018, 0.12, 0.65),
        "mid_sky_color": (0.11, 0.36, 0.85),
        "horizon_color": (0.52, 0.78, 0.98),
        "ground_color": (0.28, 0.25, 0.18),
        "cloud_shadow": (0.20, 0.28, 0.52),
        "cloud_mid": (0.74, 0.80, 0.90),
        "cloud_light": (1.20, 1.15, 1.02),
        "sun_color": (1.0, 0.93, 0.80),
        "sun_energy": 4.8,
        "sun_rotation": (0.68, 0.15, -0.65),
        "glare_tint": (1.0, 0.95, 0.82, 1.0),
        "shadow_tint": (0.28, 0.48, 0.90),
    },
    "RAINY_TOKYO": {
        "world_color": (0.12, 0.20, 0.30),
        "world_strength": 0.75,
        "sky_color": (0.022, 0.052, 0.105),
        "mid_sky_color": (0.075, 0.145, 0.22),
        "horizon_color": (0.22, 0.33, 0.42),
        "ground_color": (0.035, 0.05, 0.075),
        "cloud_shadow": (0.035, 0.06, 0.10),
        "cloud_mid": (0.14, 0.21, 0.28),
        "cloud_light": (0.34, 0.46, 0.56),
        "sun_color": (0.58, 0.76, 0.95),
        "sun_energy": 1.4,
        "sun_rotation": (0.85, 0.20, -0.45),
        "glare_tint": (0.55, 0.80, 1.0, 1.0),
        "shadow_tint": (0.20, 0.40, 0.75),
    },
    "NEON_NIGHT": {
        "world_color": (0.18, 0.03, 0.28),
        "world_strength": 0.7,
        "sky_color": (0.008, 0.012, 0.065),
        "mid_sky_color": (0.16, 0.02, 0.28),
        "horizon_color": (0.82, 0.06, 0.44),
        "ground_color": (0.02, 0.01, 0.045),
        "cloud_shadow": (0.02, 0.015, 0.07),
        "cloud_mid": (0.48, 0.05, 0.32),
        "cloud_light": (0.18, 0.78, 0.98),
        "sun_color": (1.0, 0.16, 0.52),
        "sun_energy": 2.4,
        "sun_rotation": (1.05, -0.18, -0.75),
        "glare_tint": (1.0, 0.18, 0.58, 1.0),
        "shadow_tint": (0.42, 0.14, 0.92),
    },
    "SAKURA_SPRING": {
        "world_color": (0.72, 0.48, 0.58),
        "world_strength": 0.9,
        "sky_color": (0.055, 0.16, 0.62),
        "mid_sky_color": (0.38, 0.28, 0.58),
        "horizon_color": (0.98, 0.50, 0.56),
        "ground_color": (0.24, 0.16, 0.18),
        "cloud_shadow": (0.26, 0.20, 0.40),
        "cloud_mid": (0.78, 0.54, 0.62),
        "cloud_light": (1.15, 0.90, 0.84),
        "sun_color": (1.0, 0.78, 0.72),
        "sun_energy": 4.0,
        "sun_rotation": (0.88, 0.14, -0.52),
        "glare_tint": (1.0, 0.72, 0.80, 1.0),
        "shadow_tint": (0.52, 0.36, 0.88),
    },
    "TWILIGHT_DUSK": {
        "world_color": (0.42, 0.14, 0.24),
        "world_strength": 0.8,
        "sky_color": (0.009, 0.016, 0.12),
        "mid_sky_color": (0.20, 0.05, 0.25),
        "horizon_color": (0.98, 0.20, 0.06),
        "ground_color": (0.05, 0.03, 0.06),
        "cloud_shadow": (0.03, 0.025, 0.09),
        "cloud_mid": (0.38, 0.07, 0.16),
        "cloud_light": (1.12, 0.30, 0.08),
        "sun_color": (1.0, 0.38, 0.15),
        "sun_energy": 3.2,
        "sun_rotation": (1.30, 0.10, -0.60),
        "glare_tint": (1.0, 0.42, 0.20, 1.0),
        "shadow_tint": (0.25, 0.30, 0.88),
    },
}


def preset(key):
    return PRESETS.get(key, PRESETS["GOLDEN_HOUR"])


def glare_tint(key):
    return preset(key)["glare_tint"]


def shadow_tint(key):
    return preset(key)["shadow_tint"]


def _mid_bridge(sky, horizon):
    """Compute a non-muddy chromatic bridge when custom colors are active."""
    return (
        min(1.0, (sky[0] * 0.35 + horizon[0] * 0.65) * 1.1),
        (sky[1] * 0.5 + horizon[1] * 0.5) * 0.75,
        min(1.0, (sky[2] * 0.65 + horizon[2] * 0.35) * 1.15),
    )


def effective(scene, key):
    """Preset values with the scene's custom color overrides applied."""
    p = dict(preset(key))
    settings = getattr(scene, "ald", None)
    if settings is not None and settings.custom_colors:
        sky = tuple(settings.custom_sky)
        horizon = tuple(settings.custom_horizon)
        sun = tuple(settings.custom_sun)
        shadow = tuple(settings.custom_shadow)
        p["sky_color"] = sky
        p["mid_sky_color"] = _mid_bridge(sky, horizon)
        p["horizon_color"] = horizon
        p["sun_color"] = sun
        p["shadow_tint"] = shadow
        p["cloud_shadow"] = tuple(c * 0.35 for c in shadow)
        p["cloud_mid"] = horizon
        p["cloud_light"] = sun
    return p


def shadow_tint_for(scene):
    settings = getattr(scene, "ald", None)
    if settings is None:
        return shadow_tint("GOLDEN_HOUR")
    key = scene.get("ald_effective_palette", settings.palette)
    return effective(scene, key)["shadow_tint"]


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
                           or ng.get("ald_build") != 6):
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GRADIENT_GROUP, "ShaderNodeTree")
        _build_gradient_group(ng)
        ng["ald_build"] = 6
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    types = {node.bl_idname for node in ng.nodes}
    if (not {"Sky Color", "Mid Sky Color", "Horizon Color", "Ground Color",
             "Horizon Offset", "Softness", "Sun Direction", "World Strength",
             "Cloud Amount"} <= names
            or "ShaderNodeMix" not in types
            or "ShaderNodeValToRGB" in types):
        _build_gradient_group(ng)
        ng["ald_build"] = 6
    return ng


def _build_gradient_group(ng):
    ng.nodes.clear()
    if hasattr(ng.interface, "clear"):
        ng.interface.clear()

    ng.interface.new_socket(name="Sky Color", in_out="INPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Mid Sky Color", in_out="INPUT",
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
    world_strength = ng.interface.new_socket(name="World Strength", in_out="INPUT",
                                             socket_type="NodeSocketFloat")
    world_strength.min_value = 0.0
    world_strength.max_value = 2.0
    world_strength.default_value = 1.0

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
    group_out.location = (2500, 0)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-1200, 320)

    view_norm = nodes.new("ShaderNodeVectorMath")
    view_norm.location = (-1020, 440)
    view_norm.operation = "NORMALIZE"
    links.new(texcoord.outputs["Generated"], view_norm.inputs[0])

    sun_norm = nodes.new("ShaderNodeVectorMath")
    sun_norm.location = (-1020, 600)
    sun_norm.operation = "NORMALIZE"
    links.new(group_in.outputs["Sun Direction"], sun_norm.inputs[0])

    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-1000, 280)
    links.new(view_norm.outputs["Vector"], separate.inputs["Vector"])

    to_unit = nodes.new("ShaderNodeMapRange")
    to_unit.location = (-820, 180)
    to_unit.clamp = True
    to_unit.inputs["From Min"].default_value = -1.0
    to_unit.inputs["From Max"].default_value = 1.0
    to_unit.inputs["To Min"].default_value = 0.0
    to_unit.inputs["To Max"].default_value = 1.0
    links.new(separate.outputs["Z"], to_unit.inputs["Value"])

    half = nodes.new("ShaderNodeMath")
    half.location = (-640, 120)
    half.operation = "MULTIPLY"
    half.inputs[1].default_value = 0.32
    links.new(group_in.outputs["Softness"], half.inputs[0])

    center = nodes.new("ShaderNodeMath")
    center.location = (-640, 320)
    center.operation = "ADD"
    center.inputs[1].default_value = 0.5
    links.new(group_in.outputs["Horizon Offset"], center.inputs[0])

    below = nodes.new("ShaderNodeMath")
    below.location = (-460, 380)
    below.operation = "SUBTRACT"
    links.new(center.outputs[0], below.inputs[0])
    links.new(half.outputs[0], below.inputs[1])

    above = nodes.new("ShaderNodeMath")
    above.location = (-460, 200)
    above.operation = "ADD"
    links.new(center.outputs[0], above.inputs[0])
    links.new(half.outputs[0], above.inputs[1])

    warp = nodes.new("ShaderNodeMapRange")
    warp.location = (-280, 120)
    warp.clamp = True
    warp.inputs["To Min"].default_value = 0.0
    warp.inputs["To Max"].default_value = 1.0
    links.new(to_unit.outputs["Result"], warp.inputs["Value"])
    links.new(below.outputs[0], warp.inputs["From Min"])
    links.new(above.outputs[0], warp.inputs["From Max"])

    low = nodes.new("ShaderNodeMapRange")
    low.location = (-80, 260)
    low.clamp = True
    _smooth(low)
    low.inputs["From Min"].default_value = 0.0
    low.inputs["From Max"].default_value = 0.5
    links.new(warp.outputs["Result"], low.inputs["Value"])

    mid = nodes.new("ShaderNodeMapRange")
    mid.location = (-80, 60)
    mid.clamp = True
    _smooth(mid)
    mid.inputs["From Min"].default_value = 0.5
    mid.inputs["From Max"].default_value = 0.74
    links.new(warp.outputs["Result"], mid.inputs["Value"])

    high = nodes.new("ShaderNodeMapRange")
    high.location = (-80, -140)
    high.clamp = True
    _smooth(high)
    high.inputs["From Min"].default_value = 0.70
    high.inputs["From Max"].default_value = 1.0
    links.new(warp.outputs["Result"], high.inputs["Value"])

    mix_ground = nodes.new("ShaderNodeMix")
    mix_ground.location = (120, 200)
    mix_ground.data_type = "RGBA"
    mix_ground.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_ground)
    links.new(group_in.outputs["Ground Color"], a_sock)
    links.new(group_in.outputs["Horizon Color"], b_sock)
    links.new(low.outputs["Result"], mix_ground.inputs["Factor"])

    mix_mid = nodes.new("ShaderNodeMix")
    mix_mid.location = (300, 120)
    mix_mid.data_type = "RGBA"
    mix_mid.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_mid)
    links.new(mix_ground.outputs["Result"], a_sock)
    links.new(group_in.outputs["Mid Sky Color"], b_sock)
    links.new(mid.outputs["Result"], mix_mid.inputs["Factor"])

    mix_sky = nodes.new("ShaderNodeMix")
    mix_sky.location = (480, 60)
    mix_sky.data_type = "RGBA"
    mix_sky.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_sky)
    links.new(mix_mid.outputs["Result"], a_sock)
    links.new(group_in.outputs["Sky Color"], b_sock)
    links.new(high.outputs["Result"], mix_sky.inputs["Factor"])

    sky_color = mix_sky.outputs["Result"]

    dot = nodes.new("ShaderNodeVectorMath")
    dot.location = (520, 360)
    dot.operation = "DOT_PRODUCT"
    links.new(view_norm.outputs["Vector"], dot.inputs[0])
    links.new(sun_norm.outputs["Vector"], dot.inputs[1])

    disk = nodes.new("ShaderNodeMapRange")
    disk.location = (700, 360)
    disk.clamp = True
    _smooth(disk)
    links.new(dot.outputs["Value"], disk.inputs["Value"])
    links.new(group_in.outputs["Sun Outer"], disk.inputs["From Min"])
    links.new(group_in.outputs["Sun Inner"], disk.inputs["From Max"])

    disk_scale = nodes.new("ShaderNodeMath")
    disk_scale.location = (880, 360)
    disk_scale.operation = "MULTIPLY"
    links.new(disk.outputs["Result"], disk_scale.inputs[0])
    links.new(group_in.outputs["Sun Strength"], disk_scale.inputs[1])

    disk_color = nodes.new("ShaderNodeVectorMath")
    disk_color.location = (1060, 360)
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
    noise.location = (1240, -120)
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.58
    noise.inputs["Distortion"].default_value = 0.25
    links.new(view_norm.outputs["Vector"], noise.inputs["Vector"])
    links.new(group_in.outputs["Cloud Scale"], noise.inputs["Scale"])

    detail_scale = nodes.new("ShaderNodeMath")
    detail_scale.location = (1060, -420)
    detail_scale.operation = "MULTIPLY"
    detail_scale.inputs[1].default_value = 2.6
    links.new(group_in.outputs["Cloud Scale"], detail_scale.inputs[0])

    detail = nodes.new("ShaderNodeTexNoise")
    detail.location = (1240, -420)
    detail.inputs["Detail"].default_value = 3.0
    detail.inputs["Roughness"].default_value = 0.52
    detail.inputs["Distortion"].default_value = 0.1
    links.new(view_norm.outputs["Vector"], detail.inputs["Vector"])
    links.new(detail_scale.outputs[0], detail.inputs["Scale"])

    base_weight = nodes.new("ShaderNodeMath")
    base_weight.location = (1420, -160)
    base_weight.operation = "MULTIPLY"
    base_weight.inputs[1].default_value = 0.76
    links.new(noise.outputs["Fac"], base_weight.inputs[0])

    detail_weight = nodes.new("ShaderNodeMath")
    detail_weight.location = (1420, -320)
    detail_weight.operation = "MULTIPLY"
    detail_weight.inputs[1].default_value = 0.24
    links.new(detail.outputs["Fac"], detail_weight.inputs[0])

    combined = nodes.new("ShaderNodeMath")
    combined.location = (1600, -240)
    combined.operation = "ADD"
    combined.use_clamp = True
    links.new(base_weight.outputs[0], combined.inputs[0])
    links.new(detail_weight.outputs[0], combined.inputs[1])

    coverage = nodes.new("ShaderNodeMapRange")
    coverage.location = (1420, -520)
    coverage.clamp = True
    _smooth(coverage)
    coverage.inputs["From Min"].default_value = 0.49
    coverage.inputs["From Max"].default_value = 0.55
    links.new(combined.outputs[0], coverage.inputs["Value"])

    sun_bias = nodes.new("ShaderNodeMapRange")
    sun_bias.location = (1240, -680)
    sun_bias.clamp = True
    sun_bias.inputs["From Min"].default_value = -0.5
    sun_bias.inputs["From Max"].default_value = 0.9
    sun_bias.inputs["To Min"].default_value = -0.06
    sun_bias.inputs["To Max"].default_value = 0.08
    links.new(dot.outputs["Value"], sun_bias.inputs["Value"])

    lit_signal = nodes.new("ShaderNodeMath")
    lit_signal.location = (1420, -680)
    lit_signal.operation = "ADD"
    links.new(combined.outputs[0], lit_signal.inputs[0])
    links.new(sun_bias.outputs["Result"], lit_signal.inputs[1])

    step_mid = nodes.new("ShaderNodeMapRange")
    step_mid.location = (1600, -640)
    step_mid.clamp = True
    _smooth(step_mid)
    step_mid.inputs["From Min"].default_value = 0.50
    step_mid.inputs["From Max"].default_value = 0.53
    links.new(lit_signal.outputs[0], step_mid.inputs["Value"])

    step_light = nodes.new("ShaderNodeMapRange")
    step_light.location = (1600, -820)
    step_light.clamp = True
    _smooth(step_light)
    step_light.inputs["From Min"].default_value = 0.56
    step_light.inputs["From Max"].default_value = 0.59
    links.new(lit_signal.outputs[0], step_light.inputs["Value"])

    mix_shadow = nodes.new("ShaderNodeMix")
    mix_shadow.location = (1780, -620)
    mix_shadow.data_type = "RGBA"
    mix_shadow.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_shadow)
    links.new(group_in.outputs["Cloud Shadow"], a_sock)
    links.new(group_in.outputs["Cloud Mid"], b_sock)
    links.new(step_mid.outputs["Result"], mix_shadow.inputs["Factor"])

    mix_light = nodes.new("ShaderNodeMix")
    mix_light.location = (1960, -580)
    mix_light.data_type = "RGBA"
    mix_light.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_light)
    links.new(mix_shadow.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)
    links.new(step_light.outputs["Result"], mix_light.inputs["Factor"])

    horizon = nodes.new("ShaderNodeMapRange")
    horizon.location = (1440, 700)
    horizon.clamp = True
    _smooth(horizon)
    horizon.inputs["From Min"].default_value = 0.03
    horizon.inputs["From Max"].default_value = 0.24
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
    cloud_mix.location = (2040, 0)
    cloud_mix.data_type = "RGBA"
    cloud_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(cloud_mix)
    links.new(sky_color, a_sock)
    links.new(mix_light.outputs["Result"], b_sock)
    links.new(cloud_amount_node.outputs[0], cloud_mix.inputs["Factor"])

    # Visible sky stays vivid; ambient light is scaled by World Strength.
    light_path = nodes.new("ShaderNodeLightPath")
    light_path.location = (2040, 420)
    ambient = nodes.new("ShaderNodeVectorMath")
    ambient.location = (2220, 220)
    ambient.operation = "SCALE"
    links.new(cloud_mix.outputs["Result"], ambient.inputs["Vector"])
    links.new(group_in.outputs["World Strength"], ambient.inputs["Scale"])

    visible = nodes.new("ShaderNodeMix")
    visible.location = (2320, 0)
    visible.data_type = "RGBA"
    visible.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(visible)
    links.new(ambient.outputs["Vector"], a_sock)
    links.new(cloud_mix.outputs["Result"], b_sock)
    links.new(light_path.outputs["Is Camera Ray"], visible.inputs["Factor"])
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
    if sun.get(AUTO_SUN_TAG) and sun.parent is None:
        quaternion = sun.rotation_euler.to_quaternion()
    else:
        quaternion = sun.matrix_world.to_quaternion()
    direction = quaternion @ Vector((0.0, 0.0, -1.0))
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
        background.inputs["Strength"].default_value = p["world_strength"]
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

    mid_sky = p.get("mid_sky_color") or _mid_bridge(
        p["sky_color"], p["horizon_color"])
    cloud_sh = p.get("cloud_shadow") or tuple(
        c * 0.45 for c in p["shadow_tint"])
    cloud_md = p.get("cloud_mid") or p["horizon_color"]
    cloud_lt = p.get("cloud_light") or p["sun_color"]

    node.inputs["Sky Color"].default_value = _rgba(p["sky_color"])
    node.inputs["Mid Sky Color"].default_value = _rgba(mid_sky)
    node.inputs["Horizon Color"].default_value = _rgba(p["horizon_color"])
    node.inputs["Ground Color"].default_value = _rgba(p["ground_color"])
    node.inputs["Sun Color"].default_value = _rgba(p["sun_color"])
    node.inputs["Cloud Shadow"].default_value = _rgba(cloud_sh)
    node.inputs["Cloud Mid"].default_value = _rgba(cloud_md)
    node.inputs["Cloud Light"].default_value = _rgba(cloud_lt)
    if settings is not None:
        node.inputs["Horizon Offset"].default_value = settings.horizon_offset
        node.inputs["Softness"].default_value = settings.horizon_softness
    node.inputs["World Strength"].default_value = p["world_strength"]
    background.inputs["Strength"].default_value = 1.0

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
    rotation = p.get("sun_rotation", (0.9, 0.15, -0.6))
    if sun is None and (settings is None or settings.auto_sun):
        data = bpy.data.lights.new("ALD | Sun", "SUN")
        data.angle = 0.05
        sun = bpy.data.objects.new("ALD | Sun", data)
        sun[AUTO_SUN_TAG] = True
        sun.rotation_euler = rotation
        scene.collection.objects.link(sun)
        created = True

    if sun is not None and sun.data is not None:
        if sun.library is None and sun.data.library is None:
            sun.data.color = p["sun_color"]
            sun.data.energy = p["sun_energy"]
            if sun.get(AUTO_SUN_TAG):
                sun.rotation_euler = rotation
    return sun, created


def apply_palette(scene, key):
    """Apply world gradient + sun values for a palette. Returns the preset."""
    p = effective(scene, key)
    settings = getattr(scene, "ald", None)
    world = _ensure_world(scene)
    ensure_sun(scene, p)
    nt, background = _world_nodes(world)
    _apply_gradient(scene, settings, nt, background, p)
    scene["ald_last_palette"] = key
    scene["ald_effective_palette"] = key
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
