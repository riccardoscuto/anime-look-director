"""Deterministic 3D FX: fireworks and shooting stars with real physics.

The system is evaluated analytically (see the technical guide):

* every particle state is a pure function of (seed, burst, particle, time),
  so frame jumps and re-renders are reproducible;
* time is expressed in seconds and the motion uses a linear drag model with a
  stable ballistic limit;
* trails, child sparks and the central flash are separate subsystems;
* geometry is allocated once and updated in place, so animation does not
  create or destroy objects every frame;
* FX data is owned per scene.
"""

import hashlib
import math

import bmesh
import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

FX_COLLECTION = "ALD | FX"
OWNER_KEY = "ald_fx_owner"
ID_KEY = "ald_fx_id"

FAMILIES = ("CHRYSANTHEMUM", "PEONY", "WILLOW")
FAMILY_LABELS = {
    "CHRYSANTHEMUM": "Chrysanthemum",
    "PEONY": "Peony",
    "WILLOW": "Willow",
}

FAMILY_CONFIG = {
    "CHRYSANTHEMUM": {
        "spokes": 110, "speed": 26.0, "drag": 1.3, "life": 2.6,
        "trail": 0.70, "sparks": 2, "core": 0.30, "pistil": 30,
    },
    "PEONY": {
        "spokes": 120, "speed": 28.0, "drag": 2.0, "life": 2.0,
        "trail": 0.12, "sparks": 0, "core": 0.22, "pistil": 24,
    },
    "WILLOW": {
        "spokes": 70, "speed": 18.0, "drag": 0.9, "life": 4.4,
        "trail": 1.40, "sparks": 2, "core": 0.24, "pistil": 18,
    },
}

PALETTES = (
    ((1.0, 0.34, 0.03), (1.0, 0.06, 0.02), (0.05, 1.0, 0.72)),
    ((1.0, 0.05, 0.44), (0.42, 0.05, 1.0), (1.0, 0.72, 0.02)),
    ((0.04, 0.72, 1.0), (0.05, 1.0, 0.32), (1.0, 0.22, 0.02)),
)

GRAVITY = Vector((0.0, 0.0, -9.81))
SAMPLES = 16
SYSTEMS = {}


# ---------------------------------------------------------------------------
# ownership helpers
# ---------------------------------------------------------------------------

def _scene_id(scene):
    ident = scene.get(ID_KEY)
    if not ident:
        ident = hashlib.blake2b(scene.name.encode("utf-8"),
                                digest_size=8).hexdigest()
        scene[ID_KEY] = ident
    return ident


def _collection(scene):
    owner = _scene_id(scene)
    for coll in bpy.data.collections:
        if coll.get(OWNER_KEY) == owner:
            return coll
    coll = bpy.data.collections.new(FX_COLLECTION)
    coll[OWNER_KEY] = owner
    scene.collection.children.link(coll)
    return coll


def _material(name, color, strength):
    key = "%s|%.3f|%.3f|%.3f|%.2f" % (name, color[0], color[1], color[2],
                                        strength)
    mat = bpy.data.materials.get(key)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(key)
    mat["ald_fx_material"] = True
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        rgba = (*color, 1.0)
        bsdf.inputs["Base Color"].default_value = rgba
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = strength
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = strength
        bsdf.inputs["Roughness"].default_value = 0.4
    return mat


# ---------------------------------------------------------------------------
# deterministic randomness and motion
# ---------------------------------------------------------------------------

def _hash_unit(seed, burst, particle, channel):
    payload = "%d|%d|%d|%d" % (int(seed), int(burst), int(particle),
                                int(channel))
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


def _hash_range(seed, burst, particle, channel, low, high):
    return low + (high - low) * _hash_unit(seed, burst, particle, channel)


def _fibonacci_direction(index, count, jitter, seed, burst):
    golden = math.pi * (3.0 - math.sqrt(5.0))
    z = 1.0 - (2.0 * index + 1.0) / count
    radius = math.sqrt(max(0.0, 1.0 - z * z))
    theta = golden * index
    theta += _hash_range(seed, burst, index, 7, -jitter, jitter)
    return Vector((math.cos(theta) * radius, math.sin(theta) * radius, z))


def _gn_points_object(scene, name, material, particles, trail=0.0,
                      age_offset=0.0, min_scale=0.35, decay_power=1.0,
                      gravity=None):
    """Build a points object whose motion is evaluated by Geometry Nodes."""
    from . import fx_nodes
    count = len(particles)
    mesh = bpy.data.meshes.new(name)
    mesh["ald_fx"] = True
    mesh.from_pydata([(0.0, 0.0, 0.0)] * count, [], [])
    mesh.update()
    for attr_name, attr_type, values in (
            ("birth", "FLOAT", [p["birth"] for p in particles]),
            ("life", "FLOAT", [p["life"] for p in particles]),
            ("drag", "FLOAT", [p["drag"] for p in particles]),
            ("radius", "FLOAT", [p["radius"] for p in particles]),
            ("tau", "FLOAT", [p["tau"] for p in particles]),
            ("use_decay", "FLOAT", [p["use_decay"] for p in particles]),
            ("vel", "FLOAT_VECTOR", [p["vel"] for p in particles]),
            ("pos0", "FLOAT_VECTOR", [p["pos0"] for p in particles]),
            ("jitter", "FLOAT_VECTOR", [p["jitter"] for p in particles])):
        attribute = mesh.attributes.new(attr_name, attr_type, "POINT")
        if attr_type == "FLOAT":
            attribute.data.foreach_set("value", values)
        else:
            flat = []
            for vector in values:
                flat.extend(vector)
            attribute.data.foreach_set("vector", flat)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    group, sockets = fx_nodes.build_burst_group()
    fx_nodes.attach_burst_modifier(obj, group, sockets,
                                   GRAVITY if gravity is None else gravity,
                                   material, trail=trail,
                                   age_offset=age_offset,
                                   min_scale=min_scale,
                                   decay_power=decay_power)
    return obj


