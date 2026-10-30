"""Atmospheric palettes: world gradient, sun light and halation tint."""

import math

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

from .shaders import moon as moon_shader

GRADIENT_GROUP = "ALD | World Gradient"
GRADIENT_BUILD = 37
AUTO_SUN_TAG = "ald_auto_sun"
SUN_OWNER_TAG = "ald_sun_owner"

PRESETS = {'GOLDEN_HOUR': {'world_color': (0.85, 0.38, 0.14),
                 'world_strength': 0.92,
                 'sky_color': (0.015, 0.06, 0.3),
                 'mid_sky_color': (0.48, 0.24, 0.16),
                 'horizon_color': (1.3, 0.62, 0.12),
                 'ground_color': (0.08, 0.05, 0.06),
                 'cloud_shadow': (0.16, 0.12, 0.12),
                 'cloud_mid': (0.52, 0.26, 0.18),
                 'cloud_light': (1.38, 0.82, 0.34),
                 'cloud_flatness': 0.55,
                 'cloud_scale': 3.0,
                 'cloud_rim_boost': 1.2,
                 'cloud_amount': 0.65,
                 'star_amount': 0.0,
                 'star_density': 150.0,
                 'milky_way': 0.0,
                 'contrails': 0.0,
                 'sun_glow': 0.6,
                 'sky_accent': (0.1, 0.45, 0.48),
                 'sky_accent_amount': 0.2,
                 'horizon_offset': 0.0,
                 'horizon_softness': 0.56,
                 'sun_color': (1.0, 0.55, 0.2),
                 'sun_energy': 4.2,
                 'sun_rotation': (1.28, 0.12, -0.55),
                 'glare_tint': (1.0, 0.52, 0.22, 1.0),
                 'shadow_tint': (0.26, 0.34, 0.92),
                 'cloud_seed': 17},
 'AFTER_SCHOOL': {'world_color': (0.82, 0.42, 0.48),
                  'world_strength': 0.86,
                  'sky_color': (0.1, 0.18, 0.52),
                  'mid_sky_color': (0.4, 0.32, 0.62),
                  'horizon_color': (1.18, 0.6, 0.34),
                  'ground_color': (0.12, 0.1, 0.16),
                  'cloud_shadow': (0.18, 0.14, 0.18),
                  'cloud_mid': (0.48, 0.3, 0.28),
                  'cloud_light': (1.3, 0.72, 0.42),
                  'cloud_flatness': 0.9,
                  'cloud_scale': 4.0,
                  'cloud_rim_boost': 2.0,
                  'cloud_amount': 0.55,
                  'star_amount': 0.0,
                  'star_density': 140.0,
                  'milky_way': 0.0,
                  'contrails': 0.0,
                  'sun_glow': 0.55,
                  'sky_accent': (0.35, 0.28, 0.55),
                  'sky_accent_amount': 0.18,
                  'horizon_offset': 0.02,
                  'horizon_softness': 0.56,
                  'sun_color': (1.0, 0.6, 0.4),
                  'sun_energy': 3.8,
                  'sun_rotation': (1.4, 0.1, -0.5),
                  'glare_tint': (1.0, 0.58, 0.42, 1.0),
                  'shadow_tint': (0.36, 0.4, 0.88)},
 'SUMMER_NOON': {'world_color': (0.32, 0.55, 0.95),
                 'world_strength': 0.95,
                 'sky_color': (0.01, 0.1, 0.72),
                 'mid_sky_color': (0.06, 0.34, 0.92),
                 'horizon_color': (0.48, 0.78, 0.98),
                 'ground_color': (0.14, 0.22, 0.32),
                 'cloud_shadow': (0.24, 0.36, 0.62),
                 'cloud_mid': (0.95, 0.97, 1.0),
                 'cloud_light': (1.28, 1.26, 1.18),
                 'cloud_flatness': 0.25,
                 'cloud_scale': 3.2,
                 'cloud_rim_boost': 1.0,
                 'cloud_amount': 0.7,
                 'star_amount': 0.0,
                 'star_density': 180.0,
                 'milky_way': 0.0,
                 'contrails': 0.0,
                 'sun_glow': 0.35,
                 'sky_accent': (0.18, 0.62, 0.95),
                 'sky_accent_amount': 0.15,
                 'horizon_offset': -0.04,
                 'horizon_softness': 0.48,
                 'sun_color': (1.0, 0.93, 0.8),
                 'sun_energy': 4.8,
                 'sun_rotation': (0.68, 0.15, -0.65),
                 'glare_tint': (1.0, 0.95, 0.82, 1.0),
                 'shadow_tint': (0.28, 0.48, 0.9)},
 'RAINY_TOKYO': {'world_color': (0.12, 0.2, 0.3),
                 'world_strength': 0.78,
                 'sky_color': (0.022, 0.052, 0.105),
                 'mid_sky_color': (0.075, 0.145, 0.22),
                 'horizon_color': (0.24, 0.36, 0.46),
                 'ground_color': (0.035, 0.05, 0.075),
                 'cloud_shadow': (0.035, 0.06, 0.1),
                 'cloud_mid': (0.14, 0.21, 0.28),
                 'cloud_light': (0.36, 0.48, 0.58),
                 'cloud_flatness': 0.65,
                 'cloud_scale': 3.0,
                 'cloud_rim_boost': 0.8,
                 'cloud_amount': 0.65,
                 'star_amount': 0.0,
                 'star_density': 180.0,
                 'milky_way': 0.0,
                 'contrails': 0.0,
                 'sun_glow': 0.0,
                 'sky_accent': (0.08, 0.18, 0.28),
                 'sky_accent_amount': 0.15,
                 'horizon_offset': -0.05,
                 'horizon_softness': 0.65,
                 'sun_color': (0.58, 0.76, 0.95),
                 'sun_energy': 1.1,
                 'sun_rotation': (0.85, 0.2, -0.45),
                 'glare_tint': (0.55, 0.8, 1.0, 1.0),
                 'shadow_tint': (0.2, 0.4, 0.75),
                 'sun_disk': False,
                 'sun_glow_enabled': False},
 'NEON_NIGHT': {'world_color': (0.18, 0.03, 0.28),
                'world_strength': 0.65,
                'sky_color': (0.003, 0.008, 0.06),
                'mid_sky_color': (0.04, 0.02, 0.14),
                'horizon_color': (0.65, 0.04, 0.28),
                'ground_color': (0.01, 0.01, 0.03),
                'cloud_shadow': (0.015, 0.015, 0.06),
                'cloud_mid': (0.07, 0.02, 0.12),
                'cloud_light': (0.18, 0.75, 0.95),
                'cloud_flatness': 0.75,
                'cloud_scale': 3.5,
                'cloud_rim_boost': 1.5,
                'cloud_amount': 0.45,
                'star_amount': 0.85,
                'star_density': 160.0,
                'milky_way': 0.0,
                'contrails': 0.0,
                'sun_glow': 0.2,
                'sky_accent': (0.02, 0.78, 0.88),
                'sky_accent_amount': 0.22,
                'horizon_offset': 0.0,
                'horizon_softness': 0.34,
                'sun_color': (1.0, 0.16, 0.52),
                'sun_energy': 1.2,
                'sun_rotation': (1.71, 0.1, -0.75),
                'glare_tint': (1.0, 0.18, 0.58, 1.0),
                'shadow_tint': (0.42, 0.14, 0.92),
                'sun_disk': False,
                'cloud_seed': 43},
 'SAKURA_SPRING': {'world_color': (0.72, 0.48, 0.58),
                   'world_strength': 0.83,
                   'sky_color': (0.02, 0.16, 0.74),
                   'mid_sky_color': (0.18, 0.38, 0.82),
                   'horizon_color': (1.0, 0.68, 0.6),
                   'ground_color': (0.14, 0.17, 0.25),
                   'cloud_shadow': (0.35, 0.42, 0.62),
                   'cloud_mid': (0.95, 0.9, 0.86),
                   'cloud_light': (1.3, 1.12, 1.0),
                   'cloud_flatness': 0.5,
                   'cloud_scale': 3.0,
                   'cloud_rim_boost': 1.0,
                   'cloud_amount': 0.45,
                   'star_amount': 0.0,
                   'star_density': 180.0,
                   'milky_way': 0.0,
                   'contrails': 0.0,
                   'sun_glow': 0.45,
                   'sky_accent': (0.55, 0.55, 0.72),
                   'sky_accent_amount': 0.18,
                   'horizon_offset': 0.0,
                   'horizon_softness': 0.55,
                   'sun_color': (1.0, 0.78, 0.72),
                   'sun_energy': 3.2,
                   'sun_rotation': (0.88, 0.14, -0.52),
                   'glare_tint': (1.0, 0.72, 0.8, 1.0),
                   'shadow_tint': (0.52, 0.36, 0.88)},
 'TWILIGHT_DUSK': {'world_color': (0.42, 0.14, 0.24),
                   'world_strength': 0.75,
                   'sky_color': (0.005, 0.008, 0.08),
                   'mid_sky_color': (0.08, 0.06, 0.22),
                   'horizon_color': (0.65, 0.2, 0.06),
                   'ground_color': (0.025, 0.02, 0.045),
                   'cloud_shadow': (0.02, 0.02, 0.08),
                   'cloud_mid': (0.14, 0.06, 0.14),
                   'cloud_light': (0.9, 0.3, 0.08),
                   'cloud_flatness': 0.75,
                   'cloud_scale': 3.5,
                   'cloud_rim_boost': 2.0,
                   'cloud_amount': 0.55,
                   'star_amount': 0.25,
                   'star_density': 165.0,
                   'milky_way': 0.2,
                   'contrails': 0.0,
                   'sun_glow': 0.4,
                   'sky_accent': (0.08, 0.35, 0.52),
                   'sky_accent_amount': 0.3,
                   'horizon_offset': -0.02,
                   'horizon_softness': 0.26,
                   'sun_color': (1.0, 0.38, 0.15),
                   'sun_energy': 1.0,
                   'sun_rotation': (1.64, 0.1, -0.6),
                   'glare_tint': (1.0, 0.42, 0.2, 1.0),
                   'shadow_tint': (0.25, 0.3, 0.88),
                   'sun_disk': False,
                   'cloud_seed': 71},
 'SOFT_DAWN': {'world_color': (0.75, 0.55, 0.62),
               'world_strength': 0.82,
               'sky_color': (0.05, 0.15, 0.52),
               'mid_sky_color': (0.26, 0.42, 0.74),
               'horizon_color': (1.15, 0.6, 0.35),
               'ground_color': (0.1, 0.1, 0.14),
               'cloud_shadow': (0.18, 0.22, 0.38),
               'cloud_mid': (0.55, 0.55, 0.65),
               'cloud_light': (1.22, 0.88, 0.68),
               'cloud_flatness': 0.55,
               'cloud_scale': 3.8,
               'cloud_rim_boost': 1.5,
               'cloud_amount': 0.45,
               'cloud_type': 'CUMULUS',
               'cloud_vertical': 0.75,
               'cloud_breakup': 0.3,
               'cloud_detail': 0.55,
               'cloud_sun_lighting': 1.3,
               'star_amount': 0.0,
               'star_density': 120.0,
               'milky_way': 0.0,
               'contrails': 0.0,
               'sun_glow': 0.65,
               'sky_accent': (0.2, 0.45, 0.68),
               'sky_accent_amount': 0.2,
               'horizon_offset': -0.03,
               'horizon_softness': 0.6,
               'sun_color': (1.0, 0.65, 0.45),
               'sun_energy': 2.5,
               'sun_rotation': (1.48, 0.05, -0.7),
               'glare_tint': (1.0, 0.7, 0.5, 1.0),
               'shadow_tint': (0.3, 0.32, 0.85)},
 'BLUE_HOUR': {'world_color': (0.18, 0.22, 0.48),
               'world_strength': 0.6,
               'sky_color': (0.012, 0.04, 0.24),
               'mid_sky_color': (0.06, 0.16, 0.5),
               'horizon_color': (0.26, 0.28, 0.52),
               'ground_color': (0.015, 0.02, 0.05),
               'cloud_shadow': (0.03, 0.05, 0.16),
               'cloud_mid': (0.1, 0.16, 0.34),
               'cloud_light': (0.45, 0.55, 0.85),
               'cloud_flatness': 0.75,
               'cloud_scale': 4.2,
               'cloud_rim_boost': 1.4,
               'cloud_amount': 0.55,
               'cloud_type': 'STRATOCUMULUS',
               'cloud_vertical': 0.2,
               'cloud_breakup': 0.45,
               'cloud_detail': 0.6,
               'cloud_sun_lighting': 0.9,
               'star_amount': 0.55,
               'star_density': 170.0,
               'milky_way': 0.35,
               'contrails': 0.0,
               'sun_glow': 0.18,
               'sky_accent': (0.08, 0.2, 0.5),
               'sky_accent_amount': 0.22,
               'horizon_offset': 0.0,
               'horizon_softness': 0.6,
               'sun_color': (0.65, 0.55, 0.85),
               'sun_energy': 0.7,
               'sun_rotation': (1.66, 0.1, -0.5),
               'glare_tint': (0.6, 0.5, 0.8, 1.0),
               'shadow_tint': (0.25, 0.28, 0.8),
               'sun_disk': False},
 'CLOUDY_AFTERNOON': {'world_color': (0.45, 0.55, 0.65),
                      'world_strength': 0.8,
                      'sky_color': (0.18, 0.32, 0.62),
                      'mid_sky_color': (0.48, 0.58, 0.72),
                      'horizon_color': (0.95, 0.8, 0.65),
                      'ground_color': (0.12, 0.13, 0.15),
                      'cloud_shadow': (0.18, 0.22, 0.3),
                      'cloud_mid': (0.66, 0.7, 0.76),
                      'cloud_light': (1.38, 1.3, 1.18),
                      'cloud_flatness': 0.85,
                      'cloud_scale': 3.2,
                      'cloud_rim_boost': 1.1,
                      'cloud_amount': 0.82,
                      'cloud_type': 'STRATOCUMULUS',
                      'cloud_vertical': 0.15,
                      'cloud_breakup': 0.55,
                      'cloud_detail': 0.65,
                      'cloud_sun_lighting': 1.0,
                      'star_amount': 0.0,
                      'star_density': 100.0,
                      'milky_way': 0.0,
                      'contrails': 0.0,
                      'sun_glow': 0.3,
                      'sky_accent': (0.3, 0.45, 0.6),
                      'sky_accent_amount': 0.15,
                      'horizon_offset': 0.0,
                      'horizon_softness': 0.7,
                      'sun_color': (1.0, 0.9, 0.75),
                      'sun_energy': 3.2,
                      'sun_rotation': (1.0, 0.1, -0.6),
                      'glare_tint': (1.0, 0.9, 0.75, 1.0),
                      'shadow_tint': (0.32, 0.36, 0.8)},
 'STORMY_SUNSET': {'world_color': (0.55, 0.28, 0.3),
                   'world_strength': 0.8,
                   'sky_color': (0.06, 0.05, 0.16),
                   'mid_sky_color': (0.3, 0.12, 0.22),
                   'horizon_color': (1.2, 0.35, 0.18),
                   'ground_color': (0.035, 0.03, 0.045),
                   'cloud_shadow': (0.06, 0.04, 0.08),
                   'cloud_mid': (0.22, 0.1, 0.14),
                   'cloud_light': (1.5, 0.68, 0.3),
                   'cloud_flatness': 0.8,
                   'cloud_scale': 3.0,
                   'cloud_rim_boost': 2.4,
                   'cloud_amount': 0.95,
                   'cloud_type': 'CUMULUS',
                   'cloud_vertical': 0.8,
                   'cloud_breakup': 0.7,
                   'cloud_detail': 0.8,
                   'cloud_sun_lighting': 1.6,
                   'star_amount': 0.0,
                   'star_density': 100.0,
                   'milky_way': 0.0,
                   'contrails': 0.0,
                   'sun_glow': 0.7,
                   'sky_accent': (0.5, 0.2, 0.18),
                   'sky_accent_amount': 0.3,
                   'horizon_offset': -0.05,
                   'horizon_softness': 0.45,
                   'sun_color': (1.0, 0.35, 0.12),
                   'sun_energy': 3.2,
                   'sun_rotation': (1.45, 0.1, -0.5),
                   'glare_tint': (1.0, 0.35, 0.15, 1.0),
                   'shadow_tint': (0.3, 0.2, 0.6),
                   'cloud_seed': 97},
 'MOONLIT_NIGHT': {'world_color': (0.12, 0.16, 0.35),
                   'world_strength': 0.45,
                   'sky_color': (0.015, 0.025, 0.08),
                   'mid_sky_color': (0.04, 0.07, 0.2),
                   'horizon_color': (0.18, 0.22, 0.4),
                   'ground_color': (0.015, 0.018, 0.035),
                   'cloud_shadow': (0.03, 0.04, 0.08),
                   'cloud_mid': (0.1, 0.12, 0.22),
                   'cloud_light': (0.48, 0.56, 0.85),
                   'cloud_flatness': 0.9,
                   'cloud_scale': 3.8,
                   'cloud_rim_boost': 1.2,
                   'cloud_amount': 0.5,
                   'cloud_type': 'STRATOCUMULUS',
                   'cloud_vertical': 0.1,
                   'cloud_breakup': 0.35,
                   'cloud_detail': 0.5,
                   'cloud_sun_lighting': 0.6,
                   'star_amount': 0.85,
                   'star_density': 190.0,
                   'milky_way': 0.65,
                   'contrails': 0.0,
                   'sun_glow': 0.1,
                   'sky_accent': (0.05, 0.12, 0.28),
                   'sky_accent_amount': 0.2,
                   'horizon_offset': 0.0,
                   'horizon_softness': 0.6,
                   'sun_color': (0.55, 0.65, 0.95),
                   'sun_energy': 0.3,
                   'sun_rotation': (1.55, 0.2, -0.4),
                   'glare_tint': (0.4, 0.5, 0.8, 1.0),
                   'shadow_tint': (0.18, 0.2, 0.55)}}


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
        # Cloud colors have their own overrides; Horizon/Shadow/Sun never
        # repaint the clouds implicitly.
        p["cloud_shadow"] = tuple(settings.custom_cloud_shadow)
        p["cloud_mid"] = tuple(settings.custom_cloud_mid)
        p["cloud_light"] = tuple(settings.custom_cloud_light)
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
                           or ng.get("ald_build") != GRADIENT_BUILD):
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GRADIENT_GROUP, "ShaderNodeTree")
        _build_gradient_group(ng)
        ng["ald_build"] = GRADIENT_BUILD
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    types = {node.bl_idname for node in ng.nodes}
    if (not {"Sky Color", "Mid Sky Color", "Horizon Color", "Ground Color",
             "Horizon Offset", "Softness", "Sun Direction", "World Strength",
             "Sun Glow", "Sky Accent", "Sky Accent Amount", "Cloud Amount",
             "Cloud Flatness", "Contrails", "Cloud Delta Gain",
             "Cloud Rim Boost", "Cloud Cumulus", "Cloud Stratocumulus",
             "Cloud Cirrus", "Cloud Vertical", "Cloud Breakup", "Cloud Detail",
             "Cloud Sun Lighting", "Star Amount", "Star Density",
             "Cloud Offset", "Star0 Start U", "Moon Enabled",
             "Moon Direction", "Moon Size", "Moon Halo Color",
             "Moon Light", "Moon Earthshine"} <= names
            or "ShaderNodeMix" not in types
            or "ShaderNodeValToRGB" in types):
        _build_gradient_group(ng)
        ng["ald_build"] = GRADIENT_BUILD
    return ng


