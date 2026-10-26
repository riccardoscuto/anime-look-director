"""Atmospheric smoke: a volumetric layer owned by the add-on.

The plan forbids a new World generator that hides particle defects: the smoke
is a real volumetric object in its own collection, rendered by the normal
environment path (the B layer of the FX compositor), never by the additive FX
path. It is created, synced and removed as a single unit, so Remove ALD from
Scene restores the scene without it.
"""

import bmesh
import bpy

COLLECTION_NAME = "ALD | Smoke"
OBJECT_NAME = "ALD | Smoke Volume"
MATERIAL_NAME = "ALD | Smoke Volume"
TAG = "ald_smoke"


def _collection(scene):
    owner = None
    from . import fx
    owner = fx._scene_id(scene)
    for coll in bpy.data.collections:
        if coll.get(TAG) and coll.get(fx.OWNER_KEY) == owner:
            return coll
    return None


def exists(scene):
    return _collection(scene) is not None


def _volume_material():
    material = bpy.data.materials.get(MATERIAL_NAME)
    if material is not None:
        return material
    material = bpy.data.materials.new(MATERIAL_NAME)
    material[TAG] = True
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    volume = tree.nodes.new("ShaderNodeVolumePrincipled")
    volume.location = (0, 0)
    tree.links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return material


def create(scene, density=0.25, height=8.0, color=(0.62, 0.66, 0.75)):
    """Create (or replace) the single smoke volume of the scene."""
    from . import fx, snapshot

    snapshot.ensure(scene)
    remove(scene)
    owner = fx._scene_id(scene)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    collection[TAG] = True
    collection[fx.OWNER_KEY] = owner
    scene.collection.children.link(collection)

    mesh = bpy.data.meshes.new(OBJECT_NAME)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    mesh[TAG] = True
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    obj[TAG] = True
    obj.location = (0.0, 0.0, height)
    obj.scale = (300.0, 300.0, height * 2.0)
    collection.objects.link(obj)

    material = _volume_material()
    volume = next((node for node in material.node_tree.nodes
                   if node.bl_idname == "ShaderNodeVolumePrincipled"), None)
    if volume is not None:
        volume.inputs["Density"].default_value = float(density)
        volume.inputs["Color"].default_value = (*color, 1.0)
        if "Anisotropy" in volume.inputs:
            volume.inputs["Anisotropy"].default_value = 0.3
    obj.data.materials.append(material)

    scene.ald.smoke_created = True
    return obj


def sync(scene):
    """Apply the scene settings to the existing volume without recreating it."""
    collection = _collection(scene)
    if collection is None:
        return False
    settings = getattr(scene, "ald", None)
    if settings is None:
        return False
    height = max(0.1, float(settings.smoke_height))
    obj = next((item for item in collection.objects if item.get(TAG)), None)
    if obj is None:
        return False
    obj.location = (obj.location.x, obj.location.y, height)
    obj.scale = (300.0, 300.0, height * 2.0)
    material = obj.active_material
    if material is not None:
        volume = next((node for node in material.node_tree.nodes
                       if node.bl_idname == "ShaderNodeVolumePrincipled"), None)
        if volume is not None:
            volume.inputs["Density"].default_value = float(settings.smoke_density)
            volume.inputs["Color"].default_value = (*settings.smoke_color, 1.0)
    return True


def remove(scene):
    """Remove the smoke volume and its orphans."""
    collection = _collection(scene)
    if collection is not None:
        for obj in list(collection.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
        bpy.data.collections.remove(collection)
    material = bpy.data.materials.get(MATERIAL_NAME)
    if material is not None and material.users == 0:
        bpy.data.materials.remove(material)
    settings = getattr(scene, "ald", None)
    if settings is not None:
        try:
            settings.smoke_created = False
        except (AttributeError, TypeError):
            pass
    return True
