"""Numeric check of the premultiplied Moon composition.

Renders a constant World through the shared `over_color` helper and compares
the linear result with C_moon + (1 - alpha) * C_sky at alpha 0.25/0.50/0.75.

    blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
        --python preset_dev/moon_alpha_check.py
"""

import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)

from anime_look_director.palette import over_color  # noqa: E402

OUT = os.path.join(HERE, "moon", "phases", "check")
SKY = 0.30
MOON = 0.80
ALPHAS = (0.25, 0.50, 0.75)


def build_world():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 1
    scene.render.resolution_x = 8
    scene.render.resolution_y = 8
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    camera_data = bpy.data.cameras.new("Alpha Camera")
    camera = bpy.data.objects.new("Alpha Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 5.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = camera

    world = bpy.data.worlds.new("Alpha World")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 1.0
    sky = nodes.new("ShaderNodeRGB")
    sky.outputs[0].default_value = (SKY, SKY, SKY, 1.0)
    moon = nodes.new("ShaderNodeRGB")
    moon.outputs[0].default_value = (MOON, MOON, MOON, 1.0)
    alpha = nodes.new("ShaderNodeValue")
    alpha.outputs[0].default_value = 0.5
    premult = nodes.new("ShaderNodeVectorMath")
    premult.operation = "SCALE"
    links.new(moon.outputs[0], premult.inputs[0])
    links.new(alpha.outputs[0], premult.inputs["Scale"])
    color = over_color(nodes, links, sky.outputs[0],
                       premult.outputs["Vector"], alpha.outputs[0],
                       (300, 0))
    links.new(color, background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    return scene, alpha


def render_linear(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = list(image.pixels[:])
    bpy.data.images.remove(image)
    values = [pixels[i] for i in range(0, len(pixels), 4)]
    return sum(values) / len(values)


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, alpha = build_world()
    rows = []
    for value in ALPHAS:
        alpha.outputs[0].default_value = value
        path = os.path.join(OUT, "alpha_%03d.exr" % int(value * 100))
        measured = render_linear(scene, path)
        expected = MOON * value + SKY * (1.0 - value)
        mix_style = SKY * (1.0 - value) + MOON * value * value
        rows.append({
            "alpha": value,
            "expected": round(expected, 4),
            "measured": round(measured, 4),
            "error": round(abs(measured - expected), 5),
            "old_mix_value": round(mix_style, 4),
            "passed": abs(measured - expected) < 0.005,
        })
        print("ALPHA", value, rows[-1])
    passed = all(row["passed"] for row in rows)
    with open(os.path.join(OUT, "alpha_check.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"sky": SKY, "moon": MOON, "rows": rows,
                   "passed": passed}, fh, indent=2)
    print("ALPHA CHECK", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
