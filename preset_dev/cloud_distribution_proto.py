"""Independent 2D Cloud Distribution prototype.

Generates a deterministic equirectangular density panorama from stratified
individual cumulus masses (rounded lobes, flat bases), packs it into the .blend
and samples it in the World shader. Research prototype only: it does not modify
the add-on, its UI, presets or production World generator.

Cloud Amount is the requested global coverage of the visible hemisphere,
weighted by the angular area of each panorama pixel. The per-camera coverage is
measured separately and is expected to vary.

Run::

    blender -b --factory-startup --python preset_dev/cloud_distribution_proto.py -- \
        --seed 11 --width 2048 --height 1024 --amounts 0.18,0.30,0.42
"""

import json
import math
import os
import sys
import time

import bpy
import numpy as np

VIEWS = {
    "main": ((0.0, -12.0, 3.0), (1.75, 0.0, 0.45)),
    "right": ((0.0, -12.0, 3.0), (1.80, 0.0, 0.95)),
    "seam": ((0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, -math.pi / 2.0)),
}

# Jittered Fibonacci lattice over the visible hemisphere: uniform by area,
# no latitude bands, no grid.
COUNT = 96
GOLDEN = 0.6180339887498949
RADIUS = (3.5, 7.0)
TARGET_FOOTPRINT = 0.50
MAX_RADIUS = 15.0
WARP = 0.10
EDGE = 0.10


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "preset_dev/cloud_distribution", "seed": "11",
              "width": "2048", "height": "1024",
              "amounts": "0.18,0.30,0.42", "views": "main,right",
              "variant": "baseline", "union": str(TARGET_FOOTPRINT),
              "save": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seed"] = int(values["seed"])
    values["width"] = int(values["width"])
    values["height"] = int(values["height"])
    values["amounts"] = [float(x) for x in values["amounts"].split(",") if x]
    values["union"] = float(values["union"])
    values["views"] = [x for x in values["views"].split(",") if x]
    return values


def directions(width, height):
    u = (np.arange(width, dtype=np.float32) + 0.5) / width
    lat = ((np.arange(height, dtype=np.float32) + 0.5) / height - 0.5) * np.pi
    lon = u * (2.0 * np.pi)
    cos_lat = np.cos(lat)[:, None]
    x = cos_lat * np.cos(lon)[None, :]
    y = cos_lat * np.sin(lon)[None, :]
    z = np.sin(lat)[:, None] * np.ones_like(lon)[None, :]
    return np.stack([x, y, z], axis=-1).astype(np.float32), lat


def value_noise(width, height, res_u, res_v, rng):
    grid = rng.random((res_v, res_u), dtype=np.float32)
    u = (np.arange(width, dtype=np.float32) + 0.5) / width * res_u
    v = (np.arange(height, dtype=np.float32) + 0.5) / height * res_v
    i0 = np.floor(u).astype(np.int32) % res_u
    j0 = np.floor(v).astype(np.int32) % res_v
    i1 = (i0 + 1) % res_u
    j1 = (j0 + 1) % res_v
    fu = (u - np.floor(u))[None, :]
    fv = (v - np.floor(v))[:, None]
    a = grid[j0[:, None], i0[None, :]]
    b = grid[j0[:, None], i1[None, :]]
    c = grid[j1[:, None], i0[None, :]]
    d = grid[j1[:, None], i1[None, :]]
    return ((a * (1 - fu) + b * fu) * (1 - fv)
            + (c * (1 - fu) + d * fu) * fv)


def fbm(width, height, rng, base=(8, 4), octaves=3):
    total = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    norm = 0.0
    for index in range(octaves):
        total += value_noise(width, height, base[0] * (2 ** index),
                             base[1] * (2 ** index), rng) * amplitude
        norm += amplitude
        amplitude *= 0.5
    return total / norm


