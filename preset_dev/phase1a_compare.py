"""Build the Phase 1A before/after board and the test animation."""

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


def sheet(rows, path, size, label_size=13, title=None):
    label = font(label_size)
    cells = [[cell(image, text, label, size) for text, image in row]
             for row in rows]
    width = max(len(row) for row in cells) * size[0]
    heights = [max(item.size[1] for item in row) for row in cells]
    title_h = 44 if title else 0
    canvas = Image.new("RGB", (width, title_h + sum(heights)), (12, 12, 14))
    if title:
        ImageDraw.Draw(canvas).text((12, 12), title, fill=(245, 245, 245),
                                    font=font(18))
    y = title_h
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
    values = {"before": "", "after": "", "test": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    before = os.path.abspath(values["before"])
    after = os.path.abspath(values["after"])
    test = os.path.abspath(values["test"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(before, "before_metrics.json"),
              encoding="utf-8") as handle:
        b = json.load(handle)
    with open(os.path.join(after, "after_metrics.json"),
              encoding="utf-8") as handle:
        a = json.load(handle)

    def label(report, key):
        item = report["elevations"][key]
        return "%s deg  %d px  max %.2f" % (
            key.rstrip("0").rstrip("."), item["pixels"], item["max"])

    rows = []
    for report, tag, root in ((b, "BEFORE", before), (a, "AFTER", after)):
        row = []
        for key in ("1.0", "5.0", "40.0", "85.0"):
            row.append(("%s  %s" % (tag, label(report, key)),
                        Image.open(os.path.join(
                            root, report["elevations"][key]["on"]))))
        rows.append(row)
    size = sheet(
        rows, os.path.join(out, "board.png"), (640, 360), 13,
        "PHASE 1A - SHOOTING STAR TRAJECTORIES - clouds off - frame 18 - "
        "camera aimed at the event start")
    print("BOARD", size)

    rows = []
    for report, tag, root in ((b, "BEFORE", before), (a, "AFTER", after)):
        item = report["horizon"]
        rows.append([("%s  horizon crossing  %d px  max %.2f" % (
            tag, item["pixels"], item["max"]),
            Image.open(os.path.join(root, item["on"])))])
    sheet(rows, os.path.join(out, "board_horizon.png"), (640, 360), 13,
          "PHASE 1A - HORIZON CROSSING - elevation 3 deg, direction -20, "
          "frame 33")

    frames = [os.path.join(test, "video_f%02d.png" % frame)
              for frame in range(10, 35)]
    if all(os.path.exists(path) for path in frames):
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
            "-start_number", "10", "-i",
            os.path.join(test, "video_f%02d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            os.path.join(out, "lifecycle.mp4")], check=True)
    for name in ("metrics.json",):
        source = os.path.join(test, name)
        if os.path.exists(source):
            with open(source, encoding="utf-8") as handle:
                data = json.load(handle)
            for item in data.get("renders", {}).values():
                for key in ("on", "off"):
                    if key in item:
                        item[key] = os.path.basename(item[key])
            data["video"] = [os.path.basename(path)
                             for path in data.get("video", [])]
            with open(os.path.join(out, name), "w",
                      encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
    print("PHASE1A BOARD ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