def _sample_cloud_density(nodes, links, ray_socket, group_in, flat_scale,
                          flat_inv, y_offset=0.0, flatness_socket=None):
    """Sample Perlin-Worley cloud density and its low-frequency envelope."""
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
    links.new(flatness_socket or group_in.outputs["Cloud Flatness"],
              planar_base.inputs["Scale"])

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
    macro_noise.inputs["Detail"].default_value = 5.5
    macro_noise.inputs["Roughness"].default_value = 0.56
    macro_noise.inputs["Distortion"].default_value = 0.18
    links.new(warped_pos.outputs["Vector"], macro_noise.inputs["Vector"])
    links.new(macro_scale.outputs[0], macro_noise.inputs["Scale"])

    macro_env = node("ShaderNodeMapRange", 980, 300)
    macro_env.clamp = True
    _smooth(macro_env)
    macro_env.inputs["From Min"].default_value = 0.28
    macro_env.inputs["From Max"].default_value = 0.56
    macro_env.inputs["To Min"].default_value = 0.20
    macro_env.inputs["To Max"].default_value = 1.0
    links.new(macro_noise.outputs["Fac"], macro_env.inputs["Value"])

    macro_weight = node("ShaderNodeMath", 980, 420)
    macro_weight.operation = "MULTIPLY"
    macro_weight.inputs[1].default_value = 0.62
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
    puff_scale.inputs[1].default_value = 1.55
    links.new(group_in.outputs["Cloud Scale"], puff_scale.inputs[0])

    puff = node("ShaderNodeTexVoronoi", 800, 780)
    links.new(warped_pos.outputs["Vector"], puff.inputs["Vector"])
    links.new(puff_scale.outputs[0], puff.inputs["Scale"])

    puff_range = node("ShaderNodeMapRange", 980, 780)
    puff_range.clamp = True
    _smooth(puff_range)
    puff_range.inputs["From Min"].default_value = 0.0
    puff_range.inputs["From Max"].default_value = 0.68
    puff_range.inputs["To Min"].default_value = 1.0
    puff_range.inputs["To Max"].default_value = 0.0
    links.new(puff.outputs["Distance"], puff_range.inputs["Value"])

    puff_weight = node("ShaderNodeMath", 1160, 780)
    puff_weight.operation = "MULTIPLY"
    puff_weight.inputs[1].default_value = 0.16
    links.new(puff_range.outputs["Result"], puff_weight.inputs[0])

    detail_lobes = node("ShaderNodeMath", 1340, 560)
    detail_lobes.operation = "ADD"
    detail_lobes.use_clamp = True
    links.new(billow_weight.outputs[0], detail_lobes.inputs[0])
    links.new(puff_weight.outputs[0], detail_lobes.inputs[1])

    gated_lobes = node("ShaderNodeMath", 1520, 560)
    gated_lobes.operation = "MULTIPLY"
    gated_lobes.use_clamp = True
    links.new(detail_lobes.outputs[0], gated_lobes.inputs[0])
    links.new(macro_env.outputs["Result"], gated_lobes.inputs[1])

    rho = node("ShaderNodeMath", 1700, 620)
    rho.operation = "ADD"
    rho.use_clamp = True
    links.new(macro_weight.outputs[0], rho.inputs[0])
    links.new(gated_lobes.outputs[0], rho.inputs[1])

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


