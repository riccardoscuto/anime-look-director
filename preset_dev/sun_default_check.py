"""Compare the current Sun defaults with a real 2.63.0 render.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/sun_default_check.py -- <legacy.blend> <legacy.png>
"""

import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402

OUT = os.path.join(HERE, "sun", "default_check")


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(argv) < 2:
        raise SystemExit("legacy .blend and .png required")
    legacy, legacy_png = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=legacy)
    lookdev.enable_addon()
    scene = bpy.context.scene
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    before = {"build": group.get("ald_build") if group else None}
    bpy.ops.ald.apply_palette()
    group = bpy.data.node_groups.get(palette.GRADIENT_GROUP)
    after = {
        "build": group.get("ald_build") if group else None,
        "sockets": sorted(item.name for item in group.interface.items_tree
                          if item.item_type == "SOCKET"
                          and item.in_out == "INPUT") if group else [],
    }
    scene.render.filepath = os.path.join(OUT, "current_sun.png")
    bpy.ops.render.render(write_still=True)
    delta = float(np.abs(lookdev.load_rgba(legacy_png)
                         - lookdev.load_rgba(scene.render.filepath)).max())
    checks = {
        "legacy_build": before["build"],
        "current_build": after["build"],
        "has_sun_tint": "Sun Disk Tint" in after["sockets"],
        "max_pixel_delta": round(delta, 5),
        "passed": (before["build"] == 35
                   and after["build"] == palette.GRADIENT_BUILD
                   and "Sun Disk Tint" in after["sockets"]
                   and delta < 0.01),
    }
    with open(os.path.join(OUT, "default_check.json"), "w",
              encoding="utf-8") as fh:
        json.dump(checks, fh, indent=2)
    print("SUN DEFAULT CHECK", json.dumps(checks, sort_keys=True))
    print("SUN DEFAULT CHECK", "PASS" if checks["passed"] else "FAIL")
    return 0 if checks["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
