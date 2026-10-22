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

FAMILIES = ("CHRYSANTHEMUM", "PEONY", "WILLOW", "KAMURO")
FAMILY_LABELS = {
    "CHRYSANTHEMUM": "Chrysanthemum",
    "PEONY": "Peony",
    "WILLOW": "Willow",
    "KAMURO": "Kamuro",
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
    "KAMURO": {
        # The kamuro: few thick stars, a long drooping tail and a warm core.
        "spokes": 48, "speed": 14.0, "drag": 0.55, "life": 5.6,
        "trail": 2.20, "sparks": 3, "core": 0.34, "pistil": 10,
    },
}

PALETTES = (
    ((1.0, 0.34, 0.03), (1.0, 0.06, 0.02), (0.05, 1.0, 0.72)),
    ((1.0, 0.05, 0.44), (0.42, 0.05, 1.0), (1.0, 0.72, 0.02)),
    ((0.04, 0.72, 1.0), (0.05, 1.0, 0.32), (1.0, 0.22, 0.02)),
)

#: The meteor presets. A bolide is a cinematic meteor: bigger, brighter, with
#: a long persistent train. A true comet is a different feature, not a meteor.
METEOR_PRESETS = {
    "METEOR": {"life": (0.55, 1.15), "speed": (26.0, 38.0), "radius": 0.18,
               "train": 0.32, "emission": 9.0, "spacing": 0.9, "jitter": 0.03,
               "fragments": 3, "drag": 0.08},
    "BOLIDE": {"life": (1.6, 2.4), "speed": (44.0, 62.0), "radius": 0.5,
               "train": 1.2, "emission": 16.0, "spacing": 2.2, "jitter": 0.012,
               "fragments": 8, "drag": 0.05},
}

#: The material contract of the plan: the role of a particle, its code and
#: the energy of the role relative to the head.
ROLE_CODES = {
    "head": 0, "filament": 1, "grain": 2, "ember": 3, "flash": 4, "smoke": 5,
    "shell": 6, "shell_trail": 7, "pistil": 8, "pistil_grain": 9, "spark": 10,
    "meteor_head": 11, "meteor_train": 12, "meteor_fragment": 13,
}

#: The visual profile of every role: the energy of the role relative to the
#: head. A filament is thinner and less energetic than a spark.
ROLE_ENERGY = {
    "head": 1.0, "filament": 0.45, "grain": 0.8, "ember": 0.6, "flash": 1.0,
    "smoke": 0.3, "shell": 0.9, "shell_trail": 0.5, "pistil": 1.0,
    "pistil_grain": 0.8, "spark": 0.9, "meteor_head": 1.0,
    "meteor_train": 0.55, "meteor_fragment": 0.6,
}

GRAVITY = Vector((0.0, 0.0, -9.81))
#: The object index of the FX in the render: the compositor uses it to build
#: an exact mask, so the other emissive surfaces of the scene never enter the
#: FX layer.
FX_PASS_INDEX = 12
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
        try:
            settings.fx_uid = ident
        except (AttributeError, RuntimeError):
            # During panel draw or other restricted contexts Blender blocks
            # writes to ID-class properties. The identity is already stored in
            # scene[ID_KEY]; this cache on settings is best-effort only.
            pass
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


def _material(name, color, strength, instancer=False):
    """The material of the particles.

    The energy is read from an attribute. The type of the attribute was
    verified in the runtime: the point attributes of the instancer reach the
    instances as geometry attributes, and the geometry lookup is the one
    that returns the value in both backends (the instancer lookup returns a
    constant). The flag is kept for the experiments.
    """
    suffix = ""
    key = "%s%s|%.3f|%.3f|%.3f|%.2f" % (name, suffix, color[0], color[1],
                                         color[2], strength)
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
            _bind_energy(mat, bsdf, strength, instancer)
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = rgba
            bsdf.inputs["Emission Strength"].default_value = strength
            _bind_energy(mat, bsdf, strength, instancer)
        bsdf.inputs["Roughness"].default_value = 0.4
    return mat


def _bind_energy(mat, bsdf, strength, instancer=False):
    """Drive the emission strength with the per particle energy attribute.

    The geometry scale and the emissive energy are two different curves: the
    particle shrinks and fades on its own law.
    """
    node_tree = mat.node_tree
    attribute = node_tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = "energy"
    if hasattr(attribute, "attribute_type"):
        attribute.attribute_type = "GEOMETRY"
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


def _stable_noise(index, particle):
    """A deterministic per particle variation: never a per frame flicker."""
    key = int(index) * 2654435761 % 1000003
    return _hash_unit(0, 0, key, 17)


def _event_color(particle):
    """The colour of the event of a particle."""
    color = particle.get("color")
    if color is None:
        return (1.0, 1.0, 1.0)
    return tuple(color[:3])


def _gn_points_object(scene, name, material, particles, trail=0.0,
                      age_offset=0.0, min_scale=0.35, decay_power=1.0,
                      energy_power=1.0, gravity=None, camera_position=None,
                      atmospheric_fade=0.0, role_energy=1.0,
                      time_override=0.0, use_time_override=0.0):
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
            ("role", "INT", [ROLE_CODES.get(p["role"], 0) for p in particles]),
            ("stable_noise", "FLOAT",
             [_stable_noise(index, p) for index, p in enumerate(particles)]),
            ("event_color", "FLOAT_VECTOR",
             [tuple(_event_color(p)) for p in particles]),
            ("vel", "FLOAT_VECTOR", [p["vel"] for p in particles]),
            ("pos0", "FLOAT_VECTOR", [p["pos0"] for p in particles]),
            ("jitter", "FLOAT_VECTOR", [p["jitter"] for p in particles])):
        attribute = mesh.attributes.new(attr_name, attr_type, "POINT")
        if attr_type in ("FLOAT", "INT"):
            attribute.data.foreach_set("value", values)
        else:
            flat = []
            for vector in values:
                flat.extend(vector)
            attribute.data.foreach_set("vector", flat)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    obj.pass_index = FX_PASS_INDEX
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
                                   atmospheric_fade=atmospheric_fade,
                                   role_energy=role_energy,
                                   time_override=time_override,
                                   use_time_override=use_time_override)
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
              role="head", spoke=0, trail=0.0, color=None, gravity=None,
              persistence=0.0):
    """One deterministic particle: the data shared by both backends."""
    return {
        "birth": float(birth), "life": float(life), "drag": float(drag),
        "radius": float(radius), "vel": Vector(vel), "pos0": Vector(pos0),
        "tau": float(tau), "jitter": Vector(jitter or (0.0, 0.0, 0.0)),
        "use_decay": float(use_decay), "min_scale": float(min_scale),
        "decay_power": float(decay_power),
        "energy_power": float(energy_power), "role": role, "spoke": int(spoke),
        "trail": float(trail), "color": tuple(color) if color else None,
        "gravity": Vector(gravity) if gravity is not None else GRAVITY.copy(),
        "persistence": float(persistence),
    }