def _build_shooting_stars(nodes, links, group_in, cloud_visibility):
    """Four shooting stars on the celestial sphere.

    Each event is a great-circle arc between the start and end directions;
    the width is an angular thickness, so the apparent size does not depend
    on the elevation. Start Frame is the first visible frame and Duration is
    the exact number of visible frames.
    """
    def math(x, y, operation, a=None, b=None, clamp=False):
        node = nodes.new("ShaderNodeMath")
        node.location = (x, y)
        node.operation = operation
        node.use_clamp = clamp
        if a is not None:
            if hasattr(a, "bl_idname") or hasattr(a, "is_output"):
                links.new(a, node.inputs[0])
            else:
                node.inputs[0].default_value = a
        if b is not None:
            if hasattr(b, "bl_idname") or hasattr(b, "is_output"):
                links.new(b, node.inputs[1])
            else:
                node.inputs[1].default_value = b
        return node.outputs[0]

    def vector(x, y, operation, a=None, b=None):
        node = nodes.new("ShaderNodeVectorMath")
        node.location = (x, y)
        node.operation = operation
        if a is not None:
            links.new(a, node.inputs[0])
        if b is not None:
            links.new(b, node.inputs["Scale"] if operation == "SCALE"
                      else node.inputs[1])
        return node.outputs[0]

    def dot(x, y, a, b):
        node = nodes.new("ShaderNodeVectorMath")
        node.location = (x, y)
        node.operation = "DOT_PRODUCT"
        links.new(a, node.inputs[0])
        links.new(b, node.inputs[1])
        return node.outputs["Value"]

    def radians(x, y, socket):
        return math(x, y, "MULTIPLY", socket, 0.017453292519943295)

    def direction(px, py, azimuth, elevation):
        az = radians(px, py, azimuth)
        el = radians(px, py - 100, elevation)
        cos_el = math(px + 180, py - 100, "COSINE", el)
        sin_el = math(px + 180, py, "SINE", el)
        sin_az = math(px + 180, py - 200, "SINE", az)
        cos_az = math(px + 180, py - 300, "COSINE", az)
        x = math(px + 360, py - 200, "MULTIPLY", cos_el, sin_az)
        y = math(px + 360, py - 100, "MULTIPLY", cos_el, cos_az)
        node = nodes.new("ShaderNodeCombineXYZ")
        node.location = (px + 540, py - 100)
        links.new(x, node.inputs["X"])
        links.new(y, node.inputs["Y"])
        links.new(sin_el, node.inputs["Z"])
        return node.outputs[0]

    time = nodes.new("ShaderNodeValue")
    time.location = (2200, 1200)
    time.name = "ALD | Star Time"
    time.outputs[0].default_value = 0.0
    try:
        driver = time.outputs[0].driver_add("default_value").driver
        driver.expression = "frame"
    except Exception:
        pass

    tex = nodes.new("ShaderNodeTexCoord")
    tex.location = (2200, 1520)
    view = nodes.new("ShaderNodeVectorMath")
    view.location = (2380, 1520)
    view.operation = "NORMALIZE"
    links.new(tex.outputs["Generated"], view.inputs[0])
    vsep = nodes.new("ShaderNodeSeparateXYZ")
    vsep.location = (2560, 1520)
    links.new(view.outputs["Vector"], vsep.inputs["Vector"])
    horizon = nodes.new("ShaderNodeMapRange")
    horizon.location = (2740, 1520)
    horizon.clamp = True
    _smooth(horizon)
    horizon.inputs["From Min"].default_value = 0.0
    horizon.inputs["From Max"].default_value = 0.01
    horizon.inputs["To Min"].default_value = 0.0
    horizon.inputs["To Max"].default_value = 1.0
    links.new(vsep.outputs["Z"], horizon.inputs["Value"])

    total = nodes.new("ShaderNodeRGB")
    total.location = (2200, 1000)
    total.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    current = total.outputs[0]
    for index in range(4):
        prefix = "Star%d " % index
        base = 1200 - index * 320
        start_az = group_in.outputs[prefix + "Start U"]
        start_el = group_in.outputs[prefix + "Start V"]
        end_az = group_in.outputs[prefix + "End U"]
        end_el = group_in.outputs[prefix + "End V"]
        start_frame = group_in.outputs[prefix + "Start Frame"]
        duration = group_in.outputs[prefix + "Duration"]
        trail = group_in.outputs[prefix + "Trail"]
        thickness = group_in.outputs[prefix + "Thickness"]
        # The UI max is 0.01 rad; clamp old saved events as well.
        thickness = math(3140, base - 220, "MINIMUM", thickness, 0.01)
        curvature = group_in.outputs[prefix + "Curvature"]
        brightness = group_in.outputs[prefix + "Brightness"]
        glow = group_in.outputs[prefix + "Glow"]
        enabled = group_in.outputs[prefix + "Enabled"]
        color = group_in.outputs[prefix + "Color"]

        start = direction(2900, base, start_az, start_el)
        end = direction(2900, base - 420, end_az, end_el)
        cos_theta = dot(3500, base, start, end)
        theta = math(3680, base, "ARCCOSINE", cos_theta)
        scaled = vector(3500, base - 140, "SCALE", start, cos_theta)
        diff = vector(3680, base - 140, "SUBTRACT", end, scaled)
        tangent = vector(3860, base - 140, "NORMALIZE", diff)
        normal = vector(3860, base - 260, "CROSS_PRODUCT", start, tangent)
        normal = vector(4040, base - 260, "NORMALIZE", normal)

        along_a = dot(4220, base, view.outputs["Vector"], start)
        along_b = dot(4220, base - 100, view.outputs["Vector"], tangent)
        plane = dot(4220, base - 200, view.outputs["Vector"], normal)
        phi = math(4400, base, "ARCTAN2", along_b, along_a)

        # Curvature: bow the great-circle band by a sine-shaped offset along
        # the path normal. Zero keeps the original straight great-circle arc.
        curve_u = math(4400, base - 220, "DIVIDE", phi, theta, clamp=True)
        curve_pi = math(4580, base - 220, "MULTIPLY",
                        curve_u, 3.141592653589793)
        curve_sin = math(4760, base - 220, "SINE", curve_pi)
        curve_amp = math(4580, base - 320, "MULTIPLY", curvature, theta)
        curve_amp = math(4760, base - 320, "MULTIPLY", curve_amp, 0.35)
        curve_bend = math(4940, base - 220, "MULTIPLY",
                          curve_amp, curve_sin)
        plane_curved = math(5120, base - 220, "SUBTRACT",
                            plane, curve_bend)

        span = math(4400, base - 160, "SUBTRACT", duration, 1.0)
        span = math(4580, base - 160, "MAXIMUM", span, 1.0)
        progress = math(4580, base, "SUBTRACT", time.outputs[0], start_frame)
        progress = math(4760, base, "DIVIDE", progress, span, clamp=True)

        alive_low = math(4400, base - 320, "SUBTRACT", start_frame, 0.0001)
        alive_low = math(4580, base - 320, "GREATER_THAN",
                         time.outputs[0], alive_low)
        alive_high = math(4400, base - 400, "ADD", start_frame, duration)
        alive_high = math(4580, base - 400, "LESS_THAN",
                          time.outputs[0], alive_high)
        alive = math(4760, base - 360, "MULTIPLY", alive_low, alive_high)

        life_end = math(4400, base - 520, "ADD", start_frame, duration)
        life_in_end = math(4400, base - 600, "ADD", start_frame, 2.0)
        life_in = nodes.new("ShaderNodeMapRange")
        life_in.location = (4580, base - 600)
        life_in.clamp = True
        _smooth(life_in)
        links.new(start_frame, life_in.inputs["From Min"])
        links.new(life_in_end, life_in.inputs["From Max"])
        life_in.inputs["To Min"].default_value = 0.5
        life_in.inputs["To Max"].default_value = 1.0
        links.new(time.outputs[0], life_in.inputs["Value"])
        life_out_start = math(4580, base - 520, "SUBTRACT", life_end, 3.0)
        life_out_end = math(4760, base - 520, "SUBTRACT", life_end, 1.0)
        life_out = nodes.new("ShaderNodeMapRange")
        life_out.location = (4940, base - 560)
        life_out.clamp = True
        _smooth(life_out)
        links.new(life_out_start, life_out.inputs["From Min"])
        links.new(life_out_end, life_out.inputs["From Max"])
        life_out.inputs["To Min"].default_value = 1.0
        life_out.inputs["To Max"].default_value = 0.3
        links.new(time.outputs[0], life_out.inputs["Value"])
        life_fade = math(5120, base - 560, "MULTIPLY",
                         life_in.outputs["Result"],
                         life_out.outputs["Result"])

        head_angle = math(4940, base, "MULTIPLY", progress, theta)
        tail_angle = math(4940, base - 120, "SUBTRACT", progress, trail)
        tail_angle = math(5120, base - 120, "MULTIPLY", tail_angle, theta)
        tail_angle = math(5300, base - 120, "MAXIMUM", tail_angle, 0.0)
        fade_span = math(5120, base, "SUBTRACT", head_angle, tail_angle)
        fade_span = math(5300, base, "MAXIMUM", fade_span, 0.0001)
        fade = math(5480, base, "SUBTRACT", phi, tail_angle)
        fade = math(5660, base, "DIVIDE", fade, fade_span, clamp=True)
        after_tail = math(5480, base - 120, "SUBTRACT", tail_angle, 0.0001)
        after_tail = math(5660, base - 120, "GREATER_THAN", phi, after_tail)
        before_head = math(5480, base - 200, "ADD", head_angle, 0.0001)
        before_head = math(5660, base - 200, "LESS_THAN", phi, before_head)
        along = math(5840, base - 160, "MULTIPLY", after_tail, before_head)

        tip = nodes.new("ShaderNodeMapRange")
        tip.location = (5840, base + 220)
        tip.clamp = True
        _smooth(tip)
        tip.inputs["From Min"].default_value = 0.0
        tip.inputs["From Max"].default_value = 0.18
        tip.inputs["To Min"].default_value = 0.0
        tip.inputs["To Max"].default_value = 1.0
        links.new(fade, tip.inputs["Value"])
        tail_curve = math(6020, base + 180, "MULTIPLY", fade,
                          tip.outputs["Result"])
        taper = math(6200, base, "MULTIPLY", tail_curve, 0.94)
        taper = math(6380, base, "ADD", taper, 0.06)
        local_width = math(6560, base, "MULTIPLY", thickness, taper)
        abs_plane = math(6020, base - 120, "ABSOLUTE", plane_curved)
        width = nodes.new("ShaderNodeMapRange")
        width.location = (6720, base - 60)
        width.clamp = True
        _smooth(width)
        width.inputs["From Min"].default_value = 0.0
        links.new(local_width, width.inputs["From Max"])
        width.inputs["To Min"].default_value = 1.0
        width.inputs["To Max"].default_value = 0.0
        links.new(abs_plane, width.inputs["Value"])
        tail_fade = math(6720, base + 100, "MULTIPLY", tail_curve, 0.95)
        tail_fade = math(6900, base + 100, "ADD", tail_fade, 0.05)
        body = math(7080, base + 40, "MULTIPLY",
                    width.outputs["Result"], tail_fade)
        body = math(7260, base + 40, "MULTIPLY", body, along)

        cos_head = math(5840, base - 300, "COSINE", head_angle)
        sin_head = math(6020, base - 300, "SINE", head_angle)
        head_a = vector(6200, base - 260, "SCALE", start, cos_head)
        head_b = vector(6200, base - 380, "SCALE", tangent, sin_head)
        head_point = vector(6380, base - 320, "ADD", head_a, head_b)
        head_pi = math(6380, base - 420, "MULTIPLY",
                       progress, 3.141592653589793)
        head_sin = math(6560, base - 420, "SINE", head_pi)
        head_bend = math(6740, base - 420, "MULTIPLY", curvature, theta)
        head_bend = math(6920, base - 420, "MULTIPLY", head_bend, 0.35)
        head_bend = math(7100, base - 420, "MULTIPLY", head_bend, head_sin)
        head_offset = vector(7280, base - 420, "SCALE", normal, head_bend)
        head_point = vector(7460, base - 320, "ADD", head_point, head_offset)
        head_point = vector(7640, base - 320, "NORMALIZE", head_point)
        head_dot = dot(7820, base - 320, view.outputs["Vector"], head_point)
        head_dist = math(6740, base - 320, "SUBTRACT", 1.0, head_dot)
        head_dist = math(6920, base - 320, "MULTIPLY", head_dist, 2.0)
        head_dist = math(7100, base - 320, "MAXIMUM", head_dist, 0.0)
        head_radius = math(6380, base - 440, "MULTIPLY", glow, 0.8)
        head_radius = math(6560, base - 440, "ADD", head_radius, 0.8)
        head_radius = math(6740, base - 440, "MULTIPLY",
                           head_radius, thickness)
        head_radius = math(6920, base - 440, "MINIMUM",
                           head_radius, 0.012)
        head_radius2 = math(7100, base - 440, "MULTIPLY",
                            head_radius, head_radius)
        core_radius2 = math(6920, base - 500, "MULTIPLY",
                            head_radius2, 0.1225)
        halo_ratio = math(7280, base - 380, "DIVIDE",
                          head_dist, head_radius2)
        halo_neg = math(7460, base - 380, "MULTIPLY", halo_ratio, -1.0)
        halo = math(7640, base - 380, "EXPONENT", halo_neg)
        core_ratio = math(7280, base - 500, "DIVIDE",
                          head_dist, core_radius2)
        core_neg = math(7460, base - 500, "MULTIPLY", core_ratio, -1.0)
        core = math(7640, base - 500, "EXPONENT", core_neg)
        core_w = math(7820, base - 500, "MULTIPLY", core, 0.65)
        halo_w = math(7820, base - 380, "MULTIPLY", halo, 0.35)
        head_glow = math(8000, base - 440, "ADD", core_w, halo_w)
        head_boost = math(6740, base - 200, "MULTIPLY", glow, 0.6)
        head_boost = math(6920, base - 200, "ADD", head_boost, 0.8)
        head_value = math(8180, base - 440, "MULTIPLY",
                          head_glow, head_boost)

        value = math(8000, base + 20, "ADD", body, head_value)
        value = math(8180, base + 20, "MULTIPLY", value, brightness)
        value = math(8360, base + 20, "MULTIPLY", value, enabled)
        value = math(8360, base - 80, "MULTIPLY", value, alive)
        value = math(8540, base - 200, "MULTIPLY", value, life_fade)
        value = math(8720, base + 20, "MULTIPLY", value, cloud_visibility)
        value = math(8720, base - 80, "MULTIPLY",
                     value, horizon.outputs["Result"])

        tint = nodes.new("ShaderNodeVectorMath")
        tint.location = (8900, base)
        tint.operation = "SCALE"
        links.new(color, tint.inputs["Vector"])
        links.new(value, tint.inputs["Scale"])
        add = nodes.new("ShaderNodeMix")
        add.location = (9080, base + 100)
        add.data_type = "RGBA"
        add.blend_type = "ADD"
        a_sock, b_sock, result_sock = _rgba_sockets(add)
        links.new(current, a_sock)
        links.new(tint.outputs["Vector"], b_sock)
        add.inputs["Factor"].default_value = 1.0
        current = result_sock
    return current


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
    for name, default in (("Cloud Cumulus", 1.0),
                          ("Cloud Stratocumulus", 0.0),
                          ("Cloud Cirrus", 0.0),
                          ("Cloud Vertical", 0.55),
                          ("Cloud Breakup", 0.35),
                          ("Cloud Detail", 0.60),
                          ("Cloud Sun Lighting", 1.0),
                          ("Cloud Sun Scatter", 0.0)):
        socket = ng.interface.new_socket(name=name, in_out="INPUT",
                                         socket_type="NodeSocketFloat")
        socket.min_value = 0.0
        socket.max_value = 2.0 if name == "Cloud Sun Lighting" else 1.0
        socket.default_value = default
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
    milky_way = ng.interface.new_socket(name="Milky Way", in_out="INPUT",
                                         socket_type="NodeSocketFloat")
    # Start U/V and End U/V hold the start/end azimuth and elevation in
    # degrees; the shader builds the great-circle arc from them.
    for index in range(4):
        prefix = "Star%d " % index
        for suffix, default in (("Start U", 0.0), ("Start V", 0.0),
                                ("End U", 0.0), ("End V", 0.0),
                                ("Curvature", 0.0),
                                ("Start Frame", 1.0), ("Duration", 24.0),
                                ("Trail", 0.55), ("Thickness", 0.006),
                                ("Brightness", 0.0), ("Glow", 1.0),
                                ("Enabled", 0.0)):
            socket = ng.interface.new_socket(name=prefix + suffix,
                                             in_out="INPUT",
                                             socket_type="NodeSocketFloat")
            socket.default_value = default
        socket = ng.interface.new_socket(name=prefix + "Color",
                                         in_out="INPUT",
                                         socket_type="NodeSocketColor")
        socket.default_value = (1.0, 0.86, 0.65, 1.0)
    milky_way.min_value = 0.0
    milky_way.max_value = 1.0
    milky_way.default_value = 0.0
    cloud_offset = ng.interface.new_socket(name="Cloud Offset", in_out="INPUT",
                                           socket_type="NodeSocketVector")
    cloud_offset.default_value = (0.0, 0.0, 0.0)

    for name, default in (("Moon Direction", (0.0, 0.0, 1.0)),
                          ("Moon Right", (1.0, 0.0, 0.0)),
                          ("Moon Up", (0.0, 0.0, 1.0)),
                          ("Moon Light", (0.0, 0.0, 1.0))):
        socket = ng.interface.new_socket(name=name, in_out="INPUT",
                                         socket_type="NodeSocketVector")
        socket.default_value = default
    for name, default, minimum, maximum in (
            ("Moon Enabled", 0.0, 0.0, 1.0),
            ("Moon Size", 2.6, 0.05, 40.0),
            ("Moon Brightness", 1.6, 0.0, 20.0),
            ("Moon Surface Detail", 0.25, 0.0, 1.0),
            ("Moon Crater Strength", 0.25, 0.0, 1.0),
            ("Moon Surface Contrast", 0.35, 0.0, 1.0),
            ("Moon Edge Softness", 0.14, 0.0, 1.0),
            ("Moon Glow", 0.35, 0.0, 4.0),
            ("Moon Halo Radius", 2.0, 0.0, 30.0),
            ("Moon Seed", 7.0, 0.0, 999.0),
            ("Moon Earthshine", 0.06, 0.0, 1.0)):
        socket = ng.interface.new_socket(name=name, in_out="INPUT",
                                         socket_type="NodeSocketFloat")
        socket.default_value = default
        socket.min_value = minimum
        socket.max_value = maximum
    for name, default in (("Moon Color", (1.0, 0.97, 0.9, 1.0)),
                          ("Moon Halo Color", (0.72, 0.8, 1.0, 1.0))):
        socket = ng.interface.new_socket(name=name, in_out="INPUT",
                                         socket_type="NodeSocketColor")
        socket.default_value = default

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

    cirrus_x = nodes.new("ShaderNodeMath")
    cirrus_x.location = (-880, 280)
    cirrus_x.operation = "MULTIPLY"
    cirrus_x.inputs[1].default_value = 2.4
    links.new(group_in.outputs["Cloud Cirrus"], cirrus_x.inputs[0])
    cirrus_x_add = nodes.new("ShaderNodeMath")
    cirrus_x_add.location = (-700, 280)
    cirrus_x_add.operation = "ADD"
    cirrus_x_add.inputs[1].default_value = 1.0
    links.new(cirrus_x.outputs[0], cirrus_x_add.inputs[0])
    cirrus_y = nodes.new("ShaderNodeMath")
    cirrus_y.location = (-880, 140)
    cirrus_y.operation = "MULTIPLY"
    cirrus_y.inputs[1].default_value = -0.68
    links.new(group_in.outputs["Cloud Cirrus"], cirrus_y.inputs[0])
    cirrus_y_add = nodes.new("ShaderNodeMath")
    cirrus_y_add.location = (-700, 140)
    cirrus_y_add.operation = "ADD"
    cirrus_y_add.inputs[1].default_value = 1.0
    links.new(cirrus_y.outputs[0], cirrus_y_add.inputs[0])
    family_scale = nodes.new("ShaderNodeCombineXYZ")
    family_scale.location = (-520, 200)
    links.new(cirrus_x_add.outputs[0], family_scale.inputs["X"])
    links.new(cirrus_y_add.outputs[0], family_scale.inputs["Y"])
    family_scale.inputs["Z"].default_value = 1.0
    family_view = nodes.new("ShaderNodeVectorMath")
    family_view.location = (-340, 320)
    family_view.operation = "MULTIPLY"
    links.new(view_norm.outputs["Vector"], family_view.inputs[0])
    links.new(family_scale.outputs["Vector"], family_view.inputs[1])

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

    # Horizon Offset (-0.9..0.9) truly shifts the horizon line in the frame.
    horizon_shift = nodes.new("ShaderNodeMath")
    horizon_shift.location = (-1180, 120)
    horizon_shift.operation = "MULTIPLY"
    horizon_shift.inputs[1].default_value = 0.22
    links.new(group_in.outputs["Horizon Offset"], horizon_shift.inputs[0])

    shifted_z = nodes.new("ShaderNodeMath")
    shifted_z.location = (-1000, 120)
    shifted_z.operation = "SUBTRACT"
    links.new(separate.outputs["Z"], shifted_z.inputs[0])
    links.new(horizon_shift.outputs[0], shifted_z.inputs[1])

    # Ground stays strictly below the shifted horizon.
    ground_blend = nodes.new("ShaderNodeMapRange")
    ground_blend.location = (-800, 340)
    ground_blend.clamp = True
    _smooth(ground_blend)
    ground_blend.inputs["From Min"].default_value = -0.08
    ground_blend.inputs["From Max"].default_value = 0.01
    links.new(shifted_z.outputs[0], ground_blend.inputs["Value"])

    # Sky dome height (0 at the shifted horizon, 1 at zenith).
    sky_z = nodes.new("ShaderNodeMapRange")
    sky_z.location = (-800, 140)
    sky_z.clamp = True
    sky_z.inputs["From Min"].default_value = 0.0
    sky_z.inputs["From Max"].default_value = 1.0
    links.new(shifted_z.outputs[0], sky_z.inputs["Value"])

    # Mid-sky bridge peak stays fixed because sky_z already shifts.
    mid_peak = nodes.new("ShaderNodeMath")
    mid_peak.location = (-440, 100)
    mid_peak.operation = "ADD"
    mid_peak.use_clamp = True
    mid_peak.inputs[0].default_value = 0.0
    mid_peak.inputs[1].default_value = 0.22

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
    accent_band.inputs["From Max"].default_value = 0.20
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

    disk_masked = nodes.new("ShaderNodeMath")
    disk_masked.location = (1240, 320)
    disk_masked.operation = "MULTIPLY"
    links.new(disk_scale.outputs[0], disk_masked.inputs[0])
    links.new(ground_blend.outputs["Result"], disk_masked.inputs[1])
    disk_color = nodes.new("ShaderNodeVectorMath")
    disk_color.location = (1420, 360)
    disk_color.operation = "SCALE"
    links.new(group_in.outputs["Sun Color"], disk_color.inputs["Vector"])
    links.new(disk_masked.outputs[0], disk_color.inputs["Scale"])

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

    # The family changes the vertical organization without changing the
    # coverage slider: Cumulus is billowy, Stratocumulus is flat, Cirrus is
    # stretched along the wind.
    cum_reduce = nodes.new("ShaderNodeMath")
    cum_reduce.location = (820, -520)
    cum_reduce.operation = "MULTIPLY"
    cum_reduce.inputs[1].default_value = 0.62
    links.new(group_in.outputs["Cloud Cumulus"], cum_reduce.inputs[0])
    and_flatness = nodes.new("ShaderNodeMath")
    and_flatness.location = (1000, -520)
    and_flatness.operation = "SUBTRACT"
    and_flatness.use_clamp = True
    links.new(group_in.outputs["Cloud Flatness"], and_flatness.inputs[0])
    links.new(cum_reduce.outputs[0], and_flatness.inputs[1])
    strat_bias = nodes.new("ShaderNodeMath")
    strat_bias.location = (820, -680)
    strat_bias.operation = "MULTIPLY"
    strat_bias.inputs[1].default_value = 0.20
    links.new(group_in.outputs["Cloud Stratocumulus"], strat_bias.inputs[0])
    strat_flatness = nodes.new("ShaderNodeMath")
    strat_flatness.location = (1000, -680)
    strat_flatness.operation = "ADD"
    strat_flatness.use_clamp = True
    links.new(and_flatness.outputs[0], strat_flatness.inputs[0])
    links.new(strat_bias.outputs[0], strat_flatness.inputs[1])
    vertical_reduce = nodes.new("ShaderNodeMath")
    vertical_reduce.location = (820, -820)
    vertical_reduce.operation = "MULTIPLY"
    vertical_reduce.inputs[1].default_value = 0.16
    links.new(group_in.outputs["Cloud Vertical"], vertical_reduce.inputs[0])
    family_flatness = nodes.new("ShaderNodeMath")
    family_flatness.location = (1180, -820)
    family_flatness.operation = "SUBTRACT"
    family_flatness.use_clamp = True
    links.new(strat_flatness.outputs[0], family_flatness.inputs[0])
    links.new(vertical_reduce.outputs[0], family_flatness.inputs[1])

    # Cloud Flatness: 0 = billowy cumuli, 0.65 = current strata,
    # 1 = strongly flat horizontal bands. At 0.65 this is exactly 3.2.
    flat_z = nodes.new("ShaderNodeMath")
    flat_z.location = (1000, -360)
    flat_z.operation = "MULTIPLY"
    flat_z.inputs[1].default_value = 3.0
    links.new(family_flatness.outputs[0], flat_z.inputs[0])

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
    links.new(family_flatness.outputs[0], flat_inv.inputs[1])

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

    contrail_white = nodes.new("ShaderNodeRGB")
    contrail_white.location = (3700, 960)
    contrail_white.outputs[0].default_value = (1.4, 1.4, 1.45, 1.0)

    contrail_color = nodes.new("ShaderNodeMix")
    contrail_color.location = (3880, 960)
    contrail_color.data_type = "RGBA"
    contrail_color.blend_type = "MIX"
    contrail_color.inputs["Factor"].default_value = 0.45
    a_sock, b_sock, result_sock = _rgba_sockets(contrail_color)
    links.new(contrail_white.outputs[0], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)

    contrail_add = nodes.new("ShaderNodeMix")
    contrail_add.location = (4060, 1000)
    contrail_add.data_type = "RGBA"
    contrail_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(contrail_add)
    links.new(sky_color, a_sock)
    links.new(contrail_color.outputs["Result"], b_sock)
    links.new(contrail_factor.outputs[0], contrail_add.inputs["Factor"])
    sky_color = result_sock

    rho_here, env_here, warped_pos = _sample_cloud_density(
        nodes, links, family_view.outputs["Vector"], group_in,
        flat_scale, flat_inv, y_offset=0.0,
        flatness_socket=family_flatness.outputs[0])

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
    family_view_sun = nodes.new("ShaderNodeVectorMath")
    family_view_sun.location = (2260, -900)
    family_view_sun.operation = "MULTIPLY"
    links.new(view_sun_norm.outputs["Vector"], family_view_sun.inputs[0])
    links.new(family_scale.outputs["Vector"], family_view_sun.inputs[1])

    rho_sun, env_sun, _warped_sun = _sample_cloud_density(
        nodes, links, family_view_sun.outputs["Vector"], group_in,
        flat_scale, flat_inv, y_offset=-1200.0,
        flatness_socket=family_flatness.outputs[0])

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
    sun_lighting = nodes.new("ShaderNodeMath")
    sun_lighting.location = (2620, -1020)
    sun_lighting.operation = "MULTIPLY"
    links.new(delta_used.outputs[0], sun_lighting.inputs[0])
    links.new(group_in.outputs["Cloud Sun Lighting"], sun_lighting.inputs[1])

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

    detail_edge_gain = nodes.new("ShaderNodeMath")
    detail_edge_gain.location = (2800, -1000)
    detail_edge_gain.operation = "MULTIPLY"
    detail_edge_gain.inputs[1].default_value = 0.030
    links.new(group_in.outputs["Cloud Detail"], detail_edge_gain.inputs[0])
    detail_body_gain = nodes.new("ShaderNodeMath")
    detail_body_gain.location = (2800, -1080)
    detail_body_gain.operation = "MULTIPLY"
    detail_body_gain.inputs[1].default_value = 0.017
    links.new(group_in.outputs["Cloud Detail"], detail_body_gain.inputs[0])
    detail_edge = nodes.new("ShaderNodeMath")
    detail_edge.location = (2980, -1140)
    detail_edge.operation = "MULTIPLY"
    links.new(detail_center.outputs[0], detail_edge.inputs[0])
    links.new(detail_edge_gain.outputs[0], detail_edge.inputs[1])

    detail_body = nodes.new("ShaderNodeMath")
    detail_body.location = (2980, -1260)
    detail_body.operation = "MULTIPLY"
    links.new(detail_center.outputs[0], detail_body.inputs[0])
    links.new(detail_body_gain.outputs[0], detail_body.inputs[1])

    rho_sculpted = nodes.new("ShaderNodeMath")
    rho_sculpted.location = (3160, -1080)
    rho_sculpted.operation = "ADD"
    rho_sculpted.use_clamp = True
    links.new(rho_here, rho_sculpted.inputs[0])
    links.new(detail_edge.outputs[0], rho_sculpted.inputs[1])

    breakup_amount = nodes.new("ShaderNodeMath")
    breakup_amount.location = (3340, -1200)
    breakup_amount.operation = "MULTIPLY"
    breakup_amount.inputs[1].default_value = 0.10
    links.new(group_in.outputs["Cloud Breakup"], breakup_amount.inputs[0])
    rho_break = nodes.new("ShaderNodeMath")
    rho_break.location = (3520, -1080)
    rho_break.operation = "SUBTRACT"
    rho_break.use_clamp = True
    links.new(rho_sculpted.outputs[0], rho_break.inputs[0])
    links.new(breakup_amount.outputs[0], rho_break.inputs[1])
    cirrus_thin = nodes.new("ShaderNodeMath")
    cirrus_thin.location = (3340, -1340)
    cirrus_thin.operation = "MULTIPLY"
    cirrus_thin.inputs[1].default_value = 0.05
    links.new(group_in.outputs["Cloud Cirrus"], cirrus_thin.inputs[0])
    cirrus_gain = nodes.new("ShaderNodeMath")
    cirrus_gain.location = (3520, -1340)
    cirrus_gain.operation = "SUBTRACT"
    cirrus_gain.use_clamp = True
    cirrus_gain.inputs[0].default_value = 1.0
    links.new(cirrus_thin.outputs[0], cirrus_gain.inputs[1])
    rho_family = nodes.new("ShaderNodeMath")
    rho_family.location = (3700, -1200)
    rho_family.operation = "MULTIPLY"
    rho_family.use_clamp = True
    links.new(rho_break.outputs[0], rho_family.inputs[0])
    links.new(cirrus_gain.outputs[0], rho_family.inputs[1])

    body_signal = nodes.new("ShaderNodeMath")
    body_signal.location = (3160, -900)
    body_signal.operation = "ADD"
    links.new(sun_lighting.outputs[0], body_signal.inputs[0])
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
    links.new(rho_family.outputs[0], coverage.inputs["Value"])

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
    body_mix.inputs["From Min"].default_value = -0.030
    body_mix.inputs["From Max"].default_value = 0.004
    body_mix.inputs["To Min"].default_value = 0.0
    body_mix.inputs["To Max"].default_value = 1.0
    links.new(body_signal.outputs[0], body_mix.inputs["Value"])

    height_tone = nodes.new("ShaderNodeMapRange")
    height_tone.location = (2620, -840)
    height_tone.clamp = True
    _smooth(height_tone)
    height_tone.inputs["From Min"].default_value = 0.0
    height_tone.inputs["From Max"].default_value = 0.32
    height_tone.inputs["To Min"].default_value = 0.62
    height_tone.inputs["To Max"].default_value = 1.0
    links.new(shifted_z.outputs[0], height_tone.inputs["Value"])
    body_tone = nodes.new("ShaderNodeMath")
    body_tone.location = (2800, -760)
    body_tone.operation = "MULTIPLY"
    body_tone.use_clamp = True
    links.new(body_mix.outputs["Result"], body_tone.inputs[0])
    links.new(height_tone.outputs["Result"], body_tone.inputs[1])

    fringe = nodes.new("ShaderNodeMapRange")
    fringe.location = (2440, -540)
    fringe.clamp = True
    _smooth(fringe)
    fringe.inputs["To Min"].default_value = 1.0
    fringe.inputs["To Max"].default_value = 0.0
    links.new(coverage_center.outputs["Result"], fringe.inputs["From Min"])
    links.new(fringe_top.outputs[0], fringe.inputs["From Max"])
    links.new(rho_family.outputs[0], fringe.inputs["Value"])

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

    # Sun Scatter boosts the silver lining on the side facing the sun. It
    # changes only the rim mix, not the cloud body or the clear sky.
    scatter_positive = nodes.new("ShaderNodeMath")
    scatter_positive.location = (3400, -1040)
    scatter_positive.operation = "MAXIMUM"
    scatter_positive.inputs[1].default_value = 0.0
    links.new(dot.outputs["Value"], scatter_positive.inputs[0])

    scatter_phase = nodes.new("ShaderNodeMath")
    scatter_phase.location = (3580, -1040)
    scatter_phase.operation = "POWER"
    scatter_phase.inputs[1].default_value = 4.0
    links.new(scatter_positive.outputs[0], scatter_phase.inputs[0])

    scatter_amount = nodes.new("ShaderNodeMath")
    scatter_amount.location = (3760, -1040)
    scatter_amount.operation = "MULTIPLY"
    links.new(scatter_phase.outputs[0], scatter_amount.inputs[0])
    links.new(group_in.outputs["Cloud Sun Scatter"],
              scatter_amount.inputs[1])

    scatter_boost = nodes.new("ShaderNodeMath")
    scatter_boost.location = (3940, -1040)
    scatter_boost.operation = "MULTIPLY"
    links.new(scatter_amount.outputs[0], scatter_boost.inputs[0])
    scatter_boost.inputs[1].default_value = 0.8

    scatter_one = nodes.new("ShaderNodeMath")
    scatter_one.location = (4120, -1040)
    scatter_one.operation = "ADD"
    links.new(scatter_boost.outputs[0], scatter_one.inputs[0])
    scatter_one.inputs[1].default_value = 1.0

    rim_scatter = nodes.new("ShaderNodeMath")
    rim_scatter.location = (4300, -1040)
    rim_scatter.operation = "MULTIPLY"
    rim_scatter.use_clamp = True
    links.new(rim_boosted.outputs[0], rim_scatter.inputs[0])
    links.new(scatter_one.outputs[0], rim_scatter.inputs[1])

    mix_body = nodes.new("ShaderNodeMix")
    mix_body.location = (2800, -720)
    mix_body.data_type = "RGBA"
    mix_body.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_body)
    links.new(group_in.outputs["Cloud Shadow"], a_sock)
    links.new(group_in.outputs["Cloud Mid"], b_sock)
    links.new(body_tone.outputs[0], mix_body.inputs["Factor"])

    mix_light = nodes.new("ShaderNodeMix")
    mix_light.location = (2980, -680)
    mix_light.data_type = "RGBA"
    mix_light.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mix_light)
    links.new(mix_body.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)
    links.new(rim_scatter.outputs[0], mix_light.inputs["Factor"])

    horizon = nodes.new("ShaderNodeMapRange")
    horizon.location = (1440, 700)
    horizon.clamp = True
    _smooth(horizon)
    horizon.inputs["From Min"].default_value = 0.015
    horizon.inputs["From Max"].default_value = 0.16
    links.new(shifted_z.outputs[0], horizon.inputs["Value"])

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

    # Anti-aliased pinpoint starfield: existence, magnitude and temperature
    # use independent Voronoi Color channels, so no star is sub-pixel or dim.
    cluster_noise = nodes.new("ShaderNodeTexNoise")
    cluster_noise.location = (1880, -360)
    cluster_noise.inputs["Scale"].default_value = 2.2
    cluster_noise.inputs["Detail"].default_value = 3.0
    cluster_noise.inputs["Roughness"].default_value = 0.55
    cluster_noise.inputs["Distortion"].default_value = 0.35
    links.new(view_norm.outputs["Vector"], cluster_noise.inputs["Vector"])

    cluster_mask = nodes.new("ShaderNodeMapRange")
    cluster_mask.location = (2060, -360)
    cluster_mask.clamp = True
    _smooth(cluster_mask)
    cluster_mask.inputs["From Min"].default_value = 0.28
    cluster_mask.inputs["From Max"].default_value = 0.65
    cluster_mask.inputs["To Min"].default_value = 0.55
    cluster_mask.inputs["To Max"].default_value = 1.0
    links.new(cluster_noise.outputs["Fac"], cluster_mask.inputs["Value"])

    # Tier 1: anti-subpixel stardust with guaranteed magnitude.
    star1_scale = nodes.new("ShaderNodeMath")
    star1_scale.location = (1880, -560)
    star1_scale.operation = "MULTIPLY"
    star1_scale.inputs[1].default_value = 1.30
    links.new(group_in.outputs["Star Density"], star1_scale.inputs[0])

    vor1 = nodes.new("ShaderNodeTexVoronoi")
    vor1.location = (2060, -560)
    links.new(view_norm.outputs["Vector"], vor1.inputs["Vector"])
    links.new(star1_scale.outputs[0], vor1.inputs["Scale"])

    vor1_rand = nodes.new("ShaderNodeSeparateXYZ")
    vor1_rand.location = (2240, -560)
    links.new(vor1.outputs["Color"], vor1_rand.inputs["Vector"])

    star1_spot = nodes.new("ShaderNodeMapRange")
    star1_spot.location = (2420, -560)
    star1_spot.clamp = True
    _smooth(star1_spot)
    star1_spot.inputs["From Min"].default_value = 0.0
    star1_spot.inputs["From Max"].default_value = 0.115
    star1_spot.inputs["To Min"].default_value = 1.0
    star1_spot.inputs["To Max"].default_value = 0.0
    links.new(vor1.outputs["Distance"], star1_spot.inputs["Value"])

    star1_sharp = nodes.new("ShaderNodeMath")
    star1_sharp.location = (2600, -560)
    star1_sharp.operation = "POWER"
    star1_sharp.inputs[1].default_value = 1.8
    links.new(star1_spot.outputs["Result"], star1_sharp.inputs[0])

    star1_exist = nodes.new("ShaderNodeMapRange")
    star1_exist.location = (2420, -720)
    star1_exist.clamp = True
    _smooth(star1_exist)
    star1_exist.inputs["From Min"].default_value = 0.68
    star1_exist.inputs["From Max"].default_value = 0.73
    star1_exist.inputs["To Min"].default_value = 0.0
    star1_exist.inputs["To Max"].default_value = 1.0
    links.new(vor1_rand.outputs["X"], star1_exist.inputs["Value"])

    star1_mag = nodes.new("ShaderNodeMapRange")
    star1_mag.location = (2420, -880)
    star1_mag.clamp = True
    _smooth(star1_mag)
    star1_mag.inputs["From Min"].default_value = 0.0
    star1_mag.inputs["From Max"].default_value = 1.0
    star1_mag.inputs["To Min"].default_value = 0.35
    star1_mag.inputs["To Max"].default_value = 0.85
    links.new(vor1_rand.outputs["Y"], star1_mag.inputs["Value"])

    tier1_exist_mag = nodes.new("ShaderNodeMath")
    tier1_exist_mag.location = (2600, -800)
    tier1_exist_mag.operation = "MULTIPLY"
    tier1_exist_mag.use_clamp = True
    links.new(star1_exist.outputs["Result"], tier1_exist_mag.inputs[0])
    links.new(star1_mag.outputs["Result"], tier1_exist_mag.inputs[1])

    tier1_raw = nodes.new("ShaderNodeMath")
    tier1_raw.location = (2780, -620)
    tier1_raw.operation = "MULTIPLY"
    tier1_raw.use_clamp = True
    links.new(star1_sharp.outputs[0], tier1_raw.inputs[0])
    links.new(tier1_exist_mag.outputs[0], tier1_raw.inputs[1])

    tier1_stars = nodes.new("ShaderNodeMath")
    tier1_stars.location = (2960, -620)
    tier1_stars.operation = "MULTIPLY"
    tier1_stars.use_clamp = True
    links.new(tier1_raw.outputs[0], tier1_stars.inputs[0])
    links.new(cluster_mask.outputs["Result"], tier1_stars.inputs[1])

    # Tier 2: brighter constellation stars on a translated grid.
    view_offset_2 = nodes.new("ShaderNodeVectorMath")
    view_offset_2.location = (1880, -900)
    view_offset_2.operation = "ADD"
    view_offset_2.inputs[1].default_value = (1.73, -2.41, 0.89)
    links.new(view_norm.outputs["Vector"], view_offset_2.inputs[0])

    star2_scale = nodes.new("ShaderNodeMath")
    star2_scale.location = (1880, -1060)
    star2_scale.operation = "MULTIPLY"
    star2_scale.inputs[1].default_value = 0.72
    links.new(group_in.outputs["Star Density"], star2_scale.inputs[0])

    vor2 = nodes.new("ShaderNodeTexVoronoi")
    vor2.location = (2060, -900)
    links.new(view_offset_2.outputs["Vector"], vor2.inputs["Vector"])
    links.new(star2_scale.outputs[0], vor2.inputs["Scale"])

    vor2_rand = nodes.new("ShaderNodeSeparateXYZ")
    vor2_rand.location = (2240, -900)
    links.new(vor2.outputs["Color"], vor2_rand.inputs["Vector"])

    star2_spot = nodes.new("ShaderNodeMapRange")
    star2_spot.location = (2420, -900)
    star2_spot.clamp = True
    _smooth(star2_spot)
    star2_spot.inputs["From Min"].default_value = 0.0
    star2_spot.inputs["From Max"].default_value = 0.105
    star2_spot.inputs["To Min"].default_value = 1.0
    star2_spot.inputs["To Max"].default_value = 0.0
    links.new(vor2.outputs["Distance"], star2_spot.inputs["Value"])

    star2_sharp = nodes.new("ShaderNodeMath")
    star2_sharp.location = (2600, -900)
    star2_sharp.operation = "POWER"
    star2_sharp.inputs[1].default_value = 1.8
    links.new(star2_spot.outputs["Result"], star2_sharp.inputs[0])

    star2_exist = nodes.new("ShaderNodeMapRange")
    star2_exist.location = (2420, -1060)
    star2_exist.clamp = True
    _smooth(star2_exist)
    star2_exist.inputs["From Min"].default_value = 0.76
    star2_exist.inputs["From Max"].default_value = 0.80
    star2_exist.inputs["To Min"].default_value = 0.0
    star2_exist.inputs["To Max"].default_value = 1.0
    links.new(vor2_rand.outputs["X"], star2_exist.inputs["Value"])

    star2_mag = nodes.new("ShaderNodeMapRange")
    star2_mag.location = (2420, -1220)
    star2_mag.clamp = True
    _smooth(star2_mag)
    star2_mag.inputs["From Min"].default_value = 0.0
    star2_mag.inputs["From Max"].default_value = 1.0
    star2_mag.inputs["To Min"].default_value = 0.60
    star2_mag.inputs["To Max"].default_value = 1.0
    links.new(vor2_rand.outputs["Y"], star2_mag.inputs["Value"])

    tier2_exist_mag = nodes.new("ShaderNodeMath")
    tier2_exist_mag.location = (2600, -1140)
    tier2_exist_mag.operation = "MULTIPLY"
    tier2_exist_mag.use_clamp = True
    links.new(star2_exist.outputs["Result"], tier2_exist_mag.inputs[0])
    links.new(star2_mag.outputs["Result"], tier2_exist_mag.inputs[1])

    tier2_raw = nodes.new("ShaderNodeMath")
    tier2_raw.location = (2780, -960)
    tier2_raw.operation = "MULTIPLY"
    tier2_raw.use_clamp = True
    links.new(star2_sharp.outputs[0], tier2_raw.inputs[0])
    links.new(tier2_exist_mag.outputs[0], tier2_raw.inputs[1])

    tier2_stars = nodes.new("ShaderNodeMath")
    tier2_stars.location = (2960, -960)
    tier2_stars.operation = "MULTIPLY"
    tier2_stars.use_clamp = True
    links.new(tier2_raw.outputs[0], tier2_stars.inputs[0])
    links.new(cluster_mask.outputs["Result"], tier2_stars.inputs[1])

    # Tier 3: hero stars with a tight Airy skirt.
    view_offset_3 = nodes.new("ShaderNodeVectorMath")
    view_offset_3.location = (1880, -1400)
    view_offset_3.operation = "ADD"
    view_offset_3.inputs[1].default_value = (-3.14, 1.17, 2.65)
    links.new(view_norm.outputs["Vector"], view_offset_3.inputs[0])

    star3_scale = nodes.new("ShaderNodeMath")
    star3_scale.location = (1880, -1560)
    star3_scale.operation = "MULTIPLY"
    star3_scale.inputs[1].default_value = 0.36
    links.new(group_in.outputs["Star Density"], star3_scale.inputs[0])

    vor3 = nodes.new("ShaderNodeTexVoronoi")
    vor3.location = (2060, -1400)
    links.new(view_offset_3.outputs["Vector"], vor3.inputs["Vector"])
    links.new(star3_scale.outputs[0], vor3.inputs["Scale"])

    vor3_rand = nodes.new("ShaderNodeSeparateXYZ")
    vor3_rand.location = (2240, -1400)
    links.new(vor3.outputs["Color"], vor3_rand.inputs["Vector"])

    hero_core = nodes.new("ShaderNodeMapRange")
    hero_core.location = (2420, -1400)
    hero_core.clamp = True
    _smooth(hero_core)
    hero_core.inputs["From Min"].default_value = 0.0
    hero_core.inputs["From Max"].default_value = 0.085
    hero_core.inputs["To Min"].default_value = 1.0
    hero_core.inputs["To Max"].default_value = 0.0
    links.new(vor3.outputs["Distance"], hero_core.inputs["Value"])

    hero_core_sharp = nodes.new("ShaderNodeMath")
    hero_core_sharp.location = (2600, -1400)
    hero_core_sharp.operation = "POWER"
    hero_core_sharp.inputs[1].default_value = 1.7
    links.new(hero_core.outputs["Result"], hero_core_sharp.inputs[0])

    hero_skirt = nodes.new("ShaderNodeMapRange")
    hero_skirt.location = (2420, -1560)
    hero_skirt.clamp = True
    _smooth(hero_skirt)
    hero_skirt.inputs["From Min"].default_value = 0.0
    hero_skirt.inputs["From Max"].default_value = 0.16
    hero_skirt.inputs["To Min"].default_value = 0.14
    hero_skirt.inputs["To Max"].default_value = 0.0
    links.new(vor3.outputs["Distance"], hero_skirt.inputs["Value"])

    hero_shape = nodes.new("ShaderNodeMath")
    hero_shape.location = (2780, -1480)
    hero_shape.operation = "ADD"
    hero_shape.use_clamp = True
    links.new(hero_core_sharp.outputs[0], hero_shape.inputs[0])
    links.new(hero_skirt.outputs["Result"], hero_shape.inputs[1])

    hero_exist = nodes.new("ShaderNodeMapRange")
    hero_exist.location = (2420, -1720)
    hero_exist.clamp = True
    _smooth(hero_exist)
    hero_exist.inputs["From Min"].default_value = 0.84
    hero_exist.inputs["From Max"].default_value = 0.88
    hero_exist.inputs["To Min"].default_value = 0.0
    hero_exist.inputs["To Max"].default_value = 1.0
    links.new(vor3_rand.outputs["X"], hero_exist.inputs["Value"])

    tier3_stars = nodes.new("ShaderNodeMath")
    tier3_stars.location = (2960, -1560)
    tier3_stars.operation = "MULTIPLY"
    tier3_stars.use_clamp = True
    links.new(hero_shape.outputs[0], tier3_stars.inputs[0])
    links.new(hero_exist.outputs["Result"], tier3_stars.inputs[1])

    star_sum_12 = nodes.new("ShaderNodeMath")
    star_sum_12.location = (3140, -760)
    star_sum_12.operation = "MAXIMUM"
    star_sum_12.use_clamp = True
    links.new(tier1_stars.outputs[0], star_sum_12.inputs[0])
    links.new(tier2_stars.outputs[0], star_sum_12.inputs[1])

    star_total = nodes.new("ShaderNodeMath")
    star_total.location = (3320, -760)
    star_total.operation = "MAXIMUM"
    star_total.use_clamp = True
    links.new(star_sum_12.outputs[0], star_total.inputs[0])
    links.new(tier3_stars.outputs[0], star_total.inputs[1])

    # Atmospheric masks: zenith, solar disk, and cloud coverage.
    zenith = nodes.new("ShaderNodeMapRange")
    zenith.location = (2060, -400)
    zenith.clamp = True
    _smooth(zenith)
    zenith.inputs["From Min"].default_value = 0.06
    zenith.inputs["From Max"].default_value = 0.28
    links.new(shifted_z.outputs[0], zenith.inputs["Value"])

    sun_hide = nodes.new("ShaderNodeMapRange")
    sun_hide.location = (2240, -400)
    sun_hide.clamp = True
    _smooth(sun_hide)
    sun_hide.inputs["From Min"].default_value = 0.95
    sun_hide.inputs["From Max"].default_value = 0.995
    sun_hide.inputs["To Min"].default_value = 1.0
    sun_hide.inputs["To Max"].default_value = 0.0
    links.new(dot.outputs["Value"], sun_hide.inputs["Value"])

    star_mask_a = nodes.new("ShaderNodeMath")
    star_mask_a.location = (3500, -760)
    star_mask_a.operation = "MULTIPLY"
    star_mask_a.use_clamp = True
    links.new(star_total.outputs[0], star_mask_a.inputs[0])
    links.new(zenith.outputs["Result"], star_mask_a.inputs[1])

    star_mask_b = nodes.new("ShaderNodeMath")
    star_mask_b.location = (3680, -760)
    star_mask_b.operation = "MULTIPLY"
    star_mask_b.use_clamp = True
    links.new(star_mask_a.outputs[0], star_mask_b.inputs[0])
    links.new(sun_hide.outputs["Result"], star_mask_b.inputs[1])

    cloud_hide = nodes.new("ShaderNodeMath")
    cloud_hide.location = (3500, -980)
    cloud_hide.operation = "SUBTRACT"
    cloud_hide.use_clamp = True
    cloud_hide.inputs[0].default_value = 1.0
    links.new(cloud_amount_node.outputs[0], cloud_hide.inputs[1])

    star_mask_c = nodes.new("ShaderNodeMath")
    star_mask_c.location = (3860, -760)
    star_mask_c.operation = "MULTIPLY"
    star_mask_c.use_clamp = True
    links.new(star_mask_b.outputs[0], star_mask_c.inputs[0])
    links.new(cloud_hide.outputs[0], star_mask_c.inputs[1])

    star_amount = nodes.new("ShaderNodeMath")
    star_amount.location = (4040, -760)
    star_amount.operation = "MULTIPLY"
    star_amount.use_clamp = True
    links.new(star_mask_c.outputs[0], star_amount.inputs[0])
    links.new(group_in.outputs["Star Amount"], star_amount.inputs[1])

    # Per-cell temperature: warm gold to cool ice, then 25% Cloud Light tint.
    star_warm_rgb = nodes.new("ShaderNodeRGB")
    star_warm_rgb.location = (3140, -1160)
    star_warm_rgb.outputs[0].default_value = (1.0, 0.91, 0.78, 1.0)

    star_cool_rgb = nodes.new("ShaderNodeRGB")
    star_cool_rgb.location = (3140, -1300)
    star_cool_rgb.outputs[0].default_value = (0.78, 0.91, 1.0, 1.0)

    star_temp_mix = nodes.new("ShaderNodeMix")
    star_temp_mix.location = (3320, -1220)
    star_temp_mix.data_type = "RGBA"
    star_temp_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(star_temp_mix)
    links.new(star_warm_rgb.outputs[0], a_sock)
    links.new(star_cool_rgb.outputs[0], b_sock)
    links.new(vor1_rand.outputs["Z"], star_temp_mix.inputs["Factor"])

    star_tint_mix = nodes.new("ShaderNodeMix")
    star_tint_mix.location = (3500, -1220)
    star_tint_mix.data_type = "RGBA"
    star_tint_mix.blend_type = "MIX"
    star_tint_mix.inputs["Factor"].default_value = 0.25
    a_sock, b_sock, result_sock = _rgba_sockets(star_tint_mix)
    links.new(star_temp_mix.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)

    star_tint_scale = nodes.new("ShaderNodeVectorMath")
    star_tint_scale.location = (3680, -1220)
    star_tint_scale.operation = "SCALE"
    star_tint_scale.inputs["Scale"].default_value = 12.0
    links.new(star_tint_mix.outputs["Result"], star_tint_scale.inputs["Vector"])

    star_mix = nodes.new("ShaderNodeMix")
    star_mix.location = (4220, -200)
    star_mix.data_type = "RGBA"
    star_mix.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(star_mix)
    links.new(cloud_mix.outputs["Result"], a_sock)
    links.new(star_tint_scale.outputs["Vector"], b_sock)
    links.new(star_amount.outputs[0], star_mix.inputs["Factor"])
    sky_color = star_mix.outputs["Result"]

    # Local tangent basis on the sky sphere: continuous at 360 degrees.
    neg_vy = nodes.new("ShaderNodeMath")
    neg_vy.location = (1700, -1880)
    neg_vy.operation = "MULTIPLY"
    neg_vy.inputs[1].default_value = -1.0
    links.new(separate.outputs["Y"], neg_vy.inputs[0])

    tan_h_raw = nodes.new("ShaderNodeCombineXYZ")
    tan_h_raw.location = (1880, -1880)
    links.new(neg_vy.outputs[0], tan_h_raw.inputs["X"])
    links.new(separate.outputs["X"], tan_h_raw.inputs["Y"])

    tan_h = nodes.new("ShaderNodeVectorMath")
    tan_h.location = (2060, -1880)
    tan_h.operation = "NORMALIZE"
    links.new(tan_h_raw.outputs["Vector"], tan_h.inputs[0])

    tan_v_raw = nodes.new("ShaderNodeVectorMath")
    tan_v_raw.location = (2240, -1880)
    tan_v_raw.operation = "CROSS_PRODUCT"
    links.new(tan_h.outputs["Vector"], tan_v_raw.inputs[0])
    links.new(view_norm.outputs["Vector"], tan_v_raw.inputs[1])

    tan_v = nodes.new("ShaderNodeVectorMath")
    tan_v.location = (2420, -1880)
    tan_v.operation = "NORMALIZE"
    links.new(tan_v_raw.outputs["Vector"], tan_v.inputs[0])

    # Milky Way: a diagonal galactic river with a dark dust rift.
    mw_axis = nodes.new("ShaderNodeVectorMath")
    mw_axis.location = (1880, -1880)
    mw_axis.operation = "DOT_PRODUCT"
    mw_axis.inputs[1].default_value = (0.58, 0.34, -0.74)
    links.new(view_norm.outputs["Vector"], mw_axis.inputs[0])

    mw_warp_noise = nodes.new("ShaderNodeTexNoise")
    mw_warp_noise.location = (1880, -2040)
    mw_warp_noise.inputs["Scale"].default_value = 2.4
    mw_warp_noise.inputs["Detail"].default_value = 5.0
    mw_warp_noise.inputs["Roughness"].default_value = 0.56
    mw_warp_noise.inputs["Distortion"].default_value = 0.35
    links.new(view_norm.outputs["Vector"], mw_warp_noise.inputs["Vector"])

    mw_warp_centered = nodes.new("ShaderNodeMath")
    mw_warp_centered.location = (2060, -2040)
    mw_warp_centered.operation = "SUBTRACT"
    mw_warp_centered.inputs[1].default_value = 0.5
    links.new(mw_warp_noise.outputs["Fac"], mw_warp_centered.inputs[0])

    mw_warp_amt = nodes.new("ShaderNodeMath")
    mw_warp_amt.location = (2240, -2040)
    mw_warp_amt.operation = "MULTIPLY"
    mw_warp_amt.inputs[1].default_value = 0.22
    links.new(mw_warp_centered.outputs[0], mw_warp_amt.inputs[0])

    mw_d = nodes.new("ShaderNodeMath")
    mw_d.location = (2420, -1960)
    mw_d.operation = "ADD"
    links.new(mw_axis.outputs["Value"], mw_d.inputs[0])
    links.new(mw_warp_amt.outputs[0], mw_d.inputs[1])

    mw_abs_d = nodes.new("ShaderNodeMath")
    mw_abs_d.location = (2600, -1960)
    mw_abs_d.operation = "ABSOLUTE"
    links.new(mw_d.outputs[0], mw_abs_d.inputs[0])

    mw_outer = nodes.new("ShaderNodeMapRange")
    mw_outer.location = (2780, -1960)
    mw_outer.clamp = True
    _smooth(mw_outer)
    mw_outer.inputs["From Min"].default_value = 0.0
    mw_outer.inputs["From Max"].default_value = 0.26
    mw_outer.inputs["To Min"].default_value = 1.0
    mw_outer.inputs["To Max"].default_value = 0.0
    links.new(mw_abs_d.outputs[0], mw_outer.inputs["Value"])

    mw_detail_noise = nodes.new("ShaderNodeTexNoise")
    mw_detail_noise.location = (2780, -2120)
    mw_detail_noise.inputs["Scale"].default_value = 6.5
    mw_detail_noise.inputs["Detail"].default_value = 6.0
    mw_detail_noise.inputs["Roughness"].default_value = 0.62
    mw_detail_noise.inputs["Distortion"].default_value = 0.40
    links.new(view_norm.outputs["Vector"], mw_detail_noise.inputs["Vector"])

    mw_rift_width = nodes.new("ShaderNodeMath")
    mw_rift_width.location = (2960, -2120)
    mw_rift_width.operation = "MULTIPLY"
    mw_rift_width.inputs[1].default_value = 0.065
    links.new(mw_detail_noise.outputs["Fac"], mw_rift_width.inputs[0])

    mw_rift = nodes.new("ShaderNodeMapRange")
    mw_rift.location = (3140, -2120)
    mw_rift.clamp = True
    _smooth(mw_rift)
    mw_rift.inputs["From Min"].default_value = 0.008
    mw_rift.inputs["To Min"].default_value = 0.12
    mw_rift.inputs["To Max"].default_value = 1.0
    links.new(mw_abs_d.outputs[0], mw_rift.inputs["Value"])
    links.new(mw_rift_width.outputs[0], mw_rift.inputs["From Max"])

    mw_clouds = nodes.new("ShaderNodeMapRange")
    mw_clouds.location = (3140, -2280)
    mw_clouds.clamp = True
    _smooth(mw_clouds)
    mw_clouds.inputs["From Min"].default_value = 0.25
    mw_clouds.inputs["From Max"].default_value = 0.78
    mw_clouds.inputs["To Min"].default_value = 0.35
    mw_clouds.inputs["To Max"].default_value = 1.0
    links.new(mw_detail_noise.outputs["Fac"], mw_clouds.inputs["Value"])

    mw_band1 = nodes.new("ShaderNodeMath")
    mw_band1.location = (3320, -2040)
    mw_band1.operation = "MULTIPLY"
    mw_band1.use_clamp = True
    links.new(mw_outer.outputs["Result"], mw_band1.inputs[0])
    links.new(mw_rift.outputs["Result"], mw_band1.inputs[1])

    mw_band = nodes.new("ShaderNodeMath")
    mw_band.location = (3500, -2040)
    mw_band.operation = "MULTIPLY"
    mw_band.use_clamp = True
    links.new(mw_band1.outputs[0], mw_band.inputs[0])
    links.new(mw_clouds.outputs["Result"], mw_band.inputs[1])

    mw_mask1 = nodes.new("ShaderNodeMath")
    mw_mask1.location = (3680, -2040)
    mw_mask1.operation = "MULTIPLY"
    mw_mask1.use_clamp = True
    links.new(mw_band.outputs[0], mw_mask1.inputs[0])
    links.new(zenith.outputs["Result"], mw_mask1.inputs[1])

    mw_mask = nodes.new("ShaderNodeMath")
    mw_mask.location = (3860, -2040)
    mw_mask.operation = "MULTIPLY"
    mw_mask.use_clamp = True
    links.new(mw_mask1.outputs[0], mw_mask.inputs[0])
    links.new(cloud_hide.outputs[0], mw_mask.inputs[1])

    mw_mask_amt = nodes.new("ShaderNodeMath")
    mw_mask_amt.location = (4040, -2040)
    mw_mask_amt.operation = "MULTIPLY"
    mw_mask_amt.use_clamp = True
    links.new(mw_mask.outputs[0], mw_mask_amt.inputs[0])
    links.new(group_in.outputs["Milky Way"], mw_mask_amt.inputs[1])

    mw_star_boost = nodes.new("ShaderNodeMath")
    mw_star_boost.location = (4040, -2200)
    mw_star_boost.operation = "MULTIPLY"
    mw_star_boost.use_clamp = True
    mw_star_boost.inputs[1].default_value = 0.65
    links.new(mw_outer.outputs["Result"], mw_star_boost.inputs[0])

    mw_star_boost2 = nodes.new("ShaderNodeMath")
    mw_star_boost2.location = (4220, -2200)
    mw_star_boost2.operation = "MULTIPLY"
    mw_star_boost2.use_clamp = True
    links.new(mw_star_boost.outputs[0], mw_star_boost2.inputs[0])
    links.new(group_in.outputs["Milky Way"], mw_star_boost2.inputs[1])

    cluster_total = nodes.new("ShaderNodeMath")
    cluster_total.location = (4400, -2200)
    cluster_total.operation = "ADD"
    cluster_total.use_clamp = True
    links.new(cluster_mask.outputs["Result"], cluster_total.inputs[0])
    links.new(mw_star_boost2.outputs[0], cluster_total.inputs[1])
    for link in list(tier1_stars.inputs[1].links):
        links.remove(link)
    links.new(cluster_total.outputs[0], tier1_stars.inputs[1])
    for link in list(tier2_stars.inputs[1].links):
        links.remove(link)
    links.new(cluster_total.outputs[0], tier2_stars.inputs[1])

    mw_cyan = nodes.new("ShaderNodeRGB")
    mw_cyan.location = (3320, -2280)
    mw_cyan.outputs[0].default_value = (0.06, 0.58, 0.95, 1.0)

    mw_violet = nodes.new("ShaderNodeRGB")
    mw_violet.location = (3320, -2440)
    mw_violet.outputs[0].default_value = (0.16, 0.08, 0.52, 1.0)

    mw_color_mix = nodes.new("ShaderNodeMix")
    mw_color_mix.location = (3500, -2360)
    mw_color_mix.data_type = "RGBA"
    mw_color_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(mw_color_mix)
    links.new(mw_cyan.outputs[0], a_sock)
    links.new(mw_violet.outputs[0], b_sock)
    links.new(mw_detail_noise.outputs["Fac"], mw_color_mix.inputs["Factor"])

    mw_color_tint = nodes.new("ShaderNodeMix")
    mw_color_tint.location = (3680, -2360)
    mw_color_tint.data_type = "RGBA"
    mw_color_tint.blend_type = "MIX"
    mw_color_tint.inputs["Factor"].default_value = 0.20
    a_sock, b_sock, result_sock = _rgba_sockets(mw_color_tint)
    links.new(mw_color_mix.outputs["Result"], a_sock)
    links.new(group_in.outputs["Cloud Light"], b_sock)

    mw_color_scale = nodes.new("ShaderNodeVectorMath")
    mw_color_scale.location = (3860, -2360)
    mw_color_scale.operation = "SCALE"
    mw_color_scale.inputs["Scale"].default_value = 0.85
    links.new(mw_color_tint.outputs["Result"], mw_color_scale.inputs["Vector"])

    mw_mix = nodes.new("ShaderNodeMix")
    mw_mix.location = (4040, -200)
    mw_mix.data_type = "RGBA"
    mw_mix.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(mw_mix)
    links.new(sky_color, a_sock)
    links.new(mw_color_scale.outputs["Vector"], b_sock)
    links.new(mw_mask_amt.outputs[0], mw_mix.inputs["Factor"])
    sky_color = mw_mix.outputs["Result"]

    star_visibility = nodes.new("ShaderNodeMath")
    star_visibility.location = (2040, 1200)
    star_visibility.operation = "SUBTRACT"
    star_visibility.inputs[0].default_value = 1.0
    links.new(cloud_amount_node.outputs[0], star_visibility.inputs[1])
    star_color = _build_shooting_stars(nodes, links, group_in,
                                       star_visibility.outputs[0])
    star_add = nodes.new("ShaderNodeMix")
    star_add.location = (2800, 1200)
    star_add.data_type = "RGBA"
    star_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(star_add)
    links.new(sky_color, a_sock)
    links.new(star_color, b_sock)
    star_add.inputs["Factor"].default_value = 1.0
    sky_color = result_sock

    # Moon: drawn after the stars so the disk occludes them, and gated by the
    # same shifted horizon as the ground.
    moon_node = nodes.new("ShaderNodeGroup")
    moon_node.node_tree = moon_shader.build()
    moon_node.location = (2400, -700)
    links.new(view_norm.outputs["Vector"], moon_node.inputs["View"])
    links.new(cloud_amount_node.outputs[0],
              moon_node.inputs["Cloud Visibility"])
    for name in ("Moon Direction", "Moon Right", "Moon Up", "Moon Size",
                 "Moon Brightness", "Moon Color", "Moon Surface Detail",
                 "Moon Crater Strength", "Moon Surface Contrast",
                 "Moon Edge Softness", "Moon Glow", "Moon Halo Radius",
                 "Moon Halo Color", "Moon Seed", "Moon Light",
                 "Moon Earthshine", "Moon Enabled"):
        links.new(group_in.outputs[name], moon_node.inputs[name])

    # Tight horizon gate: the disk is cut at the horizon, not faded through
    # the ground. The gradient keeps its own wider ground blend.
    moon_gate = nodes.new("ShaderNodeMapRange")
    moon_gate.location = (2400, -980)
    moon_gate.clamp = True
    _smooth(moon_gate)
    moon_gate.inputs["From Min"].default_value = -0.005
    moon_gate.inputs["From Max"].default_value = 0.005
    links.new(shifted_z.outputs[0], moon_gate.inputs["Value"])

    moon_alpha = nodes.new("ShaderNodeMath")
    moon_alpha.location = (2600, -700)
    moon_alpha.operation = "MULTIPLY"
    moon_alpha.use_clamp = True
    links.new(moon_node.outputs["Alpha"], moon_alpha.inputs[0])
    links.new(moon_gate.outputs["Result"], moon_alpha.inputs[1])

    moon_color = nodes.new("ShaderNodeVectorMath")
    moon_color.location = (2600, -860)
    moon_color.operation = "SCALE"
    links.new(moon_node.outputs["Color"], moon_color.inputs[0])
    links.new(moon_gate.outputs["Result"], moon_color.inputs["Scale"])

    moon_mix = nodes.new("ShaderNodeMix")
    moon_mix.location = (2800, -720)
    moon_mix.data_type = "RGBA"
    moon_mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _rgba_sockets(moon_mix)
    links.new(sky_color, a_sock)
    links.new(moon_color.outputs["Vector"], b_sock)
    links.new(moon_alpha.outputs[0], moon_mix.inputs["Factor"])
    sky_color = result_sock

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
        settings.cloud_seed = int(p.get("cloud_seed", 17))
        settings.cloud_delta_gain = p.get("cloud_delta_gain", 1.0)
        settings.sun_glow = p.get("sun_glow", 0.45)
        settings.sun_glow_enabled = p.get("sun_glow_enabled", True)
        settings.god_rays = p.get("god_rays", False)
        settings.sky_accent = p.get("sky_accent", (0.05, 0.32, 0.42))
        settings.sky_accent_amount = p.get("sky_accent_amount", 0.0)
        settings.horizon_offset = p.get("horizon_offset", 0.0)
        settings.horizon_softness = p.get("horizon_softness", 0.5)
        settings.contrails = p.get("contrails", 0.0)
        settings.world_gradient = p.get("world_gradient", True)
        settings.sun_disk = p.get("sun_disk", True)
        settings.sun_disk_size = p.get("sun_disk_size", 1.0)
        settings.sun_disk_strength = p.get("sun_disk_strength", 4.0)
        settings.clouds = p.get("clouds", True)
        settings.cloud_wind = p.get("cloud_wind", 0.0)
        settings.cloud_type = p.get("cloud_type", "CUMULUS")
        settings.cloud_vertical = p.get("cloud_vertical", 0.55)
        settings.cloud_breakup = p.get("cloud_breakup", 0.35)
        settings.cloud_detail = p.get("cloud_detail", 0.60)
        settings.cloud_sun_lighting = p.get("cloud_sun_lighting", 1.2)
        settings.stars = p.get("stars", True)
        settings.star_strength = p.get("star_amount", 0.0)
        settings.star_density = p.get("star_density", 180.0)
        settings.milky_way = p.get("milky_way", 0.0)
    finally:
        _syncing_style = False


