"""Phase 1 Cumulus comparison: v1.0.3 vs v2.62.0.

Builds cloud masks from each version's clouds-off reference, measures coverage,
silhouette fragmentation, ambient contrast and rim response, and writes the
comparison sheets and metrics. No generator is modified.

Run::

    python preset_dev/phase1_compare.py
"""

import json
import os
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "baseline_2_63")
OLD = os.path.join(HERE, "world_baseline", "v1.0.3")
OUT = os.path.join(HERE, "phase1")
CALIBRATED = 0.78
THRESHOLD = 0.02


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def luma(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2])


def clean_mask(diff, threshold=THRESHOLD):
    image = Image.fromarray((diff > threshold).astype(np.uint8) * 255, "L")
    image = image.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.MinFilter(3))
    image = image.filter(ImageFilter.MinFilter(3)).filter(
        ImageFilter.MaxFilter(3))
    return np.asarray(image) > 127


def mask_image(mask):
    return Image.fromarray(mask.astype(np.uint8) * 255, "L")


def components(mask, minimum):
    """Connected components on a downsampled mask; returns areas and boxes."""
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
            x0, x1, y0, y1 = x, x, y, y
            while queue:
                px, py = queue.popleft()
                area += 1
                x0, x1 = min(x0, px), max(x1, px)
                y0, y1 = min(y0, py), max(y1, py)
                for nx, ny in ((px - 1, py), (px + 1, py),
                               (px, py - 1), (px, py + 1)):
                    if (0 <= nx < width and 0 <= ny < height
                            and grid[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            if area >= minimum:
                found.append({"area": area, "box": [x0, y0, x1, y1]})
    total = width * height
    for item in found:
        item["fraction"] = round(item["area"] / total, 4)
    return sorted(found, key=lambda item: -item["area"])


def metrics(name, on_path, off_path, resolution):
    on = load(on_path)
    off = load(off_path)
    diff = np.abs(on - off).max(axis=2)
    mask = clean_mask(diff)
    lum = luma(on)
    height, width = mask.shape
    sky_rows = int(height * 0.83)
    sky = ~mask & (np.arange(height)[:, None] < sky_rows)
    cloud_values = lum[mask]
    sky_values = lum[sky]
    grad_y, grad_x = np.gradient(lum)
    edge = np.hypot(grad_x, grad_y)[:sky_rows]
    eroded = np.asarray(mask_image(mask).filter(ImageFilter.MinFilter(7))) > 127
    rim = mask & ~eroded
    interior = eroded
    cloud_components = components(mask, 115)
    openings = components(~mask & (np.arange(height)[:, None] < sky_rows), 115)
    row_profile = [round(float(value), 4)
                   for value in mask[:sky_rows].mean(axis=1)[::max(1, sky_rows // 12)]]
    return {
        "name": name,
        "resolution": resolution,
        "coverage": round(float(mask.mean()), 4),
        "cloud_luma": {
            "mean": round(float(cloud_values.mean()), 4),
            "std": round(float(cloud_values.std()), 4),
            "p10": round(float(np.percentile(cloud_values, 10)), 4),
            "p50": round(float(np.percentile(cloud_values, 50)), 4),
            "p90": round(float(np.percentile(cloud_values, 90)), 4),
        },
        "sky_luma": round(float(sky_values.mean()), 4),
        "image_gradient_mean": round(float(edge.mean()), 5),
        "rim_to_interior": round(
            float(lum[rim].mean() / max(lum[interior].mean(), 1e-6)), 4),
        "components_over_0.2pct": len(cloud_components),
        "component_areas": [item["fraction"]
                            for item in cloud_components[:8]],
        "largest_component": round(
            cloud_components[0]["fraction"] if cloud_components else 0.0, 4),
        "openings_over_0.2pct": len(openings),
        "row_profile": row_profile,
        "threshold": THRESHOLD,
        "mask": mask,
        "image": on,
    }


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(image, text, label_font, size):
    if image.size != (size[0], size[1]):
        image = image.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size[0], size[1] + 38), (18, 18, 20))
    canvas.paste(image, (0, 38))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), text, fill=(238, 238, 238), font=label_font)
    return canvas


def sheet(rows, out_path, size):
    label = font(24)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = len(cells[0]) * size[0]
    height = len(cells) * (size[1] + 38)
    canvas = Image.new("RGB", (width, height), (12, 12, 14))
    for row_index, row in enumerate(cells):
        for col_index, item in enumerate(row):
            canvas.paste(item, (col_index * size[0],
                                row_index * (size[1] + 38)))
    canvas.save(out_path)


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {"calibrated_amount": CALIBRATED, "threshold": THRESHOLD,
              "resolutions": {}}

    paths_1280 = {
        "v1.0.3": (os.path.join(OLD, "summer_noon_1280x720.png"),
                   os.path.join(BASE, "summer_noon_v1.0.3_off_native_1280x720.png")),
        "v2.62_native": (
            os.path.join(BASE, "summer_noon_v2.62.0_on_amount_070_1280x720.png"),
            os.path.join(BASE, "summer_noon_v2.62.0_off_native_1280x720.png")),
        "v2.62_calibrated": (
            os.path.join(BASE, "summer_noon_v2.62.0_on_amount_078_1280x720.png"),
            os.path.join(BASE, "summer_noon_v2.62.0_off_native_1280x720.png")),
    }
    paths_1920 = {
        "v1.0.3": (os.path.join(OLD, "summer_noon_1920x1080.png"),
                   os.path.join(BASE, "summer_noon_v1.0.3_off_native_1920x1080.png")),
        "v2.62_native": (
            os.path.join(BASE, "summer_noon_v2.62.0_on_amount_070_1920x1080.png"),
            os.path.join(BASE, "summer_noon_v2.62.0_off_native_1920x1080.png")),
        "v2.62_calibrated": (
            os.path.join(HERE, "phase1", "summer_noon_v2.62_calibrated_on_amount_078_1920x1080.png"),
            os.path.join(BASE, "summer_noon_v2.62.0_off_native_1920x1080.png")),
    }

    primary_rows = None
    for resolution, paths, size in (
            ("1280x720", paths_1280, (1280, 720)),
            ("1920x1080", paths_1920, (1920, 1080))):
        rows = []
        results = {}
        image_row = []
        mask_row = []
        for name, (on_path, off_path) in paths.items():
            result = metrics(name, on_path, off_path, resolution)
            mask = result.pop("mask")
            image = result.pop("image")
            results[name] = result
            image_row.append((name.replace("_", " "), Image.fromarray(
                (image * 255).astype(np.uint8))))
            mask_row.append(("mask - " + name.replace("_", " "),
                             mask_image(mask).convert("RGB")))
            mask_image(mask).save(os.path.join(
                OUT, "mask_%s_%s.png" % (name.replace(".", "_"), resolution)))
        rows = [image_row, mask_row]
        if resolution == "1280x720":
            primary_rows = rows
        report["resolutions"][resolution] = results
        sheet(rows, os.path.join(OUT, "contact_%s.png" % resolution), size)

    # The 1280 sheet is the primary single-table deliverable.
    sheet(primary_rows, os.path.join(OUT, "contact.png"), (1280, 720))

    # 1:1 crop of the main mass, for lighting and rim inspection.
    crop = (420, 40, 1500, 680)
    lighting = []
    for label, path in (
            ("v1.0.3", os.path.join(OLD, "summer_noon_1920x1080.png")),
            ("v2.62 native (0.70)",
             os.path.join(BASE, "summer_noon_v2.62.0_on_amount_070_1920x1080.png")),
            ("v2.62 calibrated (0.78)",
             os.path.join(HERE, "phase1", "summer_noon_v2.62_calibrated_on_amount_078_1920x1080.png"))):
        image = Image.open(path).convert("RGB").crop(crop)
        lighting.append((label, image))
    sheet([lighting], os.path.join(OUT, "contact_lighting.png"), (1080, 640))

    for name, result in report["resolutions"]["1280x720"].items():
        print("PHASE1 %-18s coverage %.3f  components %d  largest %.3f  "
              "cloud std %.3f  rim %.3f  openings %d"
              % (name, result["coverage"], result["components_over_0.2pct"],
                 result["largest_component"], result["cloud_luma"]["std"],
                 result["rim_to_interior"], result["openings_over_0.2pct"]))
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
