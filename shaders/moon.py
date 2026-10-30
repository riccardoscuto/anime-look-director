"""Procedural Moon: angular disk, surface detail and halo in a node group."""

import math

import bpy

from .common import Graph

GROUP = "ALD | Moon"
MOON_VERSION = 1

STYLES = {
    "ANIME_CLEAN": {
        "size": 2.6, "brightness": 0.80, "detail": 0.25, "crater": 0.30,
        "contrast": 0.55, "edge": 0.05, "glow": 0.30, "halo": 1.6,
        "color": (1.0, 0.97, 0.90), "halo_color": (0.72, 0.80, 1.0),
    },
    "ANIME_PAINTERLY": {
        "size": 2.8, "brightness": 0.72, "detail": 0.55, "crater": 0.60,
        "contrast": 0.55, "edge": 0.10, "glow": 0.25, "halo": 1.8,
        "color": (1.0, 0.95, 0.86), "halo_color": (0.80, 0.78, 0.95),
    },
    "DETAILED_MOON": {
        "size": 3.0, "brightness": 0.82, "detail": 1.0, "crater": 0.85,
        "contrast": 0.75, "edge": 0.04, "glow": 0.22, "halo": 1.2,
        "color": (0.98, 0.96, 0.92), "halo_color": (0.70, 0.78, 0.95),
    },
    "ETHEREAL_MOON": {
        "size": 3.2, "brightness": 0.65, "detail": 0.30, "crater": 0.35,
        "contrast": 0.45, "edge": 0.10, "glow": 0.30, "halo": 3.0,
        "color": (0.86, 0.92, 1.0), "halo_color": (0.55, 0.72, 1.0),
    },
}


def direction(azimuth, elevation):
    """Unit vector toward the Moon; azimuth 0 faces -Y like the Sun."""
    az = math.radians(azimuth)
    el = math.radians(elevation)
    return (math.cos(el) * math.sin(az),
            -math.cos(el) * math.cos(az),
            math.sin(el))


def basis(direction_vector):
    """Screen right/up for a direction, stable at the poles."""
    from mathutils import Vector

    forward = Vector(direction_vector).normalized()
    reference = Vector((0.0, 0.0, 1.0))
    if abs(forward.dot(reference)) > 0.999:
        reference = Vector((1.0, 0.0, 0.0))
    right = forward.cross(reference).normalized()
    up = right.cross(forward).normalized()
    return tuple(right), tuple(up)


def apply_style(settings):
    """Write the selected style into the individual controls."""
    style = STYLES.get(getattr(settings, "moon_style", "ANIME_CLEAN"))
    if style is None:
        return
    settings.moon_size = style["size"]
    settings.moon_brightness = style["brightness"]
    settings.moon_surface_detail = style["detail"]
    settings.moon_crater_strength = style["crater"]
    settings.moon_surface_contrast = style["contrast"]
    settings.moon_edge_softness = style["edge"]
    settings.moon_glow = style["glow"]
    settings.moon_halo_radius = style["halo"]
    settings.moon_color = style["color"]
    settings.moon_halo_color = style["halo_color"]