def ellipse_distance(x, y, cx, cy, rx, ry, angle=0.0):
    dx = x - cx
    dy = y - cy
    if angle:
        ca = math.cos(angle)
        sa = math.sin(angle)
        dx, dy = dx * ca + dy * sa, -dx * sa + dy * ca
    return (np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) - 1.0) * min(rx, ry)


def soft_maximum(a, b, k):
    if k <= 0.0:
        return np.maximum(a, b)
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h + k * h * (1.0 - h)


def mass_distance(x, y, spec):
    """Signed distance to body, lobes and base of one mass."""
    distance = ellipse_distance(x, y, **spec["body"])
    for lobe in spec["lobes"]:
        distance = np.minimum(distance, ellipse_distance(x, y, **lobe))
    base = spec["base"]
    y_base = base["y"] + base["wave"] * np.sin(
        2.0 * math.pi * (x * base["freq"] + base["phase"]))
    return soft_maximum(distance, y_base - y, base["soft"])


def baseline_lobes(rng, tall):
    lobes = []
    count = int(rng.integers(5, 8))
    for lobe_index in range(count):
        lobes.append({
            "cx": float(-0.62 + 1.24 * (lobe_index + 0.5) / count
                        + rng.uniform(-0.06, 0.06)),
            "cy": float((0.30 + rng.uniform(0.0, 0.25)) * tall),
            "rx": float(rng.uniform(0.30, 0.45)),
            "ry": float(rng.uniform(0.30, 0.48)),
            "angle": 0.0,
        })
    return lobes


