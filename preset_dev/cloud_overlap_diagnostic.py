"""Overlap diagnosis for the 2D Cumulus prototype.

Builds the four diagnostic configurations:
  A  baseline anatomy   + baseline radii
  B  hierarchical       + baseline radii
  C  baseline anatomy   + hierarchical radii
  D  hierarchical       + hierarchical radii

and renders per-mass coloured masks (overlaps in white) plus the usual binary
masks. Metrics are computed on the panorama and on the rendered frames.

    blender -b --factory-startup --python preset_dev/cloud_overlap_diagnostic.py
"""

import colorsys
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cloud_distribution_proto as proto  # noqa: E402

W, H = 2048, 1024
VIEWS = proto.VIEWS
CONFIGS = (("A", "baseline", "base"),
           ("B", "hierarchical", "base"),
           ("C", "baseline", "hier"),
           ("D", "hierarchical", "hier"))


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_overlap"),
              "radii_base": "", "radii_hier": "", "seeds": "3,17,42",
              "views": "main,right", "amount": "0.42", "renders": "1"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
    values["views"] = [x for x in values["views"].split(",") if x]
    values["amount"] = float(values["amount"])
    values["renders"] = values["renders"] == "1"
    return values


def mass_palette(count):
    colors = np.empty((count, 3), dtype=np.float32)
    for index in range(count):
        hue = (index * 0.7548776662466927 + 0.11) % 1.0
        saturation = 0.70 + 0.22 * ((index * 0.5698402910) % 1.0)
        value = 0.86 + 0.12 * ((index * 0.438579) % 1.0)
        colors[index] = colorsys.hsv_to_rgb(hue, saturation, value)
    return colors


def mass_masks(specs, dirs, warp_x, warp_y, thresholds):
    """Per-mass masks at each threshold; returns count, labels, best field."""
    height, width = dirs.shape[:2]
    results = []
    for _threshold in thresholds:
        results.append({
            "count": np.zeros((height, width), dtype=np.uint8),
            "labels": np.full((height, width, 4), -1, dtype=np.int16),
            "best": np.zeros((height, width), dtype=np.float32),
            "best_label": np.full((height, width), -1, dtype=np.int16),
            "active": 0,
        })
    for index, spec in enumerate(specs):
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
        distance = proto.mass_distance(x, y, spec)
        field = np.clip(1.0 - np.maximum(distance, 0.0) / proto.EDGE,
                        0.0, 1.0) * spec["strength"]
        field *= dot > 0.20
        for result, threshold in zip(results, thresholds):
            mask = field > threshold
            if mask.any():
                result["active"] += 1
            view_count = result["count"][row0:row1][:, cols]
            view_labels = result["labels"][row0:row1][:, cols]
            for slot in range(4):
                free = mask & (view_count == slot)
                view_labels[..., slot][free] = index
            view_count[mask] += 1
            result["count"][row0:row1][:, cols] = view_count
            result["labels"][row0:row1][:, cols] = view_labels
            view_best = result["best"][row0:row1][:, cols]
            view_best_label = result["best_label"][row0:row1][:, cols]
            better = mask & (field > view_best)
            view_best[better] = field[better]
            view_best_label[better] = index
            result["best"][row0:row1][:, cols] = view_best
            result["best_label"][row0:row1][:, cols] = view_best_label
    return results


def panorama_components(count, weights, sky):
    """4-connected components on a downsampled panorama, u wraps."""
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
    minimum = 0.0002 * total
    areas = [area for area in areas if area >= minimum]
    areas.sort(reverse=True)
    return len(areas), (round(areas[0] / total, 4) if areas else 0.0)


def summarize(result, weights, sky, amount):
    count = result["count"]
    labels = result["labels"]
    total = max(float(weights[sky].sum()), 1e-9)
    covered = count >= 1
    overlap = count >= 2
    pair_area = float((weights * (count.astype(np.int32)
                                  * (count.astype(np.int32) - 1) / 2.0)).sum())
    pairs = set()
    for first in range(4):
        for second in range(first + 1, 4):
            both = overlap & (labels[..., first] >= 0) \
                & (labels[..., second] >= 0)
            if not both.any():
                continue
            one = labels[..., first][both].astype(np.int64)
            two = labels[..., second][both].astype(np.int64)
            keys = np.minimum(one, two) * 10000 + np.maximum(one, two)
            pairs |= set(np.unique(keys).tolist())
    components, dominant = panorama_components(count, weights, sky)
    return {
        "active_masses": int(result["active"]),
        "overlapping_pairs": len(pairs),
        "overlap_area": round(float(weights[overlap].sum()) / total, 4),
        "pairwise_overlap": round(pair_area / total, 4),
        "global_coverage": round(float(weights[covered].sum()) / total, 4),
        "panorama_components": components,
        "panorama_dominant": dominant,
    }


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


