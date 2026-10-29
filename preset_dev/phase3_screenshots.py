"""Capture Phase 3 UI screenshots in a GUI Blender.

Run from a GUI session with a config that has ``show_splash = False``:

    blender --python preset_dev/phase3_screenshots.py -- \
        --out <dir> --variant current --state inactive \
        --steps 0,10,20,30,40,50

Every step is a fresh scroll from the top. The compositor state is set before
the first draw so panel heights are stable.
"""

import json
import os
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

OUT = os.path.join(HERE, "phase3_ui_shots")
VARIANT = "current"
STATE = "inactive"
STEPS = (0, 10, 20, 30, 40, 50)
AREA_SHOT = False


def parse_args():
    global OUT, VARIANT, STATE, STEPS, AREA_SHOT
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            value = argv[index + 1]
            if item == "--out":
                OUT = value
            elif item == "--variant":
                VARIANT = value
            elif item == "--state":
                STATE = value
            elif item == "--steps":
                STEPS = tuple(int(v) for v in value.split(",") if v)
            elif item == "--area-shot":
                AREA_SHOT = True


def redraw(window, iterations=6):
    with bpy.context.temp_override(window=window, screen=window.screen):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=iterations)


def shot(window, name, area=None):
    path = os.path.join(OUT, "%s_%s.png" % (VARIANT, name))
    try:
        import ctypes
        ctypes.windll.user32.SetCursorPos(2, 2)
    except Exception:
        pass
    redraw(window)
    if AREA_SHOT and area is not None:
        region = next((r for r in area.regions if r.type in ("WINDOW", "UI")),
                      None)
        with bpy.context.temp_override(window=window, screen=window.screen,
                                       area=area, region=region):
            bpy.ops.screen.screenshot_area(filepath=path)
    else:
        with bpy.context.temp_override(window=window, screen=window.screen):
            bpy.ops.screen.screenshot(filepath=path)
    print("SHOT", path, flush=True)


def scroll(area, steps):
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    if region is None:
        raise RuntimeError("Properties has no WINDOW region")
    with bpy.context.temp_override(window=bpy.context.window,
                                   screen=bpy.context.window.screen,
                                   area=area, region=region):
        for _ in range(80):
            bpy.ops.view2d.scroll_up()
        for _ in range(steps):
            bpy.ops.view2d.scroll_down()


def setup_scene():
    from anime_look_director import compositor, look, palette
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    data = bpy.data.cameras.new("UI Shot Camera")
    data.lens = 32.0
    camera = bpy.data.objects.new("UI Shot Camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.75, 0.0, 0.45)
    scene.camera = camera
    scene.ald.palette = "NEON_NIGHT"
    palette.apply_palette(scene, "NEON_NIGHT")
    scene.ald.clouds = True
    scene.ald.stars = True
    look.apply_world(scene)
    event = scene.ald.shooting_star_events.add()
    event.name = "UI Shot Star"
    event.start_frame = 10
    event.duration = 24
    event.azimuth = 120.0
    event.elevation = 40.0
    event.direction = 35.0
    event.length = 18.0
    scene.ald.shooting_star_selected = 0
    if STATE in ("active", "disabled"):
        compositor.build(scene)
        scene.ald.halation = True
        scene.ald.light_wrap = True
        scene.ald.god_rays = True
        scene.ald.painterly = True
        scene.ald.ink_lines = True
        scene.ald.dispersion = True
        scene.ald.aerial_haze = True
        scene.render.use_compositing = STATE == "active"
        compositor.update_params(scene)
    look.apply_world(scene)


def _window_handle():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value != os.getpid():
        hwnd = user32.FindWindowW(None, "Blender")
    return user32, hwnd


def click_sidebar_tab(window, area, y=242):
    import ctypes
    from ctypes import wintypes
    user32, hwnd = _window_handle()
    if not hwnd:
        print("TAB_CLICK_NO_WINDOW", flush=True)
        return
    x = int(area.x + area.width - 8)
    point = wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    user32.SetForegroundWindow(hwnd)
    user32.SetCursorPos(point.x, point.y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    print("TAB_CLICK", x, y, point.x, point.y, flush=True)


def resize_window(width, height):
    user32, hwnd = _window_handle()
    if not hwnd:
        print("RESIZE_NO_WINDOW", flush=True)
        return
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, 0, 60, 40, width, height, 0x0004)
    print("RESIZE", width, height, flush=True)


def run():
    parse_args()
    os.makedirs(OUT, exist_ok=True)
    try:
        bpy.ops.preferences.addon_enable(module="anime_look_director")
    except Exception:
        pass
    from anime_look_director import compositor
    if STATE != "legacy":
        setup_scene()
    window = bpy.context.window_manager.windows[0]
    screen = window.screen
    area3d = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
    props = next((a for a in screen.areas if a.type == "PROPERTIES"), None)
    if area3d is None or props is None:
        raise RuntimeError("The default layout has no VIEW_3D/PROPERTIES")
    area3d.spaces.active.show_region_ui = True
    props.spaces.active.context = "SCENE"
    redraw(window, 8)
    ui_region = next((r for r in area3d.regions if r.type == "UI"), None)
    if ui_region is not None:
        try:
            with bpy.context.temp_override(window=window, screen=screen,
                                           area=area3d, region=ui_region):
                ui_region.active_panel_category = "Anime Look"
            print("TAB_SET", flush=True)
        except Exception as exc:
            print("TAB_SET_FAILED", exc, flush=True)
    click_sidebar_tab(window, area3d)
    redraw(window, 6)
    shot(window, "sidebar", area3d)
    for steps in STEPS:
        scroll(props, steps)
        shot(window, "props_%02d" % steps, props)
    stack = None
    if hasattr(compositor, "scene_stack"):
        stack = compositor.scene_stack(bpy.context.scene)
    else:
        stack = bpy.context.scene.compositing_node_group
    with open(os.path.join(OUT, VARIANT + ".json"), "w",
              encoding="utf-8") as handle:
        json.dump({"variant": VARIANT, "state": STATE,
                   "width": window.width, "height": window.height,
                   "steps": list(STEPS),
                   "stack": stack is not None,
                   "use_compositing":
                       bool(bpy.context.scene.render.use_compositing)},
                  handle, indent=2)
    print("PHASE3 SHOTS DONE", VARIANT, STATE)


def main():
    try:
        run()
    except Exception:
        traceback.print_exc()
        try:
            os.makedirs(OUT, exist_ok=True)
            with open(os.path.join(OUT, VARIANT + "_error.txt"), "w",
                      encoding="utf-8") as handle:
                handle.write(traceback.format_exc())
        except Exception:
            pass
    finally:
        bpy.app.timers.register(lambda: os._exit(0), first_interval=0.5)


if __name__ == "__main__":
    bpy.app.timers.register(main, first_interval=1.0)