def sync_custom_colors(settings, p):
    """Sync all custom color fields behind the style guard."""
    global _syncing_style
    if settings is None:
        return
    was_syncing = _syncing_style
    _syncing_style = True
    try:
        settings.custom_sky = p["sky_color"]
        settings.custom_horizon = p["horizon_color"]
        settings.custom_sun = p["sun_color"]
        settings.custom_shadow = p["shadow_tint"]
        settings.custom_cloud_shadow = p["cloud_shadow"]
        settings.custom_cloud_mid = p["cloud_mid"]
        settings.custom_cloud_light = p["cloud_light"]
    finally:
        _syncing_style = was_syncing


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
    from . import identity
    owner = sun.get(SUN_OWNER_TAG)
    foreign = bool(owner) and owner != identity.scene_id(scene)
    if foreign or len(sun.users_scene) > 1:
        # A sun shared with another scene is never rotated here: the copy owns
        # its own sun after ownership.repair, a plain scene copy does not.
        return
    sun.rotation_euler = rotation_from_angles(elevation, azimuth)
    from . import cameras
    cameras.update_transforms(scene, force=True)
    update_sun_controls(scene)
    if getattr(settings, "moon_enabled", False):
        update_moon_controls(scene)


def _scene_seconds(scene):
    """The time of the scene in seconds, independent of the frame rate."""
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    return (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)


