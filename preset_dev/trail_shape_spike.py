"""P2-C spike: round tube against flat ribbon for the filaments.

One vertical filament is built twice: with the production tube group and with a
copy whose circular profile is replaced by a line (a flat strip). Both are
rendered face-on (camera on -Y) and edge-on (camera on +X). A representation is
acceptable only if a filament stays readable from every direction, because a
burst is three dimensional.

Run::

    blender -b --factory-startup --python preset_dev/trail_shape_spike.py
"""

import math
import os
import tempfile

import bpy
from mathutils import Vector

MODULE = "anime_look_director"
SAMPLES = 16
TRAIL = 0.7
RADIUS = 0.03
SPEED = 2.4


def enable_addon():
    if hasattr(bpy.types.Scene, "ald"):
        return
    import addon_utils
    addon_utils.enable(MODULE)


def emission_material():
    material = bpy.data.materials.new("P2 Spike Emission")
    material.use_nodes = True
    tree = material.node_tree
    for node in list(tree.nodes):
        tree.nodes.remove(node)
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (6.0, 4.0, 2.0, 1.0)
    emission.inputs["Strength"].default_value = 3.0
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 400
    scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("P2 Spike Black")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    background.inputs["Strength"].default_value = 0.0
    scene.world = world
    camera_data = bpy.data.cameras.new("P2 Spike Camera")
    camera_data.lens = 50.0
    camera = bpy.data.objects.new("P2 Spike Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.frame_set(1)
    return scene, camera


def spoke_particles():
    velocity = Vector((0.0, 0.0, SPEED))
    particles = []
    for step in range(SAMPLES):
        profile = step / (SAMPLES - 1.0)
        particles.append({
            "birth": 0.0, "life": 2.4, "drag": 0.1,
            "radius": 0.25 + 0.9 * profile ** 1.4,
            "vel": velocity, "pos0": Vector((0.0, 0.0, 0.0)),
            "tau": TRAIL * (1.0 - profile),
            "jitter": Vector((0.0, 0.0, 0.0)),
            "spoke": 0, "trail": TRAIL, "color": None,
        })
    return particles


def ribbon_group(tube_group):
    """Copy of the trail group whose profile is a line instead of a circle."""
    group = tube_group.copy()
    group.name = "P2 Spike Ribbon"
    nodes = group.nodes
    links = group.links
    circle = nodes.get("Curve Circle")
    curve_to_mesh = nodes.get("Curve to Mesh")
    target = None
    for link in list(links):
        if link.from_node == circle:
            target = link.to_socket
            links.remove(link)
    line = nodes.new("GeometryNodeCurvePrimitiveLine")
    line.location = circle.location
    line.inputs["Start"].default_value = (-1.0, 0.0, 0.0)
    line.inputs["End"].default_value = (1.0, 0.0, 0.0)
    links.new(line.outputs[0], target)
    nodes.remove(circle)
    # The unit line is scaled by the same radius the tube uses.
    group_in = nodes.get("Group Input")
    if "Scale" in curve_to_mesh.inputs:
        links.new(group_in.outputs["Radius"], curve_to_mesh.inputs["Scale"])
    return group


def render(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    return sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.02)


def main():
    enable_addon()
    from anime_look_director import fx

    scene, camera = build_scene()
    material = emission_material()
    fx.clear(scene)
    particles = spoke_particles()
    tube = fx._gn_trail_object(scene, "P2 Spike Tube", material, particles,
                               trail=TRAIL, age_offset=0.8, radius=RADIUS)
    ribbon = fx._gn_trail_object(scene, "P2 Spike Ribbon", material, particles,
                                 trail=TRAIL, age_offset=0.8, radius=RADIUS)
    ribbon.modifiers[0].node_group = ribbon_group(tube.modifiers[0].node_group)

    views = (("face", (0.0, -9.0, 0.0)), ("edge", (9.0, 0.0, 0.0)))
    results = {}
    for variant, obj in (("tube", tube), ("ribbon", ribbon)):
        tube.hide_render = variant != "tube"
        ribbon.hide_render = variant != "ribbon"
        for view, location in views:
            camera.location = location
            camera.rotation_euler = (Vector((0, 0, 0))
                                     - camera.location).to_track_quat(
                                         "-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            path = os.path.join(tempfile.gettempdir(),
                                "p2_%s_%s.png" % (variant, view))
            results[(variant, view)] = render(scene, path)
    print("P2 SHAPE coverage (lit pixels, 400x400)")
    for variant in ("tube", "ribbon"):
        face = results[(variant, "face")]
        edge = results[(variant, "edge")]
        ratio = edge / max(face, 1)
        print("P2 SHAPE %-6s face=%6d edge=%6d ratio=%.2f"
              % (variant, face, edge, ratio))
    tube_ratio = results[("tube", "edge")] / max(results[("tube", "face")], 1)
    ribbon_ratio = (results[("ribbon", "edge")]
                    / max(results[("ribbon", "face")], 1))
    print("P2 SHAPE verdict: tube %.2f, ribbon %.2f -> %s"
          % (tube_ratio, ribbon_ratio,
             "TUBE" if ribbon_ratio < tube_ratio * 0.6 else "NO CLEAR WINNER"))
    fx.clear(scene)


if __name__ == "__main__":
    main()
