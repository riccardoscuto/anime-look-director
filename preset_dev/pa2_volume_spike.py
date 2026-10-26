"""PA2-inspired spike: spatial cloud cards vs a native EEVEE volume.

Research only: no add-on backend is changed. The same camera and palette render
the production cloud cards and native Principled Volume slabs with a procedural
density. Several densities are rendered so the comparison is not decided by a
single arbitrary value. Metrics record the render time; the images are compared
by eye.

Run::

    blender -b --factory-startup --python preset_dev/pa2_volume_spike.py
"""

import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline_fx

OUT = os.path.join(HERE, "pa2_volume_spike")
DENSITIES = (0.02, 0.06, 0.15)


def main():
    os.makedirs(OUT, exist_ok=True)
    scene, camera = baseline_fx.build_scene(None)
    baseline_fx.enable_addon()
    from anime_look_director import clouds, fx, look, palette

    scene.ald.palette = "AFTER_SCHOOL"
    scene.ald.clouds_coverage = 0.5
    scene.ald.clouds_layers = 2
    scene.ald.clouds_altitude = 90.0
    scene.ald.clouds_depth = 180.0
    bpy.ops.ald.apply_palette()
    bpy.ops.ald.build()
    camera.rotation_euler = (1.95, 0.0, 0.0)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    bpy.context.view_layer.update()
    # The preset re-enables the world clouds: switch them off after the apply
    # so the card/volume comparison is isolated (the update calls the world).
    scene.ald.clouds = False
    look.apply_world(scene)
    report = {"resolution": [640, 360], "engine": "BLENDER_EEVEE",
              "renders": []}

    def shot(name):
        path = os.path.join(OUT, name)
        start = time.perf_counter()
        baseline_fx.render(scene, path)
        elapsed = time.perf_counter() - start
        report["renders"].append({"file": name,
                                  "render_s": round(elapsed, 3),
                                  "bytes": os.path.getsize(path)})
        print("PA2", name, "render %.2fs" % elapsed)

    # A. the production cards.
    clouds.remove(scene)
    clouds.create(scene)
    shot("card.png")
    clouds.remove(scene)

    # B. native volume slabs in the exact placement of the first card layer.
    values = palette.effective(scene, "AFTER_SCHOOL")
    origin, forward, up, right = fx._camera_basis(scene)
    axis, _elevation, units = fx._anchor(scene)
    depth = float(scene.ald.clouds_depth) * units
    altitude = float(scene.ald.clouds_altitude) * units
    lateral = depth * -0.18
    width = depth * 1.4 * float(scene.ald.clouds_scale)
    height = depth * 0.62 * float(scene.ald.clouds_scale)
    location = origin + forward * depth + right * lateral + axis * altitude
    facing = (origin - location).to_track_quat("Z", "Y").to_euler()
    for density in DENSITIES:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube = bpy.context.object
        cube.name = "PA2 Volume"
        cube.rotation_euler = facing
        cube.location = location
        cube.scale = (width, height, height * 0.2)
        cube.data.materials.append(_volume_material(values, density))
        bpy.context.view_layer.update()
        shot("volume_%.2f.png" % density)
        bpy.data.objects.remove(cube, do_unlink=True)

    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


def _volume_material(values, density):
    material = bpy.data.materials.new("PA2 Volume")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    nodes = tree.nodes
    links = tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.location = (200, 0)
    volume.inputs["Color"].default_value = (*values["cloud_mid"], 1.0)
    volume.inputs["Anisotropy"].default_value = 0.3
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-300, 0)
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.6
    density_map = nodes.new("ShaderNodeMapRange")
    density_map.location = (-80, 0)
    density_map.inputs["From Min"].default_value = 0.42
    density_map.inputs["From Max"].default_value = 0.72
    density_map.inputs["To Min"].default_value = 0.0
    density_map.inputs["To Max"].default_value = density
    links.new(noise.outputs["Fac"], density_map.inputs["Value"])
    links.new(density_map.outputs["Result"], volume.inputs["Density"])
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return material


if __name__ == "__main__":
    sys.exit(main())
