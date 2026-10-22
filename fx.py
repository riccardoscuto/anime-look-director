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
import uuid

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
#: Identity of the scene that owns each identifier: the first claim wins, a
#: duplicated scene receives a new identity.
_CLAIMED = {}


# ---------------------------------------------------------------------------
# ownership helpers
# ---------------------------------------------------------------------------

def _scene_collections(scene):
    """Every collection linked to the scene, at any depth."""
    found = []

    def walk(collection):
        for child in collection.children:
            if child in found:
                continue
            found.append(child)
            walk(child)

    walk(scene.collection)
    return found


def _retag_scene(scene, owner):
    """Give the ALD collections of a scene the new ownership.

    A collection shared with another scene is left alone: the other scene
    still owns it.
    """
    for coll in _scene_collections(scene):
        if not coll.get(OWNER_KEY):
            continue
        if _shared_with_other_scene(coll, scene):
            continue
        coll[OWNER_KEY] = owner


def _scene_id(scene):
    """Stable identity of a scene for the FX ownership.

    The identity is a persistent UUID: it survives a save and a reload and it
    is not derived from the name. The first scene that claims an identity
    keeps it: a duplicated scene receives a new one and an independent copy of
    the systems.
    """
    _prune_claims()
    ident = scene.get(ID_KEY)
    if not ident:
        ident = uuid.uuid4().hex
        scene[ID_KEY] = ident
    owner = _CLAIMED.get(ident)
    if owner is not None and owner != scene.as_pointer():
        # The scene was duplicated: it gets an independent identity.
        ident = uuid.uuid4().hex
        scene[ID_KEY] = ident
        _retag_scene(scene, ident)
    _CLAIMED[ident] = scene.as_pointer()
    settings = getattr(scene, "ald", None)
    if settings is not None:
        settings.fx_uid = ident
    return ident


def _prune_claims():
    """Drop the claims of the scenes that no longer exist."""
    alive = {scene.as_pointer() for scene in bpy.data.scenes}
    for ident, pointer in list(_CLAIMED.items()):
        if pointer not in alive:
            del _CLAIMED[ident]


def _shared_with_other_scene(coll, scene):
    """True when a collection is also linked to another scene."""
    for other in bpy.data.scenes:
        if other is scene:
            continue
        if coll in _scene_collections(other):
            return True
    return False


def _collection(scene):
    owner = _scene_id(scene)
    for coll in _scene_collections(scene):
        if coll.get(OWNER_KEY) != owner:
            continue
        if _shared_with_other_scene(coll, scene):
            # A collection shared with another scene cannot own the systems:
            # the copy gets its own.
            continue
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
            _bind_energy(mat, bsdf, strength)
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = strength
            _bind_energy(mat, bsdf, strength)
        bsdf.inputs["Roughness"].default_value = 0.4
    return mat


def _bind_energy(mat, bsdf, strength):
    """Drive the emission strength with the per particle energy attribute.

    The geometry scale and the emissive energy are two different curves: the
    particle shrinks and fades on its own law.
    """
    node_tree = mat.node_tree
    attribute = node_tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = "energy"
    attribute.location = (-520, -160)
    multiply = node_tree.nodes.new("ShaderNodeMath")
    multiply.operation = "MULTIPLY"
    multiply.location = (-300, -160)
    multiply.inputs[1].default_value = float(strength)
    node_tree.links.new(attribute.outputs["Fac"], multiply.inputs[0])
    node_tree.links.new(multiply.outputs[0], bsdf.inputs["Emission Strength"])


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
                      energy_power=1.0, gravity=None, camera_position=None,
                      atmospheric_fade=0.0):
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
                                   decay_power=decay_power,
                                   energy_power=energy_power,
                                   camera_position=camera_position,
                                   atmospheric_fade=atmospheric_fade)
    return obj


def _gn_star_data(seed, index, config, spoke, spoke_count):
    """Deterministic lifetime and initial velocity of one primary star."""
    life = _hash_range(seed, index, spoke, 2, config["life"] * 0.6,
                       config["life"])
    direction = _fibonacci_direction(spoke, spoke_count, 0.35, seed, index)
    speed = _hash_range(seed, index, spoke, 3, config["speed"] * 0.75,
                        config["speed"] * 1.15)
    return life, direction * speed


def _particle(birth, life, drag, radius, vel, pos0, tau=0.0, jitter=None,
              use_decay=1.0, min_scale=0.35, decay_power=1.0, energy_power=1.0,
              role="head", spoke=0, trail=0.0):
    """One deterministic particle: the data shared by both backends."""
    return {
        "birth": float(birth), "life": float(life), "drag": float(drag),
        "radius": float(radius), "vel": Vector(vel), "pos0": Vector(pos0),
        "tau": float(tau), "jitter": Vector(jitter or (0.0, 0.0, 0.0)),
        "use_decay": float(use_decay), "min_scale": float(min_scale),
        "decay_power": float(decay_power),
        "energy_power": float(energy_power), "role": role, "spoke": int(spoke),
        "trail": float(trail),
    }