def _cloud_offset(scene, settings):
    """The drift of the clouds, expressed in seconds and not in frames."""
    wind = getattr(settings, "cloud_wind", 0.0) if settings else 0.0
    seconds = _scene_seconds(scene)
    return (seconds * wind * 0.02, seconds * wind * 0.005, 0.0)


def _smoothstep(edge0, edge1, value):
    span = max(edge1 - edge0, 1e-6)
    t = max(0.0, min(1.0, (value - edge0) / span))
    return t * t * (3.0 - 2.0 * t)


def _sun_fade(direction):
    """The disk and glow response when the Sun crosses the horizon."""
    if direction is None:
        return 0.0, 0.0
    height = float(direction[2])
    return (_smoothstep(-0.015, 0.02, height),
            _smoothstep(-0.12, 0.02, height))


def _star_angles(event):
    """Start and end azimuth/elevation (degrees) of a shooting star."""
    azimuth = math.radians(float(event.azimuth))
    elevation = math.radians(float(event.elevation))
    direction = math.radians(float(event.direction))
    length = math.radians(max(0.5, float(event.length)))
    start = Vector((math.cos(elevation) * math.sin(azimuth),
                    math.cos(elevation) * math.cos(azimuth),
                    math.sin(elevation))).normalized()
    east = Vector((math.cos(azimuth), -math.sin(azimuth), 0.0)).normalized()
    north = Vector((-math.sin(azimuth) * math.sin(elevation),
                    -math.cos(azimuth) * math.sin(elevation),
                    math.cos(elevation))).normalized()
    tangent = east * math.cos(direction) + north * math.sin(direction)
    end = (start * math.cos(length) + tangent * math.sin(length)).normalized()

    def angles(vector):
        return (math.degrees(math.atan2(vector.x, vector.y)),
                math.degrees(math.asin(max(-1.0, min(1.0, vector.z)))))

    return angles(start) + angles(end)


