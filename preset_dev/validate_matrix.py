"""P6 validation matrix: 3 palettes x 4 families x 3 ages.

Every cell is rendered at 800x450 with the full stack, a fixed camera, seed 17,
exposure 0 and AgX. A background render without FX is used to measure the FX
coverage. The metrics and the acceptance verdicts are written next to the
images, plus a 6x6 contact sheet.

Run::

    blender -b --factory-startup --python preset_dev/validate_matrix.py
"""

import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "validation")
PALETTES = ("TWILIGHT_DUSK", "NEON_NIGHT", "GOLDEN_HOUR")
FAMILIES = ("CHRYSANTHEMUM", "PEONY", "WILLOW", "KAMURO")
AGES = (0.25, 0.7, 1.4)
THUMB = (320, 180)
GRID = (6, 6)

#: The acceptance criteria of the matrix. They are deliberately conservative:
#: they catch an empty or clipped frame, not a subjective look.
LIMITS = {"max_clipped": 0.02, "min_saturation": 0.08,
          "min_coverage": 0.002, "max_render_s": 6.0}


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def metrics(rgb, background):
    delta = np.abs(rgb - background).max(axis=2)
    coverage = float((delta > 0.02).mean())
    maximum = float(rgb.max())
    clipped = float((rgb.max(axis=2) > 0.98).mean())
    saturation = float(((rgb.max(axis=2) - rgb.min(axis=2))
                        / np.maximum(rgb.max(axis=2), 1e-4)).mean())
    return {
        "mean_luminance": round(float(rgb.mean()), 5),
        "max_luminance": round(maximum, 4),
        "clipped_fraction": round(clipped, 5),
        "mean_saturation": round(saturation, 4),
        "coverage": round(coverage, 5),
    }


def verdict(values):
    reasons = []
    if values["clipped_fraction"] > LIMITS["max_clipped"]:
        reasons.append("clipped")
    if values["mean_saturation"] < LIMITS["min_saturation"]:
        reasons.append("desaturated")
    if values["coverage"] < LIMITS["min_coverage"]:
        reasons.append("empty")
    if values["render_s"] > LIMITS["max_render_s"]:
        reasons.append("slow")
    return ("PASS" if not reasons else "FAIL"), reasons


def contact_sheet(entries):
    width, height = GRID[0] * THUMB[0], GRID[1] * THUMB[1]
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    canvas[:, :, 3] = 1.0
    for index, entry in enumerate(entries):
        rgb = read_rgb(entry["path"])
        step_y = max(1, rgb.shape[0] // THUMB[1])
        step_x = max(1, rgb.shape[1] // THUMB[0])
        thumb = rgb[::step_y, ::step_x][:THUMB[1], :THUMB[0]]
        row = index // GRID[0]
        column = index % GRID[0]
        top = height - (row + 1) * THUMB[1]
        left = column * THUMB[0]
        canvas[top:top + thumb.shape[0], left:left + thumb.shape[1],
               :3] = thumb
    image = bpy.data.images.new("ALD Validation Sheet", width=width,
                                height=height, alpha=True)
    image.pixels = canvas.ravel().tolist()
    image.filepath_raw = os.path.join(OUT, "sheet.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return os.path.join(OUT, "sheet.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.fx_gn_prototype = True
    settings.fx_age = 0.0
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.ink_lines = True
    settings.depth_near = 20.0
    settings.depth_far = 220.0
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.fps = 24
    fps = 24.0

    entries = []
    for palette in PALETTES:
        settings.palette = palette
        bpy.ops.ald.apply_palette()
        bpy.ops.ald.build()
        for family in FAMILIES:
            for age in AGES:
                fx.clear(scene)
                fx.create_fireworks(scene, 1, seed=17, distance=55.0,
                                    time=0.0, family=family)
                bpy.ops.ald.build()
                system = scene.ald.fx_systems[0]
                event = system.events[0]
                camera.rotation_euler = (
                    Vector(event.target) - camera.location).to_track_quat(
                        "-Z", "Y").to_euler()
                camera.data.lens = 32.0
                frame = int(system.origin_frame
                            + (event.birth + event.rise_time + age) * fps)
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                name = "%s_%s_%03d" % (palette.lower(), family.lower(),
                                       int(age * 100))
                path = os.path.join(OUT, name + ".png")
                start = time.perf_counter()
                baseline_fx.render(scene, path)
                elapsed = time.perf_counter() - start
                fx.clear(scene)
                bpy.ops.ald.build()
                background_path = os.path.join(OUT, name + "_bg.png")
                baseline_fx.render(scene, background_path)
                values = metrics(read_rgb(path), read_rgb(background_path))
                os.remove(background_path)
                values["render_s"] = round(elapsed, 3)
                state, reasons = verdict(values)
                entries.append({"palette": palette, "family": family,
                                "age": age, "path": path,
                                "frame": frame, **values,
                                "verdict": state, "reasons": reasons})
                print("P6 %-14s %-14s %.2f %s %.3fs coverage %.4f"
                      % (palette, family, age, state, elapsed,
                         values["coverage"]))

    sheet = contact_sheet(entries)
    summary = {
        "plan": "P6 validation matrix",
        "grid": {"palettes": list(PALETTES), "families": list(FAMILIES),
                 "ages": list(AGES), "layout": "6x6, two rows per palette"},
        "limits": LIMITS,
        "renders": entries,
        "sheet": os.path.relpath(sheet, HERE),
        "passed": sum(1 for entry in entries if entry["verdict"] == "PASS"),
        "total": len(entries),
        "mean_render_s": round(
            sum(entry["render_s"] for entry in entries) / len(entries), 3),
    }
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("P6 MATRIX %d/%d PASS | mean %.3fs"
          % (summary["passed"], summary["total"], summary["mean_render_s"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
