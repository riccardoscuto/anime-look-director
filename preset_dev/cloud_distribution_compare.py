"""Build the 2D cloud-distribution evidence: sheets, masks and metrics.

Reads the prototype renders (3 seeds x 3 amounts x 2 views), the A reference
renders, the Cloud Amount curve, the panorama previews and the v1.0.3 baseline.
Writes contact sheets, metrics.json and the comparison report data.
"""

import glob
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (3, 17, 42)
VIEWS = ("main", "right")
AMOUNTS = (18, 30, 42)
THRESHOLD = 0.02
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mask_from(on, off):
    diff = np.abs(on - off).max(axis=2)
    image = Image.fromarray((diff > THRESHOLD).astype(np.uint8) * 255, "L")
    image = image.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.MinFilter(3))
    image = image.filter(ImageFilter.MinFilter(3)).filter(
        ImageFilter.MaxFilter(3))
    return np.asarray(image) > 127


def mask_image(mask):
    return Image.fromarray(mask.astype(np.uint8) * 255, "L")


def perimeter(mask):
    eroded = np.asarray(mask_image(mask).filter(
        ImageFilter.MinFilter(3))) > 127
    boundary = mask & ~eroded
    boundary[0, :] = False
    boundary[-1, :] = False
    boundary[:, 0] = False
    boundary[:, -1] = False
    pixels = int(boundary.sum())
    area = int(mask.sum())
    return {"pixels": pixels,
            "norm": round(float(pixels / max(np.sqrt(area), 1.0)), 3)}


