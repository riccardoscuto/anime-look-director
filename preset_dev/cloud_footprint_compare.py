"""Sheets and frame metrics for the A/B/F footprint comparison."""

import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CONFIGS = ("A", "B", "F")
SEEDS = (3, 17, 42)
AMOUNTS = (0.18, 0.30, 0.42)
VIEWS = ("main", "right")
LABELS = {"A": "A base/orig", "B": "B hier/fixed", "F": "F footprint"}
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
    header = 28
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((6, 5), text, fill=(235, 235, 235),
                                font=label)
    return canvas


def sheet(rows, path, size, label_size=13):
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
    with open(os.path.join(diag, "footprint.json"),
              encoding="utf-8") as handle:
        report = json.load(handle)
    by_key = {(item["config"], item["seed"], item["amount"]): item
              for item in report["records"]}
    offs = {view: load(os.path.join(diag, "look_off_%s.png" % view))
            for view in VIEWS}
    frames = []
    panorama_rows = []
    look_rows = []
    mask_rows = []
    for config in CONFIGS:
        for seed in SEEDS:
            panorama = []
            look = []
            masks = []
            for amount in AMOUNTS:
                item = by_key[(config, seed, amount)]
                panorama.append((
                    "%s s%02d %.2f  cov %.3f  act %d"
                    % (LABELS[config], seed, amount, item["coverage"],
                       item["active_masses"]),
                    Image.open(os.path.join(
                        diag, "color_%s_s%02d_a%03d.png"
                        % (config, seed, round(amount * 100))))))
                for view in VIEWS:
                    image = load(os.path.join(
                        diag, "look_%s_s%02d_a%03d_%s.png"
                        % (config, seed, round(amount * 100), view)))
                    mask = mask_from(image, offs[view])
                    metrics = frame_metrics(mask)
                    frames.append({"config": config, "seed": seed,
                                   "amount": amount, "view": view,
                                   **metrics})
                    look.append((
                        "%s s%02d %.2f %s  fcov %.3f/%d"
                        % (LABELS[config], seed, amount, view,
                           metrics["coverage"], metrics["components"]),
                        Image.fromarray((image * 255).astype(np.uint8))))
                    masks.append((
                        "mask %s s%02d %.2f %s  L %.3f"
                        % (LABELS[config], seed, amount, view,
                           metrics["largest_component"]),
                        mask_image(mask)))
            panorama_rows.append(panorama)
            look_rows.append(look)
            mask_rows.append(masks)
    sheet(panorama_rows, os.path.join(out, "contact_footprint_panorama.png"),
          (512, 256), 12)
    sheet(look_rows, os.path.join(out, "contact_footprint_look.png"),
          (320, 180), 11)
    sheet(mask_rows, os.path.join(out, "contact_footprint_masks.png"),
          (320, 180), 11)

    summary = {}
    for config in CONFIGS:
        for amount in AMOUNTS:
            records = [item for item in report["records"]
                       if item["config"] == config
                       and item["amount"] == amount]
            frame_items = [item for item in frames
                           if item["config"] == config
                           and item["amount"] == amount]
            summary["%s_%.2f" % (config, amount)] = {
                "global_coverage": round(float(np.mean(
                    [item["coverage"] for item in records])), 4),
                "active_masses": round(float(np.mean(
                    [item["active_masses"] for item in records])), 1),
                "overlap_area": round(float(np.mean(
                    [item["overlap_area"] for item in records])), 4),
                "panorama_components": round(float(np.mean(
                    [item["panorama_components"] for item in records])), 1),
                "panorama_dominant": round(float(np.mean(
                    [item["panorama_dominant"] for item in records])), 4),
                "mean_mass_area": round(float(np.mean(
                    [item["mean_mass_area"] for item in records
                     if item.get("mean_mass_area") is not None])), 5),
                "frame_coverage": round(float(np.mean(
                    [item["coverage"] for item in frame_items])), 4),
                "frame_components": round(float(np.mean(
                    [item["components"] for item in frame_items])), 2),
                "frame_largest": round(float(np.mean(
                    [item["largest_component"] for item in frame_items])), 4),
                "frame_largest_max": round(float(max(
                    item["largest_component"] for item in frame_items)), 4),
                "generation_ms": round(float(np.mean(
                    [item["generation_ms"] for item in records])), 1),
            }
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"amounts": list(AMOUNTS), "summary": summary,
                   "records": report["records"],
                   "frames": frames}, handle, indent=2)
    for key, item in summary.items():
        print("FOOTPRINT", key, item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
