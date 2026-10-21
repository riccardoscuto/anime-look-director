"""Atmospheric palettes: world gradient, sun light and halation tint."""

import math

import bpy

GRADIENT_GROUP = "ALD | World Gradient"
AUTO_SUN_TAG = "ald_auto_sun"

PRESETS = {
    "GOLDEN_HOUR": {
        "world_color": (0.85, 0.38, 0.14),
        "world_strength": 0.9,
        "sky_color": (0.012, 0.048, 0.34),
        "mid_sky_color": (0.36, 0.11, 0.28),
        "horizon_color": (1.15, 0.35, 0.07),
        "ground_color": (0.08, 0.05, 0.06),
        "cloud_shadow": (0.09, 0.07, 0.22),
        "cloud_mid": (0.38, 0.15, 0.24),
        "cloud_light": (1.30, 0.58, 0.16),
        "cloud_flatness": 0.55,
        "cloud_scale": 3.0,
        "cloud_rim_boost": 1.2,
        "cloud_amount": 0.65,
        "star_amount": 0.25,
        "star_density": 150.0,
        "contrails": 0.45,
        "sun_glow": 0.60,
        "sky_accent": (0.10, 0.42, 0.52),
        "sky_accent_amount": 0.22,
        "horizon_offset": 0.0,
        "horizon_softness": 0.52,
        "sun_color": (1.0, 0.48, 0.18),
        "sun_energy": 4.2,
        "sun_rotation": (1.28, 0.12, -0.55),
        "glare_tint": (1.0, 0.52, 0.22, 1.0),
        "shadow_tint": (0.26, 0.34, 0.92),
    },
    "AFTER_SCHOOL": {
        "world_color": (0.82, 0.42, 0.48),
        "world_strength": 0.9,
        "sky_color": (0.085, 0.095, 0.28),
        "mid_sky_color": (0.56, 0.20, 0.38),
        "horizon_color": (1.12, 0.46, 0.32),
        "ground_color": (0.10, 0.07, 0.12),
        "cloud_shadow": (0.12, 0.09, 0.22),
        "cloud_mid": (0.30, 0.16, 0.28),
        "cloud_light": (1.15, 0.55, 0.38),
        "cloud_flatness": 0.90,
        "cloud_scale": 4.0,
        "cloud_rim_boost": 2.0,
        "cloud_amount": 0.90,
        "star_amount": 0.15,
        "star_density": 140.0,
        "contrails": 0.30,
        "sun_glow": 0.55,
        "sky_accent": (0.28, 0.22, 0.48),
        "sky_accent_amount": 0.18,
        "horizon_offset": 0.02,
        "horizon_softness": 0.56,
        "sun_color": (1.0, 0.56, 0.38),
        "sun_energy": 3.8,
        "sun_rotation": (1.32, 0.10, -0.50),
        "glare_tint": (1.0, 0.58, 0.42, 1.0),
        "shadow_tint": (0.36, 0.40, 0.88),
    },
    "SUMMER_NOON": {
        "world_color": (0.32, 0.55, 0.95),
        "world_strength": 0.95,
        "sky_color": (0.015, 0.13, 0.68),
        "mid_sky_color": (0.09, 0.38, 0.88),
        "horizon_color": (0.48, 0.78, 0.98),
        "ground_color": (0.14, 0.22, 0.32),
        "cloud_shadow": (0.28, 0.40, 0.68),
        "cloud_mid": (0.90, 0.93, 0.96),
        "cloud_light": (1.20, 1.16, 1.05),
        "cloud_flatness": 0.25,
        "cloud_scale": 3.2,
        "cloud_rim_boost": 1.0,
        "cloud_amount": 0.70,
        "star_amount": 0.0,
        "star_density": 180.0,
        "contrails": 0.35,
        "sun_glow": 0.35,
        "sky_accent": (0.18, 0.62, 0.95),
        "sky_accent_amount": 0.15,
        "horizon_offset": -0.04,
        "horizon_softness": 0.48,
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
        "cloud_flatness": 0.65,
        "cloud_scale": 3.0,
        "cloud_rim_boost": 1.0,
        "cloud_amount": 0.60,
        "star_amount": 0.0,
        "star_density": 180.0,
        "contrails": 0.0,
        "sun_glow": 0.20,
        "sky_accent": (0.08, 0.18, 0.28),
        "sky_accent_amount": 0.15,
        "horizon_offset": -0.05,
        "horizon_softness": 0.65,
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
        "mid_sky_color": (0.14, 0.02, 0.26),
        "horizon_color": (0.78, 0.06, 0.42),
        "ground_color": (0.02, 0.01, 0.045),
        "cloud_shadow": (0.018, 0.015, 0.065),
        "cloud_mid": (0.16, 0.03, 0.22),
        "cloud_light": (0.22, 0.78, 0.98),
        "cloud_flatness": 0.75,
        "cloud_scale": 3.5,
        "cloud_rim_boost": 1.5,
        "cloud_amount": 0.65,
        "star_amount": 0.85,
        "star_density": 160.0,
        "contrails": 0.0,
        "sun_glow": 0.50,
        "sky_accent": (0.05, 0.72, 0.88),
        "sky_accent_amount": 0.28,
        "horizon_offset": 0.0,
        "horizon_softness": 0.48,
        "sun_color": (1.0, 0.16, 0.52),
        "sun_energy": 2.4,
        "sun_rotation": (1.05, -0.18, -0.75),
        "glare_tint": (1.0, 0.18, 0.58, 1.0),
        "shadow_tint": (0.42, 0.14, 0.92),
    },
    "SAKURA_SPRING": {
        "world_color": (0.72, 0.48, 0.58),
        "world_strength": 0.9,
        "sky_color": (0.045, 0.16, 0.64),
        "mid_sky_color": (0.38, 0.28, 0.62),
        "horizon_color": (0.96, 0.50, 0.58),
        "ground_color": (0.16, 0.14, 0.22),
        "cloud_shadow": (0.32, 0.26, 0.48),
        "cloud_mid": (0.86, 0.72, 0.78),
        "cloud_light": (1.15, 0.92, 0.88),
        "cloud_flatness": 0.50,
        "cloud_scale": 3.0,
        "cloud_rim_boost": 1.0,
        "cloud_amount": 0.55,
        "star_amount": 0.0,
        "star_density": 180.0,
        "contrails": 0.25,
        "sun_glow": 0.45,
        "sky_accent": (0.65, 0.42, 0.68),
        "sky_accent_amount": 0.20,
        "horizon_offset": 0.0,
        "horizon_softness": 0.55,
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
        "ground_color": (0.04, 0.025, 0.06),
        "cloud_shadow": (0.035, 0.03, 0.10),
        "cloud_mid": (0.28, 0.07, 0.16),
        "cloud_light": (1.15, 0.34, 0.09),
        "cloud_flatness": 0.75,
        "cloud_scale": 3.5,
        "cloud_rim_boost": 2.0,
        "cloud_amount": 0.65,
        "star_amount": 0.75,
        "star_density": 165.0,
        "contrails": 0.35,
        "sun_glow": 0.58,
        "sky_accent": (0.08, 0.35, 0.52),
        "sky_accent_amount": 0.30,
        "horizon_offset": -0.02,
        "horizon_softness": 0.50,
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
        # Cloud Shadow/Mid/Light stay exactly on the palette preset: custom
        # horizon and shadow colors must not repaint the clouds.
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
                           or ng.get("ald_build") != 18):
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GRADIENT_GROUP, "ShaderNodeTree")
        _build_gradient_group(ng)
        ng["ald_build"] = 18
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    types = {node.bl_idname for node in ng.nodes}
    if (not {"Sky Color", "Mid Sky Color", "Horizon Color", "Ground Color",
             "Horizon Offset", "Softness", "Sun Direction", "World Strength",
             "Sun Glow", "Sky Accent", "Sky Accent Amount", "Cloud Amount",
             "Cloud Flatness", "Contrails", "Cloud Delta Gain",
             "Cloud Rim Boost", "Star Amount", "Star Density",
             "Cloud Offset"} <= names
            or "ShaderNodeMix" not in types
            or "ShaderNodeValToRGB" in types):
        _build_gradient_group(ng)
        ng["ald_build"] = 18
    return ng