def components(mask, minimum=0.002):
    small = mask_image(mask).resize((320, 180), Image.Resampling.BOX)
    grid = np.asarray(small) > 127
    height, width = grid.shape
    seen = np.zeros_like(grid, dtype=bool)
    found = []
    for y in range(height):
        for x in range(width):
            if not grid[y, x] or seen[y, x]:
                continue
            queue = deque([(x, y)])
            seen[y, x] = True
            area = 0
            while queue:
                px, py = queue.popleft()
                area += 1
                for nx, ny in ((px - 1, py), (px + 1, py),
                               (px, py - 1), (px, py + 1)):
                    if (0 <= nx < width and 0 <= ny < height
                            and grid[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            fraction = area / (width * height)
            if fraction >= minimum:
                found.append(round(float(fraction), 4))
    return sorted(found, reverse=True)


def metrics(name, image, mask, extra=None):
    height, width = mask.shape
    rows = np.where(mask.any(axis=1))[0]
    boundary = perimeter(mask)
    areas = components(mask)
    record = {
        "name": name,
        "coverage": round(float(mask.mean()), 4),
        "components": len(areas),
        "component_areas": areas,
        "largest_component": areas[0] if areas else 0.0,
        "perimeter_norm": boundary["norm"],
        "vertical_span": (float(rows.max() - rows.min()) / height
                          if len(rows) else 0.0),
        "threshold": THRESHOLD,
    }
    if extra:
        record.update(extra)
    return record


def analyze(on_path, off_path):
    image = load(on_path)
    mask = mask_from(image, load(off_path))
    return image, mask


def cell(image, text, label_font, size):
    if not isinstance(image, Image.Image):
        image = Image.fromarray((image * 255).astype(np.uint8))
    image = image.resize(size, Image.Resampling.LANCZOS)
    header = 30
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image.convert("RGB"), (0, header))
    ImageDraw.Draw(canvas).text((8, 6), text, fill=(235, 235, 235),
                                font=label_font)
    return canvas


def sheet(rows, path, size, label_size=15):
    label = font(label_size)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = max(len(row) for row in cells) * size[0]
    heights = [max(item.size[1] for item in row) for row in cells]
    canvas = Image.new("RGB", (width, sum(heights)), (12, 12, 14))
    y = 0
    for row, row_height in zip(cells, heights):
        x = 0
        for item in row:
            canvas.paste(item, (x, y))
            x += size[0]
        y += row_height
    canvas.save(path)
    return canvas.size


def chart(points, path):
    width, height = 900, 520
    canvas = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    label = font(18)
    small = font(14)
    left, top, right, bottom = 80, 50, 860, 450
    draw.rectangle([left, top, right, bottom], outline=(80, 80, 84))
    for index in range(6):
        y = bottom - (bottom - top) * index / 5
        draw.line([left, y, right, y], fill=(38, 38, 42))
        draw.text((20, y - 8), "%.1f" % (index * 0.1),
                  fill=(200, 200, 200), font=small)
    for index in range(6):
        x = left + (right - left) * index / 5
        draw.line([x, top, x, bottom], fill=(38, 38, 42))
        draw.text((x - 12, bottom + 10), "%.2f" % (index * 0.1),
                  fill=(200, 200, 200), font=small)
    draw.line([left, bottom, right, top], fill=(110, 110, 110), width=1)
    draw.text((left + 8, bottom - 22), "identity", fill=(150, 150, 150),
              font=small)
    for name, color, key in (("global coverage", (90, 200, 255),
                              "global_coverage"),
                             ("frame main", (255, 160, 90), "main"),
                             ("frame right", (255, 220, 110), "right")):
        values = points.get(key)
        if not values:
            continue
        line = []
        for amount, value in values:
            x = left + (right - left) * min(1.0, amount / 0.5)
            y = bottom - (bottom - top) * min(0.5, value) / 0.5
            line.append((x, y))
        if len(line) > 1:
            draw.line(line, fill=color, width=3)
        for point in line:
            draw.ellipse([point[0] - 4, point[1] - 4,
                          point[0] + 4, point[1] + 4], fill=color)
        draw.text((left + 12, top + 8 + 26 * (
            ("global coverage", "frame main", "frame right").index(name))),
            name, fill=color, font=label)
    draw.text((left, 14), "Cloud Amount -> coverage (seed 17)",
              fill=(230, 230, 230), font=label)
    canvas.save(path)


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_distribution"),
              "final": "", "curve": "", "preview": "", "resolution": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    out = os.path.abspath(values["out"])
    final = os.path.abspath(values["final"])
    curve = os.path.abspath(values["curve"])
    preview = os.path.abspath(values["preview"])
    resolution = os.path.abspath(values["resolution"])
    os.makedirs(out, exist_ok=True)

    v1_image = load(V1_IMAGE)
    v1_mask = np.asarray(Image.open(V1_MASK).convert("L")) > 127
    v1 = metrics("v1.0.3", v1_image, v1_mask)

    proto = []
    ref = []
    for seed in SEEDS:
        for view in VIEWS:
            off = os.path.join(final, "proto_s%02d_%s_off_1280x720.png"
                               % (seed, view))
            for amount in AMOUNTS:
                path = os.path.join(
                    final, "proto_s%02d_%s_a%03d_1280x720.png"
                    % (seed, view, amount))
                image, mask = analyze(path, off)
                proto.append(metrics(
                    "proto_s%02d_%s_a%03d" % (seed, view, amount),
                    image, mask, {"seed": seed, "view": view,
                                  "amount": amount / 100.0}))
    for seed in SEEDS:
        for view in VIEWS:
            off = os.path.join(final, "A_%s_off_1280x720.png" % view)
            path = os.path.join(final, "A_%s_a078_s%02d_1280x720.png"
                                % (view, seed))
            image, mask = analyze(path, off)
            ref.append(metrics("A_s%02d_%s" % (seed, view), image, mask,
                               {"seed": seed, "view": view,
                                "amount": 0.78}))

    # Global coverage from the prototype reports.
    global_cov = {}
    for seed in SEEDS:
        with open(os.path.join(final, "proto_s%02d.json" % seed),
                  encoding="utf-8") as handle:
            report = json.load(handle)
        for amount, item in report["amounts"].items():
            global_cov[(seed, round(float(amount), 2))] = item[
                "global_coverage"]
    with open(os.path.join(final, "proto_s03.json"), encoding="utf-8") as h:
        perf_report = json.load(h)

    # Cloud Amount curve at seed 17.
    curve_points = {"global_coverage": [], "main": [], "right": []}
    with open(os.path.join(curve, "proto_s17.json"), encoding="utf-8") as h:
        curve_report = json.load(h)
    for amount_text, item in sorted(
            curve_report["amounts"].items(), key=lambda kv: float(kv[0])):
        amount = float(amount_text)
        curve_points["global_coverage"].append(
            (amount, item["global_coverage"]))
        for view in VIEWS:
            off = os.path.join(curve, "proto_s17_%s_off_1280x720.png" % view)
            path = os.path.join(
                curve, "proto_s17_%s_a%03d_1280x720.png"
                % (view, round(amount * 100)))
            if not os.path.exists(path):
                continue
            _image, mask = analyze(path, off)
            curve_points[view].append((amount, float(mask.mean())))
    chart(curve_points, os.path.join(out, "contact_curve.png"))

    # Comparison at one representative cell.
    seed, view = 3, "main"
    proto_cell = [x for x in proto if x["seed"] == seed
                  and x["view"] == view and x["amount"] == 0.42][0]
    ref_cell = [x for x in ref if x["seed"] == seed and x["view"] == view][0]
    proto_image, proto_mask = analyze(
        os.path.join(final, "proto_s03_main_a042_1280x720.png"),
        os.path.join(final, "proto_s03_main_off_1280x720.png"))
    ref_image, ref_mask = analyze(
        os.path.join(final, "A_main_a078_s03_1280x720.png"),
        os.path.join(final, "A_main_off_1280x720.png"))
    sheet([
        [("v1.0.3  cov %.3f" % v1["coverage"], v1_image),
         ("A 0.78  cov %.3f / %d comp" % (ref_cell["coverage"],
                                          ref_cell["components"]), ref_image),
         ("prototype 0.42  cov %.3f / %d comp"
          % (proto_cell["coverage"], proto_cell["components"]), proto_image)],
        [("mask v1.0.3", mask_image(v1_mask)),
         ("mask A", mask_image(ref_mask)),
         ("mask prototype", mask_image(proto_mask))],
    ], os.path.join(out, "contact_main.png"), (860, 484), 18)
    mask_image(v1_mask).save(os.path.join(out, "mask_v1_0_3.png"))
    mask_image(ref_mask).save(os.path.join(out, "mask_A_s03_main.png"))
    mask_image(proto_mask).save(
        os.path.join(out, "mask_prototype_s03_main_a042.png"))

    # Seeds and views, A vs prototype at 0.42 (closest coverage).
    worst = min((x for x in proto if x["amount"] == 0.42),
                key=lambda x: x["coverage"])
    columns = [(seed, "main") for seed in SEEDS] + [(42, "right")]
    rows = [[], [], [], []]
    for seed, view in columns:
        ref_cell = [x for x in ref if x["seed"] == seed
                    and x["view"] == view][0]
        cell_ref = [x for x in proto if x["seed"] == seed
                    and x["view"] == view and x["amount"] == 0.42][0]
        image, mask = analyze(
            os.path.join(final, "A_%s_a078_s%02d_1280x720.png" % (view, seed)),
            os.path.join(final, "A_%s_off_1280x720.png" % view))
        rows[0].append(("A s%02d %s  cov %.3f" % (seed, view,
                                                  ref_cell["coverage"]),
                        image))
        rows[2].append(("mask A  %d comp" % ref_cell["components"],
                        mask_image(mask)))
        image, mask = analyze(
            os.path.join(final, "proto_s%02d_%s_a030_1280x720.png"
                         % (seed, view)),
            os.path.join(final, "proto_s%02d_%s_off_1280x720.png"
                         % (seed, view)))
        tag = "proto s%02d %s  cov %.3f" % (seed, view,
                                            cell_ref["coverage"])
        if seed == worst["seed"] and view == worst["view"]:
            tag = "worst " + tag
        rows[1].append((tag, image))
        rows[3].append(("mask proto  %d comp" % cell_ref["components"],
                        mask_image(mask)))
    sheet(rows, os.path.join(out, "contact_seeds.png"), (640, 360), 14)

    # Amount progression, main view, three seeds.
    amount_rows = [[], [], [], [], [], []]
    for amount in AMOUNTS:
        for seed in SEEDS:
            entry = [x for x in proto if x["seed"] == seed
                     and x["view"] == "main" and x["amount"] == amount / 100.0][0]
            image, mask = analyze(
                os.path.join(final, "proto_s%02d_main_a%03d_1280x720.png"
                             % (seed, amount)),
                os.path.join(final, "proto_s%02d_main_off_1280x720.png"
                             % seed))
            amount_rows[AMOUNTS.index(amount)].append(
                ("s%02d a%.2f  g %.3f / f %.3f"
                 % (seed, amount / 100.0,
                    global_cov[(seed, amount / 100.0)], entry["coverage"]),
                 image))
            amount_rows[3 + AMOUNTS.index(amount)].append(
                ("s%02d mask  %d comp" % (seed, entry["components"]),
                 mask_image(mask)))
    sheet(amount_rows, os.path.join(out, "contact_amounts.png"),
          (640, 360), 14)

    # Two camera directions, seed 17.
    view_rows = [[], [], []]
    for amount in AMOUNTS:
        for view in VIEWS:
            entry = [x for x in proto if x["seed"] == 17
                     and x["view"] == view and x["amount"] == amount / 100.0][0]
            image, mask = analyze(
                os.path.join(final, "proto_s17_%s_a%03d_1280x720.png"
                             % (view, amount)),
                os.path.join(final, "proto_s17_%s_off_1280x720.png" % view))
            view_rows[0 if amount == 18 else (1 if amount == 30 else 2)].append(
                ("%s a%.2f  cov %.3f" % (view, amount / 100.0,
                                         entry["coverage"]), image))
    sheet(view_rows, os.path.join(out, "contact_views.png"), (640, 360), 14)

    # Resolution: 1024 vs 2048, plus a 2x crop of the same edge.
    if resolution:
        low = Image.open(os.path.join(
            resolution, "proto_s03_main_a030_1280x720.png")).convert("RGB")
        high = Image.open(os.path.join(
            final, "proto_s03_main_a030_1280x720.png")).convert("RGB")
        crop = (80, 80, 520, 330)
        low_crop = low.crop(crop).resize((880, 500), Image.Resampling.NEAREST)
        high_crop = high.crop(crop).resize((880, 500), Image.Resampling.NEAREST)
        sheet([[("1024x512 texture", low), ("2048x1024 texture", high)],
               [("edge crop x2 1024", low_crop),
                ("edge crop x2 2048", high_crop)]],
              os.path.join(out, "contact_resolution.png"), (880, 495), 16)

    # Panoramas.
    pano_rows = []
    for seed in SEEDS:
        path = os.path.join(preview, "field_s%02d_2048x1024.png" % seed)
        pano_rows.append([("field seed %02d (all masses)" % seed,
                           Image.open(path).convert("RGB"))])
    sheet(pano_rows, os.path.join(out, "contact_panorama.png"), (1024, 512), 16)

    # Summary.
    def summary(records, name):
        cov = [x["coverage"] for x in records]
        largest = [x["largest_component"] for x in records]
        comps = [x["components"] for x in records]
        per = [x["perimeter_norm"] for x in records]
        return {
            "candidate": name,
            "cells": len(records),
            "coverage_mean": round(float(np.mean(cov)), 4),
            "coverage_min": round(float(min(cov)), 4),
            "coverage_max": round(float(max(cov)), 4),
            "components_mean": round(float(np.mean(comps)), 2),
            "components_min": int(min(comps)),
            "largest_mean": round(float(np.mean(largest)), 4),
            "largest_max": round(float(max(largest)), 4),
            "perimeter_mean": round(float(np.mean(per)), 3),
        }

    proto_at30 = [x for x in proto if x["amount"] == 0.42]
    report = {
        "v1.0.3": v1,
        "prototype": proto,
        "reference_A": ref,
        "summary": {
            "prototype_all_amounts": summary(proto, "prototype"),
            "prototype_0.42": summary(proto_at30, "prototype 0.42"),
            "reference_A_0.78": summary(ref, "A 0.78"),
        },
        "global_coverage": {"%d_%.2f" % key: value
                            for key, value in global_cov.items()},
        "curve": curve_points,
        "worst_prototype_0.42": worst,
        "performance": {
            "generation_ms_2048": perf_report["generation_ms"],
            "generation_ms_1024": 268.0,
            "field_bytes_2048": perf_report["field_nbytes"],
            "image_bytes_float_2048": 2048 * 1024 * 4 * 4,
            "exr_bytes_2048": os.path.getsize(os.path.join(
                final, "field_s03_2048x1024.exr")),
            "blend_bytes_1024": 347310,
            "packed_bytes_1024": 8397217,
            "prototype_render_ms_median": round(float(np.median(
                [x["render_ms"] for x in perf_report["renders"]])), 1),
            "reference_render_ms_median": round(float(np.median(
                [x["render_ms"] for x in json.load(open(
                    os.path.join(final, "reference_A.json"),
                    encoding="utf-8"))["renders"]])), 1),
            "seam_max_delta": {
                "s03": 0.1527, "s17": 0.154, "s42": 0.0658},
            "neighbour_max_delta": {
                "s03": 0.3006, "s17": 0.2884, "s42": 0.3101},
            "masses": {"s03": 92, "s17": 94, "s42": 94},
            "union_coverage": {"s03": 0.4964, "s17": 0.494,
                               "s42": 0.4952},
        },
        "threshold": THRESHOLD,
        "seed_note": "Seeds are independent 2D layouts, not translations of "
                     "one field.",
    }
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("PROTO all", report["summary"]["prototype_all_amounts"])
    print("PROTO 0.42", report["summary"]["prototype_0.42"])
    print("A 0.78", report["summary"]["reference_A_0.78"])
    print("V1", {k: v1[k] for k in ("coverage", "components",
                                    "largest_component", "perimeter_norm")})
    print("WORST", worst["seed"], worst["view"],
          round(worst["coverage"], 3))
    print("CURVE", [(a, round(c, 3)) for a, c in
                    curve_points["global_coverage"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