def build_world(scene):
    world = scene.world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    bg = next(n for n in nodes if n.bl_idname == "ShaderNodeBackground")
    env = nodes.new("ShaderNodeTexEnvironment")
    env.location = (-300, 520)
    env.projection = "EQUIRECTANGULAR"
    bw = nodes.new("ShaderNodeRGBToBW")
    bw.location = (-80, 520)
    links.new(env.outputs["Color"], bw.inputs["Color"])
    presence = nodes.new("ShaderNodeMapRange")
    presence.location = (120, 520)
    presence.clamp = True
    presence.inputs["From Min"].default_value = 0.0
    presence.inputs["From Max"].default_value = 0.01
    links.new(bw.outputs[0], presence.inputs["Value"])
    mix = nodes.new("ShaderNodeMix")
    mix.location = (860, 320)
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
    old = bg.inputs["Color"].links[0].from_socket \
        if bg.inputs["Color"].links else None
    if old is not None:
        links.new(old, a_sock)
    links.new(env.outputs["Color"], b_sock)
    links.new(presence.outputs["Result"], mix.inputs["Factor"])
    links.new(result_sock, bg.inputs["Color"])
    return env


def render(scene, view, path):
    location, rotation = VIEWS[view]
    data = bpy.data.cameras.new("Overlap Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Overlap Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = rotation
    scene.camera = camera
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    return path


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene, palette = proto.build_sky()
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.eevee.taa_render_samples = 32
    env = build_world(scene)
    black = bpy.data.images.new("Black", 2, 1, alpha=False,
                                float_buffer=False)
    black.colorspace_settings.name = "Non-Color"
    black.pixels.foreach_set(np.zeros(2 * 1 * 4, dtype=np.float32))
    black.update()
    env.image = black
    dirs, _lat = proto.directions(W, H)
    report = {"configs": {tag: {"anatomy": anatomy, "radii": radii}
                          for tag, anatomy, radii in CONFIGS},
              "amount": args["amount"], "size": [W, H],
              "records": []}
    if args["renders"]:
        for view in args["views"]:
            render(scene, view, os.path.join(out, "overlap_off_%s.png" % view))
    for seed in args["seeds"]:
        data = {}
        fixed = None
        for tag, anatomy, radii in CONFIGS:
            source = args["radii_base"] if radii == "base" else args["radii_hier"]
            data[tag] = proto.generate_field(
                W, H, seed, anatomy, radii_from=source)
            if tag == "D":
                fixed = data[tag]["threshold"](args["amount"])
        for tag, anatomy, radii in CONFIGS:
            item = data[tag]
            threshold = item["threshold"](args["amount"])
            results = mass_masks(item["masses"], dirs, item["warp_x"],
                                 item["warp_y"], [threshold, fixed])
            standard = summarize(results[0], item["weights"], item["sky"],
                                 args["amount"])
            fixed_item = summarize(results[1], item["weights"], item["sky"],
                                   args["amount"])
            colors = mass_palette(len(item["masses"]))
            count = results[0]["count"]
            covered = count >= 1
            overlap = count >= 2
            label = np.where(covered, results[0]["best_label"], 0)
            rgb = np.zeros((H, W, 3), dtype=np.float32)
            rgb[covered] = colors[label[covered]]
            rgb[overlap] = 1.0
            path = os.path.join(out, "overlap_%s_s%02d_panorama.png"
                                % (tag, seed))
            image = save_png(rgb, path, "Overlap %s %d" % (tag, seed))
            env.image = image
            if args["renders"]:
                for view in args["views"]:
                    render(scene, view, os.path.join(
                        out, "overlap_%s_s%02d_%s.png" % (tag, seed, view)))
            bpy.data.images.remove(image)
            record = {
                "config": tag, "seed": seed,
                "anatomy": anatomy, "radii": radii,
                "threshold": round(float(threshold), 4),
                "fixed_threshold": round(float(fixed), 4),
                "standard": standard, "fixed": fixed_item,
            }
            report["records"].append(record)
            print("OVERLAP", tag, seed, "cov", standard["global_coverage"],
                  "act", standard["active_masses"],
                  "pairs", standard["overlapping_pairs"],
                  "ovl", standard["overlap_area"],
                  "comp", standard["panorama_components"],
                  "dom", standard["panorama_dominant"],
                  "| fixed cov", fixed_item["global_coverage"],
                  "pairs", fixed_item["overlapping_pairs"],
                  "ovl", fixed_item["overlap_area"],
                  "comp", fixed_item["panorama_components"])
    with open(os.path.join(out, "diagnostic.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
