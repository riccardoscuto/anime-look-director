"""2.5D clouds: layered cloud cutouts owned by the add-on.

The World gradient paints the sky, but it has no depth: a firework always
composites in front of it. These cards are real meshes at several distances,
cut to the cloud silhouette and **opaque**: a firework behind a card is hidden
by the visible render itself, through the P1 Cryptomatte matte, with no extra
compositor path.

The cutout is geometry, not alpha: no rectangle edge, no dithering noise, and
the depth passes see a solid surface. The cards are environment (the B layer),
never FX.
"""

import math

import bpy
from mathutils import Vector

COLLECTION_NAME = "ALD | Clouds"
TAG = "ald_clouds"
DISTANCES = (160.0, 230.0, 320.0)
COLUMNS = 96
ROWS = 48


def _owner(scene):
    from . import fx
    return fx._scene_id(scene)


def _collection(scene):
    from . import fx
    owner = _owner(scene)
    for collection in bpy.data.collections:
        if collection.get(TAG) and collection.get(fx.OWNER_KEY) == owner:
            return collection
    return None


def exists(scene):
    return _collection(scene) is not None


def _palette_colors(scene):
    from . import palette
    settings = getattr(scene, "ald", None)
    key = scene.get("ald_effective_palette",
                    settings.palette if settings else "TWILIGHT_DUSK")
    values = palette.effective(scene, key)
    return (tuple(values["cloud_shadow"]), tuple(values["cloud_mid"]),
            tuple(values["cloud_light"]))


def _noise(x, y, seed):
    """A deterministic value noise in 0..1, enough for a cloud silhouette."""
    value = (math.sin(x * 6.3 + seed * 1.7)
             * math.cos(y * 8.1 + seed * 2.3) * 0.5 + 0.5)
    value += (math.sin(x * 14.7 - seed * 0.9)
              * math.cos(y * 17.3 + seed * 1.1) * 0.5 + 0.5) * 0.35
    value += (math.sin(x * 31.0 + seed * 3.1)
              * math.cos(y * 27.0 - seed * 0.5) * 0.5 + 0.5) * 0.15
    return value / 1.5


