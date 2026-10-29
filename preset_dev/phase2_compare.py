"""Build the Phase 2 atmosphere / Sun gate boards."""

import json
import os
import sys

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
                                font=font(18))
    y = 44
    for row, height in zip(cells, heights):
        x = 0
        for item in row:
            canvas.paste(item, (x, y))
            x += size[0]
        y += height
    canvas.save(path)
    return canvas.size


def text_panel(lines, title, size=(960, 360)):
    canvas = Image.new("RGB", size, (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 18), title, fill=(245, 245, 245), font=font(19))
    y = 62
    for line in lines:
        draw.text((18, y), line, fill=(205, 215, 230), font=font(14))
        y += 30
    return canvas


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"before": "", "after": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    before = os.path.abspath(values["before"])
    after = os.path.abspath(values["after"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)

    def img(root, tag, name):
        return Image.open(os.path.join(root, "%s_%s.png" % (tag, name)))

    conditions = (("noon", "noon"), ("golden", "golden"),
                  ("twilight", "twilight"), ("night", "night"))
    for title, suffix, size, filename in (
        ("PHASE 2 - FOUR CONDITIONS - clouds off - same camera", "", (640, 360),
         "board_conditions.png"),
        ("PHASE 2 - SECOND FRAMING - 50 mm", "_second", (640, 360),
         "board_second.png"),
    ):
        rows = []
        for root, tag, label in ((before, "before5", "before 1.5/6"),
                                 (after, "final7", "after 1.0/4")):
            row = []
            for name, label2 in conditions:
                row.append(("%s %s" % (label, label2),
                            img(root, tag, name + suffix)))
            rows.append(row)
        sheet(rows, os.path.join(out, filename), size, title)

    elevations = ("+8.0", "+4.0", "+2.0", "+0.0", "-1.0", "-2.0",
                  "-4.0", "-8.0")
    rows = []
    for root, tag, label in ((before, "before5", "before 1.5/6"),
                             (after, "final7", "after 1.0/4")):
        rows.append([(label + " " + elevation,
                      img(root, tag, "sweep_" + elevation))
                     for elevation in elevations])
    sheet(rows, os.path.join(out, "board_sweep.png"), (320, 180),
          "PHASE 2 - SUN ACROSS THE HORIZON - elevation +8..-8 - clouds off",
          11)

    rows = []
    for root, tag, label in ((before, "before5", "before 1.5/6"),
                             (after, "final7", "after 1.0/4")):
        rows.append([("%s offset %s" % (label, offset),
                      img(root, tag, "offset_" + offset))
                     for offset in ("-0.5", "+0.0", "+0.5")])
    sheet(rows, os.path.join(out, "board_offsets.png"), (640, 360),
          "PHASE 2 - HORIZON OFFSET - -0.5 / 0.0 / +0.5 - golden hour")

    rows = [
        [("softness 0.15", img(after, "final7", "softness_15")),
         ("softness 0.50", img(after, "final7", "softness_50")),
         ("softness 0.90", img(after, "final7", "softness_90"))],
        [("accent 0.0", img(after, "final7", "accent_00")),
         ("accent 0.3", img(after, "final7", "accent_30")),
         ("accent 0.6", img(after, "final7", "accent_60"))],
    ]
    sheet(rows, os.path.join(out, "board_controls.png"), (480, 270),
          "PHASE 2 - HORIZON SOFTNESS AND SKY ACCENT - distinct controls")

    before_ui = json.load(open(os.path.join(
        before, "before5_audit.json"), encoding="utf-8"))["ui"]
    after_ui = json.load(open(os.path.join(
        after, "final7_audit.json"), encoding="utf-8"))["ui"]
    ui = text_panel([
        "Sun Elevation requested: -18.00 deg",
        "BEFORE  property %.2f   actual %.2f   World disk %.2f" % (
            before_ui["property"], before_ui["actual_elevation"],
            before_ui["world_elevation"]),
        "AFTER   property %.2f   actual %.2f   World disk %.2f" % (
            after_ui["property"], after_ui["actual_elevation"],
            after_ui["world_elevation"]),
        "The UI range now accepts the night elevation and the World disk",
        "is updated immediately when the property changes.",
    ], "PHASE 2 - SUN ELEVATION UI AND IMMEDIATE WORLD SYNC")
    ui.save(os.path.join(out, "board_ui.png"))

    before_json = json.load(open(os.path.join(
        before, "before5_audit.json"), encoding="utf-8"))
    after_json = json.load(open(os.path.join(
        after, "final7_audit.json"), encoding="utf-8"))
    metrics = {
        "method": ("1280x720, Eevee 32 samples, AgX, exposure 0, clouds off, "
                   "no compositor; before/after share camera and palettes."),
        "before": {"sun_size": 1.5, "sun_strength": 6.0,
                   "ui": before_json["ui"],
                   "conditions": before_json["conditions"],
                   "sweep": before_json["sweep"],
                   "offsets": before_json["offsets"]},
        "after": {"sun_size": 1.0, "sun_strength": 4.0,
                  "ui": after_json["ui"],
                  "conditions": after_json["conditions"],
                  "sweep": after_json["sweep"],
                  "offsets": after_json["offsets"],
                  "softness": after_json["softness"],
                  "accent": after_json["accent"]},
        "changes": [
            "Sun Elevation min -5 -> -30 deg",
            "World disk direction updated on the property change",
            "Sun disk radius 1.5 -> 1.0 deg; strength 6 -> 4",
            "Sun disk masked by the ground gradient at the horizon",
            "World marker 31 -> 32",
        ],
        "decision": "TECHNICAL PASS - VISUAL REVIEW PENDING",
    }
    json.dump(metrics, open(os.path.join(out, "phase2_metrics.json"), "w",
                            encoding="utf-8"), indent=2)
    print("PHASE2 BOARDS ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