def _sample_cloud_density(nodes, links, ray_socket, group_in, flat_scale,
                          flat_inv, y_offset=0.0):
    """Sample the organic v1.0.0 fBm cloud density for a sky-dome ray."""
    def node(idname, x, y):
        item = nodes.new(idname)
        item.location = (x, y + y_offset)
        return item

    ray_sep = node("ShaderNodeSeparateXYZ", -1200, -200)
    links.new(ray_socket, ray_sep.inputs["Vector"])

    z_clamp = node("ShaderNodeMath", -1020, -200)
    z_clamp.operation = "MAXIMUM"
    z_clamp.inputs[1].default_value = 0.02
    links.new(ray_sep.outputs["Z"], z_clamp.inputs[0])

    z_denom = node("ShaderNodeMath", -840, -200)
    z_denom.operation = "ADD"
    z_denom.inputs[1].default_value = 0.18
    links.new(z_clamp.outputs[0], z_denom.inputs[0])

    inv_z = node("ShaderNodeMath", -660, -200)
    inv_z.operation = "DIVIDE"
    inv_z.inputs[0].default_value = 0.55
    links.new(z_denom.outputs[0], inv_z.inputs[1])

    planar_uv = node("ShaderNodeVectorMath", -480, -160)
    planar_uv.operation = "SCALE"
    links.new(ray_socket, planar_uv.inputs["Vector"])
    links.new(inv_z.outputs[0], planar_uv.inputs["Scale"])

    planar_sep = node("ShaderNodeSeparateXYZ", -300, -160)
    links.new(planar_uv.outputs["Vector"], planar_sep.inputs["Vector"])

    planar_shell = node("ShaderNodeCombineXYZ", -120, -220)
    links.new(planar_sep.outputs["X"], planar_shell.inputs["X"])
    links.new(planar_sep.outputs["Y"], planar_shell.inputs["Y"])
    links.new(ray_sep.outputs["Z"], planar_shell.inputs["Z"])

    view_base = node("ShaderNodeVectorMath", -120, -60)
    view_base.operation = "SCALE"
    links.new(ray_socket, view_base.inputs["Vector"])
    links.new(flat_inv.outputs[0], view_base.inputs["Scale"])

    planar_base = node("ShaderNodeVectorMath", -120, 80)
    planar_base.operation = "SCALE"
    links.new(planar_shell.outputs["Vector"], planar_base.inputs["Vector"])
    links.new(group_in.outputs["Cloud Flatness"], planar_base.inputs["Scale"])

    cloud_base = node("ShaderNodeVectorMath", 80, 0)
    cloud_base.operation = "ADD"
    links.new(view_base.outputs["Vector"], cloud_base.inputs[0])
    links.new(planar_base.outputs["Vector"], cloud_base.inputs[1])

    mapping = node("ShaderNodeMapping", 260, 0)
    links.new(cloud_base.outputs["Vector"], mapping.inputs["Vector"])
    links.new(flat_scale.outputs[0], mapping.inputs["Scale"])
    links.new(group_in.outputs["Cloud Offset"], mapping.inputs["Location"])

    warp_scale = node("ShaderNodeMath", 440, 200)
    warp_scale.operation = "MULTIPLY"
    warp_scale.inputs[1].default_value = 0.85
    links.new(group_in.outputs["Cloud Scale"], warp_scale.inputs[0])

    warp_noise = node("ShaderNodeTexNoise", 620, 200)
    warp_noise.inputs["Detail"].default_value = 4.0
    warp_noise.inputs["Roughness"].default_value = 0.55
    links.new(mapping.outputs["Vector"], warp_noise.inputs["Vector"])
    links.new(warp_scale.outputs[0], warp_noise.inputs["Scale"])

    warp_center = node("ShaderNodeVectorMath", 800, 200)
    warp_center.operation = "SUBTRACT"
    warp_center.inputs[1].default_value = (0.5, 0.5, 0.5)
    links.new(warp_noise.outputs["Color"], warp_center.inputs[0])

    warp_vec = node("ShaderNodeVectorMath", 980, 200)
    warp_vec.operation = "SCALE"
    links.new(warp_center.outputs["Vector"], warp_vec.inputs["Vector"])
    warp_vec.inputs["Scale"].default_value = 0.28

    warped_pos = node("ShaderNodeVectorMath", 1160, 120)
    warped_pos.operation = "ADD"
    links.new(mapping.outputs["Vector"], warped_pos.inputs[0])
    links.new(warp_vec.outputs["Vector"], warped_pos.inputs[1])

    macro_scale = node("ShaderNodeMath", 620, 420)
    macro_scale.operation = "MULTIPLY"
    macro_scale.inputs[1].default_value = 0.55
    links.new(group_in.outputs["Cloud Scale"], macro_scale.inputs[0])

    macro_noise = node("ShaderNodeTexNoise", 800, 420)
    macro_noise.inputs["Detail"].default_value = 6.0
    macro_noise.inputs["Roughness"].default_value = 0.58
    macro_noise.inputs["Distortion"].default_value = 0.18
    links.new(warped_pos.outputs["Vector"], macro_noise.inputs["Vector"])
    links.new(macro_scale.outputs[0], macro_noise.inputs["Scale"])

    macro_weight = node("ShaderNodeMath", 980, 420)
    macro_weight.operation = "MULTIPLY"
    macro_weight.inputs[1].default_value = 0.66
    links.new(macro_noise.outputs["Fac"], macro_weight.inputs[0])

    billow_scale = node("ShaderNodeMath", 620, 600)
    billow_scale.operation = "MULTIPLY"
    billow_scale.inputs[1].default_value = 1.35
    links.new(group_in.outputs["Cloud Scale"], billow_scale.inputs[0])

    billow_noise = node("ShaderNodeTexNoise", 800, 600)
    billow_noise.inputs["Detail"].default_value = 5.0
    billow_noise.inputs["Roughness"].default_value = 0.54
    billow_noise.inputs["Distortion"].default_value = 0.22
    links.new(warped_pos.outputs["Vector"], billow_noise.inputs["Vector"])
    links.new(billow_scale.outputs[0], billow_noise.inputs["Scale"])

    billow_weight = node("ShaderNodeMath", 980, 600)
    billow_weight.operation = "MULTIPLY"
    billow_weight.inputs[1].default_value = 0.22
    links.new(billow_noise.outputs["Fac"], billow_weight.inputs[0])

    puff_scale = node("ShaderNodeMath", 620, 780)
    puff_scale.operation = "MULTIPLY"
    puff_scale.inputs[1].default_value = 1.60
    links.new(group_in.outputs["Cloud Scale"], puff_scale.inputs[0])

    puff = node("ShaderNodeTexVoronoi", 800, 780)
    links.new(warped_pos.outputs["Vector"], puff.inputs["Vector"])
    links.new(puff_scale.outputs[0], puff.inputs["Scale"])

    puff_range = node("ShaderNodeMapRange", 980, 780)
    puff_range.clamp = True
    _smooth(puff_range)
    puff_range.inputs["From Min"].default_value = 0.0
    puff_range.inputs["From Max"].default_value = 0.65
    puff_range.inputs["To Min"].default_value = 1.0
    puff_range.inputs["To Max"].default_value = 0.0
    links.new(puff.outputs["Distance"], puff_range.inputs["Value"])

    puff_weight = node("ShaderNodeMath", 1160, 780)
    puff_weight.operation = "MULTIPLY"
    puff_weight.inputs[1].default_value = 0.12
    links.new(puff_range.outputs["Result"], puff_weight.inputs[0])

    macro_billow = node("ShaderNodeMath", 1160, 500)
    macro_billow.operation = "ADD"
    macro_billow.use_clamp = True
    links.new(macro_weight.outputs[0], macro_billow.inputs[0])
    links.new(billow_weight.outputs[0], macro_billow.inputs[1])

    rho = node("ShaderNodeMath", 1340, 620)
    rho.operation = "ADD"
    rho.use_clamp = True
    links.new(macro_billow.outputs[0], rho.inputs[0])
    links.new(puff_weight.outputs[0], rho.inputs[1])

    # Low-frequency envelope for the solar derivative. The silhouette above
    # stays pixel-identical to v1.0.2; this noise only drives body shading.
    envelope_noise = node("ShaderNodeTexNoise", 980, 1000)
    envelope_noise.inputs["Detail"].default_value = 2.0
    envelope_noise.inputs["Roughness"].default_value = 0.45
    envelope_noise.inputs["Distortion"].default_value = 0.15
    links.new(warped_pos.outputs["Vector"], envelope_noise.inputs["Vector"])
    links.new(macro_scale.outputs[0], envelope_noise.inputs["Scale"])

    return (rho.outputs[0], envelope_noise.outputs["Fac"],
            warped_pos.outputs["Vector"])


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
    sun_glow = ng.interface.new_socket(name="Sun Glow", in_out="INPUT",
                                       socket_type="NodeSocketFloat")
    sun_glow.min_value = 0.0
    sun_glow.max_value = 2.0
    sun_glow.default_value = 0.45
    sky_accent = ng.interface.new_socket(name="Sky Accent", in_out="INPUT",
                                         socket_type="NodeSocketColor")
    sky_accent.default_value = (0.05, 0.32, 0.42, 1.0)
    sky_accent_amount = ng.interface.new_socket(name="Sky Accent Amount",
                                                in_out="INPUT",
                                                socket_type="NodeSocketFloat")
    sky_accent_amount.min_value = 0.0
    sky_accent_amount.max_value = 1.0
    sky_accent_amount.default_value = 0.0
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
    cloud_flatness = ng.interface.new_socket(name="Cloud Flatness",
                                             in_out="INPUT",
                                             socket_type="NodeSocketFloat")
    cloud_flatness.min_value = 0.0
    cloud_flatness.max_value = 1.0
    cloud_flatness.default_value = 0.65
    contrails = ng.interface.new_socket(name="Contrails", in_out="INPUT",
                                        socket_type="NodeSocketFloat")
    contrails.min_value = 0.0
    contrails.max_value = 1.0
    contrails.default_value = 0.0
    delta_gain = ng.interface.new_socket(name="Cloud Delta Gain",
                                         in_out="INPUT",
                                         socket_type="NodeSocketFloat")
    delta_gain.min_value = 0.0
    delta_gain.max_value = 4.0
    delta_gain.default_value = 1.0
    rim_boost = ng.interface.new_socket(name="Cloud Rim Boost",
                                        in_out="INPUT",
                                        socket_type="NodeSocketFloat")
    rim_boost.min_value = 0.0
    rim_boost.max_value = 4.0
    rim_boost.default_value = 1.0
    star_amount = ng.interface.new_socket(name="Star Amount", in_out="INPUT",
                                          socket_type="NodeSocketFloat")
    star_amount.min_value = 0.0
    star_amount.max_value = 1.0
    star_amount.default_value = 0.0
    star_density = ng.interface.new_socket(name="Star Density", in_out="INPUT",
                                           socket_type="NodeSocketFloat")
    star_density.min_value = 50.0
    star_density.max_value = 400.0
    star_density.default_value = 180.0
    cloud_offset = ng.interface.new_socket(name="Cloud Offset", in_out="INPUT",
                                           socket_type="NodeSocketVector")
    cloud_offset.default_value = (0.0, 0.0, 0.0)

    ng.interface.new_socket(name="Color", in_out="OUTPUT",
                            socket_type="NodeSocketColor")

    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1200, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (2900, 0)

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

    # mu_s = L.z, used to fade the narrow solar corona below the horizon.
    sun_mu = nodes.new("ShaderNodeSeparateXYZ")
    sun_mu.location = (-820, 600)
    links.new(sun_norm.outputs["Vector"], sun_mu.inputs["Vector"])

    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-1000, 280)
    links.new(view_norm.outputs["Vector"], separate.inputs["Vector"])

    # Ground stays strictly below the horizon (Z <= 0); Horizon Offset shifts
    # how high the horizon & mid-sky glow reach into the upper sky dome.
    ground_blend = nodes.new("ShaderNodeMapRange")
    ground_blend.location = (-800, 340)
    ground_blend.clamp = True
    _smooth(ground_blend)
    ground_blend.inputs["From Min"].default_value = -0.08
    ground_blend.inputs["From Max"].default_value = 0.01
    links.new(separate.outputs["Z"], ground_blend.inputs["Value"])

    # Sky dome height (0 at horizon Z=0, 1 at zenith Z=1).
    sky_z = nodes.new("ShaderNodeMapRange")
    sky_z.location = (-800, 140)
    sky_z.clamp = True
    sky_z.inputs["From Min"].default_value = 0.0
    sky_z.inputs["From Max"].default_value = 1.0
    links.new(separate.outputs["Z"], sky_z.inputs["Value"])

    # Horizon Offset (-0.9..0.9) controls the altitude of the Mid-Sky bridge
    # between 0.08 and 0.45 without ever pulling Ground Color into Z > 0.
    offset_scaled = nodes.new("ShaderNodeMath")
    offset_scaled.location = (-620, 100)
    offset_scaled.operation = "MULTIPLY"
    offset_scaled.inputs[1].default_value = 0.16
    links.new(group_in.outputs["Horizon Offset"], offset_scaled.inputs[0])

    mid_peak = nodes.new("ShaderNodeMath")
    mid_peak.location = (-440, 100)
    mid_peak.operation = "ADD"
    mid_peak.use_clamp = True
    mid_peak.inputs[1].default_value = 0.22
    links.new(offset_scaled.outputs[0], mid_peak.inputs[0])

    mid_low = nodes.new("ShaderNodeMath")
    mid_low.location = (-260, 100)
    mid_low.operation = "MAXIMUM"
    mid_low.inputs[1].default_value = 0.05
    links.new(mid_peak.outputs[0], mid_low.inputs[0])

    mid_clamped = nodes.new("ShaderNodeMath")
    mid_clamped.location = (-80, 100)
    mid_clamped.operation = "MINIMUM"
    mid_clamped.inputs[1].default_value = 0.65
    links.new(mid_low.outputs[0], mid_clamped.inputs[0])

    soft_span = nodes.new("ShaderNodeMath")
    soft_span.location = (-620, -60)
    soft_span.operation = "MULTIPLY"
    soft_span.inputs[1].default_value = 0.55
    links.new(group_in.outputs["Softness"], soft_span.inputs[0])

    soft_min = nodes.new("ShaderNodeMath")
    soft_min.location = (-440, -60)
    soft_min.operation = "MAXIMUM"
    soft_min.inputs[1].default_value = 0.05
    links.new(soft_span.outputs[0], soft_min.inputs[0])

    zenith_start = nodes.new("ShaderNodeMath")
    zenith_start.location = (-260, -60)
    zenith_start.operation = "ADD"
    zenith_start.use_clamp = True
    links.new(mid_clamped.outputs[0], zenith_start.inputs[0])
    links.new(soft_min.outputs[0], zenith_start.inputs[1])

    zenith_clamped = nodes.new("ShaderNodeMath")
    zenith_clamped.location = (-80, -60)
    zenith_clamped.operation = "MINIMUM"
    zenith_clamped.inputs[1].default_value = 1.0
    links.new(zenith_start.outputs[0], zenith_clamped.inputs[0])

    mid = nodes.new("ShaderNodeMapRange")
    mid.location = (-160, 120)
    mid.clamp = True
    _smooth(mid)
    mid.inputs["From Min"].default_value = 0.0
    links.new(sky_z.outputs["Result"], mid.inputs["Value"])
    links.new(mid_clamped.outputs[0], mid.inputs["From Max"])

    high = nodes.new("ShaderNodeMapRange")
    high.location = (-160, -80)
    high.clamp = True
    _smooth(high)
    links.new(sky_z.outputs["Result"], high.inputs["Value"])
    links.new(mid_clamped.outputs[0], high.inputs["From Min"])
    links.new(zenith_clamped.outputs[0], high.inputs["From Max"])

    mix_ground = nodes.new("ShaderNodeMix")
    mix_ground.location = (120, 200)
    mix_ground.data_type = "RGBA"
    mix_ground.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_ground)
    links.new(group_in.outputs["Ground Color"], a_sock)
    links.new(group_in.outputs["Horizon Color"], b_sock)
    links.new(ground_blend.outputs["Result"], mix_ground.inputs["Factor"])

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

    accent_delta = nodes.new("ShaderNodeMath")
    accent_delta.location = (620, 80)
    accent_delta.operation = "SUBTRACT"
    links.new(sky_z.outputs["Result"], accent_delta.inputs[0])
    links.new(mid_clamped.outputs[0], accent_delta.inputs[1])

    accent_abs = nodes.new("ShaderNodeMath")
    accent_abs.location = (800, 80)
    accent_abs.operation = "ABSOLUTE"
    links.new(accent_delta.outputs[0], accent_abs.inputs[0])

    accent_band = nodes.new("ShaderNodeMapRange")
    accent_band.location = (980, 80)
    accent_band.clamp = True
    _smooth(accent_band)
    accent_band.inputs["From Min"].default_value = 0.0
    accent_band.inputs["From Max"].default_value = 0.07
    accent_band.inputs["To Min"].default_value = 1.0
    accent_band.inputs["To Max"].default_value = 0.0
    links.new(accent_abs.outputs[0], accent_band.inputs["Value"])

    accent_factor = nodes.new("ShaderNodeMath")
    accent_factor.location = (1160, 80)
    accent_factor.operation = "MULTIPLY"
    accent_factor.use_clamp = True
    links.new(accent_band.outputs["Result"], accent_factor.inputs[0])
    links.new(group_in.outputs["Sky Accent Amount"],
              accent_factor.inputs[1])

    accent_mix = nodes.new("ShaderNodeMix")
    accent_mix.location = (1340, 60)
    accent_mix.data_type = "RGBA"
    accent_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(accent_mix)
    links.new(mix_sky.outputs["Result"], a_sock)
    links.new(group_in.outputs["Sky Accent"], b_sock)
    links.new(accent_factor.outputs[0], accent_mix.inputs["Factor"])

    sky_color = accent_mix.outputs["Result"]

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

    # Mie-style anisotropic sun glow: a wide forward-scattering lobe that
    # warms the horizon toward the sun while leaving the opposite side cool.
    gamma_plus = nodes.new("ShaderNodeMath")
    gamma_plus.location = (1420, 400)
    gamma_plus.operation = "MAXIMUM"
    gamma_plus.use_clamp = True
    gamma_plus.inputs[1].default_value = 0.0
    links.new(dot.outputs["Value"], gamma_plus.inputs[0])

    glow_power = nodes.new("ShaderNodeMath")
    glow_power.location = (1600, 400)
    glow_power.operation = "POWER"
    glow_power.inputs[1].default_value = 3.5
    links.new(gamma_plus.outputs[0], glow_power.inputs[0])

    abs_z = nodes.new("ShaderNodeMath")
    abs_z.location = (1420, 240)
    abs_z.operation = "ABSOLUTE"
    links.new(separate.outputs["Z"], abs_z.inputs[0])

    horizon_glow = nodes.new("ShaderNodeMapRange")
    horizon_glow.location = (1600, 240)
    horizon_glow.clamp = True
    _smooth(horizon_glow)
    horizon_glow.inputs["From Min"].default_value = 0.75
    horizon_glow.inputs["From Max"].default_value = 0.0
    horizon_glow.inputs["To Min"].default_value = 0.0
    horizon_glow.inputs["To Max"].default_value = 1.0
    links.new(abs_z.outputs[0], horizon_glow.inputs["Value"])

    glow_amount = nodes.new("ShaderNodeMath")
    glow_amount.location = (1780, 320)
    glow_amount.operation = "MULTIPLY"
    glow_amount.use_clamp = True
    links.new(glow_power.outputs[0], glow_amount.inputs[0])
    links.new(horizon_glow.outputs["Result"], glow_amount.inputs[1])

    # Narrow solar corona: gamma+^16 * 0.65, distinct from the wide lobe.
    core_power = nodes.new("ShaderNodeMath")
    core_power.location = (1600, 560)
    core_power.operation = "POWER"
    core_power.inputs[1].default_value = 16.0
    links.new(gamma_plus.outputs[0], core_power.inputs[0])

    core_amount = nodes.new("ShaderNodeMath")
    core_amount.location = (1780, 560)
    core_amount.operation = "MULTIPLY"
    core_amount.inputs[1].default_value = 0.65
    links.new(core_power.outputs[0], core_amount.inputs[0])

    sun_core_gate = nodes.new("ShaderNodeMapRange")
    sun_core_gate.location = (1600, 680)
    sun_core_gate.clamp = True
    _smooth(sun_core_gate)
    sun_core_gate.inputs["From Min"].default_value = -0.08
    sun_core_gate.inputs["From Max"].default_value = 0.08
    sun_core_gate.inputs["To Min"].default_value = 0.0
    sun_core_gate.inputs["To Max"].default_value = 1.0
    links.new(sun_mu.outputs["Z"], sun_core_gate.inputs["Value"])

    core_gated = nodes.new("ShaderNodeMath")
    core_gated.location = (1960, 560)
    core_gated.operation = "MULTIPLY"
    links.new(core_amount.outputs[0], core_gated.inputs[0])
    links.new(sun_core_gate.outputs["Result"], core_gated.inputs[1])

    wide_amount = nodes.new("ShaderNodeMath")
    wide_amount.location = (1960, 320)
    wide_amount.operation = "MULTIPLY"
    wide_amount.inputs[1].default_value = 0.45
    links.new(glow_amount.outputs[0], wide_amount.inputs[0])

    glow_total = nodes.new("ShaderNodeMath")
    glow_total.location = (2140, 440)
    glow_total.operation = "ADD"
    links.new(core_gated.outputs[0], glow_total.inputs[0])
    links.new(wide_amount.outputs[0], glow_total.inputs[1])

    glow_gain = nodes.new("ShaderNodeMath")
    glow_gain.location = (2140, 600)
    glow_gain.operation = "DIVIDE"
    glow_gain.inputs[1].default_value = 0.45
    links.new(group_in.outputs["Sun Glow"], glow_gain.inputs[0])

    glow_scale = nodes.new("ShaderNodeMath")
    glow_scale.location = (2320, 440)
    glow_scale.operation = "MULTIPLY"
    glow_scale.use_clamp = True
    links.new(glow_total.outputs[0], glow_scale.inputs[0])
    links.new(glow_gain.outputs[0], glow_scale.inputs[1])

    glow_color = nodes.new("ShaderNodeVectorMath")
    glow_color.location = (2500, 320)
    glow_color.operation = "SCALE"
    links.new(group_in.outputs["Sun Color"], glow_color.inputs["Vector"])
    links.new(glow_scale.outputs[0], glow_color.inputs["Scale"])

    glow_add = nodes.new("ShaderNodeMix")
    glow_add.location = (2320, 260)
    glow_add.data_type = "RGBA"
    glow_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(glow_add)
    links.new(sky_color, a_sock)
    links.new(glow_color.outputs["Vector"], b_sock)
    glow_add.inputs["Factor"].default_value = 1.0
    sky_color = result_sock

    # Perspective planar cloud projection: projects view ray onto a curved
    # horizontal cloud deck so clouds stretch into horizontal bands near the
    # horizon (anime background style).
    z_clamp = nodes.new("ShaderNodeMath")
    z_clamp.location = (680, -140)
    z_clamp.operation = "MAXIMUM"
    z_clamp.inputs[1].default_value = 0.015
    links.new(separate.outputs["Z"], z_clamp.inputs[0])

    z_denom = nodes.new("ShaderNodeMath")
    z_denom.location = (840, -140)
    z_denom.operation = "ADD"
    z_denom.inputs[1].default_value = 0.18
    links.new(z_clamp.outputs[0], z_denom.inputs[0])

    inv_z = nodes.new("ShaderNodeMath")
    inv_z.location = (840, -300)
    inv_z.operation = "DIVIDE"
    inv_z.inputs[0].default_value = 0.55
    links.new(z_denom.outputs[0], inv_z.inputs[1])

    planar_uv = nodes.new("ShaderNodeVectorMath")
    planar_uv.location = (1000, -140)
    planar_uv.operation = "SCALE"
    links.new(view_norm.outputs["Vector"], planar_uv.inputs["Vector"])
    links.new(inv_z.outputs[0], planar_uv.inputs["Scale"])

    # Exact curved-shell point: (Vx*t, Vy*t, Vz), then the Mapping scales
    # X/Y by 0.75 and Z by the Cloud Flatness value.
    planar_sep = nodes.new("ShaderNodeSeparateXYZ")
    planar_sep.location = (1180, -100)
    links.new(planar_uv.outputs["Vector"], planar_sep.inputs["Vector"])

    planar_shell = nodes.new("ShaderNodeCombineXYZ")
    planar_shell.location = (1360, -100)
    links.new(planar_sep.outputs["X"], planar_shell.inputs["X"])
    links.new(planar_sep.outputs["Y"], planar_shell.inputs["Y"])
    links.new(separate.outputs["Z"], planar_shell.inputs["Z"])

    # Cloud Flatness: 0 = billowy cumuli, 0.65 = current strata,
    # 1 = strongly flat horizontal bands. At 0.65 this is exactly 3.2.
    flat_z = nodes.new("ShaderNodeMath")
    flat_z.location = (1000, -360)
    flat_z.operation = "MULTIPLY"
    flat_z.inputs[1].default_value = 3.0
    links.new(group_in.outputs["Cloud Flatness"], flat_z.inputs[0])

    flat_z_add = nodes.new("ShaderNodeMath")
    flat_z_add.location = (1180, -360)
    flat_z_add.operation = "ADD"
    flat_z_add.inputs[1].default_value = 1.25
    links.new(flat_z.outputs[0], flat_z_add.inputs[0])

    flat_scale = nodes.new("ShaderNodeCombineXYZ")
    flat_scale.location = (1360, -360)
    flat_scale.inputs["X"].default_value = 0.75
    flat_scale.inputs["Y"].default_value = 0.75
    links.new(flat_z_add.outputs[0], flat_scale.inputs["Z"])

    # Blend the raw spherical view (billowy cumuli) and the curved planar
    # shell (horizontal strata) with the same Cloud Flatness control.
    flat_inv = nodes.new("ShaderNodeMath")
    flat_inv.location = (1540, -280)
    flat_inv.operation = "SUBTRACT"
    flat_inv.use_clamp = True
    flat_inv.inputs[0].default_value = 1.0
    links.new(group_in.outputs["Cloud Flatness"], flat_inv.inputs[1])

    # Optional contrails: straight gnomonic-plane filaments. Use X/Z and Y/Z
    # (not the curved shell projection) so a constant-u line stays straight.
    trail_z = nodes.new("ShaderNodeMath")
    trail_z.location = (2260, 1080)
    trail_z.operation = "MAXIMUM"
    trail_z.inputs[1].default_value = 0.05
    links.new(separate.outputs["Z"], trail_z.inputs[0])

    trail_x = nodes.new("ShaderNodeMath")
    trail_x.location = (2440, 1080)
    trail_x.operation = "DIVIDE"
    links.new(separate.outputs["X"], trail_x.inputs[0])
    links.new(trail_z.outputs[0], trail_x.inputs[1])

    trail_y = nodes.new("ShaderNodeMath")
    trail_y.location = (2440, 1180)
    trail_y.operation = "DIVIDE"
    links.new(separate.outputs["Y"], trail_y.inputs[0])
    links.new(trail_z.outputs[0], trail_y.inputs[1])

    contrail_noise = nodes.new("ShaderNodeTexNoise")
    contrail_noise.location = (2260, 900)
    contrail_noise.inputs["Scale"].default_value = 4.0
    contrail_noise.inputs["Detail"].default_value = 3.0
    contrail_noise.inputs["Roughness"].default_value = 0.50
    contrail_noise.inputs["Distortion"].default_value = 0.10
    links.new(planar_shell.outputs["Vector"], contrail_noise.inputs["Vector"])

    trail_u_x = nodes.new("ShaderNodeMath")
    trail_u_x.location = (2440, 960)
    trail_u_x.operation = "MULTIPLY"
    trail_u_x.inputs[1].default_value = 0.82
    links.new(trail_x.outputs[0], trail_u_x.inputs[0])

    trail_u_y = nodes.new("ShaderNodeMath")
    trail_u_y.location = (2620, 1080)
    trail_u_y.operation = "MULTIPLY"
    trail_u_y.inputs[1].default_value = 0.57
    links.new(trail_y.outputs[0], trail_u_y.inputs[0])

    trail_u_sum = nodes.new("ShaderNodeMath")
    trail_u_sum.location = (2620, 1020)
    trail_u_sum.operation = "ADD"
    links.new(trail_u_x.outputs[0], trail_u_sum.inputs[0])
    links.new(trail_u_y.outputs[0], trail_u_sum.inputs[1])

    trail_wave = nodes.new("ShaderNodeMath")
    trail_wave.location = (2620, 900)
    trail_wave.operation = "MULTIPLY"
    trail_wave.inputs[1].default_value = 0.06
    links.new(contrail_noise.outputs["Fac"], trail_wave.inputs[0])

    trail_u = nodes.new("ShaderNodeMath")
    trail_u.location = (2800, 960)
    trail_u.operation = "ADD"
    links.new(trail_u_sum.outputs[0], trail_u.inputs[0])
    links.new(trail_wave.outputs[0], trail_u.inputs[1])

    trail_u_center = nodes.new("ShaderNodeMath")
    trail_u_center.location = (2980, 960)
    trail_u_center.operation = "SUBTRACT"
    trail_u_center.inputs[1].default_value = 0.15
    links.new(trail_u.outputs[0], trail_u_center.inputs[0])

    trail_u_abs = nodes.new("ShaderNodeMath")
    trail_u_abs.location = (3160, 960)
    trail_u_abs.operation = "ABSOLUTE"
    links.new(trail_u_center.outputs[0], trail_u_abs.inputs[0])

    contrail_band = nodes.new("ShaderNodeMapRange")
    contrail_band.location = (3340, 960)
    contrail_band.clamp = True
    _smooth(contrail_band)
    contrail_band.inputs["From Min"].default_value = 0.0
    contrail_band.inputs["From Max"].default_value = 0.012
    contrail_band.inputs["To Min"].default_value = 1.0
    contrail_band.inputs["To Max"].default_value = 0.0
    links.new(trail_u_abs.outputs[0], contrail_band.inputs["Value"])

    trail_v_x = nodes.new("ShaderNodeMath")
    trail_v_x.location = (2440, 1160)
    trail_v_x.operation = "MULTIPLY"
    trail_v_x.inputs[1].default_value = -0.57
    links.new(trail_x.outputs[0], trail_v_x.inputs[0])

    trail_v_y = nodes.new("ShaderNodeMath")
    trail_v_y.location = (2620, 1280)
    trail_v_y.operation = "MULTIPLY"
    trail_v_y.inputs[1].default_value = 0.82
    links.new(trail_y.outputs[0], trail_v_y.inputs[0])

    trail_v = nodes.new("ShaderNodeMath")
    trail_v.location = (2620, 1220)
    trail_v.operation = "ADD"
    links.new(trail_v_x.outputs[0], trail_v.inputs[0])
    links.new(trail_v_y.outputs[0], trail_v.inputs[1])

    trail_len_a = nodes.new("ShaderNodeMapRange")
    trail_len_a.location = (2800, 1180)
    trail_len_a.clamp = True
    _smooth(trail_len_a)
    trail_len_a.inputs["From Min"].default_value = -1.2
    trail_len_a.inputs["From Max"].default_value = 0.2
    trail_len_a.inputs["To Min"].default_value = 0.0
    trail_len_a.inputs["To Max"].default_value = 1.0
    links.new(trail_v.outputs[0], trail_len_a.inputs["Value"])

    trail_len_b = nodes.new("ShaderNodeMapRange")
    trail_len_b.location = (2800, 1300)
    trail_len_b.clamp = True
    _smooth(trail_len_b)
    trail_len_b.inputs["From Min"].default_value = 1.8
    trail_len_b.inputs["From Max"].default_value = 0.4
    trail_len_b.inputs["To Min"].default_value = 0.0
    trail_len_b.inputs["To Max"].default_value = 1.0
    links.new(trail_v.outputs[0], trail_len_b.inputs["Value"])

    trail_len = nodes.new("ShaderNodeMath")
    trail_len.location = (2980, 1240)
    trail_len.operation = "MULTIPLY"
    trail_len.use_clamp = True
    links.new(trail_len_a.outputs["Result"], trail_len.inputs[0])
    links.new(trail_len_b.outputs["Result"], trail_len.inputs[1])

    contrail_alt = nodes.new("ShaderNodeMapRange")
    contrail_alt.location = (3160, 1120)
    contrail_alt.clamp = True
    _smooth(contrail_alt)
    contrail_alt.inputs["From Min"].default_value = 0.08
    contrail_alt.inputs["From Max"].default_value = 0.45
    contrail_alt.inputs["To Min"].default_value = 0.0
    contrail_alt.inputs["To Max"].default_value = 1.0
    links.new(separate.outputs["Z"], contrail_alt.inputs["Value"])

    contrail_mask = nodes.new("ShaderNodeMath")
    contrail_mask.location = (3340, 1120)
    contrail_mask.operation = "MULTIPLY"
    contrail_mask.use_clamp = True
    links.new(contrail_band.outputs["Result"], contrail_mask.inputs[0])
    links.new(trail_len.outputs[0], contrail_mask.inputs[1])

    contrail_mask_alt = nodes.new("ShaderNodeMath")
    contrail_mask_alt.location = (3520, 1120)
    contrail_mask_alt.operation = "MULTIPLY"
    contrail_mask_alt.use_clamp = True
    links.new(contrail_mask.outputs[0], contrail_mask_alt.inputs[0])
    links.new(contrail_alt.outputs["Result"], contrail_mask_alt.inputs[1])

    contrail_amount = nodes.new("ShaderNodeMath")
    contrail_amount.location = (3700, 1120)
    contrail_amount.operation = "MULTIPLY"
    contrail_amount.use_clamp = True
    links.new(contrail_mask_alt.outputs[0], contrail_amount.inputs[0])
    links.new(group_in.outputs["Contrails"], contrail_amount.inputs[1])

    contrail_factor = nodes.new("ShaderNodeMath")
    contrail_factor.location = (3880, 1120)
    contrail_factor.operation = "MULTIPLY"
    contrail_factor.use_clamp = True
    contrail_factor.inputs[1].default_value = 0.18
    links.new(contrail_amount.outputs[0], contrail_factor.inputs[0])

    contrail_color = nodes.new("ShaderNodeRGB")
    contrail_color.location = (3880, 960)
    contrail_color.outputs[0].default_value = (1.8, 1.9, 2.1, 1.0)

    contrail_add = nodes.new("ShaderNodeMix")
    contrail_add.location = (4060, 1000)
    contrail_add.data_type = "RGBA"
    contrail_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(contrail_add)
    links.new(sky_color, a_sock)
    links.new(contrail_color.outputs[0], b_sock)
    links.new(contrail_factor.outputs[0], contrail_add.inputs["Factor"])
    sky_color = result_sock

    rho_here, env_here, warped_pos = _sample_cloud_density(
        nodes, links, view_norm.outputs["Vector"], group_in,
        flat_scale, flat_inv, y_offset=0.0)

    # Displace the *view ray* by ~2 degrees on the sky dome, not the mapped
    # cloud point. Sun+zenith defines the per-cloud light direction.
    light_up = nodes.new("ShaderNodeVectorMath")
    light_up.location = (1540, -720)
    light_up.operation = "ADD"
    links.new(sun_norm.outputs["Vector"], light_up.inputs[0])
    light_up.inputs[1].default_value = (0.0, 0.0, 0.65)

    light_dir = nodes.new("ShaderNodeVectorMath")
    light_dir.location = (1720, -720)
    light_dir.operation = "NORMALIZE"
    links.new(light_up.outputs["Vector"], light_dir.inputs[0])

    sun_ray_step = nodes.new("ShaderNodeVectorMath")
    sun_ray_step.location = (1900, -720)
    sun_ray_step.operation = "SCALE"
    links.new(light_dir.outputs["Vector"], sun_ray_step.inputs["Vector"])
    sun_ray_step.inputs["Scale"].default_value = 0.055

    view_sun_raw = nodes.new("ShaderNodeVectorMath")
    view_sun_raw.location = (2080, -720)
    view_sun_raw.operation = "ADD"
    links.new(view_norm.outputs["Vector"], view_sun_raw.inputs[0])
    links.new(sun_ray_step.outputs["Vector"], view_sun_raw.inputs[1])

    view_sun_norm = nodes.new("ShaderNodeVectorMath")
    view_sun_norm.location = (2260, -720)
    view_sun_norm.operation = "NORMALIZE"
    links.new(view_sun_raw.outputs["Vector"], view_sun_norm.inputs[0])

    rho_sun, env_sun, _warped_sun = _sample_cloud_density(
        nodes, links, view_sun_norm.outputs["Vector"], group_in,
        flat_scale, flat_inv, y_offset=-1200.0)

    delta = nodes.new("ShaderNodeMath")
    delta.location = (2440, -900)
    delta.operation = "SUBTRACT"
    links.new(env_here, delta.inputs[0])
    links.new(env_sun, delta.inputs[1])

    delta_used = nodes.new("ShaderNodeMath")
    delta_used.location = (2620, -900)
    delta_used.operation = "MULTIPLY"
    links.new(delta.outputs[0], delta_used.inputs[0])
    links.new(group_in.outputs["Cloud Delta Gain"], delta_used.inputs[1])

    detail_scale = nodes.new("ShaderNodeMath")
    detail_scale.location = (2440, -1140)
    detail_scale.operation = "MULTIPLY"
    detail_scale.inputs[1].default_value = 3.0
    links.new(group_in.outputs["Cloud Scale"], detail_scale.inputs[0])

    detail = nodes.new("ShaderNodeTexNoise")
    detail.location = (2620, -1140)
    detail.inputs["Detail"].default_value = 5.0
    detail.inputs["Roughness"].default_value = 0.60
    links.new(warped_pos, detail.inputs["Vector"])
    links.new(detail_scale.outputs[0], detail.inputs["Scale"])

    detail_center = nodes.new("ShaderNodeMath")
    detail_center.location = (2800, -1140)
    detail_center.operation = "SUBTRACT"
    detail_center.inputs[1].default_value = 0.5
    links.new(detail.outputs["Fac"], detail_center.inputs[0])

    detail_edge = nodes.new("ShaderNodeMath")
    detail_edge.location = (2980, -1140)
    detail_edge.operation = "MULTIPLY"
    detail_edge.inputs[1].default_value = 0.018
    links.new(detail_center.outputs[0], detail_edge.inputs[0])

    detail_body = nodes.new("ShaderNodeMath")
    detail_body.location = (2980, -1260)
    detail_body.operation = "MULTIPLY"
    detail_body.inputs[1].default_value = 0.010
    links.new(detail_center.outputs[0], detail_body.inputs[0])

    rho_sculpted = nodes.new("ShaderNodeMath")
    rho_sculpted.location = (3160, -1080)
    rho_sculpted.operation = "ADD"
    rho_sculpted.use_clamp = True
    links.new(rho_here, rho_sculpted.inputs[0])
    links.new(detail_edge.outputs[0], rho_sculpted.inputs[1])

    body_signal = nodes.new("ShaderNodeMath")
    body_signal.location = (3160, -900)
    body_signal.operation = "ADD"
    links.new(delta_used.outputs[0], body_signal.inputs[0])
    links.new(detail_body.outputs[0], body_signal.inputs[1])
    # Cloud Amount is coverage, not opacity: 0 -> few compact islands,
    # 1 -> sky-filling banks. tau0 maps 0.68..0.42.
    coverage_center = nodes.new("ShaderNodeMapRange")
    coverage_center.location = (2440, -220)
    coverage_center.clamp = True
    coverage_center.inputs["From Min"].default_value = 0.0
    coverage_center.inputs["From Max"].default_value = 1.0
    coverage_center.inputs["To Min"].default_value = 0.58
    coverage_center.inputs["To Max"].default_value = 0.40
    links.new(group_in.outputs["Cloud Amount"],
              coverage_center.inputs["Value"])

    coverage_top = nodes.new("ShaderNodeMath")
    coverage_top.location = (2620, -220)
    coverage_top.operation = "ADD"
    coverage_top.inputs[1].default_value = 0.018
    links.new(coverage_center.outputs["Result"], coverage_top.inputs[0])

    fringe_top = nodes.new("ShaderNodeMath")
    fringe_top.location = (2620, -380)
    fringe_top.operation = "ADD"
    fringe_top.inputs[1].default_value = 0.022
    links.new(coverage_center.outputs["Result"], fringe_top.inputs[0])

    # Crisp anime silhouette + directional body / silver lining.
    coverage = nodes.new("ShaderNodeMapRange")
    coverage.location = (2800, -300)
    coverage.clamp = True
    _smooth(coverage)
    links.new(coverage_center.outputs["Result"], coverage.inputs["From Min"])
    links.new(coverage_top.outputs[0], coverage.inputs["From Max"])
    links.new(rho_sculpted.outputs[0], coverage.inputs["Value"])

    amount_gate = nodes.new("ShaderNodeMapRange")
    amount_gate.location = (2440, -80)
    amount_gate.clamp = True
    _smooth(amount_gate)
    amount_gate.inputs["From Min"].default_value = 0.0
    amount_gate.inputs["From Max"].default_value = 0.03
    amount_gate.inputs["To Min"].default_value = 0.0
    amount_gate.inputs["To Max"].default_value = 1.0
    links.new(group_in.outputs["Cloud Amount"],
              amount_gate.inputs["Value"])

    coverage_gate = nodes.new("ShaderNodeMath")
    coverage_gate.location = (2980, -300)
    coverage_gate.operation = "MULTIPLY"
    coverage_gate.use_clamp = True
    links.new(coverage.outputs["Result"], coverage_gate.inputs[0])
    links.new(amount_gate.outputs["Result"], coverage_gate.inputs[1])

    body_mix = nodes.new("ShaderNodeMapRange")
    body_mix.location = (2620, -720)
    body_mix.clamp = True
    _smooth(body_mix)
    body_mix.inputs["From Min"].default_value = -0.022
    body_mix.inputs["From Max"].default_value = 0.006
    body_mix.inputs["To Min"].default_value = 0.0
    body_mix.inputs["To Max"].default_value = 1.0
    links.new(body_signal.outputs[0], body_mix.inputs["Value"])

    fringe = nodes.new("ShaderNodeMapRange")
    fringe.location = (2440, -540)
    fringe.clamp = True
    _smooth(fringe)
    fringe.inputs["To Min"].default_value = 1.0
    fringe.inputs["To Max"].default_value = 0.0
    links.new(coverage_center.outputs["Result"], fringe.inputs["From Min"])
    links.new(fringe_top.outputs[0], fringe.inputs["From Max"])
    links.new(rho_sculpted.outputs[0], fringe.inputs["Value"])

    sun_edge = nodes.new("ShaderNodeMapRange")
    sun_edge.location = (2440, -900)
    sun_edge.clamp = True
    _smooth(sun_edge)
    sun_edge.inputs["From Min"].default_value = 0.000
    sun_edge.inputs["From Max"].default_value = 0.022
    sun_edge.inputs["To Min"].default_value = 0.0
    sun_edge.inputs["To Max"].default_value = 1.0
    links.new(delta_used.outputs[0], sun_edge.inputs["Value"])

    fringe_sharp = nodes.new("ShaderNodeMath")
    fringe_sharp.location = (2620, -540)
    fringe_sharp.operation = "POWER"
    fringe_sharp.inputs[1].default_value = 2.0
    links.new(fringe.outputs["Result"], fringe_sharp.inputs[0])

    fringe_weight = nodes.new("ShaderNodeMath")
    fringe_weight.location = (2800, -540)
    fringe_weight.operation = "MULTIPLY"
    fringe_weight.inputs[1].default_value = 0.95
    links.new(fringe_sharp.outputs[0], fringe_weight.inputs[0])

    fringe_add = nodes.new("ShaderNodeMath")
    fringe_add.location = (2980, -540)
    fringe_add.operation = "ADD"
    # No body base at all: Cloud Light is strictly the sun-facing fringe.
    # The old 0.35 (then 0.08) still washed the opaque body toward beige.
    fringe_add.inputs[1].default_value = 0.0
    links.new(fringe_weight.outputs[0], fringe_add.inputs[0])

    gamma_sq = nodes.new("ShaderNodeMath")
    gamma_sq.location = (2440, -1040)
    gamma_sq.operation = "POWER"
    gamma_sq.inputs[1].default_value = 2.0
    links.new(gamma_plus.outputs[0], gamma_sq.inputs[0])

    gamma_weight = nodes.new("ShaderNodeMath")
    gamma_weight.location = (2620, -1040)
    gamma_weight.operation = "MULTIPLY"
    gamma_weight.inputs[1].default_value = 0.55
    links.new(gamma_sq.outputs[0], gamma_weight.inputs[0])

    gamma_add = nodes.new("ShaderNodeMath")
    gamma_add.location = (2800, -1040)
    gamma_add.operation = "ADD"
    gamma_add.inputs[1].default_value = 0.45
    links.new(gamma_weight.outputs[0], gamma_add.inputs[0])

    rim_edge = nodes.new("ShaderNodeMath")
    rim_edge.location = (2980, -900)
    rim_edge.operation = "MULTIPLY"
    rim_edge.use_clamp = True
    links.new(fringe_add.outputs[0], rim_edge.inputs[0])
    links.new(sun_edge.outputs["Result"], rim_edge.inputs[1])

    rim_factor = nodes.new("ShaderNodeMath")
    rim_factor.location = (3160, -900)
    rim_factor.operation = "MULTIPLY"
    rim_factor.use_clamp = True
    links.new(rim_edge.outputs[0], rim_factor.inputs[0])
    links.new(gamma_add.outputs[0], rim_factor.inputs[1])

    # The silver lining must occur only where the cloud exists. This presence
    # gate suppresses rims around low-density holes while keeping the outer
    # silhouette edge, where coverage is about 0.5.
    rim_presence = nodes.new("ShaderNodeMath")
    rim_presence.location = (3160, -760)
    rim_presence.operation = "MULTIPLY"
    rim_presence.use_clamp = True
    rim_presence.inputs[1].default_value = 2.0
    links.new(coverage.outputs["Result"], rim_presence.inputs[0])

    rim_masked = nodes.new("ShaderNodeMath")
    rim_masked.location = (3400, -900)
    rim_masked.operation = "MULTIPLY"
    rim_masked.use_clamp = True
    links.new(rim_factor.outputs[0], rim_masked.inputs[0])
    links.new(rim_presence.outputs[0], rim_masked.inputs[1])

    rim_boosted = nodes.new("ShaderNodeMath")
    rim_boosted.location = (3880, -900)
    rim_boosted.operation = "MULTIPLY"
    rim_boosted.use_clamp = True
    links.new(rim_masked.outputs[0], rim_boosted.inputs[0])
    links.new(group_in.outputs["Cloud Rim Boost"], rim_boosted.inputs[1])

    mix_body = nodes.new("ShaderNodeMix")
    mix_body.location = (2800, -720)
    mix_body.data_type = "RGBA"
    mix_body.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_body)
    links.new(group_in.outputs["Cloud Shadow"], a_sock)
    links.new(group_in.outputs["Cloud Mid"], b_sock)
    links.new(body_mix.outputs["Result"], mix_body.inputs["Factor"])

    mix_light = nodes.new("ShaderNodeMix")
    mix_light.location = (2980, -680)
    mix_light.data_type = "RGBA"
    mix_light.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_light)
    links.new(mix_body.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)
    links.new(rim_boosted.outputs[0], mix_light.inputs["Factor"])

    horizon = nodes.new("ShaderNodeMapRange")
    horizon.location = (1440, 700)
    horizon.clamp = True
    _smooth(horizon)
    horizon.inputs["From Min"].default_value = 0.015
    horizon.inputs["From Max"].default_value = 0.16
    links.new(separate.outputs["Z"], horizon.inputs["Value"])

    cloud_mask = nodes.new("ShaderNodeMath")
    cloud_mask.location = (1640, 660)
    cloud_mask.operation = "MULTIPLY"
    cloud_mask.use_clamp = True
    links.new(coverage_gate.outputs[0], cloud_mask.inputs[0])
    links.new(horizon.outputs["Result"], cloud_mask.inputs[1])

    cloud_amount_node = nodes.new("ShaderNodeMath")
    cloud_amount_node.location = (1820, 620)
    cloud_amount_node.operation = "MULTIPLY"
    cloud_amount_node.use_clamp = True
    links.new(cloud_mask.outputs[0], cloud_amount_node.inputs[0])
    cloud_amount_node.inputs[1].default_value = 1.0

    # The Mie glow also warms the clouds near the solar disk, not only the
    # exposed sky behind them.
    cloud_glow_scale = nodes.new("ShaderNodeMath")
    cloud_glow_scale.location = (2040, 760)
    cloud_glow_scale.operation = "MULTIPLY"
    cloud_glow_scale.inputs[1].default_value = 0.08
    links.new(glow_power.outputs[0], cloud_glow_scale.inputs[0])

    cloud_glow_user = nodes.new("ShaderNodeMath")
    cloud_glow_user.location = (2220, 760)
    cloud_glow_user.operation = "MULTIPLY"
    cloud_glow_user.use_clamp = True
    links.new(cloud_glow_scale.outputs[0], cloud_glow_user.inputs[0])
    links.new(group_in.outputs["Sun Glow"], cloud_glow_user.inputs[1])

    cloud_glow_color = nodes.new("ShaderNodeVectorMath")
    cloud_glow_color.location = (2400, 760)
    cloud_glow_color.operation = "SCALE"
    links.new(group_in.outputs["Sun Color"], cloud_glow_color.inputs["Vector"])
    links.new(cloud_glow_user.outputs[0], cloud_glow_color.inputs["Scale"])

    cloud_glow_add = nodes.new("ShaderNodeMix")
    cloud_glow_add.location = (2580, 760)
    cloud_glow_add.data_type = "RGBA"
    cloud_glow_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(cloud_glow_add)
    links.new(mix_light.outputs["Result"], a_sock)
    links.new(cloud_glow_color.outputs["Vector"], b_sock)
    cloud_glow_add.inputs["Factor"].default_value = 1.0

    cloud_mix = nodes.new("ShaderNodeMix")
    cloud_mix.location = (2040, 0)
    cloud_mix.data_type = "RGBA"
    cloud_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(cloud_mix)
    links.new(sky_color, a_sock)
    links.new(cloud_glow_add.outputs["Result"], b_sock)
    links.new(cloud_amount_node.outputs[0], cloud_mix.inputs["Factor"])

    # Clustered painterly anime starfield: a sparse background layer plus a
    # handful of soft gouache hero stars, grouped into broad constellations.
    cluster_noise = nodes.new("ShaderNodeTexNoise")
    cluster_noise.location = (1880, -360)
    cluster_noise.inputs["Scale"].default_value = 3.2
    cluster_noise.inputs["Detail"].default_value = 3.0
    cluster_noise.inputs["Roughness"].default_value = 0.55
    cluster_noise.inputs["Distortion"].default_value = 0.25
    links.new(view_norm.outputs["Vector"], cluster_noise.inputs["Vector"])

    cluster_mask = nodes.new("ShaderNodeMapRange")
    cluster_mask.location = (2060, -360)
    cluster_mask.clamp = True
    _smooth(cluster_mask)
    cluster_mask.inputs["From Min"].default_value = 0.36
    cluster_mask.inputs["From Max"].default_value = 0.68
    cluster_mask.inputs["To Min"].default_value = 0.08
    cluster_mask.inputs["To Max"].default_value = 1.0
    links.new(cluster_noise.outputs["Fac"], cluster_mask.inputs["Value"])

    # Background micro-stars: sparse, soft, and always subordinate.
    star_scale = nodes.new("ShaderNodeMath")
    star_scale.location = (1880, -560)
    star_scale.operation = "MULTIPLY"
    star_scale.inputs[1].default_value = 1.6
    links.new(group_in.outputs["Star Density"], star_scale.inputs[0])

    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.location = (2060, -560)
    links.new(view_norm.outputs["Vector"], voronoi.inputs["Vector"])
    links.new(star_scale.outputs[0], voronoi.inputs["Scale"])

    star_curve = nodes.new("ShaderNodeMapRange")
    star_curve.location = (2240, -560)
    star_curve.clamp = True
    _smooth(star_curve)
    star_curve.inputs["From Min"].default_value = 0.0
    star_curve.inputs["From Max"].default_value = 0.055
    star_curve.inputs["To Min"].default_value = 1.0
    star_curve.inputs["To Max"].default_value = 0.0
    links.new(voronoi.outputs["Distance"], star_curve.inputs["Value"])

    star_noise = nodes.new("ShaderNodeTexNoise")
    star_noise.location = (2060, -760)
    star_noise.inputs["Scale"].default_value = 95.0
    star_noise.inputs["Detail"].default_value = 1.0
    links.new(view_norm.outputs["Vector"], star_noise.inputs["Vector"])

    star_mag = nodes.new("ShaderNodeMapRange")
    star_mag.location = (2240, -760)
    star_mag.clamp = True
    _smooth(star_mag)
    star_mag.inputs["From Min"].default_value = 0.60
    star_mag.inputs["From Max"].default_value = 0.86
    star_mag.inputs["To Min"].default_value = 0.0
    star_mag.inputs["To Max"].default_value = 1.0
    links.new(star_noise.outputs["Fac"], star_mag.inputs["Value"])

    star_bg = nodes.new("ShaderNodeMath")
    star_bg.location = (2420, -620)
    star_bg.operation = "MULTIPLY"
    star_bg.use_clamp = True
    links.new(star_curve.outputs["Result"], star_bg.inputs[0])
    links.new(star_mag.outputs["Result"], star_bg.inputs[1])

    star_bg_clustered = nodes.new("ShaderNodeMath")
    star_bg_clustered.location = (2600, -620)
    star_bg_clustered.operation = "MULTIPLY"
    star_bg_clustered.use_clamp = True
    links.new(star_bg.outputs[0], star_bg_clustered.inputs[0])
    links.new(cluster_mask.outputs["Result"], star_bg_clustered.inputs[1])

    star_bg_scaled = nodes.new("ShaderNodeMath")
    star_bg_scaled.location = (2780, -620)
    star_bg_scaled.operation = "MULTIPLY"
    star_bg_scaled.use_clamp = True
    star_bg_scaled.inputs[1].default_value = 0.42
    links.new(star_bg_clustered.outputs[0], star_bg_scaled.inputs[0])

    # Hero stars: a few larger cores with a very soft gouache halo.
    hero_scale = nodes.new("ShaderNodeMath")
    hero_scale.location = (1880, -960)
    hero_scale.operation = "MULTIPLY"
    hero_scale.inputs[1].default_value = 0.42
    links.new(group_in.outputs["Star Density"], hero_scale.inputs[0])

    hero_voronoi = nodes.new("ShaderNodeTexVoronoi")
    hero_voronoi.location = (2060, -960)
    links.new(view_norm.outputs["Vector"], hero_voronoi.inputs["Vector"])
    links.new(hero_scale.outputs[0], hero_voronoi.inputs["Scale"])

    hero_core = nodes.new("ShaderNodeMapRange")
    hero_core.location = (2240, -960)
    hero_core.clamp = True
    _smooth(hero_core)
    hero_core.inputs["From Min"].default_value = 0.0
    hero_core.inputs["From Max"].default_value = 0.048
    hero_core.inputs["To Min"].default_value = 1.0
    hero_core.inputs["To Max"].default_value = 0.0
    links.new(hero_voronoi.outputs["Distance"], hero_core.inputs["Value"])

    hero_halo = nodes.new("ShaderNodeMapRange")
    hero_halo.location = (2240, -1120)
    hero_halo.clamp = True
    _smooth(hero_halo)
    hero_halo.inputs["From Min"].default_value = 0.0
    hero_halo.inputs["From Max"].default_value = 0.18
    hero_halo.inputs["To Min"].default_value = 0.35
    hero_halo.inputs["To Max"].default_value = 0.0
    links.new(hero_voronoi.outputs["Distance"], hero_halo.inputs["Value"])

    hero_shape = nodes.new("ShaderNodeMath")
    hero_shape.location = (2420, -1020)
    hero_shape.operation = "ADD"
    hero_shape.use_clamp = True
    links.new(hero_core.outputs["Result"], hero_shape.inputs[0])
    links.new(hero_halo.outputs["Result"], hero_shape.inputs[1])

    hero_noise = nodes.new("ShaderNodeTexNoise")
    hero_noise.location = (2060, -1280)
    hero_noise.inputs["Scale"].default_value = 38.0
    hero_noise.inputs["Detail"].default_value = 1.0
    links.new(view_norm.outputs["Vector"], hero_noise.inputs["Vector"])

    hero_cull = nodes.new("ShaderNodeMapRange")
    hero_cull.location = (2240, -1280)
    hero_cull.clamp = True
    _smooth(hero_cull)
    hero_cull.inputs["From Min"].default_value = 0.68
    hero_cull.inputs["From Max"].default_value = 0.88
    hero_cull.inputs["To Min"].default_value = 0.0
    hero_cull.inputs["To Max"].default_value = 1.0
    links.new(hero_noise.outputs["Fac"], hero_cull.inputs["Value"])

    hero_stars = nodes.new("ShaderNodeMath")
    hero_stars.location = (2600, -1080)
    hero_stars.operation = "MULTIPLY"
    hero_stars.use_clamp = True
    links.new(hero_shape.outputs[0], hero_stars.inputs[0])
    links.new(hero_cull.outputs["Result"], hero_stars.inputs[1])

    star_total = nodes.new("ShaderNodeMath")
    star_total.location = (2780, -820)
    star_total.operation = "ADD"
    star_total.use_clamp = True
    links.new(star_bg_scaled.outputs[0], star_total.inputs[0])
    links.new(hero_stars.outputs[0], star_total.inputs[1])

    # Atmospheric masks: zenith, solar disk, and cloud coverage.
    zenith = nodes.new("ShaderNodeMapRange")
    zenith.location = (1880, -520)
    zenith.clamp = True
    _smooth(zenith)
    zenith.inputs["From Min"].default_value = 0.08
    zenith.inputs["From Max"].default_value = 0.32
    links.new(separate.outputs["Z"], zenith.inputs["Value"])

    sun_hide = nodes.new("ShaderNodeMapRange")
    sun_hide.location = (2060, -520)
    sun_hide.clamp = True
    _smooth(sun_hide)
    sun_hide.inputs["From Min"].default_value = 0.95
    sun_hide.inputs["From Max"].default_value = 0.995
    sun_hide.inputs["To Min"].default_value = 1.0
    sun_hide.inputs["To Max"].default_value = 0.0
    links.new(dot.outputs["Value"], sun_hide.inputs["Value"])

    star_mask_a = nodes.new("ShaderNodeMath")
    star_mask_a.location = (2960, -760)
    star_mask_a.operation = "MULTIPLY"
    star_mask_a.use_clamp = True
    links.new(star_total.outputs[0], star_mask_a.inputs[0])
    links.new(zenith.outputs["Result"], star_mask_a.inputs[1])

    star_mask_b = nodes.new("ShaderNodeMath")
    star_mask_b.location = (3140, -760)
    star_mask_b.operation = "MULTIPLY"
    star_mask_b.use_clamp = True
    links.new(star_mask_a.outputs[0], star_mask_b.inputs[0])
    links.new(sun_hide.outputs["Result"], star_mask_b.inputs[1])

    cloud_hide = nodes.new("ShaderNodeMath")
    cloud_hide.location = (2960, -1000)
    cloud_hide.operation = "SUBTRACT"
    cloud_hide.use_clamp = True
    cloud_hide.inputs[0].default_value = 1.0
    links.new(cloud_amount_node.outputs[0], cloud_hide.inputs[1])

    star_mask_c = nodes.new("ShaderNodeMath")
    star_mask_c.location = (3320, -760)
    star_mask_c.operation = "MULTIPLY"
    star_mask_c.use_clamp = True
    links.new(star_mask_b.outputs[0], star_mask_c.inputs[0])
    links.new(cloud_hide.outputs[0], star_mask_c.inputs[1])

    star_amount = nodes.new("ShaderNodeMath")
    star_amount.location = (3500, -760)
    star_amount.operation = "MULTIPLY"
    star_amount.use_clamp = True
    links.new(star_mask_c.outputs[0], star_amount.inputs[0])
    links.new(group_in.outputs["Star Amount"], star_amount.inputs[1])

    # Painterly tint: warm starlight blended 38% toward Cloud Light, scaled to
    # a soft glow rather than the old clipped white (15.0) points.
    star_base_rgb = nodes.new("ShaderNodeRGB")
    star_base_rgb.location = (2960, -1180)
    star_base_rgb.outputs[0].default_value = (1.0, 0.98, 0.94, 1.0)

    star_tint_mix = nodes.new("ShaderNodeMix")
    star_tint_mix.location = (3140, -1180)
    star_tint_mix.data_type = "RGBA"
    star_tint_mix.blend_type = "MIX"
    star_tint_mix.inputs["Factor"].default_value = 0.38
    a_sock, b_sock, result_sock = _rgba_sockets(star_tint_mix)
    links.new(star_base_rgb.outputs[0], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)

    star_tint_scale = nodes.new("ShaderNodeVectorMath")
    star_tint_scale.location = (3320, -1180)
    star_tint_scale.operation = "SCALE"
    star_tint_scale.inputs["Scale"].default_value = 2.6
    links.new(star_tint_mix.outputs["Result"], star_tint_scale.inputs["Vector"])

    star_mix = nodes.new("ShaderNodeMix")
    star_mix.location = (3500, -200)
    star_mix.data_type = "RGBA"
    star_mix.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(star_mix)
    links.new(cloud_mix.outputs["Result"], a_sock)
    links.new(star_tint_scale.outputs["Vector"], b_sock)
    links.new(star_amount.outputs[0], star_mix.inputs["Factor"])
    sky_color = star_mix.outputs["Result"]

    # Visible sky stays vivid; ambient light is scaled by World Strength.
    light_path = nodes.new("ShaderNodeLightPath")
    light_path.location = (2320, 420)
    ambient = nodes.new("ShaderNodeVectorMath")
    ambient.location = (2500, 220)
    ambient.operation = "SCALE"
    links.new(sky_color, ambient.inputs["Vector"])
    links.new(group_in.outputs["World Strength"], ambient.inputs["Scale"])

    visible = nodes.new("ShaderNodeMix")
    visible.location = (2680, 0)
    visible.data_type = "RGBA"
    visible.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(visible)
    links.new(ambient.outputs["Vector"], a_sock)
    links.new(sky_color, b_sock)
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
    if (sun.get(AUTO_SUN_TAG) and sun.parent is None
            and len(sun.constraints) == 0):
        quaternion = sun.rotation_euler.to_quaternion()
    else:
        quaternion = sun.matrix_world.to_quaternion()
    direction = quaternion @ Vector((0.0, 0.0, -1.0))
    return (-direction.x, -direction.y, -direction.z)


