"""Build the Phase 1B visual boards from the 2.60.1 and Phase 1A renders."""

import json
import os
import subprocess
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


def crop(image, box, size):
    return image.convert("RGB").crop(box).resize(size, Image.Resampling.LANCZOS)


def target_panel(size=(480, 360)):
    canvas = Image.new("RGB", size, (10, 13, 22))
    draw = ImageDraw.Draw(canvas)
    points = [(55, 285), (130, 245), (210, 200), (290, 155), (365, 112)]
    widths = [11, 8, 5, 3, 1]
    for (x0, y0), (x1, y1), w0, w1 in zip(points, points[1:],
                                          widths, widths[1:]):
        draw.line((x0, y0, x1, y1), fill=(220, 235, 255), width=max(w0, 1))
        draw.ellipse((x1 - w1, y1 - w1, x1 + w1, y1 + w1),
                     fill=(240, 248, 255))
    draw.ellipse((357, 104, 373, 120), fill=(180, 210, 255))
    draw.ellipse((361, 108, 369, 116), fill=(255, 255, 255))
    draw.text((16, 16), "TARGET (schematic, not a render)",
              fill=(245, 245, 245), font=font(16))
    draw.text((16, 42), "small bright head + continuous tapered trail",
              fill=(190, 200, 220), font=font(12))
    draw.text((16, 60), "intensity falls toward the tail; soft temporal fade",
              fill=(190, 200, 220), font=font(12))
    draw.text((16, 330), "reference for the five visual criteria",
              fill=(140, 150, 170), font=font(11))
    return canvas


def metrics_panel(facts, size=(480, 360)):
    canvas = Image.new("RGB", size, (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((14, 14), "CURRENT 1A - MEASURED FACTS", fill=(245, 245, 245),
              font=font(16))
    lines = [
        ("head radius (shader)", "%.3f deg" % facts["head_radius_deg"]),
        ("visible head glow", "~0.7-0.9 deg"),
        ("trail full width", "%.3f deg" % facts["trail_full_width_deg"]),
        ("head / trail ratio", "%.1fx" % facts["head_to_trail_ratio"]),
        ("head peak / trail peak", "%.1fx" % facts["head_to_trail_peak"]),
        ("tail tip brightness", "%.0f%%" % facts["tail_tip_brightness"]),
        ("tail tip width", "%.0f%%" % facts["tail_tip_width"]),
        ("temporal fade", "none (binary alive)"),
        ("tail end", "hard cut"),
    ]
    y = 50
    for left, right in lines:
        draw.text((16, y), left, fill=(190, 200, 220), font=font(12))
        draw.text((300, y), right, fill=(245, 245, 245), font=font(12))
        y += 26
    draw.text((16, y + 10), "Decision: IMPROVEMENTS REQUIRED",
              fill=(250, 190, 100), font=font(16))
    return canvas


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"current": "", "old": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    current = os.path.abspath(values["current"])
    old = os.path.abspath(values["old"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)

    def img(tag, name):
        root = current if tag == "current" else old
        return Image.open(os.path.join(root, "%s_%s.png" % (tag, name)))

    # Elevations: 2.60.1 then 1A.
    rows = []
    for tag, label in (("2601", "2.60.1"), ("current", "1A")):
        row = []
        for elevation in (1, 5, 40, 85):
            row.append(("%s  %s deg" % (label, elevation),
                        img(tag, "night_elev_%d" % elevation)))
        rows.append(row)
    sheet(rows, os.path.join(out, "board_elevations.png"), (640, 360),
          "PHASE 1B - SHOOTING STARS 2.60.1 vs 1A - elevations 1/5/40/85 deg "
          "- clouds off - frame 18")

    # Lifecycle: key frames; old f10 is absent.
    frames = (10, 13, 18, 25, 32, 33, 34)
    rows = []
    for tag, label in (("2601", "2.60.1"), ("current", "1A")):
        row = []
        for frame in frames:
            note = ("first" if frame == (11 if tag == "2601" else 10)
                    else "after" if frame == 34 else "")
            if tag == "2601" and frame == 10:
                note = "absent"
            if tag == "current" and frame == 10:
                note = "head only"
            row.append(("%s f%02d %s" % (label, frame, note),
                        img(tag, "life_f%02d" % frame)))
        rows.append(row)
    sheet(rows, os.path.join(out, "board_lifecycle.png"), (360, 203),
          "PHASE 1B - LIFECYCLE - frame 10/13/18/25/32/33/34 - start 10, "
          "duration 24 - clouds off")

    # Context: night, twilight, four events.
    rows = []
    for tag, label in (("2601", "2.60.1"), ("current", "1A")):
        rows.append([
            ("%s  night 40 deg" % label, img(tag, "night_40")),
            ("%s  twilight 20 deg" % label, img(tag, "twilight_20")),
            ("%s  four events, frame 20" % label, img(tag, "four_night")),
        ])
    sheet(rows, os.path.join(out, "board_context.png"), (640, 360),
          "PHASE 1B - CONTRAST AND COMPOSITION - night vs twilight - "
          "single vs four events - clouds off")

    # Head detail and target.
    crop_box = (580, 150, 900, 390)
    facts = {
        "head_radius_deg": 0.371,
        "trail_full_width_deg": 0.206,
        "head_to_trail_ratio": 3.6,
        "head_to_trail_peak": 2.0,
        "tail_tip_brightness": 35,
        "tail_tip_width": 25,
    }
    rows = [[
        ("1A head detail (crop 320x240, enlarged)",
         crop(img("current", "night_40"), crop_box, (480, 360))),
        ("2.60.1 head detail (same crop)",
         crop(img("2601", "night_40"), crop_box, (480, 360))),
        ("TARGET reference", target_panel()),
        ("Measured current facts", metrics_panel(facts)),
    ]]
    sheet(rows, os.path.join(out, "board_head.png"), (480, 360),
          "PHASE 1B - HEAD AND TRAIL DETAIL - same camera, crop and exposure")

    # Videos.
    for tag, name in (("current", "lifecycle_current.mp4"),
                      ("2601", "lifecycle_2601.mp4")):
        root = current if tag == "current" else old
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
            "-start_number", "10", "-i",
            os.path.join(root, tag + "_life_f%02d.png"),
            "-frames:v", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            os.path.join(out, name)], check=True)

    params = {
        "current": json.load(open(os.path.join(
            current, "current_params.json"), encoding="utf-8")),
        "old_2601": json.load(open(os.path.join(
            old, "2601_params.json"), encoding="utf-8")),
        "shader_facts": facts,
        "video": {"frames": [10, 33], "count": 24, "fps": 24},
        "notes": {
            "head_radius": "(2 + 2*glow) * thickness at glow=0.8, "
                           "thickness=0.0018 rad",
            "trail_width": "2 * thickness * taper at the head",
            "tail_tip": "tail_fade=0.35, taper=0.25 at the tail gate",
            "temporal": "value is multiplied by the binary alive gate; no "
                        "fade in/out",
            "old_2601": "thin line with a tiny/absent head; no readable glow",
        },
        "decision": "IMPROVEMENTS REQUIRED",
    }
    with open(os.path.join(out, "phase1b_metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump(params, handle, indent=2)
    print("PHASE1B BOARDS", os.path.join(out, "board_elevations.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