def _apply_star_slots(scene, settings, node):
    events = list(getattr(settings, "shooting_star_events", []))
    for index in range(4):
        prefix = "Star%d " % index
        event = events[index] if index < len(events) else None
        if event is None:
            node.inputs[prefix + "Brightness"].default_value = 0.0
            node.inputs[prefix + "Enabled"].default_value = 0.0
            continue
        start_az, start_el, end_az, end_el = _star_angles(event)
        node.inputs[prefix + "Start U"].default_value = start_az
        node.inputs[prefix + "Start V"].default_value = start_el
        node.inputs[prefix + "End U"].default_value = end_az
        node.inputs[prefix + "End V"].default_value = end_el
        node.inputs[prefix + "Start Frame"].default_value = float(
            event.start_frame)
        node.inputs[prefix + "Duration"].default_value = float(
            max(2, event.duration))
        node.inputs[prefix + "Trail"].default_value = float(event.trail)
        node.inputs[prefix + "Thickness"].default_value = min(
            float(event.thickness), 0.01)
        node.inputs[prefix + "Curvature"].default_value = float(
            getattr(event, "curvature", 0.0))
        node.inputs[prefix + "Brightness"].default_value = float(
            event.brightness)
        node.inputs[prefix + "Glow"].default_value = float(event.glow)
        node.inputs[prefix + "Enabled"].default_value = (
            1.0 if event.enabled else 0.0)
        color = tuple(event.color)
        node.inputs[prefix + "Color"].default_value = (
            color[0], color[1], color[2], 1.0)


