"""Render the preset identity review boards.

Two modes:
  gradients - fixed neutral sun, clouds/stars/disk off, identical conditions.
  sun       - native Sun, clouds/stars off, wide sky camera with horizon.

Usage:
  blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 \
      --python preset_dev/preset_identity.py -- --mode gradients --out <dir>
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(HERE)
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lookdev  # noqa: E402
from anime_look_director import palette  # noqa: E402

LABELS = {
    "GOLDEN_HOUR": "Golden Hour",
    "AFTER_SCHOOL": "After School",
    "SUMMER_NOON": "Summer Noon",
    "RAINY_TOKYO": "Rainy Tokyo",
    "NEON_NIGHT": "Neon Night",
    "SAKURA_SPRING": "Sakura Spring",
    "TWILIGHT_DUSK": "Twilight Dusk",
    "SOFT_DAWN": "Soft Dawn",
    "BLUE_HOUR": "Blue Hour",
    "CLOUDY_AFTERNOON": "Cloudy Afternoon",
    "STORMY_SUNSET": "Stormy Sunset",
    "MOONLIT_NIGHT": "Moonlit Night",
}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    mode = "gradients"
    out = os.path.join(HERE, "preset_identity", "gradients")
    for index, item in enumerate(argv):
        if item == "--mode" and index + 1 < len(argv):
            mode = argv[index + 1]
        elif item == "--out" and index + 1 < len(argv):
            out = argv[index + 1]
    return mode, os.path.abspath(out)


def gradient_node(scene):
    return palette._gradient_node(scene.world.node_tree)


def remove_scene_sun(scene):
    for obj in list(scene.objects):
        if (obj.type == "LIGHT" and obj.data is not None
                and obj.data.type == "SUN"):
            bpy.data.objects.remove(obj, do_unlink=True)


def set_static_sun(scene):
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    if sun is None:
        return
    sun.rotation_euler = (0.95, 0.10, -0.75)
    sun.data.energy = 4.0
    sun.data.color = (1.0, 0.95, 0.90)
    sun.data.angle = 0.08


def hide_clouds_stars_disk(scene, disk=False):
    settings = scene.ald
    settings.clouds = False
    settings.stars = False
    settings.contrails = 0.0
    settings.sun_disk = disk
    settings.sun_glow_enabled = disk
    node = gradient_node(scene)
    if node is not None:
        node.inputs["Cloud Amount"].default_value = 0.0
        node.inputs["Star Amount"].default_value = 0.0
        node.inputs["Contrails"].default_value = 0.0
        if not disk:
            node.inputs["Sun Strength"].default_value = 0.0
            node.inputs["Sun Glow"].default_value = 0.0
        direction = palette.sun_toward(scene)
        if direction is not None:
            node.inputs["Sun Direction"].default_value = direction
            sun = next((o for o in scene.objects
                        if o.type == "LIGHT" and o.data is not None
                        and o.data.type == "SUN"), None)
            if sun is not None:
                node.inputs["Sun Color"].default_value = (
                    *sun.data.color, 1.0)


def camera_aim(camera, azimuth, elevation):
    az = math.radians(azimuth)
    el = math.radians(elevation)
    direction = Vector((math.cos(el) * math.sin(az),
                        math.cos(el) * math.cos(az),
                        math.sin(el))).normalized()
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_camera(scene, lens=14.0, location=(0.0, -14.0, 2.2)):
    data = bpy.data.cameras.new("Preset Identity Camera")
    data.lens = lens
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Preset Identity Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    scene.camera = camera
    return camera


def board(paths, out_path, title, footer):
    from PIL import Image, ImageDraw, ImageFont
    images = [Image.open(path).convert("RGB") for path in paths]
    width, height = images[0].size
    title_h, header, foot = 46, 34, 30
    board = Image.new("RGB", (width * 4 + 24, title_h + (height + header) * 3 + foot),
                      (18, 18, 18))
    try:
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
        label_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 17)
        small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 13)
    except OSError:
        title_font = label_font = small = ImageFont.load_default()
    for index, (path, key) in enumerate(zip(images, LABELS)):
        col, row = index % 4, index // 4
        x = col * (width + 8)
        y = title_h + row * (height + header) + header
        board.paste(path, (x, y))
        draw = ImageDraw.Draw(board)
        draw.text((x + 8, y - 27),
                  "%02d  %s" % (index + 1, LABELS[key]),
                  font=label_font, fill=(235, 235, 235))
    draw = ImageDraw.Draw(board)
    draw.text((8, 10), title, font=title_font, fill=(240, 240, 240))
    draw.text((8, board.height - 22), footer, font=small, fill=(180, 180, 180))
    board.save(out_path)


def main():
    mode, out = parse_args()
    os.makedirs(out, exist_ok=True)
    lookdev.build_scene()
    lookdev.enable_addon()
    scene = bpy.context.scene
    # The lookdev sun is a user sun; remove it so the native board exercises
    # the preset's own ALD sun instead of the fixed lookdev light.
    remove_scene_sun(scene)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 800
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    settings = scene.ald
    paths = []
    metrics = {}
    if mode == "gradients":
        set_static_sun(scene)
        for obj in scene.objects:
            if obj.type == "MESH":
                obj.hide_render = True
        camera = make_camera(scene, lens=16.0, location=(0.0, -10.0, 2.0))
        camera_aim(camera, 120.0, 45.0)
    if mode == "sun":
        camera = make_camera(scene)
    for key in lookdev.PALETTES:
        settings.palette = key
        bpy.ops.ald.apply_palette()
        if mode == "gradients":
            set_static_sun(scene)
            hide_clouds_stars_disk(scene, disk=False)
        elif mode == "sun":
            settings.clouds = False
            settings.stars = False
            settings.contrails = 0.0
            node = gradient_node(scene)
            if node is not None:
                node.inputs["Cloud Amount"].default_value = 0.0
                node.inputs["Star Amount"].default_value = 0.0
                node.inputs["Contrails"].default_value = 0.0
            direction = palette.sun_toward(scene)
            if direction is not None:
                sun_az = math.degrees(math.atan2(direction[0], direction[1]))
                sun_el = math.degrees(math.asin(max(-1.0, min(1.0, direction[2]))))
                camera_aim(camera, sun_az, max(0.0, sun_el * 0.3))
        # clouds mode leaves the native sun, clouds and stars untouched.
        path = os.path.join(out, "%02d_%s.png" % (lookdev.PALETTES.index(key) + 1,
                                                   key.lower()))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        metrics[key] = lookdev.render_stats(path)
        print("PRESET", mode, key, metrics[key])
    try:
        board(paths, os.path.join(out, "board.png"),
              "Anime Look Director 2.63.0 - preset identity: %s" % mode,
              "Fixed lookdev scene. %s" % (
                  "Sky-only gradient, identical neutral sun."
                  if mode == "gradients"
                  else ("Native Sun per preset; wide camera with horizon."
                        if mode == "sun"
                        else "Native Sun, clouds and stars; original lookdev camera.")))
    except Exception as exc:
        print("BOARD_SKIP", exc)
    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump({"mode": mode, "presets": metrics}, handle, indent=2)
    print("PRESET BOARD", mode, os.path.join(out, "board.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
