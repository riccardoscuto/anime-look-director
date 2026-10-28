"""Phase A feasibility: fixed silhouettes with the current 92-94 masses.

Computes the angular area of every fixed silhouette (sum before overlap) and
the union of the current layout, for the hierarchical anatomy at the baseline
radii (config B). No Cloud Amount deformation is involved.

    blender -b --factory-startup --python preset_dev/cloud_footprint_feasibility.py
"""

import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cloud_distribution_proto as proto  # noqa: E402

W, H = 2048, 1024
AA = 0.02


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_footprint"),
              "radii_base": "", "seeds": "3,17,42"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["seeds"] = [int(x) for x in values["seeds"].split(",") if x]
    return values


def mass_silhouette(spec, dirs, warp_x, warp_y):
    radius = spec["radius"]
    lon = spec["u"] * 2.0 * math.pi
    center = np.array([math.cos(spec["lat"]) * math.cos(lon),
                       math.cos(spec["lat"]) * math.sin(lon),
                       math.sin(spec["lat"])], dtype=np.float32)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0], dtype=np.float32)
    up = np.cross(center, east)
    up /= max(float(np.linalg.norm(up)), 1e-6)
    reach = 1.8 * radius
    lat0 = max(-math.pi / 2.0, spec["lat"] - reach)
    lat1 = min(math.pi / 2.0, spec["lat"] + reach)
    height, width = dirs.shape[:2]
    row0 = max(0, int(math.floor((lat0 / math.pi + 0.5) * height)))
    row1 = min(height, int(math.ceil((lat1 / math.pi + 0.5) * height)) + 1)
    if lat0 <= -math.pi / 2.0 or lat1 >= math.pi / 2.0:
        cos_min = 0.0
    else:
        cos_min = min(math.cos(lat0), math.cos(lat1))
    d_lon = (math.pi if cos_min < 0.12 else
             math.asin(min(1.0, math.sin(reach) / cos_min)))
    col_start = int(math.floor(
        ((lon - d_lon) / (2.0 * math.pi)) * width)) - 1
    col_count = int(math.ceil(2.0 * d_lon / (2.0 * math.pi) * width)) + 3
    if col_count >= width:
        cols = np.arange(width)
    else:
        cols = np.arange(col_start, col_start + col_count) % width
    sub = dirs[row0:row1][:, cols]
    dot = sub @ center
    safe = np.maximum(dot, 0.20)
    tangent = safe * math.tan(radius)
    x = (sub @ east) / tangent + warp_x[row0:row1][:, cols]
    y = (sub @ up) / (tangent * spec["aspect"]) \
        + warp_y[row0:row1][:, cols]
    distance = proto.mass_distance(x, y, spec)
    alpha = np.clip(0.5 - distance / AA, 0.0, 1.0)
    alpha *= dot > 0.20
    return row0, row1, cols, alpha


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    dirs, _lat = proto.directions(W, H)
    report = {"count": 0, "seeds": {}, "AA": AA}
    for seed in args["seeds"]:
        data = proto.generate_field(W, H, seed, "hierarchical",
                                    radii_from=args["radii_base"])
        specs = data["masses"]
        weights = data["weights"]
        sky = data["sky"]
        sky_weight = float(weights[sky].sum())
        union = np.zeros((H, W), dtype=bool)
        areas = []
        for spec in specs:
            row0, row1, cols, alpha = mass_silhouette(
                spec, dirs, data["warp_x"], data["warp_y"])
            mask = (alpha >= 0.5) & sky[row0:row1][:, cols]
            area = float(weights[row0:row1][:, cols][mask].sum())
            areas.append(area)
            union[row0:row1, cols] |= mask
        union_area = float(weights[union].sum())
        report["seeds"][str(seed)] = {
            "masses": len(specs),
            "mean_radius_deg": round(float(np.mean(
                [math.degrees(spec["radius"]) for spec in specs])), 2),
            "sum_fraction": round(sum(areas) / sky_weight, 4),
            "union_fraction": round(union_area / sky_weight, 4),
            "mean_area_fraction": round(float(np.mean(areas)) / sky_weight, 5),
            "sum_sr": round(sum(areas) / sky_weight * 2.0 * math.pi, 4),
            "union_sr": round(union_area / sky_weight * 2.0 * math.pi, 4),
        }
        print("FEAS", seed, "masses", len(specs),
              "sum", round(sum(areas) / sky_weight, 4),
              "union", round(union_area / sky_weight, 4))
    with open(os.path.join(out, "feasibility.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
