"""Ownership repair for duplicated scenes in the World Sky Edition.

A plain ``Scene.copy()`` shares the world and the ordinary objects. The repair
gives the copy a new identity and its own world, so applying a palette to the
copy cannot rewrite the original sky. Materials and lights shared with another
scene remain untouched (see ``materials.material_is_shared`` and
``palette.apply_sun_angles``).
"""

import uuid

import bpy

from . import identity


def same_identity(scene):
    return identity.same_identity(scene)


def has_shared(scene):
    return identity.same_identity(scene)


def world_is_shared(scene):
    world = scene.world
    return world is not None and any(
        other != scene and other.world is world for other in bpy.data.scenes)


def repair(scene):
    """Give the copy a new identity and its own world."""
    if not identity.same_identity(scene):
        return 0
    scene[identity.ID_KEY] = uuid.uuid4().hex
    if world_is_shared(scene):
        scene.world = scene.world.copy()
    return 1