def _gn_star_data(seed, index, config, spoke, spoke_count):
    """Deterministic lifetime and initial velocity of one primary star."""
    life = _hash_range(seed, index, spoke, 2, config["life"] * 0.6,
                       config["life"])
    direction = _fibonacci_direction(spoke, spoke_count, 0.35, seed, index)
    speed = _hash_range(seed, index, spoke, 3, config["speed"] * 0.75,
                        config["speed"] * 1.15)
    return life, direction * speed


def _gn_head_particles(seed, index, config, birth, center, size_scale,
                       spoke_count):
    """Point data of the star heads, evaluated by Geometry Nodes."""
    particles = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        particles.append({
            "birth": birth, "life": life, "drag": config["drag"],
            "radius": 0.13 * size_scale, "vel": v0, "pos0": center,
            "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
        })
    return particles


def _gn_bead_particles(seed, index, config, birth, center, size_scale,
                       spoke_count, slot):
    """Point data of the trail grains of one colour slot."""
    particles = []
    spokes = [s for s in range(spoke_count) if s % 3 == slot]
    for spoke in spokes:
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        for step in range(SAMPLES):
            profile = step / (SAMPLES - 1.0)
            scatter = 0.10 * size_scale * (1.0 - profile)
            jitter = Vector((
                _hash_range(seed, index, spoke * 16 + step, 20,
                            -scatter, scatter),
                _hash_range(seed, index, spoke * 16 + step, 21,
                            -scatter, scatter),
                _hash_range(seed, index, spoke * 16 + step, 22,
                            -scatter, scatter),
            ))
            grain = 0.65 + 0.7 * _hash_unit(seed, index, spoke * 16 + step, 23)
            particles.append({
                "birth": birth, "life": life, "drag": config["drag"],
                "radius": 0.05 * size_scale * (0.25 + 0.75 * profile) * grain,
                "vel": v0, "pos0": center,
                "tau": config["trail"] * (1.0 - profile),
                "jitter": jitter, "use_decay": 0.0,
            })
    return particles


def _gn_pistil_particles(seed, index, config, birth, center, size_scale,
                         pistil_count, grains=False):
    """Point data of the inner pistil population (heads or trail grains)."""
    particles = []
    for spoke in range(pistil_count):
        life = _hash_range(seed, index, spoke + 500, 2,
                           config["life"] * 0.6 * 0.85, config["life"] * 0.85)
        direction = _fibonacci_direction(spoke, pistil_count, 0.35, seed, index)
        speed = _hash_range(seed, index, spoke + 500, 3,
                            config["speed"] * 0.75 * 0.68,
                            config["speed"] * 1.15 * 0.68)
        v0 = direction * speed
        drag = config["drag"] * 1.2
        if grains:
            for step in range(SAMPLES):
                profile = step / (SAMPLES - 1.0)
                particles.append({
                    "birth": birth, "life": life, "drag": drag,
                    "radius": 0.028 * size_scale * (0.25 + 0.75 * profile),
                    "vel": v0, "pos0": center,
                    "tau": config["trail"] * 0.6 * (1.0 - profile),
                    "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 0.0,
                })
        else:
            particles.append({
                "birth": birth, "life": life, "drag": drag,
                "radius": 0.10 * size_scale, "vel": v0, "pos0": center,
                "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
            })
    return particles


def _gn_spark_particles(seed, index, config, birth, center, size_scale,
                         spoke_count):
    """Point data of the child sparks.

    The emission point is the position of the parent star at the emission
    time: the spark is a body of its own, not a particle of a moving source.
    """
    particles = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        for child in range(config["sparks"]):
            emit = _hash_range(seed, index, spoke * 8 + child, 4, 0.05,
                               life * 0.55)
            child_life = _hash_range(seed, index, spoke * 8 + child, 5, 0.45,
                                     1.5)
            parent_pos = _position(center, v0, config["drag"], emit)
            parent_vel = _velocity(v0, config["drag"], emit)
            perturb = Vector((
                _hash_range(seed, index, spoke * 8 + child, 6, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 7, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 8, -1.6, 1.6),
            )) * 1.2
            particles.append({
                "birth": birth + emit, "life": child_life, "drag": 2.4,
                "radius": 0.045 * size_scale,
                "vel": parent_vel * 0.35 + perturb, "pos0": parent_pos,
                "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
            })
    return particles


def _gn_trail_object(scene, name, material, particles, trail=0.0,
                     age_offset=0.0, radius=0.02, fade_window=0.0):
    """Build a curve object whose motion is evaluated by Geometry Nodes."""
    from . import fx_nodes
    count = len(particles)
    mesh = bpy.data.meshes.new(name)
    mesh["ald_fx"] = True
    mesh.from_pydata([(0.0, 0.0, 0.0)] * count, [], [])
    mesh.update()
    for attr_name, attr_type, values in (
            ("birth", "FLOAT", [p["birth"] for p in particles]),
            ("life", "FLOAT", [p["life"] for p in particles]),
            ("drag", "FLOAT", [p["drag"] for p in particles]),
            ("radius", "FLOAT", [p["radius"] for p in particles]),
            ("tau", "FLOAT", [p["tau"] for p in particles]),
            ("weight", "FLOAT", [float(p["weight"]) for p in particles]),
            ("curve_id", "INT", [int(p["curve_id"]) for p in particles]),
            ("vel", "FLOAT_VECTOR", [p["vel"] for p in particles]),
            ("pos0", "FLOAT_VECTOR", [p["pos0"] for p in particles]),
            ("jitter", "FLOAT_VECTOR", [p["jitter"] for p in particles])):
        attribute = mesh.attributes.new(attr_name, attr_type, "POINT")
        if attr_type == "FLOAT_VECTOR":
            flat = []
            for vector in values:
                flat.extend(vector)
            attribute.data.foreach_set("vector", flat)
        else:
            attribute.data.foreach_set("value", values)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    group, sockets = fx_nodes.build_trail_group()
    fx_nodes.attach_trail_modifier(obj, group, sockets, GRAVITY, material,
                                   trail=trail, age_offset=age_offset,
                                   radius=radius, fade_window=fade_window)
    return obj