def shell_population(launch, v0, drag, birth, rise_time, size_scale,
                     color=None):
    """The rising shell: the body and its short trail."""
    head = _particle(birth, rise_time, drag, 0.20 * size_scale, v0, launch,
                     use_decay=0.0, role="shell", color=color)
    trail = []
    for step in range(SAMPLES):
        profile = step / (SAMPLES - 1.0)
        trail.append(_particle(
            birth, rise_time, drag, 0.6 + 0.4 * profile, v0, launch,
            tau=rise_time * (1.0 - profile), use_decay=0.0, role="shell_trail",
            spoke=0, trail=rise_time, color=color))
    return {"head": head, "trail": trail}


def burst_population(seed, index, config, birth, center, size_scale,
                     spoke_count, shell_velocity=None, colors=None,
                     gravity=None):
    """Deterministic initial conditions of one burst.

    The same data feeds the Geometry Nodes attributes and the Python writer:
    the two backends cannot diverge. ``shell_velocity`` is the residual
    velocity of the rising shell: the stars inherit its momentum, so the burst
    continues the motion of the shell without a discontinuity.
    """
    palette = colors or ((1.0, 1.0, 1.0),) * 3
    inherit = Vector(shell_velocity) if shell_velocity is not None \
        else Vector((0.0, 0.0, 0.0))
    gravity = GRAVITY if gravity is None else Vector(gravity)
    heads = []
    grains = []
    trail = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        v0 = v0 + inherit
        slot = spoke % 3
        heads.append(_particle(birth, life, config["drag"],
                               0.13 * size_scale, v0, center, role="head",
                               spoke=spoke, color=palette[0], gravity=gravity))
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
                spoke=spoke, trail=config["trail"], color=palette[slot],
                gravity=gravity))
            trail.append(_particle(
                birth, life, config["drag"],
                0.25 + 0.9 * profile ** 1.4, v0, center, tau=tau,
                use_decay=0.0, role="filament", spoke=spoke,
                trail=config["trail"], color=palette[slot],
                gravity=gravity))

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
        v0 = v0 + inherit
        drag = config["drag"] * 1.2
        pistil.append(_particle(birth, life, drag, 0.10 * size_scale, v0, center,
                                role="pistil", color=palette[1],
                                gravity=gravity))
        for step in range(SAMPLES):
            profile = step / (SAMPLES - 1.0)
            pistil_grains.append(_particle(
                birth, life, drag,
                0.028 * size_scale * (0.25 + 0.75 * profile), v0, center,
                tau=config["trail"] * 0.6 * (1.0 - profile), use_decay=0.0,
                role="pistil_grain", trail=config["trail"] * 0.6,
                color=palette[1], gravity=gravity))

    sparks = []
    for spoke in range(spoke_count):
        life, v0 = _gn_star_data(seed, index, config, spoke, spoke_count)
        # The star inherits the residual velocity of the rising shell: the
        # child sparks inherit the same one, so the whole burst continues
        # the motion of the shell.
        star_v0 = v0 + inherit
        for child in range(config["sparks"]):
            emit = _hash_range(seed, index, spoke * 8 + child, 4, 0.05,
                               life * 0.55)
            child_life = _hash_range(seed, index, spoke * 8 + child, 5, 0.45,
                                     1.5)
            # The origin is fixed at the emission instant: the spark is a
            # body of its own, not a particle of a moving source. The
            # position and the velocity of the parent are the ones of the
            # star, with the residual velocity of the shell.
            parent_pos = _position(center, star_v0, config["drag"], emit)
            parent_vel = _velocity(star_v0, config["drag"], emit)
            perturb = Vector((
                _hash_range(seed, index, spoke * 8 + child, 6, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 7, -1.6, 1.6),
                _hash_range(seed, index, spoke * 8 + child, 8, -1.6, 1.6),
            )) * 1.2
            sparks.append(_particle(
                birth + emit, child_life, 2.4, 0.045 * size_scale,
                parent_vel * 0.35 + perturb, parent_pos, min_scale=0.0,
                role="spark", color=palette[2], gravity=gravity))

    flash = [_particle(birth, config["core"], 100.0, 0.25 * size_scale,
                        Vector((0.0, 0.0, 0.0)), center, min_scale=0.0,
                        decay_power=0.5, role="flash", color=palette[1],
                        gravity=gravity)]
    return {"heads": heads, "grains": grains, "trail": trail,
            "pistil": pistil, "pistil_grains": pistil_grains,
            "sparks": sparks, "flash": flash}


def _energy_powers(scene):
    """The energy decay exponents of every role."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return {}
    head = float(settings.fx_energy_head)
    grain = float(settings.fx_energy_grain)
    ember = float(settings.fx_energy_ember)
    return {"head": head, "pistil": head, "flash": head, "shell": head,
            "meteor_head": head, "filament": grain, "grain": grain,
            "pistil_grain": grain, "shell_trail": grain, "meteor_train": grain,
            "ember": ember, "spark": ember, "meteor_fragment": ember}


def _atmospheric_fade(scene):
    """The atmospheric attenuation of the FX emission."""
    settings = getattr(scene, "ald", None)
    return float(settings.fx_atmospheric_fade) if settings else 0.0


def _particle_state(particle, time, powers=None, fade=0.0, camera=None):
    """Evaluate one particle: position, scale, energy and alive flag."""
    age = time - particle["birth"]
    life = max(particle["life"], 1e-3)
    gravity = particle.get("gravity", GRAVITY)
    # The train never runs ahead of the body: the front of the train is the
    # last position of the body. After the body dies no new sample is born
    # along the trajectory: the residuals fade, they do not travel.
    persistence = float(particle.get("persistence", 0.0))
    front = min(max(age, 0.0), max(life - persistence, 0.0))
    window = particle.get("trail", 0.0)
    if window > 0.0:
        train = min(front, window)
        tau = particle["tau"] * (train / window)
    else:
        tau = 0.0
    sample_age = front - tau
    alive = 0.0 <= age <= particle["life"] and sample_age >= 0.0
    u = min(max(age / life, 0.0), 1.0)
    if sample_age <= 0.0:
        position = particle["pos0"].copy()
    else:
        position = _position(particle["pos0"], particle["vel"],
                             particle["drag"], sample_age, gravity)
    position = position + particle["jitter"]
    minimum = particle["min_scale"]
    shape = minimum + (1.0 - minimum) * (1.0 - u) ** particle["decay_power"]
    scale = particle["radius"] * (shape if particle["use_decay"] else 1.0)
    power = particle["energy_power"]
    if powers:
        power = powers.get(particle["role"], power)
    energy = (1.0 - u) ** power
    energy *= ROLE_ENERGY.get(particle["role"], 1.0)
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
                     age_offset=0.0, radius=0.02, fade_window=0.0,
                     time_override=0.0, use_time_override=0.0,
                     energy_power=1.0, role_energy=1.0):
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
    obj.pass_index = FX_PASS_INDEX
    _collection(scene).objects.link(obj)
    group, sockets = fx_nodes.build_trail_group()
    fx_nodes.attach_trail_modifier(obj, group, sockets, GRAVITY, material,
                                   trail=trail, age_offset=age_offset,
                                   radius=radius, fade_window=fade_window,
                                   time_override=time_override,
                                   use_time_override=use_time_override,
                                   energy_power=energy_power,
                                   role_energy=role_energy)
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


def _gravity(scene):
    """The world gravity used by the FX."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return GRAVITY
    return Vector(settings.fx_gravity)


