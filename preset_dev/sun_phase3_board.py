"""Assemble the Phase 3 Sun size, style and horizon boards."""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))


def font(size):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def row(items, folder, out, title, footer):
    images = [Image.open(os.path.join(folder, item["path"])).convert("RGB")
              for item in items]
    width, height = images[0].size
    scale = 0.5
    width, height = int(width * scale), int(height * scale)
    header, foot, title_h = 30, 28, 42
    board = Image.new("RGB", (width * len(items) + 6 * (len(items) - 1),
                              title_h + height + header + foot), (18, 18, 18))
    draw = ImageDraw.Draw(board)
    label_font = font(16)
    for index, (item, image) in enumerate(zip(items, images)):
        x = index * (width + 6)
        y = title_h + header
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
        HERE, "sun", "phase3")
    with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    row([{"label": "Radius %s deg" % item["size"],
          "path": "sizes/" + item["file"]} for item in data["sizes"]],
        folder, os.path.join(folder, "sizes_board.jpg"),
        "Phase 3 - Sun size (angular radius)",
        "GOLDEN_HOUR, elevation 25 deg, Sun Clean, 24 mm, AgX.")
    row([{"label": "%s, %s deg" % (
              "Cinematic" if item["style"] == "ANIME_CINEMATIC" else "Clean",
              item["size"]),
          "path": "styles/" + item["file"]} for item in data["styles"]],
        folder, os.path.join(folder, "styles_board.jpg"),
        "Phase 3 - Sun Clean vs Anime Cinematic",
        "3 and 10 deg radius, same sky and camera.")
    row([{"label": "Elevation %s deg" % item["elevation"],
          "path": "horizon/" + item["file"]} for item in data["horizon"]],
        folder, os.path.join(folder, "horizon_board.jpg"),
        "Phase 3 - horizon fade",
        "4 deg radius, Clean, 35 mm camera at the horizon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