def variant_anatomy(rng, tall, width, variant):
    """Body, lobes and base for the hierarchical morphology variants.

    Towers are stacks of overlapping lobes with protruding caps, not single
    tall ellipses, so their flanks stay scalloped and never read as capsules.
    """
    base = {"y": -0.22, "wave": 0.018, "freq": 0.9,
            "phase": float(rng.uniform(0.0, 1.0)), "soft": 0.05}
    lobes = []
    if variant == "hierarchical":
        body = {"cx": -0.06, "cy": 0.06, "rx": width * 0.94,
                "ry": 0.46 * tall}
        tx = float(rng.uniform(-0.36, -0.14))
        for offset, cy, rx, ry in ((0.00, 0.20, 0.38, 0.34),
                                   (0.03, 0.38, 0.32, 0.30),
                                   (-0.02, 0.56, 0.27, 0.27),
                                   (0.01, 0.72, 0.23, 0.24)):
            lobes.append({"cx": tx + offset + float(rng.uniform(-0.02, 0.02)),
                          "cy": float(cy * tall), "rx": rx, "ry": ry,
                          "angle": float(rng.uniform(-0.08, 0.08))})
        lobes.append({"cx": tx + 0.10, "cy": float(0.88 * tall),
                      "rx": float(rng.uniform(0.12, 0.16)),
                      "ry": float(rng.uniform(0.12, 0.15)), "angle": 0.0})
        lobes.append({"cx": tx - 0.13, "cy": float(0.80 * tall),
                      "rx": float(rng.uniform(0.10, 0.13)),
                      "ry": float(rng.uniform(0.09, 0.12)), "angle": 0.0})
        tx2 = float(rng.uniform(0.28, 0.42))
        for cy, rx, ry in ((0.30, 0.24, 0.24), (0.44, 0.20, 0.20)):
            lobes.append({"cx": tx2 + float(rng.uniform(-0.02, 0.02)),
                          "cy": float(cy * tall), "rx": rx, "ry": ry,
                          "angle": float(rng.uniform(-0.10, 0.10))})
        lobes.append({"cx": tx2 + 0.04, "cy": float(0.60 * tall),
                      "rx": float(rng.uniform(0.10, 0.13)),
                      "ry": float(rng.uniform(0.08, 0.11)), "angle": 0.0})
        for cx, cy, rx, ry in ((-0.60, 0.14, 0.22, 0.18),
                               (0.62, 0.10, 0.24, 0.16)):
            lobes.append({"cx": float(cx + rng.uniform(-0.03, 0.03)),
                          "cy": float((cy + rng.uniform(-0.02, 0.04)) * tall),
                          "rx": float(rx + rng.uniform(-0.02, 0.02)),
                          "ry": float(ry + rng.uniform(-0.02, 0.02)),
                          "angle": 0.0})
        for cx, cy in ((0.46, 0.26), (-0.40, 0.22), (0.14, 0.56)):
            lobes.append({"cx": float(cx + rng.uniform(-0.04, 0.04)),
                          "cy": float((cy + rng.uniform(-0.03, 0.03)) * tall),
                          "rx": float(rng.uniform(0.08, 0.12)),
                          "ry": float(rng.uniform(0.07, 0.10)), "angle": 0.0})
    else:
        base["wave"] = 0.025
        base["freq"] = 1.1
        body = {"cx": 0.06, "cy": 0.08, "rx": width * 0.92,
                "ry": 0.44 * tall}
        tx = float(rng.uniform(-0.44, -0.22))
        for offset, cy, rx, ry in ((0.00, 0.20, 0.34, 0.32),
                                   (-0.03, 0.40, 0.30, 0.29),
                                   (-0.07, 0.58, 0.26, 0.26),
                                   (-0.10, 0.74, 0.22, 0.23)):
            lobes.append({"cx": tx + offset + float(rng.uniform(-0.02, 0.02)),
                          "cy": float(cy * tall), "rx": rx, "ry": ry,
                          "angle": float(rng.uniform(-0.10, 0.10))})
        lobes.append({"cx": tx - 0.17, "cy": float(0.88 * tall),
                      "rx": float(rng.uniform(0.12, 0.15)),
                      "ry": float(rng.uniform(0.11, 0.14)), "angle": 0.0})
        lobes.append({"cx": tx + 0.00, "cy": float(0.82 * tall),
                      "rx": float(rng.uniform(0.10, 0.12)),
                      "ry": float(rng.uniform(0.09, 0.11)), "angle": 0.0})
        tx2 = float(rng.uniform(0.30, 0.44))
        for cy, rx, ry in ((0.30, 0.20, 0.21), (0.42, 0.17, 0.18)):
            lobes.append({"cx": tx2 + float(rng.uniform(-0.02, 0.02)),
                          "cy": float(cy * tall), "rx": rx, "ry": ry,
                          "angle": float(rng.uniform(-0.10, 0.10))})
        for cy, rx, ry in ((0.10, 0.16, 0.13), (0.24, 0.13, 0.11)):
            lobes.append({"cx": float(rng.uniform(-0.58, -0.44)),
                          "cy": float((cy + rng.uniform(-0.02, 0.03)) * tall),
                          "rx": rx, "ry": ry, "angle": 0.0})
        lobes.append({"cx": float(rng.uniform(0.56, 0.66)),
                      "cy": float(rng.uniform(0.06, 0.14) * tall),
                      "rx": float(rng.uniform(0.20, 0.24)),
                      "ry": float(rng.uniform(0.14, 0.18)), "angle": 0.0})
        for cx, cy in ((0.46, 0.28), (-0.32, 0.38)):
            lobes.append({"cx": float(cx + rng.uniform(-0.03, 0.03)),
                          "cy": float((cy + rng.uniform(-0.03, 0.03)) * tall),
                          "rx": float(rng.uniform(0.08, 0.11)),
                          "ry": float(rng.uniform(0.07, 0.09)), "angle": 0.0})
    return body, lobes, base