def _launch_point(origin, forward, up, right, target):
    """The default launcher: below the burst point, in the world space.

    The shell rises vertically, so the shot shows a real ascent.
    """
    return Vector(target) - Vector((0.0, 0.0, 26.0))


def _launcher_empty(scene, index, position, system=None, event=None):
    """The visible launcher of a burst: an empty the user can grab.

    The empty is the manipulator of the persistent event: it carries the
    identity of the system and of the event, so it is never searched by a
    global name (two scenes, two systems: the same name would collide) and
    it is never removed by an update of the geometry.
    """
    empty = None
    system_uid = system.uid if system is not None else ""
    event_uid = event.uid if event is not None else ""
    for candidate in _collection(scene).objects:
        if not candidate.get("ald_fx"):
            continue
        if candidate.get("ald_fx_role") != "launcher":
            continue
        if candidate.get("ald_fx_system") != system_uid:
            continue
        if candidate.get("ald_fx_event") != event_uid:
            continue
        empty = candidate
        break
    if empty is None:
        name = "ALD FX Launcher %s %d" % (system_uid[:6] or "new", index)
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "SPHERE"
        empty.empty_display_size = 1.2
        _collection(scene).objects.link(empty)
    empty["ald_fx"] = True
    empty["ald_fx_kind"] = "fireworks"
    empty["ald_fx_role"] = "launcher"
    empty["ald_fx_index"] = index
    if system is not None:
        empty["ald_fx_system"] = system_uid
    if event is not None:
        empty["ald_fx_event"] = event_uid
    if position is not None:
        empty.location = Vector(position)
    return empty


def _empty_position(empty):
    """The world position of a manipulator.

    The local transform is always up to date, the matrix is not.
    """
    if empty is None:
        return None
    if empty.parent is None:
        return empty.location.copy()
    return empty.matrix_world.translation.copy()


def _fps(scene):
    """The effective frame rate of the scene."""
    return max(scene.render.fps / max(scene.render.fps_base, 1e-6), 1e-6)


def system_clock(scene, system=None):
    """The clock of a system: the offset and the override of the group.

    Timeline: the local time is ``(frame - origin_frame) / fps``.
    Preview: the local time is the value chosen by the user and it does not
    depend on the frame.
    The Burst Age is the director control: it shifts every system.
    """
    age = _age_offset(scene)
    mode = getattr(system, "timing_mode", "TIMELINE") if system else "TIMELINE"
    if mode == "PREVIEW":
        return {"age_offset": 0.0,
                "override": float(getattr(system, "origin_time", 0.0)) + age,
                "use_override": 1.0}
    origin_frame = float(getattr(system, "origin_frame", 1.0)) if system else 1.0
    # The Scene Time node counts the frames from the first one: the offset
    # of the group compensates the origin frame of the system.
    return {"age_offset": age - origin_frame / _fps(scene),
            "override": 0.0, "use_override": 0.0}


def system_time(scene, system=None):
    """The local time of a system, in seconds."""
    clock = system_clock(scene, system)
    if clock["use_override"] > 0.5:
        return clock["override"]
    origin_frame = float(getattr(system, "origin_frame", 1.0)) if system else 1.0
    return (scene.frame_current + scene.frame_subframe - origin_frame) \
        / _fps(scene) + _age_offset(scene)


def _rise_time(scene, index):
    """The rise time of the shell of a burst."""
    settings = getattr(scene, "ald", None)
    if settings is not None and settings.fx_systems:
        system = settings.fx_systems[0]
        for event in system.events:
            if event.kind == "FIREWORK":
                return float(event.rise_time)
    return 1.2


def _event_drag(scene, config):
    """The drag of the rising shell."""
    settings = getattr(scene, "ald", None)
    if settings is not None and settings.fx_systems:
        for event in settings.fx_systems[0].events:
            if event.kind == "FIREWORK":
                return float(event.drag)
    return float(config["drag"])


def _rise_velocity(launcher, target, rise_time, drag, gravity, mode="DIRECTOR",
                   speed=0.0, direction=None):
    """The initial velocity of the rising shell.

    Director mode: the burst target and the rise time define the shot.
    Physical mode: the launcher, the direction and the speed define the shot.
    With a linear drag and a constant wind:

        v_inf = w + g / k
        A(T)  = (1 - exp(-k T)) / k
        v0    = v_inf + (pB - pL - v_inf T) / A(T)

    Without drag the limit is ``v0 = (pB - pL - 0.5 g T^2) / T``.
    """
    launcher = Vector(launcher)
    delta = Vector(target) - launcher
    gravity = Vector(gravity)
    if rise_time <= 1e-6:
        return delta
    if mode == "PHYSICAL":
        if direction is None:
            return delta / rise_time
        direction = Vector(direction)
        if direction.length < 1e-6:
            return delta / rise_time
        return direction.normalized() * float(speed)
    if drag < 1e-4:
        return (delta - 0.5 * gravity * rise_time * rise_time) / rise_time
    v_inf = gravity / drag
    a = (1.0 - math.exp(-drag * rise_time)) / drag
    if a < 1e-9:
        return delta / rise_time
    return v_inf + (delta - v_inf * rise_time) / a


def _rise_position(launcher, v0, drag, gravity, elapsed):
    """The position of the rising shell after ``elapsed`` seconds."""
    launcher = Vector(launcher)
    gravity = Vector(gravity)
    if elapsed <= 0.0:
        return launcher.copy()
    if drag < 1e-6:
        return launcher + v0 * elapsed + 0.5 * gravity * elapsed * elapsed
    x = drag * elapsed
    if x < 1e-3:
        factor = elapsed * (1.0 - x * (0.5 - x * (1.0 / 6.0 - x / 24.0)))
        gravity_term = elapsed * elapsed * (0.5 - x * (1.0 / 6.0 - x / 24.0))
        return launcher + v0 * factor + gravity * gravity_term
    factor = -math.expm1(-x) / drag
    return launcher + v0 * factor + gravity * (elapsed - factor) / drag


def _rise_velocity_at(v0, drag, gravity, elapsed):
    """The residual velocity of the rising shell."""
    gravity = Vector(gravity)
    if drag < 1e-4:
        return v0 + gravity * elapsed
    v_inf = gravity / drag
    return v_inf + (v0 - v_inf) * math.exp(-drag * elapsed)


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


