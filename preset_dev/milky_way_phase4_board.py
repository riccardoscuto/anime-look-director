"""Assemble the Phase 4 Milky Way boards."""

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
        HERE, "milky_way", "phase4")
    with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    cases = data["cases"]
    columns = 4
    rows = (len(cases) + columns - 1) // columns
    images = [Image.open(os.path.join(folder, item["file"])).convert("RGB")
              for item in cases]
    width, height = images[0].size
    scale = 0.5
    width, height = int(width * scale), int(height * scale)
    header, foot, title_h = 30, 28, 42
    board = Image.new("RGB", (width * columns + 6 * (columns - 1),
                              title_h + (height + header) * rows + foot),
                      (18, 18, 18))
    draw = ImageDraw.Draw(board)
    label_font = font(16)
    for index, (case, image) in enumerate(zip(cases, images)):
        col, row = index % columns, index // columns
        x = col * (width + 6)
        y = title_h + row * (height + header) + header
        board.paste(image.resize((width, height), Image.LANCZOS), (x, y))
        draw.text((x + 4, y - 22), case["label"], font=label_font,
                  fill=(235, 235, 235))
    draw.text((8, 10), "Phase 4 - Milky Way 2.0", font=font(22),
              fill=(240, 240, 240))
    draw.text((8, board.height - 22),
              "16 mm panorama, elevation 35, stars only; cloud case uses "
              "cloud amount 0.55.",
              font=font(13), fill=(180, 180, 180))
    out = os.path.join(folder, "board.jpg")
    board.save(out, quality=90, optimize=True, progressive=True)
    print(out, board.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
