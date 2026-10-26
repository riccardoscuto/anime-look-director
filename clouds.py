"""Spatial clouds 2.0: layered cloud masses with real sky openings.

The World gradient paints the distant sky; these layers are real geometry at a
few depths, cut to an irregular silhouette by a deterministic density field.
They are opaque, so they write depth and a firework behind a mass is hidden by
the visible render itself (the P1 Cryptomatte matte needs no extra path).

Design rules (see AGENTS.md):

- ``Coverage`` is the threshold of the density field: 0 removes every face,
  1 keeps the most of it. It changes the geometry, never only the colour.
- ``Altitude`` is world units along the ALD Sky/FX Anchor vertical, not a
  fraction of the depth. ``Depth`` is the distance from the creation camera.
- ``Layer Count`` adds independent bands at increasing depth.
- ``Mode``: SHOT_LOCKED keeps the creation orientation, CAMERA_FACING follows
  the active camera without moving the world position.
- Colour, transform and geometry updates are separate: a palette change never
  rebuilds the mesh; a depth slider never rebuilds the shape.
- The material is emissive with a stylised local flash: the burst energy and
  position light the nearby cloud cards (``event.glow`` finally does work).
"""

import math

import bpy
from mathutils import Vector

COLLECTION_NAME = "ALD | Spatial Clouds"
TAG = "ald_clouds"
SCHEMA = 2
MAX_COLS = 512
MAX_ROWS = 128
NOISE_MODES = ("SHOT_LOCKED", "CAMERA_FACING")
FLASH_RADIUS = 0.24
FLASH_COLOR = (1.0, 0.72, 0.45)


# ---------------------------------------------------------------------------
# deterministic density field
# ---------------------------------------------------------------------------

def _hash_2d(x, y, seed):
    value = math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453
    return value - math.floor(value)


def _value_noise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    a = _hash_2d(ix, iy, seed)
    b = _hash_2d(ix + 1, iy, seed)
    c = _hash_2d(ix, iy + 1, seed)
    d = _hash_2d(ix + 1, iy + 1, seed)
    return (a * (1 - ux) + b * ux) * (1 - uy) + (c * (1 - ux) + d * ux) * uy


def _fbm(x, y, seed, octaves=4, gain=0.5):
    total = 0.0
    amplitude = 1.0
    norm = 0.0
    for octave in range(octaves):
        total += _value_noise(x, y, seed + octave * 17.3) * amplitude
        norm += amplitude
        amplitude *= gain
        x *= 2.03
        y *= 2.03
    return total / norm


def _field(u, v, seed):
    """Density in 0..1; zero at the card border so no rectangle can appear."""
    warp = 0.10 * (_value_noise(u * 2.2 + seed, v * 2.2 - seed, seed) - 0.5)
    x = u + warp
    y = v + warp * 0.6
    macro = _fbm(x * 4.2 + 3.1, y * 4.6 - 1.7, seed, 3)
    lobes = _fbm(x * 9.5 - 1.1, y * 10.2 + 2.3, seed + 9.1, 2)
    value = macro * 0.68 + lobes * 0.32
    ex = max(0.0, min(1.0, (0.5 - abs(u)) / 0.09))
    ey = max(0.0, min(1.0, (0.5 - abs(v)) / 0.09))
    envelope = ex * ex * (3.0 - 2.0 * ex) * ey * ey * (3.0 - 2.0 * ey)
    # Normalise the fbm to a usable 0..1 range: the raw average is 0.5 with a
    # narrow spread, so a plain threshold made Coverage binary.
    return max(0.0, min(1.0, (value * envelope - 0.30) / 0.40))


def _field_grid(seed, columns, rows):
    """Coarse density grid; the fine mesh samples it bilinearly."""
    return [[_field(column / columns - 0.5, row / rows - 0.5, seed)
             for column in range(columns + 1)]
            for row in range(rows + 1)]