def make_masses(rng, variant="baseline", anatomy_rng=None):
    specs = []
    spacing = math.sqrt(2.0 * math.pi / COUNT)
    for index in range(COUNT):
        z = (index + 0.5) / COUNT
        lon = (index * GOLDEN) % 1.0 * 2.0 * math.pi
        ring = math.sqrt(max(0.0, 1.0 - z * z))
        direction = np.array([ring * math.cos(lon), ring * math.sin(lon), z],
                             dtype=np.float64)
        axis = rng.normal(size=3)
        axis -= direction * float(np.dot(axis, direction))
        norm = float(np.linalg.norm(axis))
        if norm < 1e-6:
            continue
        axis /= norm
        angle = rng.uniform(0.0, 0.5) * spacing
        direction = (direction * math.cos(angle)
                     + axis * math.sin(angle))
        if direction[2] < 0.02:
            continue
        lat_c = math.asin(float(direction[2]))
        lon_c = math.atan2(float(direction[1]), float(direction[0])) % (
            2.0 * math.pi)
        tall = rng.uniform(0.85, 1.45)
        radius = math.radians(rng.uniform(*RADIUS))
        strength = float(rng.uniform(0.55, 1.0))
        aspect = float(rng.uniform(0.66, 0.95))
        width = float(rng.uniform(0.80, 0.98))
        if variant == "baseline":
            body = {"cx": 0.0, "cy": 0.0, "rx": width, "ry": 0.38 * tall}
            lobes = baseline_lobes(rng, tall)
            base = {"y": -0.22, "wave": 0.0, "freq": 0.9,
                    "phase": 0.0, "soft": 0.0}
        else:
            # Consume the baseline draw so the layout sequence is identical.
            baseline_lobes(rng, tall)
            body, lobes, base = variant_anatomy(
                anatomy_rng, tall, width, variant)
        specs.append({
            "u": lon_c / (2.0 * math.pi), "lat": float(lat_c),
            "radius": radius, "strength": strength, "aspect": aspect,
            "width": width, "height": tall, "body": body, "lobes": lobes,
            "base": base, "variant": variant,
        })
    return specs


def rasterize(specs, scale, dirs, warp_x, warp_y):
    height, width = dirs.shape[:2]
    field = np.zeros((height, width), dtype=np.float32)
    for spec in specs:
        radius = spec["radius"] * scale
        lon = spec["u"] * 2.0 * math.pi
        center = np.array([math.cos(spec["lat"]) * math.cos(lon),
                           math.cos(spec["lat"]) * math.sin(lon),
                           math.sin(spec["lat"])], dtype=np.float32)
        east = np.array([-math.sin(lon), math.cos(lon), 0.0], dtype=np.float32)
        up = np.cross(center, east)
        up /= max(float(np.linalg.norm(up)), 1e-6)

        # Rasterize only the mass footprint: the gnomonic shape reaches about
        # 1.8 radii including lobes and warp.
        reach = 1.8 * radius
        lat0 = max(-math.pi / 2.0, spec["lat"] - reach)
        lat1 = min(math.pi / 2.0, spec["lat"] + reach)
        row0 = max(0, int(math.floor((lat0 / math.pi + 0.5) * height)))
        row1 = min(height,
                   int(math.ceil((lat1 / math.pi + 0.5) * height)) + 1)
        if lat0 <= -math.pi / 2.0 or lat1 >= math.pi / 2.0:
            cos_min = 0.0
        else:
            cos_min = min(math.cos(lat0), math.cos(lat1))
        d_lon = (math.pi if cos_min < 0.12 else
                 math.asin(min(1.0, math.sin(reach) / cos_min)))
        col_start = int(math.floor(
            ((lon - d_lon) / (2.0 * math.pi)) * width)) - 1
        col_count = int(math.ceil(2.0 * d_lon / (2.0 * math.pi) * width)) + 3
        if col_count >= width:
            cols = np.arange(width)
        else:
            cols = np.arange(col_start, col_start + col_count) % width

        sub = dirs[row0:row1][:, cols]
        dot = sub @ center
        safe = np.maximum(dot, 0.20)
        tangent = safe * math.tan(radius)
        x = (sub @ east) / tangent + warp_x[row0:row1][:, cols]
        y = (sub @ up) / (tangent * spec["aspect"]) \
            + warp_y[row0:row1][:, cols]
        distance = mass_distance(x, y, spec)
        shape = np.clip(1.0 - np.maximum(distance, 0.0) / EDGE,
                        0.0, 1.0) * spec["strength"]
        shape *= dot > 0.20
        block = field[row0:row1, cols]
        field[row0:row1, cols] = np.maximum(block, shape)
    return field


