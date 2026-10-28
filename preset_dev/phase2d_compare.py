"""Phase 2D morphology diagnosis: A, P, R, PR.

Builds the comparison table, coverage curves, spaced-seed check and alternate
views. Reads the raw renders produced by phase2d_render.py.
"""

import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "phase2d")
SPACED = os.path.join(BASE, "spaced")
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")
VARIANTS = (("A", 0.78), ("P", 0.86), ("R", 0.66), ("PR", 0.78))
NATIVE = (("0.60", "060"), ("0.70", "070"), ("0.78", "078"))
SPACED_SEEDS = (0, 7, 14, 21, 28, 35, 42, 49, 56, 63)
ALT_SEEDS = (0, 28, 56)
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
    gradient_mean = np.hypot(grad_x, grad_y)[:int(height * 0.83)].mean()
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
        "image_gradient_mean": round(float(gradient_mean), 5),
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


def image_of(path):
    return Image.open(path).convert("RGB")


def summary(records):
    coverage = [item["coverage"] for item in records]
    largest = [item["largest_component"] for item in records]
    comps = [item["components"] for item in records]
    perim = [item["perimeter_norm"] for item in records]
    return {
        "coverage_mean": round(float(np.mean(coverage)), 4),
        "coverage_min": round(float(min(coverage)), 4),
        "coverage_max": round(float(max(coverage)), 4),
        "coverage_std": round(float(np.std(coverage)), 4),
        "largest_mean": round(float(np.mean(largest)), 4),
        "largest_max": round(float(max(largest)), 4),
        "components_mean": round(float(np.mean(comps)), 2),
        "components_min": int(min(comps)),
        "components_max": int(max(comps)),
        "perimeter_mean": round(float(np.mean(perim)), 3),
        "worst_largest": [{"seed": item["seed"],
                           "coverage": item["coverage"],
                           "components": item["components"],
                           "largest": item["largest_component"],
                           "perimeter": item["perimeter_norm"]}
                          for item in sorted(
                              records,
                              key=lambda item: -item["largest_component"])[:3]],
    }


