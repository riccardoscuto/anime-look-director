"""Footprint-aware Cumulus distribution (candidate F) and A/B/F comparison.

Phase A established that 92-94 fixed silhouettes at the original radii total
0.302-0.324 of the hemisphere: no repositioning reaches 0.42. Candidate F
raises the mass budget and places the centres using the silhouette footprint;
Cloud Amount activates whole masses while the contour stays fixed.

    blender -b --factory-startup --python preset_dev/cloud_footprint.py -- --stage full
"""

import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cloud_distribution_proto as proto  # noqa: E402

W, H = 2048, 1024
AA = 0.02
GOLDEN = 0.6180339887498949
VIEWS = ("main", "right")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_footprint"),
              "radii_base": "", "seeds": "3,17,42",
              "views": "main,right", "amounts": "0.18,0.30,0.42",
              "count": "184", "soft": "0.9", "stage": "test",
              "renders": "1"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
    values["views"] = [x for x in values["views"].split(",") if x]
    values["amounts"] = [float(x) for x in values["amounts"].split(",") if x]
    values["count"] = int(values["count"])
    values["soft"] = float(values["soft"])
    return values


def mass_palette(count):
    import colorsys
    colors = np.empty((count, 3), dtype=np.float32)
    for index in range(count):
        hue = (index * 0.7548776662466927 + 0.11) % 1.0
        saturation = 0.70 + 0.22 * ((index * 0.5698402910) % 1.0)
        value = 0.86 + 0.12 * ((index * 0.438579) % 1.0)
        colors[index] = colorsys.hsv_to_rgb(hue, saturation, value)
    return colors


def fibonacci(count, rng):
    spacing = math.sqrt(2.0 * math.pi / count)
    points = np.empty((count, 3), dtype=np.float64)
    for index in range(count):
        z = (index + 0.5) / count
        lon = (index * GOLDEN) % 1.0 * 2.0 * math.pi
        ring = math.sqrt(max(0.0, 1.0 - z * z))
        direction = np.array([ring * math.cos(lon), ring * math.sin(lon), z])
        axis = rng.normal(size=3)
        axis -= direction * float(np.dot(axis, direction))
        norm = float(np.linalg.norm(axis))
        if norm < 1e-6:
            continue
        axis /= norm
        angle = rng.uniform(0.0, 0.5) * spacing
        points[index] = (direction * math.cos(angle)
                         + axis * math.sin(angle))
    return points


def relax(points, feet, soft, iterations=40):
    count = len(points)
    for iteration in range(iterations):
        step = 0.45 * (1.0 - iteration / iterations) + 0.05
        displacement = np.zeros_like(points)
        moved = False
        for first in range(count - 1):
            dots = np.clip(points[first + 1:] @ points[first], -1.0, 1.0)
            distance = np.arccos(dots)
            need = soft * (feet[first] + feet[first + 1:])
            close = distance < need
            if not close.any():
                continue
            tangent = points[first + 1:][close] \
                - np.outer(dots[close], points[first])
            norms = np.linalg.norm(tangent, axis=1)
            valid = norms > 1e-9
            if not valid.any():
                continue
            tangent = tangent[valid] / norms[valid][:, None]
            delta = (need[close][valid] - distance[close][valid]) \
                * 0.25 * step
            push = tangent * delta[:, None]
            displacement[first] -= push.sum(axis=0)
            indices = np.arange(first + 1, count)[close][valid]
            np.add.at(displacement, indices, push)
            moved = True
        points = points + displacement
        points /= np.linalg.norm(points, axis=1)[:, None]
        if not moved:
            break
    return points


