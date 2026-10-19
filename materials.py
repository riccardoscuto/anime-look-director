"""Palette-driven shadow tint inserted into scene materials.

The tint is a shared node group placed before the Principled Base Color.
It is reversible: removing the node restores the previous link or color.
"""

import bpy

GROUP_NAME = "ALD | Shadow Tint"
NODE_TAG = "ald_shadow_tint"
COLOR_KEY = "ald_st_color"
EM_COLOR_KEY = "ald_em_color"
EM_STRENGTH_KEY = "ald_em_strength"

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


def _ensure_socket(ng, name, in_out, socket_type, default=None,
                   min_value=None, max_value=None):
    for item in ng.interface.items_tree:
        if getattr(item, "in_out", "") == in_out and item.name == name:
            return item
    sock = ng.interface.new_socket(name=name, in_out=in_out,
                                   socket_type=socket_type)
    if default is not None:
        try:
            sock.default_value = default
        except Exception:
            pass
    if min_value is not None:
        try:
            sock.min_value = min_value
        except Exception:
            pass
    if max_value is not None:
        try:
            sock.max_value = max_value
        except Exception:
            pass
    return sock


def _smooth(node):
    try:
        items = [item.identifier for item in
                 node.bl_rna.properties["interpolation_type"].enum_items]
        if "SMOOTHSTEP" in items:
            node.interpolation_type = "SMOOTHSTEP"
    except Exception:
        pass


