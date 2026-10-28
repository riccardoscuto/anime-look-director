"""Phase 2A Cumulus morphology comparison (A vs B vs v1.0.3).

Builds masks from the clouds-off references, measures true mask perimeter,
component distribution, vertical extent and timing, and writes the A/B sheets.

Run after ``phase2a_render.py`` has filled ``preset_dev/phase2a/raw``::

    python preset_dev/phase2a_compare.py
"""

import glob
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "phase2a")
IMAGES = os.path.join(OUT, "raw")
REGRESSION = os.path.join(OUT, "regression")
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")
THRESHOLD = 0.02


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def luma(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2])


def clean_mask(diff):
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
    norm = pixels / max(np.sqrt(area), 1.0)
    resolution = pixels / np.sqrt(mask.size)
    return pixels, round(float(norm), 3), round(float(resolution), 4)


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
    sky_rows = int(height * 0.83)
    gradient = np.gradient(luma(image))
    gradient_mean = np.hypot(gradient[1], gradient[0])[:sky_rows].mean()
    rows = np.where(mask.any(axis=1))[0]
    centroid = float(np.argwhere(mask)[:, 0].mean()) / height
    boundary, perimeter_norm, perimeter_res = perimeter(mask)
    component_areas = components(mask)
    profile = mask[:sky_rows].mean(axis=1)
    row_profile = [round(float(value), 4) for value in
                   profile[::max(1, sky_rows // 12)]]
    return {
        "name": name,
        "resolution": [width, height],
        "coverage": round(float(mask.mean()), 4),
        "area_pixels": int(mask.sum()),
        "perimeter_pixels": boundary,
        "perimeter_norm": perimeter_norm,
        "perimeter_per_resolution": perimeter_res,
        "components": len(component_areas),
        "component_areas": component_areas,
        "largest_component": component_areas[0] if component_areas else 0.0,
        "vertical_top": int(rows.min()) / height if len(rows) else None,
        "vertical_bottom": int(rows.max()) / height if len(rows) else None,
        "vertical_span": (float(rows.max() - rows.min()) / height
                          if len(rows) else 0.0),
        "vertical_centroid": round(centroid, 3),
        "row_profile": row_profile,
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


def analyze(name, on_path, off_path=None, mask=None, image=None):
    if image is None:
        image = load(on_path)
    if mask is None:
        mask = clean_mask(np.abs(image - load(off_path)).max(axis=2))
    return metrics(name, image, mask), mask, image


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(image, text, label_font, size):
    if not isinstance(image, Image.Image):
        image = Image.fromarray((image * 255).astype(np.uint8))
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size[0], size[1] + 38), (18, 18, 20))
    canvas.paste(image.convert("RGB"), (0, 38))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), text, fill=(238, 238, 238), font=label_font)
    return canvas


def sheet(rows, out_path, size):
    label = font(24)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = max(len(row) for row in cells) * size[0]
    height = len(cells) * (size[1] + 38)
    canvas = Image.new("RGB", (width, height), (12, 12, 14))
    for row_index, row in enumerate(cells):
        for col_index, item in enumerate(row):
            canvas.paste(item, (col_index * size[0],
                                row_index * (size[1] + 38)))
    canvas.save(out_path)


def image_of(path):
    return Image.open(path).convert("RGB")


def timing(prefix):
    files = sorted(glob.glob(os.path.join(IMAGES, "meta_%s_a*.json" % prefix)))
    apply_values, render_values = [], []
    for path in files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        apply_values.append(data["apply_ms"])
        render_values.append(data["render_ms"])
    main = os.path.join(IMAGES, "meta_%s_main_a078_s17.json" % prefix)
    with open(main, encoding="utf-8") as f:
        reference = json.load(f)
    return {
        "apply_ms_median": round(float(np.median(apply_values)), 2),
        "render_ms_median": round(float(np.median(render_values)), 1),
        "first_render_ms": reference["render_ms"],
        "group_nodes": reference["group_nodes"],
        "world_nodes": reference["world_nodes"],
    }


def regression():
    result = {}
    for sub, family in (("strat", "STRATOCUMULUS"), ("cirrus", "CIRRUS")):
        tag = family.lower()
        a = os.path.join(REGRESSION, sub,
                         "A_main_%s_a060_s17_1280x720.png" % tag)
        b = os.path.join(REGRESSION, sub,
                         "B_main_%s_a060_s17_1280x720.png" % tag)
        if not (os.path.exists(a) and os.path.exists(b)):
            result[family] = {"identical": False, "error": "missing render"}
            continue
        aa = np.asarray(Image.open(a).convert("RGB"), dtype=np.uint8)
        bb = np.asarray(Image.open(b).convert("RGB"), dtype=np.uint8)
        delta = np.abs(aa.astype(np.int16) - bb.astype(np.int16)).max()
        result[family] = {"identical": bool(np.array_equal(aa, bb)),
                          "max_delta": int(delta)}
    return result