_syncing_angles = False
_syncing_style = False


def angles_syncing():
    return _syncing_angles


def style_syncing():
    return _syncing_style


def apply_preset_style(scene, p):
    """Apply preset cloud/glow controls behind the style guard."""
    global _syncing_style
    settings = getattr(scene, "ald", None)
    if settings is None:
        return
    _syncing_style = True
    try:
        settings.cloud_flatness = p.get("cloud_flatness", 0.65)
        settings.cloud_scale = p.get("cloud_scale", 3.0)
        settings.cloud_rim_boost = p.get("cloud_rim_boost", 1.0)
        settings.cloud_amount = p.get("cloud_amount", 0.6)
        settings.cloud_delta_gain = p.get("cloud_delta_gain", 1.0)
        settings.sun_glow = p.get("sun_glow", 0.45)
        settings.sky_accent = p.get("sky_accent", (0.05, 0.32, 0.42))
        settings.sky_accent_amount = p.get("sky_accent_amount", 0.0)
        settings.horizon_offset = p.get("horizon_offset", 0.0)
        settings.horizon_softness = p.get("horizon_softness", 0.5)
        settings.contrails = p.get("contrails", 0.0)
        settings.star_strength = p.get("star_strength", 1.0)
        settings.star_density = p.get("star_density", 180.0)
    finally:
        _syncing_style = False