def _apply_gradient(scene, settings, nt, background, p):
    enabled = settings.world_gradient if settings is not None else True
    node = _gradient_node(nt)

    if not enabled:
        if node is not None:
            nt.nodes.remove(node)
        for link in list(background.inputs["Color"].links):
            nt.links.remove(link)
        saved = scene.get("ald_world_bg_color")
        if saved is not None:
            background.inputs["Color"].default_value = tuple(saved)
            background.inputs["Strength"].default_value = float(
                scene.get("ald_world_bg_strength", 1.0))
        else:
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
    sun_strength = (getattr(settings, "sun_disk_strength", 4.0)
                    if settings else 4.0)
    disk_gate, glow_gate = _sun_fade(direction)
    node.inputs["Sun Strength"].default_value = (
        sun_strength * disk_gate if sun_disk and direction is not None else 0.0)
    radius = max(0.1, getattr(settings, "sun_disk_size", 1.0)
                 if settings else 1.0)
    softness = max(0.2, radius * 0.25)
    node.inputs["Sun Inner"].default_value = math.cos(math.radians(radius))
    node.inputs["Sun Outer"].default_value = math.cos(
        math.radians(radius + softness))
    sun_glow_on = getattr(settings, "sun_glow_enabled", True) if settings else True
    node.inputs["Sun Glow"].default_value = (
        (getattr(settings, "sun_glow", 0.45) if settings else 0.45)
        * glow_gate if sun_glow_on else 0.0)
    node.inputs["Sky Accent"].default_value = _rgba(
        getattr(settings, "sky_accent", (0.05, 0.32, 0.42))
        if settings else (0.05, 0.32, 0.42))
    node.inputs["Sky Accent Amount"].default_value = (
        getattr(settings, "sky_accent_amount", 0.0) if settings else 0.0)

    clouds = getattr(settings, "clouds", True) if settings else False
    cloud_amount = getattr(settings, "cloud_amount", 0.6) if clouds else 0.0
    node.inputs["Cloud Amount"].default_value = cloud_amount
    node.inputs["Cloud Scale"].default_value = (
        getattr(settings, "cloud_scale", 3.0) if settings else 3.0)
    node.inputs["Cloud Flatness"].default_value = (
        getattr(settings, "cloud_flatness", 0.60) if settings else 0.60)
    cloud_type = getattr(settings, "cloud_type", "CUMULUS") \
        if settings else "CUMULUS"
    node.inputs["Cloud Cumulus"].default_value = (
        1.0 if cloud_type == "CUMULUS" else 0.0)
    node.inputs["Cloud Stratocumulus"].default_value = (
        1.0 if cloud_type == "STRATOCUMULUS" else 0.0)
    node.inputs["Cloud Cirrus"].default_value = (
        1.0 if cloud_type == "CIRRUS" else 0.0)
    node.inputs["Cloud Vertical"].default_value = (
        getattr(settings, "cloud_vertical", 0.55) if settings else 0.55)
    node.inputs["Cloud Breakup"].default_value = (
        getattr(settings, "cloud_breakup", 0.35) if settings else 0.35)
    node.inputs["Cloud Detail"].default_value = (
        getattr(settings, "cloud_detail", 0.60) if settings else 0.60)
    node.inputs["Cloud Sun Lighting"].default_value = (
        getattr(settings, "cloud_sun_lighting", 1.2) if settings else 1.2)
    node.inputs["Cloud Sun Scatter"].default_value = (
        getattr(settings, "cloud_sun_scatter", 0.0) if settings else 0.0)
    node.inputs["Contrails"].default_value = (
        getattr(settings, "contrails", 0.0) if settings else 0.0)
    node.inputs["Cloud Delta Gain"].default_value = (
        getattr(settings, "cloud_delta_gain", 1.0) if settings else 1.0)
    node.inputs["Cloud Rim Boost"].default_value = (
        getattr(settings, "cloud_rim_boost", 1.0) if settings else 1.0)

    stars = getattr(settings, "stars", True) if settings else False
    star_amount = ((getattr(settings, "star_strength", p.get("star_amount", 0.0))
                    if settings else p.get("star_amount", 0.0))
                   if stars else 0.0)
    node.inputs["Star Amount"].default_value = max(0.0, min(1.0, star_amount))
    node.inputs["Star Density"].default_value = (
        getattr(settings, "star_density", 180.0) if settings else 180.0)
    node.inputs["Milky Way"].default_value = (
        (getattr(settings, "milky_way", 0.0)
         if getattr(settings, "stars", True) else 0.0)
        if settings else 0.0)
    seed = int(getattr(settings, "cloud_seed", 17)) if settings else 17
    wind = _cloud_offset(scene, settings)
    node.inputs["Cloud Offset"].default_value = (
        wind[0] + seed * 0.017, wind[1] + seed * 0.011, 0.0)
    if settings is not None:
        _apply_star_slots(scene, settings, node)
        moon_shader.write_values(node, settings, sun_toward(scene))

    # Remember the original world background so disabling the gradient can
    # restore an HDRI or the user's own color instead of a flat fill.
    if "ald_world_bg_color" not in scene:
        scene["ald_world_bg_color"] = tuple(
            background.inputs["Color"].default_value)
        scene["ald_world_bg_strength"] = float(
            background.inputs["Strength"].default_value)
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
        from . import identity
        sun[SUN_OWNER_TAG] = identity.scene_id(scene)
        sun.rotation_euler = rotation
        scene.collection.objects.link(sun)
        created = True

    if sun is not None and sun.data is not None:
        from . import identity
        owner = sun.get(SUN_OWNER_TAG)
        if owner is None and sun.get(AUTO_SUN_TAG) \
                and len(sun.users_scene) <= 1:
            # An older file: the only scene using the sun is its owner.
            owner = sun[SUN_OWNER_TAG] = identity.scene_id(scene)
        foreign = bool(owner) and owner != identity.scene_id(scene)
        if not foreign and sun.library is None and sun.data.library is None:
            sun.data.color = p["sun_color"]
            sun.data.energy = p["sun_energy"]
            if sun.get(AUTO_SUN_TAG) and reset_rotation:
                sun.rotation_euler = rotation
    return sun, created


