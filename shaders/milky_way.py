"""Structured Milky Way: great-circle band, bulge, dust lanes and stars."""

import math

import bpy

from .common import Graph

GROUP = "ALD | Milky Way"
VERSION = 1

STYLES = {
    "SCIENTIFIC": {
        "width": 12.0, "core": 0.70, "dust_contrast": 0.75,
        "dust_density": 0.65, "detail": 0.65, "stars": 0.50,
        "core_color": (1.0, 0.72, 0.40),
        "outer_color": (0.22, 0.38, 0.90),
        "dust_color": (0.010, 0.010, 0.030),
    },
    "ANIME_CINEMATIC": {
        "width": 14.0, "core": 1.00, "dust_contrast": 0.65,
        "dust_density": 0.55, "detail": 0.85, "stars": 0.65,
        "core_color": (1.0, 0.68, 0.32),
        "outer_color": (0.28, 0.50, 1.0),
        "dust_color": (0.020, 0.010, 0.050),
    },
}


def axes(settings):
    """Pole, core and in-plane cross vectors for the galactic great circle."""
    from mathutils import Vector

    rotation = math.radians(getattr(settings, "milky_way_rotation", 120.0))
    elevation = math.radians(getattr(settings, "milky_way_elevation", -45.0))
    pole = Vector((math.cos(elevation) * math.sin(rotation),
                   -math.cos(elevation) * math.cos(rotation),
                   math.sin(elevation))).normalized()
    reference = Vector((0.0, 0.0, 1.0))
    if abs(pole.dot(reference)) > 0.999:
        reference = Vector((1.0, 0.0, 0.0))
    right = pole.cross(reference).normalized()
    up = right.cross(pole).normalized()
    angle = math.radians(getattr(settings, "milky_way_core_position", 90.0))
    core = (right * math.cos(angle) + up * math.sin(angle)).normalized()
    cross = pole.cross(core).normalized()
    return tuple(pole), tuple(core), tuple(cross)


def apply_style(settings):
    style = STYLES.get(getattr(settings, "milky_way_style", "SCIENTIFIC"))
    if style is None:
        return
    settings.milky_way_width = style["width"]
    settings.milky_way_core_strength = style["core"]
    settings.milky_way_dust_contrast = style["dust_contrast"]
    settings.milky_way_dust_density = style["dust_density"]
    settings.milky_way_detail = style["detail"]
    settings.milky_way_star_concentration = style["stars"]
    settings.milky_way_core_color = style["core_color"]
    settings.milky_way_outer_color = style["outer_color"]
    settings.milky_way_dust_color = style["dust_color"]


def write_values(node, settings):
    if node is None or settings is None:
        return
    pole, core, cross = axes(settings)
    values = {
        "MW Pole": pole,
        "MW Core": core,
        "MW Cross": cross,
        "MW Width": math.radians(getattr(settings, "milky_way_width", 18.0)),
        "MW Core Strength": getattr(settings, "milky_way_core_strength", 0.7),
        "MW Dust Contrast": getattr(settings, "milky_way_dust_contrast", 0.65),
        "MW Dust Density": getattr(settings, "milky_way_dust_density", 0.6),
        "MW Detail": getattr(settings, "milky_way_detail", 0.6),
        "MW Star Concentration": getattr(
            settings, "milky_way_star_concentration", 0.45),
        "MW Horizon": math.radians(
            getattr(settings, "milky_way_horizon_fade", 6.0)),
        "MW Seed": float(getattr(settings, "milky_way_seed", 3)),
        "MW Core Color": tuple(getattr(
            settings, "milky_way_core_color", (1.0, 0.86, 0.62)))[:3] + (1.0,),
        "MW Outer Color": tuple(getattr(
            settings, "milky_way_outer_color", (0.3, 0.46, 0.85)))[:3] + (1.0,),
        "MW Dust Color": tuple(getattr(
            settings, "milky_way_dust_color", (0.01, 0.01, 0.03)))[:3] + (1.0,),
    }
    for name, value in values.items():
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value


