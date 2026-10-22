"""UI verification: screenshot the Anime Look Director panels.

Usage:
  blender --factory-startup --python preset_dev/ui_probe.py -- [--out DIR]

Opens a fresh Blender, enables the add-on, creates the FX systems and writes
the screenshots of the sidebar panel and of the Scene properties (Anime Look
Director, World & Shadows, Compositor Stack and FX Particles).

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
    out = os.path.join(tempfile.gettempdir(), "ald_ui")
    wait = 10.0
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
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


def step():
    STATE["step"] += 1
    index = STATE["step"]
    out_dir = STATE["out"]
    if index == 1:
        try:
            bpy.ops.preferences.addon_enable(module=MODULE)
        except Exception as exc:
            print("ALD UI ENABLE FAILED", exc)
        try:
            bpy.ops.ald.fx_fireworks(count=3, age=0.8)
            bpy.ops.ald.fx_meteors(count=4, age=0.6)
        except Exception as exc:
            print("ALD UI FX FAILED", exc)
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
            maximize(area)
        window, area = find_area("VIEW_3D")
        if area is not None:
            for region in area.regions:
                if region.type == "UI":
                    region.active_panel_category = "Anime Look"
            area.tag_redraw()
        print("ALD UI STEP 2: the sidebar panel is on the Anime Look category")
        return 1.5
    if index == 3:
        shot(out_dir, "ui_sidebar.png")
        print("ALD UI STEP 3: done")
        return 1.0
    if index == 4:
        print("ALD UI QUIT")
        bpy.ops.wm.quit_blender()
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