def _build_group(ng):
    ng.nodes.clear()
    _ensure_socket(ng, "Color", "INPUT", "NodeSocketColor")
    _ensure_socket(ng, "Tint", "INPUT", "NodeSocketColor")
    _ensure_socket(ng, "Strength", "INPUT", "NodeSocketFloat", 0.35, 0.0, 1.0)
    _ensure_socket(ng, "Distance", "INPUT", "NodeSocketFloat", 0.6, 0.0, 100.0)
    _ensure_socket(ng, "Sun Direction", "INPUT", "NodeSocketVector",
                   (0.0, 0.0, 1.0))
    _ensure_socket(ng, "Sun Color", "INPUT", "NodeSocketColor",
                   (1.0, 1.0, 1.0, 1.0))
    _ensure_socket(ng, "Toon Strength", "INPUT", "NodeSocketFloat",
                   0.0, 0.0, 1.0)
    _ensure_socket(ng, "Terminator Sharpness", "INPUT", "NodeSocketFloat",
                   0.08, 0.005, 0.5)
    _ensure_socket(ng, "Rim Strength", "INPUT", "NodeSocketFloat",
                   0.0, 0.0, 1.0)
    _ensure_socket(ng, "Rim Width", "INPUT", "NodeSocketFloat",
                   0.5, 0.0, 1.0)
    _ensure_socket(ng, "Color", "OUTPUT", "NodeSocketColor")
    _ensure_socket(ng, "Emission", "OUTPUT", "NodeSocketColor")

    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-820, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (760, 0)

    ao = nodes.new("ShaderNodeAmbientOcclusion")
    ao.location = (-620, -260)
    ao.samples = 16
    links.new(group_in.outputs["Distance"], ao.inputs["Distance"])

    # AO is 1 when open and 0 when fully occluded: invert and scale.
    invert = nodes.new("ShaderNodeMath")
    invert.location = (-400, -260)
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    links.new(ao.outputs["AO"], invert.inputs[1])

    scale = nodes.new("ShaderNodeMath")
    scale.location = (-200, -260)
    scale.operation = "MULTIPLY"
    scale.use_clamp = True
    links.new(invert.outputs[0], scale.inputs[0])
    links.new(group_in.outputs["Strength"], scale.inputs[1])

    # Directional terminator: N dot L against the palette sun.
    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.location = (-820, 380)
    dot = nodes.new("ShaderNodeVectorMath")
    dot.location = (-620, 380)
    dot.operation = "DOT_PRODUCT"
    links.new(geometry.outputs["Normal"], dot.inputs[0])
    links.new(group_in.outputs["Sun Direction"], dot.inputs[1])

    negative = nodes.new("ShaderNodeMath")
    negative.location = (-620, 560)
    negative.operation = "MULTIPLY"
    negative.inputs[1].default_value = -1.0
    links.new(group_in.outputs["Terminator Sharpness"], negative.inputs[0])

    terminator = nodes.new("ShaderNodeMapRange")
    terminator.location = (-420, 460)
    terminator.clamp = True
    _smooth(terminator)
    links.new(dot.outputs["Value"], terminator.inputs["Value"])
    links.new(negative.outputs[0], terminator.inputs["From Min"])
    links.new(group_in.outputs["Terminator Sharpness"],
              terminator.inputs["From Max"])
    terminator.inputs["To Min"].default_value = 1.0
    terminator.inputs["To Max"].default_value = 0.0

    toon = nodes.new("ShaderNodeMath")
    toon.location = (-200, 460)
    toon.operation = "MULTIPLY"
    toon.use_clamp = True
    links.new(terminator.outputs["Result"], toon.inputs[0])
    links.new(group_in.outputs["Toon Strength"], toon.inputs[1])

    combined = nodes.new("ShaderNodeMath")
    combined.location = (0, -180)
    combined.operation = "MAXIMUM"
    combined.use_clamp = True
    links.new(scale.outputs[0], combined.inputs[0])
    links.new(toon.outputs[0], combined.inputs[1])

    mix = nodes.new("ShaderNodeMix")
    mix.location = (220, 0)
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    a_sock, b_sock, result_sock = _rgba_sockets(mix)
    if a_sock is None or b_sock is None or result_sock is None:
        raise RuntimeError("Could not resolve ShaderNodeMix RGBA sockets")
    links.new(group_in.outputs["Color"], a_sock)
    links.new(group_in.outputs["Tint"], b_sock)
    links.new(combined.outputs[0], mix.inputs["Factor"])

    # Fresnel rim on the sun-facing side, tinted by the sun color.
    layer = nodes.new("ShaderNodeLayerWeight")
    layer.location = (-200, 720)
    layer.inputs["Blend"].default_value = 0.5

    rim_edge = nodes.new("ShaderNodeMath")
    rim_edge.location = (-200, 880)
    rim_edge.operation = "SUBTRACT"
    rim_edge.inputs[0].default_value = 1.0
    links.new(group_in.outputs["Rim Width"], rim_edge.inputs[1])

    rim_curve = nodes.new("ShaderNodeMapRange")
    rim_curve.location = (0, 820)
    rim_curve.clamp = True
    _smooth(rim_curve)
    links.new(layer.outputs["Facing"], rim_curve.inputs["Value"])
    links.new(rim_edge.outputs[0], rim_curve.inputs["From Min"])
    rim_curve.inputs["From Max"].default_value = 1.0
    rim_curve.inputs["To Min"].default_value = 0.0
    rim_curve.inputs["To Max"].default_value = 1.0

    facing = nodes.new("ShaderNodeMath")
    facing.location = (200, 720)
    facing.operation = "MAXIMUM"
    facing.use_clamp = True
    links.new(dot.outputs["Value"], facing.inputs[0])
    facing.inputs[1].default_value = 0.0

    rim_mask = nodes.new("ShaderNodeMath")
    rim_mask.location = (400, 720)
    rim_mask.operation = "MULTIPLY"
    links.new(rim_curve.outputs["Result"], rim_mask.inputs[0])
    links.new(facing.outputs[0], rim_mask.inputs[1])

    rim_scale = nodes.new("ShaderNodeMath")
    rim_scale.location = (600, 720)
    rim_scale.operation = "MULTIPLY"
    rim_scale.use_clamp = True
    links.new(rim_mask.outputs[0], rim_scale.inputs[0])
    links.new(group_in.outputs["Rim Strength"], rim_scale.inputs[1])

    rim_color = nodes.new("ShaderNodeVectorMath")
    rim_color.location = (800, 720)
    rim_color.operation = "SCALE"
    links.new(group_in.outputs["Sun Color"], rim_color.inputs["Vector"])
    links.new(rim_scale.outputs[0], rim_color.inputs["Scale"])

    rim_add = nodes.new("ShaderNodeMix")
    rim_add.location = (720, 0)
    rim_add.data_type = "RGBA"
    rim_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(rim_add)
    links.new(mix.outputs["Result"], a_sock)
    links.new(rim_color.outputs["Vector"], b_sock)
    rim_add.inputs["Factor"].default_value = 1.0
    links.new(result_sock, group_out.inputs["Color"])

    shadow_amount = nodes.new("ShaderNodeMath")
    shadow_amount.location = (520, 880)
    shadow_amount.operation = "MULTIPLY"
    shadow_amount.use_clamp = True
    shadow_amount.inputs[1].default_value = 0.12
    links.new(combined.outputs[0], shadow_amount.inputs[0])

    shadow_emit = nodes.new("ShaderNodeVectorMath")
    shadow_emit.location = (720, 880)
    shadow_emit.operation = "SCALE"
    links.new(group_in.outputs["Tint"], shadow_emit.inputs["Vector"])
    links.new(shadow_amount.outputs[0], shadow_emit.inputs["Scale"])

    emit_add = nodes.new("ShaderNodeMix")
    emit_add.location = (920, 720)
    emit_add.data_type = "RGBA"
    emit_add.blend_type = "ADD"
    a_sock, b_sock, result_sock = _rgba_sockets(emit_add)
    links.new(rim_color.outputs["Vector"], a_sock)
    links.new(shadow_emit.outputs["Vector"], b_sock)
    emit_add.inputs["Factor"].default_value = 1.0
    links.new(result_sock, group_out.inputs["Emission"])


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
    outputs = {item.name for item in ng.interface.items_tree
               if getattr(item, "in_out", "") == "OUTPUT"}
    required = {"Color", "Tint", "Strength", "Distance",
                "Sun Direction", "Sun Color", "Toon Strength",
                "Terminator Sharpness", "Rim Strength", "Rim Width"}
    if not required <= names or not {"Color", "Emission"} <= outputs:
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


