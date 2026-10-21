"""Geometry Nodes prototype for the 3D FX bursts.

The Python side owns the deterministic data (hash based seeds, birth times,
velocities, lifetimes, per grain jitter). Geometry Nodes evaluates the analytic
motion every frame, so the timeline no longer depends on a Python handler
rewriting mesh vertices.

The same group evaluates the star heads and the beaded trail grains:

``tau``
    age offset of the sample: ``0`` for a head, the trail offset for a grain.
``jitter``
    constant offset applied to the sample position (grain scatter).
``use_decay``
    ``1`` follows the head brightness decay, ``0`` keeps the baked size.

The motion is the same closed form used by the Python solver:

``p = p0 + v_inf * a + (v0 - v_inf) * (1 - e^(-k a)) / k``

with the ``1 / k`` guard for the drag free limit.
"""

import bpy
from mathutils import Vector

GROUP_NAME = "ALD | FX Burst GN"


def _math(nodes, links, operation, x, y, location):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    node.location = location
    if x is not None:
        links.new(x, node.inputs[0])
    if y is not None:
        links.new(y, node.inputs[1])
    return node


def _vector(nodes, links, operation, x, y, location, scale=None):
    node = nodes.new("ShaderNodeVectorMath")
    node.operation = operation
    node.location = location
    if x is not None:
        links.new(x, node.inputs[0])
    if y is not None:
        links.new(y, node.inputs[1])
    if scale is not None:
        links.new(scale, node.inputs["Scale"])
    return node


def _attribute(nodes, links, name, data_type, location):
    node = nodes.new("GeometryNodeInputNamedAttribute")
    node.data_type = data_type
    node.location = location
    node.inputs["Name"].default_value = name
    return node


#: interface sockets exposed by the group, in creation order.
SOCKET_NAMES = ("Geometry", "Gravity", "Material", "Trail", "Age Offset",
                "Min Scale")


def _socket_ids(ng):
    """Resolve the interface socket identifiers by name."""
    ids = {}
    for item in ng.interface.items_tree:
        name = getattr(item, "name", "")
        if getattr(item, "in_out", "") == "INPUT":
            ids[name.lower().replace(" ", "_")] = item.identifier
        else:
            ids["output"] = item.identifier
    defaults = {"geometry": "Socket_0", "gravity": "Socket_1",
                "material": "Socket_2", "trail": "Socket_3",
                "age_offset": "Socket_4", "min_scale": "Socket_5"}
    for key, value in defaults.items():
        ids.setdefault(key, value)
    return ids


