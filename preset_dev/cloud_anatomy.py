"""Single-mass anatomy test for the 2D Cumulus prototype.

Renders one isolated Cumulus silhouette per variant and specimen as a
black/white mask. No colours, shading or glow: this is a contour study.

    blender -b --factory-startup --python preset_dev/cloud_anatomy.py -- \
        --out preset_dev/cloud_distribution/anatomy
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cloud_distribution_proto as proto  # noqa: E402

W, H = 1040, 880
XMIN, XMAX = -1.30, 1.30
YMIN, YMAX = -0.40, 1.80
VARIANTS = ("baseline", "hierarchical", "asymmetric")
SPECIMENS = ((1.05, 0.86), (1.25, 0.92), (1.15, 0.80))


def warp_fields(rng, variant):
    if variant == "baseline":
        wx = (proto.fbm(W, H, rng, base=(3, 3), octaves=3) - 0.5) * 2.0 \
            * proto.WARP
        wy = (proto.fbm(W, H, rng, base=(3, 3), octaves=3) - 0.5) * 2.0 \
            * proto.WARP
        return wx, wy
    wx = np.zeros((H, W), dtype=np.float32)
    wy = np.zeros((H, W), dtype=np.float32)
    for base, amplitude, octaves in (((2, 2), 0.070, 2),
                                     ((8, 7), 0.035, 2),
                                     ((22, 18), 0.012, 1)):
        wx += ((proto.fbm(W, H, rng, base=base, octaves=octaves) - 0.5)
               * 2.0) * amplitude
        wy += ((proto.fbm(W, H, rng, base=base, octaves=octaves) - 0.5)
               * 2.0) * amplitude
    return wx, wy


def mass_spec(variant, tall, width, rng):
    if variant == "baseline":
        body = {"cx": 0.0, "cy": 0.0, "rx": width, "ry": 0.38 * tall}
        lobes = proto.baseline_lobes(rng, tall)
        base = {"y": -0.22, "wave": 0.0, "freq": 0.9,
                "phase": 0.0, "soft": 0.0}
    else:
        body, lobes, base = proto.variant_anatomy(rng, tall, width, variant)
    return {"body": body, "lobes": lobes, "base": base}


def save_mask(mask, path):
    image = bpy.data.images.new(os.path.basename(path), width=W, height=H,
                                alpha=False, float_buffer=False)
    rgba = np.empty((H, W, 4), dtype=np.float32)
    rgba[:, :, :3] = np.flipud(mask.astype(np.float32))[:, :, None]
    rgba[:, :, 3] = 1.0
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    image.file_format = "PNG"
    image.filepath_raw = path
    image.save()
    bpy.data.images.remove(image)


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_distribution", "anatomy")}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    x = np.linspace(XMIN, XMAX, W, dtype=np.float32)[None, :]
    y = np.linspace(YMAX, YMIN, H, dtype=np.float32)[:, None]
    records = []
    for variant in VARIANTS:
        for index, (tall, width) in enumerate(SPECIMENS):
            rng = np.random.default_rng(900 + index)
            spec = mass_spec(variant, tall, width, rng)
            wrng = np.random.default_rng(
                1400 + index * 10 + VARIANTS.index(variant))
            wx, wy = warp_fields(wrng, variant)
            distance = proto.mass_distance(x + wx, y + wy, spec)
            field = np.clip(1.0 - np.maximum(distance, 0.0) / proto.EDGE,
                            0.0, 1.0)
            mask = field > 0.5
            name = "anatomy_%s_%d.png" % (variant, index)
            save_mask(mask, os.path.join(out, name))
            records.append({
                "variant": variant, "specimen": index,
                "file": name, "tall": tall, "width": width,
                "primitives": 1 + len(spec["lobes"]),
                "body": spec["body"], "base": spec["base"],
            })
            print("ANATOMY", variant, index, "primitives",
                  len(spec["lobes"]) + 1)
    with open(os.path.join(out, "anatomy.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"size": [W, H], "bounds": [XMIN, XMAX, YMIN, YMAX],
                   "threshold": 0.5, "records": records}, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
