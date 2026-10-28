"""Phase 2E comparison: A vs calibrated P.

Reads the Cloud Amount curve, the 20-seed x 3-view same-control renders, and
the per-case matched diagnostic renders. Writes the visual table, masks,
curve chart and metrics. The per-case matching is diagnostic only.
"""

import glob
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "phase2e")
CURVE_A = os.path.join(HERE, "phase2e_curve")
CURVE_P = os.path.join(HERE, "phase2e_curve2")
SEEDS = os.path.join(HERE, "phase2e_seeds")
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")
VIEWS = ("main", "left", "right")
SPACED_SEEDS = (0, 7, 14, 21, 28, 35, 42, 49, 56, 63,
                70, 77, 84, 91, 98, 105, 112, 119, 126, 133)
REPRESENTATIVE = (0, 49, 84)
AMOUNTS = ("020", "040", "060", "070", "078", "090", "100")
THRESHOLD = 0.02


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def luma(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2])


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
    eroded = np.asarray(mask_image(mask).filter(ImageFilter.MinFilter(3))) > 127
    boundary = mask & ~eroded
    boundary[0, :] = False
    boundary[-1, :] = False
    boundary[:, 0] = False
    boundary[:, -1] = False
    pixels = int(boundary.sum())
    area = int(mask.sum())
    return {
        "pixels": pixels,
        "norm": round(float(pixels / max(np.sqrt(area), 1.0)), 3),
        "resolution": round(float(pixels / np.sqrt(mask.size)), 4),
    }


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


def metrics(name, image, mask):
    height, width = mask.shape
    cloud = luma(image)[mask]
    rows = np.where(mask.any(axis=1))[0]
    boundary = perimeter(mask)
    areas = components(mask)
    grad_y, grad_x = np.gradient(luma(image))
    gradient = np.hypot(grad_x, grad_y)[:int(height * 0.83)].mean()
    return {
        "name": name,
        "resolution": [width, height],
        "coverage": round(float(mask.mean()), 4),
        "area_pixels": int(mask.sum()),
        "perimeter_pixels": boundary["pixels"],
        "perimeter_norm": boundary["norm"],
        "perimeter_per_resolution": boundary["resolution"],
        "components": len(areas),
        "component_areas": areas,
        "largest_component": areas[0] if areas else 0.0,
        "vertical_top": int(rows.min()) / height if len(rows) else None,
        "vertical_bottom": int(rows.max()) / height if len(rows) else None,
        "vertical_span": (float(rows.max() - rows.min()) / height
                          if len(rows) else 0.0),
        "vertical_centroid": round(float(np.argwhere(mask)[:, 0].mean())
                                   / height, 3),
        "image_gradient_mean": round(float(gradient), 5),
        "cloud_luma": {
            "mean": round(float(cloud.mean()), 4),
            "std": round(float(cloud.std()), 4),
            "p10": round(float(np.percentile(cloud, 10)), 4),
            "p50": round(float(np.percentile(cloud, 50)), 4),
            "p90": round(float(np.percentile(cloud, 90)), 4),
        },
        "threshold": THRESHOLD,
    }


def analyze(name, on_path, off_path, mask=None, image=None):
    if image is None:
        image = load(on_path)
    if mask is None:
        mask = mask_from(image, load(off_path))
    return metrics(name, image, mask), mask, image


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(image, text, label_font, size, title_size=24):
    if not isinstance(image, Image.Image):
        image = Image.fromarray((image * 255).astype(np.uint8))
    image = image.resize(size, Image.Resampling.LANCZOS)
    header = 38 if title_size >= 20 else 28
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image.convert("RGB"), (0, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 5 if header == 28 else 8), text,
              fill=(238, 238, 238), font=label_font)
    return canvas


def sheet(rows, out_path, size, title_size=24):
    label = font(title_size)
    cells = [[cell(image, text, label, size, title_size)
              for text, image in row] for row in rows]
    width = max(len(row) for row in cells) * size[0]
    height = sum(max(item.size[1] for item in row) for row in cells)
    canvas = Image.new("RGB", (width, height), (12, 12, 14))
    y = 0
    for row in cells:
        x = 0
        row_height = max(item.size[1] for item in row)
        for item in row:
            canvas.paste(item, (x, y))
            x += size[0]
        y += row_height
    canvas.save(out_path)


