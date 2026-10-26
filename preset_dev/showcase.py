"""Final showcase: the whole stack together at 1920x1080.

A directed five-burst show, the 2.5D cloud bands and the full compositor
(Cryptomatte FX, painterly filters, ink, light wrap) in one frame, at night and
at dusk. This is the integration evidence: P1 and P3 (compositing and
shading), P4 (composition), P5 (clouds) in the same scene.

Run::

    blender -b --factory-startup --python preset_dev/showcase.py
"""

import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "showcase")
AGE = 2.0


def add_foreground(scene):
    """A dark skyline at the bottom edge: scene content for the showcase.

    It gives scale to the sky and exercises the ink lines and the occlusion
    (the compositor treats it as environment, not FX). It is not an add-on
    feature: the add-on dresses the user's scene, it does not own one.
    """
    from anime_look_director import palette
    key = scene.get("ald_effective_palette", scene.ald.palette)
    material = bpy.data.materials.new("Showcase Silhouette")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        # A silhouette, not a lit building: the ambient world must not lift it.
        bsdf.inputs["Base Color"].default_value = (0.004, 0.004, 0.008, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.0
    collection = bpy.data.collections.new("Showcase Foreground")
    scene.collection.children.link(collection)
    camera = scene.camera
    origin, forward, up, right = None, None, None, None
    from anime_look_director import fx
    origin, forward, _up, right = fx._camera_basis(scene)
    shapes = ((-0.55, 30.0, 5.0, 3.0, 7.0),
              (0.55, 28.0, 4.0, 3.0, 9.0),
              (-0.18, 42.0, 3.0, 3.0, 5.0),
              (0.24, 46.0, 3.0, 3.0, 4.5))
    for index, (lateral, depth, width, thickness, height) in enumerate(shapes):
        mesh = bpy.data.meshes.new("Showcase Block %d" % index)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("Showcase Block %d" % index, mesh)
        collection.objects.link(obj)
        base = origin + forward * depth + right * (lateral * depth)
        obj.location = (base.x, base.y, height * 0.5)
        obj.scale = (width, thickness, height)
        obj.data.materials.append(material)
    # A short antenna on the left block.
    mesh = bpy.data.meshes.new("Showcase Antenna")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=4, radius1=0.10,
                          radius2=0.02, depth=3.0)
    bm.to_mesh(mesh)
    bm.free()
    antenna = bpy.data.objects.new("Showcase Antenna", mesh)
    collection.objects.link(antenna)
    base = origin + forward * 30.0 + right * (-0.55 * 30.0)
    antenna.location = (base.x, base.y, 7.0 + 1.5)
    antenna.data.materials.append(material)
    return collection


def remove_foreground(collection):
    for obj in list(collection.objects):
        mesh = obj.data if obj.type == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        if material.name == "Showcase Silhouette" and material.users == 0:
            bpy.data.materials.remove(material)


def build(palette, count, lens, name):
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx

    settings = scene.ald
    settings.palette = palette
    settings.fx_age = 0.0
    settings.fx_gn_prototype = True
    settings.halation_strength = 0.5
    settings.kuwahara_size = 6.0
    settings.light_wrap_strength = 0.4
    settings.light_wrap_size = 24.0
    settings.shadow_tint_strength = 0.45
    settings.ink_lines = True
    settings.depth_near = 20.0
    settings.depth_far = 320.0
    settings.fx_glow_strength = 1.0
    settings.fx_glow_threshold = 0.0
    settings.fx_glow_size = 0.35
    settings.clouds_coverage = 0.5
    settings.clouds_layers = 3
    settings.clouds_altitude = 90.0
    settings.clouds_depth = 180.0
    settings.clouds_flash = True
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()

    fx.create_fireworks(scene, count, seed=23, distance=120.0, time=0.0)
    bpy.ops.ald.build()
    system = scene.ald.fx_systems[0]
    hero = system.events[0]
    camera.rotation_euler = (Vector(hero.target) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    camera.data.lens = lens
    bpy.context.view_layer.update()
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    scene.frame_set(int(system.origin_frame + AGE * fps))
    bpy.context.view_layer.update()

    # The cards are placed along the final camera basis.
    clouds.create(scene)
    foreground = add_foreground(scene)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    baseline_fx.render(scene, os.path.join(OUT, name))
    events = len(system.events)
    clouds_count = len(clouds._collection(scene).objects)
    remove_foreground(foreground)
    fx.clear(scene)
    clouds.remove(scene)
    return {"file": name, "palette": palette, "bursts": events,
            "clouds": clouds_count, "age": AGE, "lens": lens}


def main():
    os.makedirs(OUT, exist_ok=True)
    report = [
        build("NEON_NIGHT", 5, 35.0, "night_5_bursts.png"),
        build("TWILIGHT_DUSK", 3, 40.0, "dusk_3_bursts.png"),
    ]
    with open(os.path.join(OUT, "showcase.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for entry in report:
        print("SHOWCASE", entry["file"], entry["bursts"], "bursts",
              entry["clouds"], "clouds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
