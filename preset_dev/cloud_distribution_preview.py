"""Export toned PNG previews of the prototype panorama EXRs."""

import os
import sys

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
values = {"out": "", "files": ""}
for index, item in enumerate(argv):
    if item.startswith("--") and index + 1 < len(argv):
        values[item[2:].replace("-", "_")] = argv[index + 1]
out = values["out"]
os.makedirs(out, exist_ok=True)
for path in values["files"].split(","):
    image = bpy.data.images.load(path)
    image.colorspace_settings.name = "Non-Color"
    image.scale(1024, 512)
    image.file_format = "PNG"
    name = os.path.splitext(os.path.basename(path))[0] + ".png"
    image.filepath_raw = os.path.join(out, name)
    image.save()
    print("PREVIEW", name, tuple(image.size), os.path.getsize(
        os.path.join(out, name)))
    bpy.data.images.remove(image)
