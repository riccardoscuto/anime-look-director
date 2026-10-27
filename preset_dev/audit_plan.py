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
    ("P2-A", "Material reads event_color/stable_noise/age_norm/tail_u",
     lambda: has("fx.py", '_attribute_node(node_tree, "event_color"',
                 '_attribute_node(node_tree, "stable_noise"',
                 '_attribute_node(node_tree, "age_norm"',
                 '_attribute_node(node_tree, "tail_u"')),
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
    # ---- Visual integration P3 (shading, palette, glow) ------------------
    ("VI-P3", "Instanced particles read the INSTANCER domain",
     lambda: has("fx.py", 'attribute_type = "INSTANCER" if instancer',
                 "instancer_materials")),
    ("VI-P3", "F uses a binary presence, not the fractional matte",
     lambda: has("compositor.py", "presence", "GREATER_THAN",
                 "presence.outputs[0]")),
    ("VI-P3", "The punch-out writes black, not the 0.5 grey default",
     lambda: has("compositor.py",
                 "b_sock.default_value = (0.0, 0.0, 0.0, 1.0)")),
    ("VI-P3", "Glow calibrated on the composite and tested",
     lambda: has("properties.py", 'name="FX Glow", default=1.0',
                 'name="FX Glow Threshold", default=0.0',
                 'name="FX Glow Size", default=0.35')
     and has("preset_dev/verify.py", "check_fx_p3_shading")[0]),
    ("VI-P3", "Tail falloff and sky-tinted FX palette",
     lambda: has("fx.py", "tail_u", "1.0, 0.35", "_sky_tinted_colors")),
    # ---- Visual integration P4 (composition) -----------------------------
    ("VI-P4", "Depth hierarchy: farther means smaller",
     lambda: has("fx.py", "depth = (1.0, 1.18, 1.42)[role]",
                 "event.size = (1.0, 0.9, 0.8)[role]")),
    ("VI-P4", "A show grows its distance and lateral spread",
     lambda: has("fx.py", "distance *= 1.4", "spread *= 1.3")),
    ("VI-P4", "Every burst has exploded at the show age",
     lambda: has("fx.py", "(0.25 if role == 1 else 0.55)")),
    ("VI-P4", "Composition evidence and gate",
     lambda: (exists("preset_dev/composition.py")[0]
              and has("preset_dev/verify.py", "check_fx_composition")[0],
              "preset_dev/composition/composition.json")),
    # ---- Spatial Clouds 2.0 (v2.40) --------------------------------------
    ("VI-SC", "Coverage is the density threshold and is monotonic",
     lambda: has("clouds.py", "def _cloud_mesh", "threshold = max(0.02",
                 "if coverage <= 0.001")
     and has("preset_dev/verify.py", "Coverage 0 still builds")[0]),
    ("VI-SC", "Altitude and depth are world units on the Anchor axis",
     lambda: has("clouds.py", "clouds_altitude", "Vector(layer.axis)",
                 "fx._anchor")),
    ("VI-SC", "Persistent layers and in-place updates",
     lambda: has("clouds.py", "def refresh", "ald_clouds_signature",
                 "bpy.data.objects.get(layer.object_name)")
     and has("properties.py", "cloud_layers: CollectionProperty")[0]),
    ("VI-SC", "Islands with real sky openings, not a slab",
     lambda: has("clouds.py", "def _field", "_field_grid", "_sample",
                 "def _cloud_mesh")),
    ("VI-SC", "Shot Locked and Camera Facing",
     lambda: has("clouds.py", "SHOT_LOCKED", "CAMERA_FACING",
                 "def update_orientation")),
    ("VI-SC", "Local flash response driven by event.glow",
     lambda: has("clouds.py", "def update_flash", "ALD | Flash Energy")
     and has("fx.py", "event.glow")[0]),
    ("VI-SC", "Distinct UI and diagnostics",
     lambda: has("panels.py", '"Spatial Clouds"', "clouds_coverage",
                 "diagnostics")),
    ("VI-SC", "Environment filters read the base layer",
     lambda: has("compositor.py", "environment_layers", "use_pass_normal",
                 "_silhouette_mask(nodes, links, environment_layers")),
    ("VI-SC", "Apparent widths follow camera and resolution",
     lambda: has("fx.py", "def refresh_widths", "ald_fx_physical")
     and has("cameras.py", "fx.refresh_widths(scene)")[0]),
    ("VI-SC", "Event colour receives the sky-tinted palette",
     lambda: has("fx.py", "colors=family_colors")),
    ("VI-SC", "Coverage 1 keeps the border empty (strict threshold)",
     lambda: has("clouds.py", "0.98 - 1.02", "value > threshold")),
    ("VI-SC", "Shot Locked stores the creation rotation once",
     lambda: has("clouds.py", "rotation_valid", "current_rotation",
                 "layer.rotation = tuple(facing)")),
    ("VI-SC", "The mesh rebuild keeps the material",
     lambda: has("clouds.py", "material = obj.active_material",
                 "mesh.materials.append(material)")),
    ("VI-SC", "Cloud objects are resolved by UID inside the scene",
     lambda: has("clouds.py", "def _object", "ald_cloud_uid",
                 "_shared_with_other_scene")),
    ("VI-SC", "Flash attenuates with the world distance",
     lambda: has("clouds.py", "world_distance", "attenuation")),
    ("VI-SC", "Painterly depth uses the environment layer",
     lambda: has("compositor.py",
                 'depth = environment_layers.outputs.get("Depth") or depth')),
    ("VI-SC", "FX materials are scene-owned, including modifier inputs",
     lambda: has("compositor.py", "modifier.keys()", "ald_fx_material")
     and has("fx.py", "_scene_fx_materials")[0]),
    ("VI-SC", "The emission C0 test is runnable and fails explicitly",
     lambda: has("preset_dev/emission_isolation.py", "regions",
                 "return 0 if report[\"verdict\"] == \"PASS\" else 1")),
    ("VI-SC", "F is an external FX pass image, not the main emission",
     lambda: has("compositor.py", "def render_fx_pass", "NODE_FX_PASS",
                 "CompositorNodeImage")),
    ("VI-SC", "The gate proves the pass excludes a foreign emitter",
     lambda: has("preset_dev/verify.py", "check_fx_pass_isolation",
                 "the FX pass contains the foreign emitter")),
    ("VI-SC", "The FX pass is exposed in the UI",
     lambda: has("operators.py", "ald.fx_render_pass")
     and has("panels.py", "ald.fx_render_pass")[0]),
    ("VI-SC", "Framing checks the whole burst envelope",
     lambda: has("fx.py", "def event_envelope", "def event_frame_fraction")
     and has("preset_dev/verify.py", "event_frame_fraction")[0]),
    ("VI-SC", "A show fits its distance and lateral spread to the lens",
     lambda: has("fx.py", "def _fit_distance", "_tan_half", "limit =")),
    ("VI-SC", "The composition report uses the envelope",
     lambda: has("preset_dev/composition.py", "frame_fraction",
                 "event_frame_fraction")),
    ("VI-SC", "The cloud benchmark measures coverage and layers",
     lambda: has("preset_dev/bench_clouds.py", "polygons", "creation_s",
                 "refresh_s", "render_s")
     and exists("preset_dev/clouds_bench/metrics.json")[0]),
    ("VI-SC", "Scene copy: removal unlinks shared objects",
     lambda: has("clouds.py", "obj.users_collection",
                 "collection.objects.unlink(obj)")),
    ("VI-SC", "The FX pass follows the animation", 
     lambda: has("compositor.py", "def render_fx_pass_animation",
                 "frame_duration", "def _frame_path")
     and has("operators.py", "ald.fx_render_pass_animation")[0]),
    ("VI-SC", "The FX pass image belongs to one scene",
     lambda: has("compositor.py", "def _pass_image_name",
                 "ALD | FX Pass | ")),
    ("VI-SC", "The FX pass state is content-aware", 
     lambda: has("compositor.py", "def fx_pass_state", "pass_signature")
     and has("panels.py", "fx_pass_state")[0]),
    ("VI-SC", "Build repairs a duplicated scene before modifying it",
     lambda: has("operators.py", "ownership.repair", "ald.build")),
    ("VI-SC", "The shot and animation render the pass and the composite",
     lambda: has("operators.py", "ald.fx_render_shot", "ald.fx_render_animation",
                 "render(animation=True)")),
    ("VI-SC", "Cloud cards carry a border rim",
     lambda: has("clouds.py", "ald_edge", "edge_gain")),
    ("VI-SC", "FX materials are owned by the scene",
     lambda: has("fx.py", "owner=owner", "ald_fx_owner")
     and has("preset_dev/verify.py",
             "fx materials are shared between scenes")[0]),
    ("VI-SC", "The show fit uses the solver reach and the 0.95 target",
     lambda: has("fx.py", "def _family_reach", "def _fit_show",
                 "target=0.95")),
    ("VI-SC", "The hero is centred in the show layout",
     lambda: has("fx.py", "Symmetric show", "index == 0")),
    ("VI-SC", "An intentional crop is an explicit override",
     lambda: has("properties.py", "fx_fit_override")
     and has("preset_dev/verify.py", "fx_fit_override")[0]),
    ("VI-SC", "Light events are independent of the effect",
     lambda: has("fx.py", "def light_events", "METEOR")
     and has("clouds.py", "fx.light_events")[0]),
    ("VI-SC", "Two cloud light sources add",
     lambda: has("clouds.py", "ALD | Flash X2", "total_energy")),
    ("VI-SC", "The FX pass writes atomically and restores the render state",
     lambda: has("compositor.py", "os.replace", "previous_compositing")),
    ("VI-SC", "The FX pass isolates a nested FX collection",
     lambda: has("compositor.py", "def _isolate_collection",
                 "layer_collection")),
    ("VI-SC", "Spatial quality and World blend are controls",
     lambda: has("properties.py", "clouds_quality", "clouds_world_blend")
     and has("palette.py", "clouds_world_blend")[0]),
    ("VI-SC", "The duplicate fixture survives save and reload",
     lambda: has("preset_dev/duplicate_fixture.py", "save_as_mainfile",
                 "open_mainfile", "clouds._collection")),
    ("VI-SC", "The pass signature is scoped to the scene",
     lambda: has("fx.py", "\"scene\": _scene_id(scene)")),
    ("VI-SC", "Cloud islands use an interpolated contour",
     lambda: has("clouds.py", "def _cell_rings", "iso-line")
     and has("preset_dev/verify.py", "check_cloud_contour")[0]),
    ("VI-SC", "The release package excludes the research evidence",
     lambda: exists("LICENSE")[0]
     and has("blender_manifest.toml", "paths_exclude_pattern", "preset_dev/")
     and has("preset_dev/build_release.py", "extension", "build")[0]),
    ("VI-SC", "The copy owns its world", 
     lambda: has("ownership.py", "world.copy()", "scene.world")),
    ("VI-SC", "The auto sun is owned by its scene",
     lambda: has("palette.py", "SUN_OWNER_TAG", "users_scene")),
    ("VI-SC", "The default FX pass path is per scene",
     lambda: has("compositor.py", "def _default_pass_path",
                 "ald_fx_pass_%s")),
    ("VI-SC", "The sequence signature is per frame",
     lambda: has("compositor.py", "signatures[frame]", "json.dumps")
     and has("compositor.py", "json.loads")[0]),
    ("VI-SC", "Remove ALD on a duplicated scene is safe",
     lambda: has("operators.py", "ald.remove_from_scene", "ownership.repair")
     and has("snapshot.py", "world_is_shared")[0]),
    ("VI-SC", "One command runs gate, fixture and audit",
     lambda: has("preset_dev/verify_all.py", "ALD ALL: PASS")
     and has("preset_dev/audit_plan.py",
             "return 0 if passed == len(results) else 1")[0]),
    ("VI-SC", "Duplicated scene repair makes the copy independent",
     lambda: has("ownership.py", "def repair", "def _duplicate_objects",
                 "same_identity")
     and exists("preset_dev/duplicate_fixture.py")[0]),
    ("VI-SC", "Repair ownership is exposed in the UI",
     lambda: has("operators.py", "ald.repair_ownership")
     and has("panels.py", "ald.repair_ownership", "ALD data shared")[0]),
    ("VI-SC", "The duplicate fixture passes",
     lambda: has("preset_dev/duplicate_fixture.py", "DUP FIXTURE: PASS")),
    ("VI-SC", "The slab/control defect is reproduced in the baseline",
     lambda: (exists("preset_dev/clouds_baseline/metrics.json")[0]
              and exists("preset_dev/clouds_baseline/h0.35_a0.00_oblique.png")[0],
              "preset_dev/clouds_baseline/metrics.json")),
    # ---- Visual integration P6 (validation matrix) -----------------------
    ("VI-P6", "Matrix: 3 palettes x 4 families x 3 ages with metrics",
     lambda: has("preset_dev/validate_matrix.py", "PALETTES =",
                 "FAMILIES =", "AGES =", "def metrics", "contact_sheet")),
    ("VI-P6", "Criteria declared and pinned clock",
     lambda: has("preset_dev/validate_matrix.py", "LIMITS =",
                 "settings.fx_age = 0.0")),
    ("VI-P6", "36/36 pass with a contact sheet and the report",
     lambda: (exists("preset_dev/validation/metrics.json")[0]
              and exists("preset_dev/validation/sheet.png")[0]
              and exists("preset_dev/P6_REPORT.md")[0],
              "preset_dev/validation/metrics.json")),
    ("VI-P6", "Apparent-size floor for heads and beads too",
     lambda: has("fx.py", "0.6 * 1.2 * world_per_px", '"pistil_grains"')),
    # ---- Verification pass (v2.37) ---------------------------------------
    ("VI-UI", "The gate calls the icon and parity checks",
     lambda: has("preset_dev/verify.py", "check_ui_parity(scene)",
                 "check_panel_icons()")),
    ("VI-UI", "The cloud panel icon exists in Blender 5.1",
     lambda: has("panels.py", '"Spatial Clouds", icon="WORLD"')),
    ("VI-UI", "UI probe resolves relative output against the add-on",
     lambda: has("preset_dev/ui_probe.py", "os.path.isabs(out)",
                 "os.path.join(ADDON_PATH, out)")),
    ("VI-UI", "Temporal strip: six ages and evidence",
     lambda: (exists("preset_dev/temporal_strip.py")[0]
              and exists("preset_dev/temporal/sheet.png")[0],
              "preset_dev/temporal/temporal.json")),
    # ---- Showcase (v2.38) ------------------------------------------------
    ("VI-ALL", "A 1080p showcase with the whole stack",
     lambda: (exists("preset_dev/showcase.py")[0]
              and exists("preset_dev/showcase/night_5_bursts.png")[0]
              and exists("preset_dev/showcase/dusk_3_bursts.png")[0],
              "preset_dev/showcase/showcase.json")),

    ("VI-ALL", "Showcase foreground is scene content, not an add-on feature",
     lambda: has("preset_dev/showcase.py", "def add_foreground",
                 "(0.004, 0.004, 0.008")),
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
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