def _sample(grid, u, v, columns, rows):
    x = (u + 0.5) * columns
    y = (v + 0.5) * rows
    x0 = max(0, min(columns - 1, int(x)))
    y0 = max(0, min(rows - 1, int(y)))
    fx = x - x0
    fy = y - y0
    a = grid[y0][x0] * (1 - fx) + grid[y0][x0 + 1] * fx
    b = grid[y0 + 1][x0] * (1 - fx) + grid[y0 + 1][x0 + 1] * fx
    return a * (1 - fy) + b * fy


def _cloud_mesh(name, seed, coverage, columns, rows):
    """Islands of the density field above the coverage threshold."""
    mesh = bpy.data.meshes.new(name)
    mesh[TAG] = True
    if coverage <= 0.001:
        return mesh
    threshold = max(0.02, 0.98 - 1.1 * max(0.0, min(1.0, coverage)))
    coarse = 96
    coarse_rows = 28
    grid = _field_grid(seed, coarse, coarse_rows)
    verts = []
    index_of = {}
    faces = []
    for row in range(rows):
        v0 = row / rows - 0.5
        v1 = (row + 1) / rows - 0.5
        for column in range(columns):
            u0 = column / columns - 0.5
            u1 = (column + 1) / columns - 0.5
            density = _sample(grid, (u0 + u1) * 0.5, (v0 + v1) * 0.5,
                              coarse, coarse_rows)
            if density <= threshold:
                continue
            corners = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
            face = []
            for corner in corners:
                key = (round(corner[0] * 100000), round(corner[1] * 100000))
                index = index_of.get(key)
                if index is None:
                    index = len(verts)
                    index_of[key] = index
                    verts.append((corner[0], corner[1], 0.0))
                face.append(index)
            faces.append(tuple(face))
    if verts:
        mesh.from_pydata(verts, [], faces)
        mesh.update()
    return mesh


# ---------------------------------------------------------------------------
# material
# ---------------------------------------------------------------------------

def _rgb(nodes, name, color, location):
    node = nodes.new("ShaderNodeRGB")
    node.name = name
    node.location = location
    node.outputs[0].default_value = (*color, 1.0)
    return node


def _value(nodes, name, value, location):
    node = nodes.new("ShaderNodeValue")
    node.name = name
    node.location = location
    node.outputs[0].default_value = float(value)
    return node


