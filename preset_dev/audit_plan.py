"""Audit the operational plan against the code.

Usage:
  blender -b --factory-startup --python preset_dev/audit_plan.py -- [--out FILE]

Every requirement of the plan is checked in the source of the add-on and in
the gate, and the report says what is covered and what is not.

It never saves the .blend of the user.
"""

import json
import os
import sys

import bpy

ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return out


def read(name):
    path = os.path.join(ADDON_PATH, name)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def find(text, *needles):
    return all(needle in text for needle in needles)


def build_report():
    fx = read("fx.py")
    nodes = read("fx_nodes.py")
    props = read("properties.py")
    panels = read("panels.py")
    ops = read("operators.py")
    comp = read("compositor.py")
    palette = read("palette.py")
    cameras = read("cameras.py")
    shot = read("shots.py")
    verify = read(os.path.join("preset_dev", "verify.py"))
    materials = read("materials.py")
    snapshot = read("snapshot.py")
    docs = {name: read(name) for name in
            ("README.md", "RECAP.md", "CHANGELOG.md", "TECH_NOTES.md",
             "AGENTS.md")}
    items = []

    def item(section, requirement, ok, evidence):
        items.append({"section": section, "requirement": requirement,
                      "ok": bool(ok), "evidence": evidence})

    # 2. the architectural invariants
    item("2", "Determinism: the state depends on the configuration, the seed "
         "and the time, never on the history",
         find(fx, "def burst_population", "hashlib")
         and find(verify, "check_fx_gn_determinism", "check_fx_gn_python_parity"),
         "burst_population + the frame jump and the parity tests")
    item("2", "Time in seconds: the same state at 24, 30 and 60 fps",
         find(fx, "expm1")
         and find(palette, "_scene_seconds")
         and find(verify, "check_world_time_seconds"),
         "the stable solver, the clouds in seconds, the fps test")
    item("2", "Ownership per scene and per system",
         find(fx, "def _scene_id", "OWNER_KEY", "uuid"),
         "the persistent UUID and the tagged collection")
    item("2", "No global purge: only the datablocks of the add-on",
         find(fx, "def _cleanup_orphans")
         and find(snapshot, "ald_fx_material", "\"ald_fx\""),
         "_cleanup_orphans and the orphan removal")
    item("2", "Reversibility: a snapshot or a detach strategy",
         find(snapshot, "def ensure", "def restore", "def detach"),
         "the snapshot, the removal and the detach")
    item("2", "Exclusive backend: OFF, Legacy World and FX 3D",
         find(fx, "def apply_backend")
         and find(verify, "check_fx_backend"),
         "apply_backend and the exclusivity test")
    item("2", "GN and Python share the same initial data",
         find(fx, "def burst_population")
         and find(fx, "population[\"heads\"]"),
         "burst_population feeds the attributes and the writer")
    item("2", "No automatic save of the .blend and no implicit bake",
         "save_as_mainfile" not in fx and "save_as_mainfile" not in ops
         and "wm.save" not in fx,
         "no save call in the add-on")

    # 3. the phase P0-A
    item("3.1", "FX-01 the decay shrinks: s(u) = m + (1 - m) * (1 - u) ** p",
         find(nodes, "one_minus", "Decay Power", "Role Energy")
         and find(verify, "check_fx_decay_curve"),
         "the shape decay, the energy attribute and the multi age test")
    item("3.2", "FX-02 the burst count is never overwritten",
         find(fx, "total", "len(events)")
         and find(verify, "check_fx_burst_centers"),
         "the distinct names and the composition test")
    item("3.3", "FX-03 the meteors cross the screen",
         find(fx, "shower")
         and find(verify, "check_fx_meteor_travel"),
         "the lateral shower and the travel test")
    item("3.4", "FX-04 one event birth for the head, the train and the "
         "fragments",
         find(fx, "event_birth", "persistence")
         and find(verify, "check_fx_meteor_timing"),
         "the event birth and the timing test")
    item("3.5", "FX-05 the origin of the children is fixed at the emission",
         find(fx, "parent = _position(start, v0, drag, emit)"),
         "the fixed origin in the population")

    # 4. the phase P0-B
    item("4.1", "A persistent structure of systems and events",
         find(props, "class ALD_FX_System", "class ALD_FX_Event",
              "CollectionProperty"),
         "the PropertyGroups and the collections")
    item("4.2", "The registry is rebuilt after load_post",
         find(fx, "def rebuild_registry", "_on_load_post"),
         "rebuild_registry and the load handler")
    item("4.3", "A robust identity and the duplication of a scene",
         find(fx, "_CLAIMED", "_retag_scene")
         and find(verify, "check_fx_scene_duplicate"),
         "the claim of the identity and the duplication test")
    item("4.4", "The node groups carry a version marker",
         find(nodes, "ald_schema", "SCHEMA")
         and find(verify, "check_fx_gn_schema"),
         "the build marker and the migration test")

    # 5. the phase P1-A
    item("5.1", "The two surfaces share the drawing functions",
         find(panels, "def draw_fx", "def draw_world", "def draw_compositor")
         and find(verify, "check_ui_parity"),
         "the shared functions and the parity test")
    item("5.2", "The FX panel follows the structure of the plan",
         find(panels, "Systems", "Timing", "Launch", "Explosion", "Look",
              "Advanced", "Actions"),
         "the seven sections")
    item("5.3", "The backend semantics are applied at once",
         find(fx, "def apply_backend")
         and find(panels, "LEGACY"),
         "apply_backend and the legacy controls")

    # 6. the phase P1-B
    item("6.1", "A snapshot before the first modification",
         find(snapshot, "def ensure", "bg_color", "use_compositing")
         and find(comp, "use_pass_object_index")
         and find(props, "_on_world"),
         "the world, the sun, the compositor, the passes and the materials")
    item("6.2", "Remove ALD from Scene with a maintenance mode",
         find(snapshot, "MAINTENANCE_KEY", "def restore")
         and find(ops, "ald.remove_from_scene"),
         "the maintenance flag and the operator")

    # 7. the phase P1-C
    item("7.1", "The firework is a complete event",
         find(fx, "shell_population", "def burst_population"),
         "the launcher, the shell and the burst")
    item("7.2", "The Director and the Physical modes",
         find(fx, "def _rise_velocity", "PHYSICAL", "DIRECTOR"),
         "the two modes")
    item("7.3", "The operational equations",
         find(fx, "expm1", "v_inf"),
         "the stable form of the equations")
    item("7.4", "The continuity at the burst",
         find(fx, "residual")
         and find(verify, "check_fx_event_continuity"),
         "the inherited velocity and the continuity test")
    item("7.5", "An explicit time origin: Timeline and Preview",
         find(props, "timing_mode")
         and find(fx, "origin_frame"),
         "the timing mode of the system")

    # 8. the phase P1-D
    item("8", "The meteors are events with a shared radiant",
         find(fx, "shower", "event_birth")
         and find(verify, "check_fx_meteor_timing", "check_fx_meteor_travel"),
         "the radiant, the timing and the travel tests")
    item("8", "The Hero Meteor preset",
         find(fx, "BOLIDE") and find(ops, "ald.fx_bolide")
         and find(verify, "check_fx_bolide"),
         "the preset, the operator and the test")

    # 9. the phase P2
    item("9.1", "The material contract of the particles",
         find(fx, "ROLE_CODES", "event_color", "stable_noise")
         and find(nodes, "trail_u", "age_norm", "energy"),
         "the attributes of the contract")
    item("9.2", "The visual profile of every role",
         find(fx, "ROLE_ENERGY") and find(nodes, "Role Energy"),
         "the energy of the role")
    item("9.3", "The FX layer is isolated from the other emissive surfaces",
         find(comp, "ALD | FX Contribution", "ensure_fx_base_layer")
         and find(verify, "check_fx_foreign_emission"),
         "the dedicated layer and the foreign emission test")
    item("9.4", "The atmosphere and the colour management",
         find(fx, "fx_atmospheric_fade") and find(nodes, "Atmospheric Fade"),
         "the atmospheric fade")

    # 10. the phase P3
    item("10", "The solver is numerically stable",
         find(fx, "expm1") and find(verify, "check_fx_solver_stability"),
         "the stable form and the test")
    item("10", "The backend is chosen before the allocation",
         find(fx, "_build_python_objects", "if not use_gn"),
         "the two paths and the transactional swap")
    item("10", "The camera uses the evaluated transform",
         find(fx, "evaluated_get")
         and find(verify, "check_fx_camera_evaluated"),
         "the evaluated matrix and the constraint test")
    item("10", "The custom colours accept the HDR range",
         find(props, "max=4.0"),
         "the custom colours")
    item("10", "The clouds and the legacy stars follow the seconds",
         find(palette, "_scene_seconds", "_shooting_star_phase")
         and find(verify, "check_world_time_seconds"),
         "the seconds and the test")
    item("10", "The Kamuro family",
         find(fx, "KAMURO") and find(verify, "check_fx_kamuro"),
         "the family and the test")
    item("10", "The atmospheric smoke",
         False,
         "optional in the plan: only when really necessary")

    # 11. the file map
    for name, needle in (("fx.py", "burst_population"),
                         ("fx_nodes.py", "SCHEMA"),
                         ("properties.py", "ALD_FX_System"),
                         ("operators.py", "ald.remove_from_scene"),
                         ("panels.py", "draw_fx"),
                         ("compositor.py", "ALD | FX Contribution"),
                         ("palette.py", "_scene_seconds"),
                         ("materials.py", "ald_st_color"),
                         ("cameras.py", "evaluated_get"),
                         ("preset_dev/verify.py", "ALD GATE"),
                         ("preset_dev/lookdev_fx.py", "def main"),
                         ("preset_dev/ui_probe.py", "def main")):
        item("11", "The file map: %s" % name,
             find(read(name.replace("/", os.sep)), needle),
             needle)

    # 12. the test matrix
    for label, needle in (("Decay multi age", "check_fx_decay_curve"),
                          ("GN against Python", "check_fx_gn_python_parity"),
                          ("Frame jump", "check_fx_gn_determinism"),
                          ("24/30/60 fps", "check_world_time_seconds"),
                          ("Future event", "check_fx_future_event"),
                          ("Firework continuity", "check_fx_event_continuity"),
                          ("Meteor timing", "check_fx_meteor_timing"),
                          ("Meteor screen travel", "check_fx_meteor_travel"),
                          ("Reopen fixture", "check_fx_fixture"),
                          ("Scene duplicate", "check_fx_scene_duplicate"),
                          ("Backend modes", "check_fx_backend"),
                          ("Remove ALD", "check_scene_actions"),
                          ("Foreign emission", "check_fx_foreign_emission"),
                          ("Occlusion", "check_fx_occlusion"),
                          ("GN migration", "check_fx_gn_schema"),
                          ("UI parity", "check_ui_parity")):
        item("12", "The test matrix: %s" % label, needle in verify, needle)

    # 13. the documentation
    item("13", "The documentation is aligned with the version and the "
         "behaviour",
         all("2.11" in text or "2.12" in text for text in docs.values()),
         "the version in the five documents")

    # 14. the definition of done
    item("14", "The definition of done of the milestone",
         os.path.exists(os.path.join(ADDON_PATH, "preset_dev", "milestone.py")),
         "preset_dev/milestone.py with the thirteen checks")
    return items


def main():
    out = parse_args()
    items = build_report()
    passed = sum(1 for entry in items if entry["ok"])
    print("ALD PLAN AUDIT %d/%d" % (passed, len(items)))
    section = None
    for entry in items:
        if entry["section"] != section:
            section = entry["section"]
            print("-- section %s" % section)
        print("  [%s] %-72s %s"
              % ("OK" if entry["ok"] else "--", entry["requirement"][:72],
                 entry["evidence"]))
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"passed": passed, "total": len(items), "items": items},
                      handle, indent=2)
        print("ALD PLAN AUDIT FILE", out)


if __name__ == "__main__":
    main()
