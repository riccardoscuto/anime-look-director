"""Phase 3 UI registration, state, lifecycle and compatibility checks."""

import inspect
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

from anime_look_director import compositor, operators, panels  # noqa: E402

EVIDENCE = os.path.join(HERE, "phase3_ui")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="anime_look_director")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    cam_data = bpy.data.cameras.new("UI Camera")
    camera = bpy.data.objects.new("UI Camera", cam_data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    result = {}
    failures = []

    def check(name, ok, detail=""):
        result[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    # Scenario A: a preset applies without a compositor stack.
    scene.ald.palette = "GOLDEN_HOUR"
    applied = bpy.ops.ald.apply_palette()
    check("scenario_a.applied", applied == {"FINISHED"}, str(applied))
    check("scenario_a.no_stack", compositor.scene_stack(scene) is None)
    check("scenario_a.no_group", scene.compositing_node_group is None)
    check("scenario_a.preset", scene.ald.palette == "GOLDEN_HOUR")

    # Scenario B: the World controls remain reachable and effective.
    scene.ald.sun_elevation = -4.0
    scene.ald.horizon_offset = 0.2
    scene.ald.clouds = True
    scene.ald.cloud_type = "CIRRUS"
    scene.ald.cloud_amount = 0.7
    scene.ald.cloud_sun_scatter = 0.6
    scene.ald.stars = False
    check("scenario_b.values",
          abs(scene.ald.sun_elevation + 4.0) < 1e-4
          and abs(scene.ald.horizon_offset - 0.2) < 1e-5
          and scene.ald.cloud_type == "CIRRUS"
          and abs(scene.ald.cloud_amount - 0.7) < 1e-5
          and abs(scene.ald.cloud_sun_scatter - 0.6) < 1e-5
          and not scene.ald.stars)

    scene_panels = ("ALD_PT_scene", "ALD_PT_atmosphere", "ALD_PT_clouds",
                    "ALD_PT_stars", "ALD_PT_shooting_stars", "ALD_PT_custom",
                    "ALD_PT_materials", "ALD_PT_compositor", "ALD_PT_advanced")
    view3d_sections = {
        "ALD_PT_view3d_atmosphere": ("draw_atmosphere",),
        "ALD_PT_view3d_clouds": ("draw_clouds",),
        "ALD_PT_view3d_stars": ("draw_stars",),
        "ALD_PT_view3d_shooting_stars": ("draw_shooting_stars",),
        "ALD_PT_view3d_custom": ("draw_custom_colors",),
        "ALD_PT_view3d_materials": ("draw_material_presets", "draw_shadows"),
        "ALD_PT_view3d_compositor": ("draw_compositor",),
        "ALD_PT_view3d_advanced": ("draw_legacy", "draw_scene_actions"),
    }
    for name in scene_panels + tuple(view3d_sections) + ("ALD_PT_view3d",):
        check("registered." + name, hasattr(bpy.types, name))

    check("shooting.parent",
          bpy.types.ALD_PT_shooting_stars.bl_parent_id == "ALD_PT_scene")
    check("stars.parent",
          bpy.types.ALD_PT_stars.bl_parent_id == "ALD_PT_scene")
    check("sidebar.parent",
          bpy.types.ALD_PT_view3d.bl_space_type == "VIEW_3D")
    check("sidebar.category",
          bpy.types.ALD_PT_view3d.bl_category == "Anime Look")
    check("sidebar.root",
          "draw_palette" in inspect.getsource(panels.ALD_PT_view3d.draw))
    for name, functions in view3d_sections.items():
        cls = getattr(bpy.types, name)
        source = inspect.getsource(cls.draw)
        check("sidebar." + name,
              cls.bl_parent_id == "ALD_PT_view3d"
              and all(function in source for function in functions))

    atmosphere = inspect.getsource(panels.draw_atmosphere)
    clouds = inspect.getsource(panels.draw_clouds)
    shooting = inspect.getsource(panels.draw_shooting_stars)
    compositor_draw = inspect.getsource(panels.draw_compositor)
    viewport_op = inspect.getsource(
        operators.ALD_OT_viewport_compositor.execute)
    check("atmosphere.no_beams", "god_rays" not in atmosphere)
    check("compositor.beams", "god_rays" in compositor_draw)
    check("clouds.groups",
          all(word in clouds for word in
              ("Distribution", "Shape", "Lighting", "Animation",
               "cloud_sun_scatter")))
    check("shooting.groups",
          all(word in shooting for word in
              ("Timing", "Trajectory", "Appearance")))
    check("compositor.states",
          all(text in compositor_draw for text in
              ("Inactive: no ALD stack", "Configured; render disabled",
               "Active in render", "Viewport preview")))
    check("compositor.foreign_warning",
          "Non-ALD compositor group" in compositor_draw)
    check("viewport_op.current_area", "context.area" in viewport_op
          and "context.window_manager.windows" not in viewport_op)
    check("shooting_event_controls",
          all(name in shooting for name in
              ("start_frame", "duration", "azimuth", "elevation",
               "direction", "length", "curvature", "trail", "thickness",
               "brightness", "glow", "color")))

    # Scenario D/E: inactive, foreign, configured and active states.
    scene.compositing_node_group = None
    scene.render.use_compositing = True
    check("state.inactive", compositor.scene_stack(scene) is None)

    user = bpy.data.node_groups.new("User Compositor", "CompositorNodeTree")
    scene.compositing_node_group = user
    check("state.foreign.none", compositor.scene_stack(scene) is None)
    compositor.remove(scene)
    check("state.foreign.untouched",
          scene.compositing_node_group == user)

    scene.compositing_node_group = None
    stack = compositor.build(scene)
    check("state.active.stack", stack == compositor.scene_stack(scene))
    check("state.active.render", bool(scene.render.use_compositing))
    scene.render.use_compositing = False
    check("state.disabled.stack",
          compositor.scene_stack(scene) is not None)
    check("state.disabled.render", not scene.render.use_compositing)
    scene.render.use_compositing = True

    # Scenario C: add, duplicate, preview, remove, and the four-event cap.
    settings = scene.ald
    while len(settings.shooting_star_events):
        settings.shooting_star_events.remove(0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.frame_set(7)
    added = bpy.ops.ald.shooting_star_add()
    check("scenario_c.add", added == {"FINISHED"})
    check("scenario_c.add_state",
          len(settings.shooting_star_events) == 1
          and settings.shooting_star_selected == 0
          and settings.shooting_star_events[0].start_frame == 7)
    first = settings.shooting_star_events[0]
    check("scenario_c.add_sky",
          first.elevation >= 1.0 and first.elevation <= 89.0)
    duplicated = bpy.ops.ald.shooting_star_duplicate()
    check("scenario_c.duplicate",
          duplicated == {"FINISHED"} and len(settings.shooting_star_events) == 2)
    copy = settings.shooting_star_events[1]
    check("scenario_c.duplicate_values",
          copy.name == first.name + " Copy"
          and copy.start_frame == first.start_frame + 12)
    previewed = bpy.ops.ald.shooting_star_preview()
    check("scenario_c.preview", previewed == {"FINISHED"})
    check("scenario_c.preview_frame",
          scene.frame_current == copy.start_frame + max(1, copy.duration // 3))
    removed = bpy.ops.ald.shooting_star_remove()
    check("scenario_c.remove",
          removed == {"FINISHED"}
          and len(settings.shooting_star_events) == 1
          and settings.shooting_star_selected == 0)
    for _ in range(3):
        bpy.ops.ald.shooting_star_add()
    check("scenario_c.limit", len(settings.shooting_star_events) == 4)
    check("scenario_c.fifth_cancelled",
          bpy.ops.ald.shooting_star_add() == {"CANCELLED"})
    check("scenario_c.duplicate_cancelled",
          bpy.ops.ald.shooting_star_duplicate() == {"CANCELLED"})
    while len(settings.shooting_star_events):
        settings.shooting_star_events.remove(0)
    settings.shooting_star_selected = 0

    # Scenario F: a real pre-2.57 project keeps its data and shader marker.
    legacy = os.path.join(EVIDENCE, "legacy_scene.blend")
    if not os.path.isfile(legacy):
        legacy = os.path.join(HERE, "legacy", "v256_fixture.blend")
    bpy.ops.wm.open_mainfile(filepath=legacy)
    old_scene = bpy.context.scene
    old_events = old_scene.ald.shooting_star_events
    old_group = bpy.data.node_groups.get("ALD | World Gradient")
    check("scenario_f.loaded", old_scene.world is not None
          and old_scene.camera is not None)
    check("scenario_f.events", len(old_events) == 4
          and [event.name for event in old_events]
          == ["Legacy A", "Legacy B", "Legacy C", "Legacy D"])
    check("scenario_f.values",
          abs(old_events[0].azimuth - 110.0) < 1e-6
          and old_events[0].duration == 24
          and old_events[0].start_frame == 10)
    check("scenario_f.palette", old_scene.ald.palette == "NEON_NIGHT")
    check("scenario_f.marker",
          old_group is not None and old_group.get("ald_build") == 29,
          str(old_group.get("ald_build")) if old_group else "no group")
    check("scenario_f.no_compositor",
          old_scene.compositing_node_group is None)

    result["failures"] = failures
    result["status"] = "PASS" if not failures else "FAIL"
    os.makedirs(EVIDENCE, exist_ok=True)
    out = os.environ.get("PHASE3_UI_OUT",
                         os.path.join(EVIDENCE, "phase3_ui.json"))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("PHASE3 UI", json.dumps({"status": result["status"],
                                   "failures": failures}))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