def footprint_specs(seed, count, soft):
    rng = np.random.default_rng(seed + 31013)
    points = fibonacci(count, rng)
    radius_rng = np.random.default_rng(seed + 41017)
    radii = np.radians(radius_rng.uniform(5.0, 9.9, count))
    feet = 0.65 * radii
    points = relax(points, feet, soft)
    anatomy_rng = np.random.default_rng(seed + 51019)
    specs = []
    for index in range(count):
        if points[index][2] < 0.02:
            continue
        lat = math.asin(float(np.clip(points[index][2], -1.0, 1.0)))
        lon = math.atan2(float(points[index][1]), float(points[index][0])) \
            % (2.0 * math.pi)
        tall = anatomy_rng.uniform(0.85, 1.45)
        width = anatomy_rng.uniform(0.80, 0.98)
        aspect = anatomy_rng.uniform(0.66, 0.95)
        strength = float(anatomy_rng.uniform(0.55, 1.0))
        body, lobes, base = proto.variant_anatomy(
            anatomy_rng, tall, width, "hierarchical")
        specs.append({
            "u": lon / (2.0 * math.pi), "lat": lat,
            "radius": radii[index], "strength": strength, "aspect": aspect,
            "width": width, "height": tall, "body": body, "lobes": lobes,
            "base": base, "variant": "hierarchical",
        })
    return specs


def variant_warp(width, height, seed):
    wrng = np.random.default_rng(seed + 104729)
    wx = np.zeros((height, width), dtype=np.float32)
    wy = np.zeros((height, width), dtype=np.float32)
    for base, amplitude, octaves in (((32, 16), 0.070, 2),
                                     ((96, 48), 0.035, 2),
                                     ((192, 96), 0.018, 1)):
        wx += ((proto.fbm(width, height, wrng, base=base, octaves=octaves)
                - 0.5) * 2.0) * amplitude
        wy += ((proto.fbm(width, height, wrng, base=base, octaves=octaves)
                - 0.5) * 2.0) * amplitude
    return wx, wy


def mass_field(spec, dirs, warp_x, warp_y):
    radius = spec["radius"]
    lon = spec["u"] * 2.0 * math.pi
    center = np.array([math.cos(spec["lat"]) * math.cos(lon),
                       math.cos(spec["lat"]) * math.sin(lon),
                       math.sin(spec["lat"])], dtype=np.float32)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0], dtype=np.float32)
    up = np.cross(center, east)
    up /= max(float(np.linalg.norm(up)), 1e-6)
    reach = 1.8 * radius
    lat0 = max(-math.pi / 2.0, spec["lat"] - reach)
    lat1 = min(math.pi / 2.0, spec["lat"] + reach)
    height, width = dirs.shape[:2]
    row0 = max(0, int(math.floor((lat0 / math.pi + 0.5) * height)))
    row1 = min(height, int(math.ceil((lat1 / math.pi + 0.5) * height)) + 1)
    if lat0 <= -math.pi / 2.0 or lat1 >= math.pi / 2.0:
        cos_min = 0.0
    else:
        cos_min = min(math.cos(lat0), math.cos(lat1))
    d_lon = (math.pi if cos_min < 0.12 else
             math.asin(min(1.0, math.sin(reach) / cos_min)))
    col_start = int(math.floor(
        ((lon - d_lon) / (2.0 * math.pi) * width))) - 1
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
    distance = proto.mass_distance(x, y, spec)
    height_trim = np.clip(0.5 - distance / AA, 0.0, 1.0)
    density = np.clip(1.0 - np.maximum(distance, 0.0) / proto.EDGE,
                      0.0, 1.0) * spec["strength"]
    gate = dot > 0.20
    return row0, row1, cols, height_trim * gate, density * gate


def density_composites(specs, dirs, wx, wy, thresholds, weights, sky):
    height, width = dirs.shape[:2]
    state = {}
    for threshold in thresholds:
        state[threshold] = {
            "count": np.zeros((height, width), dtype=np.uint8),
            "labels": np.full((height, width, 4), -1, dtype=np.int16),
            "best": np.zeros((height, width), dtype=np.float32),
            "best_label": np.full((height, width), -1, dtype=np.int16),
            "areas": [],
        }
    for index, spec in enumerate(specs):
        row0, row1, cols, _geom, density = mass_field(
            spec, dirs, wx, wy)
        for threshold in thresholds:
            state[threshold]["areas"].append(float(weights[
                row0:row1][:, cols][(density > threshold)
                                     & sky[row0:row1][:, cols]].sum()))
            mask = density > threshold
            item = state[threshold]
            view_count = item["count"][row0:row1][:, cols]
            view_labels = item["labels"][row0:row1][:, cols]
            for slot in range(4):
                free = mask & (view_count == slot)
                view_labels[..., slot][free] = index
            view_count[mask] += 1
            item["count"][row0:row1][:, cols] = view_count
            item["labels"][row0:row1][:, cols] = view_labels
            view_best = item["best"][row0:row1][:, cols]
            view_label = item["best_label"][row0:row1][:, cols]
            better = mask & (density > view_best)
            view_best[better] = density[better]
            view_label[better] = index
            item["best"][row0:row1][:, cols] = view_best
            item["best_label"][row0:row1][:, cols] = view_label
    return state


