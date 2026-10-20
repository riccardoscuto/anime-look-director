"""Render every palette on a fixed look-dev scene.

Usage:
  blender -b --factory-startup --python preset_dev/lookdev.py -- [--out DIR]

Outputs one PNG per palette plus a contact sheet and prints image stats.
This is a development tool: it never saves a .blend.
"""

import os
import sys
import tempfile

import bpy
import numpy as np

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTES = ("GOLDEN_HOUR", "AFTER_SCHOOL", "SUMMER_NOON", "RAINY_TOKYO",
            "NEON_NIGHT", "SAKURA_SPRING", "TWILIGHT_DUSK")


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    out = os.path.join(tempfile.gettempdir(), "ald_lookdev")
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
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    scene = bpy.context.scene
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.eevee.taa_render_samples = 32

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "Lookdev Ground"
    ground.data.materials.append(make_material(
        "Lookdev Ground", (0.48, 0.42, 0.35), roughness=0.9))

    colors = ((0.82, 0.78, 0.70), (0.62, 0.22, 0.13), (0.08, 0.38, 0.42))
    for index, color in enumerate(colors):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.85, segments=48, ring_count=24,
            location=(-2.2 + index * 2.2, 0.2, 0.85))
        sphere = bpy.context.object
        sphere.name = "Lookdev Sphere %d" % index
        sphere.data.materials.append(make_material(
            "Lookdev Sphere %d" % index, color,
            roughness=0.3 if index != 1 else 0.65))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.4, 5.5, 2.0))
    backdrop = bpy.context.object
    backdrop.name = "Lookdev Backdrop"
    backdrop.scale = (5.5, 0.25, 2.0)
    backdrop.data.materials.append(make_material(
        "Lookdev Backdrop", (0.55, 0.55, 0.58), roughness=0.7))

    camera_data = bpy.data.cameras.new("Lookdev Camera")
    camera_data.lens = 35
    camera = bpy.data.objects.new("Lookdev Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (6.0, -10.5, 2.2)
    scene.camera = camera
    target = bpy.data.objects.new("Lookdev Target", None)
    target.location = (0, 0, 2.4)
    scene.collection.objects.link(target)
    track = camera.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    sun_data = bpy.data.lights.new("Lookdev Sun", "SUN")
    sun_data.energy = 4.0
    sun_data.angle = 0.08
    sun = bpy.data.objects.new("Lookdev Sun", sun_data)
    sun.rotation_euler = (0.95, 0.1, -0.75)
    scene.collection.objects.link(sun)
    return scene


def make_material(name, color, roughness=0.5):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = mat.node_tree.nodes.get("Material Output")
        if output is None:
            output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def render_stats(path):
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(image)
    luminance = pixels.mean(axis=1)
    saturation = (pixels.max(axis=1) - pixels.min(axis=1)).mean()
    return {
        "luma": round(float(luminance.mean()), 4),
        "contrast": round(float(luminance.std()), 4),
        "saturation": round(float(saturation), 4),
    }


def load_rgba(path):
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    bpy.data.images.remove(image)
    return pixels


def make_sheet(paths, out_path):
    width, height = 800, 450
    columns = 4
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
    image = bpy.data.images.new("ALD Lookdev Sheet", width * columns,
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
    settings = scene.ald

    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.dispersion_amount = 0.01
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.shadow_tint_distance = 0.6
    settings.ink_lines = True
    settings.ink_strength = 0.6
    settings.ink_size = 1.5
    settings.depth_near = 4.0
    settings.depth_far = 35.0

    paths = []
    for index, key in enumerate(PALETTES):
        settings.palette = key
        bpy.ops.ald.apply_palette()
        bpy.ops.ald.build()
        path = os.path.join(out_dir, "%d_%s.png" % (index, key.lower()))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print("ALD LOOKDEV", key, render_stats(path))

    sheet_path = os.path.join(out_dir, "sheet.png")
    make_sheet(paths, sheet_path)
    print("ALD LOOKDEV SHEET", sheet_path)


if __name__ == "__main__":
    main()