def burst_population(seed, index, config, birth, center, size_scale,
                     spoke_count):
    """Deterministic initial conditions of one burst.

    The same data feeds the Geometry Nodes attributes and the Python writer:
    the two backends cannot diverge.
    """
    heads = []
    grains = []
    trail = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        heads.append(_particle(birth, life, config["drag"],
                               0.13 * size_scale, v0, center, role="head",
                               spoke=spoke))
        for step in range(SAMPLES):
            profile = step / (SAMPLES - 1.0)
            tau = config["trail"] * (1.0 - profile)
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
            grains.append(_particle(
                birth, life, config["drag"],
                0.05 * size_scale * (0.25 + 0.75 * profile) * grain, v0, center,
                tau=tau, jitter=jitter, use_decay=0.0, role="grain",
                spoke=spoke, trail=config["trail"]))
            trail.append(_particle(
                birth, life, config["drag"],
                0.25 + 0.9 * profile ** 1.4, v0, center, tau=tau,
                use_decay=0.0, role="filament", spoke=spoke,
                trail=config["trail"]))

    pistil = []
    pistil_grains = []
    pistil_count = config["pistil"]
    for spoke in range(pistil_count):
        life = _hash_range(seed, index, spoke + 500, 2,
                           config["life"] * 0.6 * 0.85, config["life"] * 0.85)
        direction = _fibonacci_direction(spoke, pistil_count, 0.35, seed, index)
        speed = _hash_range(seed, index, spoke + 500, 3,
                            config["speed"] * 0.75 * 0.68,
                            config["speed"] * 1.15 * 0.68)
        v0 = direction * speed
        drag = config["drag"] * 1.2
        pistil.append(_particle(birth, life, drag, 0.10 * size_scale, v0, center,
                                role="pistil"))
        for step in range(SAMPLES):
            profile = step / (SAMPLES - 1.0)
            pistil_grains.append(_particle(
                birth, life, drag,
                0.028 * size_scale * (0.25 + 0.75 * profile), v0, center,
                tau=config["trail"] * 0.6 * (1.0 - profile), use_decay=0.0,
                role="pistil_grain", trail=config["trail"] * 0.6))

    sparks = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        for child in range(config["sparks"]):
            emit = _hash_range(seed, index, spoke * 8 + child, 4, 0.05,
                               life * 0.55)
            child_life = _hash_range(seed, index, spoke * 8 + child, 5, 0.45,
                                     1.5)
            # The origin is fixed at the emission instant: the spark is a
            # body of its own, not a particle of a moving source.
            parent_pos = _position(center, v0, config["drag"], emit)
            parent_vel = _velocity(v0, config["drag"], emit)
            perturb = Vector((
                _hash_range(seed, index, spoke * 8 + child, 6, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 7, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 8, -1.6, 1.6),
            )) * 1.2
            sparks.append(_particle(
                birth + emit, child_life, 2.4, 0.045 * size_scale,
                parent_vel * 0.35 + perturb, parent_pos, min_scale=0.0,
                role="spark"))

    flash = [_particle(birth, config["core"], 100.0, 0.25 * size_scale,
                        Vector((0.0, 0.0, 0.0)), center, min_scale=0.0,
                        decay_power=0.5, role="flash")]
    return {"heads": heads, "grains": grains, "trail": trail,
            "pistil": pistil, "pistil_grains": pistil_grains,
            "sparks": sparks, "flash": flash}