def _cloud_mesh(name, seed, amount):
    """A wavy cloud band: the top edge sits off-frame, the bottom is a cloud.

    A band of 512 columns keeps the silhouette at about one pixel at 160 m;
    a full 2D grid would need millions of faces for the same edge.
    """
    columns = 512
    top = 0.62
    vertices = []
    for column in range(columns + 1):
        t = column / columns
        x = t - 0.5
        taper = math.sin(math.pi * t) ** 0.45
        wave = (-0.16 + 0.10 * math.sin(t * 11.0 + seed)
                + 0.05 * math.sin(t * 27.0 + seed * 2.0)
                + 0.03 * math.sin(t * 61.0 - seed * 0.7))
        bottom = top + (wave - top) * taper
        vertices.append((x, top, 0.0))
        vertices.append((x, bottom, 0.0))
    faces = []
    for column in range(columns):
        index = column * 2
        faces.append((index, index + 1, index + 3, index + 2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh[TAG] = True
    return mesh


def _material(name, colors):
    """An opaque cloud colour: emission, no alpha, no rectangle."""
    material = bpy.data.materials.new(name)
    material[TAG] = True
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    nodes = tree.nodes
    links = tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (380, 0)
    links.new(emission.outputs[0], output.inputs["Surface"])

    coords = nodes.new("ShaderNodeTexCoord")
    coords.location = (-900, 0)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-700, -260)
    links.new(coords.outputs["Generated"], separate.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-700, 0)
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.55
    links.new(coords.outputs["Generated"], noise.inputs["Vector"])

    shadow = nodes.new("ShaderNodeRGB")
    shadow.name = "ALD | Cloud Shadow"
    shadow.location = (-700, 300)
    shadow.outputs[0].default_value = (*colors[0], 1.0)
    mid = nodes.new("ShaderNodeRGB")
    mid.name = "ALD | Cloud Mid"
    mid.location = (-700, 460)
    mid.outputs[0].default_value = (*colors[1], 1.0)
    light = nodes.new("ShaderNodeRGB")
    light.name = "ALD | Cloud Light"
    light.location = (-700, 620)
    light.outputs[0].default_value = (*colors[2], 1.0)

    first = nodes.new("ShaderNodeMix")
    first.data_type = "RGBA"
    first.blend_type = "MIX"
    first.location = (-460, 380)
    first_a = next(s for s in first.inputs if s.name == "A" and s.type == "RGBA")
    first_b = next(s for s in first.inputs if s.name == "B" and s.type == "RGBA")
    first_out = next(s for s in first.outputs
                     if s.name == "Result" and s.type == "RGBA")
    links.new(mid.outputs[0], first_a)
    links.new(shadow.outputs[0], first_b)
    links.new(noise.outputs["Fac"], first.inputs["Factor"])

    second = nodes.new("ShaderNodeMix")
    second.data_type = "RGBA"
    second.blend_type = "MIX"
    second.location = (-220, 380)
    second_a = next(s for s in second.inputs
                    if s.name == "A" and s.type == "RGBA")
    second_b = next(s for s in second.inputs
                    if s.name == "B" and s.type == "RGBA")
    second_out = next(s for s in second.outputs
                      if s.name == "Result" and s.type == "RGBA")
    links.new(first_out, second_a)
    links.new(light.outputs[0], second_b)
    vertical = nodes.new("ShaderNodeMapRange")
    vertical.location = (-460, 620)
    vertical.inputs["From Min"].default_value = 0.58
    vertical.inputs["From Max"].default_value = 1.0
    links.new(separate.outputs["Y"], vertical.inputs["Value"])
    links.new(vertical.outputs["Result"], second.inputs["Factor"])
    links.new(second_out, emission.inputs["Color"])
    return material


def create(scene, amount=0.6, height=0.35):
    """Create (or replace) the cloud layer of the scene."""
    from . import fx, snapshot

    snapshot.ensure(scene)
    remove(scene)
    owner = _owner(scene)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    collection[TAG] = True
    collection[fx.OWNER_KEY] = owner
    scene.collection.children.link(collection)

    _axis, _elevation, units = fx._anchor(scene)
    origin, forward, up, right = fx._camera_basis(scene)
    colors = _palette_colors(scene)
    for index, distance in enumerate(DISTANCES):
        depth = distance * units
        width = depth * 1.7
        card_height = depth * 0.55
        mesh = _cloud_mesh("ALD | Cloud %d" % index, index * 3.7 + 1.0, amount)
        obj = bpy.data.objects.new("ALD | Cloud %d" % index, mesh)
        obj[TAG] = True
        collection.objects.link(obj)
        lateral = depth * (-0.22 + 0.22 * index)
        obj.location = (origin + forward * depth
                        + right * lateral
                        + up * (depth * (0.26 + height * 0.20 + 0.05 * index)))
        obj.rotation_euler = (origin - obj.location).to_track_quat(
            "Z", "Y").to_euler()
        obj.scale = (width, card_height, 1.0)
        obj.data.materials.append(_material("ALD | Cloud %d" % index, colors))
    return len(DISTANCES)


def sync(scene):
    """Apply the palette to the existing cards."""
    collection = _collection(scene)
    settings = getattr(scene, "ald", None)
    if collection is None or settings is None:
        return False
    colors = _palette_colors(scene)
    for obj in collection.objects:
        for material in obj.data.materials:
            if material is None or not material.get(TAG):
                continue
            nodes = material.node_tree.nodes
            for name, color in (("ALD | Cloud Shadow", colors[0]),
                                ("ALD | Cloud Mid", colors[1]),
                                ("ALD | Cloud Light", colors[2])):
                rgb = nodes.get(name)
                if rgb is not None:
                    rgb.outputs[0].default_value = (*color, 1.0)
    return True


def remove(scene):
    collection = _collection(scene)
    if collection is None:
        return False
    materials = set()
    for obj in list(collection.objects):
        for slot in obj.material_slots:
            if slot.material is not None:
                materials.add(slot.material)
        mesh = obj.data if obj.type == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(collection)
    for material in materials:
        if material.users == 0:
            bpy.data.materials.remove(material)
    return True
