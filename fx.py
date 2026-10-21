"""Deterministic 3D FX: fireworks and shooting stars with real physics.

Design (see Anime_Look_Director_Guida_Tecnica_v2.0.1.md):

* every particle is evaluated analytically from its own data, so the result
  never depends on the frame history (frame jumps are safe);
* time is expressed in seconds, not frames;
* motion uses a linear drag model with a stable zero-drag limit;
* the primary stars, their trails, the secondary sparks and the central flash
  are four distinct subsystems;
* FX data is owned per scene, so clearing one scene never touches another.

The system is evaluated at an explicit instant (``time`` in seconds). Use
``ald.fx_update`` to rebuild the system at the current frame.
"""

import hashlib
import math
import random

import bmesh
import bpy
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

# Family configuration: primary stars, speed, drag, lifetime, trail and sparks.
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
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
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
# deterministic randomness
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


# ---------------------------------------------------------------------------
# analytic motion
# ---------------------------------------------------------------------------

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

def _multicurve(scene, name, splines, materials, width):
    """One curve object with several splines and per-spline materials."""
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = width
    curve.bevel_resolution = 2
    curve.resolution_u = 2
    curve["ald_fx"] = True
    for mat in materials:
        curve.materials.append(mat)
    for points, material_index in splines:
        if len(points) < 2:
            continue
        spline = curve.splines.new("POLY")
        spline.points.add(len(points) - 1)
        spline.material_index = material_index
        for i, point in enumerate(points):
            spline.points[i].co = (point.x, point.y, point.z, 1.0)
            # Oldest sample first: the head is the brightest and widest.
            t = i / (len(points) - 1)
            spline.points[i].radius = 0.25 + 0.9 * (t ** 1.4)
    obj = bpy.data.objects.new(name, curve)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _points_mesh(scene, name, points, radii, material):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for point, radius in zip(points, radii):
        res = bmesh.ops.create_icosphere(bm, subdivisions=1,
                                         radius=max(radius, 0.004))
        for vertex in res["verts"]:
            vertex.co += point
    bm.to_mesh(mesh)
    bm.free()
    mesh["ald_fx"] = True
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _camera_basis(scene):
    camera = scene.camera
    if camera is None:
        return (Vector((0.0, -8.0, 1.5)), Vector((0.0, 1.0, 0.0)),
                Vector((0.0, 0.0, 1.0)), Vector((1.0, 0.0, 0.0)))
    matrix = camera.matrix_world
    rotation = matrix.to_quaternion()
    return (matrix.translation,
            (rotation @ Vector((0.0, 0.0, -1.0))).normalized(),
            (rotation @ Vector((0.0, 1.0, 0.0))).normalized(),
            (rotation @ Vector((1.0, 0.0, 0.0))).normalized())


def _burst_center(origin, forward, up, right, index, total, distance):
    spread_x = -0.24 + 0.48 * (index + 0.5) / max(total, 1)
    spread_y = 0.16 + 0.07 * math.sin(index * 1.7)
    return (origin + forward * distance + right * distance * spread_x
            + up * distance * spread_y)


# ---------------------------------------------------------------------------
# fireworks
# ---------------------------------------------------------------------------

