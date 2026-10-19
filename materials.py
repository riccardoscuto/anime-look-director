"""Palette-driven shadow tint inserted into scene materials.

The tint is a shared node group placed before the Principled Base Color.
It is reversible: removing the node restores the previous link or color.
"""

import bpy

GROUP_NAME = "ALD | Shadow Tint"
NODE_TAG = "ald_shadow_tint"
COLOR_KEY = "ald_st_color"

PRESET_DATA = {
    "SKIN": {
        "name": "ALD | Skin",
        "color": (0.86, 0.68, 0.58),
        "roughness": 0.55,
        "metallic": 0.0,
    },
    "HAIR": {
        "name": "ALD | Hair",
        "color": (0.09, 0.06, 0.05),
        "roughness": 0.35,
        "metallic": 0.0,
    },
    "FABRIC": {
        "name": "ALD | Fabric",
        "color": (0.32, 0.42, 0.60),
        "roughness": 0.9,
        "metallic": 0.0,
    },
    "METAL": {
        "name": "ALD | Metal",
        "color": (0.72, 0.73, 0.76),
        "roughness": 0.25,
        "metallic": 1.0,
    },
    "EMISSION": {
        "name": "ALD | Emission",
        "color": (1.0, 0.35, 0.12),
        "roughness": 0.4,
        "metallic": 0.0,
        "emission": (1.0, 0.35, 0.12),
        "emission_strength": 3.0,
    },
}


def _rgba_sockets(mix):
    a = b = result = None
    for sock in mix.inputs:
        if sock.name == "A" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            a = sock
        elif sock.name == "B" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            b = sock
    for sock in mix.outputs:
        if sock.name == "Result" and sock.type == "RGBA" and getattr(sock, "enabled", True):
            result = sock
    return a, b, result


def _build_group(ng):
    ng.nodes.clear()
    if hasattr(ng.interface, "clear"):
        ng.interface.clear()

    ng.interface.new_socket(name="Color", in_out="INPUT",
                            socket_type="NodeSocketColor")
    ng.interface.new_socket(name="Tint", in_out="INPUT",
                            socket_type="NodeSocketColor")
    strength = ng.interface.new_socket(name="Strength", in_out="INPUT",
                                       socket_type="NodeSocketFloat")
    strength.min_value = 0.0
    strength.max_value = 1.0
    strength.default_value = 0.35
    distance = ng.interface.new_socket(name="Distance", in_out="INPUT",
                                       socket_type="NodeSocketFloat")
    distance.min_value = 0.0
    distance.max_value = 100.0
    distance.default_value = 0.6
    ng.interface.new_socket(name="Color", in_out="OUTPUT",
                            socket_type="NodeSocketColor")

    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-760, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (520, 0)

    ao = nodes.new("ShaderNodeAmbientOcclusion")
    ao.location = (-520, -220)
    ao.samples = 16
    links.new(group_in.outputs["Distance"], ao.inputs["Distance"])

    # AO is 1 when open and 0 when fully occluded: invert and scale.
    invert = nodes.new("ShaderNodeMath")
    invert.location = (-300, -220)
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    links.new(ao.outputs["AO"], invert.inputs[1])

    scale = nodes.new("ShaderNodeMath")
    scale.location = (-100, -220)
    scale.operation = "MULTIPLY"
    scale.use_clamp = True
    links.new(invert.outputs[0], scale.inputs[0])
    links.new(group_in.outputs["Strength"], scale.inputs[1])

    mix = nodes.new("ShaderNodeMix")
    mix.location = (180, 0)
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    a_sock, b_sock, result_sock = _rgba_sockets(mix)
    if a_sock is None or b_sock is None or result_sock is None:
        raise RuntimeError("Could not resolve ShaderNodeMix RGBA sockets")
    links.new(group_in.outputs["Color"], a_sock)
    links.new(group_in.outputs["Tint"], b_sock)
    links.new(scale.outputs[0], mix.inputs["Factor"])
    links.new(result_sock, group_out.inputs["Color"])


def _group():
    """Return the shared shadow-tint group, building it on first use."""
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if ng is not None and ng.bl_idname != "ShaderNodeTree":
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None:
        ng = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
        _build_group(ng)
        return ng
    names = {item.name for item in ng.interface.items_tree
             if getattr(item, "in_out", "") == "INPUT"}
    if not {"Color", "Tint", "Strength", "Distance"} <= names:
        _build_group(ng)
    return ng