def _position(p0, v0, drag, age, gravity=None):
    """Position at ``age`` seconds with linear drag and world gravity.

    The closed form ``p0 + v_inf a + (v0 - v_inf) A`` cancels two large
    terms when the drag is small. The stable form is used instead:

        p = p0 + v0 A + g (a - A) / k,  A = (1 - e^(-k a)) / k

    with a series expansion of A for the small ``k a``. The gravity is the
    one of the context: the scene and the event must not disagree.
    """
    gravity = GRAVITY if gravity is None else Vector(gravity)
    if age <= 0.0:
        return p0.copy()
    if drag < 1e-6:
        return p0 + v0 * age + 0.5 * gravity * (age * age)
    x = drag * age
    if x < 1e-3:
        # A = a (1 - x/2 + x^2/6 - x^3/24) and (a - A)/k = a^2 (1/2 - x/6).
        factor = age * (1.0 - x * (0.5 - x * (1.0 / 6.0 - x / 24.0)))
        gravity_term = age * age * (0.5 - x * (1.0 / 6.0 - x / 24.0))
        return p0 + v0 * factor + gravity * gravity_term
    factor = -math.expm1(-x) / drag
    return p0 + v0 * factor + gravity * (age - factor) / drag


def _velocity(v0, drag, age, gravity=None):
    """The velocity at ``age`` seconds, in the stable form.

    The velocity is the derivative of the position: the decay of the initial
    velocity is ``exp(-x)``, not the expansion of A. The series is

        exp(-x) = 1 - x + x^2/2 - x^3/6
    """
    gravity = GRAVITY if gravity is None else Vector(gravity)
    if drag < 1e-6:
        return v0 + gravity * age
    x = drag * age
    if x < 1e-3:
        decay = 1.0 - x * (1.0 - x * 0.5)
        return v0 * decay + gravity * age * (1.0 - x * 0.5)
    decay = math.exp(-x)
    return v0 * decay + gravity * (-math.expm1(-x) / drag)


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
    obj.pass_index = FX_PASS_INDEX
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
    obj.pass_index = FX_PASS_INDEX
    _collection(scene).objects.link(obj)
    return obj


def _camera_basis(scene):
    """The evaluated camera frame: the constraints and the parents included.

    The local transform of a camera with a constraint or a parent is not the
    frame of the shot: the evaluated matrix is the only reliable source.
    """
    camera = scene.camera
    if camera is None:
        return (Vector((0.0, -8.0, 1.5)), Vector((0.0, 1.0, 0.0)),
                Vector((0.0, 0.0, 1.0)), Vector((1.0, 0.0, 0.0)))
    matrix = None
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = camera.evaluated_get(depsgraph)
        matrix = evaluated.matrix_world
    except Exception:
        matrix = None
    if matrix is None:
        matrix = camera.matrix_world
    origin = matrix.translation.copy()
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

def _build_python_objects(scene, kind, family_key, index, population, config,
                          center, spoke_count, pistil_count, materials,
                          size_scale):
    """The meshes of the Python writer: the fallback backend."""
    trail_obj = _build_curve(scene, "ALD FX %s %d Filament" % (family_key, index),
                             spoke_count, materials, 0.022 * size_scale)
    trail_obj["ald_fx_kind"] = kind
    bead_objects = []
    for slot in range(3):
        grains = [p for p in population["grains"] if p["spoke"] % 3 == slot]
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
    return {"trail": trail_obj, "heads": head_obj, "head_ranges": head_ranges,
            "beads": bead_objects, "pistil_obj": pistil_obj,
            "pistil_ranges": pistil_ranges, "pistil_bead_obj": pistil_bead_obj,
            "pistil_bead_ranges": pistil_bead_ranges, "sparks": spark_obj,
            "spark_ranges": spark_ranges, "core": core_obj,
            "core_ranges": core_ranges}


def _event_config(event):
    """The configuration of a family, with the overrides of the event."""
    config = dict(FAMILY_CONFIG[event.family])
    if int(event.spokes) > 0:
        config["spokes"] = int(event.spokes)
    if int(event.pistil) >= 0 and int(event.pistil) != FAMILY_CONFIG[
            event.family]["pistil"]:
        config["pistil"] = int(event.pistil)
    if int(event.sparks) >= 0 and int(event.sparks) != FAMILY_CONFIG[
            event.family]["sparks"]:
        config["sparks"] = int(event.sparks)
    return config


