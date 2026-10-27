"""Phase 6 technical gate for the World Sky Edition.

Checks idempotent apply, deterministic generation, wind continuity, shooting
star slot isolation, duplicated-scene ownership, save/reload persistence and
resource cost. Writes ``preset_dev/phase6/technical.json``.

Run::

    blender -b --factory-startup --python-exit-code 1 \
        --python preset_dev/phase6_technical.py
"""

import json
import os
import sys
import tempfile
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "phase6")
TMP = os.path.join(tempfile.gettempdir(), "ald_phase6_technical.blend")
CHECKS = []


def check(name, condition, detail=""):
    passed = bool(condition)
    CHECKS.append({"name": name, "passed": passed, "detail": detail})
    print("P6T %-38s %s %s" % (name, "OK" if passed else "FAIL", detail))
    return passed


def build_scene(name="Phase6 Technical"):
    scene = bpy.data.scenes.new(name)
    scene.world = None
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 320
    scene.render.resolution_y = 180
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    data = bpy.data.cameras.new(name + " Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new(name + " Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    return scene


def render(scene, name):
    path = os.path.join(OUT, name + ".png")
    scene.render.filepath = path
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def signature(scene, palette):
    node = palette._gradient_node(scene.world.node_tree)
    values = {}
    for item in node.inputs:
        try:
            value = item.default_value
            if hasattr(value, "__len__"):
                values[item.name] = [round(float(v), 6) for v in value]
            else:
                values[item.name] = round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return values


def apply(scene, palette, key, **values):
    scene.ald.palette = key
    palette.apply_palette(scene, key)
    for name, value in values.items():
        setattr(scene.ald, name, value)
    palette.apply_palette(scene, key)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    from anime_look_director import palette, ownership, identity

    scene = build_scene()
    apply(scene, palette, "SUMMER_NOON", cloud_amount=0.55,
          cloud_type="CUMULUS")

    # 1. Applying the same palette twice is idempotent.
    before = signature(scene, palette)
    node_count = len(scene.world.node_tree.nodes)
    image_a = render(scene, "tech_idempotent_a")
    apply(scene, palette, "SUMMER_NOON")
    after = signature(scene, palette)
    image_b = render(scene, "tech_idempotent_b")
    check("apply is idempotent", before == after and
          node_count == len(scene.world.node_tree.nodes),
          "signature %s, nodes %d" % ("equal" if before == after else "changed",
                                      node_count))
    check("idempotent render is identical", np.array_equal(image_a, image_b),
          "max delta %.6f" % float(np.max(np.abs(image_a - image_b))))

    # 2. A fresh world generated in a second scene is identical.
    other = build_scene("Phase6 Technical B")
    apply(other, palette, "SUMMER_NOON", cloud_amount=0.55,
          cloud_type="CUMULUS")
    image_c = render(other, "tech_deterministic_b")
    check("generation is deterministic", before == signature(other, palette),
          "second scene signature")
    check("deterministic render is identical",
          np.array_equal(image_a, image_c),
          "max delta %.6f" % float(np.max(np.abs(image_a - image_c))))

    # 3. Wind advances the field and returns deterministically to frame 1.
    scene.ald.cloud_wind = 1.0
    palette.apply_palette(scene, "SUMMER_NOON")
    scene.frame_set(1)
    palette.update_sun_controls(scene)
    frame_1 = render(scene, "tech_wind_f1")
    offset_1 = list(signature(scene, palette)["Cloud Offset"])
    scene.frame_set(48)
    palette.update_sun_controls(scene)
    frame_12 = render(scene, "tech_wind_f48")
    offset_12 = list(signature(scene, palette)["Cloud Offset"])
    scene.frame_set(1)
    palette.update_sun_controls(scene)
    frame_1b = render(scene, "tech_wind_f1b")
    wind_delta = float(np.mean(np.abs(frame_1 - frame_12)))
    check("wind advances the cloud field",
          offset_1 != offset_12 and wind_delta > 0.002,
          "offset %s -> %s, delta %.4f" % (offset_1[:2], offset_12[:2],
                                           wind_delta))
    check("wind is deterministic at a fixed frame",
          np.array_equal(frame_1, frame_1b),
          "max delta %.6f" % float(np.max(np.abs(frame_1 - frame_1b))))

    # 4. Shooting-star slots are independent.
    scene.ald.clouds = False
    scene.ald.stars = True
    scene.ald.palette = "NEON_NIGHT"
    bpy.ops.ald.apply_palette()
    scene.ald.clouds = False
    scene.ald.shooting_star_events.clear()
    for index in range(2):
        event = scene.ald.shooting_star_events.add()
        event.name = "Tech Star %d" % (index + 1)
        event.start_frame = 1
        event.duration = 24
        event.azimuth = -26.0 + index * 8.0
        event.elevation = 20.0
        event.direction = -35.0
        event.length = 22.0
        event.trail = 0.60
        event.thickness = 0.0018
        event.brightness = 3.0
        event.glow = 0.8
        event.color = (0.88, 0.94, 1.0)
    palette.apply_palette(scene, "NEON_NIGHT")
    scene.frame_set(8)
    both = render(scene, "tech_stars_both")
    slots_both = signature(scene, palette)
    scene.ald.shooting_star_events[0].enabled = False
    palette.apply_palette(scene, "NEON_NIGHT")
    slots_one = signature(scene, palette)
    star1_before = {k: v for k, v in slots_both.items()
                    if k.startswith("Star1 ")}
    star1_after = {k: v for k, v in slots_one.items() if k.startswith("Star1 ")}
    check("disabling a star leaves the other slot intact",
          slots_one["Star0 Enabled"] == 0.0 and star1_before == star1_after,
          "Star0 %s, Star1 %s" % (slots_one["Star0 Enabled"],
                                  "equal" if star1_before == star1_after
                                  else "changed"))
    alone = render(scene, "tech_stars_one")
    check("the disabled star leaves the render",
          not np.array_equal(both, alone) and
          float(both.max()) >= float(alone.max()),
          "max %.4f vs %.4f" % (float(both.max()), float(alone.max())))
    scene.ald.shooting_star_events[0].enabled = True
    palette.apply_palette(scene, "NEON_NIGHT")
    restored = signature(scene, palette)
    check("re-enabling restores the exact slot",
          restored["Star0 Enabled"] == 1.0 and
          {k: v for k, v in restored.items() if k.startswith("Star0 ")} ==
          {k: v for k, v in slots_both.items() if k.startswith("Star0 ")},
          "Star0 Enabled %s" % restored["Star0 Enabled"])

    # 5. A duplicated scene can be repaired without touching the original.
    original_world = scene.world
    original_sky = signature(scene, palette)["Sky Color"]
    copy = scene.copy()
    shared_before = ownership.has_shared(copy)
    shared_world = copy.world is original_world
    check("a plain scene copy shares identity and World",
          shared_before and shared_world,
          "id %s" % copy.get(identity.ID_KEY, "")[:8])
    repaired = ownership.repair(copy)
    check("ownership repair gives a new identity and World",
          repaired == 1 and not ownership.has_shared(copy) and
          copy.world is not original_world and
          identity.scene_id(copy) != identity.scene_id(scene),
          "id %s" % identity.scene_id(copy)[:8])
    apply(copy, palette, "NEON_NIGHT")
    check("the original scene is untouched by the copy",
          signature(scene, palette)["Sky Color"] == original_sky and
          scene.world is original_world,
          "sky %s" % original_sky)

    # 6. Cost and the absence of FX objects.
    start = time.perf_counter()
    for _ in range(20):
        palette.apply_palette(scene, "SUMMER_NOON")
    apply_ms = (time.perf_counter() - start) * 1000.0 / 20.0
    start = time.perf_counter()
    render(scene, "tech_timing")
    render_ms = (time.perf_counter() - start) * 1000.0
    star_inputs = [name for name in signature(scene, palette)
                   if name.startswith("Star") and name.endswith("Enabled")]
    check("the World builds four fixed star slots",
          len(star_inputs) == 4, "%d slots" % len(star_inputs))
    check("no FX object or legacy collection exists",
          not [o for o in bpy.data.objects if o.get("ald_fx")] and
          not [c for c in bpy.data.collections
               if c.name in {"ald_fx", "ald_clouds", "ald_smoke"}],
          "%d objects" % len(bpy.data.objects))
    check("apply and render stay within budget",
          apply_ms < 50.0 and render_ms < 5000.0,
          "apply %.1f ms, render %.0f ms" % (apply_ms, render_ms))

    # 7. The controlled event survives save/reload.
    scene.ald.shooting_star_events[1].name = "Tech Persist"
    bpy.ops.wm.save_as_mainfile(filepath=TMP)
    bpy.ops.wm.open_mainfile(filepath=TMP)
    scene = bpy.data.scenes["Phase6 Technical"]
    events = scene.ald.shooting_star_events
    check("the shooting star survives save/reload",
          len(events) == 2 and events[1].name == "Tech Persist",
          "%d events" % len(events))
    check("the World group survives save/reload",
          palette._gradient_node(scene.world.node_tree) is not None,
          "gradient marker")

    report = {
        "checks": CHECKS,
        "passed": sum(1 for item in CHECKS if item["passed"]),
        "total": len(CHECKS),
        "apply_ms": round(apply_ms, 2),
        "render_ms": round(render_ms, 1),
        "objects": len(bpy.data.objects),
        "world_nodes": len(scene.world.node_tree.nodes),
    }
    with open(os.path.join(OUT, "technical.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    ok = report["passed"] == report["total"]
    print("ALD PHASE6 TECHNICAL %d/%d %s"
          % (report["passed"], report["total"], "PASS" if ok else "FAIL"))
    try:
        os.remove(TMP)
    except OSError:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
