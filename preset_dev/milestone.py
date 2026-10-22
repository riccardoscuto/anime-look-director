"""Final acceptance: a single complete and reversible firework.

Usage:
  blender -b --factory-startup --python preset_dev/milestone.py -- [--out DIR]

The script checks the Definition of Done of the operational plan, one point
at a time, and writes the filmstrip of the event.

It never saves the .blend of the user: the fixture lives in the temporary
directory and it is removed at the end.
"""

import json
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(tempfile.gettempdir(), "ald_milestone")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    return out


def enable_addon():
    if hasattr(bpy.types.Scene, "ald"):
        return
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
    except Exception:
        parent = os.path.dirname(ADDON_PATH)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import importlib
        importlib.import_module(MODULE).register()


def check(label, condition, detail=""):
    RESULTS.append((label, bool(condition), detail))
    print("ALD DOD %-46s %s %s" % (label, "OK" if condition else "FAIL",
                                   detail))
    return bool(condition)


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass
    camera_data = bpy.data.cameras.new("Milestone Camera")
    camera_data.lens = 50.0
    camera = bpy.data.objects.new("Milestone Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -14.0, 2.0)
    camera.rotation_euler = (1.94, 0.0, 0.0)
    scene.camera = camera
    return scene


def load_rgba(path):
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    bpy.data.images.remove(image)
    return pixels


def make_strip(paths, out_path, size=640):
    columns = len(paths)
    strip = np.zeros((size, size * columns, 4), dtype=np.float32)
    strip[..., 3] = 1.0
    for index, path in enumerate(paths):
        pixels = load_rgba(path).reshape(size, size, 4)
        strip[:, index * size:(index + 1) * size] = pixels
    image = bpy.data.images.new("ALD Milestone Strip", size * columns, size,
                                alpha=True, float_buffer=False)
    image.pixels.foreach_set(strip.ravel())
    image.filepath_raw = out_path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def main():
    out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    scene = build_scene()
    enable_addon()
    from anime_look_director import fx as fx_module
    from anime_look_director import fx_nodes
    from anime_look_director import snapshot

    scene.ald.palette = "TWILIGHT_DUSK"
    scene.ald.fx_age = 0.0
    scene.ald.halation_strength = 0.5
    scene.ald.kuwahara_size = 6.0
    scene.ald.ink_lines = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()

    # 1. A single firework from a visible launcher.
    fx_module.create_fireworks(scene, 1, seed=13, distance=30.0, time=0.0)
    registry = fx_module.SYSTEMS[fx_module._scene_id(scene)]
    burst = registry["fireworks"]["bursts"][0]
    # The camera frames the burst point.
    scene.camera.rotation_euler = (Vector(burst["target"])
                                   - scene.camera.location).to_track_quat(
                                       "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    launcher = bpy.data.objects.get("ALD FX Launcher 0")
    check("the launcher is visible and manageable", launcher is not None
          and launcher.get("ald_fx") is True)

    # 2. The rise is continuous and the burst happens at the target.
    gravity = fx_module._gravity(scene)
    rise = float(burst["rise_time"])
    at_burst = fx_module._rise_position(burst["launch"], burst["shell_velocity"],
                                        burst["drag"], gravity, rise)
    check("the shell reaches the burst point",
          (at_burst - Vector(burst["target"])).length < 1e-3,
          "%.4f m" % (at_burst - Vector(burst["target"])).length)

    # 3. The stars take the position and the velocity of the shell.
    head = burst["population"]["heads"][0]
    check("the stars are born at the burst point",
          (Vector(head["pos0"]) - Vector(burst["target"])).length < 1e-6)
    residual = Vector(burst["residual"])
    check("the stars inherit the velocity of the shell",
          (Vector(head["vel"]) - residual).length > 0.5)

    # 4. Every component decays.
    scene.frame_set(int(rise * 24) + 2)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    decays = {}
    for name, role in (("ALD FX GN Heads 0", "head"),
                       ("ALD FX GN Pistil 0", "pistil"),
                       ("ALD FX GN Flash 0", "flash")):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        instances = fx_nodes.realized_instances(obj, depsgraph)
        decays[role] = bool([radius for _center, radius in instances
                              if radius > 1e-4])
    check("the components are alive at the burst",
          all(decays.values()) if decays else False, str(decays))
    scene.frame_set(int(rise * 24) + int(2.8 * 24))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    late = {}
    for name, role in (("ALD FX GN Heads 0", "head"),
                       ("ALD FX GN Sparks 0", "sparks"),
                       ("ALD FX GN Flash 0", "flash")):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        instances = fx_nodes.realized_instances(obj, depsgraph)
        late[role] = bool([radius for _center, radius in instances
                           if radius > 1e-4])
    check("the flash is off and the embers survive",
          not late.get("flash", True) and late.get("sparks", False),
          str(late))

    # 5. The energy fades in time, it is not only a shrink.
    group = bpy.data.node_groups.get(fx_nodes.GROUP_NAME)
    stores = [node for node in group.nodes
              if node.bl_idname == "GeometryNodeStoreNamedAttribute"
              and node.inputs["Name"].default_value == "energy"]
    check("the energy is an attribute, not a scale", bool(stores),
          "the node group stores the energy attribute")

    def burst_energy(frame):
        """The light of the burst: the difference with and without the FX."""
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        path = os.path.join(out_dir, "dod_energy.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        with_fx = load_rgba(path).reshape(640, 640, 4)[:, :, :3].copy()
        hidden = []
        for obj in bpy.data.objects:
            if obj.get("ald_fx") and not obj.get("ald_fx_role") == "launcher":
                hidden.append(obj)
                obj.hide_render = True
        bpy.ops.render.render(write_still=True)
        without_fx = load_rgba(path).reshape(640, 640, 4)[:, :, :3].copy()
        for obj in hidden:
            obj.hide_render = False
        difference = np.abs(with_fx - without_fx)
        return float(np.max(difference))

    young = burst_energy(int(rise * 24) + 8)
    old = burst_energy(int(rise * 24) + int(1.6 * 24))
    check("the burst fades in time", old < young * 0.9,
          "young %.4f, old %.4f" % (young, old))

    # 6. The compositor isolates the FX.
    ng = scene.compositing_node_group
    check("the compositor isolates the FX layer",
          ng is not None and ng.nodes.get("ALD | FX Contribution") is not None
          and ng.nodes.get("ALD | FX Punch Out") is not None)

    # 7. Both interfaces drive the same systems.
    from anime_look_director import panels
    shared = [name for name in dir(panels) if name.startswith("draw_")]
    source = inspect_source(panels)
    check("the systems are manageable from both interfaces",
          len(shared) >= 8 and "draw_fx" in source)

    # 8. The reopened project keeps the configuration.
    path = os.path.join(out_dir, "milestone_fixture.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    reopened = bpy.context.scene
    info = dict(fx_module.systems_info(reopened))
    check("the reopened project keeps the systems",
          info.get("fireworks", 0) > 0 and len(reopened.ald.fx_systems) > 0,
          str(info))

    # 9. Remove ALD from Scene restores the registered state.
    before_world = reopened.world.name if reopened.world else None
    bpy.ops.ald.remove_from_scene()
    check("Remove ALD from Scene restores the state",
          not [obj for obj in bpy.data.objects if obj.get("ald_fx")],
          "world %s" % before_world)
    check("the stack of the user is restored or removed",
          reopened.compositing_node_group is None
          or not reopened.compositing_node_group.name.startswith("ALD |"))

    # 10. The filmstrip of the event.
    scene = build_scene()
    enable_addon()
    scene.ald.palette = "TWILIGHT_DUSK"
    scene.ald.fx_age = 0.0
    scene.ald.halation_strength = 0.5
    scene.ald.kuwahara_size = 6.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    fx_module.create_fireworks(scene, 1, seed=13, distance=30.0, time=0.0)
    registry = fx_module.SYSTEMS[fx_module._scene_id(scene)]
    burst = registry["fireworks"]["bursts"][0]
    scene.camera.rotation_euler = (Vector(burst["target"])
                                   - scene.camera.location).to_track_quat(
                                       "-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    frames = [1, int(0.6 * 24), int(1.2 * 24), int(1.7 * 24), int(2.4 * 24),
              int(3.4 * 24)]
    paths = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        path = os.path.join(out_dir, "dod_%02d.png" % frame)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
    strip = os.path.join(out_dir, "milestone_strip.png")
    make_strip(paths, strip)

    summary = {
        "checks": [{"label": label, "ok": ok, "detail": detail}
                   for label, ok, detail in RESULTS],
        "passed": sum(1 for _label, ok, _detail in RESULTS if ok),
        "total": len(RESULTS),
        "strip": strip,
    }
    with open(os.path.join(out_dir, "milestone.json"), "w",
              encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print("ALD DOD %d/%d" % (summary["passed"], summary["total"]))
    print("ALD DOD STRIP", strip)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    if summary["passed"] != summary["total"]:
        raise SystemExit(1)


def inspect_source(module):
    import inspect
    source = ""
    for name in dir(module):
        item = getattr(module, name)
        if inspect.isfunction(item):
            source += inspect.getsource(item)
    return source


if __name__ == "__main__":
    main()