def _build_fireworks(scene, system):
    """Build the geometry of the firework events of a system.

    The persistent events are the source of truth: the camera is not read
    here, the world positions were written in the events when they were
    created. Moving the camera never moves an event.
    """
    settings = getattr(scene, "ald", None)
    clock = system_clock(scene, system)
    age_offset = clock["age_offset"]
    gravity = _gravity(scene)
    bursts = []
    events = [event for event in system.events if event.enabled]
    total = len(events)
    for index, event in enumerate(events):
        family_key = event.family
        config = _event_config(event)
        spoke_count = config["spokes"]
        pistil_count = config["pistil"]
        size_scale = max(0.6, min(2.0, float(event.size)))
        birth = float(event.birth)
        center = Vector(event.target)
        target = center
        # The launcher of the event wins: the user can grab it.
        launch = Vector(event.launcher)
        rise_time = float(event.rise_time)
        drag = float(event.drag)
        launch_mode = event.launch_mode
        speed = float(event.speed)
        direction = Vector(event.direction)
        # The empty of the scene is the manipulator of the event: it is read
        # before anything is removed, so a moved launcher is never lost.
        empty = _launcher_empty(scene, index, launch, system, event)
        if empty is not None:
            launch = _empty_position(empty)
        v0 = _rise_velocity(launch, target, rise_time, drag, gravity,
                            mode=launch_mode, speed=speed,
                            direction=direction)
        burst_birth = birth + rise_time
        residual = _rise_velocity_at(v0, drag, gravity, rise_time)
        shell = shell_population(launch, v0, drag, birth, rise_time, size_scale)
        # The deterministic data is built once and feeds both backends.
        population = burst_population(seed=int(event.seed), index=index,
                                      config=config, birth=burst_birth,
                                      center=target, size_scale=size_scale,
                                      spoke_count=spoke_count,
                                      shell_velocity=residual,
                                      gravity=gravity)
        family_colors = PALETTES[index % len(PALETTES)]
        # The backend is chosen before any allocation: the two paths never
        # build the same geometry twice. The material reads the energy from
        # the domain of its backend: the instances or the points.
        use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
            else False
        materials = [
            _material("ALD FX %s %d A" % (family_key, index), family_colors[0],
                      6.0, instancer=use_gn),
            _material("ALD FX %s %d B" % (family_key, index), family_colors[1],
                      6.0, instancer=use_gn),
            _material("ALD FX %s %d C" % (family_key, index), family_colors[2],
                      6.0, instancer=use_gn),
        ]
        trail_obj = None
        head_obj = None
        head_ranges = []
        bead_objects = []
        pistil_obj = None
        pistil_ranges = []
        pistil_bead_obj = None
        pistil_bead_ranges = []
        spark_obj = None
        spark_ranges = []
        core_obj = None
        core_ranges = []
        if not use_gn:
            python_objects = _build_python_objects(
                scene, kind="fireworks", family_key=family_key, index=index,
                population=population, config=config, center=center,
                spoke_count=spoke_count, pistil_count=pistil_count,
                materials=materials, size_scale=size_scale)
            trail_obj = python_objects["trail"]
            head_obj = python_objects["heads"]
            head_ranges = python_objects["head_ranges"]
            bead_objects = python_objects["beads"]
            pistil_obj = python_objects["pistil_obj"]
            pistil_ranges = python_objects["pistil_ranges"]
            pistil_bead_obj = python_objects["pistil_bead_obj"]
            pistil_bead_ranges = python_objects["pistil_bead_ranges"]
            spark_obj = python_objects["sparks"]
            spark_ranges = python_objects["spark_ranges"]
            core_obj = python_objects["core"]
            core_ranges = python_objects["core_ranges"]
        gn_heads = None
        gn_beads = []
        gn_pistil = None
        gn_sparks = None
        gn_flash = None
        gn_trails = []
        # Geometry Nodes path: the node group evaluates the same data.
        if use_gn:
            created = []
            try:
                powers = _energy_powers(scene)
                fade = _atmospheric_fade(scene)
                camera_position = tuple(_camera_basis(scene)[0])
                gn_heads = _gn_points_object(
                    scene, "ALD FX GN Heads %d" % index, materials[0],
                    population["heads"], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("head", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["head"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
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
                        atmospheric_fade=fade,
                        role_energy=ROLE_ENERGY["grain"],
                        time_override=clock["override"],
                        use_time_override=clock["use_override"])
                    created.append(bead_gn)
                    gn_beads.append(bead_gn)
                gn_pistil = _gn_points_object(
                    scene, "ALD FX GN Pistil %d" % index, materials[1],
                    population["pistil"], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("pistil", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["pistil"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_pistil)
                gn_pistil_grains = _gn_points_object(
                    scene, "ALD FX GN Pistil Grains %d" % index, materials[1],
                    population["pistil_grains"],
                    trail=config["trail"] * 0.6, age_offset=age_offset,
                    energy_power=powers.get("pistil_grain", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["pistil_grain"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_pistil_grains)
                gn_beads.append(gn_pistil_grains)
                gn_sparks = _gn_points_object(
                    scene, "ALD FX GN Sparks %d" % index, materials[2],
                    population["sparks"], trail=0.0, age_offset=age_offset,
                    min_scale=0.0,
                    energy_power=powers.get("spark", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["spark"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_sparks)
                for slot in range(3):
                    samples = [p for p in population["trail"]
                               if p["spoke"] % 3 == slot]
                    trail_gn = _gn_trail_object(
                        scene, "ALD FX GN Trail %d %d" % (index, slot),
                        materials[slot], samples, trail=config["trail"],
                        age_offset=age_offset, radius=0.022 * size_scale,
                        time_override=clock["override"],
                        use_time_override=clock["use_override"],
                        energy_power=powers.get("filament", 1.0),
                        role_energy=ROLE_ENERGY["filament"])
                    created.append(trail_gn)
                    gn_trails.append(trail_gn)
                gn_flash = _gn_points_object(
                    scene, "ALD FX GN Flash %d" % index, materials[1],
                    population["flash"], trail=0.0, age_offset=age_offset,
                    min_scale=0.0, decay_power=0.5,
                    energy_power=powers.get("flash", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["flash"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_flash)
                # The rising shell and its short trail.
                gn_shell = _gn_points_object(
                    scene, "ALD FX GN Shell %d" % index, materials[0],
                    [shell["head"]], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("shell", 1.0),
                    camera_position=camera_position,
                    atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["shell"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_shell)
                gn_shell_trail = _gn_trail_object(
                    scene, "ALD FX GN Shell Trail %d" % index, materials[0],
                    shell["trail"], trail=rise_time, age_offset=age_offset,
                    radius=0.03 * size_scale,
                    time_override=clock["override"],
                    use_time_override=clock["use_override"],
                    energy_power=powers.get("shell_trail", 1.0),
                    role_energy=ROLE_ENERGY["shell_trail"])
                created.append(gn_shell_trail)
                for obj in created:
                    obj["ald_fx_kind"] = "fireworks"
                    obj["ald_fx_system"] = system.uid
                    obj["ald_fx_event"] = event.uid
                # The replaced Python meshes must not survive as orphans.
                _cleanup_orphans()
            except Exception as exc:
                print("ALD FX GN BUILD FAILED", exc)
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
            "center": center, "birth": birth, "seed": int(event.seed),
            "size_scale": size_scale, "materials": materials,
            "population": population, "shell": shell,
            "launch": launch, "shell_velocity": v0, "drag": drag,
            "rise_time": rise_time, "target": target,
            "burst_birth": burst_birth, "residual": residual,
            "event": event,
            "spread_x": (-0.18 + 0.36 * (index + 0.5) / max(total, 1)),
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
    # Conflict check (T15 of the operational plan): if the camera looks below
    # the ground or a burst target is under the ground elevation, report the
    # conflict instead of silently generating underground coordinates.
    conflict = False
    if settings is not None and scene.camera is not None:
        ground = float(getattr(settings, "fx_anchor_ground_elevation", 0.0))
        axis = getattr(settings, "fx_anchor_axis", "Z")
        axis_index = {"Z": 2, "Y": 1, "X": 0}.get(axis, 2)
        axis_sign = -1.0 if axis.startswith("-") else 1.0
        cam = scene.camera
        cam_matrix = cam.matrix_world
        cam_forward = (cam_matrix.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        # Camera looking down toward the ground?
        if cam_forward[axis_index] * axis_sign < -0.1:
            conflict = True
        # Any burst target under the ground?
        for burst in bursts:
            if burst["center"][axis_index] < ground + 1.0:
                conflict = True
                break
    if conflict:
        scene["ald_fx_conflict_warning"] = (
            "Camera points below the ground or a burst target is under the "
            "ground elevation: no silent underground target was generated.")
    else:
        scene.pop("ald_fx_conflict_warning", None)
    return {"kind": "fireworks", "bursts": bursts, "time": None,
            "scene": scene, "camera": _camera_basis(scene)[0],
            "uid": system.uid, "system": system,
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
                      persistence, radius=0.18, fragments=3, gravity=None):
    """Deterministic data of one meteor: head, train and fragments.

    Every component shares the same ``event_birth``: the train and the
    fragments can never appear before the body.
    """
    gravity = GRAVITY if gravity is None else Vector(gravity)
    head = _particle(event_birth, life, drag, radius, v0, start, use_decay=0.0,
                     role="meteor_head", spoke=index, gravity=gravity)
    train_samples = []
    for step in range(SAMPLES):
        profile = step / (SAMPLES - 1.0)
        train_samples.append(_particle(
            event_birth, life + persistence, drag, 0.2 + 0.8 * profile, v0,
            start, tau=train * (1.0 - profile), use_decay=0.0,
            role="meteor_train", spoke=index, trail=train,
            gravity=gravity, persistence=persistence))
    fragment_points = []
    for fragment in range(fragments):
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
        fragment_points.append(_particle(
            event_birth + emit, frag_life, 1.6, 0.05, parent_vel * 0.25 + push,
            parent, role="meteor_fragment", spoke=index, gravity=gravity))
    return {"head": head, "train": train_samples, "fragments": fragment_points}


def _build_meteors(scene, system):
    """Build the geometry of the meteor events of a system.

    The persistent events are the source of truth: the start point, the
    direction, the speed and the lifetime are read from them. Every event
    owns its objects, so a single event can be hidden, measured or removed
    without touching the others.
    """
    origin, _forward, _up, _right = _camera_basis(scene)
    clock = system_clock(scene, system)
    age_offset = clock["age_offset"]
    settings = getattr(scene, "ald", None)
    use_gn = bool(getattr(settings, "fx_gn_prototype", True)) if settings \
        else False
    persistence = float(getattr(settings, "fx_meteor_persistence", 0.32)) \
        if settings else 0.32
    events = [event for event in system.events if event.enabled]
    total = max(1, len(events))
    material = _material("ALD FX Meteor", (0.85, 0.94, 1.0), 9.0,
                         instancer=use_gn)
    runtime = {"kind": "meteors", "count": total, "seed": int(system.seed),
               "distance": 0.0, "shower": Vector((1.0, 0.0, 0.0)),
               "origin": origin, "material": material, "gn": False,
               "trail": None, "preset": events[0].kind if events else "METEOR",
               "uid": system.uid,
               "system": system, "events": [],
               "heads": None, "head_ranges": [], "fragments": None,
               "fragment_ranges": [], "populations": []}
    populations = []
    for index, event in enumerate(events):
        preset = METEOR_PRESETS.get(event.kind, METEOR_PRESETS["METEOR"])
        drag = float(event.drag) if float(event.drag) > 0.0 \
            else preset["drag"]
        life = float(event.life)
        start = Vector(event.target)
        direction = Vector(event.direction)
        if direction.length < 1e-6:
            direction = Vector((1.0, 0.0, 0.0))
        direction = direction.normalized()
        v0 = direction * float(event.speed)
        population = _meteor_population(
            int(event.seed), index, start, v0, drag, float(event.birth), life,
            preset["train"], persistence, radius=preset["radius"],
            fragments=int(event.sparks) if int(event.sparks) > 0
            else preset["fragments"], gravity=_gravity(scene))
        populations.append(population)
        entry = {"index": index, "event": event, "population": population,
                 "preset": preset, "gn": False, "trail": None, "heads": None,
                 "head_ranges": [], "fragments": None,
                 "fragment_ranges": []}
        if use_gn:
            created = []
            try:
                powers = _energy_powers(scene)
                fade = _atmospheric_fade(scene)
                camera_position = tuple(origin)
                gn_heads = _gn_points_object(
                    scene, "ALD FX GN Meteor Heads %d" % index, material,
                    [population["head"]], trail=0.0, age_offset=age_offset,
                    energy_power=powers.get("meteor_head", 1.0),
                    camera_position=camera_position, atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["meteor_head"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_heads)
                gn_train = _gn_trail_object(
                    scene, "ALD FX GN Meteor Trails %d" % index, material,
                    population["train"], trail=preset["train"],
                    age_offset=age_offset,
                    radius=0.07 * (preset["radius"] / 0.18),
                    fade_window=persistence,
                    time_override=clock["override"],
                    use_time_override=clock["use_override"],
                    energy_power=powers.get("meteor_train", 1.0),
                    role_energy=ROLE_ENERGY["meteor_train"])
                created.append(gn_train)
                gn_fragments = _gn_points_object(
                    scene, "ALD FX GN Meteor Fragments %d" % index, material,
                    population["fragments"], trail=0.0, age_offset=age_offset,
                    min_scale=0.0,
                    energy_power=powers.get("meteor_fragment", 1.0),
                    camera_position=camera_position, atmospheric_fade=fade,
                    role_energy=ROLE_ENERGY["meteor_fragment"],
                    time_override=clock["override"],
                    use_time_override=clock["use_override"])
                created.append(gn_fragments)
                for obj in created:
                    obj["ald_fx_kind"] = "meteors"
                    obj["ald_fx_system"] = system.uid
                    obj["ald_fx_event"] = event.uid
                entry["gn"] = True
                entry["gn_heads"] = gn_heads
                entry["gn_train"] = gn_train
                entry["gn_fragments"] = gn_fragments
                runtime["gn"] = True
            except Exception as exc:
                print("ALD FX: geometry nodes meteors failed (%s)" % exc)
                for obj in created:
                    if obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                _cleanup_orphans()
        if not entry["gn"]:
            trail_obj = _build_curve(scene, "ALD FX Meteor Trails %d" % index,
                                     1, [material],
                                     0.07 * (preset["radius"] / 0.18))
            trail_obj["ald_fx_kind"] = "meteors"
            trail_obj["ald_fx_system"] = system.uid
            trail_obj["ald_fx_event"] = event.uid
            head_obj, head_ranges = _build_particle_mesh(
                "ALD FX Meteor Heads %d" % index, [origin], [0.001], material)
            _collection(scene).objects.link(head_obj)
            head_obj["ald_fx_kind"] = "meteors"
            head_obj["ald_fx_system"] = system.uid
            head_obj["ald_fx_event"] = event.uid
            fragment_total = len(population["fragments"])
            fragment_obj, fragment_ranges = _build_particle_mesh(
                "ALD FX Meteor Fragments %d" % index, [origin] * fragment_total,
                [0.001] * fragment_total, material)
            _collection(scene).objects.link(fragment_obj)
            fragment_obj["ald_fx_kind"] = "meteors"
            fragment_obj["ald_fx_system"] = system.uid
            fragment_obj["ald_fx_event"] = event.uid
            entry["trail"] = trail_obj
            entry["heads"] = head_obj
            entry["head_ranges"] = head_ranges
            entry["fragments"] = fragment_obj
            entry["fragment_ranges"] = fragment_ranges
        runtime["events"].append(entry)
    runtime["populations"] = populations
    return runtime


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
                     fps=24.0, family="CHRYSANTHEMUM", replace=True):
    """Create a firework system: the persistent events first, then the
    geometry.

    The events are written in the scene and they are the source of truth:
    the geometry is compiled from them and an update never rewrites them.
    """
    if replace:
        clear(scene, kind="fireworks")
    system = _new_system(scene, "FIREWORKS", seed, time)
    origin, forward, up, right = _camera_basis(scene)
    settings = getattr(scene, "ald", None)
    spread = float(getattr(settings, "fx_burst_spread", 1.0)) if settings else 1.0
    offset = Vector(getattr(settings, "fx_composition_offset", (0.0, 0.0, 0.0))) \
        if settings else Vector((0.0, 0.0, 0.0))
    total = max(1, int(count))
    for index in range(total):
        event = system.events.add()
        event.uid = uuid.uuid4().hex
        event.kind = "FIREWORK"
        event.enabled = True
        event.seed = int(seed)
        # The composition: the first burst is the hero, the others are
        # secondary and staggered in time so the sky is never a uniform field.
        role = index % 3
        event.family = family if index == 0 else FAMILIES[(index - 1) %
                                                         len(FAMILIES)]
        event.birth = 0.0 if index == 0 else (0.25 if role == 1 else 0.85)
        config = FAMILY_CONFIG[event.family]
        event.size = 1.0
        event.spokes = config["spokes"]
        event.pistil = config["pistil"]
        event.sparks = config["sparks"]
        family_distance = distance * (1.0 if index == 0 else
                                      (0.78 if role == 1 else 0.58))
        center = _burst_center(origin, forward, up, right, index, total,
                                family_distance * (0.85 + 0.25 *
                                                   _hash_unit(seed, index, 0, 1)),
                                spread) + offset
        event.target = tuple(center)
        event.launcher = tuple(_launch_point(origin, forward, up, right, center))
        event.launch_mode = "DIRECTOR"
        event.rise_time = 1.2
        event.drag = config["drag"]
        event.duration = config["life"]
        event.life = config["life"]
        event.glow = 0.6
    compile_system(scene, system)
    return total


def create_meteors(scene, count=4, seed=21, distance=140.0, time=0.0,
                   fps=24.0, kind="METEOR", replace=True):
    """Create a meteor system: the persistent events first, then the
    geometry."""
    if replace:
        clear(scene, kind="meteors")
    system = _new_system(scene, "METEORS", seed, time)
    origin, forward, up, right = _camera_basis(scene)
    preset = METEOR_PRESETS.get(kind, METEOR_PRESETS["METEOR"])
    # The shower direction is a world direction, almost lateral: the meteors
    # cross the sky instead of moving along the line of sight. The radiant
    # emerges from the convergence of the parallel trajectories.
    shower = (forward * 0.16 + right * 0.94 + up * 0.30).normalized()
    total = max(1, int(count))
    for index in range(total):
        event = system.events.add()
        event.uid = uuid.uuid4().hex
        event.kind = kind
        event.enabled = True
        event.seed = int(seed)
        event.birth = index * preset["spacing"] + _hash_range(
            seed, index, 0, 1, 0.0, 0.6)
        event.family = "WILLOW"
        event.size = 1.0
        event.spokes = 0
        event.pistil = 0
        event.sparks = preset["fragments"]
        # The start points are spread on a plane far away from the camera.
        plane_center = origin + forward * distance
        lateral_x = _hash_range(seed, index, 10, 11, -0.55, 0.55) * distance
        lateral_y = _hash_range(seed, index, 10, 12, -0.30, 0.34) * distance
        start = plane_center + right * lateral_x + up * lateral_y
        event.target = tuple(start)
        event.launcher = tuple(start)
        jitter_range = preset["jitter"]
        jitter = Vector((
            _hash_range(seed, index, 0, 3, -jitter_range, jitter_range),
            _hash_range(seed, index, 0, 4, -jitter_range, jitter_range),
            _hash_range(seed, index, 0, 5, -jitter_range * 0.7,
                        jitter_range * 0.7),
        ))
        direction = (shower + jitter).normalized()
        speed = _hash_range(seed, index, 0, 6, preset["speed"][0],
                            preset["speed"][1])
        event.direction = tuple(direction)
        event.speed = speed
        event.drag = preset["drag"]
        life = _hash_range(seed, index, 0, 2, preset["life"][0],
                            preset["life"][1])
        event.life = life
        event.duration = life
        event.glow = 0.6
    compile_system(scene, system)
    return total


def _new_system(scene, kind, seed, time):
    """Create the persistent description of a system."""
    from .properties import FX_SCHEMA
    settings = getattr(scene, "ald", None)
    if settings is None:
        raise RuntimeError("Anime Look Director settings are not registered")
    system = settings.fx_systems.add()
    system.uid = uuid.uuid4().hex
    system.kind = kind
    system.enabled = True
    system.seed = int(seed)
    system.timing_mode = "TIMELINE"
    system.origin_frame = 1
    system.origin_time = float(time)
    system.isolation_mode = "EMISSION"
    settings.fx_schema = FX_SCHEMA
    return system


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


def system_by_uid(scene, uid):
    """The persistent system with the given identity."""
    settings = getattr(scene, "ald", None)
    if settings is None or not uid:
        return None
    for system in settings.fx_systems:
        if system.uid == uid:
            return system
    return None


def runtime_by_uid(scene, uid):
    """The runtime state of a persistent system."""
    registry = SYSTEMS.get(_scene_id(scene)) or {}
    return registry.get(uid)


def compile_system(scene, system):
    """Build the geometry of a system from its persistent events.

    The objects of the previous build are removed first, but the
    manipulators of the events (the launchers) are read before the removal
    and they survive it.
    """
    if system is None:
        return None
    _remove_system_objects(scene, system.uid)
    if system.kind == "FIREWORKS":
        runtime = _build_fireworks(scene, system)
    else:
        runtime = _build_meteors(scene, system)
    registry = _registry(scene)
    registry[system.uid] = runtime
    _update_system(runtime, system_time(scene, system))
    return runtime


def update_system(scene, system):
    """Recompile a system after a change of its events.

    The identity of the system and of its events is preserved: an update
    never resets the values chosen by the user.
    """
    if system is None:
        return None
    return compile_system(scene, system)


def update_all(scene):
    """Recompile every system of the scene."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return 0
    count = 0
    for system in settings.fx_systems:
        if not system.enabled:
            continue
        compile_system(scene, system)
        count += 1
    return count


def _remove_system_objects(scene, uid):
    """Remove the objects generated by a system.

    The manipulators of the events (the launchers) survive: they are the
    handles of the user, not generated geometry.
    """
    owner = _scene_id(scene)
    for coll in bpy.data.collections:
        if coll.get(OWNER_KEY) != owner:
            continue
        for obj in list(coll.objects):
            if not obj.get("ald_fx"):
                continue
            if obj.get("ald_fx_system") != uid:
                continue
            if obj.get("ald_fx_role") == "launcher":
                continue
            bpy.data.objects.remove(obj, do_unlink=True)
    _cleanup_orphans()


def _find_objects(scene):
    """The ALD objects of a scene, indexed by name."""
    return {obj.name: obj for obj in _collection(scene).objects
            if obj.get("ald_fx")}


def rebuild_registry(scene):
    """Rebuild the runtime registry from the persistent configuration.

    The geometry saved in the file is reused: nothing is regenerated. The
    runtime cache is never the source of truth. The registry is keyed by the
    identity of the system, so two systems of the same kind never collide.
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
        events = [event for event in system.events if event.enabled]
        if not events:
            continue
        if system.kind == "FIREWORKS":
            bursts = []
            for index, event in enumerate(events):
                config = _event_config(event)
                spoke_count = config["spokes"]
                center = Vector(event.target)
                launch = Vector(event.launcher)
                rise_time = float(event.rise_time)
                drag = float(event.drag)
                gravity = _gravity(scene)
                v0 = _rise_velocity(launch, center, rise_time, drag, gravity,
                                    mode=event.launch_mode,
                                    speed=float(event.speed),
                                    direction=Vector(event.direction))
                residual = _rise_velocity_at(v0, drag, gravity, rise_time)
                population = burst_population(event.seed, index, config,
                                              event.birth + rise_time,
                                              center, float(event.size),
                                              spoke_count,
                                              shell_velocity=residual)
                family_key = event.family
                prefix = "ALD FX %s %d " % (family_key, index)
                bursts.append({
                    "index": index, "family": family_key, "config": config,
                    "center": center, "birth": float(event.birth),
                    "seed": event.seed, "size_scale": float(event.size),
                    "materials": [], "population": population,
                    "launch": launch, "shell_velocity": v0, "drag": drag,
                    "rise_time": rise_time, "target": center,
                    "burst_birth": float(event.birth) + rise_time,
                    "residual": residual, "event": event,
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
            registry[system.uid] = {
                "kind": "fireworks", "bursts": bursts, "time": None,
                "uid": system.uid, "system": system,
                "camera": _camera_basis(scene)[0],
                "gn": all(burst["gn_heads"] is not None for burst in bursts)}
            rebuilt += 1
        elif system.kind == "METEORS":
            populations = []
            for index, event in enumerate(events):
                preset = METEOR_PRESETS.get(event.kind, METEOR_PRESETS["METEOR"])
                drag = float(event.drag) if float(event.drag) > 0.0 \
                    else preset["drag"]
                life = float(event.life)
                direction = Vector(event.direction)
                if direction.length < 1e-6:
                    direction = Vector((1.0, 0.0, 0.0))
                direction = direction.normalized()
                start = Vector(event.target)
                v0 = direction * float(event.speed)
                populations.append(_meteor_population(
                    event.seed, index, start, v0, drag, float(event.birth),
                    life, preset["train"], 0.32,
                    radius=preset["radius"], fragments=preset["fragments"]))
            registry[system.uid] = {
                "kind": "meteors", "count": len(populations),
                "seed": system.seed, "distance": 0.0,
                "shower": Vector((1.0, 0.0, 0.0)),
                "origin": _camera_basis(scene)[0],
                "material": None, "gn": True, "trail": None, "heads": None,
                "head_ranges": [], "fragments": None, "fragment_ranges": [],
                "uid": system.uid, "system": system,
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
    # The legacy world effects follow the backend: the shader fireworks and
    # the shader shooting stars only live in the Legacy World backend.
    if settings.fireworks != (backend == "LEGACY"):
        settings.fireworks = (backend == "LEGACY")
    if backend != "LEGACY" and settings.shooting_stars:
        settings.shooting_stars = False
    return True


def set_age(scene, age):
    """Move the FX systems in time without rebuilding the geometry.

    The Geometry Nodes systems only need the clock of their modifiers:
    the deterministic data stays untouched. The Python systems are re-evaluated
    at the new instant.
    """
    from . import fx_nodes
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return False
    updated = False
    collection = _collection(scene)
    powers = _energy_powers(scene)
    fade = _atmospheric_fade(scene)
    origin, _forward, _up, _right = _camera_basis(scene)
    for uid, runtime in list(registry.items()):
        if not runtime:
            continue
        system = runtime.get("system")
        clock = system_clock(scene, system)
        now = system_time(scene, system)
        if runtime.get("gn"):
            for obj in collection.objects:
                if not obj.get("ald_fx"):
                    continue
                if obj.get("ald_fx_system") != uid:
                    continue
                fx_nodes.set_clock(obj, clock["age_offset"],
                                   time_override=clock["override"],
                                   use_time_override=clock["use_override"])
                fx_nodes.set_look(obj, camera_position=tuple(origin),
                                  atmospheric_fade=fade)
            runtime["time"] = None
            updated = True
        else:
            try:
                _update_system(runtime, now)
                updated = True
            except Exception:
                pass
    return updated


def update(scene, time=None):
    """Re-evaluate every FX system of a scene at the time of its clock."""
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return False
    for uid, runtime in list(registry.items()):
        if not runtime:
            continue
        system = runtime.get("system")
        if time is None:
            moment = system_time(scene, system)
        else:
            moment = time
        _update_system(runtime, moment)
    return True


def systems_info(scene):
    """Return the FX systems present in a scene as (kind, object count)."""
    registry = SYSTEMS.get(_scene_id(scene), {})
    settings = getattr(scene, "ald", None)
    info = []
    systems = list(settings.fx_systems) if settings else []
    for system in systems:
        runtime = registry.get(system.uid)
        if runtime is None:
            continue
        count = 0
        for uid, entry in registry.items():
            if entry is runtime:
                count = _object_count(scene, system.uid)
        info.append((system.kind.lower(), count))
    return info


def _object_count(scene, uid):
    """The number of generated objects of a system."""
    owner = _scene_id(scene)
    count = 0
    for coll in bpy.data.collections:
        if coll.get(OWNER_KEY) != owner:
            continue
        for obj in coll.objects:
            if not obj.get("ald_fx"):
                continue
            if obj.get("ald_fx_system") != uid:
                continue
            if obj.get("ald_fx_role") == "launcher":
                continue
            count += 1
    return count


def clear(scene, keep_system=False, kind=None):
    """Remove the FX systems owned by ``scene`` and their orphan data.

    The persistent description is removed too, unless it is explicitly kept:
    a system that stays in the file must be able to rebuild its geometry.
    """
    owner = _scene_id(scene)
    removed = 0
    settings = getattr(scene, "ald", None)
    if settings is None:
        return 0
    # The collection is walked backwards: the indexes shift when a system is
    # removed.
    for index in range(len(settings.fx_systems) - 1, -1, -1):
        system = settings.fx_systems[index]
        if kind is not None and system.kind.lower() != kind:
            continue
        for obj in list(_collection(scene).objects):
            if not obj.get("ald_fx"):
                continue
            if obj.get("ald_fx_system") != system.uid:
                continue
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
        registry = SYSTEMS.get(owner)
        if registry is not None:
            registry.pop(system.uid, None)
        if not keep_system:
            settings.fx_systems.remove(index)
    _cleanup_orphans()
    return removed


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

@persistent
def _on_frame_change(scene, *_args):
    from . import snapshot
    if snapshot.is_inactive(scene):
        return
    registry = SYSTEMS.get(_scene_id(scene))
    if not registry:
        return
    for uid, runtime in list(registry.items()):
        if not runtime:
            continue
        if runtime.get("gn"):
            # Every particle is evaluated by the node group.
            continue
        time = system_time(scene, runtime.get("system"))
        if runtime.get("time") is not None \
                and abs(time - runtime["time"]) < 1e-6:
            continue
        try:
            _update_system(runtime, time)
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