def _energy_powers(scene):
    """The energy decay exponents of every role."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return {}
    return {"head": float(settings.fx_energy_head),
            "grain": float(settings.fx_energy_grain),
            "ember": float(settings.fx_energy_ember)}


def _atmospheric_fade(scene):
    """The atmospheric attenuation of the FX emission."""
    settings = getattr(scene, "ald", None)
    return float(settings.fx_atmospheric_fade) if settings else 0.0


def _particle_state(particle, time, powers=None, fade=0.0, camera=None):
    """Evaluate one particle: position, scale, energy and alive flag."""
    age = time - particle["birth"]
    life = max(particle["life"], 1e-3)
    # The trail window: the sample is an older point of the same trajectory.
    window = particle.get("trail", 0.0)
    if window > 0.0:
        train = max(0.0, min(max(age, 0.0), window)
                    - max(0.0, age - particle["life"]))
        tau = particle["tau"] * (train / window)
    else:
        tau = 0.0
    sample_age = age - tau
    alive = 0.0 <= age <= particle["life"] and sample_age >= 0.0
    u = min(max(age / life, 0.0), 1.0)
    if sample_age <= 0.0:
        position = particle["pos0"].copy()
    else:
        position = _position(particle["pos0"], particle["vel"],
                             particle["drag"], sample_age)
    position = position + particle["jitter"]
    minimum = particle["min_scale"]
    shape = minimum + (1.0 - minimum) * (1.0 - u) ** particle["decay_power"]
    scale = particle["radius"] * (shape if particle["use_decay"] else 1.0)
    power = particle["energy_power"]
    if powers:
        power = powers.get(particle["role"], power)
    energy = (1.0 - u) ** power
    if fade > 0.0 and camera is not None:
        energy *= math.exp(-fade * (position - camera).length / 100.0)
    return position, scale, energy, alive


def _population_particles(population, role, slot=None):
    """Particles of one role, optionally filtered by colour slot."""
    particles = population[role]
    if slot is None:
        return particles
    return [particle for index, particle in enumerate(particles)
            if index % 3 == slot]


def _population_trail(population, role, slot=None):
    """Filament samples of one role, optionally filtered by colour slot."""
    samples = population["trail"] if role == "heads" else population[
        "pistil_grains"]
    if slot is None:
        return samples
    grouped = []
    for index, sample in enumerate(samples):
        if index % SAMPLES == 0 and (index // SAMPLES) % 3 == slot:
            grouped.append(sample)
    return grouped


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
            ("weight", "FLOAT", [float(index % SAMPLES)
                                 for index in range(len(particles))]),
            ("curve_id", "INT", [int(p.get("spoke", index // SAMPLES))
                                 for index, p in enumerate(particles)]),
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


def _write_particle_mesh(mesh, ranges, centers, radii, energies=None):
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
    if energies:
        # The energy is an attribute: the material fades the particle without
        # touching its size.
        attribute = mesh.attributes.get("energy")
        if attribute is None:
            attribute = mesh.attributes.new("energy", "FLOAT", "POINT")
        values = []
        for index, energy in enumerate(energies):
            values.extend([float(energy)] * count)
        attribute.data.foreach_set("value", values)


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
    # The number of bursts never changes during the construction.
    burst_count = max(1, int(count))
    bursts = []
    for index in range(burst_count):
        # Composition: the first burst is the hero, the others are secondary
        # and staggered in time so the sky is never a uniform field.
        role = index % 3
        family_key = family if index == 0 else FAMILIES[(index - 1) % len(FAMILIES)]
        config = FAMILY_CONFIG[family_key]
        family_distance = distance * (1.0 if index == 0 else
                                      (0.78 if role == 1 else 0.58))
        center = _burst_center(origin, forward, up, right, index, burst_count,
                                family_distance * (0.85 + 0.25 *
                                                   _hash_unit(seed, index, 0, 1)),
                                spread) + offset
        birth = 0.0 if index == 0 else (0.25 if role == 1 else 0.85)
        spoke_count = config["spokes"]
        sample_count = SAMPLES
        pistil_count = config["pistil"]
        # The deterministic data is built once and feeds both backends.
        population = burst_population(seed, index, config, birth, center,
                                      size_scale, spoke_count)
        family_colors = PALETTES[index % len(PALETTES)]
        materials = [
            _material("ALD FX %s %d A" % (family_key, index), family_colors[0],
                      6.0),
            _material("ALD FX %s %d B" % (family_key, index), family_colors[1],
                      6.0),
            _material("ALD FX %s %d C" % (family_key, index), family_colors[2],
                      6.0),
        ]
        # Python meshes: the fallback writer.
        trail_obj = _build_curve(scene, "ALD FX %s %d Filament" % (family_key, index),
                                 spoke_count, materials, 0.022 * size_scale)
        trail_obj["ald_fx_kind"] = kind
        bead_objects = []
        for slot in range(3):
            grains = [p for p in population["grains"]
                      if p["spoke"] % 3 == slot]
            bead_obj, bead_ranges = _build_particle_mesh(
                "ALD FX %s %d Beads %d" % (family_key, index, slot),
                [center] * len(grains), [0.001] * len(grains), materials[slot])
            _collection(scene).objects.link(bead_obj)
            bead_obj["ald_fx_kind"] = kind
            bead_objects.append((bead_obj, bead_ranges, grains))
        head_obj, head_ranges = _build_particle_mesh(
            "ALD FX %s %d Heads" % (family_key, index),
            [center] * spoke_count, [0.001] * spoke_count, materials[0])
        _collection(scene).objects.link(head_obj)
        head_obj["ald_fx_kind"] = kind
        # Inner contrasting pistil population (the classic Hanabi core).
        pistil_obj, pistil_ranges = _build_particle_mesh(
            "ALD FX %s %d Pistil Heads" % (family_key, index),
            [center] * pistil_count, [0.001] * pistil_count, materials[1])
        _collection(scene).objects.link(pistil_obj)
        pistil_obj["ald_fx_kind"] = kind
        pistil_bead_obj, pistil_bead_ranges = _build_particle_mesh(
            "ALD FX %s %d Pistil Beads" % (family_key, index),
            [center] * (pistil_count * sample_count),
            [0.001] * (pistil_count * sample_count), materials[1])
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
        gn_heads = None
        gn_beads = []
        gn_pistil = None
        gn_sparks = None
        gn_flash = None
        gn_trails = []
        # Geometry Nodes path: the node group evaluates the same data.
        use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
            else False
        if use_gn:
            created = []
            try:
                age_offset = float(getattr(settings, "fx_age", 0.0)) \
                    if settings else 0.0
                powers = _energy_powers(scene)
                fade = _atmospheric_fade(scene)
                camera_position = tuple(origin)
                gn_heads = _gn_points_object(
                    scene, "ALD FX GN Heads %d" % index, materials[0],
                    population["heads"], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("head", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade)
                created.append(gn_heads)
                for slot in range(3):
                    grains = [p for p in population["grains"]
                              if p["spoke"] % 3 == slot]
                    bead_gn = _gn_points_object(
                        scene, "ALD FX GN Beads %d %d" % (index, slot),
                        materials[slot], grains, trail=config["trail"],
                        age_offset=age_offset,
                        energy_power=powers.get("grain", 1.0),
                        camera_position=camera_position,
                        atmospheric_fade=fade)
                    created.append(bead_gn)
                    gn_beads.append(bead_gn)
                gn_pistil = _gn_points_object(
                    scene, "ALD FX GN Pistil %d" % index, materials[1],
                    population["pistil"], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("head", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade)
                created.append(gn_pistil)
                gn_pistil_grains = _gn_points_object(
                    scene, "ALD FX GN Pistil Grains %d" % index, materials[1],
                    population["pistil_grains"],
                    trail=config["trail"] * 0.6, age_offset=age_offset,
                    energy_power=powers.get("grain", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade)
                created.append(gn_pistil_grains)
                gn_beads.append(gn_pistil_grains)
                gn_sparks = _gn_points_object(
                    scene, "ALD FX GN Sparks %d" % index, materials[2],
                    population["sparks"], trail=0.0, age_offset=age_offset,
                    min_scale=0.0,
                    energy_power=powers.get("ember", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade)
                created.append(gn_sparks)
                for slot in range(3):
                    samples = [p for p in population["trail"]
                               if p["spoke"] % 3 == slot]
                    trail_gn = _gn_trail_object(
                        scene, "ALD FX GN Trail %d %d" % (index, slot),
                        materials[slot], samples, trail=config["trail"],
                        age_offset=age_offset, radius=0.022 * size_scale)
                    created.append(trail_gn)
                    gn_trails.append(trail_gn)
                gn_flash = _gn_points_object(
                    scene, "ALD FX GN Flash %d" % index, materials[1],
                    population["flash"], trail=0.0, age_offset=age_offset,
                    min_scale=0.0, decay_power=0.5,
                    energy_power=powers.get("head", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade)
                created.append(gn_flash)
                for obj in created:
                    obj["ald_fx_kind"] = kind
                # The Python meshes are replaced by the node group.
                for python_obj in (head_obj, pistil_obj, pistil_bead_obj,
                                   spark_obj, trail_obj, core_obj):
                    bpy.data.objects.remove(python_obj, do_unlink=True)
                for bead_obj, _bead_ranges, _grains in bead_objects:
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
                gn_flash = None
                gn_trails = []
        bursts.append({
            "index": index, "family": family_key, "config": config,
            "center": center, "birth": birth, "seed": seed,
            "size_scale": size_scale, "materials": materials,
            "population": population,
            "spread_x": (-0.18 + 0.36 * (index + 0.5) / burst_count) * spread,
            "trail": trail_obj, "heads": head_obj, "head_ranges": head_ranges,
            "gn_heads": gn_heads, "gn_beads": gn_beads,
            "gn_pistil": gn_pistil, "gn_sparks": gn_sparks,
            "gn_flash": gn_flash, "gn_trails": gn_trails,
            "beads": bead_objects,
            "pistil": (pistil_obj, pistil_ranges, pistil_bead_obj,
                       pistil_bead_ranges, pistil_count),
            "sparks": spark_obj, "spark_ranges": spark_ranges,
            "core": core_obj, "core_ranges": core_ranges,
        })
    return {"kind": "fireworks", "bursts": bursts, "time": None,
            "scene": scene, "camera": origin,
            "gn": all(burst.get("gn_heads") is not None for burst in bursts)}


def _evaluate(population, role, time, powers=None, fade=0.0, camera=None):
    """Evaluate a population: (centers, radii, energies, alive flags).

    A dead particle is moved away and shrunk: the Geometry Nodes path hides it
    with a zero scale, the Python path cannot write a zero radius.
    """
    centers = []
    radii = []
    energies = []
    alive_flags = []
    for particle in population[role]:
        position, scale, energy, alive = _particle_state(particle, time, powers,
                                                        fade, camera)
        if not alive:
            position = particle["pos0"] + Vector((0.0, 0.0, 1000.0))
            scale = 0.0001
        centers.append(position)
        radii.append(scale)
        energies.append(energy)
        alive_flags.append(alive)
    return centers, radii, energies, alive_flags


def _update_fireworks(system, time):
    for burst in system["bursts"]:
        population = burst["population"]
        if burst.get("gn_heads") is not None:
            # The node group evaluates every particle of the burst.
            continue
        center = burst["center"]
        powers = _energy_powers(system.get("scene"))
        fade = _atmospheric_fade(system.get("scene"))
        camera = system.get("camera")
        # Filament: the thin trail of every star.
        trail_data = burst["trail"].data if burst["trail"] is not None else None
        if trail_data is not None:
            for spoke in range(len(trail_data.splines)):
                samples = [p for p in population["trail"]
                           if p["spoke"] == spoke]
                spline = trail_data.splines[spoke]
                for step, particle in enumerate(samples):
                    position, _scale, _energy, alive = _particle_state(
                        particle, time, powers, fade, camera)
                    if not alive:
                        position = center + Vector((0.0, 0.0, 1000.0))
                    spline.points[step].co = (position.x, position.y,
                                              position.z, 1.0)
                    spline.points[step].radius = particle["radius"]
        heads = _evaluate(population, "heads", time, powers, fade, camera)
        _write_particle_mesh(burst["heads"].data, burst["head_ranges"],
                             heads[0], heads[1], heads[2])
        for slot, (bead_obj, bead_ranges, grains) in enumerate(burst["beads"]):
            centers = []
            radii = []
            energies = []
            for particle in grains:
                position, scale, energy, alive = _particle_state(
                    particle, time, powers, fade, camera)
                if not alive:
                    position = center + Vector((0.0, 0.0, 1000.0))
                    scale = 0.0001
                centers.append(position)
                radii.append(scale)
                energies.append(energy)
            _write_particle_mesh(bead_obj.data, bead_ranges, centers, radii,
                                 energies)
        (pistil_obj, pistil_ranges, pistil_bead_obj, pistil_bead_ranges,
         _pistil_count) = burst["pistil"]
        pistil = _evaluate(population, "pistil", time, powers, fade, camera)
        _write_particle_mesh(pistil_obj.data, pistil_ranges, pistil[0],
                             pistil[1], pistil[2])
        pistil_grains = _evaluate(population, "pistil_grains", time, powers,
                                  fade, camera)
        _write_particle_mesh(pistil_bead_obj.data, pistil_bead_ranges,
                             pistil_grains[0], pistil_grains[1],
                             pistil_grains[2])
        sparks = _evaluate(population, "sparks", time, powers, fade, camera)
        _write_particle_mesh(burst["sparks"].data, burst["spark_ranges"],
                             sparks[0], sparks[1], sparks[2])
        flash = _evaluate(population, "flash", time, powers, fade, camera)
        _write_particle_mesh(burst["core"].data, burst["core_ranges"],
                             flash[0], flash[1], flash[2])


# ---------------------------------------------------------------------------
# shooting stars
# ---------------------------------------------------------------------------

def _meteor_population(seed, index, start, v0, drag, event_birth, life, train,
                      persistence):
    """Deterministic data of one meteor: head, train and fragments.

    Every component shares the same ``event_birth``: the train and the
    fragments can never appear before the body.
    """
    head = _particle(event_birth, life, drag, 0.18, v0, start, use_decay=0.0,
                     role="meteor_head", spoke=index)
    train_samples = []
    for step in range(SAMPLES):
        profile = step / (SAMPLES - 1.0)
        train_samples.append(_particle(
            event_birth, life + persistence, drag, 0.2 + 0.8 * profile, v0,
            start, tau=train * (1.0 - profile), use_decay=0.0,
            role="meteor_train", spoke=index, trail=train))
    fragments = []
    for fragment in range(3):
        emit = _hash_range(seed, index, 30 + fragment, 7, 0.05, life * 0.8)
        frag_life = _hash_range(seed, index, 30 + fragment, 8, 0.4, 1.4)
        # The origin is the position of the body at the emission instant.
        parent = _position(start, v0, drag, emit)
        parent_vel = v0 * math.exp(-drag * emit)
        push = Vector((
            _hash_range(seed, index, 30 + fragment, 9, -2.4, 2.4),
            _hash_range(seed, index, 30 + fragment, 10, -2.4, 2.4),
            _hash_range(seed, index, 30 + fragment, 11, -3.2, 1.2),
        ))
        fragments.append(_particle(
            event_birth + emit, frag_life, 1.6, 0.05, parent_vel * 0.25 + push,
            parent, role="meteor_fragment", spoke=index))
    return {"head": head, "train": train_samples, "fragments": fragments}


def _build_meteors(scene, count, seed, distance):
    origin, forward, up, right = _camera_basis(scene)
    # The shower direction is a world direction, almost lateral: the meteors
    # cross the sky instead of moving along the line of sight. The radiant
    # emerges from the convergence of the parallel trajectories.
    shower = (forward * 0.16 + right * 0.94 + up * 0.30).normalized()
    material = _material("ALD FX Meteor", (0.85, 0.94, 1.0), 9.0)
    settings = getattr(scene, "ald", None)
    use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
        else False
    age_offset = float(getattr(settings, "fx_age", 0.0)) if settings else 0.0
    persistence = float(getattr(settings, "fx_meteor_persistence", 0.32)) \
        if settings else 0.32
    total = max(1, int(count))
    system = {"kind": "meteors", "count": total, "seed": seed,
              "distance": distance, "shower": shower, "origin": origin,
              "material": material, "gn": False, "trail": None,
              "heads": None, "head_ranges": [], "fragments": None,
              "fragment_ranges": [], "populations": []}
    populations = []
    for index in range(total):
        life = _hash_range(seed, index, 0, 2, 0.55, 1.15)
        event_birth = index * 0.9 + _hash_range(seed, index, 0, 1, 0.0, 0.6)
        # The start points are spread on a plane far away from the camera.
        plane_center = origin + forward * distance
        lateral_x = _hash_range(seed, index, 10, 11, -0.55, 0.55) * distance
        lateral_y = _hash_range(seed, index, 10, 12, -0.30, 0.34) * distance
        start = plane_center + right * lateral_x + up * lateral_y
        # The velocities are almost parallel in world space, with a small
        # angular jitter so the radiant is not a perfect point.
        jitter = Vector((
            _hash_range(seed, index, 0, 3, -0.03, 0.03),
            _hash_range(seed, index, 0, 4, -0.03, 0.03),
            _hash_range(seed, index, 0, 5, -0.02, 0.02),
        ))
        direction = (shower + jitter).normalized()
        speed = _hash_range(seed, index, 0, 6, 26.0, 38.0)
        v0 = direction * speed
        populations.append(_meteor_population(seed, index, start, v0, 0.08,
                                             event_birth, life, 0.32,
                                             persistence))
    system["populations"] = populations
    if use_gn:
        created = []
        try:
            powers = _energy_powers(scene)
            fade = _atmospheric_fade(scene)
            camera_position = tuple(origin)
            head_points = [population["head"] for population in populations]
            train_points = []
            fragment_points = []
            for population in populations:
                train_points.extend(population["train"])
                fragment_points.extend(population["fragments"])
            gn_heads = _gn_points_object(
                scene, "ALD FX GN Meteor Heads", material, head_points,
                trail=0.0, age_offset=age_offset,
                energy_power=powers.get("head", 1.0),
                camera_position=camera_position, atmospheric_fade=fade)
            created.append(gn_heads)
            gn_train = _gn_trail_object(
                scene, "ALD FX GN Meteor Trails", material, train_points,
                trail=0.32, age_offset=age_offset, radius=0.07,
                fade_window=persistence)
            created.append(gn_train)
            gn_fragments = _gn_points_object(
                scene, "ALD FX GN Meteor Fragments", material, fragment_points,
                trail=0.0, age_offset=age_offset, min_scale=0.0,
                energy_power=powers.get("ember", 1.0),
                camera_position=camera_position, atmospheric_fade=fade)
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
    origin = system["origin"]
    populations = system["populations"]
    trail_data = system["trail"].data
    head_centers = []
    head_radii = []
    head_energies = []
    fragment_centers = []
    fragment_radii = []
    fragment_energies = []
    for index, population in enumerate(populations):
        head = population["head"]
        position, scale, energy, alive = _particle_state(head, time)
        if not alive:
            position = origin + Vector((0.0, 0.0, 1000.0))
            scale = 0.0001
        head_centers.append(position)
        head_radii.append(scale)
        head_energies.append(energy)
        spline = trail_data.splines[index]
        for step, particle in enumerate(population["train"]):
            point, _scale, _energy, sample_alive = _particle_state(particle,
                                                                   time)
            if not sample_alive:
                point = origin + Vector((0.0, 0.0, 1000.0))
            spline.points[step].co = (point.x, point.y, point.z, 1.0)
            spline.points[step].radius = particle["radius"]
        for particle in population["fragments"]:
            point, scale, energy, fragment_alive = _particle_state(particle,
                                                                    time)
            if not fragment_alive:
                point = origin + Vector((0.0, 0.0, 1000.0))
                scale = 0.0001
            fragment_centers.append(point)
            fragment_radii.append(scale)
            fragment_energies.append(energy)
    _write_particle_mesh(system["heads"].data, system["head_ranges"],
                         head_centers, head_radii, head_energies)
    _write_particle_mesh(system["fragments"].data, system["fragment_ranges"],
                         fragment_centers, fragment_radii, fragment_energies)


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


def _age_offset(scene):
    """The Burst Age offset applied to every FX system of a scene."""
    settings = getattr(scene, "ald", None)
    offset = float(getattr(settings, "fx_age", 0.0)) if settings else 0.0
    if offset:
        return offset
    config = scene.get("ald_fx_config") or {}
    if isinstance(config, dict):
        return float(config.get("age", 0.0))
    return 0.0


def store_system(scene, kind, count, seed, distance, family, time):
    """Write the persistent description of a system and of its events.

    The runtime registry is only a cache: this configuration is the source of
    truth and it is saved with the .blend file.
    """
    from .properties import FX_SCHEMA
    settings = getattr(scene, "ald", None)
    if settings is None:
        return None
    registry = SYSTEMS.get(_scene_id(scene)) or {}
    system = None
    for entry in settings.fx_systems:
        if entry.kind == kind:
            system = entry
            break
    if system is None:
        system = settings.fx_systems.add()
    if not system.uid:
        system.uid = uuid.uuid4().hex
    system.kind = kind
    system.enabled = True
    system.seed = seed
    system.timing_mode = "TIMELINE"
    system.origin_frame = 1
    system.origin_time = time
    system.isolation_mode = "EMISSION"
    system.events.clear()
    origin, _forward, _up, _right = _camera_basis(scene)
    if kind == "FIREWORKS":
        for burst in registry.get("fireworks", {}).get("bursts", []):
            event = system.events.add()
            event.uid = uuid.uuid4().hex
            event.kind = "FIREWORK"
            event.enabled = True
            event.seed = seed
            event.birth = burst["birth"]
            event.family = burst.get("family", family)
            event.size = burst.get("size_scale", 1.0)
            event.count = 1
            event.target = tuple(burst["center"])
            event.launcher = tuple(origin)
            event.duration = burst["config"].get("life", 1.0)
            event.life = event.duration
            event.glow = 0.6
    else:
        populations = registry.get("meteors", {}).get("populations", [])
        for population in populations:
            head = population["head"]
            event = system.events.add()
            event.uid = uuid.uuid4().hex
            event.kind = "METEOR"
            event.enabled = True
            event.seed = seed
            event.birth = head["birth"]
            event.family = family
            event.size = 1.0
            event.count = 1
            event.target = tuple(head["pos0"])
            event.launcher = tuple(head["pos0"])
            event.direction = tuple(head["vel"])
            event.speed = head["vel"].length
            event.life = head["life"]
            event.duration = head["life"]
            event.glow = 0.6
    settings.fx_schema = FX_SCHEMA
    return system


def _find_objects(scene):
    """The ALD objects of a scene, indexed by name."""
    return {obj.name: obj for obj in _collection(scene).objects
            if obj.get("ald_fx")}


def rebuild_registry(scene):
    """Rebuild the runtime registry from the persistent configuration.

    The geometry saved in the file is reused: nothing is regenerated. The
    runtime cache is never the source of truth.
    """
    settings = getattr(scene, "ald", None)
    registry = _registry(scene)
    registry.clear()
    if settings is None:
        return 0
    objects = _find_objects(scene)
    rebuilt = 0
    for system in settings.fx_systems:
        if not system.enabled:
            continue
        events = list(system.events)
        if not events:
            continue
        if system.kind == "FIREWORKS":
            bursts = []
            for index, event in enumerate(events):
                config = FAMILY_CONFIG[event.family]
                spoke_count = config["spokes"]
                center = Vector(event.target)
                population = burst_population(event.seed, index, config,
                                              event.birth, center, event.size,
                                              spoke_count)
                family_key = event.family
                prefix = "ALD FX %s %d " % (family_key, index)
                bursts.append({
                    "index": index, "family": family_key, "config": config,
                    "center": center, "birth": event.birth,
                    "seed": event.seed, "size_scale": event.size,
                    "materials": [], "population": population,
                    "trail": objects.get(prefix + "Filament"),
                    "heads": objects.get(prefix + "Heads"),
                    "head_ranges": [],
                    "gn_heads": objects.get("ALD FX GN Heads %d" % index),
                    "gn_beads": [], "gn_pistil": None, "gn_sparks": None,
                    "gn_flash": None, "gn_trails": [],
                    "beads": [], "pistil": (None, [], None, [], 0),
                    "sparks": None, "spark_ranges": [],
                    "core": objects.get(prefix + "Flash"), "core_ranges": [],
                })
            registry["fireworks"] = {
                "kind": "fireworks", "bursts": bursts, "time": None,
                "gn": all(burst["gn_heads"] is not None for burst in bursts)}
            rebuilt += 1
        elif system.kind == "METEORS":
            populations = []
            for index, event in enumerate(events):
                life = event.life
                speed = event.speed
                direction = Vector(event.direction)
                if direction.length < 1e-6:
                    direction = Vector((1.0, 0.0, 0.0))
                direction = direction.normalized()
                start = Vector(event.target)
                v0 = direction * speed
                populations.append(_meteor_population(
                    event.seed, index, start, v0, 0.08, event.birth, life, 0.32,
                    0.32))
            registry["meteors"] = {
                "kind": "meteors", "count": len(populations),
                "seed": system.seed, "distance": 0.0,
                "shower": Vector((1.0, 0.0, 0.0)), "origin": Vector((0, 0, 0)),
                "material": None, "gn": True, "trail": None, "heads": None,
                "head_ranges": [], "fragments": None, "fragment_ranges": [],
                "populations": populations}
            rebuilt += 1
    return rebuilt


def apply_backend(scene):
    """Apply the backend semantics immediately.

    OFF hides the 3D systems and the legacy shader, the data is preserved.
    LEGACY enables the legacy world shader and hides the 3D systems.
    FX3D disables the legacy shader and shows the 3D systems.
    """
    settings = getattr(scene, "ald", None)
    if settings is None:
        return False
    backend = settings.fx_backend
    visible = (backend == "FX3D")
    for obj in _collection(scene).objects:
        if not obj.get("ald_fx"):
            continue
        obj.hide_render = not visible
        obj.hide_viewport = not visible
    # The legacy world fireworks follow the backend.
    if settings.fireworks != (backend == "LEGACY"):
        settings.fireworks = (backend == "LEGACY")
    return True


def set_age(scene, age):
    """Move the FX systems in time without rebuilding the geometry.

    The Geometry Nodes systems only need the age offset of their modifiers:
    the deterministic data stays untouched. The Python systems are re-evaluated
    at the new instant.
    """
    from . import fx_nodes
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return False
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    now = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
    updated = False
    collection = _collection(scene)
    powers = _energy_powers(scene)
    fade = _atmospheric_fade(scene)
    origin, _forward, _up, _right = _camera_basis(scene)
    role_by_object = {}
    for system in registry.values():
        if not system:
            continue
        if system.get("gn"):
            for obj in collection.objects:
                if obj.get("ald_fx"):
                    fx_nodes.set_age_offset(obj, age)
                    fx_nodes.set_look(obj, camera_position=tuple(origin),
                                      atmospheric_fade=fade)
            system["time"] = None
            updated = True
        else:
            try:
                _update_system(system, now + age)
                updated = True
            except Exception:
                pass
    return updated


def update(scene, time=None):
    """Re-evaluate every FX system of a scene at the given time."""
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return False
    if time is None:
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        time = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
        time += _age_offset(scene)
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
    time = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
    time += _age_offset(scene)
    for system in registry.values():
        if not system:
            continue
        if system.get("gn"):
            # Every particle is evaluated by the node group.
            continue
        if system.get("time") is not None \
                and abs(time - system["time"]) < 1e-6:
            continue
        try:
            _update_system(system, time)
        except Exception:
            pass


@persistent
def _on_load_post(*_args):
    """A new file invalidates every cached FX system.

    The registry is rebuilt from the persistent configuration: the geometry
    saved in the file is reused.
    """
    SYSTEMS.clear()
    _CLAIMED.clear()
    for scene in bpy.data.scenes:
        try:
            rebuild_registry(scene)
        except Exception:
            pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    SYSTEMS.clear()
