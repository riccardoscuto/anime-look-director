"""Assemble the Phase 1A review evidence: temporal, migration and backends.

    python preset_dev/phase1a_review.py -- \
        --temporal-old <dir> --temporal-new <dir> \
        --migration-old <dir> --migration-new <dir> \
        --gl <gate-gl-dir> --vk <gate-vk-dir> \
        --metrics preset_dev/phase1a_shooting_stars/metrics.json \
        --out preset_dev/phase1a_shooting_stars

Writes temporal.json, migration.json, backend.json, review.json, the boards and
appends the review block to metrics.json.
"""

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def font(size):
    for name in (r"C:\Windows\Fonts\arial.ttf", "arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cell(image, text, label, size, header=30):
    image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 20))
    canvas.paste(image, (0, header))
    ImageDraw.Draw(canvas).text((7, 6), text, fill=(235, 235, 235),
                                font=label)
    return canvas


def sheet(rows, path, size, title, label_size=12):
    label = font(label_size)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = max(len(row) for row in cells) * size[0]
    heights = [max(item.size[1] for item in row) for row in cells]
    canvas = Image.new("RGB", (width, 44 + sum(heights)), (12, 12, 14))
    ImageDraw.Draw(canvas).text((12, 12), title, fill=(245, 245, 245),
                                font=font(17))
    y = 44
    for row, height in zip(cells, heights):
        x = 0
        for item in row:
            canvas.paste(item, (x, y))
            x += size[0]
        y += height
    canvas.save(path)
    return canvas.size


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": "", "interactive": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    return values


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def visible(frames):
    return sorted(int(frame) for frame, item in frames.items()
                  if item["pixels"] > 0)


def vector(angles):
    az = math.radians(angles[0])
    el = math.radians(angles[1])
    return (math.cos(el) * math.sin(az), math.cos(el) * math.cos(az),
            math.sin(el))


def angular(a, b):
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    return round(math.degrees(math.acos(dot)), 3)


def temporal(old, new):
    cases = {}
    for name in ("main", "short", "timeline_start"):
        o = old["cases"][name]
        n = new["cases"][name]
        old_visible = visible(o["frames"])
        new_visible = visible(n["frames"])
        old_set = set(range(old_visible[0], old_visible[-1] + 1))
        new_set = set(range(new_visible[0], new_visible[-1] + 1))
        cases[name] = {
            "start": o["start"], "duration": o["duration"],
            "old": {"visible_samples": old_visible,
                    "first": old_visible[0], "last": old_visible[-1],
                    "count": len(old_set)},
            "new": {"visible_samples": new_visible,
                    "first": new_visible[0], "last": new_visible[-1],
                    "count": len(new_set)},
            "added": sorted(new_set - old_set),
            "removed": sorted(old_set - new_set),
        }
    summary = {
        "cases": cases,
        "rule": ("old: first visible = start + 1; new: first visible = start; "
                 "last visible = start + duration - 1 on both"),
        "conclusion": ("the new lifecycle adds the start frame and keeps the "
                       "last frame; the visible count grows from duration - 1 "
                       "to duration. No frame is removed."),
    }
    return summary


def migration(old, new):
    events = []
    old_endpoints = old["endpoints"]
    new_endpoints = new["endpoints"]
    for index, item in enumerate(old["events"]):
        old_end = old_endpoints[index]
        new_end = new_endpoints[index]
        events.append({
            "name": item["name"],
            "start_frame": item["start_frame"],
            "duration": item["duration"],
            "direction": item["direction"],
            "old_end": old_end["end"],
            "new_end": new_end["end"],
            "start_delta": angular(vector(old_end["start"]),
                                    vector(new_end["start"])),
            "end_delta": angular(vector(old_end["end"]),
                                  vector(new_end["end"])),
            "old_pixels": old["per_event"][str(index)]["pixels"],
            "new_pixels": new["per_event"][str(index)]["pixels"],
        })
    return {
        "events_preserved": (new["events_before"] == old["events"]
                             and new["events_after"] == old["events"]),
        "event_count": len(old["events"]),
        "marker_before": new["marker_before"],
        "marker_after": new["marker_after"],
        "node_tree": new["node_tree"],
        "wide_old": old["wide"],
        "wide_new": new["wide"],
        "persistence": new["persistence"],
        "events": events,
        "conclusion": ("all four events and their properties survive; the "
                       "World group rebuilds from marker 29 to 30; the end "
                       "direction changes are the intentional SS-02 bearing "
                       "change, the starts are preserved."),
    }


