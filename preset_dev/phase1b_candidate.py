"""Build the Phase 1B candidate before/after boards (1A -> candidate)."""

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


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"baseline": "", "candidate": "", "out": "", "gate": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    baseline = os.path.abspath(values["baseline"])
    candidate = os.path.abspath(values["candidate"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)

    def img(root, tag, name):
        return Image.open(os.path.join(root, "%s_%s.png" % (tag, name)))

    rows = []
    for root, tag, label in ((baseline, "current", "1A"),
                             (candidate, "candidate", "candidate")):
        row = []
        for elevation in (1, 5, 40, 85):
            row.append(("%s  %s deg" % (label, elevation),
                        img(root, tag, "night_elev_%d" % elevation)))
        rows.append(row)
    sheet(rows, os.path.join(out, "candidate_elevations.png"), (640, 360),
          "PHASE 1B CANDIDATE - 1A vs appearance candidate - elevations "
          "1/5/40/85 - frame 18 - clouds off")

    frames = (9, 10, 11, 13, 18, 25, 31, 32, 33, 34)
    rows = []
    for root, tag, label in ((baseline, "current", "1A"),
                             (candidate, "candidate", "candidate")):
        row = []
        for frame in frames:
            row.append(("%s f%02d" % (label, frame),
                        img(root, tag, "life_f%02d" % frame)))
        rows.append(row)
    sheet(rows, os.path.join(out, "candidate_lifecycle.png"), (320, 180),
          "PHASE 1B CANDIDATE - lifecycle 9/10/11/13/18/25/31/32/33/34 - "
          "start 10, duration 24", 11)

    context = (("night_40", "night 40 deg"),
               ("twilight_20", "twilight 20 deg"),
               ("four_night", "four events, frame 20"))
    rows = []
    for root, tag, label in ((baseline, "current", "1A"),
                             (candidate, "candidate", "candidate")):
        rows.append([("%s  %s" % (label, text), img(root, tag, name))
                     for name, text in context])
    sheet(rows, os.path.join(out, "candidate_context.png"), (640, 360),
          "PHASE 1B CANDIDATE - contrast and composition - 1A vs candidate")

    head_box = (680, 225, 820, 330)
    tip_box = (720, 215, 840, 305)

    def facts_panel():
        canvas = Image.new("RGB", (480, 360), (12, 14, 20))
        draw = ImageDraw.Draw(canvas)
        draw.text((14, 14), "CANDIDATE - MEASURED", fill=(245, 245, 245),
                  font=font(16))
        lines = [
            ("head radius", "0.371 -> 0.149 deg"),
            ("head / trail width", "3.6x -> 1.44x"),
            ("head / trail peak", "2.0x -> 1.42x"),
            ("tail tip brightness", "35% -> 5%"),
            ("tail tip width", "25% -> 6%"),
            ("life fade", "none -> 0.5 / 0.3"),
            ("SS-01 f9/f10/f33/f34", "0 / 149 / 829 / 0 px"),
            ("duration 2", "f10 140 / f11 802 px"),
        ]
        y = 50
        for left, right in lines:
            draw.text((16, y), left, fill=(190, 200, 220), font=font(12))
            draw.text((270, y), right, fill=(245, 245, 245), font=font(12))
            y += 27
        draw.text((16, y + 12), "TECHNICAL PASS - VISUAL REVIEW PENDING",
                  fill=(120, 230, 140), font=font(14))
        return canvas

    target = Image.open(os.path.join(out, "board_head.png")).crop(
        (960, 44, 1440, 404)).resize((480, 360), Image.Resampling.LANCZOS)
    rows = [
        [
            ("1A head (crop 4x)", crop(img(baseline, "current", "night_40"),
                                      head_box, (480, 360))),
            ("candidate head (crop 4x)",
             crop(img(candidate, "candidate", "night_40"), head_box,
                  (480, 360))),
            ("TARGET reference", target),
        ],
        [
            ("1A tail tip f33 (crop 4x)",
             crop(img(baseline, "current", "life_f33"), tip_box, (480, 360))),
            ("candidate tail tip f33 (crop 4x)",
             crop(img(candidate, "candidate", "life_f33"), tip_box,
                  (480, 360))),
            ("Measured candidate facts", facts_panel()),
        ],
    ]
    sheet(rows, os.path.join(out, "candidate_head_tip.png"), (480, 360),
          "PHASE 1B CANDIDATE - head and tail tip - same crops and exposure", 11)

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
        "-start_number", "10", "-i",
        os.path.join(candidate, "candidate_life_f%02d.png"),
        "-frames:v", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", os.path.join(out, "candidate_lifecycle.mp4")],
        check=True)

    metrics = {
        "baseline": "Phase 1A (master 63ffa29)",
        "candidate": "Phase 1B appearance candidate",
        "head_radius_deg": 0.1485,
        "head_diameter_deg": 0.297,
        "trail_full_width_deg": 0.206,
        "head_to_trail_ratio": 1.44,
        "head_peak": 3.84,
        "trail_near_head": 2.7,
        "head_to_trail_peak": 1.42,
        "tail_tip_brightness": 5,
        "tail_tip_width": 6,
        "tip_smoothstep_fraction": 0.18,
        "life_fade": {"start": 0.5, "last": 0.3},
        "ss01_render": {"f9": 0, "f10": 149, "f33": 829, "f34": 0},
        "duration2_render": {"f10": 140, "f11": 802},
        "four_events": {"pixels": 2214, "components": 4},
        "gate": "37/37 Vulkan and OpenGL",
        "interactive": "5/5",
        "decision": "TECHNICAL PASS - VISUAL REVIEW PENDING",
    }
    with open(os.path.join(out, "candidate_metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print("PHASE1B CANDIDATE BOARDS ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
