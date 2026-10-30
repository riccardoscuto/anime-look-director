"""Assemble the Phase 1 Moon style board from moon_styles.py renders."""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = {
    "ANIME_CLEAN": "Anime Clean",
    "ANIME_PAINTERLY": "Anime Painterly",
    "DETAILED_MOON": "Detailed Moon",
    "ETHEREAL_MOON": "Ethereal Moon",
}


def main():
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
        HERE, "moon", "styles")
    with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    styles, sizes = data["styles"], data["sizes"]
    images = {}
    for case in data["cases"]:
        images[(case["style"], case["size"])] = Image.open(
            os.path.join(folder, case["file"])).convert("RGB")
    width, height = images[(styles[0], sizes[0])].size
    title_h, header, foot = 48, 34, 30
    board = Image.new("RGB", (width * len(styles) + 8 * (len(styles) - 1),
                              title_h + (height + header) * len(sizes) + foot),
                      (18, 18, 18))
    try:
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
        label_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
        small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    except OSError:
        title_font = label_font = small = ImageFont.load_default()
    draw = ImageDraw.Draw(board)
    for column, style in enumerate(styles):
        x = column * (width + 8)
        draw.text((x + 6, 14), LABELS[style], font=title_font,
                  fill=(240, 240, 240))
        for row, size in enumerate(sizes):
            y = title_h + row * (height + header) + header
            board.paste(images[(style, size)], (x, y))
            draw.text((x + 8, y - 24), "Moon %s deg" % size, font=label_font,
                      fill=(225, 225, 225))
    draw.text((8, board.height - 22),
              "Phase 1 - Moonlit Night, clouds/stars/Sun off, 135 mm, AgX. "
              "Same sky and camera for every style.",
              font=small, fill=(180, 180, 180))
    out = os.path.join(folder, "moon_styles.jpg")
    board.save(out, quality=90, optimize=True, progressive=True)
    print(out, board.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