def build_burst_group():
    """Create (or reuse) the burst node group and return it with its sockets."""
    existing = bpy.data.node_groups.get(GROUP_NAME)
    if existing is not None:
        return existing, _socket_ids(existing)
    ng = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
    nodes = ng.nodes
    links = ng.links

    geometry = ng.interface.new_socket(name="Geometry", in_out="INPUT",
                                        socket_type="NodeSocketGeometry")
    gravity = ng.interface.new_socket(name="Gravity", in_out="INPUT",
                                       socket_type="NodeSocketVector")
    material = ng.interface.new_socket(name="Material", in_out="INPUT",
                                        socket_type="NodeSocketMaterial")
    trail = ng.interface.new_socket(name="Trail", in_out="INPUT",
                                    socket_type="NodeSocketFloat")
    trail.default_value = 0.0
    age_offset = ng.interface.new_socket(name="Age Offset", in_out="INPUT",
                                         socket_type="NodeSocketFloat")
    age_offset.default_value = 0.0
    min_scale = ng.interface.new_socket(name="Min Scale", in_out="INPUT",
                                        socket_type="NodeSocketFloat")
    min_scale.default_value = 0.35
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT",
                             socket_type="NodeSocketGeometry")
    sockets = {"geometry": geometry.identifier, "gravity": gravity.identifier,
               "material": material.identifier, "trail": trail.identifier,
               "age_offset": age_offset.identifier,
               "min_scale": min_scale.identifier}

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1700, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1500, 0)

    birth = _attribute(nodes, links, "birth", "FLOAT", (-1700, -260))
    life = _attribute(nodes, links, "life", "FLOAT", (-1700, -360))
    vel = _attribute(nodes, links, "vel", "FLOAT_VECTOR", (-1700, -460))
    drag = _attribute(nodes, links, "drag", "FLOAT", (-1700, -560))
    pos0 = _attribute(nodes, links, "pos0", "FLOAT_VECTOR", (-1700, -660))
    rad = _attribute(nodes, links, "radius", "FLOAT", (-1700, -760))
    tau = _attribute(nodes, links, "tau", "FLOAT", (-1700, -860))
    jitter = _attribute(nodes, links, "jitter", "FLOAT_VECTOR", (-1700, -960))
    use_decay = _attribute(nodes, links, "use_decay", "FLOAT", (-1700, -1060))

    clock = nodes.new("GeometryNodeInputSceneTime")
    clock.location = (-1700, -140)

    # head_age = scene seconds + age offset - birth
    time_offset = _math(nodes, links, "ADD", clock.outputs["Seconds"],
                        group_in.outputs["Age Offset"], (-1520, -180))
    head_age = _math(nodes, links, "SUBTRACT", time_offset.outputs[0],
                     birth.outputs["Attribute"], (-1360, -200))

    # The trail scales with the age, exactly like the Python solver:
    # trail_time = min(age, trail).
    trail_safe = _math(nodes, links, "MAXIMUM", group_in.outputs["Trail"], None,
                       (-1360, -320))
    trail_safe.inputs[1].default_value = 0.0001
    trail_clamped = _math(nodes, links, "MINIMUM", head_age.outputs[0],
                          group_in.outputs["Trail"], (-1200, -320))
    trail_scale = _math(nodes, links, "DIVIDE", trail_clamped.outputs[0],
                        trail_safe.outputs[0], (-1040, -320))
    tau_eff = _math(nodes, links, "MULTIPLY", tau.outputs["Attribute"],
                    trail_scale.outputs[0], (-880, -380))
    sample_age = _math(nodes, links, "SUBTRACT", head_age.outputs[0],
                       tau_eff.outputs[0], (-720, -280))

    alive_a = _math(nodes, links, "GREATER_THAN", sample_age.outputs[0],
                    None, (-560, -340))
    alive_a.inputs[1].default_value = 0.0
    alive_b = _math(nodes, links, "LESS_THAN", sample_age.outputs[0],
                    life.outputs["Attribute"], (-560, -420))
    alive_sample = _math(nodes, links, "MULTIPLY", alive_a.outputs[0],
                         alive_b.outputs[0], (-400, -380))
    # The whole family dies with the star, not only with the sample.
    head_alive = _math(nodes, links, "LESS_THAN", head_age.outputs[0],
                       life.outputs["Attribute"], (-560, -460))
    alive = _math(nodes, links, "MULTIPLY", alive_sample.outputs[0],
                  head_alive.outputs[0], (-240, -400))

    k = _math(nodes, links, "MAXIMUM", drag.outputs["Attribute"], None,
              (-560, -520))
    k.inputs[1].default_value = 0.0001
    inv_k = _math(nodes, links, "DIVIDE", None, None, (-400, -520))
    inv_k.inputs[0].default_value = 1.0
    links.new(k.outputs[0], inv_k.inputs[1])

    k_age = _math(nodes, links, "MULTIPLY", k.outputs[0], sample_age.outputs[0],
                  (-240, -500))
    neg_k_age = _math(nodes, links, "MULTIPLY", k_age.outputs[0], None,
                      (-80, -500))
    neg_k_age.inputs[1].default_value = -1.0
    decay_term = _math(nodes, links, "EXPONENT", neg_k_age.outputs[0], None,
                       (80, -500))
    one_minus = _math(nodes, links, "SUBTRACT", None, decay_term.outputs[0],
                      (240, -500))
    one_minus.inputs[0].default_value = 1.0
    factor = _math(nodes, links, "DIVIDE", one_minus.outputs[0], k.outputs[0],
                   (400, -500))

    v_inf = _vector(nodes, links, "SCALE", group_in.outputs["Gravity"], None,
                    (-400, -680), scale=inv_k.outputs[0])
    v_inf_age = _vector(nodes, links, "SCALE", v_inf.outputs["Vector"], None,
                        (-240, -680), scale=sample_age.outputs[0])
    vel_minus = _vector(nodes, links, "SUBTRACT", vel.outputs["Attribute"],
                        v_inf.outputs["Vector"], (-400, -840))
    vel_scaled = _vector(nodes, links, "SCALE", vel_minus.outputs["Vector"],
                         None, (-240, -840), scale=factor.outputs[0])
    offset = _vector(nodes, links, "ADD", v_inf_age.outputs["Vector"],
                     vel_scaled.outputs["Vector"], (-80, -760))
    position = _vector(nodes, links, "ADD", pos0.outputs["Attribute"],
                       offset.outputs["Vector"], (80, -720))
    position_jitter = _vector(nodes, links, "ADD", position.outputs["Vector"],
                              jitter.outputs["Attribute"], (240, -720))

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (420, -200)
    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(position_jitter.outputs["Vector"], set_pos.inputs["Position"])

    ico = nodes.new("GeometryNodeMeshIcoSphere")
    ico.location = (420, -1020)
    if "Radius" in ico.inputs:
        ico.inputs["Radius"].default_value = 1.0

    scale_vec = nodes.new("ShaderNodeCombineXYZ")
    scale_vec.location = (420, -820)
    links.new(rad.outputs["Attribute"], scale_vec.inputs["X"])
    links.new(rad.outputs["Attribute"], scale_vec.inputs["Y"])
    links.new(rad.outputs["Attribute"], scale_vec.inputs["Z"])

    # Brightness decay: the head fades with its age, the grains keep their size.
    head_frac = _math(nodes, links, "DIVIDE", head_age.outputs[0],
                      life.outputs["Attribute"], (-880, -700))
    head_decay = _math(nodes, links, "SUBTRACT", None, head_frac.outputs[0],
                       (-720, -700))
    head_decay.inputs[0].default_value = 1.0
    head_decay_pos = _math(nodes, links, "MAXIMUM", head_decay.outputs[0], None,
                           (-560, -700))
    head_decay_pos.inputs[1].default_value = 0.0
    scale_range = _math(nodes, links, "SUBTRACT", None, head_decay_pos.outputs[0],
                        (-400, -700))
    scale_range.inputs[0].default_value = 1.0
    span = _math(nodes, links, "SUBTRACT", None, group_in.outputs["Min Scale"],
                 (-400, -820))
    span.inputs[0].default_value = 1.0
    decay_scaled = _math(nodes, links, "MULTIPLY", scale_range.outputs[0],
                         span.outputs[0], (-240, -760))
    decay_base = _math(nodes, links, "ADD", decay_scaled.outputs[0],
                       group_in.outputs["Min Scale"], (-80, -760))
    decay_mix = _math(nodes, links, "MULTIPLY", decay_base.outputs[0],
                      use_decay.outputs["Attribute"], (80, -760))
    decay_const = _math(nodes, links, "SUBTRACT", None,
                        use_decay.outputs["Attribute"], (80, -880))
    decay_const.inputs[0].default_value = 1.0
    decay_final = _math(nodes, links, "ADD", decay_mix.outputs[0],
                        decay_const.outputs[0], (240, -800))
    alive_decay = _math(nodes, links, "MULTIPLY", alive.outputs[0],
                        decay_final.outputs[0], (400, -800))

    scale_alive = _vector(nodes, links, "SCALE", scale_vec.outputs["Vector"],
                          None, (560, -800), scale=alive_decay.outputs[0])

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (740, -200)
    links.new(set_pos.outputs["Geometry"], instance.inputs["Points"])
    links.new(ico.outputs["Mesh"], instance.inputs["Instance"])
    links.new(scale_alive.outputs["Vector"], instance.inputs["Scale"])

    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.location = (960, -200)
    links.new(instance.outputs["Instances"], set_material.inputs["Geometry"])
    links.new(group_in.outputs["Material"], set_material.inputs["Material"])

    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    return ng, sockets