def _gn_trail_particles(seed, index, config, birth, center, spoke_count, slot):
    """Point data of the thin filament of every star of one colour slot."""
    particles = []
    spokes = [s for s in range(spoke_count) if s % 3 == slot]
    for spoke in spokes:
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        for step in range(SAMPLES):
            profile = step / (SAMPLES - 1.0)
            particles.append({
                "birth": birth, "life": life, "drag": config["drag"],
                "radius": 0.25 + 0.9 * profile ** 1.4,
                "vel": v0, "pos0": center,
                "tau": config["trail"] * (1.0 - profile),
                "jitter": Vector((0.0, 0.0, 0.0)),
                "curve_id": spoke, "weight": step,
            })
    return particles


def _gn_flash_particles(birth, core, center, size_scale):
    """Point data of the central flash of a burst."""
    return [{
        "birth": birth, "life": core, "drag": 100.0,
        "radius": 0.25 * size_scale, "vel": Vector((0.0, 0.0, 0.0)),
        "pos0": center, "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)),
        "use_decay": 1.0,
    }]


def _star_state(seed, index, spoke, count, config, age, speed_scale=1.0,
                life_scale=1.0, hash_offset=0):
    """Deterministic state of one primary star at a given age."""
    life = _hash_range(seed, index, spoke + hash_offset, 2,
                       config["life"] * 0.6 * life_scale,
                       config["life"] * life_scale)
    direction = _fibonacci_direction(spoke, count, 0.35, seed, index)
    speed = _hash_range(seed, index, spoke + hash_offset, 3,
                        config["speed"] * 0.75 * speed_scale,
                        config["speed"] * 1.15 * speed_scale)
    v0 = direction * speed
    alive = 0.0 <= age <= life
    return direction, life, v0, alive


def _position(p0, v0, drag, age):
    """Position at ``age`` seconds with linear drag and world gravity."""
    if age <= 0.0:
        return p0.copy()
    if drag < 1e-4:
        return p0 + v0 * age + 0.5 * GRAVITY * (age * age)
    v_inf = GRAVITY / drag
    decay = math.exp(-drag * age)
    factor = (1.0 - decay) / drag
    return p0 + v_inf * age + (v0 - v_inf) * factor


def _velocity(v0, drag, age):
    if drag < 1e-4:
        return v0 + GRAVITY * age
    v_inf = GRAVITY / drag
    return v_inf + (v0 - v_inf) * math.exp(-drag * age)


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

_SPHERE = None


def _unit_sphere():
    global _SPHERE
    if _SPHERE is None:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        verts = [tuple(v.co) for v in bm.verts]
        faces = [tuple(v.index for v in face.verts) for face in bm.faces]
        bm.free()
        _SPHERE = (verts, faces)
    return _SPHERE