def rotation_from_angles(elevation, azimuth):
    """Sun rotation for an elevation/azimuth in degrees."""
    return (math.radians(90.0 - elevation), 0.0,
            math.radians(azimuth))


def angles_from_direction(direction):
    elevation = math.degrees(math.asin(
        max(-1.0, min(1.0, direction[2]))))
    azimuth = math.degrees(math.atan2(direction[0], -direction[1]))
    return elevation, azimuth


def sync_sun_angles(scene):
    """Refresh the UI angle sliders from the active sun direction."""
    global _syncing_angles
    settings = getattr(scene, "ald", None)
    direction = sun_toward(scene)
    if settings is None or direction is None:
        return
    elevation, azimuth = angles_from_direction(direction)
    _syncing_angles = True
    try:
        settings.sun_elevation = elevation
        settings.sun_azimuth = azimuth
    finally:
        _syncing_angles = False


def apply_sun_angles(scene, elevation, azimuth):
    """Move the active sun to the requested elevation/azimuth."""
    settings = getattr(scene, "ald", None)
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    if sun is None and settings is not None:
        key = scene.get("ald_effective_palette", settings.palette)
        ensure_sun(scene, effective(scene, key))
        sun = next((o for o in scene.objects
                    if o.type == "LIGHT" and o.data is not None
                    and o.data.type == "SUN"), None)
    if sun is None or sun.library is not None or sun.data.library is not None:
        return
    sun.rotation_euler = rotation_from_angles(elevation, azimuth)
    from . import cameras
    cameras.update_transforms(scene, force=True)


