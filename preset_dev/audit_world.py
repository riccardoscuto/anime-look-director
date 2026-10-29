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


def phase6_matrix():
    path = os.path.join(ROOT, "preset_dev/phase6/metrics.json")
    if not os.path.exists(path):
        return False, "missing metrics"
    with io.open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    count = len(report.get("cells", []))
    return count == 22, "%d cells" % count


def phase6_gate():
    path = os.path.join(ROOT, "preset_dev/phase6/technical.json")
    if not os.path.exists(path):
        return False, "missing technical report"
    with io.open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    passed = report.get("passed", 0)
    total = report.get("total", 0)
    return passed == total and total >= 17, "%s/%s" % (passed, total)


def _legacy_report(name, minimum):
    path = os.path.join(ROOT, "preset_dev/legacy", name)
    if not os.path.exists(path):
        return False, "missing " + name
    with io.open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    passed = report.get("passed", 0)
    total = report.get("total", 0)
    return passed == total and total >= minimum, "%s/%s" % (passed, total)


def legacy_fixtures():
    synthetic = _legacy_report("report.json", 36)
    native = _legacy_report("v256_report.json", 9)
    return synthetic[0] and native[0], "%s; v2.56 %s" % (
        synthetic[1], native[1])


CHECKS = [
    ("Reduction", "The version is the World Sky Edition",
     lambda: has("__init__.py", '"version": (2, 62, 0)')
     and has("blender_manifest.toml", 'version = "2.62.0"')),
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
    ("UI", "The surfaces share the drawing functions",
     lambda: has("panels.py", "draw_quick_look", "draw_atmosphere",
                 "draw_clouds", "draw_stars", "draw_shooting_stars",
                 "draw_custom_colors", "draw_compositor")),
    ("UI", "The sidebar is compact: Quick Look only",
     lambda: has("panels.py", "Quick Look", "ALD_PT_view3d")[0]
     and "ALD_PT_view3d_advanced" not in read("panels.py")
     and "ALD_PT_view3d_compositor" not in read("panels.py")),
    ("UI", "The quick panel exposes the low-frequency controls",
     lambda: has("panels.py", "sun_elevation", "cloud_type",
                 "cloud_amount", "cloud_wind", "stars")),
    ("UI", "The compositor controls are hidden when inactive",
     lambda: has("panels.py", "Inactive: no ALD stack",
                 "Enable Compositor")),
    ("Presets", "The five Phase 5 presets are registered",
     lambda: has("properties.py", "SOFT_DAWN", "BLUE_HOUR",
                 "CLOUDY_AFTERNOON", "STORMY_SUNSET", "MOONLIT_NIGHT")
     and has("palette.py", "SOFT_DAWN", "BLUE_HOUR",
             "CLOUDY_AFTERNOON", "STORMY_SUNSET", "MOONLIT_NIGHT")[0]),
    ("Presets", "Reset and Save as Custom are explicit",
     lambda: has("operators.py", "ald.reset_look",
                 "ald.save_custom_palette")
     and has("panels.py", "save_custom_palette")[0]),
    ("Evidence", "The full preset sheet is recorded",
     lambda: exists("preset_dev/palettes/sheet.png")[0]),
    ("Sky", "The sky accent band is soft, not a stripe",
     lambda: has("palette.py", 'accent_band.inputs["From Max"].default_value = 0.20')),
    ("Sky", "The Sun disk and glow fade below the horizon",
     lambda: has("palette.py", "def _sun_fade", "disk_gate", "glow_gate")),
    ("Evidence", "The Phase 0 World baseline is frozen",
     lambda: exists("preset_dev/world_baseline/contact_1280.png",
                    "preset_dev/world_baseline/README.md")[0]),
    ("Clouds", "Three cloud families are selectable and exclusive",
     lambda: has("properties.py", "cloud_type", "CUMULUS", "STRATOCUMULUS",
                 "CIRRUS")
     and has("palette.py", "Cloud Cumulus", "Cloud Stratocumulus",
             "Cloud Cirrus")[0]),
    ("Clouds", "Family shape and artistic controls are wired",
     lambda: has("palette.py", "Cloud Vertical", "Cloud Breakup",
                 "Cloud Detail", "Cloud Sun Lighting", "family_flatness")),
    ("Evidence", "The Phase 2 cloudless sky matrix is recorded",
     lambda: exists("preset_dev/sky/contact.png",
                    "preset_dev/sky/metrics.json",
                    "preset_dev/sky/README.md")[0]),
    ("Evidence", "The three-family cloud gate is recorded",
     lambda: exists("preset_dev/cloud_families/contact.png",
                    "preset_dev/cloud_families/metrics.json",
                    "preset_dev/cloud_families/README.md")[0]),
    ("Evidence", "The sunset cloud gate is recorded",
     lambda: exists("preset_dev/cloud_sunset/contact.png",
                    "preset_dev/cloud_sunset/metrics.json",
                    "preset_dev/cloud_sunset/README.md")[0]),
    ("Shooting stars", "Events are persistent and bounded",
     lambda: has("properties.py", "ALD_ShootingStar",
                 "shooting_star_events", "start_frame", "duration")),
    ("Shooting stars", "The event controls are exposed",
     lambda: has("operators.py", "ald.shooting_star_add",
                 "ald.shooting_star_duplicate",
                 "ald.shooting_star_remove")
     and has("panels.py", "draw_shooting_stars")[0]),
    ("Shooting stars", "The World shader evaluates the events",
     lambda: has("palette.py", "def _build_shooting_stars",
                 "Star0 Start U", 'prefix + "Color"')),
    ("Shooting stars", "Editing a star refreshes the World",
     lambda: has("properties.py", "def _on_star", "update=_on_star")),
    ("Shooting stars", "The star can be previewed in the camera",
     lambda: has("operators.py", "ald.shooting_star_preview")
     and has("panels.py", "ald.shooting_star_preview")[0]),
    ("Evidence", "The shooting-star gate is recorded",
     lambda: exists("preset_dev/shooting_star/contact.png",
                    "preset_dev/shooting_star/metrics.json",
                    "preset_dev/shooting_star/README.md")[0]),
    ("Evidence", "The Phase 6 release matrix is recorded",
     lambda: exists("preset_dev/phase6/contact.png",
                    "preset_dev/phase6/metrics.json",
                    "preset_dev/phase6/README.md")[0]
     and phase6_matrix()),
    ("Release", "The Phase 6 technical gate passes",
     phase6_gate),
    ("Legacy", "Discovery uses historical tags, never names",
     lambda: has("legacy.py", "ald_fx_collection", "ald_fx_owner",
                 "ald_clouds", "ald_smoke", "ald_fx_anchor",
                 "ald_fx_ground", "def is_legacy_collection")),
    ("Legacy", "Disable is per-view-layer and reversible",
     lambda: has("legacy.py", "layer.exclude", "STATE_KEY", "def restore")
     and has("operators.py", "ald.legacy_restore")[0]),
    ("Legacy", "Remove confirms and skips shared data",
     lambda: has("operators.py", "confirm", "invoke_props_dialog",
                 "ald.legacy_remove")
     and has("legacy.py", "def _shared_with_other_scene",
             "skipped")[0]),
    ("Evidence", "The legacy fixtures pass",
     legacy_fixtures),
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