def main():
    global IMAGES, OUT, REGRESSION
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    for index, item in enumerate(argv):
        if item == "--images" and index + 1 < len(argv):
            IMAGES = os.path.abspath(argv[index + 1])
        elif item == "--out" and index + 1 < len(argv):
            OUT = os.path.abspath(argv[index + 1])
        elif item == "--regression" and index + 1 < len(argv):
            REGRESSION = os.path.abspath(argv[index + 1])
    os.makedirs(OUT, exist_ok=True)
    v1_metrics, v1_mask, v1_image = analyze(
        "v1.0.3", V1_IMAGE, mask=np.asarray(
            Image.open(V1_MASK).convert("L")) > 127)
    candidates = {}
    main_cells = []
    mask_cells = [("mask - v1.0.3", mask_image(v1_mask))]
    main_cells.append(("v1.0.3 - coverage %.3f" % v1_metrics["coverage"],
                       v1_image))
    for candidate in ("A", "B"):
        off = os.path.join(IMAGES, "%s_main_off_1280x720.png" % candidate)
        main = analyze(candidate + " main",
                       os.path.join(IMAGES, "%s_main_a078_s17_1280x720.png"
                                    % candidate), off)
        candidates[candidate] = {"main": main[0]}
        main_cells.append(("%s 0.78 - coverage %.3f, %d comp, largest %.3f"
                           % (candidate, main[0]["coverage"],
                              main[0]["components"],
                              main[0]["largest_component"]), main[2]))
        mask_cells.append(("mask - %s 0.78" % candidate, mask_image(main[1])))
        mask_image(main[1]).save(os.path.join(
            OUT, "mask_%s_main.png" % candidate))

        coverage = {}
        coverage_cells = []
        for amount, label, shown in (("060", "low", "0.60"),
                                     ("070", "medium", "0.70"),
                                     ("078", "high", "0.78")):
            result = analyze(
                "%s %s" % (candidate, label),
                os.path.join(IMAGES, "%s_main_a%s_s17_1280x720.png"
                             % (candidate, amount)), off)
            coverage[label] = result[0]
            coverage_cells.append(("%s %s %s - cov %.3f"
                                   % (candidate, label, shown,
                                      result[0]["coverage"]), result[2]))
        candidates[candidate]["coverage"] = coverage
        sheet([coverage_cells], os.path.join(
            OUT, "contact_%s_coverage.png" % candidate), (1280, 720))

        seeds = {}
        seed_cells = []
        for seed in ("07", "17", "31"):
            result = analyze(
                "%s seed %s" % (candidate, seed),
                os.path.join(IMAGES, "%s_main_a078_s%s_1280x720.png"
                             % (candidate, seed)), off)
            seeds[seed] = result[0]
            seed_cells.append(("%s seed %s - cov %.3f, %d comp"
                               % (candidate, seed, result[0]["coverage"],
                                  result[0]["components"]), result[2]))
        candidates[candidate]["seeds"] = seeds
        sheet([seed_cells], os.path.join(
            OUT, "contact_%s_seeds.png" % candidate), (1280, 720))

        alt = analyze(
            "%s alt" % candidate,
            os.path.join(IMAGES, "%s_alt_a078_s17_1280x720.png" % candidate),
            os.path.join(IMAGES, "%s_alt_off_1280x720.png" % candidate))
        candidates[candidate]["alt"] = alt[0]
        sheet([[("%s alt view - cov %.3f, %d comp"
                 % (candidate, alt[0]["coverage"], alt[0]["components"]),
                 alt[2])]], os.path.join(
            OUT, "contact_%s_alt.png" % candidate), (1280, 720))

    # Main single table: v1.0.3 / A / B, images and masks.
    sheet([main_cells, mask_cells], os.path.join(OUT, "contact_main.png"),
          (1280, 720))

    # Coverage and seed overview across both candidates.
    coverage_rows = []
    for candidate in ("A", "B"):
        row = []
        for label in ("low", "medium", "high"):
            item = candidates[candidate]["coverage"][label]
            row.append(("%s %s - cov %.3f"
                        % (candidate, label, item["coverage"]),
                        image_of(os.path.join(
                            IMAGES, "%s_main_a%s_s17_1280x720.png"
                            % (candidate, {"low": "060", "medium": "070",
                                           "high": "078"}[label])))))
        coverage_rows.append(row)
    sheet(coverage_rows, os.path.join(OUT, "contact_coverage.png"),
          (1280, 720))

    seed_rows = []
    for candidate in ("A", "B"):
        row = []
        for seed in ("07", "17", "31"):
            item = candidates[candidate]["seeds"][seed]
            row.append(("%s seed %s - cov %.3f"
                        % (candidate, seed, item["coverage"]),
                        image_of(os.path.join(
                            IMAGES, "%s_main_a078_s%s_1280x720.png"
                            % (candidate, seed)))))
        seed_rows.append(row)
    sheet(seed_rows, os.path.join(OUT, "contact_seeds.png"), (1280, 720))

    alt_rows = [[
        ("A alt - cov %.3f" % candidates["A"]["alt"]["coverage"],
         image_of(os.path.join(IMAGES, "A_alt_a078_s17_1280x720.png"))),
        ("B alt - cov %.3f" % candidates["B"]["alt"]["coverage"],
         image_of(os.path.join(IMAGES, "B_alt_a078_s17_1280x720.png"))),
    ]]
    sheet(alt_rows, os.path.join(OUT, "contact_alt.png"), (1280, 720))

    report = {
        "v1.0.3": v1_metrics,
        "candidates": candidates,
        "timing": {"A": timing("A"), "B": timing("B")},
        "regression": regression(),
        "threshold": THRESHOLD,
        "calibration": {"A": 0.78, "B": 0.78,
                        "target_coverage": 0.42, "tolerance": 0.02},
    }
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for candidate in ("A", "B"):
        item = candidates[candidate]["main"]
        print("PHASE2A %s cov %.3f components %d largest %.3f perimeter %.3f "
              "vertical %.3f"
              % (candidate, item["coverage"], item["components"],
                 item["largest_component"], item["perimeter_norm"],
                 item["vertical_span"]))
    print("PHASE2A v1.0.3 cov %.3f components %d largest %.3f perimeter %.3f"
          % (v1_metrics["coverage"], v1_metrics["components"],
             v1_metrics["largest_component"], v1_metrics["perimeter_norm"]))
    print("PHASE2A regression", report["regression"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
