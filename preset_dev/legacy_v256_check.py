"""Open a real v2.56.0 file and verify the current Legacy Disable/Remove.

The .blend is created by ``make_v256_fixture.py`` using the v2.56.0 add-on from
the tag of the same name. This script only reads and then removes the tagged
legacy data; it never saves the user's file.

Run::

    blender -b --factory-startup --python-exit-code 1 \
        --python preset_dev/legacy_v256_check.py
"""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLEND = os.path.join(HERE, "legacy", "v256_fixture.blend")
CHECKS = []


def check(name, condition, detail=""):
    passed = bool(condition)
    CHECKS.append({"name": name, "passed": passed, "detail": detail})
    print("V256 %-48s %s %s" % (name, "OK" if passed else "FAIL", detail))
    return passed


def layer(scene, collection, view_layer=None):
    view_layer = view_layer or scene.view_layers[0]
    return legacy._layer_collection(view_layer, collection)


def op(name, **kwargs):
    with bpy.context.temp_override(scene=bpy.context.scene,
                                   view_layer=bpy.context.view_layer):
        return getattr(bpy.ops.ald, name)(**kwargs)


def main():
    global legacy
    if not os.path.isfile(BLEND):
        print("V256 FAIL missing fixture:", BLEND)
        return 1
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import legacy as module
    legacy = module
    scene = bpy.context.scene

    expected = {"ALD | FX", "ALD | Spatial Clouds", "ALD | Smoke"}
    found = {c.name for c in legacy.legacy_collections(scene)}
    check("the v2.56.0 file exposes the three tagged collections",
          found == expected, str(sorted(found)))
    check("the user collection is not legacy",
          "ALD | User FX" not in found)
    plan = legacy.plan(scene)
    check("the plan includes the v2.56.0 collections",
          set(plan["collections"]) == expected, str(sorted(plan["collections"])))
    user = bpy.data.collections.get("ALD | User FX")
    anchor = bpy.data.objects.get("ALD Sky/FX Anchor")
    ground = bpy.data.objects.get("ALD FX Ground")
    check("the v2.56.0 fixture contains the anchor and ground",
          anchor is not None and ground is not None)

    op("legacy_disable")
    visible = [layer(scene, bpy.data.collections[name]).exclude
               for name in expected]
    check("Disable hides the three collections", all(visible))
    op("legacy_restore")
    visible = [layer(scene, bpy.data.collections[name]).exclude
               for name in expected]
    check("Restore shows the three collections again", not any(visible))

    op("legacy_remove", confirm=True)
    check("Remove deletes the three collections",
          all(bpy.data.collections.get(name) is None for name in expected))
    check("Remove keeps the user collection and its object",
          bpy.data.collections.get("ALD | User FX") is user
          and bpy.data.objects.get("User Prop") is not None)
    check("Remove deletes the non-collection anchor and ground",
          bpy.data.objects.get("ALD Sky/FX Anchor") is None
          and bpy.data.objects.get("ALD FX Ground") is None)

    report = {"file": os.path.relpath(BLEND, ROOT), "checks": CHECKS,
              "passed": sum(1 for item in CHECKS if item["passed"]),
              "total": len(CHECKS)}
    with open(os.path.join(HERE, "legacy", "v256_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    ok = report["passed"] == report["total"]
    print("ALD LEGACY V256 %d/%d %s"
          % (report["passed"], report["total"], "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
