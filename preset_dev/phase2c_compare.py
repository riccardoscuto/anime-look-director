"""Phase 2C comparison and 20-seed gate.

Reads the A/C seed renders and optional coverage/alt/regression renders,
measures true mask perimeter, component distribution and timing, and writes the
20-seed sheet, worst cases, main sheet and metrics.

Run with explicit directories while iterating::

    python preset_dev/phase2c_compare.py -- --a-dir <A> --c-dir <C> \
        --c-extra <C extras> --reg-a <A regression> --reg-c <C regression> \
        --out <output>
"""

import glob
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "phase2c")
A_DIR = os.path.join(OUT, "raw", "A")
C_DIR = os.path.join(OUT, "raw", "C")
C_EXTRA = os.path.join(OUT, "raw", "C_extra")
REG_A = os.path.join(OUT, "regression", "A")
REG_C = os.path.join(OUT, "regression", "C")
V1_IMAGE = os.path.join(HERE, "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")
V1_MASK = os.path.join(HERE, "phase1", "mask_v1_0_3_1280x720.png")
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
    if image.size != size:
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
    worst_largest = sorted(records, key=lambda item: -item["largest_component"])[:4]
    worst_coverage = sorted(records, key=lambda item: item["coverage"])[:4]
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
        "perimeter_min": round(float(min(perim)), 3),
        "worst_largest": [{"seed": item["seed"],
                           "coverage": item["coverage"],
                           "components": item["components"],
                           "largest": item["largest_component"],
                           "perimeter": item["perimeter_norm"]}
                          for item in worst_largest],
        "worst_coverage": [{"seed": item["seed"],
                            "coverage": item["coverage"],
                            "components": item["components"],
                            "largest": item["largest_component"]}
                           for item in worst_coverage],
    }


