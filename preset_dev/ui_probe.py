"""UI verification: screenshot the Anime Look Director panels.

Usage:
  blender --factory-startup --python preset_dev/ui_probe.py -- [--out DIR]

Opens a fresh Blender, enables the add-on, applies a World palette and writes
the screenshots of the sidebar panel and of the Scene properties (Anime Look
Director, World & Shadows and the optional Compositor Stack).

The Properties editor is maximised so the whole panel fits, and the window
must be on screen: a screenshot taken while the window is minimized or off
screen is black.

This is a development tool: it never saves a .blend.
"""

import os
import sys
import tempfile

import bpy

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = {"step": 0}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(ADDON_PATH, "preset_dev", "ui")
    wait = 10.0
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        if not os.path.isabs(out):
            # Blender's working directory is not the add-on directory: a
            # relative --out wrote the screenshots outside the repository and
            # the probe reported them missing.
            out = os.path.join(ADDON_PATH, out)
    if "--wait" in argv:
        wait = float(argv[argv.index("--wait") + 1])
    return out, wait


def shot(out_dir, name):
    path = os.path.join(out_dir, name)
    try:
        bpy.ops.screen.screenshot(filepath=path)
        print("ALD UI SHOT", path, os.path.exists(path))
    except Exception as exc:
        print("ALD UI SHOT FAILED", name, exc)


def find_area(kind):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == kind:
                return window, area
    return None, None


def maximize(area):
    window = bpy.context.window_manager.windows[0]
    for region in area.regions:
        if region.type == "WINDOW":
            with bpy.context.temp_override(window=window, area=area,
                                           region=region):
                bpy.ops.screen.screen_full_area()
            return True
    return False


def scroll(area, steps):
    """Scroll a Properties-style editor with the view2d operator."""
    window = bpy.context.window_manager.windows[0]
    for region in area.regions:
        if region.type != "WINDOW":
            continue
        try:
            with bpy.context.temp_override(window=window, area=area,
                                           region=region):
                for _ in range(abs(int(steps))):
                    if steps > 0:
                        bpy.ops.view2d.scroll_down()
                    else:
                        bpy.ops.view2d.scroll_up()
            return True
        except Exception as exc:
            print("ALD UI SCROLL FAILED", exc)
    return False


def check_fx_absent():
    for name in ("fx_fireworks", "fx_meteors", "clouds_create",
                 "smoke_create", "fx_render_shot"):
        if hasattr(bpy.ops.ald, name):
            print("ALD UI RETIRED OP PRESENT", name)
            return False
    print("ALD UI RETIRED OPS ABSENT")
    return True


def step():
    STATE["step"] += 1
    index = STATE["step"]
    out_dir = STATE["out"]
    try:
        if index == 1:
            try:
                bpy.ops.preferences.addon_enable(module=MODULE)
            except Exception as exc:
                print("ALD UI ENABLE FAILED", exc)
            scene = bpy.context.scene
            if scene.camera is None:
                data = bpy.data.cameras.new("ALD UI Camera")
                data.lens = 32.0
                cam = bpy.data.objects.new("ALD UI Camera", data)
                scene.collection.objects.link(cam)
                cam.location = (0.0, -12.0, 3.0)
                cam.rotation_euler = (1.75, 0.0, 0.45)
                scene.camera = cam
            scene.ald.palette = "AFTER_SCHOOL"
            bpy.ops.ald.apply_palette()
            if not len(scene.ald.shooting_star_events):
                star = scene.ald.shooting_star_events.add()
                star.name = "UI Shooting Star"
                star.start_frame = 1
                star.duration = 24
            from anime_look_director import look
            look.apply_world(scene)
            check_fx_absent()
            window, area = find_area("PROPERTIES")
            if area is not None:
                area.spaces.active.context = "SCENE"
                maximize(area)
            print("ALD UI STEP 1: the Scene properties are maximised")
            return STATE["wait"]
        if index == 2:
            shot(out_dir, "ui_properties.png")
            window, area = find_area("PROPERTIES")
            if area is not None:
                scroll(area, 18)
            print("ALD UI STEP 2: the properties were scrolled down")
            return 1.0
        if index == 3:
            shot(out_dir, "ui_properties_lower.png")
            window, area = find_area("PROPERTIES")
            if area is not None:
                scroll(area, 120)
            print("ALD UI STEP 3: the properties were scrolled down")
            return 1.0
        if index == 4:
            shot(out_dir, "ui_compositor.png")
            window, area = find_area("PROPERTIES")
            if area is not None:
                scroll(area, -120)
                # Toggle the full-area view off: the 3D view must exist again.
                maximize(area)
            window, area = find_area("VIEW_3D")
            if area is not None:
                area.spaces.active.show_region_ui = True
                area.tag_redraw()
            print("ALD UI STEP 4: the sidebar was opened")
            return 1.5
        if index == 5:
            window, area = find_area("VIEW_3D")
            if area is not None:
                try:
                    for region in area.regions:
                        if region.type == "UI":
                            region.active_panel_category = "Anime Look"
                except Exception as exc:
                    print("ALD UI SIDEBAR CATEGORY FAILED", exc)
                area.tag_redraw()
            shot(out_dir, "ui_sidebar.png")
            print("ALD UI STEP 5: done")
            return 1.0
        if index == 6:
            print("ALD UI QUIT")
            bpy.ops.wm.quit_blender()
            return None
    except Exception as exc:
        print("ALD UI STEP FAILED", index, exc)
        bpy.app.timers.register(
            lambda: bpy.ops.wm.quit_blender(), first_interval=1.0)
        return None
    return None


def main():
    out_dir, wait = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    STATE["out"] = out_dir
    STATE["wait"] = wait
    bpy.app.timers.register(step, first_interval=1.5)
    print("ALD UI PROBE STARTED", out_dir, "wait", wait)


if __name__ == "__main__":
    main()
