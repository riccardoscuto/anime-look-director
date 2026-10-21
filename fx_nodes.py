"""Geometry Nodes prototype for the 3D FX bursts.

The Python side still owns the deterministic data (hash based seeds, birth
times, velocities, lifetimes). Geometry Nodes evaluates the analytic motion
every frame on the GPU, so the timeline no longer depends on a Python handler
rewriting mesh vertices.

Only the *heads* of one burst are evaluated here in the prototype: the trail
beads stay on the Python path until the Points to Curves variant is validated.
"""

import bpy

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


def _socket_ids(ng):
    ids = {}
    for item in ng.interface.items_tree:
        name = getattr(item, "name", "")
        if getattr(item, "in_out", "") == "INPUT":
            ids[name.lower()] = item.identifier
        else:
            ids["output"] = item.identifier
    ids.setdefault("geometry", "Socket_0")
    ids.setdefault("gravity", "Socket_1")
    ids.setdefault("material", "Socket_2")
    ids.setdefault("radius", "Socket_3")
    return ids


def build_burst_group():
    """Create (or refresh) the burst node group and return it with its sockets."""
    existing = bpy.data.node_groups.get(GROUP_NAME)
    if existing is not None:
        return existing, _socket_ids(existing)
    ng = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
    nodes = ng.nodes
    links = ng.links

    sockets = {}
    geometry = ng.interface.new_socket(name="Geometry", in_out="INPUT",
                                        socket_type="NodeSocketGeometry")
    gravity = ng.interface.new_socket(name="Gravity", in_out="INPUT",
                                       socket_type="NodeSocketVector")
    material = ng.interface.new_socket(name="Material", in_out="INPUT",
                                        socket_type="NodeSocketMaterial")
    radius = ng.interface.new_socket(name="Radius", in_out="INPUT",
                                     socket_type="NodeSocketFloat")
    radius.default_value = 1.0
    output = ng.interface.new_socket(name="Geometry", in_out="OUTPUT",
                                     socket_type="NodeSocketGeometry")
    sockets = {"geometry": geometry.identifier, "gravity": gravity.identifier,
               "material": material.identifier, "radius": radius.identifier,
               "output": output.identifier}

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1200, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1200, 0)

    birth = _attribute(nodes, links, "birth", "FLOAT", (-1200, -260))
    life = _attribute(nodes, links, "life", "FLOAT", (-1200, -360))
    vel = _attribute(nodes, links, "vel", "FLOAT_VECTOR", (-1200, -460))
    drag = _attribute(nodes, links, "drag", "FLOAT", (-1200, -560))
    pos0 = _attribute(nodes, links, "pos0", "FLOAT_VECTOR", (-1200, -660))
    rad = _attribute(nodes, links, "radius", "FLOAT", (-1200, -760))

    clock = nodes.new("GeometryNodeInputSceneTime")
    clock.location = (-1200, -140)

    age = _math(nodes, links, "SUBTRACT", clock.outputs["Seconds"],
                birth.outputs["Attribute"], (-1000, -200))
    alive_a = _math(nodes, links, "GREATER_THAN", age.outputs[0],
                    None, (-840, -260))
    alive_a.inputs[1].default_value = 0.0
    alive_b = _math(nodes, links, "LESS_THAN", age.outputs[0],
                    life.outputs["Attribute"], (-840, -340))
    alive = _math(nodes, links, "MULTIPLY", alive_a.outputs[0],
                  alive_b.outputs[0], (-680, -300))

    life_frac = _math(nodes, links, "DIVIDE", age.outputs[0],
                      life.outputs["Attribute"], (-680, -620))
    decay = _math(nodes, links, "SUBTRACT", None, life_frac.outputs[0],
                  (-520, -620))
    decay.inputs[0].default_value = 1.0
    decay_pos = _math(nodes, links, "MAXIMUM", decay.outputs[0], None,
                      (-360, -620))
    decay_pos.inputs[1].default_value = 0.0
    scale_amount = _math(nodes, links, "MULTIPLY", alive.outputs[0],
                         decay_pos.outputs[0], (-200, -620))

    k = _math(nodes, links, "MAXIMUM", drag.outputs["Attribute"], None,
              (-840, -440))
    k.inputs[1].default_value = 0.0001
    inv_k = _math(nodes, links, "DIVIDE", None, None, (-680, -440))
    inv_k.inputs[0].default_value = 1.0
    links.new(k.outputs[0], inv_k.inputs[1])

    neg_k_age = _math(nodes, links, "MULTIPLY", k.outputs[0], age.outputs[0],
                      (-520, -420))
    decay = _math(nodes, links, "EXPONENT", neg_k_age.outputs[0], None,
                  (-360, -420))
    one_minus = _math(nodes, links, "SUBTRACT", None, decay.outputs[0],
                      (-200, -420))
    one_minus.inputs[0].default_value = 1.0
    factor = _math(nodes, links, "DIVIDE", one_minus.outputs[0],
                   k.outputs[0], (-40, -420))

    v_inf = _vector(nodes, links, "SCALE", group_in.outputs["Gravity"], None,
                    (-360, -600), scale=inv_k.outputs[0])
    v_inf_age = _vector(nodes, links, "SCALE", v_inf.outputs["Vector"], None,
                        (-200, -600), scale=age.outputs[0])
    vel_minus = _vector(nodes, links, "SUBTRACT", vel.outputs["Attribute"],
                        v_inf.outputs["Vector"], (-360, -760))
    vel_scaled = _vector(nodes, links, "SCALE", vel_minus.outputs["Vector"], None,
                         (-200, -760), scale=factor.outputs[0])
    offset = _vector(nodes, links, "ADD", v_inf_age.outputs["Vector"],
                     vel_scaled.outputs["Vector"], (-40, -660))
    position = _vector(nodes, links, "ADD", pos0.outputs["Attribute"],
                       offset.outputs["Vector"], (120, -600))

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (320, -200)
    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(position.outputs["Vector"], set_pos.inputs["Position"])

    ico = nodes.new("GeometryNodeMeshIcoSphere")
    ico.location = (320, -900)
    if "Radius" in ico.inputs:
        ico.inputs["Radius"].default_value = 1.0

    scale_vec = nodes.new("ShaderNodeCombineXYZ")
    scale_vec.location = (320, -700)
    links.new(rad.outputs["Attribute"], scale_vec.inputs["X"])
    links.new(rad.outputs["Attribute"], scale_vec.inputs["Y"])
    links.new(rad.outputs["Attribute"], scale_vec.inputs["Z"])
    scale_alive = _vector(nodes, links, "SCALE", scale_vec.outputs["Vector"], None,
                          (480, -700), scale=scale_amount.outputs[0])

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (640, -200)
    links.new(set_pos.outputs["Geometry"], instance.inputs["Points"])
    links.new(ico.outputs["Mesh"], instance.inputs["Instance"])
    links.new(scale_alive.outputs["Vector"], instance.inputs["Scale"])

    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.location = (860, -200)
    links.new(instance.outputs["Instances"], set_material.inputs["Geometry"])
    links.new(group_in.outputs["Material"], set_material.inputs["Material"])

    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    return ng, sockets


def attach_burst_modifier(obj, group, sockets, gravity, material, radius=1.0):
    """Add the burst modifier to a points object and set its inputs."""
    modifier = obj.modifiers.new("ALD FX Burst", "NODES")
    modifier.node_group = group
    modifier[sockets["gravity"]] = gravity
    modifier[sockets["material"]] = material
    modifier[sockets["radius"]] = radius
    return modifier