def generate_field(width, height, seed, variant="baseline",
                   union_target=None):
    rng = np.random.default_rng(seed)
    dirs, lat = directions(width, height)
    sky = dirs[:, :, 2] >= 0.0
    # Always consume the baseline warp draws so the mass layout is identical
    # across variants at the same seed.
    warp_x = (fbm(width, height, rng, base=(48, 24), octaves=3) - 0.5) * 2.0
    warp_y = (fbm(width, height, rng, base=(48, 24), octaves=3) - 0.5) * 2.0
    if variant == "baseline":
        warp_x *= WARP
        warp_y *= WARP
    else:
        wrng = np.random.default_rng(seed + 104729)
        warp_x = np.zeros((height, width), dtype=np.float32)
        warp_y = np.zeros((height, width), dtype=np.float32)
        for base, amplitude, octaves in (((32, 16), 0.070, 2),
                                         ((96, 48), 0.035, 2),
                                         ((192, 96), 0.018, 1)):
            warp_x += ((fbm(width, height, wrng, base=base,
                            octaves=octaves) - 0.5) * 2.0) * amplitude
            warp_y += ((fbm(width, height, wrng, base=base,
                            octaves=octaves) - 0.5) * 2.0) * amplitude
    if union_target is None:
        union_target = TARGET_FOOTPRINT
    anatomy_rng = np.random.default_rng(seed + 7919)
    specs = make_masses(rng, variant, anatomy_rng)
    weights = np.where(sky, np.cos(lat)[:, None], 0.0).astype(np.float32)
    weight_sum = max(float(weights[sky].sum()), 1e-6)

    # Scale the masses until the union of their footprints is the intended
    # maximum coverage, so the threshold curve does not depend on the draw.
    scale = 1.0
    field = np.zeros((height, width), dtype=np.float32)
    for attempt in range(3):
        field = rasterize(specs, scale, dirs, warp_x, warp_y)
        field[~sky] = 0.0
        union = float(weights[sky & (field > 0.0)].sum() / weight_sum)
        if abs(union - union_target) <= 0.02:
            break
        adjust = math.sqrt(union_target / max(union, 1e-4))
        tallest = max(spec["radius"] for spec in specs) * scale
        adjust = min(adjust, math.radians(MAX_RADIUS) / max(tallest, 1e-6))
        if abs(adjust - 1.0) < 0.01 or attempt == 2:
            break
        scale *= adjust
    for spec in specs:
        spec["radius"] *= scale
    flat = field[sky]
    wflat = weights[sky]
    order = np.argsort(flat)[::-1]
    values = flat[order]
    cumulative = np.cumsum(wflat[order]) / max(float(wflat.sum()), 1e-6)

    def threshold(amount):
        if amount <= 0.0:
            return 1.5
        index = int(np.searchsorted(cumulative, amount, side="left"))
        return float(values[min(index, len(values) - 1)])

    def coverage(thr):
        mask = sky & (field > thr)
        return float(weights[mask].sum()
                     / max(float(weights[sky].sum()), 1e-6))

    return {
        "field": field, "masses": specs, "weights": weights, "sky": sky,
        "lat": lat, "threshold": threshold, "coverage": coverage,
        "union": coverage(0.0),
    }


def build_sky():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import palette
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0
    scene.frame_set(1)
    scene.ald.palette = "SUMMER_NOON"
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.ald.clouds = False
    palette.apply_palette(scene, "SUMMER_NOON")
    return scene, palette


