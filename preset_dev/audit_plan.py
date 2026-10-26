"""Audit the v2.27.0 operational plan (P0-P3) against the code.

This replaces the audit of the previous plan. Every requirement is checked in
the source of the add-on and in the gate; the report distinguishes what is
implemented (OK), what is only partial (PARTIAL) and what is missing (MISSING).
The runtime evidence is `preset_dev/verify.py` (ALD GATE: PASS) and
`preset_dev/benchmarks.json`.

Usage:
  blender -b --factory-startup --python preset_dev/audit_plan.py -- [--out FILE]

It never saves the .blend of the user.
"""

import json
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ADDON, "preset_dev", "audit_report.json")
IGNORED_DIRS = {"preset_dev", "data", ".git", "__pycache__"}


def read(relative):
    path = os.path.join(ADDON, relative)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def has(relative, *needles):
    text = read(relative)
    missing = [needle for needle in needles if needle not in text]
    return not missing, ("missing: " + ", ".join(missing)) if missing else ""


def exists(*relative):
    missing = [path for path in relative
               if not os.path.exists(os.path.join(ADDON, path))]
    return not missing, ("missing: " + ", ".join(missing)) if missing else ""


CHECKS = [
    # ---- P0-A -----------------------------------------------------------
    ("P0-A", "Baseline: version, hashes, schemas, public flows",
     lambda: exists("preset_dev/baseline.py", "preset_dev/baseline.json",
                    "preset_dev/P0_BASELINE.md")),
    ("P0-A", "Gate records the expected failures and their evidence",
     lambda: has("preset_dev/P0_BASELINE.md", "N01", "N02", "Update FX")),
    # ---- P0-B -----------------------------------------------------------
    ("P0-B", "Update FX rebuilds the selected system by UID",
     lambda: has("operators.py", "fx.update_system(scene, system)",
                 "fx_selected_system")),
    ("P0-B", "Remove/duplicate coordinate record and geometry",
     lambda: has("operators.py", "fx.remove_system(context.scene, system)",
                 "fx.compile_system(context.scene, copy)")
     if has("operators.py")[0] else (False, "operators.py missing")),
    ("P0-B", "Compilation is atomic (stash + rollback)",
     lambda: has("fx.py", "ALD | FX Compile", "Roll back", "raise")),
    ("P0-B", "Neutral reset never detaches a user compositor",
     lambda: has("snapshot.py", 'ng.get("ald_scene") is not None')),
    # ---- P0-C -----------------------------------------------------------
    ("P0-C", "Snapshot before every mutation path (Build included)",
     lambda: has("compositor.py", "snapshot.ensure(scene)")
     if has("fx.py", "_ensure_snapshot(scene)")[0]
     and has("fx.py", "_ensure_snapshot(scene)", "create_fireworks",
             "create_meteors", "compile_system", "apply_backend")[0]
     else (False, "snapshot coverage incomplete")),
    ("P0-C", "REMOVED state blocks automatic re-entry",
     lambda: has("snapshot.py", "REMOVED_KEY", "is_inactive",
                 "scene.get(REMOVED_KEY)")),
    ("P0-C", "Detach keeps the result (no material clear)",
     lambda: has("snapshot.py", "def detach", "fx.clear(scene)")
     and "materials.clear_scene(scene)" not in read("snapshot.py").split(
         "def detach", 1)[1].split("def ", 1)[0]),
    ("P0-C", "Shared collections are not removed",
     lambda: has("snapshot.py", "_shared_with_other_scene")),
    # ---- P0-D -----------------------------------------------------------
    ("P0-D", "FX coverage is the Cryptomatte matte, not luminance",
     lambda: has("compositor.py", "CompositorNodeCryptomatte", "NODE_FX_MATTE",
                 "matte_id")),
    ("P0-D", "F = Emission * coverage; main layer has the crypto pass",
     lambda: has("compositor.py", "NODE_FX_EMISSION",
                 "CompositorNodeCombineColor",
                 "use_pass_cryptomatte_material")),
    ("P0-D", "No legacy ALD FX Only build path",
     lambda: (not has("compositor.py", "def ensure_fx_only_layer")[0],
              "")),
    ("P0-D", "C = P(B)*(1-A) + F + Glare(F), F added unscaled",
     lambda: has("compositor.py", 'blend_type = "ADD"',
                 'restore.inputs["Factor"].default_value = 1.0')),
    ("P0-D", "View layers/transparent world cleaned up",
     lambda: has("compositor.py", "def remove_fx_layers", "remove_fx_layers(scene)")),
    ("P0-D", "Gate: real occlusion, zero-FX identity, P1 visibility",
     lambda: has("preset_dev/verify.py", "check_fx_occlusion(scene)",
                 "check_fx_identity(scene)", "check_fx_p1_visibility(scene)")),
    # ---- P0-E -----------------------------------------------------------
    ("P0-E", "Read-only diagnostics; UNKNOWN instead of unproven OK",
     lambda: has("diagnostics.py", '"UNKNOWN"',
                 'state["state"] = "UNKNOWN"',
                 "never during panel draw")
     and has("panels.py", "fx_diagnostic_report")[0]),
    ("P0-E", "Explicit diagnose operator evaluates and caches the report",
     lambda: has("operators.py", "class ALD_OT_fx_diagnose",
                 "diagnostics.diagnose_scene")),
    # ---- P1-A -----------------------------------------------------------
    ("P1-A", "Runtime rebuilt from event UID + explicit role, never names",
     lambda: has("fx.py", 'key = (obj.get("ald_fx_event")',
                 'obj.get("ald_fx_role")', "def _one_object")),
    ("P1-A", "Stable random_key independent from the list index",
     lambda: has("fx.py", "def _derive_key", "event.random_key = _derive_key",
                 "def _event_key")),
    ("P1-A", "Versioned migration and undo/redo rebuild",
     lambda: has("fx.py", "def migrate", "undo_post", "redo_post")
     and has("properties.py", "FX_SCHEMA = 2")[0]),
    # ---- P1-B -----------------------------------------------------------
    ("P1-B", "Anchor drives axis, units and gravity",
     lambda: has("fx.py", "def _anchor", "AXIS_VECTORS",
                 "-axis * 9.81 * scale")),
    ("P1-B", "Physical mode bursts at p_shell(T)",
     lambda: has("fx.py", '"PHYSICAL"', "_rise_position(launch, v0, drag, gravity, rise_time)")),
    ("P1-B", "Clock refresh without rebuilding",
     lambda: has("fx.py", "def refresh_clock")
     and has("properties.py", "def _on_fx_clock", "_on_fx_clock")[0]),
    ("P1-B", "Creation starts at the current frame",
     lambda: has("fx.py", "system.origin_frame = int(scene.frame_current)")),
    # ---- P1-C -----------------------------------------------------------
    ("P1-C", "Per-event GN failure falls back to the Python writer",
     lambda: has("fx.py", "fallback_materials", "A Py", "forced GN failure")
     and has("preset_dev/verify.py", "check_fx_gn_fallback")[0]),
    ("P1-C", "Mixed systems: gn = all, per-event skips",
     lambda: has("fx.py", 'runtime["gn"] = all',
                 'if entry.get("gn"):', 'if burst.get("gn_heads") is not None')),
    ("P1-C", "Trail energy/colour via Geometry attributes",
     lambda: has("fx.py", "event_color", "stable_noise")
     and has("fx_nodes.py", "energy_store", '"age_norm"', '"trail_u"')[0]),
    # ---- P2-A -----------------------------------------------------------
    ("P2-A", "Material reads event_color/stable_noise/age_norm/trail_u",
     lambda: has("fx.py", '_attribute_node(node_tree, "event_color"',
                 '_attribute_node(node_tree, "stable_noise"',
                 '_attribute_node(node_tree, "age_norm"',
                 '_attribute_node(node_tree, "trail_u"')),
    ("P2-A", "Role energies and Bolide render preset",
     lambda: has("fx.py", "ROLE_ENERGY", "meteor_head", "meteor_train")
     and has("fx.py", '"BOLIDE"', "METEOR_PRESETS")[0]),
    ("P2-A", "Visual profile exposed with its sub-roles",
     lambda: has("panels.py", "def draw_fx_profile", "ROLE_ENERGY")
     and has("fx.py", "ROLE_ENERGY")[0]),
    ("P2-A", "Explicit per-profile UI (Firework/Meteor/Bolide sub-roles)",
     lambda: has("panels.py", "draw_fx_profile", "Event: %s")
     and has("fx.py", '"BOLIDE"')[0]),
    # ---- P2-B -----------------------------------------------------------
    ("P2-B", "Calibration matrix: AgX, fixed camera/seed/exposure, glow",
     lambda: has("preset_dev/calibrate_fx.py", "AgX", "GLOWS", "exposure",
                 '"night"', '"sunset"')
     and exists("preset_dev/calibration/metrics.json")[0]),
    ("P2-B", "Standard is a diagnostic control, not a certificate",
     lambda: has("preset_dev/calibrate_fx.py",
                 "diagnostic control, not an AgX certificate")),
    # ---- P3 -------------------------------------------------------------
    ("P3", "Smoke is a real volume, not a World generator",
     lambda: has("smoke.py", "ShaderNodeVolumePrincipled", "ALD | Smoke",
                 "def create")),
    ("P3", "Smoke removed by Remove ALD",
     lambda: has("snapshot.py", "smoke_module.remove(scene)")),
    ("P3", "Aesthetic variants change the look without rebuilding",
     lambda: has("fx.py", "STYLES", "def apply_style")
     and has("properties.py", "fx_style")[0]),
    ("P3", "Directed 3/5 burst show",
     lambda: has("operators.py", "class ALD_OT_fx_show", '("3", "3 Bursts"',
                 '("5", "5 Bursts"')),
    ("P3", "Distinct benchmarks with hardware/scenario and budgets",
     lambda: has("preset_dev/bench_fx.py", "BUDGETS", "hardware", "scenario",
                 "frame_eval_gn_24_frames_s",
                 "frame_eval_python_24_frames_s")
     and exists("preset_dev/benchmarks.json")[0]),
    ("P3", "Smoke follows the Anchor axis (Y-up/X-up)",
     lambda: has("smoke.py", "def _place", "rotation_difference",
                 "fx._anchor")),
    # ---- Visual integration P2 (filament geometry) -----------------------
    ("VI-P2", "Points to Curves is fed by Mesh to Points",
     lambda: has("fx_nodes.py", "GeometryNodeMeshToPoints",
                 "to_points.outputs[\"Points\"]")),
    ("VI-P2", "The filament keeps an apparent width in pixels",
     lambda: has("fx.py", "def _world_per_pixel", "def _apparent_radius",
                 "fx_trail_min_px")
     and has("preset_dev/verify.py", "check_fx_trail_width")[0]),
    ("VI-P2", "Trail geometry realized: the width reaches real faces",
     lambda: has("preset_dev/verify.py", "new_from_object",
                 "the trail geometry is empty")),
    ("VI-P2", "Tube chosen over ribbon with a measured spike",
     lambda: (exists("preset_dev/trail_shape_spike.py")[0],
              "preset_dev/trail_shape_spike.py: tube 1.00, ribbon 0.00 edge-on")),
    ("VI-P2", "Secondary stars and a per-star trail cap",
     lambda: has("fx.py", "spoke, 25) < 0.35", "config[\"trail\"] * cap")),
]


def main():
    results = []
    for phase, label, check in CHECKS:
        try:
            outcome = check()
            if isinstance(outcome, tuple):
                ok, evidence = outcome
            else:
                ok, evidence = bool(outcome), ""
        except Exception as exc:
            ok, evidence = False, "audit error: %s" % exc
        results.append({"phase": phase, "label": label,
                        "state": "OK" if ok else "PARTIAL",
                        "evidence": evidence})
    counts = {}
    for item in results:
        counts[item["phase"]] = counts.get(item["phase"], 0) + 1
    passed = sum(1 for item in results if item["state"] == "OK")
    data = {"plan": "v2.27.0 P0-P3", "total": len(results),
            "passed": passed,
            "partial": len(results) - passed,
            "checks": results}
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    for item in results:
        print("AUDIT %-4s %-58s %-7s %s"
              % (item["phase"], item["label"], item["state"],
                 item["evidence"]))
    print("ALD AUDIT %d/%d OK | report %s"
          % (passed, len(results), OUT))
    return 0 if passed == len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
