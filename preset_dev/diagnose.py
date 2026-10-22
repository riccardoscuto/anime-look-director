"""The diagnostic report of the FX.

The report says why an effect is not visible: a missing attribute, an event
out of time, out of camera, disabled, not emissive or hidden.

Usage:
    blender -b --factory-startup --python preset_dev/diagnose.py -- \
        [--kind meteor|firework|user] [--out FILE]

It never saves the .blend of the user: the fixture is built in the current
session and the report is written as JSON.
"""

import json
import os
import sys

import bpy


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    kind = "meteor"
    out = None
    if "--kind" in argv:
        kind = argv[argv.index("--kind") + 1]
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return kind, out


def main():
    import addon_utils

    addon_utils.enable("anime_look_director", default_set=True)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fixtures
    from anime_look_director import diagnostics

    kind, out = parse_args()
    scene = bpy.context.scene
    fixtures.build(kind, scene)
    report = diagnostics.report(scene)
    print("ALD DIAGNOSTICS")
    print(diagnostics.format_report(scene))
    print("ALD DIAGNOSTICS SUMMARY", diagnostics.summary(scene))
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print("ALD DIAGNOSTICS FILE", out)


if __name__ == "__main__":
    main()
