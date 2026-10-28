"""Reopen the prototype .blend and verify the packed mask survives.

Renders one frame from the saved file; the compare step checks it against the
original render.
"""

import os
import sys

import bpy

VIEW = ((0.0, -12.0, 3.0), (1.75, 0.0, 0.45))


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"blend": "", "out": "", "threshold": "0.6709"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    bpy.ops.wm.open_mainfile(filepath=values["blend"])
    image = bpy.data.images.get("ALD | Cloud Distribution")
    print("RELOAD image", image.name if image else None,
          "size", tuple(image.size) if image else None,
          "packed", bool(image.packed_file) if image else None,
          "packed_bytes", image.packed_file.size if image else None,
          "filepath", image.filepath if image else None,
          "float", image.is_float if image else None,
          "colorspace", image.colorspace_settings.name if image else None)
    scene = bpy.context.scene
    data = bpy.data.cameras.new("Reload Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("Reload Camera", data)
    scene.collection.objects.link(camera)
    camera.location = VIEW[0]
    camera.rotation_euler = VIEW[1]
    scene.camera = camera
    world = scene.world
    for item in world.node_tree.nodes:
        if item.name == "ALD Prototype Threshold":
            item.outputs[0].default_value = float(values["threshold"])
    scene.render.filepath = os.path.join(values["out"],
                                         "reload_s03_main_a030_1280x720.png")
    bpy.ops.render.render(write_still=True)
    print("RELOAD rendered", scene.render.filepath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