def geometry_composites(specs, dirs, wx, wy, cutoffs, weights, sky):
    """cutoffs: {amount: number of active masses in the strength order}."""
    height, width = dirs.shape[:2]
    order = np.argsort([-spec["strength"] for spec in specs])
    rank = {int(index): position for position, index in enumerate(order)}
    state = {}
    for amount, cutoff in cutoffs.items():
        state[amount] = {
            "count": np.zeros((height, width), dtype=np.uint8),
            "labels": np.full((height, width, 4), -1, dtype=np.int16),
            "best": np.zeros((height, width), dtype=np.float32),
            "best_label": np.full((height, width), -1, dtype=np.int16),
            "areas": [],
        }
    areas = []
    for index, spec in enumerate(specs):
        row0, row1, cols, geom, _density = mass_field(spec, dirs, wx, wy)
        mask = geom >= 0.5
        areas.append(float(weights[row0:row1][:, cols][
            mask & sky[row0:row1][:, cols]].sum()))
        for amount, cutoff in cutoffs.items():
            if rank[index] >= cutoff:
                continue
            item = state[amount]
            view_count = item["count"][row0:row1][:, cols]
            view_labels = item["labels"][row0:row1][:, cols]
            for slot in range(4):
                free = mask & (view_count == slot)
                view_labels[..., slot][free] = index
            view_count[mask] += 1
            item["count"][row0:row1][:, cols] = view_count
            item["labels"][row0:row1][:, cols] = view_labels
            view_best = item["best"][row0:row1][:, cols]
            view_label = item["best_label"][row0:row1][:, cols]
            better = geom > view_best
            view_best[better] = geom[better]
            view_label[better] = index
            item["best"][row0:row1][:, cols] = view_best
            item["best_label"][row0:row1][:, cols] = view_label
            view_count = item["count"][row0:row1][:, cols]
    return state, areas, rank


def activation_cutoffs(specs, dirs, wx, wy, amounts, weights, sky):
    order = np.argsort([-spec["strength"] for spec in specs])
    union = np.zeros(dirs.shape[:2], dtype=bool)
    total = max(float(weights[sky].sum()), 1e-9)
    coverages = []
    for index in order:
        row0, row1, cols, geom, _density = mass_field(
            specs[int(index)], dirs, wx, wy)
        mask = geom >= 0.5
        union[row0:row1, cols] |= mask
        coverages.append(float(weights[union].sum()) / total)
    cutoffs = {}
    achieved = {}
    for amount in amounts:
        found = None
        for position, coverage in enumerate(coverages):
            if coverage >= amount:
                found = position + 1
                break
        if found is None:
            found = len(order)
        cutoffs[amount] = found
        achieved[amount] = coverages[found - 1]
    return cutoffs, achieved, coverages