def attach_burst_modifier(obj, group, sockets, gravity, material, trail=0.0,
                          age_offset=0.0, min_scale=0.35):
    """Add the burst modifier to a points object and set its inputs."""
    modifier = obj.modifiers.new("ALD FX Burst", "NODES")
    modifier.node_group = group
    modifier[sockets["gravity"]] = gravity
    modifier[sockets["material"]] = material
    modifier[sockets["trail"]] = float(trail)
    modifier[sockets["age_offset"]] = float(age_offset)
    modifier[sockets["min_scale"]] = float(min_scale)
    return modifier


#: vertices of the icosphere instance used by the group.
INSTANCE_VERTS = 12


def realized_centers(obj, depsgraph):
    """Evaluate the group and return the centre of every instance.

    The instances are temporarily realized so the gate can compare the node
    evaluation against the Python solver.
    """
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        return []
    output = next((node for node in group.nodes
                   if node.bl_idname == "NodeGroupOutput"), None)
    if output is None:
        return []
    socket = output.inputs["Geometry"]
    source = socket.links[0].from_socket if socket.links else None
    if source is None:
        return []
    realize = group.nodes.new("GeometryNodeRealizeInstances")
    group.links.new(source, realize.inputs["Geometry"])
    group.links.new(realize.outputs["Geometry"], socket)
    try:
        obj.update_tag()
        depsgraph.update()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        centers = []
        for start in range(0, len(mesh.vertices), INSTANCE_VERTS):
            chunk = mesh.vertices[start:start + INSTANCE_VERTS]
            if len(chunk) < INSTANCE_VERTS:
                break
            total = Vector((0.0, 0.0, 0.0))
            for vertex in chunk:
                total += vertex.co
            centers.append(total / len(chunk))
        evaluated.to_mesh_clear()
        return centers
    finally:
        group.nodes.remove(realize)
        group.links.new(source, socket)
