"""Final visual gate for cloud footprint candidate F.

Renders the F distribution at Cloud Amount 0.42 on the full hemisphere:
camera elevations 0/30/60/85 degrees, two azimuths, seeds 3/17/42, 1920x1080,
SUMMER_NOON, no compositor. Saves the look renders, binary masks and coverage.

    blender -b --factory-startup --python preset_dev/cloud_footprint_gate.py
"""

import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cloud_distribution_proto as proto  # noqa: E402
import cloud_footprint as fp  # noqa: E402

W, H = 2048, 1024
RW, RH = 1920, 1080
SEEDS = (3, 17, 42)
ELEVATIONS = (0, 30, 60, 85)
AZIMUTHS = (0, 90)
AMOUNT = 0.42


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    values = {"out": os.path.join(HERE, "cloud_footprint_gate"),
              "count": "184", "soft": "0.9"}
    for index, item in enumerate(argv):
        if item.startswith("--") and index + 1 < len(argv):
            values[item[2:].replace("-", "_")] = argv[index + 1]
    values["count"] = int(values["count"])
    values["soft"] = float(values["soft"])
    return values


def make_camera(scene, elevation, azimuth):
    data = bpy.data.cameras.new("Gate Camera")
    data.lens = 32.0
    data.sensor_width = 36.0
    data.clip_start = 0.1
    data.clip_end = 1000.0
    camera = bpy.data.objects.new("Gate Camera", data)
    scene.collection.objects.link(camera)
    elevation = math.radians(elevation)
    azimuth = math.radians(azimuth)
    direction = Vector((math.cos(elevation) * math.cos(azimuth),
                        math.cos(elevation) * math.sin(azimuth),
                        math.sin(elevation)))
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.location = (0.0, 0.0, 0.0)
    return camera


def render(scene, camera, path):
    scene.camera = camera
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def read_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        height, width, 4)[:, :, :3]
    bpy.data.images.remove(image)
    return pixels


def mask_from(on, off):
    return np.abs(on - off).max(axis=2) > 0.02


def save_mask(mask, path):
    height, width = mask.shape
    image = bpy.data.images.new("Gate Mask", width=width, height=height,
                                alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = np.flipud(mask.astype(np.float32))[:, :, None]
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    image.file_format = "PNG"
    image.filepath_raw = path
    image.save()
    bpy.data.images.remove(image)


def main():
    args = parse_args()
    out = os.path.abspath(args["out"])
    os.makedirs(out, exist_ok=True)
    scene, palette_module = proto.build_sky()
    scene.render.resolution_x = RW
    scene.render.resolution_y = RH
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.color_depth = "8"
    scene.eevee.taa_render_samples = 32
    threshold_node = proto.setup_world(scene, None, palette_module)
    env = next(node for node in scene.world.node_tree.nodes
               if node.bl_idname == "ShaderNodeTexEnvironment")
    black = bpy.data.images.new("Black", 2, 1, alpha=False,
                                float_buffer=False)
    black.colorspace_settings.name = "Non-Color"
    black.pixels.foreach_set(np.zeros(8, dtype=np.float32))
    black.update()
    env.image = black
    cameras = {}
    for elevation in ELEVATIONS:
        for azimuth in AZIMUTHS:
            cameras[(elevation, azimuth)] = make_camera(
                scene, elevation, azimuth)
            render(scene, cameras[(elevation, azimuth)],
                   os.path.join(out, "gate_off_e%03d_a%03d.png"
                                % (elevation, azimuth)))
    dirs, _lat = proto.directions(W, H)
    sky = dirs[:, :, 2] >= 0.0
    lat = np.arcsin(np.clip(dirs[:, :, 2], -1.0, 1.0))
    weights = np.where(sky, np.cos(lat), 0.0).astype(np.float32)
    report = {"amount": AMOUNT, "count": args["count"],
              "soft": args["soft"], "records": []}
    for seed in SEEDS:
        specs = fp.footprint_specs(seed, args["count"], args["soft"])
        wx, wy = fp.variant_warp(W, H, seed)
        cutoffs, achieved, _coverages = fp.activation_cutoffs(
            specs, dirs, wx, wy, [AMOUNT], weights, sky)
        state, areas, rank = fp.geometry_composites(
            specs, dirs, wx, wy, cutoffs, weights, sky)
        texture = proto.make_image(
            state[AMOUNT]["best"],
            os.path.join(out, "gate_field_s%02d.exr" % seed))
        env.image = texture
        threshold_node.outputs[0].default_value = 0.5
        record = {"seed": seed, "masses": len(specs),
                  "cutoff": cutoffs[AMOUNT],
                  "global_coverage": round(achieved[AMOUNT], 4),
                  "frames": []}
        for elevation in ELEVATIONS:
            for azimuth in AZIMUTHS:
                name = "gate_F_s%02d_e%03d_a%03d.png" % (
                    seed, elevation, azimuth)
                path = os.path.join(out, name)
                render(scene, cameras[(elevation, azimuth)], path)
                off = read_rgb(os.path.join(
                    out, "gate_off_e%03d_a%03d.png" % (elevation, azimuth)))
                mask = mask_from(read_rgb(path), off)
                coverage = float(mask.mean())
                save_mask(mask, os.path.join(
                    out, "gate_mask_s%02d_e%03d_a%03d.png"
                    % (seed, elevation, azimuth)))
                record["frames"].append({
                    "elevation": elevation, "azimuth": azimuth,
                    "file": name, "coverage": round(coverage, 4)})
                print("GATE", seed, elevation, azimuth,
                      "coverage", round(coverage, 4))
        report["records"].append(record)
        bpy.data.images.remove(texture)
        env.image = black
    with open(os.path.join(out, "gate.json"), "w",
              encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