def save_png(rgb, path, name):
    height, width = rgb.shape[:2]
    image = bpy.data.images.new(name, width=width, height=height,
                                alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(rgb, 0.0, 1.0)
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    image.file_format = "PNG"
    image.filepath_raw = path
    image.save()
    image.pack()
    return image


def color_image(state, colors):
    height, width = state["count"].shape
    rgb = np.zeros((height, width, 3), dtype=np.float32)
    covered = state["count"] >= 1
    overlap = state["count"] >= 2
    index = np.where(covered, state["best_label"], 0)
    rgb[covered] = colors[index[covered]]
    rgb[overlap] = 1.0
    return rgb


def overlay_metrics(state, weights, sky):
    total = max(float(weights[sky].sum()), 1e-9)
    covered = (state["count"] >= 1) & sky
    overlap = (state["count"] >= 2) & sky
    pair_area = float((weights * (state["count"].astype(np.int32)
                                  * (state["count"].astype(np.int32) - 1)
                                  / 2.0)).sum())
    return {
        "coverage": round(float(weights[covered].sum()) / total, 4),
        "overlap_area": round(float(weights[overlap].sum()) / total, 4),
        "pairwise_overlap": round(pair_area / total, 4),
    }


def panorama_components(count, weights, sky):
    step = 4
    height, width = count.shape
    rows = height // step
    cols = width // step
    covered = count.reshape(rows, step, cols, step).mean(axis=(1, 3)) > 0.5
    box = weights.reshape(rows, step, cols, step).sum(axis=(1, 3))
    seen = np.zeros_like(covered, dtype=bool)
    areas = []
    for row in range(rows):
        for col in range(cols):
            if not covered[row, col] or seen[row, col]:
                continue
            stack = [(row, col)]
            seen[row, col] = True
            area = 0.0
            while stack:
                y, x = stack.pop()
                area += float(box[y, x])
                for ny, nx in ((y - 1, x), (y + 1, x),
                               (y, (x - 1) % cols), (y, (x + 1) % cols)):
                    if 0 <= ny < rows and covered[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            areas.append(area)
    total = max(float(weights[sky].sum()), 1e-9)
    areas = sorted([area for area in areas if area >= 0.0002 * total],
                   reverse=True)
    return len(areas), (round(areas[0] / total, 4) if areas else 0.0)


def build_world(scene, palette_module):
    return proto.setup_world(scene, None, palette_module)


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    dirs, _lat = proto.directions(W, H)
    sky = dirs[:, :, 2] >= 0.0
    lat = np.arcsin(np.clip(dirs[:, :, 2], -1.0, 1.0))
    weights = np.where(sky, np.cos(lat), 0.0).astype(np.float32)
    total = max(float(weights[sky].sum()), 1e-9)
    report = {"stage": args["stage"], "amounts": args["amounts"],
              "count": args["count"], "soft": args["soft"], "records": []}
    if args["stage"] == "test":
        for seed in args["seeds"]:
            specs = footprint_specs(seed, args["count"], args["soft"])
            wx, wy = variant_warp(W, H, seed)
            count = np.zeros((H, W), dtype=np.uint8)
            union = np.zeros((H, W), dtype=bool)
            for spec in specs:
                row0, row1, cols, geom, _density = mass_field(
                    spec, dirs, wx, wy)
                mask = geom >= 0.5
                union[row0:row1, cols] |= mask
            coverage = float(weights[union].sum()) / total
            report["records"].append({
                "seed": seed, "masses": len(specs),
                "union": round(coverage, 4)})
            print("FOOTPRINT", seed, "masses", len(specs),
                  "union", round(coverage, 4))
        with open(os.path.join(out, "footprint_test.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        return 0

    renders = args.get("renders", "1") == "1"
    env = None
    threshold_node = None
    black = None
    if renders:
        scene, palette_module = proto.build_sky()
        scene.view_settings.view_transform = "AgX"
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.image_settings.color_mode = "RGB"
        scene.render.use_compositing = False
        scene.eevee.taa_render_samples = 32
        threshold_node = build_world(scene, palette_module)
        env = next(node for node in scene.world.node_tree.nodes
                   if node.bl_idname == "ShaderNodeTexEnvironment")
        black = bpy.data.images.new("Black", 2, 1, alpha=False,
                                    float_buffer=False)
        black.colorspace_settings.name = "Non-Color"
        black.pixels.foreach_set(np.zeros(8, dtype=np.float32))
        black.update()
        env.image = black
        for view in args["views"]:
            proto.render(scene, view, os.path.join(
                out, "look_off_%s.png" % view))

    configs = ("A", "B", "F")
    for config in configs:
        for seed in args["seeds"]:
            start = time.perf_counter()
            if config == "A":
                data = proto.generate_field(W, H, seed, "baseline",
                                            union_target=0.5)
                specs = data["masses"]
                wx = data["warp_x"]
                wy = data["warp_y"]
                thresholds = [data["threshold"](amount)
                              for amount in args["amounts"]]
                state = density_composites(specs, dirs, wx, wy, thresholds,
                                           weights, sky)
                per_amount = {}
                for amount, threshold in zip(args["amounts"], thresholds):
                    per_amount[amount] = {
                        "threshold": round(float(threshold), 4),
                        "state": state[threshold],
                        "areas": state[threshold]["areas"],
                    }
                texture = proto.make_image(
                    data["field"], os.path.join(
                        out, "field_A_s%02d.exr" % seed)) \
                    if renders else None
                textures = {amount: texture for amount in args["amounts"]}
                threshold_values = {amount: threshold
                                    for amount, threshold in zip(
                                        args["amounts"], thresholds)}
            else:
                if config == "B":
                    data = proto.generate_field(
                        W, H, seed, "hierarchical",
                        radii_from=args["radii_base"])
                    specs = data["masses"]
                    wx = data["warp_x"]
                    wy = data["warp_y"]
                else:
                    specs = footprint_specs(seed, args["count"], args["soft"])
                    wx, wy = variant_warp(W, H, seed)
                cutoffs, achieved, coverages = activation_cutoffs(
                    specs, dirs, wx, wy, args["amounts"], weights, sky)
                state, areas, rank = geometry_composites(
                    specs, dirs, wx, wy, cutoffs, weights, sky)
                per_amount = {}
                textures = {}
                threshold_values = {}
                for amount in args["amounts"]:
                    per_amount[amount] = {
                        "threshold": 0.5,
                        "cutoff": cutoffs[amount],
                        "requested": amount,
                        "union_coverage": round(achieved[amount], 4),
                        "state": state[amount],
                        "areas": areas,
                    }
                    texture = proto.make_image(
                        state[amount]["best"], os.path.join(
                            out, "field_%s_s%02d_a%03d.exr"
                            % (config, seed, round(amount * 100)))) \
                        if renders else None
                    textures[amount] = texture
                    threshold_values[amount] = 0.5
            generation = (time.perf_counter() - start) * 1000.0
            colors = mass_palette(len(specs))
            for amount in args["amounts"]:
                item = per_amount[amount]
                state_item = item["state"]
                metrics = overlay_metrics(state_item, weights, sky)
                components, dominant = panorama_components(
                    state_item["count"], weights, sky)
                rgb = color_image(state_item, colors)
                save_png(rgb, os.path.join(
                    out, "color_%s_s%02d_a%03d.png"
                    % (config, seed, round(amount * 100))),
                    "Color %s %d %.2f" % (config, seed, amount))
                if renders:
                    env.image = textures[amount]
                    threshold_node.outputs[0].default_value = \
                        threshold_values[amount]
                    for view in args["views"]:
                        proto.render(scene, view, os.path.join(
                            out, "look_%s_s%02d_a%03d_%s.png"
                            % (config, seed, round(amount * 100), view)))
                active = int(np.count_nonzero(
                    np.unique(state_item["labels"][
                        state_item["count"] >= 1]) >= 0))
                record = {
                    "config": config, "seed": seed, "amount": amount,
                    "coverage": metrics["coverage"],
                    "overlap_area": metrics["overlap_area"],
                    "pairwise_overlap": metrics["pairwise_overlap"],
                    "active_masses": active,
                    "panorama_components": components,
                    "panorama_dominant": dominant,
                    "threshold": item.get("threshold"),
                    "cutoff": item.get("cutoff"),
                    "union_coverage": item.get("union_coverage"),
                    "mean_mass_area": round(float(np.mean(item["areas"]))
                                            / total, 5)
                    if item.get("areas") else None,
                    "generation_ms": round(generation, 1),
                }
                report["records"].append(record)
                print("FOOTPRINT", config, seed, amount,
                      "cov", metrics["coverage"], "active", active,
                      "comp", components, "dom", dominant)
                if renders and config != "A":
                    bpy.data.images.remove(textures[amount])
            if renders and config == "A":
                bpy.data.images.remove(texture)
            if renders:
                env.image = black
    with open(os.path.join(out, "footprint.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
