"""Procedural 3D FX: physically placed fireworks and shooting-star particles.

These helpers deliberately create temporary objects in the ``ALD | FX``
collection. They are independent of the world shader so explosions have real
depth, perspective and overlap. Use ``ald.fx_clear`` to remove them.
"""

import math
import random

import bmesh
import bpy
from mathutils import Vector

FX_COLLECTION = "ALD | FX"


def _collection(scene):
    coll = bpy.data.collections.get(FX_COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(FX_COLLECTION)
        scene.collection.children.link(coll)
    return coll


def _camera_basis(scene):
    camera = scene.camera
    if camera is None:
        forward = Vector((0.0, 1.0, 0.0))
        up = Vector((0.0, 0.0, 1.0))
        right = Vector((1.0, 0.0, 0.0))
        origin = Vector((0.0, -8.0, 1.5))
    else:
        matrix = camera.matrix_world
        origin = matrix.translation
        rotation = matrix.to_quaternion()
        forward = rotation @ Vector((0.0, 0.0, -1.0))
        up = rotation @ Vector((0.0, 1.0, 0.0))
        right = rotation @ Vector((1.0, 0.0, 0.0))
    return origin, forward.normalized(), up.normalized(), right.normalized()


def _material(name, color, strength):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
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
        bsdf.inputs["Roughness"].default_value = 0.35
    return mat


def _curve_object(scene, name, points, material, width=0.012):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = width
    curve.bevel_resolution = 3
    curve.resolution_u = 2
    curve.materials.append(material)
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for index, point in enumerate(points):
        spline.points[index].co = (point.x, point.y, point.z, 1.0)
        spline.points[index].radius = 1.25 - 0.9 * (index / max(len(points) - 1, 1))
    obj = bpy.data.objects.new(name, curve)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _spark_cloud(scene, name, points, material, rng, count=18, radius=0.012):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for _ in range(count):
        base = points[rng.randrange(max(len(points) - 2, 1))]
        offset = Vector((rng.uniform(-0.10, 0.10), rng.uniform(-0.10, 0.10),
                         rng.uniform(-0.10, 0.10)))
        res = bmesh.ops.create_icosphere(
            bm, subdivisions=1, radius=radius * rng.uniform(0.45, 1.35))
        for vertex in res["verts"]:
            vertex.co += base + offset
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _sphere_object(scene, name, point, radius, material):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = point
    obj["ald_fx"] = True
    _collection(scene).objects.link(obj)
    return obj


def _random_unit(rng):
    while True:
        value = Vector((rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0),
                        rng.uniform(-1.0, 1.0)))
        if 0.08 < value.length_squared <= 1.0:
            return value.normalized()


def _burst_position(camera_origin, forward, up, right, index, total, distance):
    spread_x = (-0.22 + 0.44 * (index + 0.5) / max(total, 1))
    spread_y = 0.16 + 0.08 * math.sin(index * 1.7)
    return (camera_origin + forward * distance
            + right * distance * spread_x
            + up * distance * spread_y)


def create_fireworks(scene, count=4, seed=7, distance=30.0):
    """Create 3D chrysanthemum/peony/willow bursts in camera space."""
    rng = random.Random(seed)
    origin, forward, up, right = _camera_basis(scene)
    palette = (
        ((1.0, 0.30, 0.02), (1.0, 0.06, 0.02), (0.05, 1.0, 0.72)),
        ((1.0, 0.04, 0.42), (0.35, 0.04, 1.0), (1.0, 0.72, 0.02)),
        ((0.04, 0.72, 1.0), (0.04, 1.0, 0.35), (1.0, 0.20, 0.02)),
    )
    for index in range(max(1, count)):
        center = _burst_position(origin, forward, up, right, index, count,
                                 distance * (0.78 + 0.20 * rng.random()))
        family = palette[index % len(palette)]
        materials = [
            _material("ALD FX Firework %d A" % index, family[0], 12.0),
            _material("ALD FX Firework %d B" % index, family[1], 12.0),
            _material("ALD FX Firework %d C" % index, family[2], 12.0),
        ]
        shells = (
            (1.0, 34, materials[0], 0.010),
            (0.66, 23, materials[1], 0.008),
            (0.40, 15, materials[2], 0.007),
        )
        shell_radius = distance * (0.18 + 0.12 * rng.random())
        for shell_index, (scale, spokes, material, width) in enumerate(shells):
            spark_points = []
            for spoke in range(spokes):
                direction = _random_unit(rng)
                length = shell_radius * scale * rng.uniform(0.62, 1.12)
                gravity = Vector((0.0, 0.0, -1.0)) * length * rng.uniform(
                    0.22 if shell_index == 2 else 0.12, 0.58)
                points = []
                start_t = (0.22, 0.34, 0.46)[shell_index]
                for step in range(11):
                    t = start_t + (1.0 - start_t) * step / 10.0
                    # Parabolic weeping-willow trajectory.
                    point = center + direction * length * t + gravity * (t * t)
                    points.append(point)
                _curve_object(scene, "ALD FX Burst %d Trail" % index, points,
                              material, width)
                head = points[-1]
                _sphere_object(scene, "ALD FX Burst %d Head" % index, head,
                               0.030 if shell_index else 0.045, material)
                spark_points.extend(points[2:-1])
            _spark_cloud(scene, "ALD FX Burst %d Sparks" % index,
                         spark_points, material, rng, count=spokes * 3,
                         radius=0.016)
        core = materials[1]
        _sphere_object(scene, "ALD FX Burst %d Core" % index, center, 0.085,
                       core)
    return count


def create_meteors(scene, count=4, seed=21, distance=34.0):
    """Create parallel radiant meteors with tapered needle-like trails."""
    rng = random.Random(seed)
    origin, forward, up, right = _camera_basis(scene)
    radiant = (origin + forward * distance + up * distance * 0.55
               + right * distance * 0.18)
    material = _material("ALD FX Meteor", (0.82, 0.93, 1.0), 12.0)
    for index in range(max(1, count)):
        offset = (right * rng.uniform(-0.34, 0.34)
                  + up * rng.uniform(-0.10, 0.24))
        start = radiant + offset * distance
        travel = (forward * rng.uniform(-0.34, -0.18)
                  + right * rng.uniform(-0.22, 0.10)
                  + up * rng.uniform(-0.18, 0.02)).normalized()
        length = distance * rng.uniform(0.24, 0.42)
        points = []
        for step in range(12):
            t = step / 11.0
            points.append(start + travel * length * t
                          + Vector((0.0, 0.0, -0.10 * length * t * t)))
        _curve_object(scene, "ALD FX Meteor %d Trail" % index, points,
                      material, 0.006)
        _sphere_object(scene, "ALD FX Meteor %d Head" % index, points[-1],
                       0.024, material)
    return count


def clear(scene):
    coll = bpy.data.collections.get(FX_COLLECTION)
    if coll is None:
        return 0
    removed = 0
    for obj in list(coll.objects):
        if obj.get("ald_fx"):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed
