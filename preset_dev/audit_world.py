"""World Sky Edition source audit.

Checks the reduction of the operational path and the World-only features.

Run::

    python preset_dev/audit_world.py
"""

import io
import json
import os
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(path):
    with io.open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
        return f.read()


def has(path, *needles):
    text = read(path)
    missing = [item for item in needles if item not in text]
    return not missing, ("missing: " + ", ".join(missing)) if missing else ""


def exists(*paths):
    missing = [path for path in paths
               if not os.path.exists(os.path.join(ROOT, path))]
    return not missing, ("missing: " + ", ".join(missing)) if missing else ""


CHECKS = [
    ("Reduction", "The version is the World Sky Edition",
     lambda: has("__init__.py", '"version": (2, 57, 0)')
     and has("blender_manifest.toml", 'version = "2.57.0"')),
    ("Reduction", "The FX and spatial modules are gone",
     lambda: not any(os.path.exists(os.path.join(ROOT, name))
                     for name in ("fx.py", "fx_nodes.py", "clouds.py",
                                  "smoke.py", "diagnostics.py"))),
    ("Reduction", "Registration has no FX/clouds/smoke modules",
     lambda: not any(name in read("__init__.py")
                     for name in ("fx", "clouds", "smoke"))),
    ("Reduction", "Operators no longer create FX, clouds or smoke",
     lambda: not any(name in read("operators.py")
                     for name in ("ald.fx", "ald.clouds", "ald.smoke",
                                  "FX Pass", "Render FX"))),
    ("Reduction", "Panels no longer draw FX or spatial clouds",
     lambda: not any(name in read("panels.py")
                     for name in ("draw_fx", "FX Particles",
                                  "Spatial Clouds", "Atmospheric Smoke"))),
    ("Reduction", "The compositor has no Cryptomatte or FX pass",
     lambda: not any(name in read("compositor.py")
                     for name in ("Cryptomatte", "FX Pass", "fx_pass")),
     ),
    ("World", "The four-zone World group is present",
     lambda: has("palette.py", "Ground Color", "Horizon Color",
                 "Mid Sky Color", "Sky Color")),
    ("World", "The Sun controls are wired",
     lambda: has("palette.py", "def apply_sun_angles",
                 "SUN_OWNER_TAG")),
    ("World", "The World clouds are a shader feature",
     lambda: has("palette.py", "Cloud Amount", "Cloud Shadow",
                 "Cloud Mid", "Cloud Light")),
    ("World", "The World stars and Milky Way remain",
     lambda: has("palette.py", "Star Amount", "Star Density",
                 "Milky Way")),
    ("World", "Horizon offset and softness are controls",
     lambda: has("palette.py", "Horizon Offset", "Softness")),
    ("Persistent", "The scene identity is independent of FX",
     lambda: exists("identity.py")[0]
     and has("palette.py", "identity.scene_id")[0]),
    ("Persistent", "The snapshot restores the World and the passes",
     lambda: has("snapshot.py", "def restore",
                 "use_pass_cryptomatte_material",
                 "use_pass_object_index")),
    ("Persistent", "A duplicated scene gets its own World",
     lambda: has("ownership.py", "world.copy", "identity")),
    ("Compatibility", "Legacy ALD data has explicit disable/remove",
     lambda: has("operators.py", "ald.legacy_disable",
                 "ald.legacy_remove")
     and has("panels.py", "draw_legacy")[0]),
    ("Compatibility", "Old files are not cleaned automatically",
     lambda: has("panels.py", "never cleaned automatically")),
    ("UI", "The two surfaces share the drawing functions",
     lambda: has("panels.py", "draw_world", "draw_compositor",
                 "ALD_PT_view3d_world", "ALD_PT_view3d_compositor")),
    ("UI", "The quick panel exposes Apply and the compositor state",
     lambda: has("panels.py", "ald.apply_palette",
                 "Compositor optional")),
    ("Evidence", "The Phase 0 World baseline is frozen",
     lambda: exists("preset_dev/world_baseline/contact_1280.png",
                    "preset_dev/world_baseline/README.md")[0]),
    ("Evidence", "The World gate and lifecycle fixture are runnable",
     lambda: exists("preset_dev/verify.py",
                    "preset_dev/world_fixture.py")[0]),
]


def main():
    results = []
    for category, label, predicate in CHECKS:
        outcome = predicate()
        if isinstance(outcome, tuple):
            passed, detail = outcome
        else:
            passed, detail = bool(outcome), ""
        results.append({"category": category, "label": label,
                        "passed": bool(passed), "detail": detail})
        print("AUDIT %-12s %-55s %s %s"
              % (category, label, "OK" if passed else "FAIL", detail))
    passed = sum(1 for item in results if item["passed"])
    report = {"passed": passed, "total": len(results), "results": results}
    with io.open(os.path.join(HERE, "audit_world.json"), "w",
                 encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("ALD WORLD AUDIT %d/%d %s"
          % (passed, len(results), "OK" if passed == len(results) else "FAIL"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