def _cloud_offset(scene, settings):
    wind = getattr(settings, "cloud_wind", 0.0) if settings else 0.0
    frame = float(scene.frame_current)
    return (frame * wind * 0.02, frame * wind * 0.005, 0.0)


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
    cloud_md = p.get("cloud_mid") or (0.6, 0.6, 0.7)
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
    node.inputs["Sun Glow"].default_value = (
        getattr(settings, "sun_glow", 0.45) if settings else 0.45)
    node.inputs["Sky Accent"].default_value = _rgba(
        getattr(settings, "sky_accent", (0.05, 0.32, 0.42))
        if settings else (0.05, 0.32, 0.42))
    node.inputs["Sky Accent Amount"].default_value = (
        getattr(settings, "sky_accent_amount", 0.0) if settings else 0.0)

    clouds = getattr(settings, "clouds", True) if settings else False
    node.inputs["Cloud Amount"].default_value = (
        getattr(settings, "cloud_amount", 0.6) if clouds else 0.0)
    node.inputs["Cloud Scale"].default_value = (
        getattr(settings, "cloud_scale", 3.0) if settings else 3.0)
    node.inputs["Cloud Flatness"].default_value = (
        getattr(settings, "cloud_flatness", 0.65) if settings else 0.65)
    node.inputs["Contrails"].default_value = (
        getattr(settings, "contrails", 0.0) if settings else 0.0)
    node.inputs["Cloud Delta Gain"].default_value = (
        getattr(settings, "cloud_delta_gain", 1.0) if settings else 1.0)
    node.inputs["Cloud Rim Boost"].default_value = (
        getattr(settings, "cloud_rim_boost", 1.0) if settings else 1.0)

    stars = getattr(settings, "stars", True) if settings else False
    star_amount = 0.0
    if stars:
        star_amount = (p.get("star_amount", 0.0)
                       * getattr(settings, "star_strength", 1.0))
    node.inputs["Star Amount"].default_value = max(0.0, min(1.0, star_amount))
    node.inputs["Star Density"].default_value = (
        getattr(settings, "star_density", 180.0) if settings else 180.0)
    node.inputs["Cloud Offset"].default_value = _cloud_offset(scene, settings)

    for link in list(background.inputs["Color"].links):
        nt.links.remove(link)
    nt.links.new(node.outputs["Color"], background.inputs["Color"])


def ensure_sun(scene, p, reset_rotation=True):
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
            if sun.get(AUTO_SUN_TAG) and reset_rotation:
                sun.rotation_euler = rotation
    return sun, created


def apply_palette(scene, key):
    """Apply world gradient + sun values for a palette. Returns the preset."""
    global _syncing_style
    p = effective(scene, key)
    settings = getattr(scene, "ald", None)
    world = _ensure_world(scene)
    key_changed = scene.get("ald_last_palette") != key
    ensure_sun(scene, p, reset_rotation=key_changed)
    if key_changed and settings is not None:
        apply_preset_style(scene, p)
    nt, background = _world_nodes(world)
    _apply_gradient(scene, settings, nt, background, p)
    scene["ald_last_palette"] = key
    scene["ald_effective_palette"] = key
    sync_sun_angles(scene)
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
    if settings is not None:
        node.inputs["Cloud Offset"].default_value = _cloud_offset(scene, settings)
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