def _look(scene, settings):
    from . import palette

    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    direction = palette.sun_toward(scene)
    has_sun = direction is not None and sun is not None
    sun_color = (tuple(sun.data.color)
                 if sun is not None and sun.data is not None
                 else (1.0, 1.0, 1.0))
    toon_on = bool(settings is not None and settings.toon_shading and has_sun)
    rim_on = bool(settings is not None and settings.rim_light and has_sun)
    return {
        "sun_dir": direction if direction is not None else (0.0, 0.0, 1.0),
        "sun_color": sun_color,
        "toon_strength": (settings.toon_strength if toon_on else 0.0),
        "sharpness": settings.toon_sharpness if settings is not None else 0.08,
        "rim_strength": (settings.rim_strength if rim_on else 0.0),
        "rim_width": settings.rim_width if settings is not None else 0.5,
        "emission": (settings.rim_emission
                     if settings is not None and has_sun
                     and (rim_on or toon_on) else 0.0),
    }


def _set_look(node, mat, look):
    if "Sun Direction" not in node.inputs:
        return
    node.inputs["Sun Direction"].default_value = look["sun_dir"]
    node.inputs["Sun Color"].default_value = (*look["sun_color"], 1.0)
    node.inputs["Toon Strength"].default_value = look["toon_strength"]
    node.inputs["Terminator Sharpness"].default_value = look["sharpness"]
    rim_strength = look["rim_strength"]
    rim_width = look["rim_width"]
    if mat.name == "ALD | Hair":
        rim_strength = min(1.0, rim_strength + 0.3)
        rim_width = min(rim_width, 0.35)
    node.inputs["Rim Strength"].default_value = rim_strength
    node.inputs["Rim Width"].default_value = rim_width


def _wire_emission(mat, node, look):
    """Route the group Emission output into Principled, reversibly."""
    bsdf = _principled(mat)
    if bsdf is None:
        return
    color = bsdf.inputs.get("Emission Color")
    strength = bsdf.inputs.get("Emission Strength")
    if color is None or strength is None:
        return
    output = node.outputs.get("Emission")
    if output is None:
        return

    linked = color.is_linked and color.links[0].from_node == node
    if color.is_linked and not linked:
        return

    target = float(look.get("emission", 0.0))
    if target <= 0.0:
        if linked:
            for link in list(color.links):
                mat.node_tree.links.remove(link)
            if EM_COLOR_KEY in mat:
                color.default_value = mat[EM_COLOR_KEY]
            if EM_STRENGTH_KEY in mat:
                strength.default_value = mat[EM_STRENGTH_KEY]
            for key in (EM_COLOR_KEY, EM_STRENGTH_KEY):
                if key in mat:
                    del mat[key]
        return

    if not linked:
        if strength.default_value > 0.05:
            return
        mat[EM_COLOR_KEY] = [float(v) for v in color.default_value]
        mat[EM_STRENGTH_KEY] = float(strength.default_value)
        mat.node_tree.links.new(output, color)
    strength.default_value = target


def sync_material(mat, tint, strength, distance, look=None):
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
    if look is not None:
        _set_look(node, mat, look)
        _wire_emission(mat, node, look)
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

    bsdf = _principled(mat)
    if bsdf is not None:
        emission = bsdf.inputs.get("Emission Color")
        strength = bsdf.inputs.get("Emission Strength")
        if (emission is not None and emission.is_linked
                and emission.links[0].from_node == node):
            for link in list(emission.links):
                nt.links.remove(link)
            if EM_COLOR_KEY in mat:
                emission.default_value = mat[EM_COLOR_KEY]
            if EM_STRENGTH_KEY in mat and strength is not None:
                strength.default_value = mat[EM_STRENGTH_KEY]
        for key in (EM_COLOR_KEY, EM_STRENGTH_KEY):
            if key in mat:
                del mat[key]

    nt.nodes.remove(node)
    if COLOR_KEY in mat:
        del mat[COLOR_KEY]
    return True


def sync_scene(scene, tint, strength, distance):
    settings = getattr(scene, "ald", None)
    look = _look(scene, settings)
    count = 0
    for mat in scene_materials(scene):
        if sync_material(mat, tint, strength, distance, look):
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
        sync_material(mat, palette.shadow_tint_for(scene),
                      settings.shadow_tint_strength,
                      settings.shadow_tint_distance,
                      _look(scene, settings))
    return len(objects), mat


def update_sun(scene):
    """Refresh sun direction/color in every tinted material, per frame."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        return
    look = _look(scene, settings)
    for mat in scene_materials(scene):
        node = _tint_node(mat)
        if node is not None:
            _set_look(node, mat, look)
            _wire_emission(mat, node, look)


def _on_frame_change(scene, *_args):
    try:
        update_sun(scene)
    except Exception:
        pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)