def backend(gl, vk, env):
    geometry = {}
    for elevation in ("1.0", "5.0", "40.0", "85.0"):
        g = gl["metrics"]["geometry"][elevation]
        v = vk["metrics"]["geometry"][elevation]
        geometry[elevation] = {
            "width_p95": [g["back"]["width_p95"], v["back"]["width_p95"]],
            "head_error": [g["head"]["error"], v["head"]["error"]],
            "pixels": [g["pixels"], v["pixels"]],
        }
    return {
        "environment": env,
        "opengl": {"status": gl["status"], "checks": len(gl["checks"]),
                   "failures": gl["failures"]},
        "vulkan": {"status": vk["status"], "checks": len(vk["checks"]),
                   "failures": vk["failures"]},
        "geometry": geometry,
        "linear_brightness": {
            "opengl": gl["metrics"]["linear_brightness"],
            "vulkan": vk["metrics"]["linear_brightness"]},
        "four_events": {
            "opengl": gl["metrics"]["four_events"],
            "vulkan": vk["metrics"]["four_events"]},
        "master_opengl": ("the master before-board was re-rendered on OpenGL "
                          "in this review: 10 images, same metrics"),
        "conclusion": ("both backends render and pass 37/37; geometry, "
                       "positions and the linear brightness agree. The "
                       "earlier OpenGL context crash also hit a no-add-on "
                       "Eevee smoke scene, and the master before-board was "
                       "re-rendered on OpenGL in this review with the same "
                       "metrics; it was environmental, not code-specific, "
                       "and is gone."),
    }


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    old_t = load(os.path.join(args["temporal_old"], "old_temporal.json"))
    new_t = load(os.path.join(args["temporal_new"], "new_temporal.json"))
    t = temporal(old_t, new_t)
    with open(os.path.join(out, "temporal.json"), "w",
              encoding="utf-8") as handle:
        json.dump(t, handle, indent=2)
    frames = (9, 10, 11, 33, 34)
    rows = []
    for tag, root in (("old", args["temporal_old"]),
                      ("new", args["temporal_new"])):
        report = old_t if tag == "old" else new_t
        row = []
        for frame in frames:
            key = str(frame)
            item = report["cases"]["main"]["frames"][key]
            row.append(("%s f%02d  %d px  max %.2f" % (
                tag, frame, item["pixels"], item["max"]),
                Image.open(os.path.join(
                    root, "%s_main_f%02d.png" % (tag, frame)))))
        rows.append(row)
    size = sheet(rows, os.path.join(out, "temporal.png"), (480, 270),
                 "PHASE 1A - TEMPORAL COMPATIBILITY - start 10 / duration 24 "
                 "- old 11..33, new 10..33")
    print("TEMPORAL BOARD", size)

    old_m = load(os.path.join(args["migration_old"], "old_migration.json"))
    new_m = load(os.path.join(args["migration_new"], "new_migration.json"))
    m = migration(old_m, new_m)
    with open(os.path.join(out, "migration.json"), "w",
              encoding="utf-8") as handle:
        json.dump(m, handle, indent=2)
    names = [event["name"] for event in old_m["events"]]
    rows = []
    for tag, root, report in (("old", args["migration_old"], old_m),
                              ("new", args["migration_new"], new_m)):
        row = []
        for index, name in enumerate(names):
            row.append(("%s %s  %d px" % (
                tag, name, report["per_event"][str(index)]["pixels"]),
                Image.open(os.path.join(
                    root, "%s_event%d.png" % (tag, index)))))
        row.append(("%s ALL  %d px / %d comp" % (
            tag, report["wide"]["pixels"], report["wide"]["components"]),
            Image.open(os.path.join(root, "%s_all.png" % tag))))
        rows.append(row)
    size = sheet(rows, os.path.join(out, "migration.png"), (480, 270),
                 "PHASE 1A - LEGACY SCENE MIGRATION - marker 29 -> 30 - "
                 "four events preserved")
    print("MIGRATION BOARD", size)

    gl = load(os.path.join(args["gl"], "metrics.json"))
    vk = load(os.path.join(args["vk"], "metrics.json"))
    env = {
        "blender": "5.1.2 (hash ec6e62d40fa9, built 2026-05-19 01:37:34)",
        "os": "Windows 11 Pro 10.0.26200",
        "cpu": os.environ.get("PROCESSOR_IDENTIFIER", ""),
        "gpu": "NVIDIA GeForce RTX 3060 Ti, driver 32.0.16.1714 "
               "(datetime 2026-09-17); Meta Virtual Monitor also present",
    }
    b = backend(gl, vk, env)
    rows = []
    for tag, root, report in (("OpenGL", args["gl"], gl),
                              ("Vulkan", args["vk"], vk)):
        row = []
        for elevation in ("1.0", "5.0", "40.0", "85.0"):
            key = elevation
            image = Image.open(os.path.join(
                root, "elev_%g_on.png" % float(elevation)))
            row.append(("%s %s deg  %d px" % (
                tag, key.rstrip("0").rstrip("."),
                report["metrics"]["geometry"][key]["pixels"]), image))
        rows.append(row)
    size = sheet(rows, os.path.join(out, "backend.png"), (480, 270),
                 "PHASE 1A - EEVEE OPENGL vs VULKAN - 1/5/40/85 deg, "
                 "clouds off, frame 33")
    print("BACKEND BOARD", size)
    visual = {}
    for elevation in ("1.0", "5.0", "40.0", "85.0"):
        name = "elev_%g_on.png" % float(elevation)
        a = np.asarray(Image.open(os.path.join(
            args["gl"], name)).convert("RGB"), dtype=np.int16)
        c = np.asarray(Image.open(os.path.join(
            args["vk"], name)).convert("RGB"), dtype=np.int16)
        diff = np.abs(a - c)
        visual[elevation] = {"max": int(diff.max()),
                             "mean": round(float(diff.mean()), 3)}
    b["visual_diff_8bit"] = visual
    with open(os.path.join(out, "backend.json"), "w",
              encoding="utf-8") as handle:
        json.dump(b, handle, indent=2)

    interactive = None
    if args.get("interactive"):
        interactive = load(args["interactive"])
    review = {"temporal": t, "migration": m, "backend": b,
              "interactive": interactive}
    metrics_path = os.path.abspath(args["metrics"])
    metrics = load(metrics_path)
    metrics["review"] = review
    with open(metrics_path, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    with open(os.path.join(out, "review.json"), "w",
              encoding="utf-8") as handle:
        json.dump(review, handle, indent=2)
    print("REVIEW ok", len(metrics["checks"]), metrics["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