def _build_particle_mesh(name, centers, radii, material):
    """One mesh holding every particle; returns (object, ranges)."""
    verts, faces = _unit_sphere()
    vertices = []
    all_faces = []
    for index, (center, radius) in enumerate(zip(centers, radii)):
        for vx, vy, vz in verts:
            vertices.append((center.x + vx * radius, center.y + vy * radius,
                             center.z + vz * radius))
        offset = index * len(verts)
        for face in faces:
            all_faces.append(tuple(vertex + offset for vertex in face))
    mesh = bpy.data.meshes.new(name)
    mesh["ald_fx"] = True
    mesh.from_pydata(vertices, [], all_faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    ranges = [(index * len(verts), len(verts))
              for index in range(len(centers))]
    return obj, ranges


def _write_particle_mesh(mesh, ranges, centers, radii):
    verts, _faces = _unit_sphere()
    count = len(verts)
    data = []
    for index, (center, radius) in enumerate(zip(centers, radii)):
        start = ranges[index][0]
        for vx, vy, vz in verts:
            data.append(center.x + vx * radius)
            data.append(center.y + vy * radius)
            data.append(center.z + vz * radius)
    if data:
        mesh.vertices.foreach_set("co", data)
        mesh.update()


def _build_curve(scene, name, spline_count, materials, width):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve["ald_fx"] = True
    curve.dimensions = "3D"
    curve.bevel_depth = width
    curve.bevel_resolution = 2
    curve.resolution_u = 2
    for mat in materials:
        curve.materials.append(mat)
    for index in range(spline_count):
        spline = curve.splines.new("POLY")
        spline.points.add(SAMPLES - 1)
        spline.material_index = index % max(len(materials), 1)
    obj = bpy.data.objects.new(name, curve)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _camera_basis(scene):
    camera = scene.camera
    if camera is None:
        return (Vector((0.0, -8.0, 1.5)), Vector((0.0, 1.0, 0.0)),
                Vector((0.0, 0.0, 1.0)), Vector((1.0, 0.0, 0.0)))
    if camera.parent is None:
        # Read the local transform directly: matrix_world can be stale when the
        # FX are created right after moving the camera.
        origin = camera.location.copy()
        rotation = camera.rotation_euler.to_quaternion()
    else:
        matrix = camera.matrix_world
        origin = matrix.translation
        rotation = matrix.to_quaternion()
    return (origin,
            (rotation @ Vector((0.0, 0.0, -1.0))).normalized(),
            (rotation @ Vector((0.0, 1.0, 0.0))).normalized(),
            (rotation @ Vector((1.0, 0.0, 0.0))).normalized())


def _burst_center(origin, forward, up, right, index, total, distance,
                 spread=1.0):
    spread_x = (-0.18 + 0.36 * (index + 0.5) / max(total, 1)) * spread
    spread_y = (0.05 + 0.05 * math.sin(index * 1.7)) * spread
    return (origin + forward * distance + right * distance * spread_x
            + up * distance * spread_y)


# ---------------------------------------------------------------------------
# fireworks
# ---------------------------------------------------------------------------

def _build_fireworks(scene, count, seed, distance, family):
    origin, forward, up, right = _camera_basis(scene)
    kind = "fireworks"
    size_scale = max(0.6, min(2.0, distance / 60.0))
    settings = getattr(scene, "ald", None)
    spread = float(getattr(settings, "fx_burst_spread", 1.0)) if settings else 1.0
    offset = Vector(getattr(settings, "fx_composition_offset", (0.0, 0.0, 0.0))) \
        if settings else Vector((0.0, 0.0, 0.0))
    bursts = []
    for index in range(max(1, count)):
        # Composition: the first burst is the hero, the others are secondary
        # and staggered in time so the sky is never a uniform field.
        role = index % 3
        family_key = family if index == 0 else FAMILIES[(index - 1) % len(FAMILIES)]
        config = FAMILY_CONFIG[family_key]
        family_distance = distance * (1.0 if index == 0 else
                                      (0.78 if role == 1 else 0.58))
        center = _burst_center(origin, forward, up, right, index, count,
                                family_distance * (0.85 + 0.25 *
                                                   _hash_unit(seed, index, 0, 1)),
                                spread) + offset
        birth = 0.0 if index == 0 else (0.25 if role == 1 else 0.85)
        family_colors = PALETTES[index % len(PALETTES)]
        materials = [
            _material("ALD FX %s %d A" % (family_key, index), family_colors[0],
                      6.0),
            _material("ALD FX %s %d B" % (family_key, index), family_colors[1],
                      6.0),
            _material("ALD FX %s %d C" % (family_key, index), family_colors[2],
                      6.0),
        ]
        spoke_count = config["spokes"]
        trail_obj = _build_curve(scene, "ALD FX %s %d Filament" % (family_key, index),
                                 spoke_count, materials, 0.022 * size_scale)
        trail_obj["ald_fx_kind"] = kind
        # Beaded spark trails: a chain of small emissive grains per star,
        # exactly like the granular string of sparks in the references.
        bead_objects = []
        for slot in range(3):
            spokes = [s for s in range(spoke_count) if s % 3 == slot]
            count = len(spokes) * SAMPLES
            bead_obj, bead_ranges = _build_particle_mesh(
                "ALD FX %s %d Beads %d" % (family_key, index, slot),
                [center] * count, [0.001] * count, materials[slot])
            _collection(scene).objects.link(bead_obj)
            bead_obj["ald_fx_kind"] = kind
            bead_objects.append((bead_obj, bead_ranges, spokes))
        head_obj, head_ranges = _build_particle_mesh(
            "ALD FX %s %d Heads" % (family_key, index),
            [center] * spoke_count, [0.001] * spoke_count, materials[0])
        _collection(scene).objects.link(head_obj)
        head_obj["ald_fx_kind"] = kind
        gn_heads = None
        gn_beads = []
        gn_pistil = None
        gn_sparks = None
        # Inner contrasting pistil population (the classic Hanabi core).
        pistil_count = config["pistil"]
        pistil_obj, pistil_ranges = _build_particle_mesh(
            "ALD FX %s %d Pistil Heads" % (family_key, index),
            [center] * pistil_count, [0.001] * pistil_count, materials[1])
        _collection(scene).objects.link(pistil_obj)
        pistil_obj["ald_fx_kind"] = kind
        pistil_bead_obj, pistil_bead_ranges = _build_particle_mesh(
            "ALD FX %s %d Pistil Beads" % (family_key, index),
            [center] * (pistil_count * SAMPLES),
            [0.001] * (pistil_count * SAMPLES), materials[1])
        _collection(scene).objects.link(pistil_bead_obj)
        pistil_bead_obj["ald_fx_kind"] = kind
        spark_total = spoke_count * config["sparks"]
        spark_obj, spark_ranges = _build_particle_mesh(
            "ALD FX %s %d Sparks" % (family_key, index),
            [center] * spark_total, [0.001] * spark_total, materials[2])
        _collection(scene).objects.link(spark_obj)
        spark_obj["ald_fx_kind"] = kind
        core_obj, core_ranges = _build_particle_mesh(
            "ALD FX %s %d Flash" % (family_key, index), [center], [0.001],
            materials[1])
        _collection(scene).objects.link(core_obj)
        core_obj["ald_fx_kind"] = kind
        # Geometry Nodes prototype: the burst particles are evaluated by the
        # node group instead of Python.
        use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
            else False
        if use_gn:
            created = []
            try:
                age_offset = float(getattr(settings, "fx_age", 0.0)) \
                    if settings else 0.0
                gn_heads = _gn_points_object(
                    scene, "ALD FX GN Heads %d" % index, materials[0],
                    _gn_head_particles(seed, index, config, birth, center,
                                       size_scale, spoke_count),
                    trail=0.0, age_offset=age_offset)
                created.append(gn_heads)
                for slot in range(3):
                    bead_gn = _gn_points_object(
                        scene, "ALD FX GN Beads %d %d" % (index, slot),
                        materials[slot],
                        _gn_bead_particles(seed, index, config, birth, center,
                                           size_scale, spoke_count, slot),
                        trail=config["trail"], age_offset=age_offset)
                    created.append(bead_gn)
                    gn_beads.append(bead_gn)
                gn_pistil = _gn_points_object(
                    scene, "ALD FX GN Pistil %d" % index, materials[1],
                    _gn_pistil_particles(seed, index, config, birth, center,
                                         size_scale, pistil_count),
                    trail=0.0, age_offset=age_offset)
                created.append(gn_pistil)
                gn_pistil_grains = _gn_points_object(
                    scene, "ALD FX GN Pistil Grains %d" % index, materials[1],
                    _gn_pistil_particles(seed, index, config, birth, center,
                                         size_scale, pistil_count, grains=True),
                    trail=config["trail"] * 0.6, age_offset=age_offset)
                created.append(gn_pistil_grains)
                gn_beads.append(gn_pistil_grains)
                gn_sparks = _gn_points_object(
                    scene, "ALD FX GN Sparks %d" % index, materials[2],
                    _gn_spark_particles(seed, index, config, birth, center,
                                        size_scale, spoke_count),
                    trail=0.0, age_offset=age_offset, min_scale=0.0)
                created.append(gn_sparks)
                for slot in range(3):
                    trail_gn = _gn_trail_object(
                        scene, "ALD FX GN Trail %d %d" % (index, slot),
                        materials[slot],
                        _gn_trail_particles(seed, index, config, birth, center,
                                            spoke_count, slot),
                        trail=config["trail"], age_offset=age_offset,
                        radius=0.022 * size_scale)
                    created.append(trail_gn)
                gn_flash = _gn_points_object(
                    scene, "ALD FX GN Flash %d" % index, materials[1],
                    _gn_flash_particles(birth, config["core"], center,
                                        size_scale),
                    trail=0.0, age_offset=age_offset, min_scale=0.0,
                    decay_power=0.5)
                created.append(gn_flash)
                # The Python meshes are replaced by the node group.
                for python_obj in (head_obj, pistil_obj, pistil_bead_obj,
                                   spark_obj, trail_obj, core_obj):
                    bpy.data.objects.remove(python_obj, do_unlink=True)
                for bead_obj, _bead_ranges, _spokes in bead_objects:
                    bpy.data.objects.remove(bead_obj, do_unlink=True)
                head_obj = None
                head_ranges = []
                bead_objects = []
                pistil_obj = None
                pistil_ranges = []
                pistil_bead_obj = None
                pistil_bead_ranges = []
                spark_obj = None
                spark_ranges = []
                trail_obj = None
                core_obj = None
                core_ranges = []
                # The replaced Python meshes must not survive as orphans.
                _cleanup_orphans()
            except Exception:
                for obj in created:
                    if obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                gn_heads = None
                gn_beads = []
                gn_pistil = None
                gn_sparks = None
        bursts.append({
            "index": index, "family": family_key, "config": config,
            "center": center, "birth": birth, "seed": seed,
            "size_scale": size_scale, "materials": materials,
            "trail": trail_obj, "heads": head_obj, "head_ranges": head_ranges,
            "gn_heads": gn_heads, "gn_beads": gn_beads,
            "gn_pistil": gn_pistil, "gn_sparks": gn_sparks,
            "beads": bead_objects,
            "pistil": (pistil_obj, pistil_ranges, pistil_bead_obj,
                       pistil_bead_ranges, pistil_count),
            "sparks": spark_obj, "spark_ranges": spark_ranges,
            "core": core_obj, "core_ranges": core_ranges,
        })
    return {"kind": "fireworks", "bursts": bursts, "time": None,
            "gn": all(burst.get("gn_heads") is not None for burst in bursts)}


def _update_fireworks(system, time):
    for burst in system["bursts"]:
        config = burst["config"]
        center = burst["center"]
        seed = burst["seed"]
        index = burst["index"]
        age = time - burst["birth"]
        spoke_count = config["spokes"]
        gn_heads = burst.get("gn_heads")
        gn_pistil = burst.get("gn_pistil")
        gn_sparks = burst.get("gn_sparks")
        trail_data = burst["trail"].data if burst["trail"] is not None else None
        head_centers = []
        head_radii = []
        spark_centers = []
        spark_radii = []
        bead_centers = [[], [], []]
        bead_radii = [[], [], []]
        for spoke in range(spoke_count) if gn_heads is None else ():
            life = _hash_range(seed, index, spoke, 2, config["life"] * 0.6,
                               config["life"])
            direction = _fibonacci_direction(spoke, spoke_count, 0.35, seed,
                                             index)
            speed = _hash_range(seed, index, spoke, 3, config["speed"] * 0.75,
                                config["speed"] * 1.15)
            v0 = direction * speed
            alive = 0.0 <= age <= life
            spline = trail_data.splines[spoke] if trail_data else None
            trail_time = min(age, config["trail"]) if alive else 0.0
            for step in range(SAMPLES):
                tau = trail_time * (1.0 - step / (SAMPLES - 1.0))
                sample_age = max(0.0, age - tau)
                point = _position(center, v0, config["drag"], sample_age)
                profile = step / (SAMPLES - 1.0)
                if not alive:
                    point = center + Vector((0.0, 0.0, 1000.0))
                if spline is not None:
                    spline.points[step].co = (point.x, point.y, point.z, 1.0)
                    spline.points[step].radius = 0.25 + 0.9 * profile ** 1.4
                slot = spoke % 3
                bead_centers[slot].append(point)
                if alive:
                    scatter = 0.10 * burst["size_scale"] * (1.0 - profile)
                    jitter = Vector((
                        _hash_range(seed, index, spoke * 16 + step, 20,
                                    -scatter, scatter),
                        _hash_range(seed, index, spoke * 16 + step, 21,
                                    -scatter, scatter),
                        _hash_range(seed, index, spoke * 16 + step, 22,
                                    -scatter, scatter),
                    ))
                    bead_centers[slot][-1] = point + jitter
                    grain = 0.65 + 0.7 * _hash_unit(seed, index,
                                                   spoke * 16 + step, 23)
                    bead_radii[slot].append(
                        0.05 * burst["size_scale"] * (0.25 + 0.75 * profile)
                        * grain)
                else:
                    bead_radii[slot].append(0.0001)
            head = _position(center, v0, config["drag"], max(0.0, age))
            radius = 0.13 * burst["size_scale"]
            if not alive:
                head = center + Vector((0.0, 0.0, 1000.0))
                radius = 0.0001
            else:
                radius *= 0.35 + 0.65 * (1.0 - age / max(life, 1e-3))
            head_centers.append(head)
            head_radii.append(radius)
            for child in range(config["sparks"]) if not gn_sparks else ():
                emit = _hash_range(seed, index, spoke * 8 + child, 4, 0.05,
                                  life * 0.55)
                child_age = age - emit
                child_life = _hash_range(seed, index, spoke * 8 + child, 5,
                                         0.45, 1.5)
                if child_age <= 0.0 or child_age > child_life:
                    spark_centers.append(center + Vector((0.0, 0.0, 1000.0)))
                    spark_radii.append(0.0001)
                    continue
                parent_pos = _position(center, v0, config["drag"], age - emit)
                parent_vel = _velocity(v0, config["drag"], age - emit)
                perturb = Vector((
                    _hash_range(seed, index, spoke * 8 + child, 6, -1.6, 1.6),
                    _hash_range(seed, index, spoke * 8 + child, 7, -1.6, 1.6),
                    _hash_range(seed, index, spoke * 8 + child, 8, -1.6, 1.6),
                )) * 1.2
                child_v0 = parent_vel * 0.35 + perturb
                spark_centers.append(_position(parent_pos, child_v0, 2.4,
                                              child_age))
                spark_radii.append(0.045 * burst["size_scale"]
                                   * (1.0 - child_age / max(child_life, 1e-3)))
        # Inner contrasting pistil: a smaller, slower population.
        (pistil_obj, pistil_ranges, pistil_bead_obj, pistil_bead_ranges,
         pistil_count) = burst["pistil"]
        pistil_centers = []
        pistil_radii = []
        pistil_bead_centers = []
        pistil_bead_radii = []
        for spoke in range(pistil_count) if not gn_pistil else ():
            direction, life, v0, alive = _star_state(
                seed, index, spoke, pistil_count, config, age,
                speed_scale=0.68, life_scale=0.85, hash_offset=500)
            drag = config["drag"] * 1.2
            if alive:
                head = _position(center, v0, drag, age)
                pistil_centers.append(head)
                pistil_radii.append(
                    0.10 * burst["size_scale"]
                    * (0.35 + 0.65 * (1.0 - age / max(life, 1e-3))))
            else:
                pistil_centers.append(center + Vector((0.0, 0.0, 1000.0)))
                pistil_radii.append(0.0001)
            trail_time = min(age, config["trail"] * 0.6) if alive else 0.0
            for step in range(SAMPLES):
                tau = trail_time * (1.0 - step / (SAMPLES - 1.0))
                point = _position(center, v0, drag, max(0.0, age - tau))
                profile = step / (SAMPLES - 1.0)
                if not alive:
                    point = center + Vector((0.0, 0.0, 1000.0))
                pistil_bead_centers.append(point)
                if alive:
                    pistil_bead_radii.append(
                        0.028 * burst["size_scale"] * (0.25 + 0.75 * profile))
                else:
                    pistil_bead_radii.append(0.0001)

        if burst.get("gn_heads") is None:
            _write_particle_mesh(burst["heads"].data, burst["head_ranges"],
                                 head_centers, head_radii)
        if gn_pistil is None:
            _write_particle_mesh(pistil_obj.data, pistil_ranges,
                                 pistil_centers, pistil_radii)
            _write_particle_mesh(pistil_bead_obj.data, pistil_bead_ranges,
                                 pistil_bead_centers, pistil_bead_radii)
        for slot, (bead_obj, bead_ranges, _spokes) in enumerate(burst["beads"]):
            _write_particle_mesh(bead_obj.data, bead_ranges,
                                 bead_centers[slot], bead_radii[slot])
        if spark_centers and gn_sparks is None:
            _write_particle_mesh(burst["sparks"].data, burst["spark_ranges"],
                                 spark_centers, spark_radii)
        # Central flash: bright for a fraction of a second only.
        if burst["core"] is not None:
            core_centers = [center]
            core_radii = [0.001]
            if 0.0 <= age < config["core"]:
                energy = 1.0 - age / max(config["core"], 1e-3)
                core_radii = [0.25 * burst["size_scale"] * energy ** 0.5]
            else:
                core_centers = [center + Vector((0.0, 0.0, 1000.0))]
            _write_particle_mesh(burst["core"].data, burst["core_ranges"],
                                 core_centers, core_radii)


# ---------------------------------------------------------------------------
# shooting stars
# ---------------------------------------------------------------------------

def _gn_meteor_particles(seed, index, life, start, v0, drag, size):
    """Point data of one meteor head."""
    return [{
        "birth": 0.0, "life": life, "drag": drag, "radius": 0.18,
        "vel": v0, "pos0": start, "tau": 0.0,
        "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 0.0,
    }]


def _gn_meteor_train_particles(seed, index, start, v0, drag, train):
    """Point data of the persistent train of one meteor."""
    particles = []
    for step in range(SAMPLES):
        profile = step / (SAMPLES - 1.0)
        particles.append({
            "birth": 0.0, "life": 10.0, "drag": drag,
            "radius": 0.2 + 0.8 * profile,
            "vel": v0, "pos0": start,
            "tau": train * (1.0 - profile),
            "jitter": Vector((0.0, 0.0, 0.0)),
            "curve_id": index, "weight": step,
        })
    return particles


def _gn_meteor_fragment_particles(seed, index, life, start, v0, drag):
    """Point data of the burning fragments of one meteor."""
    particles = []
    for fragment in range(3):
        emit = _hash_range(seed, index, 30 + fragment, 7, 0.05, life * 0.8)
        frag_life = _hash_range(seed, index, 30 + fragment, 8, 0.4, 1.4)
        parent = _position(start, v0, drag, emit)
        parent_vel = v0 * math.exp(-drag * emit)
        push = Vector((
            _hash_range(seed, index, 30 + fragment, 9, -2.4, 2.4),
            _hash_range(seed, index, 30 + fragment, 10, -2.4, 2.4),
            _hash_range(seed, index, 30 + fragment, 11, -3.2, 1.2),
        ))
        particles.append({
            "birth": emit, "life": frag_life, "drag": 1.6, "radius": 0.05,
            "vel": parent_vel * 0.25 + push, "pos0": parent,
            "tau": 0.0, "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 1.0,
        })
    return particles


def _build_meteors(scene, count, seed, distance):
    origin, forward, up, right = _camera_basis(scene)
    radiant = (forward * 0.86 + up * 0.42 + right * 0.28).normalized()
    material = _material("ALD FX Meteor", (0.85, 0.94, 1.0), 9.0)
    settings = getattr(scene, "ald", None)
    use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
        else False
    age_offset = float(getattr(settings, "fx_age", 0.0)) if settings else 0.0
    system = {"kind": "meteors", "count": count, "seed": seed,
              "distance": distance, "radiant": radiant, "origin": origin,
              "material": material, "gn": False, "trail": None,
              "heads": None, "head_ranges": [], "fragments": None,
              "fragment_ranges": []}
    total = max(1, count)
    if use_gn:
        created = []
        try:
            head_points = []
            train_points = []
            fragment_points = []
            for index in range(total):
                life = _hash_range(seed, index, 0, 2, 0.55, 1.15)
                spread = Vector((
                    _hash_range(seed, index, 0, 3, -0.09, 0.09),
                    _hash_range(seed, index, 0, 4, -0.06, 0.06),
                    _hash_range(seed, index, 0, 5, -0.04, 0.04),
                ))
                direction = (radiant + spread).normalized()
                start = origin + direction * distance * 0.9
                speed = _hash_range(seed, index, 0, 6, 26.0, 38.0)
                v0 = direction * speed
                head_points.append({
                    "birth": index * 0.9 + _hash_range(seed, index, 0, 1,
                                                       0.0, 0.6),
                    "life": life, "drag": 0.08, "radius": 0.18,
                    "vel": v0, "pos0": start, "tau": 0.0,
                    "jitter": Vector((0.0, 0.0, 0.0)), "use_decay": 0.0,
                })
                train_points.extend(_gn_meteor_train_particles(
                    seed, index, start, v0, 0.08, 0.32))
                fragment_points.extend(_gn_meteor_fragment_particles(
                    seed, index, life, start, v0, 0.08))
            gn_heads = _gn_points_object(
                scene, "ALD FX GN Meteor Heads", material, head_points,
                trail=0.0, age_offset=age_offset)
            created.append(gn_heads)
            gn_train = _gn_trail_object(
                scene, "ALD FX GN Meteor Trails", material, train_points,
                trail=0.32, age_offset=age_offset, radius=0.07,
                fade_window=0.32)
            created.append(gn_train)
            gn_fragments = _gn_points_object(
                scene, "ALD FX GN Meteor Fragments", material, fragment_points,
                trail=0.0, age_offset=age_offset, min_scale=0.0)
            created.append(gn_fragments)
            for obj in created:
                obj["ald_fx_kind"] = "meteors"
            system["gn"] = True
            return system
        except Exception as exc:
            print("ALD FX: geometry nodes meteors failed (%s)" % exc)
            for obj in created:
                if obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            _cleanup_orphans()
            # The material may have been purged with the failed objects.
            material = _material("ALD FX Meteor", (0.85, 0.94, 1.0), 9.0)
    trail_obj = _build_curve(scene, "ALD FX Meteor Trails", total,
                             [material], 0.07)
    trail_obj["ald_fx_kind"] = "meteors"
    head_obj, head_ranges = _build_particle_mesh(
        "ALD FX Meteor Heads", [origin] * total, [0.001] * total, material)
    _collection(scene).objects.link(head_obj)
    head_obj["ald_fx_kind"] = "meteors"
    fragment_obj, fragment_ranges = _build_particle_mesh(
        "ALD FX Meteor Fragments", [origin] * (total * 3),
        [0.001] * (total * 3), material)
    _collection(scene).objects.link(fragment_obj)
    fragment_obj["ald_fx_kind"] = "meteors"
    system.update({"trail": trail_obj, "heads": head_obj,
                   "head_ranges": head_ranges, "fragments": fragment_obj,
                   "fragment_ranges": fragment_ranges})
    return system


def _update_meteors(system, time):
    if system.get("gn"):
        # The node group evaluates the meteors: no Python work per frame.
        return
    count = system["count"]
    seed = system["seed"]
    origin = system["origin"]
    radiant = system["radiant"]
    distance = system["distance"]
    trail_data = system["trail"].data
    head_centers = []
    head_radii = []
    fragment_centers = []
    fragment_radii = []
    for index in range(max(1, count)):
        birth = index * 0.9 + _hash_range(seed, index, 0, 1, 0.0, 0.6)
        age = time - birth
        life = _hash_range(seed, index, 0, 2, 0.55, 1.15)
        spline = trail_data.splines[index]
        alive = 0.0 < age <= life
        # The persistent train outlives the head for a short while.
        train = min(max(age, 0.0), 0.32)
        if age > life:
            train = max(0.0, 0.32 - (age - life)) if age - life < 0.32 else 0.0
        spread = Vector((
            _hash_range(seed, index, 0, 3, -0.09, 0.09),
            _hash_range(seed, index, 0, 4, -0.06, 0.06),
            _hash_range(seed, index, 0, 5, -0.04, 0.04),
        ))
        direction = (radiant + spread).normalized()
        start = origin + direction * distance * 0.9
        speed = _hash_range(seed, index, 0, 6, 26.0, 38.0)
        v0 = direction * speed
        for step in range(SAMPLES):
            tau = train * (1.0 - step / (SAMPLES - 1.0))
            point = _position(start, v0, 0.08, max(0.0, age - tau))
            if train <= 0.0:
                point = origin + Vector((0.0, 0.0, 1000.0))
            spline.points[step].co = (point.x, point.y, point.z, 1.0)
            fade = 1.0
            if age > life:
                fade = max(0.0, 1.0 - (age - life) / 0.32)
            spline.points[step].radius = (0.2 + 0.8 * (step / (SAMPLES - 1.0))) \
                * fade
        head = _position(start, v0, 0.08, max(0.0, age))
        radius = 0.18
        if not alive:
            head = origin + Vector((0.0, 0.0, 1000.0))
            radius = 0.0001
        head_centers.append(head)
        head_radii.append(radius)
        # Fragments: small embers that keep burning after the meteor.
        for fragment in range(3):
            emit = _hash_range(seed, index, 30 + fragment, 7, 0.05, life * 0.8)
            frag_age = age - emit
            frag_life = _hash_range(seed, index, 30 + fragment, 8, 0.4, 1.4)
            if frag_age <= 0.0 or frag_age > frag_life:
                fragment_centers.append(origin + Vector((0.0, 0.0, 1000.0)))
                fragment_radii.append(0.0001)
                continue
            parent = _position(start, v0, 0.08, age - emit)
            parent_vel = v0 * math.exp(-0.08 * (age - emit))
            push = Vector((
                _hash_range(seed, index, 30 + fragment, 9, -2.4, 2.4),
                _hash_range(seed, index, 30 + fragment, 10, -2.4, 2.4),
                _hash_range(seed, index, 30 + fragment, 11, -3.2, 1.2),
            ))
            fragment_centers.append(_position(parent, parent_vel * 0.25 + push,
                                               1.6, frag_age))
            fragment_radii.append(0.05 * (1.0 - frag_age / max(frag_life, 1e-3)))
    _write_particle_mesh(system["heads"].data, system["head_ranges"],
                         head_centers, head_radii)
    _write_particle_mesh(system["fragments"].data, system["fragment_ranges"],
                         fragment_centers, fragment_radii)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def _update_system(system, time):
    if system.get("gn"):
        # Every particle is evaluated by the node group.
        system["time"] = time
        return
    if system["kind"] == "fireworks":
        _update_fireworks(system, time)
    else:
        _update_meteors(system, time)
    system["time"] = time


def _registry(scene):
    return SYSTEMS.setdefault(_scene_id(scene), {})


def _cleanup_orphans():
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in list(datablocks):
            if (block.get("ald_fx") or block.get("ald_fx_material")) \
                    and block.users == 0:
                datablocks.remove(block)


def _remove_kind(scene, kind):
    owner = _scene_id(scene)
    for coll in bpy.data.collections:
        if coll.get(OWNER_KEY) != owner:
            continue
        for obj in list(coll.objects):
            if obj.get("ald_fx") and obj.get("ald_fx_kind") == kind:
                bpy.data.objects.remove(obj, do_unlink=True)
    _cleanup_orphans()


def create_fireworks(scene, count=3, seed=7, distance=110.0, time=0.0,
                     fps=24.0, family="CHRYSANTHEMUM"):
    """Create (or replace) a deterministic multi-burst firework system."""
    _remove_kind(scene, "fireworks")
    system = _build_fireworks(scene, count, seed, distance, family)
    _update_system(system, time)
    _registry(scene)["fireworks"] = system
    return count


def create_meteors(scene, count=4, seed=21, distance=140.0, time=0.0,
                   fps=24.0):
    """Create (or replace) a deterministic meteor shower."""
    _remove_kind(scene, "meteors")
    system = _build_meteors(scene, count, seed, distance)
    _update_system(system, time)
    _registry(scene)["meteors"] = system
    return count


def update(scene, time=None):
    """Re-evaluate every FX system of a scene at the given time."""
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return False
    if time is None:
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        time = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
    for system in registry.values():
        if system:
            _update_system(system, time)
    return True


def systems_info(scene):
    """Return the FX systems present in a scene as (kind, object count)."""
    registry = SYSTEMS.get(_scene_id(scene), {})
    info = []
    for kind, system in registry.items():
        if not system:
            continue
        owner = _scene_id(scene)
        count = 0
        for coll in bpy.data.collections:
            if coll.get(OWNER_KEY) != owner:
                continue
            for obj in coll.objects:
                if obj.get("ald_fx") and obj.get("ald_fx_kind") == kind:
                    count += 1
        info.append((kind, count))
    return info


def clear(scene, keep_system=False, kind=None):
    """Remove the FX systems owned by ``scene`` and their orphan data."""
    owner = _scene_id(scene)
    removed = 0
    coll = None
    for candidate in bpy.data.collections:
        if candidate.get(OWNER_KEY) == owner:
            coll = candidate
            break
    if coll is not None:
        for obj in list(coll.objects):
            if not obj.get("ald_fx"):
                continue
            if kind is not None and obj.get("ald_fx_kind") != kind:
                continue
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    if kind is not None:
        registry = SYSTEMS.get(owner)
        if registry is not None:
            registry.pop(kind, None)
    elif not keep_system:
        SYSTEMS.pop(owner, None)
    _cleanup_orphans()
    return removed


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

@persistent
def _on_frame_change(scene, *_args):
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    settings = getattr(scene, "ald", None)
    age_offset = float(getattr(settings, "fx_age", 0.0)) if settings else 0.0
    if not age_offset:
        config = scene.get("ald_fx_config") or {}
        if isinstance(config, dict):
            age_offset = float(config.get("age", 0.0))
    time = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
    time += age_offset
    for system in registry.values():
        if not system:
            continue
        if system.get("time") is not None \
                and abs(time - system["time"]) < 1e-6:
            continue
        try:
            _update_system(system, time)
        except Exception:
            pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
    SYSTEMS.clear()