def make_image(field, path):
    height, width = field.shape
    image = bpy.data.images.new("ALD | Cloud Distribution", width=width,
                                height=height, alpha=True, float_buffer=True)
    # Changing the colorspace reallocates the buffer: do it before writing.
    image.colorspace_settings.name = "Non-Color"
    rgba = np.empty((height, width, 4), dtype=np.float32)
    rgba[:, :, 0] = field
    rgba[:, :, 1] = field
    rgba[:, :, 2] = field
    rgba[:, :, 3] = 1.0
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    image.file_format = "OPEN_EXR"
    image.filepath_raw = path
    image.save()
    image.pack()
    return image


def setup_world(scene, image, palette):
    world = scene.world
    nt = world.node_tree
    nodes = nt.nodes
    links = nt.links
    bg = next(n for n in nodes if n.bl_idname == "ShaderNodeBackground")
    # No Vector input: the Environment Texture samples the view direction,
    # the same Generated vector the production World uses.
    env = nodes.new("ShaderNodeTexEnvironment")
    env.location = (-240, 500)
    env.image = image
    env.interpolation = "Linear"
    env.projection = "EQUIRECTANGULAR"
    bw = nodes.new("ShaderNodeRGBToBW")
    bw.location = (-40, 500)
    links.new(env.outputs["Color"], bw.inputs["Color"])

    threshold = nodes.new("ShaderNodeValue")
    threshold.name = "ALD Prototype Threshold"
    threshold.label = "Prototype Threshold"
    threshold.location = (-240, 720)
    threshold.outputs[0].default_value = 0.4
    # Hard selection: masses are whole or absent, never semi-transparent.
    mask = nodes.new("ShaderNodeMath")
    mask.operation = "GREATER_THAN"
    mask.location = (160, 500)
    mask.use_clamp = True
    links.new(bw.outputs[0], mask.inputs[0])
    links.new(threshold.outputs[0], mask.inputs[1])

    tex = nodes.new("ShaderNodeTexCoord")
    tex.location = (160, 880)
    view = nodes.new("ShaderNodeVectorMath")
    view.operation = "NORMALIZE"
    view.location = (340, 880)
    links.new(tex.outputs["Generated"], view.inputs[0])
    horizon = nodes.new("ShaderNodeSeparateXYZ")
    horizon.location = (520, 880)
    links.new(view.outputs["Vector"], horizon.inputs["Vector"])
    horizon_gate = nodes.new("ShaderNodeMapRange")
    horizon_gate.location = (700, 880)
    horizon_gate.clamp = True
    horizon_gate.inputs["From Min"].default_value = 0.0
    horizon_gate.inputs["From Max"].default_value = 0.025
    links.new(horizon.outputs["Z"], horizon_gate.inputs["Value"])

    gate = nodes.new("ShaderNodeMath")
    gate.operation = "MULTIPLY"
    gate.location = (520, 620)
    gate.use_clamp = True
    links.new(mask.outputs[0], gate.inputs[0])
    links.new(horizon_gate.outputs["Result"], gate.inputs[1])

    cloud_color = nodes.new("ShaderNodeRGB")
    cloud_color.location = (520, 380)
    cloud_color.outputs[0].default_value = (
        *palette.PRESETS["SUMMER_NOON"]["cloud_mid"], 1.0)
    mix = nodes.new("ShaderNodeMix")
    mix.location = (900, 250)
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    a_sock = b_sock = result_sock = None
    for sock in mix.inputs:
        if sock.name == "A" and sock.type == "RGBA":
            a_sock = sock
        elif sock.name == "B" and sock.type == "RGBA":
            b_sock = sock
    for sock in mix.outputs:
        if sock.name == "Result" and sock.type == "RGBA":
            result_sock = sock
    old = bg.inputs["Color"].links[0].from_socket if bg.inputs["Color"].links else None
    if old is not None:
        links.new(old, a_sock)
    else:
        a_sock.default_value = tuple(bg.inputs["Color"].default_value)
    links.new(cloud_color.outputs[0], b_sock)
    links.new(gate.outputs[0], mix.inputs["Factor"])
    links.new(result_sock, bg.inputs["Color"])
    return threshold