def apply_palette(scene, key):
    """Apply world gradient + sun values for a palette. Returns the preset."""
    global _syncing_style
    from . import snapshot
    # The state of the user is saved before the first modification.
    snapshot.ensure(scene)
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
        seed = int(getattr(settings, "cloud_seed", 17))
        wind = _cloud_offset(scene, settings)
        node.inputs["Cloud Offset"].default_value = (
            wind[0] + seed * 0.017, wind[1] + seed * 0.011, 0.0)
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
    disk_gate, glow_gate = _sun_fade(direction)
    if settings is not None and settings.sun_disk:
        node.inputs["Sun Strength"].default_value = (
            settings.sun_disk_strength * disk_gate)
        node.inputs["Sun Glow"].default_value = (
            settings.sun_glow * glow_gate
            if settings.sun_glow_enabled else 0.0)
    else:
        node.inputs["Sun Strength"].default_value = 0.0
        node.inputs["Sun Glow"].default_value = 0.0


def update_moon_controls(scene):
    """Push the Moon controls into the World without rebuilding the group."""
    world = scene.world
    if world is None or world.node_tree is None:
        return
    node = _gradient_node(world.node_tree)
    if node is None:
        return
    moon_shader.write_values(node, getattr(scene, "ald", None),
                             sun_toward(scene))


@persistent
def _on_frame_change(scene, *_args):
    try:
        update_sun_controls(scene)
        if getattr(getattr(scene, "ald", None), "moon_enabled", False):
            update_moon_controls(scene)
    except Exception:
        pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
