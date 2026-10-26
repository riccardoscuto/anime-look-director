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
SHAPED = ((0.04, 0.0), (0.08, 0.0), (0.08, 0.15))


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

    # C. shaped volumes: faded borders, noise density and optional emission.
    for density, emission in SHAPED:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube = bpy.context.object
        cube.name = "PA2 Volume Shaped"
        cube.rotation_euler = facing
        cube.location = location
        cube.scale = (width, height, height * 0.2)
        cube.data.materials.append(
            _shaped_volume_material(values, density, emission))
        bpy.context.view_layer.update()
        name = "volume_shaped_%03d%s.png" % (
            int(round(density * 1000)), "_glow" if emission else "")
        shot(name)
        bpy.data.objects.remove(cube, do_unlink=True)

    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return 0


def _shaped_volume_material(values, density, emission):
    """A volume with a faded border and a noise-thresholded density."""
    material = bpy.data.materials.new("PA2 Volume Shaped")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    nodes = tree.nodes
    links = tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (700, 0)
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.location = (400, 0)
    volume.inputs["Anisotropy"].default_value = 0.25
    coordinates = nodes.new("ShaderNodeTexCoord")
    coordinates.location = (-900, 0)
    absolute = nodes.new("ShaderNodeVectorMath")
    absolute.operation = "ABSOLUTE"
    absolute.location = (-700, 0)
    links.new(coordinates.outputs["Object"], absolute.inputs[0])
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-520, 0)
    links.new(absolute.outputs["Vector"], separate.inputs[0])
    maximum = nodes.new("ShaderNodeMath")
    maximum.operation = "MAXIMUM"
    maximum.location = (-340, 120)
    links.new(separate.outputs["X"], maximum.inputs[0])
    links.new(separate.outputs["Y"], maximum.inputs[1])
    last = nodes.new("ShaderNodeMath")
    last.operation = "MAXIMUM"
    last.location = (-180, 120)
    links.new(maximum.outputs[0], last.inputs[0])
    links.new(separate.outputs["Z"], last.inputs[1])
    border = nodes.new("ShaderNodeMapRange")
    border.location = (0, 120)
    border.inputs["From Min"].default_value = 0.30
    border.inputs["From Max"].default_value = 0.48
    border.inputs["To Min"].default_value = 1.0
    border.inputs["To Max"].default_value = 0.0
    links.new(last.outputs[0], border.inputs["Value"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-340, -160)
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.62
    links.new(coordinates.outputs["Object"], noise.inputs["Vector"])
    macro = nodes.new("ShaderNodeMapRange")
    macro.location = (-120, -160)
    macro.inputs["From Min"].default_value = 0.38
    macro.inputs["From Max"].default_value = 0.62
    macro.inputs["To Min"].default_value = 0.0
    macro.inputs["To Max"].default_value = 1.0
    links.new(noise.outputs["Fac"], macro.inputs["Value"])
    shape = nodes.new("ShaderNodeMath")
    shape.operation = "MULTIPLY"
    shape.location = (160, 40)
    links.new(border.outputs["Result"], shape.inputs[0])
    links.new(macro.outputs["Result"], shape.inputs[1])
    density_node = nodes.new("ShaderNodeMath")
    density_node.operation = "MULTIPLY"
    density_node.location = (320, 40)
    density_node.inputs[1].default_value = density
    links.new(shape.outputs[0], density_node.inputs[0])
    links.new(density_node.outputs[0], volume.inputs["Density"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (0, -320)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (*values["cloud_shadow"], 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*values["cloud_light"], 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], volume.inputs["Color"])
    if emission:
        volume.inputs["Emission Color"].default_value = (
            *values["cloud_light"], 1.0)
        volume.inputs["Emission Strength"].default_value = emission
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return material


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