def render(scene, view, path):
    location, rotation = VIEWS[view]
    data = bpy.data.cameras.new("Prototype Camera")
    data.lens = 32.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Prototype Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    scene.camera = camera
    scene.render.filepath = path
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    elapsed = (time.perf_counter() - start) * 1000.0
    bpy.data.objects.remove(camera, do_unlink=True)
    return elapsed


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    start = time.perf_counter()
    data = generate_field(args["width"], args["height"], args["seed"],
                          args["variant"], args["union"])
    generation = time.perf_counter() - start
    field = data["field"]
    masses = data["masses"]
    panorama = os.path.join(out, "field_s%02d_%dx%d.exr" % (
        args["seed"], args["width"], args["height"]))
    seam = float(np.abs(field[:, 0] - field[:, -1]).max())
    neighbour = float(np.abs(field[:, 1:] - field[:, :-1]).max())

    scene, palette = build_sky()
    image = make_image(field, panorama)
    threshold = setup_world(scene, image, palette)
    report = {
        "seed": args["seed"], "size": [args["width"], args["height"]],
        "variant": args["variant"], "union_target": args["union"],
        "masses": len(masses),
        "masses_detail": [{"u": round(m["u"], 4),
                           "lat": round(math.degrees(m["lat"]), 2),
                           "radius": round(math.degrees(m["radius"]), 2),
                           "strength": round(m["strength"], 3),
                           "lobes": len(m["lobes"])} for m in masses],
        "generation_ms": round(generation * 1000, 1),
        "field_nbytes": int(field.nbytes),
        "image_nbytes": int(args["width"] * args["height"] * 16),
        "panorama": os.path.basename(panorama),
        "seam_max_delta": round(seam, 4),
        "neighbour_max_delta": round(neighbour, 4),
        "union_coverage": round(data["union"], 4),
        "amounts": {}, "renders": [],
    }
    for amount in args["amounts"]:
        thr = data["threshold"](amount)
        coverage = data["coverage"](thr)
        report["amounts"][str(amount)] = {
            "threshold": round(thr, 4),
            "global_coverage": round(coverage, 4),
        }
        threshold.outputs[0].default_value = 1.5 if amount <= 0 else thr
        for view in args["views"]:
            name = "proto_s%02d_%s_a%03d_1280x720.png" % (
                args["seed"], view, round(amount * 100))
            elapsed = render(scene, view, os.path.join(out, name))
            report["renders"].append({"seed": args["seed"], "view": view,
                                      "amount": amount, "file": name,
                                      "global_coverage": round(coverage, 4),
                                      "render_ms": round(elapsed, 1)})
            print("PROTO", args["seed"], view, amount,
                  "global %.3f" % coverage, "render %.0fms" % elapsed)
    threshold.outputs[0].default_value = 1.5
    for view in args["views"]:
        name = "proto_s%02d_%s_off_1280x720.png" % (args["seed"], view)
        render(scene, view, os.path.join(out, name))
    if args["save"]:
        bpy.ops.wm.save_as_mainfile(filepath=args["save"])
        report["blend_bytes"] = os.path.getsize(args["save"])
    report["image_packed"] = bool(image.packed_file)
    with open(os.path.join(out, "proto_s%02d.json" % args["seed"]), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("PROTO", args["seed"], "gen %.1fms" % (generation * 1000),
          "variant", args["variant"], "size", args["width"], args["height"],
          "masses", len(masses),
          "union %.3f" % data["union"], "packed", bool(image.packed_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