def write_values(node, settings):
    """Push the Moon settings into an existing ALD | Moon group node."""
    if node is None or settings is None:
        return
    moon_direction = direction(settings.moon_azimuth, settings.moon_elevation)
    right, up = basis(moon_direction)
    values = {
        "Moon Enabled": 1.0 if settings.moon_enabled else 0.0,
        "Moon Direction": moon_direction,
        "Moon Right": right,
        "Moon Up": up,
        "Moon Size": settings.moon_size,
        "Moon Brightness": settings.moon_brightness,
        "Moon Color": tuple(settings.moon_color)[:3] + (1.0,),
        "Moon Surface Detail": settings.moon_surface_detail,
        "Moon Crater Strength": settings.moon_crater_strength,
        "Moon Surface Contrast": settings.moon_surface_contrast,
        "Moon Edge Softness": settings.moon_edge_softness,
        "Moon Glow": settings.moon_glow,
        "Moon Halo Radius": settings.moon_halo_radius,
        "Moon Halo Color": tuple(settings.moon_halo_color)[:3] + (1.0,),
        "Moon Seed": float(settings.moon_seed),
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


def _crater_layer(g, mapped, scale, weight, y):
    voronoi = g.node("ShaderNodeTexVoronoi", 200, y, feature="F1")
    voronoi.inputs["Scale"].default_value = scale
    voronoi.inputs["Randomness"].default_value = 0.8
    g.feed(voronoi.inputs["Vector"], mapped)
    distance = voronoi.outputs["Distance"]
    separate = g.node("ShaderNodeSeparateColor", 380, y)
    g.feed(separate.inputs["Color"], voronoi.outputs["Color"])
    random = separate.outputs["Red"]
    radius = g.math("ADD", 0.10, g.math("MULTIPLY", random, 0.45),
                    x=560, y=y)
    inner = g.maprange(distance, 0.0, radius, 1.0, 0.0, x=740, y=y)
    band = g.math("MULTIPLY", radius, 0.24, x=740, y=y - 120)
    rim_low = g.maprange(distance,
                         g.math("SUBTRACT", radius, band, x=740, y=y - 160),
                         radius, 0.0, 1.0, x=920, y=y)
    rim_high = g.maprange(distance, radius,
                          g.math("ADD", radius, band, x=740, y=y - 240),
                          1.0, 0.0, x=920, y=y - 100)
    rim = g.math("MULTIPLY", rim_low, rim_high, x=1100, y=y)
    rim_strength = g.math("ADD", 0.45,
                          g.math("MULTIPLY", separate.outputs["Green"], 0.55,
                                 x=740, y=y - 320),
                          x=920, y=y - 320)
    rim = g.math("MULTIPLY", rim, rim_strength, x=1280, y=y)
    floor = g.math("MULTIPLY", inner, -0.32, x=1100, y=y - 120)
    edge = g.math("MULTIPLY", rim, 0.22, x=1460, y=y)
    effect = g.math("ADD", floor, edge, x=1640, y=y)
    return g.math("MULTIPLY", effect, weight, x=1820, y=y)


def build():
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.get("ald_moon_version") == MOON_VERSION:
        return ng
    if ng is not None:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(GROUP, "ShaderNodeTree")

    _input(ng, "View", "NodeSocketVector", (0.0, 0.0, 1.0))
    _input(ng, "Moon Direction", "NodeSocketVector", (0.0, -1.0, 0.0))
    _input(ng, "Moon Right", "NodeSocketVector", (1.0, 0.0, 0.0))
    _input(ng, "Moon Up", "NodeSocketVector", (0.0, 0.0, 1.0))
    _input(ng, "Moon Size", "NodeSocketFloat", 2.6, 0.05, 40.0)
    _input(ng, "Moon Brightness", "NodeSocketFloat", 1.0, 0.0, 20.0)
    _input(ng, "Moon Color", "NodeSocketColor", (1.0, 0.97, 0.9, 1.0))
    _input(ng, "Moon Surface Detail", "NodeSocketFloat", 0.25, 0.0, 1.0)
    _input(ng, "Moon Crater Strength", "NodeSocketFloat", 0.35, 0.0, 1.0)
    _input(ng, "Moon Surface Contrast", "NodeSocketFloat", 0.45, 0.0, 1.0)
    _input(ng, "Moon Edge Softness", "NodeSocketFloat", 0.14, 0.0, 1.0)
    _input(ng, "Moon Glow", "NodeSocketFloat", 0.35, 0.0, 4.0)
    _input(ng, "Moon Halo Radius", "NodeSocketFloat", 2.0, 0.0, 30.0)
    _input(ng, "Moon Halo Color", "NodeSocketColor", (0.72, 0.8, 1.0, 1.0))
    _input(ng, "Moon Seed", "NodeSocketFloat", 7.0, 0.0, 999.0)
    _input(ng, "Cloud Visibility", "NodeSocketFloat", 0.0, 0.0, 1.0)
    _input(ng, "Moon Enabled", "NodeSocketFloat", 0.0, 0.0, 1.0)
    ng.interface.new_socket(name="Color", in_out="OUTPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Alpha", in_out="OUTPUT",
                            socket_type="NodeSocketFloat")

    g = Graph(ng)
    group_in = g.node("NodeGroupInput", -1400, 0)
    group_out = g.node("NodeGroupOutput", 2600, 0)
    view = group_in.outputs["View"]
    direction_socket = group_in.outputs["Moon Direction"]
    dot = g.vmath("DOT_PRODUCT", view, direction_socket, x=-1200, y=600)

    # Angular disk: cos comparison keeps the edge circular at any elevation.
    half = g.math("MULTIPLY", group_in.outputs["Moon Size"],
                  math.radians(0.5), x=-1200, y=420)
    soft = g.math("MAXIMUM",
                  g.math("MULTIPLY", group_in.outputs["Moon Edge Softness"],
                         math.radians(1.0), x=-1200, y=300),
                  math.radians(0.03), x=-1020, y=300)
    inner_angle = g.math("MAXIMUM",
                         g.math("SUBTRACT", half, soft, x=-1040, y=420),
                         0.0, x=-880, y=420)
    outer_angle = g.math("ADD", half, soft, x=-880, y=540)
    disk = g.maprange(dot, g.math("COSINE", outer_angle, x=-700, y=540),
                      g.math("COSINE", inner_angle, x=-700, y=420),
                      0.0, 1.0, x=-520, y=480)

    # Surface coordinates: orthographic projection of the sky cap, so the
    # detail never depends on camera distance and the rim stays circular.
    sin_half = g.math("SINE", half, x=-1040, y=120)
    u = g.math("DIVIDE",
               g.vmath("DOT_PRODUCT", view, group_in.outputs["Moon Right"],
                       x=-1200, y=0),
               sin_half, x=-860, y=60)
    v = g.math("DIVIDE",
               g.vmath("DOT_PRODUCT", view, group_in.outputs["Moon Up"],
                       x=-1200, y=-140),
               sin_half, x=-860, y=-80)
    combine = g.node("ShaderNodeCombineXYZ", -680, 0)
    g.feed(combine.inputs["X"], u)
    g.feed(combine.inputs["Y"], v)
    mapping = g.node("ShaderNodeMapping", -500, 0)
    g.feed(mapping.inputs["Vector"], combine.outputs["Vector"])
    seed = group_in.outputs["Moon Seed"]
    seed_offset = g.node("ShaderNodeCombineXYZ", -680, -260)
    g.feed(seed_offset.inputs["X"],
           g.math("MULTIPLY", seed, 2.7, x=-860, y=-260))
    g.feed(seed_offset.inputs["Y"],
           g.math("MULTIPLY", seed, 1.3, x=-860, y=-340))
    g.feed(mapping.inputs["Location"], seed_offset.outputs["Vector"])
    mapped = mapping.outputs["Vector"]

    maria_noise = g.node("ShaderNodeTexNoise", -300, 240)
    maria_noise.inputs["Scale"].default_value = 1.4
    maria_noise.inputs["Detail"].default_value = 3.0
    maria_noise.inputs["Roughness"].default_value = 0.55
    maria_noise.inputs["Distortion"].default_value = 0.3
    g.feed(maria_noise.inputs["Vector"], mapped)
    maria = g.maprange(maria_noise.outputs["Fac"], 0.40, 0.60,
                       0.0, 1.0, x=-100, y=240)

    micro_noise = g.node("ShaderNodeTexNoise", -300, -340)
    micro_noise.inputs["Scale"].default_value = 44.0
    micro_noise.inputs["Detail"].default_value = 6.0
    micro_noise.inputs["Roughness"].default_value = 0.5
    g.feed(micro_noise.inputs["Vector"], mapped)
    grain = g.math("MULTIPLY",
                   g.math("SUBTRACT", micro_noise.outputs["Fac"], 0.5,
                          x=-100, y=-340),
                   g.math("MULTIPLY", group_in.outputs["Moon Surface Detail"],
                          0.05, x=-100, y=-460),
                   x=80, y=-380)

    contrast = group_in.outputs["Moon Surface Contrast"]
    maria_depth = g.math("MULTIPLY",
                         g.math("MULTIPLY", maria, contrast, x=80, y=240),
                         0.55, x=260, y=240)
    tone = g.math("SUBTRACT", 1.0, maria_depth, x=440, y=240)

    crater_amount = g.math("MULTIPLY",
                           group_in.outputs["Moon Crater Strength"], 1.0,
                           x=200, y=-700)
    craters = _crater_layer(g, mapped, 2.6, crater_amount, -640)
    secondary = _crater_layer(g, mapped, 8.0,
                              g.math("MULTIPLY", crater_amount, 0.35,
                                     x=200, y=-900), -960)
    surface_noise = g.math("ADD", g.math("ADD", grain, craters, x=1820, y=-300),
                           secondary, x=2000, y=-300)
    light = g.math("MAXIMUM", g.math("ADD", tone, surface_noise, x=2180, y=-100),
                   0.05, x=2360, y=-100)

    # Spherical read: the limb darkens, the centre stays bright.
    radius2 = g.math("ADD",
                     g.math("MULTIPLY", u, u, x=-680, y=-460),
                     g.math("MULTIPLY", v, v, x=-680, y=-560),
                     x=-500, y=-500)
    normal_z = g.math("SQRT",
                      g.math("MAXIMUM",
                             g.math("SUBTRACT", 1.0, radius2, x=-320, y=-500),
                             0.0, x=-140, y=-500),
                      x=40, y=-500)
    limb = g.math("ADD", 0.32, g.math("MULTIPLY", normal_z, 0.68,
                                      x=220, y=-500), x=400, y=-500)

    base = group_in.outputs["Moon Color"]
    cool = g.vmath("MULTIPLY", base, (0.84, 0.89, 1.05), x=80, y=600)
    warm = g.vmath("MULTIPLY", base, (1.05, 1.0, 0.9), x=80, y=460)
    maria_tint = g.mix(g.math("MULTIPLY", maria, contrast, x=260, y=600),
                       base, cool, x=440, y=560)
    warm_amount = g.math("MULTIPLY",
                         g.math("SUBTRACT", 1.0, maria, x=260, y=700),
                         0.15, x=440, y=700)
    tint = g.mix(warm_amount, maria_tint, warm, x=620, y=560)
    shaded = g.scale_color(tint, light, x=2540, y=100)
    shaded = g.scale_color(shaded, limb, x=2720, y=100)
    shaded = g.scale_color(shaded, group_in.outputs["Moon Brightness"],
                           x=2900, y=100)

    # Halo: a tight glow plus a wide atmospheric falloff, independent of size.
    chord = g.math("SQRT",
                   g.math("MAXIMUM",
                          g.math("MULTIPLY",
                                 g.math("SUBTRACT", 1.0, dot, x=-1200, y=800),
                                 2.0, x=-1020, y=800),
                          0.0, x=-860, y=800),
                   x=-700, y=800)
    tight_end = g.math("ADD", half, math.radians(0.9), x=-520, y=760)
    tight = g.maprange(chord, half, tight_end, 1.0, 0.0, x=-340, y=760)
    tight = g.math("MULTIPLY", g.math("MULTIPLY", tight, tight,
                                      x=-160, y=760),
                   g.math("MULTIPLY", group_in.outputs["Moon Glow"], 0.6,
                          x=-160, y=640), x=20, y=760)
    halo_angle = g.math("MAXIMUM",
                        g.math("MULTIPLY", group_in.outputs["Moon Halo Radius"],
                               math.radians(1.0), x=-520, y=980),
                        math.radians(0.05), x=-340, y=980)
    wide_end = g.math("ADD", half, halo_angle, x=-160, y=980)
    wide = g.maprange(chord, half, wide_end, 1.0, 0.0, x=20, y=980)
    wide = g.math("MULTIPLY", g.math("MULTIPLY", wide, wide, x=200, y=980),
                  wide, x=380, y=980)
    wide = g.math("MULTIPLY", wide, group_in.outputs["Moon Glow"],
                  x=560, y=980)
    halo = g.math("ADD", tight, wide, x=740, y=900)

    cloud = group_in.outputs["Cloud Visibility"]
    disk_open = g.math("SUBTRACT", 1.0,
                       g.math("MULTIPLY", cloud, 0.92, x=-300, y=1200),
                       x=-120, y=1200)
    halo_open = g.math("SUBTRACT", 1.0,
                       g.math("MULTIPLY", cloud, 0.65, x=-300, y=1320),
                       x=-120, y=1320)
    disk_alpha = g.math("MULTIPLY", disk, disk_open, x=600, y=1200)
    halo_alpha = g.math("MULTIPLY", halo, halo_open, x=780, y=1320)
    halo_alpha = g.math("MINIMUM", halo_alpha, 1.0, x=960, y=1320)
    # Halo and disk are separate layers: the halo only fills the sky outside
    # the disk, so it never flattens the surface detail. Both are premultiplied
    # by their own coverage and composited once by the World.
    halo_outside = g.math(
        "MULTIPLY", halo_alpha,
        g.math("SUBTRACT", 1.0, disk_alpha, x=960, y=1440), x=1140, y=1440)
    alpha = g.math("MAXIMUM", disk_alpha, halo_outside, x=1320, y=1260)
    alpha = g.math("MULTIPLY", alpha, group_in.outputs["Moon Enabled"],
                   x=1500, y=1260)

    disk_rgb = g.scale_color(shaded, disk_alpha, x=3080, y=600)
    halo_rgb = g.scale_color(group_in.outputs["Moon Halo Color"], halo_outside,
                             x=3080, y=900)
    color = g.vmath("ADD", disk_rgb, halo_rgb, x=3260, y=700)
    color = g.scale_color(color, group_in.outputs["Moon Enabled"],
                          x=3440, y=700)

    g.feed(group_out.inputs["Color"], color)
    g.feed(group_out.inputs["Alpha"], alpha)
    ng["ald_moon_version"] = MOON_VERSION
    return ng
