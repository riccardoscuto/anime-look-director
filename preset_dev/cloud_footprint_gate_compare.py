"""Sheets and metrics for the final cloud footprint visual gate."""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SEEDS = (3, 17, 42)
ELEVATIONS = (0, 30, 60, 85)
AZIMUTHS = (0, 90)
V1_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "world_baseline", "v1.0.3",
                        "summer_noon_1280x720.png")


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(image, text, label, size):
    image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    header = 30
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((7, 6), text, fill=(235, 235, 235),
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
    values = {"gate": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    gate = os.path.abspath(values["gate"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(gate, "gate.json"), encoding="utf-8") as handle:
        report = json.load(handle)
    coverage = {}
    for record in report["records"]:
        for frame in record["frames"]:
            coverage[(record["seed"], frame["elevation"],
                      frame["azimuth"])] = frame["coverage"]
    for azimuth in AZIMUTHS:
        rows = []
        for elevation in ELEVATIONS:
            row = []
            for seed in SEEDS:
                item = coverage[(seed, elevation, azimuth)]
                row.append((
                    "F  seed %02d  elev %03d  azim %03d  cov %.3f"
                    % (seed, elevation, azimuth, item),
                    Image.open(os.path.join(
                        gate, "gate_F_s%02d_e%03d_a%03d.png"
                        % (seed, elevation, azimuth)))))
            rows.append(row)
        sheet(rows, os.path.join(out, "contact_gate_az%03d.png" % azimuth),
              (640, 360), 14)
    mask_rows = []
    for elevation in ELEVATIONS:
        for azimuth in AZIMUTHS:
            row = []
            for seed in SEEDS:
                item = coverage[(seed, elevation, azimuth)]
                row.append((
                    "mask s%02d e%03d a%03d  %.3f"
                    % (seed, elevation, azimuth, item),
                    Image.open(os.path.join(
                        gate, "gate_mask_s%02d_e%03d_a%03d.png"
                        % (seed, elevation, azimuth)))))
            mask_rows.append(row)
    sheet(mask_rows, os.path.join(out, "contact_gate_masks.png"),
          (480, 270), 12)

    # Native 1:1 details: upper-sky banks and isolated masses.
    details = []
    f85 = Image.open(os.path.join(
        gate, "gate_F_s17_e085_a090.png")).convert("RGB")
    f60 = Image.open(os.path.join(
        gate, "gate_F_s17_e060_a090.png")).convert("RGB")
    f30 = Image.open(os.path.join(
        gate, "gate_F_s17_e030_a000.png")).convert("RGB")
    f0 = Image.open(os.path.join(
        gate, "gate_F_s17_e000_a000.png")).convert("RGB")
    details.append([
        ("F s17 e085 a090  1:1  zenith bank", f85.crop((500, 120, 1140, 480))),
        ("F s17 e060 a090  1:1  upper bank", f60.crop((0, 80, 640, 440))),
        ("F s17 e030 a000  1:1  merged bank", f30.crop((1100, 60, 1740, 420))),
    ])
    v1 = Image.open(V1_IMAGE).convert("RGB")
    details.append([
        ("v1.0.3  1:1  articulated clouds", v1.crop((320, 0, 960, 360))),
        ("v1.0.3  1:1  articulated clouds", v1.crop((0, 100, 640, 460))),
        ("F s17 e000 a000  1:1  isolated tower", f0.crop((480, 0, 1120, 360))),
    ])
    sheet(details, os.path.join(out, "contact_gate_detail.png"),
          (640, 360), 13)

    summary = {}
    for elevation in ELEVATIONS:
        values_ = [coverage[(seed, elevation, azimuth)]
                   for seed in SEEDS for azimuth in AZIMUTHS]
        summary["elev_%03d" % elevation] = {
            "mean": round(float(np.mean(values_)), 4),
            "min": round(float(min(values_)), 4),
            "max": round(float(max(values_)), 4),
        }
    for seed in SEEDS:
        record = [item for item in report["records"]
                  if item["seed"] == seed][0]
        summary["seed_%02d" % seed] = {
            "global_coverage": record["global_coverage"],
            "cutoff": record["cutoff"],
        }
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"coverage": {"%d_%03d_%03d" % key: value
                                for key, value in coverage.items()},
                   "summary": summary,
                   "report": report}, handle, indent=2)
    for key, item in summary.items():
        print("GATE", key, item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