def timing(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    values = [item["render_ms"] for item in data["seeds"]]
    return {
        "first_render_ms": values[0] if values else None,
        "render_ms_median": round(float(np.median(values)), 1) if values else None,
        "group_nodes": data.get("group_nodes"),
        "world_nodes": data.get("world_nodes"),
    }


def regression():
    result = {}
    for sub, family in (("strat", "STRATOCUMULUS"), ("cirrus", "CIRRUS")):
        tag = family.lower()
        a = os.path.join(REG_A, sub,
                         "A_main_%s_a060_s17_1280x720.png" % tag)
        c = os.path.join(REG_C, sub,
                         "C_main_%s_a060_s17_1280x720.png" % tag)
        if not (os.path.exists(a) and os.path.exists(c)):
            result[family] = {"identical": False, "error": "missing render"}
            continue
        aa = np.asarray(Image.open(a).convert("RGB"), dtype=np.uint8)
        cc = np.asarray(Image.open(c).convert("RGB"), dtype=np.uint8)
        result[family] = {
            "identical": bool(np.array_equal(aa, cc)),
            "max_delta": int(np.abs(aa.astype(np.int16)
                                    - cc.astype(np.int16)).max()),
        }
    return result


def main():
    global OUT, A_DIR, C_DIR, C_EXTRA, REG_A, REG_C
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    for index, item in enumerate(argv):
        if index + 1 >= len(argv):
            continue
        if item == "--a-dir":
            A_DIR = os.path.abspath(argv[index + 1])
        elif item == "--c-dir":
            C_DIR = os.path.abspath(argv[index + 1])
        elif item == "--c-extra":
            C_EXTRA = os.path.abspath(argv[index + 1])
        elif item == "--reg-a":
            REG_A = os.path.abspath(argv[index + 1])
        elif item == "--reg-c":
            REG_C = os.path.abspath(argv[index + 1])
        elif item == "--out":
            OUT = os.path.abspath(argv[index + 1])
    os.makedirs(OUT, exist_ok=True)

    v1_metrics, v1_mask, v1_image = analyze(
        "v1.0.3", V1_IMAGE, None,
        mask=np.asarray(Image.open(V1_MASK).convert("L")) > 127)

    a_off = os.path.join(A_DIR, "A_off_1280x720.png")
    c_off = os.path.join(C_DIR, "C_off_1280x720.png")
    a_records, c_records = [], []
    a_images, c_images = {}, {}
    for seed in range(20):
        a_path = os.path.join(A_DIR, "A_s%02d_1280x720.png" % seed)
        c_path = os.path.join(C_DIR, "C_s%02d_1280x720.png" % seed)
        a_metrics, a_mask, a_image = analyze(
            "A s%02d" % seed, a_path, a_off)
        c_metrics, c_mask, c_image = analyze(
            "C s%02d" % seed, c_path, c_off)
        a_metrics["seed"] = seed
        c_metrics["seed"] = seed
        a_records.append(a_metrics)
        c_records.append(c_metrics)
        a_images[seed] = (a_image, a_mask)
        c_images[seed] = (c_image, c_mask)

    # Main sheet: v1.0.3 / A / C at seed 17, images and masks.
    main_row = [
        ("v1.0.3 - cov %.3f" % v1_metrics["coverage"], v1_image),
        ("A s17 - cov %.3f, %d comp, largest %.3f"
         % (a_records[17]["coverage"], a_records[17]["components"],
            a_records[17]["largest_component"]), a_images[17][0]),
        ("C s17 - cov %.3f, %d comp, largest %.3f"
         % (c_records[17]["coverage"], c_records[17]["components"],
            c_records[17]["largest_component"]), c_images[17][0]),
    ]
    mask_row = [
        ("mask - v1.0.3", mask_image(v1_mask)),
        ("mask - A s17", mask_image(a_images[17][1])),
        ("mask - C s17", mask_image(c_images[17][1])),
    ]
    sheet([main_row, mask_row], os.path.join(OUT, "contact_main.png"),
          (1280, 720))
    mask_image(a_images[17][1]).save(os.path.join(OUT, "mask_A_main.png"))
    mask_image(c_images[17][1]).save(os.path.join(OUT, "mask_C_main.png"))

    # 20-seed overview, thumbnails.
    a_rows, c_rows = [], []
    for block in range(4):
        a_row, c_row = [], []
        for col in range(5):
            seed = block * 5 + col
            a_row.append(("A s%02d cov %.3f / L %.3f"
                          % (seed, a_records[seed]["coverage"],
                             a_records[seed]["largest_component"]),
                          a_images[seed][0]))
            c_row.append(("C s%02d cov %.3f / L %.3f"
                          % (seed, c_records[seed]["coverage"],
                             c_records[seed]["largest_component"]),
                          c_images[seed][0]))
        a_rows.append(a_row)
        c_rows.append(c_row)
    sheet(a_rows, os.path.join(OUT, "contact_20seeds_A.png"),
          (320, 180), title_size=14)
    sheet(c_rows, os.path.join(OUT, "contact_20seeds_C.png"),
          (320, 180), title_size=14)
    # Combined A over C, same seeds.
    combined = []
    for index in range(4):
        combined.append(a_rows[index])
        combined.append(c_rows[index])
    sheet(combined, os.path.join(OUT, "contact_20seeds.png"),
          (320, 180), title_size=14)

    # Worst cases: four highest C largest shares, A and C at the same seeds.
    worst = sorted(c_records, key=lambda item: -item["largest_component"])[:4]
    worst_a = [("A s%02d cov %.3f / L %.3f"
                % (item["seed"], a_records[item["seed"]]["coverage"],
                   a_records[item["seed"]]["largest_component"]),
                a_images[item["seed"]][0]) for item in worst]
    worst_c = [("C s%02d cov %.3f / L %.3f"
                % (item["seed"], item["coverage"],
                   item["largest_component"]),
                c_images[item["seed"]][0]) for item in worst]
    sheet([worst_a, worst_c], os.path.join(OUT, "contact_worst.png"),
          (640, 360), title_size=18)

    # Coverage progression at seed 17.
    coverage_rows = []
    for candidate, directory, prefix in (
            ("A", A_DIR, "A_main_a%s_s17_1280x720.png"),
            ("C", C_EXTRA, "C_main_a%s_s17_1280x720.png")):
        row = []
        for label, amount, shown in (("low", "060", "0.60"),
                                     ("medium", "070", "0.70"),
                                     ("high", "078", "0.78")):
            path = os.path.join(directory, prefix % amount)
            if not os.path.exists(path):
                continue
            result = analyze("%s %s" % (candidate, label), path,
                             a_off if candidate == "A" else c_off)
            row.append(("%s %s %s - cov %.3f"
                        % (candidate, label, shown, result[0]["coverage"]),
                        result[2]))
        if row:
            coverage_rows.append(row)
    if coverage_rows:
        sheet(coverage_rows, os.path.join(OUT, "contact_coverage.png"),
              (640, 360), title_size=18)

    # Alternate view.
    alt_paths = (
        ("A", os.path.join(A_DIR, "A_alt_a078_s17_1280x720.png"),
         os.path.join(A_DIR, "A_alt_off_1280x720.png")),
        ("C", os.path.join(C_EXTRA, "C_alt_a078_s17_1280x720.png"),
         os.path.join(C_EXTRA, "C_alt_off_1280x720.png")),
    )
    alt_row = []
    alt_metrics = {}
    for candidate, on_path, off_path in alt_paths:
        if os.path.exists(on_path):
            result = analyze(candidate + " alt", on_path, off_path)
            alt_metrics[candidate] = result[0]
            alt_row.append(("%s alt - cov %.3f, %d comp"
                            % (candidate, result[0]["coverage"],
                               result[0]["components"]), result[2]))
    if alt_row:
        sheet([alt_row], os.path.join(OUT, "contact_alt.png"),
              (1280, 720))

    report = {
        "v1.0.3": v1_metrics,
        "A": {"seeds": a_records, "summary": summary(a_records),
              "timing": timing(os.path.join(A_DIR, "meta_A.json"))},
        "C": {"seeds": c_records, "summary": summary(c_records),
              "timing": timing(os.path.join(C_DIR, "meta_C.json"))},
        "coverage": {"A": {}, "C": {}},
        "alt": alt_metrics,
        "regression": regression(),
        "threshold": THRESHOLD,
        "target_coverage": 0.42,
        "tolerance": 0.02,
    }
    for label, amount in (("low", "060"), ("medium", "070"), ("high", "078")):
        for candidate, directory, prefix, off in (
                ("A", A_DIR, "A_main_a%s_s17_1280x720.png", a_off),
                ("C", C_EXTRA, "C_main_a%s_s17_1280x720.png", c_off)):
            path = os.path.join(directory, prefix % amount)
            if os.path.exists(path):
                result = analyze("%s %s" % (candidate, label), path, off)
                report["coverage"][candidate][label] = result[0]
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    for candidate in ("A", "C"):
        item = report[candidate]["summary"]
        print("PHASE2C %s cov %.3f [%.3f..%.3f] largest mean %.3f max %.3f "
              "components %.1f [%d..%d] perim %.2f"
              % (candidate, item["coverage_mean"], item["coverage_min"],
                 item["coverage_max"], item["largest_mean"],
                 item["largest_max"], item["components_mean"],
                 item["components_min"], item["components_max"],
                 item["perimeter_mean"]))
    print("PHASE2C regression", report["regression"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