def main():
    global BASE, SPACED
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    for index, item in enumerate(argv):
        if index + 1 >= len(argv):
            continue
        if item == "--base":
            BASE = os.path.abspath(argv[index + 1])
        elif item == "--spaced":
            SPACED = os.path.abspath(argv[index + 1])
    os.makedirs(BASE, exist_ok=True)
    v1_metrics, v1_mask, v1_image = analyze(
        "v1.0.3", V1_IMAGE, None,
        mask=np.asarray(Image.open(V1_MASK).convert("L")) > 127)
    main_report = {"v1.0.3": v1_metrics, "variants": {}}
    main_images = {}
    main_masks = {}
    for variant, amount in VARIANTS:
        on = os.path.join(BASE, "%s_main_a%03d_s17_1280x720.png"
                          % (variant, round(amount * 100)))
        off = os.path.join(BASE, "A_main_off_1280x720.png")
        result, mask, image = analyze(variant, on, off)
        result["amount"] = amount
        main_report["variants"][variant] = result
        main_images[variant] = image
        main_masks[variant] = mask

    # Main table: v1, A, P, R, PR, images and masks.
    image_row = [("v1.0.3 cov %.3f" % v1_metrics["coverage"], v1_image)]
    mask_row = [("mask v1.0.3", mask_image(v1_mask))]
    for variant, _amount in VARIANTS:
        item = main_report["variants"][variant]
        image_row.append(("%s %.2f cov %.3f / %d comp / L %.3f"
                          % (variant, item["amount"], item["coverage"],
                             item["components"], item["largest_component"]),
                          main_images[variant]))
        mask_row.append(("mask %s" % variant, mask_image(main_masks[variant])))
        mask_image(main_masks[variant]).save(os.path.join(
            BASE, "mask_%s.png" % variant))
    sheet([image_row, mask_row], os.path.join(BASE, "contact_variants.png"),
          (960, 540), title_size=17)

    # Coverage curve at native amounts.
    coverage_rows = []
    coverage_report = {}
    for variant, _amount in VARIANTS:
        row = []
        coverage_report[variant] = {}
        for shown, amount in NATIVE:
            on = os.path.join(BASE, "%s_main_a%s_s17_1280x720.png"
                              % (variant, amount))
            result = analyze("%s %s" % (variant, shown), on,
                             os.path.join(BASE,
                                          "A_main_off_1280x720.png"))
            coverage_report[variant][shown] = result[0]
            row.append(("%s %s cov %.3f / %d comp / L %.3f"
                        % (variant, shown, result[0]["coverage"],
                           result[0]["components"],
                           result[0]["largest_component"]), result[2]))
        coverage_rows.append(row)
    sheet(coverage_rows, os.path.join(BASE, "contact_coverage.png"),
          (640, 360), title_size=16)
    main_report["coverage"] = coverage_report

    # Alternate view at calibrated amounts.
    alt_report = {}
    alt_row = []
    for variant, amount in VARIANTS:
        on = os.path.join(BASE, "%s_alt_a%03d_s17_1280x720.png"
                          % (variant, round(amount * 100)))
        result = analyze(variant + " alt", on,
                         os.path.join(BASE, "A_alt_off_1280x720.png"))
        alt_report[variant] = result[0]
        alt_row.append(("%s alt %.2f cov %.3f / %d comp / L %.3f"
                        % (variant, amount, result[0]["coverage"],
                           result[0]["components"],
                           result[0]["largest_component"]), result[2]))
    sheet([alt_row], os.path.join(BASE, "contact_alt.png"),
          (960, 540), title_size=17)
    main_report["alt"] = alt_report

    # Spaced seeds, main and alternate views.
    spaced_report = {}
    spaced_rows = []
    for variant, amount in (("A", 0.78), ("P", 0.86)):
        records = []
        for seed in SPACED_SEEDS:
            on = os.path.join(SPACED, "%s_main_a%03d_s%02d_1280x720.png"
                              % (variant, round(amount * 100), seed))
            result = analyze("%s s%02d" % (variant, seed), on,
                             os.path.join(BASE,
                                          "A_main_off_1280x720.png"))
            result[0]["seed"] = seed
            records.append(result[0])
        spaced_report[variant] = {"seeds": records,
                                  "summary": summary(records)}
        for block in range(2):
            row = []
            for col in range(5):
                item = records[block * 5 + col]
                row.append(("%s s%02d cov %.3f / L %.3f"
                            % (variant, item["seed"], item["coverage"],
                               item["largest_component"]),
                            image_of(os.path.join(
                                SPACED,
                                "%s_main_a%03d_s%02d_1280x720.png"
                                % (variant, round(amount * 100),
                                   item["seed"])))))
            spaced_rows.append(row)
    sheet(spaced_rows, os.path.join(BASE, "contact_spaced.png"),
          (320, 180), title_size=14)

    spaced_alt = {}
    alt_rows = []
    for variant, amount in (("A", 0.78), ("P", 0.86)):
        records = []
        cells = []
        for seed in ALT_SEEDS:
            on = os.path.join(SPACED, "%s_alt_a%03d_s%02d_1280x720.png"
                              % (variant, round(amount * 100), seed))
            result = analyze("%s alt s%02d" % (variant, seed), on,
                             os.path.join(BASE,
                                          "A_alt_off_1280x720.png"))
            result[0]["seed"] = seed
            records.append(result[0])
            cells.append(("%s alt s%02d cov %.3f / %d comp"
                          % (variant, seed, result[0]["coverage"],
                             result[0]["components"]), result[2]))
        spaced_alt[variant] = {"seeds": records,
                               "summary": summary(records)}
        alt_rows.append(cells)
    sheet(alt_rows, os.path.join(BASE, "contact_spaced_alt.png"),
          (640, 360), title_size=16)
    main_report["spaced"] = spaced_report
    main_report["spaced_alt"] = spaced_alt

    with open(os.path.join(BASE, "metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(main_report, f, indent=2)
    for variant, amount in VARIANTS:
        item = main_report["variants"][variant]
        print("PHASE2D %s cal %.2f cov %.3f comp %d largest %.3f perim %.3f"
              % (variant, amount, item["coverage"], item["components"],
                 item["largest_component"], item["perimeter_norm"]))
    for variant in ("A", "P"):
        item = main_report["spaced"][variant]["summary"]
        print("PHASE2D %s spaced cov %.3f [%.3f..%.3f] largest max %.3f "
              "comps %.1f perim %.2f"
              % (variant, item["coverage_mean"], item["coverage_min"],
                 item["coverage_max"], item["largest_max"],
                 item["components_mean"], item["perimeter_mean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
