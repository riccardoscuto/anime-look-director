"""Panorama comparison: baseline vs hierarchical morphology at 0.42.

Reads the 2048 prototype renders for both variants, the v1.0.3 baseline and
writes the distribution sheets plus metrics.
"""

import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (3, 17, 42)
VIEWS = ("main", "right")
AMOUNT = 42
THRESHOLD = 0.02
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


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
    return {"pixels": int(boundary.sum()),
            "norm": round(float(boundary.sum() / max(np.sqrt(mask.sum()), 1.0)),
                          3)}


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


def metrics(name, mask):
    height, width = mask.shape
    rows = np.where(mask.any(axis=1))[0]
    boundary = perimeter(mask)
    areas = components(mask)
    return {
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


def cell(image, text, label, size):
    if not isinstance(image, Image.Image):
        image = Image.fromarray((image * 255).astype(np.uint8))
    image = image.resize(size, Image.Resampling.LANCZOS).convert("RGB")
    header = 30
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((7, 6), text, fill=(235, 235, 235),
                                font=label)
    return canvas


def sheet(rows, path, size=(640, 360), label_size=14):
    label = font(label_size)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = max(len(row) for row in cells) * size[0]
    heights = [max(item.size[1] for item in row) for row in cells]
    canvas = Image.new("RGB", (width, sum(heights)), (12, 12, 14))
    y = 0
    for row, height in zip(cells, heights):
        x = 0
        for item in row:
            canvas.paste(item, (x, y))
            x += size[0]
        y += height
    canvas.save(path)
    return canvas.size


def analyze(root, variant, seed, view):
    off = os.path.join(root, "proto_s%02d_%s_off_1280x720.png" % (seed, view))
    path = os.path.join(root, "proto_s%02d_%s_a%03d_1280x720.png"
                        % (seed, view, AMOUNT))
    image = load(path)
    mask = mask_from(image, load(off))
    return image, mask, metrics("%s_s%02d_%s" % (variant, seed, view), mask)


def summary(records):
    coverages = [item["coverage"] for item in records]
    components_ = [item["components"] for item in records]
    largest = [item["largest_component"] for item in records]
    perimeter_ = [item["perimeter_norm"] for item in records]
    return {
        "cells": len(records),
        "coverage_mean": round(float(np.mean(coverages)), 4),
        "coverage_min": round(float(min(coverages)), 4),
        "coverage_max": round(float(max(coverages)), 4),
        "components_mean": round(float(np.mean(components_)), 2),
        "components_min": int(min(components_)),
        "components_max": int(max(components_)),
        "largest_mean": round(float(np.mean(largest)), 4),
        "largest_max": round(float(max(largest)), 4),
        "largest_over_030": int(sum(1 for item in largest if item > 0.30)),
        "perimeter_mean": round(float(np.mean(perimeter_)), 3),
    }


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"base": "", "hier": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    base = os.path.abspath(values["base"])
    hier = os.path.abspath(values["hier"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)

    records = {"baseline": [], "hierarchical": []}
    images = {}
    masks = {}
    for tag, root in (("baseline", base), ("hierarchical", hier)):
        for seed in SEEDS:
            for view in VIEWS:
                image, mask, record = analyze(root, tag, seed, view)
                record.update({"variant": tag, "seed": seed, "view": view})
                records[tag].append(record)
                images[(tag, seed, view)] = image
                masks[(tag, seed, view)] = mask

    global_cov = {}
    generation = {}
    for tag, root in (("baseline", base), ("hierarchical", hier)):
        generation[tag] = []
        for seed in SEEDS:
            with open(os.path.join(root, "proto_s%02d.json" % seed),
                      encoding="utf-8") as handle:
                report = json.load(handle)
            global_cov[(tag, seed)] = report["amounts"]["0.42"][
                "global_coverage"]
            generation[tag].append(report["generation_ms"])

    columns = [(seed, view) for view in VIEWS for seed in SEEDS]
    rows = [[], [], [], []]
    for tag, label in (("baseline", "baseline"), ("hierarchical", "hier")):
        image_row = 0 if tag == "baseline" else 1
        mask_row = 2 if tag == "baseline" else 3
        for seed, view in columns:
            item = [record for record in records[tag]
                    if record["seed"] == seed and record["view"] == view][0]
            rows[image_row].append(
                ("%s s%02d %s  cov %.3f / %d comp"
                 % (label, seed, view, item["coverage"], item["components"]),
                 Image.fromarray((images[(tag, seed, view)] * 255)
                                 .astype(np.uint8))))
            rows[mask_row].append(
                ("mask %s  largest %.3f" % (label, item["largest_component"]),
                 mask_image(masks[(tag, seed, view)])))
    sheet(rows, os.path.join(out, "contact_distribution.png"),
          (480, 270), 13)

    # Detail crop at seed 17 main.
    crop = (40, 20, 680, 380)
    detail = [[], []]
    for tag, label in (("baseline", "baseline"), ("hierarchical", "hier")):
        full = Image.fromarray((images[(tag, 17, "main")] * 255)
                               .astype(np.uint8))
        crop_image = full.crop(crop)
        mask = mask_image(masks[(tag, 17, "main")]).convert("RGB").crop(crop)
        detail[0].append(("%s full 2x crop" % label, crop_image))
        detail[1].append(("mask %s 2x crop" % label, mask))
    sheet(detail, os.path.join(out, "contact_distribution_detail.png"))

    # v1.0.3 baseline.
    v1_image = Image.open(V1_IMAGE).convert("RGB")
    v1_mask = np.asarray(Image.open(V1_MASK).convert("L")) > 127
    v1 = metrics("v1.0.3", v1_mask)
    sheet([[("v1.0.3  cov %.3f / %d comp" % (v1["coverage"],
                                             v1["components"]), v1_image)],
           [("mask v1.0.3  largest %.3f" % v1["largest_component"],
             mask_image(v1_mask))]],
          os.path.join(out, "contact_v103.png"), (960, 540), 16)

    summary_data = {"baseline": summary(records["baseline"]),
                    "hierarchical": summary(records["hierarchical"]),
                    "v1.0.3": v1}
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump({
            "amount": AMOUNT / 100.0,
            "global_coverage": {"%s_%d" % key: value
                                for key, value in global_cov.items()},
            "generation_ms": generation,
            "records": records,
            "summary": summary_data,
            "threshold": THRESHOLD,
            "seed_note": "The hierarchical variant reuses the same mass "
                         "positions, strengths and Cloud Amount logic as the "
                         "baseline.",
        }, handle, indent=2)
    for tag in ("baseline", "hierarchical"):
        print("MORPH", tag, summary_data[tag])
    print("MORPH v1.0.3", {key: v1[key] for key in (
        "coverage", "components", "largest_component", "perimeter_norm")})
    print("MORPH global", global_cov)
    print("MORPH gen", generation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