def _input(ng, name, socket_type, default, minimum=None, maximum=None):
    socket = ng.interface.new_socket(name=name, in_out="INPUT",
                                     socket_type=socket_type)
    socket.default_value = default
    if minimum is not None:
        socket.min_value = minimum
    if maximum is not None:
        socket.max_value = maximum
    return socket


def build():
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.get("ald_mw_version") == VERSION:
        return ng
    if ng is not None:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(GROUP, "ShaderNodeTree")

    _input(ng, "View", "NodeSocketVector", (0.0, 0.0, 1.0))
    _input(ng, "MW Pole", "NodeSocketVector", (0.58, 0.34, -0.74))
    _input(ng, "MW Core", "NodeSocketVector", (1.0, 0.0, 0.0))
    _input(ng, "MW Cross", "NodeSocketVector", (0.0, 1.0, 0.0))
    _input(ng, "Intensity", "NodeSocketFloat", 0.0, 0.0, 1.0)
    _input(ng, "MW Width", "NodeSocketFloat", math.radians(12.0),
           0.02, 0.7)
    _input(ng, "MW Core Strength", "NodeSocketFloat", 0.7, 0.0, 2.0)
    _input(ng, "MW Dust Contrast", "NodeSocketFloat", 0.75, 0.0, 1.0)
    _input(ng, "MW Dust Density", "NodeSocketFloat", 0.65, 0.0, 1.0)
    _input(ng, "MW Detail", "NodeSocketFloat", 0.6, 0.0, 1.0)
    _input(ng, "MW Star Concentration", "NodeSocketFloat", 0.45, 0.0, 1.0)
    _input(ng, "MW Horizon", "NodeSocketFloat", math.radians(6.0),
           0.0, 0.7)
    _input(ng, "MW Seed", "NodeSocketFloat", 3.0, 0.0, 999.0)
    _input(ng, "MW Core Color", "NodeSocketColor", (1.0, 0.72, 0.40, 1.0))
    _input(ng, "MW Outer Color", "NodeSocketColor", (0.22, 0.38, 0.9, 1.0))
    _input(ng, "MW Dust Color", "NodeSocketColor", (0.01, 0.01, 0.03, 1.0))
    _input(ng, "Cloud Visibility", "NodeSocketFloat", 0.0, 0.0, 1.0)
    ng.interface.new_socket(name="Color", in_out="OUTPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Star Boost", in_out="OUTPUT",
                            socket_type="NodeSocketFloat")

    g = Graph(ng)
    group_in = g.node("NodeGroupInput", -1400, 0)
    group_out = g.node("NodeGroupOutput", 2200, 0)
    view = group_in.outputs["View"]
    pole = group_in.outputs["MW Pole"]
    core_vec = group_in.outputs["MW Core"]
    cross_vec = group_in.outputs["MW Cross"]

    lat = g.vmath("DOT_PRODUCT", view, pole, x=-1200, y=200)
    lon = g.math("ARCTAN2",
                 g.vmath("DOT_PRODUCT", view, cross_vec, x=-1200, y=40),
                 g.vmath("DOT_PRODUCT", view, core_vec, x=-1200, y=-120),
                 x=-1000, y=60)
    width = g.math("MAXIMUM", group_in.outputs["MW Width"], 0.01,
                   x=-1000, y=320)
    lat_n = g.math("DIVIDE", lat, width, x=-800, y=280)
    band = g.math("EXPONENT",
                  g.math("MULTIPLY", g.math("MULTIPLY", lat_n, lat_n,
                                            x=-620, y=280),
                         -2.0, x=-440, y=280), x=-260, y=280)

    # Cylinder coordinates keep the noise continuous across the 360 seam.
    cos_lon = g.math("COSINE", lon, x=-800, y=40)
    sin_lon = g.math("SINE", lon, x=-800, y=-80)
    seed = group_in.outputs["MW Seed"]
    cylinder = g.node("ShaderNodeCombineXYZ", -620, 0)
    g.feed(cylinder.inputs["X"], g.math("ADD",
                                        g.math("MULTIPLY", cos_lon, 2.0,
                                               x=-620, y=40),
                                        g.math("MULTIPLY", seed, 1.7,
                                               x=-620, y=-40), x=-440, y=0))
    g.feed(cylinder.inputs["Y"], g.math("ADD",
                                        g.math("MULTIPLY", sin_lon, 2.0,
                                               x=-620, y=-120),
                                        g.math("MULTIPLY", seed, 2.3,
                                               x=-620, y=-200), x=-440, y=-120))
    g.feed(cylinder.inputs["Z"], g.math("ADD",
                                        g.math("MULTIPLY", lat, 5.0,
                                               x=-620, y=-280),
                                        g.math("MULTIPLY", seed, 0.7,
                                               x=-620, y=-360), x=-440, y=-280))

    detail = group_in.outputs["MW Detail"]
    macro = g.node("ShaderNodeTexNoise", -260, 120)
    macro.inputs["Scale"].default_value = 2.4
    macro.inputs["Detail"].default_value = 5.0
    macro.inputs["Roughness"].default_value = 0.6
    macro.inputs["Distortion"].default_value = 0.35
    g.feed(macro.inputs["Vector"], cylinder.outputs["Vector"])
    file_noise = g.node("ShaderNodeTexNoise", -260, -120)
    file_noise.inputs["Scale"].default_value = 7.5
    file_noise.inputs["Detail"].default_value = 4.0
    file_noise.inputs["Roughness"].default_value = 0.55
    g.feed(file_noise.inputs["Vector"], cylinder.outputs["Vector"])

    macro_mix = g.math("ADD", 0.35, g.math("MULTIPLY", macro.outputs["Fac"],
                                          1.0, x=-80, y=120), x=100, y=120)
    file_mix = g.math("ADD", 0.55, g.math("MULTIPLY",
                                          file_noise.outputs["Fac"],
                                          g.math("MULTIPLY", detail, 0.8,
                                                 x=-80, y=-120), x=100, y=-120),
                      x=280, y=-120)
    band = g.math("MULTIPLY", band, macro_mix, x=100, y=280)
    band = g.math("MULTIPLY", band, file_mix, x=280, y=280)

    core = g.math("EXPONENT",
                  g.math("MULTIPLY",
                         g.math("POWER", g.math("DIVIDE", lon, 0.35,
                                                x=-620, y=460), 2.0,
                                x=-440, y=460), -1.0, x=-260, y=460),
                  x=-80, y=460)
    core = g.math("MULTIPLY", core, group_in.outputs["MW Core Strength"],
                  x=100, y=460)

    # Dust: a main rift on the plane plus weaker secondary branches.
    rift = g.math("EXPONENT",
                  g.math("MULTIPLY",
                         g.math("POWER", g.math("DIVIDE", lat,
                                                g.math("MULTIPLY", width, 0.26,
                                                       x=-620, y=620),
                                                x=-440, y=620), 2.0,
                                x=-260, y=620), -1.0, x=-80, y=620),
                  x=100, y=620)
    rift = g.math("MULTIPLY", rift,
                  g.math("ADD", 0.45, g.math("MULTIPLY", macro.outputs["Fac"],
                                             0.9, x=100, y=740), x=280, y=740),
                  x=460, y=620)
    branch = g.math("EXPONENT",
                    g.math("MULTIPLY",
                           g.math("POWER",
                                  g.math("DIVIDE",
                                         g.math("SUBTRACT",
                                                g.math("ABSOLUTE", lat,
                                                       x=-620, y=860),
                                                g.math("MULTIPLY", width, 0.52,
                                                       x=-440, y=860),
                                                x=-260, y=860),
                                         g.math("MULTIPLY", width, 0.12,
                                                x=-80, y=860),
                                         x=100, y=860), 2.0,
                                  x=280, y=860), -1.0, x=460, y=860),
                    x=640, y=860)
    branch = g.math("MULTIPLY", branch,
                    g.math("ADD", 0.25, g.math("MULTIPLY",
                                               file_noise.outputs["Fac"],
                                               0.9, x=460, y=980),
                           x=640, y=980), x=820, y=860)
    dust = g.math("ADD", g.math("MULTIPLY", rift,
                                group_in.outputs["MW Dust Density"],
                                x=640, y=620),
                  g.math("MULTIPLY", branch,
                         g.math("MULTIPLY", group_in.outputs["MW Dust Density"],
                                0.6, x=640, y=980), x=820, y=980),
                  x=1000, y=760)
    dust = g.math("MULTIPLY", dust,
                  group_in.outputs["MW Dust Contrast"], clamp=True,
                  x=1180, y=760)

    band_clean = g.math("MULTIPLY", band,
                        g.math("SUBTRACT", 1.0, dust, x=1180, y=600),
                        x=1360, y=600)
    tone = g.math("ADD", g.math("MULTIPLY", core, 1.15, x=1360, y=460),
                  g.math("MULTIPLY", band_clean, 0.12,
                         x=1360, y=520), x=1540, y=460)
    tone = g.math("MINIMUM", tone, 1.0, x=1720, y=460)
    color = g.mix(tone, group_in.outputs["MW Outer Color"],
                  group_in.outputs["MW Core Color"], x=1900, y=460)
    color = g.mix(g.math("MULTIPLY", dust, 0.85, x=1540, y=300),
                  color, group_in.outputs["MW Dust Color"], x=2080, y=360)

    intensity = group_in.outputs["Intensity"]
    brightness = g.math("MULTIPLY", band_clean, intensity, x=1540, y=160)
    brightness = g.math("MULTIPLY", brightness,
                        g.math("ADD", 0.22, g.math("MULTIPLY", core, 1.0,
                                                   x=1540, y=40),
                               x=1720, y=40), x=1900, y=120)
    view_z = g.vmath("DOT_PRODUCT", view, (0.0, 0.0, 1.0),
                     x=1540, y=-120)
    horizon = g.maprange(
        view_z, 0.0,
        g.math("MAXIMUM", group_in.outputs["MW Horizon"], 0.001,
               x=1540, y=-240),
        0.0, 1.0, x=1720, y=-180)
    cloud = g.math("SUBTRACT", 1.0, group_in.outputs["Cloud Visibility"],
                   x=1720, y=-320)
    brightness = g.math("MULTIPLY", brightness, horizon, x=2080, y=120)
    brightness = g.math("MULTIPLY", brightness, cloud, x=2260, y=120)
    color = g.scale_color(color, brightness, x=2440, y=360)

    star_boost = g.math("MULTIPLY", band,
                        g.math("ADD", 0.5, core, x=1540, y=-460),
                        x=1720, y=-460)
    star_boost = g.math("MULTIPLY", star_boost,
                        group_in.outputs["MW Star Concentration"],
                        x=1900, y=-460)
    star_boost = g.math("MULTIPLY", star_boost, intensity, x=2080, y=-460)
    star_boost = g.math("MULTIPLY", star_boost,
                        g.math("SUBTRACT", 1.0, dust, x=2260, y=-560),
                        x=2260, y=-460)
    star_boost = g.math("MULTIPLY", star_boost, horizon, x=2440, y=-460)
    star_boost = g.math("MINIMUM", star_boost, 1.0, x=2620, y=-460)

    g.feed(group_out.inputs["Color"], color)
    g.feed(group_out.inputs["Star Boost"], star_boost)
    ng["ald_mw_version"] = VERSION
    return ng
