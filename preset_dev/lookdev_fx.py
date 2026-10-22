"""Render the FX comparison sheets required by the technical guide.

Usage:
  blender -b --factory-startup --python preset_dev/lookdev_fx.py -- [--out DIR]

Outputs:
  fx_noglow.png     the burst without the dedicated FX glow
  fx_glow.png       the burst with the dedicated FX glow
  fx_occluder.png   the burst hidden behind a building
  fx_motionblur.png the burst with motion blur enabled
  seq_XX.png        a short animated sequence of the burst
  sheet.png         a contact sheet of the stills
  metadata.json     resolution, camera, seed, exposure, view transform, engine

This is a development tool: it never saves a .blend.
"""

import json
import os
import sys
import tempfile

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 7
DISTANCE = 60.0
COUNT = 4
SEQUENCE_FRAMES = (1, 14, 24, 30, 40, 56)
#: The burst happens at the end of the rise: the stills show the expansion.
STILL_FRAME = 44


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(tempfile.gettempdir(), "ald_lookdev_fx")
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


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = 24
    scene.view_settings.view_transform = "AgX"
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass

    camera_data = bpy.data.cameras.new("FX Lookdev Camera")
    camera_data.lens = 32.0
    camera = bpy.data.objects.new("FX Lookdev Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -12.0, 3.0)
    # Look up into the sky where the bursts are born.
    camera.rotation_euler = (1.92, 0.0, 0.0)
    scene.camera = camera
    return scene


def apply_look(scene, palette="TWILIGHT_DUSK"):
    settings = scene.ald
    settings.palette = palette
    # The event starts at the first frame: the sequence shows the launch, the
    # rise, the burst and the fade.
    settings.fx_age = 0.0
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.ink_lines = True
    settings.ink_strength = 0.6
    settings.ink_size = 1.5
    settings.depth_near = 20.0
    settings.depth_far = 140.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()


def make_occluder(scene, camera):
    """A building between the camera and the burst."""
    from anime_look_director import fx as fx_module
    from mathutils import Vector
    origin, forward, up, right = fx_module._camera_basis(scene)
    center = fx_module._burst_center(origin, forward, up, right, 0, COUNT,
                                     DISTANCE,
                                     scene.ald.fx_burst_spread)
    direction = (center - origin).normalized()
    bpy.ops.mesh.primitive_cube_add(size=11.0,
                                    location=tuple(origin + direction * 26.0))
    cube = bpy.context.object
    cube.name = "FX Lookdev Building"
    cube.rotation_euler = (-direction).to_track_quat("Z", "Y").to_euler()
    material = bpy.data.materials.new("FX Lookdev Building")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.13, 0.16, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
    cube.data.materials.append(material)
    return cube


def render(scene, path, frame=None):
    if frame is not None:
        scene.frame_set(frame)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def load_rgba(path):
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    bpy.data.images.remove(image)
    return pixels


def make_sheet(paths, out_path, width=800, height=450, columns=3):
    rows = max(1, (len(paths) + columns - 1) // columns)
    sheet = np.zeros((height * rows, width * columns, 4), dtype=np.float32)
    sheet[..., 3] = 1.0
    for index, path in enumerate(paths):
        pixels = load_rgba(path).reshape(height, width, 4)
        # Blender image rows start at the bottom: first row on top.
        row = rows - 1 - index // columns
        col = index % columns
        sheet[row * height:(row + 1) * height,
              col * width:(col + 1) * width] = pixels
    image = bpy.data.images.new("ALD FX Sheet", width * columns,
                                height * rows, alpha=True, float_buffer=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = out_path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def main():
    out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    build_scene()
    enable_addon()
    scene = bpy.context.scene
    camera = scene.camera

    # The sequence starts at the birth of the burst.
    bpy.ops.ald.fx_fireworks(count=COUNT, age=0.0, seed=SEED,
                             distance=DISTANCE)
    apply_look(scene)

    stills = []
    sequence = []
    for frame in SEQUENCE_FRAMES:
        path = os.path.join(out_dir, "seq_%02d.png" % frame)
        render(scene, path, frame)
        sequence.append(path)

    # Without the dedicated FX glow.
    scene.ald.fx_glow_strength = 0.0
    path = render(scene, os.path.join(out_dir, "fx_noglow.png"), STILL_FRAME)
    stills.append(path)

    # With the dedicated FX glow.
    scene.ald.fx_glow_strength = 0.6
    path = render(scene, os.path.join(out_dir, "fx_glow.png"), STILL_FRAME)
    stills.append(path)

    # The burst hidden behind a building.
    cube = make_occluder(scene, camera)
    path = render(scene, os.path.join(out_dir, "fx_occluder.png"), STILL_FRAME)
    stills.append(path)
    bpy.data.objects.remove(cube, do_unlink=True)

    # Motion blur: the topology is stable, the trail must stay coherent.
    try:
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = 0.5
    except Exception:
        pass
    path = render(scene, os.path.join(out_dir, "fx_motionblur.png"), STILL_FRAME)
    stills.append(path)
    try:
        scene.render.use_motion_blur = False
    except Exception:
        pass

    sheet_path = os.path.join(out_dir, "sheet.png")
    make_sheet(stills, sheet_path)
    sequence_sheet = os.path.join(out_dir, "sequence.png")
    make_sheet(sequence, sequence_sheet, columns=len(sequence))

    metadata = {
        "renderer": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "resolution_percentage": scene.render.resolution_percentage,
        "fps": scene.render.fps,
        "frame_range": [min(SEQUENCE_FRAMES), max(SEQUENCE_FRAMES)],
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
        "gamma": scene.view_settings.gamma,
        "palette": scene.ald.palette,
        "camera": {
            "name": camera.name,
            "location": [round(value, 4) for value in camera.location],
            "rotation_euler": [round(value, 4)
                               for value in camera.rotation_euler],
            "lens": camera.data.lens,
        },
        "fx": {
            "backend": scene.ald.fx_backend,
            "geometry_nodes": scene.ald.fx_gn_prototype,
            "count": COUNT,
            "seed": SEED,
            "distance": DISTANCE,
            "age": scene.ald.fx_age,
            "spread": scene.ald.fx_burst_spread,
            "composition_offset": list(scene.ald.fx_composition_offset),
            "glow_strength": 0.6,
            "glow_size": scene.ald.fx_glow_size,
        },
        "compositor": {
            "painterly": scene.ald.painterly,
            "kuwahara_size": scene.ald.kuwahara_size,
            "ink_lines": scene.ald.ink_lines,
            "halation_strength": scene.ald.halation_strength,
        },
        "outputs": {
            "stills": [os.path.basename(path) for path in stills],
            "sequence": [os.path.basename(path) for path in sequence],
            "sheet": os.path.basename(sheet_path),
            "sequence_sheet": os.path.basename(sequence_sheet),
        },
    }
    meta_path = os.path.join(out_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print("ALD FX LOOKDEV SHEET", sheet_path)
    print("ALD FX LOOKDEV METADATA", meta_path)
    for path in stills + sequence:
        print("   ", os.path.basename(path))


if __name__ == "__main__":
    main()
