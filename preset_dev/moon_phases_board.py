"""Assemble the Phase 2 phase boards from moon_phases.py renders."""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = {
    "NEW": "New", "WAXING_CRESCENT": "Waxing Crescent",
    "FIRST_QUARTER": "First Quarter", "WAXING_GIBBOUS": "Waxing Gibbous",
    "FULL": "Full", "WANING_GIBBOUS": "Waning Gibbous",
    "LAST_QUARTER": "Last Quarter", "WANING_CRESCENT": "Waning Crescent",
}


def font(size):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def grid(items, columns, out, title, footer, scale=0.62):
    images = [Image.open(item["path"]).convert("RGB") for item in items]
    width, height = images[0].size
    width, height = int(width * scale), int(height * scale)
    rows = (len(items) + columns - 1) // columns
    header, foot, title_h = 30, 28, 42
    board = Image.new("RGB", (width * columns + 6 * (columns - 1),
                              title_h + (height + header) * rows + foot),
                      (18, 18, 18))
    draw = ImageDraw.Draw(board)
    label_font = font(16)
    for index, (item, image) in enumerate(zip(items, images)):
        col, row = index % columns, index // columns
        x = col * (width + 6)
        y = title_h + row * (height + header) + header
        board.paste(image.resize((width, height), Image.LANCZOS), (x, y))
        draw.text((x + 4, y - 22), item["label"], font=label_font,
                  fill=(235, 235, 235))
    draw.text((8, 10), title, font=font(22), fill=(240, 240, 240))
    draw.text((8, board.height - 22), footer, font=font(13),
              fill=(180, 180, 180))
    board.save(out, quality=90, optimize=True, progressive=True)
    print(out, board.size)


def main():
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
        HERE, "moon", "phases")
    with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    named = [{"label": LABELS[item["name"]],
              "path": os.path.join(folder, "named", item["file"])}
             for item in data["named"]]
    grid(named, 4, os.path.join(folder, "named_board.jpg"),
         "Phase 2 - eight lunar phases (Detailed Moon, 4 deg)",
         "Moonlit Night, clouds/stars/Sun off, 135 mm, AgX. Same sky and camera.",
         scale=0.62)
    sweep = [{"label": "Phase %.3f" % item["phase"],
              "path": os.path.join(folder, item["file"])}
             for item in data["sweep"]]
    grid(sweep, 3, os.path.join(folder, "sweep_board.jpg"),
         "Phase 2 - continuous illumination 0.0 -> 1.0",
         "Manual mode, waxing; 4 deg, Detailed Moon.",
         scale=0.55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
