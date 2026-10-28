"""Build the shooting-star audit boards and the test video."""

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
    values = {"audit": "", "out": ""}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    audit = os.path.abspath(values["audit"])
    out = os.path.abspath(values["out"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(audit, "audit.json"), encoding="utf-8") as handle:
        report = json.load(handle)
    checks = report["checks"]
    lifecycle = checks["lifecycle"]

    def lifecycle_label(frame):
        item = lifecycle[str(frame)]
        return "f%02d  star %d px  max %.2f" % (
            frame, item["pixels"], item["max"])

    rows = [[
        (lifecycle_label(8), Image.open(os.path.join(
            audit, "lifecycle_f08.png"))),
        (lifecycle_label(10), Image.open(os.path.join(
            audit, "lifecycle_f10.png"))),
        (lifecycle_label(11), Image.open(os.path.join(
            audit, "lifecycle_f11.png"))),
    ], [
        (lifecycle_label(18), Image.open(os.path.join(
            audit, "lifecycle_f18.png"))),
        (lifecycle_label(33), Image.open(os.path.join(
            audit, "lifecycle_f33.png"))),
        (lifecycle_label(34), Image.open(os.path.join(
            audit, "lifecycle_f34.png"))),
    ]]
    sheet(rows, os.path.join(out, "contact_lifecycle.png"), (640, 360), 14)

    def simple(key):
        item = checks[key]
        if "star" in item:
            item = item["star"]
        return "star %d px  max %.2f" % (item["pixels"], item["max"])

    rows = [[
        ("Add from a horizon camera: " + simple("add"),
         Image.open(os.path.join(audit, "add_after.png"))),
        ("elevation 5 deg: " + simple("horizon_5"),
         Image.open(os.path.join(audit, "horizon_elev5.png"))),
    ], [
        ("elevation 1 deg (clamp): " + simple("horizon_1"),
         Image.open(os.path.join(audit, "horizon_elev1.png"))),
        ("elevation 85 deg: " + simple("zenith_85"),
         Image.open(os.path.join(audit, "zenith_elev85.png"))),
    ]]
    sheet(rows, os.path.join(out, "contact_position.png"), (640, 360), 14)

    rows = [[
        ("one event (f18)", Image.open(os.path.join(
            audit, "lifecycle_f18.png"))),
        ("four events (f26)", Image.open(os.path.join(
            audit, "multiple_4.png"))),
        ("three events after remove (f26)", Image.open(os.path.join(
            audit, "multiple_3_after_remove.png"))),
    ]]
    sheet(rows, os.path.join(out, "contact_multiple.png"), (640, 360), 14)

    rows = [[
        ("Preview: working camera (75 deg)", Image.open(os.path.join(
            audit, "preview_before_view.png"))),
        ("Preview: camera moved by the operator", Image.open(os.path.join(
            audit, "preview_after_view.png"))),
        ("Persistence: before save (f26)", Image.open(os.path.join(
            audit, "persist_before.png"))),
    ], [
        ("Persistence: after reopen (identical)", Image.open(os.path.join(
            audit, "persist_after.png"))),
        ("Original scene after the copy edit", Image.open(os.path.join(
            audit, "persist_original.png"))),
        ("Duplicated scene, event edited", Image.open(os.path.join(
            audit, "persist_copy.png"))),
    ]]
    sheet(rows, os.path.join(out, "contact_preview_persistence.png"),
          (640, 360), 13)

    frames = [os.path.join(audit, "video_f%02d.png" % frame)
              for frame in range(10, 35)]
    if all(os.path.exists(path) for path in frames):
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
            "-start_number", "10",
            "-i", os.path.join(audit, "video_f%02d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            os.path.join(out, "lifecycle.mp4")], check=True)
    with open(os.path.join(out, "metrics.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("AUDIT SHEETS ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
