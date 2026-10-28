"""Sheets and frame metrics for the overlap diagnosis."""

import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CONFIGS = ("A", "B", "C", "D")
SEEDS = (3, 17, 42)
VIEWS = ("main", "right")
LABELS = {"A": "A base/base", "B": "B hier/base",
          "C": "C base/hier", "D": "D hier/hier"}
THRESHOLD = 0.02


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


def frame_metrics(mask):
    areas = components(mask)
    return {
        "coverage": round(float(mask.mean()), 4),
        "components": len(areas),
        "largest_component": areas[0] if areas else 0.0,
    }


def cell(image, text, label, size):
    image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    header = 30
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((7, 6), text, fill=(235, 235, 235),
                                font=label)
    return canvas


def sheet(rows, path, size=(480, 270), label_size=13):
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


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"diag": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    diag = os.path.abspath(values["diag"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(diag, "diagnostic.json"), encoding="utf-8") as h:
        report = json.load(h)
    by_key = {(item["config"], item["seed"]): item
              for item in report["records"]}
    columns = [(seed, view) for view in VIEWS for seed in SEEDS]
    frame_records = []
    image_rows = []
    mask_rows = []
    for tag in CONFIGS:
        image_row = []
        mask_row = []
        for seed, view in columns:
            on = load(os.path.join(diag, "overlap_%s_s%02d_%s.png"
                                   % (tag, seed, view)))
            off = load(os.path.join(diag, "overlap_off_%s.png" % view))
            mask = mask_from(on, off)
            metrics = frame_metrics(mask)
            item = by_key[(tag, seed)]
            frame_records.append({"config": tag, "seed": seed, "view": view,
                                  **metrics})
            image_row.append((
                "%s s%02d %s  fcov %.3f / %d comp"
                % (LABELS[tag], seed, view, metrics["coverage"],
                   metrics["components"]),
                Image.fromarray((on * 255).astype(np.uint8))))
            mask_row.append((
                "mask %s  largest %.3f"
                % (LABELS[tag], metrics["largest_component"]),
                mask_image(mask)))
        image_rows.append(image_row)
        mask_rows.append(mask_row)
    sheet(image_rows, os.path.join(out, "contact_overlap.png"))
    sheet(mask_rows, os.path.join(out, "contact_overlap_masks.png"))

    panorama_rows = []
    for tag in CONFIGS:
        row = []
        for seed in SEEDS:
            item = by_key[(tag, seed)]
            standard = item["standard"]
            row.append((
                "%s s%02d  pairs %d  ovl %.1f%%  comps %d  dom %.3f"
                % (LABELS[tag], seed, standard["overlapping_pairs"],
                   standard["overlap_area"] * 100.0,
                   standard["panorama_components"],
                   standard["panorama_dominant"]),
                Image.open(os.path.join(diag, "overlap_%s_s%02d_panorama.png"
                                        % (tag, seed)))))
        panorama_rows.append(row)
    sheet(panorama_rows, os.path.join(out, "contact_overlap_panorama.png"),
          (512, 256), 13)

    summary = {}
    for tag in CONFIGS:
        items = [item for item in frame_records if item["config"] == tag]
        panorama = [by_key[(tag, seed)]["standard"] for seed in SEEDS]
        fixed = [by_key[(tag, seed)]["fixed"] for seed in SEEDS]
        summary[tag] = {
            "frame_coverage": round(float(np.mean(
                [item["coverage"] for item in items])), 4),
            "frame_components": round(float(np.mean(
                [item["components"] for item in items])), 2),
            "frame_largest": round(float(np.mean(
                [item["largest_component"] for item in items])), 4),
            "frame_largest_max": round(float(max(
                item["largest_component"] for item in items)), 4),
            "global_coverage": round(float(np.mean(
                [item["global_coverage"] for item in panorama])), 4),
            "overlap_area": round(float(np.mean(
                [item["overlap_area"] for item in panorama])), 4),
            "overlapping_pairs": round(float(np.mean(
                [item["overlapping_pairs"] for item in panorama])), 1),
            "panorama_components": round(float(np.mean(
                [item["panorama_components"] for item in panorama])), 1),
            "panorama_dominant": round(float(np.mean(
                [item["panorama_dominant"] for item in panorama])), 4),
            "fixed_coverage": round(float(np.mean(
                [item["global_coverage"] for item in fixed])), 4),
            "fixed_overlap": round(float(np.mean(
                [item["overlap_area"] for item in fixed])), 4),
            "fixed_pairs": round(float(np.mean(
                [item["overlapping_pairs"] for item in fixed])), 1),
            "fixed_components": round(float(np.mean(
                [item["panorama_components"] for item in fixed])), 1),
            "fixed_dominant": round(float(np.mean(
                [item["panorama_dominant"] for item in fixed])), 4),
        }
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"configs": report["configs"],
                   "panorama_records": report["records"],
                   "frame_records": frame_records,
                   "summary": summary}, handle, indent=2)
    for tag in CONFIGS:
        print("OVERLAP", tag, summary[tag])
    return 0


if __name__ == "__main__":
    sys.exit(main())