def _material(name, colors):
    material = bpy.data.materials.new(name)
    material[TAG] = True
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    nodes = tree.nodes
    links = tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (700, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (480, 0)
    links.new(emission.outputs[0], output.inputs["Surface"])

    coords = nodes.new("ShaderNodeTexCoord")
    coords.location = (-1100, 0)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (-900, -260)
    links.new(coords.outputs["Object"], separate.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-900, 0)
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.55
    links.new(coords.outputs["Object"], noise.inputs["Vector"])

    shadow = _rgb(nodes, "ALD | Cloud Shadow", colors[0], (-900, 320))
    mid = _rgb(nodes, "ALD | Cloud Mid", colors[1], (-900, 480))
    light = _rgb(nodes, "ALD | Cloud Light", colors[2], (-900, 640))
    first = nodes.new("ShaderNodeMix")
    first.data_type = "RGBA"
    first.blend_type = "MIX"
    first.location = (-660, 400)
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
    second.location = (-420, 400)
    second_a = next(s for s in second.inputs
                    if s.name == "A" and s.type == "RGBA")
    second_b = next(s for s in second.inputs
                    if s.name == "B" and s.type == "RGBA")
    second_out = next(s for s in second.outputs
                      if s.name == "Result" and s.type == "RGBA")
    links.new(first_out, second_a)
    links.new(light.outputs[0], second_b)
    vertical = nodes.new("ShaderNodeMapRange")
    vertical.location = (-660, 640)
    vertical.inputs["From Min"].default_value = 0.0
    vertical.inputs["From Max"].default_value = 0.62
    links.new(separate.outputs["Y"], vertical.inputs["Value"])
    links.new(vertical.outputs["Result"], second.inputs["Factor"])

    # Stylised local flash: the burst lights the card around the projected
    # point. The handler writes the local position and the energy every frame.
    flash_x = _value(nodes, "ALD | Flash X", 0.0, (-660, -520))
    flash_y = _value(nodes, "ALD | Flash Y", 0.0, (-660, -600))
    flash_energy = _value(nodes, "ALD | Flash Energy", 0.0, (-660, -680))
    flash_color = _rgb(nodes, "ALD | Flash Color", FLASH_COLOR, (-660, -760))
    combine = nodes.new("ShaderNodeCombineXYZ")
    combine.location = (-460, -560)
    links.new(flash_x.outputs[0], combine.inputs["X"])
    links.new(flash_y.outputs[0], combine.inputs["Y"])
    point = nodes.new("ShaderNodeCombineXYZ")
    point.location = (-660, -360)
    links.new(separate.outputs["X"], point.inputs["X"])
    links.new(separate.outputs["Y"], point.inputs["Y"])
    distance = nodes.new("ShaderNodeVectorMath")
    distance.location = (-460, -400)
    distance.operation = "DISTANCE"
    links.new(point.outputs[0], distance.inputs[0])
    links.new(combine.outputs[0], distance.inputs[1])
    ratio = nodes.new("ShaderNodeMath")
    ratio.location = (-260, -420)
    ratio.operation = "MULTIPLY"
    links.new(distance.outputs["Value"], ratio.inputs[0])
    ratio.inputs[1].default_value = 1.0 / FLASH_RADIUS
    square = nodes.new("ShaderNodeMath")
    square.location = (-80, -420)
    square.operation = "MULTIPLY"
    links.new(ratio.outputs[0], square.inputs[0])
    links.new(ratio.outputs[0], square.inputs[1])
    negative = nodes.new("ShaderNodeMath")
    negative.location = (100, -420)
    negative.operation = "MULTIPLY"
    links.new(square.outputs[0], negative.inputs[0])
    negative.inputs[1].default_value = -1.0
    falloff = nodes.new("ShaderNodeMath")
    falloff.location = (280, -420)
    falloff.operation = "EXPONENT"
    links.new(negative.outputs[0], falloff.inputs[0])
    energy = nodes.new("ShaderNodeMath")
    energy.location = (100, -600)
    energy.operation = "MULTIPLY"
    links.new(falloff.outputs[0], energy.inputs[0])
    links.new(flash_energy.outputs[0], energy.inputs[1])
    tinted = nodes.new("ShaderNodeMix")
    tinted.data_type = "RGBA"
    tinted.blend_type = "ADD"
    tinted.location = (280, 400)
    tinted_a = next(s for s in tinted.inputs
                    if s.name == "A" and s.type == "RGBA")
    tinted_b = next(s for s in tinted.inputs
                    if s.name == "B" and s.type == "RGBA")
    tinted_out = next(s for s in tinted.outputs
                      if s.name == "Result" and s.type == "RGBA")
    links.new(second_out, tinted_a)
    links.new(flash_color.outputs[0], tinted_b)
    links.new(energy.outputs[0], tinted.inputs["Factor"])
    links.new(tinted_out, emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.0
    return material


# ---------------------------------------------------------------------------
# scene helpers
# ---------------------------------------------------------------------------

def _owner(scene):
    from . import fx
    return fx._scene_id(scene)


def _collection(scene):
    from . import fx
    owner = _owner(scene)
    for collection in bpy.data.collections:
        if collection.get(TAG) and collection.get(fx.OWNER_KEY) == owner:
            if _shared_with_other_scene(collection, scene):
                continue
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


def _object(scene, layer):
    """Resolve the object by UID inside the collection owned by this scene."""
    collection = _collection(scene)
    if collection is None:
        return None
    for obj in collection.objects:
        if obj.get("ald_cloud_uid") == layer.uid:
            return obj
    return None


def _shared_with_other_scene(collection, scene):
    """A collection linked to another scene must not be modified here."""
    def walk(coll):
        if coll == collection:
            return True
        return any(walk(child) for child in coll.children)

    for other in bpy.data.scenes:
        if other == scene:
            continue
        if walk(other.collection):
            return True
    return False


def _layers(scene):
    settings = getattr(scene, "ald", None)
    return settings.cloud_layers if settings is not None else []


def _settings(scene):
    return getattr(scene, "ald", None)


def _world_per_pixel(scene, position):
    from . import fx
    return fx._world_per_pixel(scene, position)


def _layout(scene, layer, camera_facing=False):
    """Place the card from the stored basis and the current controls."""
    settings = _settings(scene)
    if settings is None:
        return
    units = float(settings.fx_anchor_units_scale)
    origin = Vector(layer.origin)
    forward = Vector(layer.forward)
    right = Vector(layer.right)
    axis = Vector(layer.axis)
    depth = float(settings.clouds_depth) * units * (1.0 + 0.45 * layer.index)
    altitude = (float(settings.clouds_altitude) * units
                + layer.index * 8.0 * units)
    lateral = depth * (-0.18 + 0.18 * layer.index
                       / max(len(_layers(scene)) - 1, 1))
    location = origin + forward * depth + right * lateral + axis * altitude
    width = depth * 1.4 * float(settings.clouds_scale)
    height = depth * 0.62 * float(settings.clouds_scale)
    obj = _object(scene, layer)
    if obj is None:
        return
    obj.location = location
    obj.scale = (width, height, 1.0)
    from . import fx
    cam_origin = fx._camera_basis(scene)[0]
    facing = (cam_origin - location).to_track_quat("Z", "Y").to_euler()
    if camera_facing or settings.clouds_mode == "CAMERA_FACING":
        obj.rotation_euler = facing
        layer.current_rotation = tuple(facing)
    else:
        if not layer.rotation_valid:
            layer.rotation = tuple(facing)
            layer.rotation_valid = True
        obj.rotation_euler = Vector(layer.rotation)


def _rebuild_mesh(scene, layer):
    obj = _object(scene, layer)
    if obj is None:
        return
    settings = _settings(scene)
    units = float(settings.fx_anchor_units_scale)
    depth = float(settings.clouds_depth) * units * (1.0 + 0.45 * layer.index)
    width = depth * 1.4 * float(settings.clouds_scale)
    world_per_px = _world_per_pixel(scene, obj.location) if obj else 0.0
    if world_per_px > 1e-9:
        columns = int(max(64, min(MAX_COLS, width / (world_per_px * 4.0))))
        rows = int(max(16, min(MAX_ROWS, width * 0.24
                              / (world_per_px * 4.0))))
    else:
        columns, rows = 256, 96
    mesh = _cloud_mesh("ALD | Cloud %d" % layer.index, layer.seed,
                       float(settings.clouds_coverage), columns, rows)
    old = obj.data
    material = obj.active_material
    if material is not None:
        mesh.materials.append(material)
    obj.data = mesh
    if old is not None and old.users == 0:
        bpy.data.meshes.remove(old)
    if material is None:
        material = _material("ALD | Cloud %d" % layer.index,
                             _palette_colors(scene))
        obj.data.materials.append(material)


def _new_layer(scene, index, basis):
    settings = _settings(scene)
    layers = _layers(scene)
    layer = layers.add()
    from . import fx
    layer.uid = "cloud-%s-%d" % (fx._scene_id(scene)[:8], index)
    layer.index = index
    layer.seed = 3.7 + index * 11.9
    layer.origin = basis[0]
    layer.forward = basis[1]
    layer.right = basis[3]
    layer.axis = basis[4]
    layer.object_name = "ALD | Cloud %d" % index
    return layer


def create(scene, coverage=None, altitude=None):
    """Create (or replace) the spatial cloud layer from the scene settings."""
    from . import fx, snapshot

    settings = _settings(scene)
    if settings is None:
        return 0
    snapshot.ensure(scene)
    remove(scene)
    if coverage is not None:
        settings.clouds_coverage = float(coverage)
    if altitude is not None:
        settings.clouds_altitude = float(altitude)
    owner = _owner(scene)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    collection[TAG] = True
    collection[fx.OWNER_KEY] = owner
    collection["ald_schema"] = SCHEMA
    scene.collection.children.link(collection)

    settings.cloud_layers.clear()
    origin, forward, up, right = fx._camera_basis(scene)
    axis, _elevation, units = fx._anchor(scene)
    basis = (origin, forward, up, right, axis)
    count = max(1, min(5, int(settings.clouds_layers)))
    for index in range(count):
        layer = _new_layer(scene, index, basis)
        mesh = bpy.data.meshes.new(layer.object_name)
        mesh[TAG] = True
        obj = bpy.data.objects.new(layer.object_name, mesh)
        obj[TAG] = True
        obj["ald_cloud_uid"] = layer.uid
        collection.objects.link(obj)
        _layout(scene, layer)
        _rebuild_mesh(scene, layer)
    settings.clouds_created = True
    scene["ald_clouds_signature"] = "%s|%s|%d|%s" % (
        settings.clouds_coverage, settings.clouds_scale, count,
        [round(layer.seed, 3) for layer in settings.cloud_layers])
    bpy.context.view_layer.update()
    update_flash(scene)
    return count


def refresh(scene):
    """Apply the controls without destroying the layer identity."""
    settings = _settings(scene)
    collection = _collection(scene)
    if settings is None or collection is None:
        return False
    count = max(1, min(5, int(settings.clouds_layers)))
    layers = _layers(scene)
    while len(layers) > count:
        layer = layers[-1]
        obj = _object(scene, layer)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
        layers.remove(len(layers) - 1)
    if len(layers) == 0:
        from . import fx
        origin, forward, up, right = fx._camera_basis(scene)
        axis = fx._anchor(scene)[0]
        basis = (origin, forward, up, right, axis)
        for index in range(count):
            _new_layer(scene, index, basis)
    while len(layers) < count:
        first = layers[0]
        basis = (Vector(first.origin), Vector(first.forward),
                 Vector((0.0, 0.0, 1.0)), Vector(first.right),
                 Vector(first.axis))
        layer = _new_layer(scene, len(layers), basis)

    signature = "%s|%s|%d|%s" % (settings.clouds_coverage,
                                 settings.clouds_scale, count,
                                 [round(layer.seed, 3) for layer in layers])
    rebuild = scene.get("ald_clouds_signature") != signature
    for index, layer in enumerate(layers):
        layer.index = index
        obj = _object(scene, layer)
        if obj is None:
            mesh = bpy.data.meshes.new(layer.object_name)
            mesh[TAG] = True
            obj = bpy.data.objects.new(layer.object_name, mesh)
            obj[TAG] = True
            obj["ald_cloud_uid"] = layer.uid
            collection.objects.link(obj)
            rebuild = True
        _layout(scene, layer)
        if rebuild:
            _rebuild_mesh(scene, layer)
    scene["ald_clouds_signature"] = signature
    sync(scene)
    bpy.context.view_layer.update()
    update_flash(scene)
    return True


def sync(scene):
    """Palette only: no geometry, no transforms."""
    collection = _collection(scene)
    if collection is None:
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


def update_orientation(scene):
    """Camera Facing: re-orient the cards without moving them."""
    settings = _settings(scene)
    if settings is None or settings.clouds_mode != "CAMERA_FACING":
        return False
    collection = _collection(scene)
    if collection is None:
        return False
    from . import fx
    cam_origin = fx._camera_basis(scene)[0]
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        rotation = (cam_origin - obj.location).to_track_quat(
            "Z", "Y").to_euler()
        obj.rotation_euler = rotation
        for layer in _layers(scene):
            if layer.object_name == obj.name:
                layer.current_rotation = tuple(rotation)
    return True


def update_flash(scene):
    """Stylised local response: the strongest burst lights the nearby cards."""
    settings = _settings(scene)
    collection = _collection(scene)
    if settings is None or collection is None:
        return False
    energy = 0.0
    position = None
    if getattr(settings, "clouds_flash", True):
        from . import fx
        best = 0.0
        for system in settings.fx_systems:
            time = fx.system_time(scene, system)
            for event in system.events:
                if not event.enabled:
                    continue
                age = time - (float(event.birth) + float(event.rise_time))
                if age < 0.0 or age > float(event.life):
                    continue
                decay = 1.0 - age / max(float(event.life), 1e-3)
                value = float(event.glow) * decay
                if value > best:
                    best = value
                    position = Vector(event.target)
        energy = best * float(settings.clouds_flash_strength)
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        material = obj.active_material
        if material is None or not material.get(TAG):
            continue
        nodes = material.node_tree.nodes
        local = Vector((0.0, 0.0, 0.0))
        if position is not None:
            matrix = obj.matrix_world.inverted()
            local = matrix @ position
        node = nodes.get("ALD | Flash X")
        if node is not None:
            node.outputs[0].default_value = float(local.x)
        node = nodes.get("ALD | Flash Y")
        if node is not None:
            node.outputs[0].default_value = float(local.y)
        node = nodes.get("ALD | Flash Energy")
        if node is not None:
            # World distance, on top of the local XY falloff: a burst far
            # behind or beside the card must light it less.
            world_distance = ((position - obj.location).length
                              if position is not None else 0.0)
            attenuation = 1.0 / (1.0 + (world_distance / 120.0) ** 2)
            node.outputs[0].default_value = energy * attenuation
    flash = [round(energy, 4), 0.0, 0.0, 0.0]
    if position is not None:
        flash[1:] = [round(v, 2) for v in position]
    scene["ald_clouds_flash"] = flash
    return True


def diagnostics(scene):
    """The depth order and the flash state, for the panel."""
    settings = _settings(scene)
    collection = _collection(scene)
    if settings is None or collection is None:
        return []
    units = float(settings.fx_anchor_units_scale)
    lines = []
    for layer in _layers(scene):
        depth = float(settings.clouds_depth) * units * (1.0 + 0.45
                                                        * layer.index)
        obj = _object(scene, layer)
        polygons = len(obj.data.polygons) if obj is not None else 0
        lines.append("Layer %d: depth %.0f, %d polygons"
                     % (layer.index + 1, depth, polygons))
    flash = scene.get("ald_clouds_flash")
    if flash is not None:
        lines.append("Flash energy %.2f" % float(flash[0]))
    return lines


def remove(scene):
    collection = _collection(scene)
    settings = _settings(scene)
    if collection is None:
        if settings is not None:
            settings.cloud_layers.clear()
            settings.clouds_created = False
        return False
    for obj in list(collection.objects):
        mesh = obj.data if obj.type == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        if material.get(TAG) and material.users == 0:
            bpy.data.materials.remove(material)
    if settings is not None:
        settings.cloud_layers.clear()
        settings.clouds_created = False
    scene.pop("ald_clouds_signature", None)
    return True


def rebuild(scene):
    """Recreate the objects of a saved scene from its persistent layers."""
    settings = _settings(scene)
    if settings is None or len(settings.cloud_layers) == 0:
        return False
    if _collection(scene) is not None:
        return refresh(scene)
    from . import fx
    owner = _owner(scene)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    collection[TAG] = True
    collection[fx.OWNER_KEY] = owner
    collection["ald_schema"] = SCHEMA
    scene.collection.children.link(collection)
    for layer in settings.cloud_layers:
        mesh = bpy.data.meshes.new(layer.object_name)
        mesh[TAG] = True
        obj = bpy.data.objects.new(layer.object_name, mesh)
        obj[TAG] = True
        obj["ald_cloud_uid"] = layer.uid
        collection.objects.link(obj)
        _layout(scene, layer)
        _rebuild_mesh(scene, layer)
    scene["ald_clouds_signature"] = ""
    sync(scene)
    update_flash(scene)
    settings.clouds_created = True
    return True


@bpy.app.handlers.persistent
def _on_frame_change(*_args):
    for scene in bpy.data.scenes:
        try:
            from . import snapshot
            if snapshot.is_inactive(scene):
                continue
            if _collection(scene) is not None:
                update_flash(scene)
        except Exception:
            pass


@bpy.app.handlers.persistent
def _on_load_post(*_args):
    for scene in bpy.data.scenes:
        try:
            rebuild(scene)
        except Exception:
            pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(_on_frame_change)
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(_on_frame_change)
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