def _principled(mat):
    nt = mat.node_tree
    if nt is None:
        return None
    output = next((n for n in nt.nodes
                   if n.bl_idname == "ShaderNodeOutputMaterial"), None)
    if output is not None and output.inputs["Surface"].is_linked:
        source = output.inputs["Surface"].links[0].from_node
        if source.bl_idname == "ShaderNodeBsdfPrincipled":
            return source
    return next((n for n in nt.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)


def _tint_node(mat):
    if mat.node_tree is None:
        return None
    return next((n for n in mat.node_tree.nodes if n.get(NODE_TAG)), None)


def scene_materials(scene):
    """Unique materials assigned to objects in the scene."""
    seen = set()
    result = []
    for obj in scene.objects:
        data = getattr(obj, "data", None)
        materials = getattr(data, "materials", None) if data is not None else None
        if not materials:
            continue
        for mat in materials:
            if mat is None or mat.name_full in seen:
                continue
            seen.add(mat.name_full)
            result.append(mat)
    return result


def sync_material(mat, tint, strength, distance):
    """Insert or refresh the tint node in a material. Returns True if used."""
    if mat.library is not None or mat.node_tree is None:
        return False
    bsdf = _principled(mat)
    if bsdf is None:
        return False

    nt = mat.node_tree
    base = bsdf.inputs["Base Color"]
    node = _tint_node(mat)

    if node is None:
        node = nt.nodes.new("ShaderNodeGroup")
        node.node_tree = _group()
        node.name = "ALD | Shadow Tint"
        node[NODE_TAG] = True
        node.location = (bsdf.location.x - 260, bsdf.location.y + 180)
        if base.is_linked:
            source = base.links[0].from_socket
            nt.links.remove(base.links[0])
            nt.links.new(source, node.inputs["Color"])
        else:
            mat[COLOR_KEY] = [float(v) for v in base.default_value]
            node.inputs["Color"].default_value = base.default_value
        nt.links.new(node.outputs["Color"], base)
    else:
        node.node_tree = _group()
        if not base.is_linked:
            if COLOR_KEY not in mat and not node.inputs["Color"].is_linked:
                mat[COLOR_KEY] = [float(v) for v in base.default_value]
                node.inputs["Color"].default_value = base.default_value
            nt.links.new(node.outputs["Color"], base)

    node.inputs["Tint"].default_value = (*tint, 1.0)
    node.inputs["Strength"].default_value = strength
    node.inputs["Distance"].default_value = distance
    return True


def remove_material(mat):
    """Remove the tint node and restore the original Base Color. Returns bool."""
    node = _tint_node(mat)
    if node is None or mat.node_tree is None:
        return False
    nt = mat.node_tree
    target = None
    for link in node.outputs["Color"].links:
        if (link.to_socket.name == "Base Color"
                and link.to_node.bl_idname == "ShaderNodeBsdfPrincipled"):
            target = link.to_socket
            break

    if target is not None:
        for link in list(target.links):
            nt.links.remove(link)
        if node.inputs["Color"].is_linked:
            nt.links.new(node.inputs["Color"].links[0].from_socket, target)
        elif COLOR_KEY in mat:
            target.default_value = mat[COLOR_KEY]
        else:
            target.default_value = node.inputs["Color"].default_value

    nt.nodes.remove(node)
    if COLOR_KEY in mat:
        del mat[COLOR_KEY]
    return True


def sync_scene(scene, tint, strength, distance):
    count = 0
    for mat in scene_materials(scene):
        if sync_material(mat, tint, strength, distance):
            count += 1
    scene["ald_shadow_materials"] = count
    return count


def clear_scene(scene):
    count = 0
    for mat in scene_materials(scene):
        if remove_material(mat):
            count += 1
    scene["ald_shadow_materials"] = 0
    return count


def count_scene(scene):
    return sum(1 for mat in scene_materials(scene) if _tint_node(mat) is not None)


def _preset_material(key):
    info = PRESET_DATA[key]
    mat = bpy.data.materials.get(info["name"])
    if mat is None:
        mat = bpy.data.materials.new(info["name"])
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        nt.nodes.clear()
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*info["color"], 1.0)
    bsdf.inputs["Roughness"].default_value = info["roughness"]
    bsdf.inputs["Metallic"].default_value = info["metallic"]
    emission_color = bsdf.inputs.get("Emission Color")
    emission_strength = bsdf.inputs.get("Emission Strength")
    if emission_color is not None and emission_strength is not None:
        if "emission" in info:
            emission_color.default_value = (*info["emission"], 1.0)
            emission_strength.default_value = info.get("emission_strength", 1.0)
        else:
            emission_strength.default_value = 0.0
    node = _tint_node(mat)
    if node is not None and not node.inputs["Color"].is_linked:
        node.inputs["Color"].default_value = (*info["color"], 1.0)
        mat[COLOR_KEY] = [float(v) for v in (*info["color"], 1.0)]
    mat.use_fake_user = True
    return mat


def apply_preset_to_selected(scene, key):
    """Assign a material preset to selected objects. Returns (count, material)."""
    info = PRESET_DATA.get(key)
    if info is None:
        return 0, None

    objects = []
    for obj in bpy.context.selected_objects:
        data = getattr(obj, "data", None)
        if (obj.library is not None or data is None
                or getattr(data, "library", None) is not None
                or not hasattr(data, "materials")
                or not hasattr(obj, "active_material_index")):
            continue
        objects.append(obj)
    if not objects:
        return 0, None

    mat = _preset_material(key)
    for obj in objects:
        slots = obj.data.materials
        if not any(slot == mat for slot in slots):
            slots.append(mat)
        obj.active_material_index = next(
            index for index, slot in enumerate(slots) if slot == mat)

    settings = getattr(scene, "ald", None)
    if settings is not None and settings.shadow_tint:
        from . import palette
        sync_material(mat, palette.shadow_tint(settings.palette),
                      settings.shadow_tint_strength,
                      settings.shadow_tint_distance)
    return len(objects), mat