def summary(records):
    cov = [x["coverage"] for x in records]
    lar = [x["largest_component"] for x in records]
    comp = [x["components"] for x in records]
    per = [x["perimeter_norm"] for x in records]
    return {
        "coverage_mean": round(float(np.mean(cov)), 4),
        "coverage_min": round(float(min(cov)), 4),
        "coverage_max": round(float(max(cov)), 4),
        "coverage_std": round(float(np.std(cov)), 4),
        "largest_mean": round(float(np.mean(lar)), 4),
        "largest_max": round(float(max(lar)), 4),
        "components_mean": round(float(np.mean(comp)), 2),
        "components_min": int(min(comp)),
        "components_max": int(max(comp)),
        "perimeter_mean": round(float(np.mean(per)), 3),
        "worst_largest": [{"view": x["view"], "seed": x["seed"],
                           "coverage": x["coverage"],
                           "components": x["components"],
                           "largest": x["largest_component"],
                           "perimeter": x["perimeter_norm"]}
                          for x in sorted(records,
                                          key=lambda x: -x["largest_component"])[:4]],
        "worst_coverage": [{"view": x["view"], "seed": x["seed"],
                            "coverage": x["coverage"],
                            "largest": x["largest_component"]}
                           for x in sorted(records,
                                           key=lambda x: x["coverage"])[:4]],
    }


def chart(curve_a, curve_p, path):
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
        draw.text((20, y - 8), "%.1f" % (index * 0.2), fill=(200, 200, 200),
                  font=small)
    for index in range(5):
        x = left + (right - left) * index / 4
        draw.line([x, top, x, bottom], fill=(38, 38, 42))
        draw.text((x - 12, bottom + 10), "%.2f" % (index * 0.25),
                  fill=(200, 200, 200), font=small)
    target_y = bottom - (bottom - top) * (0.42 / 1.0)
    draw.line([left, target_y, right, target_y], fill=(180, 150, 80), width=1)
    draw.text((left + 6, target_y - 18), "target 0.42", fill=(210, 180, 110),
              font=small)
    for curve, color, name in ((curve_a, (90, 180, 255), "A"),
                               (curve_p, (255, 150, 90), "P calibrated")):
        points = []
        for amount, item in curve:
            x = left + (right - left) * amount
            y = bottom - (bottom - top) * min(0.9, item["coverage"])
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        for point in points:
            draw.ellipse([point[0] - 4, point[1] - 4,
                          point[0] + 4, point[1] + 4], fill=color)
        draw.text((left + 12, top + 8 + (0 if name == "A" else 28)),
                  name, fill=color, font=label)
    draw.text((left, 14), "Cloud Amount -> coverage", fill=(230, 230, 230),
              font=label)
    canvas.save(path)


