"""P0 baseline: a single Chrysanthemum, three comparable renders.

Produces, at 800x450 and 1920x1080:
  emission_<res>.png  the FX emission on a black world, no compositor
  glow_<res>.png      the same emission with the dedicated FX Glare only
  full_<res>.png      the World anime look with the complete compositor

The three images separate geometry defects (emission), shading/glow defects
(glow) and compositing defects (full). The camera, seed, frame, exposure and
view transform are recorded in metadata.json, together with the git commit and
the measured creation / evaluation / render times.

This is a development tool: it never saves a .blend.

Run (from the add-on directory)::

    blender -b --factory-startup --python preset_dev/baseline_fx.py -- [--out DIR]
"""

import json
import os
import subprocess
import sys
import time

import bpy
from mathutils import Vector

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 13
DISTANCE = 55.0
FAMILY = "CHRYSANTHEMUM"
RESOLUTIONS = ((800, 450), (1920, 1080))
AGE_AFTER_BURST = 0.4


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(ADDON_PATH, "preset_dev", "baseline_fx")
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


def commit_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ADDON_PATH,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def build_scene(scene):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.0

    camera_data = bpy.data.cameras.new("Baseline Camera")
    camera_data.lens = 32.0
    camera_data.clip_start = 0.1
    camera_data.clip_end = 1000.0
    camera = bpy.data.objects.new("Baseline Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    camera.rotation_euler = (1.92, 0.0, 0.0)
    scene.camera = camera
    return scene, camera


def black_world():
    world = bpy.data.worlds.get("ALD | Baseline Black")
    if world is None:
        world = bpy.data.worlds.new("ALD | Baseline Black")
        world.use_nodes = True
        tree = world.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputWorld")
        background = tree.nodes.new("ShaderNodeBackground")
        background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        background.inputs["Strength"].default_value = 0.0
        tree.links.new(background.outputs["Background"],
                       output.inputs["Surface"])
    return world


def hide_non_fx(scene, hidden):
    for obj in scene.objects:
        if obj.get("ald_fx") or obj.type in ("CAMERA", "LIGHT"):
            continue
        hidden.append((obj, obj.hide_render))
        obj.hide_render = True


def restore_hidden(hidden):
    for obj, state in hidden:
        obj.hide_render = state
    hidden.clear()


def glow_only_compositor(scene, settings):
    """A temporary compositor: FX Render Layers -> Glare -> Output."""
    group = bpy.data.node_groups.new("ALD | Baseline Glow",
                                     "CompositorNodeTree")
    group.interface.new_socket(name="Image", in_out="OUTPUT",
                               socket_type="NodeSocketColor")
    render = group.nodes.new("CompositorNodeRLayers")
    render.scene = scene
    render.layer = scene.view_layers[0].name
    glare = group.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Threshold"].default_value = float(
        getattr(settings, "fx_glow_threshold", 0.35))
    glare.inputs["Strength"].default_value = float(
        getattr(settings, "fx_glow_strength", 0.6))
    if "Size" in glare.inputs:
        glare.inputs["Size"].default_value = float(
            getattr(settings, "fx_glow_size", 0.7))
    output = group.nodes.new("NodeGroupOutput")
    group.links.new(render.outputs["Image"], glare.inputs["Image"])
    group.links.new(glare.outputs["Glare"], output.inputs[0])
    scene.compositing_node_group = group
    scene.render.use_compositing = True
    return group


def render(scene, path):
    scene.render.filepath = path
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return time.perf_counter() - start


def main():
    out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    scene, camera = build_scene(None)
    enable_addon()
    from anime_look_director import fx

    settings = scene.ald
    settings.palette = "TWILIGHT_DUSK"
    settings.fx_age = 0.0
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.ink_lines = True
    settings.depth_near = 20.0
    settings.depth_far = 140.0
    settings.fx_gn_prototype = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()

    start = time.perf_counter()
    fx.create_fireworks(scene, 1, seed=SEED, distance=DISTANCE, time=0.0,
                        family=FAMILY)
    creation = time.perf_counter() - start
    # The stack must see the new FX collection: rebuild it now.
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    event = system.events[0]
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    frame = int(system.origin_frame
                + (event.birth + event.rise_time + AGE_AFTER_BURST) * fps)
    start = time.perf_counter()
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    evaluation = time.perf_counter() - start

    origin, forward, _up, _right = fx._camera_basis(scene)
    target = Vector(event.target)
    camera.rotation_euler = (target - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    bpy.context.view_layer.update()

    world = scene.world
    main_group = scene.compositing_node_group
    hidden = []
    data = {
        "plan": "P0 baseline FX",
        "commit": commit_hash(),
        "addon_version": list(sys.modules[MODULE].bl_info["version"])
        if MODULE in sys.modules else [],
        "blender": bpy.app.version_string,
        "engine": scene.render.engine,
        "fps": fps,
        "seed": SEED,
        "family": FAMILY,
        "distance": DISTANCE,
        "frame": frame,
        "system_time": round(fx.system_time(scene, system), 5),
        "age_after_burst": AGE_AFTER_BURST,
        "exposure": float(scene.view_settings.exposure),
        "view_transform": scene.view_settings.view_transform,
        "camera": {
            "location": [round(v, 4) for v in camera.location],
            "rotation_euler": [round(v, 4) for v in camera.rotation_euler],
            "lens": camera.data.lens,
            "clip_start": camera.data.clip_start,
            "clip_end": camera.data.clip_end,
        },
        "timings": {"creation_s": round(creation, 5),
                    "evaluation_s": round(evaluation, 5)},
        "renders": [],
    }

    try:
        # 1. Emission only: black world, non-FX objects hidden, no compositor.
        scene.world = black_world()
        scene.render.use_compositing = False
        hide_non_fx(scene, hidden)
        for width, height in RESOLUTIONS:
            scene.render.resolution_x = width
            scene.render.resolution_y = height
            name = "emission_%dx%d.png" % (width, height)
            elapsed = render(scene, os.path.join(out_dir, name))
            data["renders"].append({"pass": "emission", "file": name,
                                    "resolution": [width, height],
                                    "render_s": round(elapsed, 5)})

        # 2. Glow only: the FX image through the dedicated Glare.
        glow_group = glow_only_compositor(scene, settings)
        for width, height in RESOLUTIONS:
            scene.render.resolution_x = width
            scene.render.resolution_y = height
            name = "glow_%dx%d.png" % (width, height)
            elapsed = render(scene, os.path.join(out_dir, name))
            data["renders"].append({"pass": "glow", "file": name,
                                    "resolution": [width, height],
                                    "render_s": round(elapsed, 5)})
        scene.compositing_node_group = main_group
        bpy.data.node_groups.remove(glow_group)

        # 3. Full: World anime + complete compositor.
        restore_hidden(hidden)
        scene.world = world
        scene.render.use_compositing = True
        for width, height in RESOLUTIONS:
            scene.render.resolution_x = width
            scene.render.resolution_y = height
            name = "full_%dx%d.png" % (width, height)
            elapsed = render(scene, os.path.join(out_dir, name))
            data["renders"].append({"pass": "full", "file": name,
                                    "resolution": [width, height],
                                    "render_s": round(elapsed, 5)})
    finally:
        restore_hidden(hidden)
        scene.world = world
        scene.compositing_node_group = main_group
        scene.render.use_compositing = True

    metadata = os.path.join(out_dir, "metadata.json")
    with open(metadata, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("ALD BASELINE FX:", out_dir)
    print(json.dumps(data["timings"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
