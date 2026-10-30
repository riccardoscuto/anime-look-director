"""Assemble the Clean/Cinematic comparison for both palettes."""

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


def main():
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
        HERE, "sun", "style_compare")
    with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    palettes = data["palettes"]
    cases = data["cases"]
    images = {(case["palette"], case["style"], case["size"]):
              Image.open(os.path.join(folder, case["file"])).convert("RGB")
              for case in cases}
    width, height = next(iter(images.values())).size
    scale = 0.5
    width, height = int(width * scale), int(height * scale)
    columns = 4
    header, foot, title_h = 30, 28, 42
    board = Image.new("RGB", (width * columns + 6 * (columns - 1),
                              title_h + (height + header) * len(palettes) + foot),
                      (18, 18, 18))
    draw = ImageDraw.Draw(board)
    label_font = font(16)
    order = (("CLEAN", 3.0), ("ANIME_CINEMATIC", 3.0),
             ("CLEAN", 10.0), ("ANIME_CINEMATIC", 10.0))
    for row, palette_key in enumerate(palettes):
        for col, (style, size) in enumerate(order):
            image = images[(palette_key, style, size)]
            x = col * (width + 6)
            y = title_h + row * (height + header) + header
            board.paste(image.resize((width, height), Image.LANCZOS), (x, y))
            label = "%s %s, %s deg" % (
                "Cinematic" if style == "ANIME_CINEMATIC" else "Clean",
                palette_key.replace("_", " ").title(), size)
            draw.text((x + 4, y - 22), label, font=label_font,
                      fill=(235, 235, 235))
    draw.text((8, 10), "Phase 3 - Sun Clean vs Anime Cinematic",
              font=font(22), fill=(240, 240, 240))
    draw.text((8, board.height - 22),
              "Two palettes, 3 and 10 deg radius, same camera.",
              font=font(13), fill=(180, 180, 180))
    out = os.path.join(folder, "compare_board.jpg")
    board.save(out, quality=90, optimize=True, progressive=True)
    print(out, board.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