def main():
    global OUT, CURVE_A, CURVE_P, SEEDS
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    for index, item in enumerate(argv):
        if index + 1 >= len(argv):
            continue
        if item == "--out":
            OUT = os.path.abspath(argv[index + 1])
        elif item == "--curve-a":
            CURVE_A = os.path.abspath(argv[index + 1])
        elif item == "--curve-p":
            CURVE_P = os.path.abspath(argv[index + 1])
        elif item == "--seeds":
            SEEDS = os.path.abspath(argv[index + 1])
    os.makedirs(OUT, exist_ok=True)

    v1_metrics, v1_mask, v1_image = analyze(
        "v1.0.3", V1_IMAGE, None,
        mask=np.asarray(Image.open(V1_MASK).convert("L")) > 127)

    # Cloud Amount curve.
    curve = {"A": [], "P": []}
    for name, directory in (("A", CURVE_A), ("P", CURVE_P)):
        off = os.path.join(CURVE_P, "A_main_off_1280x720.png")
        for amount in AMOUNTS:
            path = os.path.join(directory, "%s_main_a%s_s17_1280x720.png"
                                % (name, amount))
            result = analyze("%s %s" % (name, amount), path, off)
            curve[name].append((int(amount) / 100.0, result[0]))
    chart(curve["A"], curve["P"], os.path.join(OUT, "contact_curve.png"))

    # Same-control 20 seed x 3 view.
    native = {}
    native_records = {"A": [], "P": []}
    for view in VIEWS:
        off = os.path.join(SEEDS, "A_%s_off_1280x720.png" % view)
        for candidate in ("A", "P"):
            for seed in SPACED_SEEDS:
                path = os.path.join(
                    SEEDS, "%s_%s_a078_s%02d_1280x720.png"
                    % (candidate, view, seed))
                result = analyze("%s %s s%02d" % (candidate, view, seed),
                                 path, off)
                result[0]["view"] = view
                result[0]["seed"] = seed
                result[0]["candidate"] = candidate
                native_records[candidate].append(result[0])
    native["A"] = {"records": native_records["A"],
                   "summary": summary(native_records["A"])}
    native["P"] = {"records": native_records["P"],
                   "summary": summary(native_records["P"])}

    # Per-case matched diagnostic.
    matched = {}
    matched_records = {"A": [], "P": []}
    for view in VIEWS:
        off = os.path.join(SEEDS, "A_%s_off_1280x720.png" % view)
        for candidate in ("A", "P"):
            for seed in SPACED_SEEDS:
                pattern = os.path.join(
                    SEEDS, "%s_%s_matched_a*_s%02d_1280x720.png"
                    % (candidate, view, seed))
                paths = glob.glob(pattern)
                if not paths:
                    continue
                path = paths[0]
                result = analyze("%s %s matched s%02d"
                                 % (candidate, view, seed), path, off)
                result[0]["view"] = view
                result[0]["seed"] = seed
                result[0]["candidate"] = candidate
                result[0]["amount"] = int(
                    os.path.basename(path).split("_a")[1].split("_")[0]) / 100.0
                matched_records[candidate].append(result[0])
    matched["A"] = {"records": matched_records["A"],
                    "summary": summary(matched_records["A"])}
    matched["P"] = {"records": matched_records["P"],
                    "summary": summary(matched_records["P"])}

    # Main sheet at seed 17, calibrated amounts 0.78.
    main_row = []
    mask_row = []
    main_row.append(("v1.0.3 cov %.3f" % v1_metrics["coverage"], v1_image))
    mask_row.append(("mask v1.0.3", mask_image(v1_mask)))
    for candidate, directory in (("A", CURVE_A), ("P", CURVE_P)):
        path = os.path.join(directory, "%s_main_a078_s17_1280x720.png"
                            % candidate)
        result, mask, image = analyze(
            candidate, path,
            os.path.join(CURVE_P, "A_main_off_1280x720.png"))
        main_row.append(("%s 0.78 cov %.3f / %d comp / L %.3f"
                         % (candidate, result["coverage"],
                            result["components"],
                            result["largest_component"]), image))
        mask_row.append(("mask %s" % candidate, mask_image(mask)))
        mask_image(mask).save(os.path.join(OUT, "mask_%s_main.png" % candidate))
    sheet([main_row, mask_row], os.path.join(OUT, "contact_main.png"),
          (1280, 720), title_size=18)

    # Table: A/P matched at three representative seeds, worst, left seed 17.
    worst = sorted(matched_records["P"],
                   key=lambda x: -x["largest_component"])[0]
    cells = []
    for seed in REPRESENTATIVE:
        cells.append((("main", seed), seed))
    cells.append((("worst", worst["seed"]), worst["view"]))
    cells.append((("left", 49), 49))

    image_rows = []
    mask_rows = []
    for candidate in ("A", "P"):
        image_row = []
        mask_row = []
        for label, spec in cells:
            if label[0] == "worst":
                view, seed = spec, label[1]
                tag = "worst %s s%02d" % (view, seed)
            else:
                view, seed = label[0], label[1]
                tag = "%s s%02d" % (view, seed)
            pattern = os.path.join(
                SEEDS, "%s_%s_matched_a*_s%02d_1280x720.png"
                % (candidate, view, seed))
            paths = glob.glob(pattern)
            if not paths:
                continue
            path = paths[0]
            result, mask, image = analyze(
                "%s %s" % (candidate, tag), path,
                os.path.join(SEEDS, "A_%s_off_1280x720.png" % view))
            image_row.append(("%s %s cov %.3f / %d comp / L %.3f"
                              % (candidate, tag, result["coverage"],
                                 result["components"],
                                 result["largest_component"]), image))
            mask_row.append(("%s mask %s" % (candidate, tag),
                             mask_image(mask)))
        image_rows.append(image_row)
        mask_rows.append(mask_row)
    sheet(image_rows, os.path.join(OUT, "contact_table.png"),
          (640, 360), title_size=14)
    sheet(mask_rows, os.path.join(OUT, "contact_masks.png"),
          (640, 360), title_size=14)

    report = {
        "v1.0.3": v1_metrics,
        "curve": {name: [{"amount": amount, **item}
                         for amount, item in values]
                  for name, values in curve.items()},
        "native": native,
        "matched": matched,
        "representative_cells": [
            {"view": (label[1] if label[0] == "worst" else label[0]),
             "seed": (spec if label[0] == "worst" else label[1])}
            for label, spec in cells
        ],
        "threshold": THRESHOLD,
        "target_coverage": 0.42,
        "tolerance": 0.02,
        "seed_note": "Seed is a translation of the same procedural field; "
                     "samples are correlated, not independent.",
    }
    with open(os.path.join(OUT, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for name in ("A", "P"):
        item = native[name]["summary"]
        print("PHASE2E native %s cov %.3f [%.3f..%.3f] largest max %.3f "
              "comps %.1f perim %.2f"
              % (name, item["coverage_mean"], item["coverage_min"],
                 item["coverage_max"], item["largest_max"],
                 item["components_mean"], item["perimeter_mean"]))
        item = matched[name]["summary"]
        print("PHASE2E matched %s cov %.3f [%.3f..%.3f] largest max %.3f "
              "comps %.1f perim %.2f"
              % (name, item["coverage_mean"], item["coverage_min"],
                 item["coverage_max"], item["largest_max"],
                 item["components_mean"], item["perimeter_mean"]))
    print("PHASE2E curve A", [(a, x["coverage"]) for a, x in curve["A"]])
    print("PHASE2E curve P", [(a, x["coverage"]) for a, x in curve["P"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
