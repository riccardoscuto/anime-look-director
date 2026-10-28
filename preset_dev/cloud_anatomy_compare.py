"""Build the single-mass anatomy sheet and metrics."""

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCALE = 2.6 / 1040.0  # local units per pixel (square canvas pixels)


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def peaks(top, minimum=12, window=45, merge=25):
    smooth = np.convolve(top.astype(np.float64), np.ones(5) / 5.0, "same")
    found = []
    for index in range(2, len(smooth) - 2):
        if not (smooth[index] <= smooth[index - 1]
                and smooth[index] <= smooth[index + 1]):
            continue
        left = smooth[max(0, index - window):index].max()
        right = smooth[index + 1:index + window + 1].max()
        if min(left, right) - smooth[index] >= minimum:
            found.append(index)
    merged = []
    for item in found:
        if merged and item - merged[-1] < merge:
            if smooth[item] < smooth[merged[-1]]:
                merged[-1] = item
        else:
            merged.append(item)
    return merged


def analyze(mask):
    rows, cols = np.nonzero(mask)
    row0, row1 = int(rows.min()), int(rows.max())
    col0, col1 = int(cols.min()), int(cols.max())
    area_px = int(mask.sum())
    padded = np.pad(mask, 1)
    interior = (padded[:-2, 1:-1] & padded[2:, 1:-1]
                & padded[1:-1, :-2] & padded[1:-1, 2:])
    perimeter_px = int((mask & ~interior).sum())
    top = np.array([np.argmax(mask[:, col])
                    for col in range(col0, col1 + 1)], dtype=np.float64)
    found = peaks(top)
    low = col0 + int(0.2 * (col1 - col0))
    high = col0 + int(0.8 * (col1 - col0))
    bottom = np.array([np.nonzero(mask[:, col])[0].max()
                       for col in range(low, high + 1)])
    crop = mask[row0:row1 + 1, col0:col1 + 1]
    flip = crop[:, ::-1]
    union = float((crop | flip).sum())
    iou = float((crop & flip).sum()) / max(union, 1.0)
    summit_cols = cols[rows == row0]
    height = (row1 - row0 + 1) * SCALE
    width = (col1 - col0 + 1) * SCALE
    return {
        "width": round(width, 3),
        "height": round(height, 3),
        "area": round(area_px * SCALE * SCALE, 3),
        "perimeter_norm": round(perimeter_px / math.sqrt(max(area_px, 1)), 3),
        "peaks": len(found),
        "peak_height": [round((row1 - (row0 + top[i])) * SCALE, 3)
                        for i in found],
        "symmetry_iou": round(iou, 3),
        "asymmetry": round(1.0 - iou, 3),
        "base_std": round(float(bottom.std()) * SCALE, 4),
        "base_range": round(float(bottom.max() - bottom.min()) * SCALE, 4),
        "summit_offset": round(float(
            (summit_cols.mean() - 0.5 * (col0 + col1))
            / max(col1 - col0, 1)), 3),
    }


def cell(image, text, label, size):
    image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    header = 32
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((7, 7), text, fill=(235, 235, 235),
                                font=label)
    return canvas


def sheet(rows, path, size=(520, 440), label_size=13):
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


def fit(image, size):
    scale = min(size[0] / image.size[0], size[1] / image.size[1])
    resized = image.resize((max(1, round(image.size[0] * scale)),
                            max(1, round(image.size[1] * scale))),
                           Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (0, 0, 0))
    canvas.paste(resized, ((size[0] - resized.size[0]) // 2,
                           (size[1] - resized.size[1]) // 2))
    return canvas


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"anatomy": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    anatomy = os.path.abspath(values["anatomy"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(anatomy, "anatomy.json"),
              encoding="utf-8") as handle:
        report = json.load(handle)
    variants = ("baseline", "hierarchical", "asymmetric")
    specimens = (0, 1, 2)
    records = []
    masks = {}
    for variant in variants:
        for specimen in specimens:
            record = [item for item in report["records"]
                      if item["variant"] == variant
                      and item["specimen"] == specimen][0]
            path = os.path.join(anatomy, record["file"])
            mask = np.asarray(Image.open(path).convert("L")) > 127
            masks[(variant, specimen)] = mask
            metrics = analyze(mask)
            metrics.update({"variant": variant, "specimen": specimen,
                            "height_param": record["tall"],
                            "width_param": record["width"],
                            "primitives": record["primitives"]})
            records.append(metrics)

    rows = []
    for variant in variants:
        row = []
        for specimen in specimens:
            item = [record for record in records
                    if record["variant"] == variant
                    and record["specimen"] == specimen][0]
            text = ("%s s%d  H%.2f W%.2f A%.2f  peaks%d  asym%.2f  base%.3f"
                    % (variant, specimen, item["height"], item["width"],
                       item["area"], item["peaks"], item["asymmetry"],
                       item["base_std"]))
            row.append((text, Image.open(os.path.join(
                anatomy, "anatomy_%s_%d.png" % (variant, specimen)))))
        rows.append(row)
    sheet(rows, os.path.join(out, "contact_anatomy.png"))

    # Detail crops: full, top, base for specimen 1.
    detail_rows = []
    for variant in variants:
        image = Image.open(os.path.join(
            anatomy, "anatomy_%s_1.png" % variant)).convert("L")
        full = image
        top = image.crop((140, 10, 900, 570))
        base = image.crop((140, 540, 900, 880))
        detail_rows.append([
            ("%s full" % variant, full),
            ("%s summit detail" % variant, top),
            ("%s base detail" % variant, base),
        ])
    label = font(13)
    cells = []
    for row in detail_rows:
        line = []
        for text, image in row:
            line.append((text, fit(image.convert("RGB"), (520, 440))))
        cells.append(line)
    sheet(cells, os.path.join(out, "contact_anatomy_detail.png"))

    summary = {}
    for variant in variants:
        items = [record for record in records if record["variant"] == variant]
        summary[variant] = {
            "height": round(float(np.mean([i["height"] for i in items])), 3),
            "width": round(float(np.mean([i["width"] for i in items])), 3),
            "area": round(float(np.mean([i["area"] for i in items])), 3),
            "peaks": round(float(np.mean([i["peaks"] for i in items])), 2),
            "asymmetry": round(float(np.mean([i["asymmetry"] for i in items])),
                               3),
            "base_std": round(float(np.mean([i["base_std"] for i in items])),
                              4),
            "perimeter_norm": round(float(np.mean(
                [i["perimeter_norm"] for i in items])), 3),
        }
    with open(os.path.join(out, "anatomy_metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"records": records, "summary": summary,
                   "scale_units_per_px": SCALE}, handle, indent=2)
    for variant, item in summary.items():
        print("ANATOMY", variant, item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