def create_fireworks(scene, count=3, seed=7, distance=110.0, time=0.0,
                     fps=24.0, family="CHRYSANTHEMUM"):
    """Evaluate a deterministic multi-burst firework system at ``time``."""
    family = family if family in FAMILY_CONFIG else "CHRYSANTHEMUM"
    config = FAMILY_CONFIG[family]
    origin, forward, up, right = _camera_basis(scene)
    size_scale = max(0.6, min(2.0, distance / 60.0))
    for index in range(max(1, count)):
        center = _burst_center(origin, forward, up, right, index, count,
                                distance * (0.85 + 0.25 *
                                           _hash_unit(seed, index, 0, 1)))
        birth = index * 0.32
        age = time - birth
        if age < 0.0:
            continue
        family_colors = PALETTES[index % len(PALETTES)]
        materials = [
            _material("ALD FX %s %d A" % (family, index), family_colors[0],
                      6.0),
            _material("ALD FX %s %d B" % (family, index), family_colors[1],
                      6.0),
            _material("ALD FX %s %d C" % (family, index), family_colors[2],
                      6.0),
        ]
        trail_splines = []
        head_points = [[], [], []]
        head_radii = [[], [], []]
        spark_points = [[], [], []]
        spark_radii = [[], [], []]
        spoke_count = config["spokes"]
        for spoke in range(spoke_count):
            life = _hash_range(seed, index, spoke, 2, config["life"] * 0.6,
                               config["life"])
            if age > life:
                continue
            direction = _fibonacci_direction(spoke, spoke_count, 0.35, seed,
                                             index)
            speed = _hash_range(seed, index, spoke, 3, config["speed"] * 0.75,
                                config["speed"] * 1.15)
            v0 = direction * speed
            p0 = center
            color_index = spoke % 3
            # Trail: samples of the same analytic trajectory in the past.
            trail_time = min(age, config["trail"])
            if trail_time > 0.02:
                samples = 10
                points = []
                for step in range(samples):
                    tau = trail_time * (1.0 - step / (samples - 1.0))
                    points.append(_position(p0, v0, config["drag"], age - tau))
                trail_splines.append((points, color_index))
            # Head.
            head_points[color_index].append(_position(p0, v0, config["drag"],
                                                      age))
            head_radii[color_index].append(
                0.030 * size_scale * (0.35 + 0.65 * (1.0 - age / max(life, 1e-3))))
            # Secondary sparks emitted by the star.
            for child in range(config["sparks"]):
                emit = _hash_range(seed, index, spoke, 4, 0.05, life * 0.55)
                child_age = age - emit
                if child_age <= 0.0:
                    continue
                child_life = _hash_range(seed, index, spoke * 8 + child, 5,
                                         0.45, 1.5)
                if child_age > child_life:
                    continue
                parent_pos = _position(p0, v0, config["drag"], age - emit)
                parent_vel = _velocity(v0, config["drag"], age - emit)
                perturb = Vector((
                    _hash_range(seed, index, spoke * 8 + child, 6, -1.6, 1.6),
                    _hash_range(seed, index, spoke * 8 + child, 7, -1.6, 1.6),
                    _hash_range(seed, index, spoke * 8 + child, 8, -1.6, 1.6),
                )) * 1.2
                child_v0 = parent_vel * 0.35 + perturb
                spark_points[color_index].append(
                    _position(parent_pos, child_v0, 2.4, child_age))
                spark_radii[color_index].append(
                    0.010 * size_scale * (1.0 - child_age / max(child_life, 1e-3)))
        if trail_splines:
            _multicurve(scene, "ALD FX %s %d Trails" % (family, index),
                         trail_splines, materials, 0.011 * size_scale)
        for slot in range(3):
            if head_points[slot]:
                _points_mesh(scene, "ALD FX %s %d Heads" % (family, index),
                             head_points[slot], head_radii[slot], materials[slot])
            if spark_points[slot]:
                _points_mesh(scene, "ALD FX %s %d Sparks" % (family, index),
                             spark_points[slot], spark_radii[slot],
                             materials[slot])
        # Ephemeral central flash.
        if age < config["core"]:
            energy = 1.0 - age / max(config["core"], 1e-3)
            _points_mesh(scene, "ALD FX %s %d Flash" % (family, index),
                         [center], [0.16 * size_scale * energy ** 0.5],
                         materials[1])
    return count


# ---------------------------------------------------------------------------
# shooting stars
# ---------------------------------------------------------------------------

def create_meteors(scene, count=4, seed=21, distance=140.0, time=0.0,
                   fps=24.0):
    """Meteors sharing one radiant direction, as in a real shower."""
    origin, forward, up, right = _camera_basis(scene)
    # Shared radiant: a single world direction for the whole shower.
    radiant_dir = (forward * 0.86 + up * 0.42 + right * 0.28).normalized()
    material = _material("ALD FX Meteor", (0.85, 0.94, 1.0), 9.0)
    splines = []
    heads = []
    radii = []
    for index in range(max(1, count)):
        birth = index * 0.9 + _hash_range(seed, index, 0, 1, 0.0, 0.6)
        age = time - birth
        life = _hash_range(seed, index, 0, 2, 0.55, 1.15)
        if age <= 0.0 or age > life:
            continue
        # Small angular dispersion around the shared radiant.
        spread = Vector((
            _hash_range(seed, index, 0, 3, -0.09, 0.09),
            _hash_range(seed, index, 0, 4, -0.06, 0.06),
            _hash_range(seed, index, 0, 5, -0.04, 0.04),
        ))
        direction = (radiant_dir + spread).normalized()
        start = origin + direction * distance * 0.9
        speed = _hash_range(seed, index, 0, 6, 26.0, 38.0)
        v0 = direction * speed
        points = []
        samples = 14
        trail = min(age, 0.32)
        for step in range(samples):
            tau = trail * (1.0 - step / (samples - 1.0))
            points.append(_position(start, v0, 0.08, age - tau))
        splines.append((points, 0))
        heads.append(_position(start, v0, 0.08, age))
        radii.append(0.026 * (1.0 - 0.5 * age / max(life, 1e-3)))
    if splines:
        _multicurve(scene, "ALD FX Meteor Trails", splines, [material],
                     0.007)
    if heads:
        _points_mesh(scene, "ALD FX Meteor Heads", heads, radii, material)
    return count


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def clear(scene):
    """Remove only the FX system owned by ``scene`` and its orphan data."""
    owner = _scene_id(scene)
    removed = 0
    coll = None
    for candidate in bpy.data.collections:
        if candidate.get(OWNER_KEY) == owner:
            coll = candidate
            break
    if coll is None:
        return 0
    for obj in list(coll.objects):
        if obj.get("ald_fx"):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    # Only clean ALD-owned datablocks without users.
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in list(datablocks):
            if block.get("ald_fx_material") or block.get("ald_fx"):
                if block.users == 0:
                    datablocks.remove(block)
    return removed
