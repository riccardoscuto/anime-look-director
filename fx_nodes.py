"""Geometry Nodes evaluation of the 3D FX bursts.

The Python side owns the deterministic data (hash based seeds, birth times,
velocities, lifetimes, per grain jitter). Geometry Nodes evaluates the analytic
motion every frame, so the timeline no longer depends on a Python handler
rewriting mesh vertices.

Two groups are built:

``ALD | FX Burst GN``
    evaluates the star heads, the beaded trail grains, the inner pistil and
    the child sparks as instanced spheres;
``ALD | FX Trail GN``
    evaluates the thin filament of every star as a curve tube.

The same point attributes drive both:

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
TRAIL_GROUP_NAME = "ALD | FX Trail GN"

#: Build marker of the node groups: a group saved with an older marker is
#: rebuilt and the modifiers are remapped on the new structure.
#: 3: the clock accepts a time override (the preview mode of a system).
SCHEMA = 3


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


def _socket_ids(ng, defaults):
    """Resolve the interface socket identifiers by name."""
    ids = {}
    for item in ng.interface.items_tree:
        name = getattr(item, "name", "")
        if getattr(item, "in_out", "") == "INPUT":
            ids[name.lower().replace(" ", "_")] = item.identifier
        else:
            ids["output"] = item.identifier
    for key, value in defaults.items():
        ids.setdefault(key, value)
    return ids


BURST_SOCKET_DEFAULTS = {"geometry": "Socket_0", "gravity": "Socket_1",
                          "material": "Socket_2", "trail": "Socket_3",
                          "age_offset": "Socket_4", "min_scale": "Socket_5",
                          "decay_power": "Socket_6", "energy_power": "Socket_7",
                          "camera_position": "Socket_8",
                          "atmospheric_fade": "Socket_9",
                          "role_energy": "Socket_10",
                          "time_override": "Socket_11",
                          "use_time_override": "Socket_12",
                          "fade_window": "Socket_13"}
TRAIL_SOCKET_DEFAULTS = {"geometry": "Socket_0", "gravity": "Socket_1",
                          "material": "Socket_2", "trail": "Socket_3",
                          "age_offset": "Socket_4", "radius": "Socket_5",
                          "fade_window": "Socket_6",
                          "time_override": "Socket_7",
                          "use_time_override": "Socket_8",
                          "energy_power": "Socket_9",
                          "role_energy": "Socket_10"}


def _motion(nodes, links, group_in):
    """Build the analytic motion subgraph.

    Returns the sockets of the sample position, the sample age, the head age
    and the lifetime, so the callers can reuse them.
    """
    birth = _attribute(nodes, links, "birth", "FLOAT", (-1700, -260))
    life = _attribute(nodes, links, "life", "FLOAT", (-1700, -360))
    vel = _attribute(nodes, links, "vel", "FLOAT_VECTOR", (-1700, -460))
    drag = _attribute(nodes, links, "drag", "FLOAT", (-1700, -560))
    pos0 = _attribute(nodes, links, "pos0", "FLOAT_VECTOR", (-1700, -660))
    tau = _attribute(nodes, links, "tau", "FLOAT", (-1700, -860))
    jitter = _attribute(nodes, links, "jitter", "FLOAT_VECTOR", (-1700, -960))

    clock = nodes.new("GeometryNodeInputSceneTime")
    clock.location = (-1700, -140)

    # The clock of the system: the scene time, unless the system is in
    # preview mode: then the time is a fixed value chosen by the user.
    #   clock = scene_seconds * (1 - use_override) + override * use_override
    use_override = _math(nodes, links, "MINIMUM", group_in.outputs[
        "Use Time Override"], None, (-1700, -40))
    use_override.inputs[1].default_value = 1.0
    inverse_override = _math(nodes, links, "SUBTRACT", None,
                             use_override.outputs[0], (-1540, -40))
    inverse_override.inputs[0].default_value = 1.0
    scene_seconds = _math(nodes, links, "MULTIPLY", clock.outputs["Seconds"],
                           inverse_override.outputs[0], (-1380, -100))
    override_value = _math(nodes, links, "MULTIPLY",
                            group_in.outputs["Time Override"],
                            use_override.outputs[0], (-1380, 20))
    clock_value = _math(nodes, links, "ADD", scene_seconds.outputs[0],
                        override_value.outputs[0], (-1220, -60))

    # head_age = the clock of the system + age offset - birth
    time_offset = _math(nodes, links, "ADD", clock_value.outputs[0],
                        group_in.outputs["Age Offset"], (-1060, -180))
    head_age = _math(nodes, links, "SUBTRACT", time_offset.outputs[0],
                     birth.outputs["Attribute"], (-900, -200))

    # The train never runs ahead of the body: the front of the train is the
    # last position of the body, not the current time. After the body dies
    # no new sample is born along the trajectory: the residuals fade, they
    # do not travel.
    #   front   = clamp(head_age, 0, life - fade_window)
    #   train   = min(front, trail)
    #   tau_eff = tau * train / trail
    #   sample_age = front - tau_eff
    trail_safe = _math(nodes, links, "MAXIMUM", group_in.outputs["Trail"], None,
                       (-1360, -320))
    trail_safe.inputs[1].default_value = 0.0001
    fade_window = _math(nodes, links, "MAXIMUM", group_in.outputs[
        "Fade Window"], None, (-1360, -420))
    fade_window.inputs[1].default_value = 0.0
    burn_life = _math(nodes, links, "SUBTRACT", life.outputs["Attribute"],
                      fade_window.outputs[0], (-1360, -500))
    head_age_pos = _math(nodes, links, "MAXIMUM", head_age.outputs[0], None,
                         (-1200, -240))
    head_age_pos.inputs[1].default_value = 0.0
    front = _math(nodes, links, "MINIMUM", head_age_pos.outputs[0],
                  burn_life.outputs[0], (-1040, -280))
    front_pos = _math(nodes, links, "MAXIMUM", front.outputs[0], None,
                      (-880, -280))
    front_pos.inputs[1].default_value = 0.0
    train_time = _math(nodes, links, "MINIMUM", front_pos.outputs[0],
                       trail_safe.outputs[0], (-760, -360))
    trail_scale = _math(nodes, links, "DIVIDE", train_time.outputs[0],
                        trail_safe.outputs[0], (-620, -360))
    tau_eff = _math(nodes, links, "MULTIPLY", tau.outputs["Attribute"],
                    trail_scale.outputs[0], (-460, -380))
    sample_age = _math(nodes, links, "SUBTRACT", front_pos.outputs[0],
                       tau_eff.outputs[0], (-300, -280))
    # A negative age is a sample that is not born yet: the evaluation is
    # clamped, so the position never leaves the trajectory.
    sample_age_pos = _math(nodes, links, "MAXIMUM", sample_age.outputs[0],
                           None, (-140, -280))
    sample_age_pos.inputs[1].default_value = 0.0

    k = _math(nodes, links, "MAXIMUM", drag.outputs["Attribute"], None,
              (-560, -520))
    k.inputs[1].default_value = 0.0001
    inv_k = _math(nodes, links, "DIVIDE", None, None, (-400, -520))
    inv_k.inputs[0].default_value = 1.0
    links.new(k.outputs[0], inv_k.inputs[1])

    k_age = _math(nodes, links, "MULTIPLY", k.outputs[0],
                  sample_age_pos.outputs[0], (-240, -500))
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

    # Drag free limit: the closed form above loses precision when k -> 0, so
    # the ballistic solution is used instead (same branch as the Python
    # solver).
    ballistic = _math(nodes, links, "LESS_THAN", drag.outputs["Attribute"],
                      None, (240, -1040))
    ballistic.inputs[1].default_value = 0.0001
    age_squared = _math(nodes, links, "MULTIPLY", sample_age_pos.outputs[0],
                        sample_age_pos.outputs[0], (240, -1160))
    half_gravity = _math(nodes, links, "MULTIPLY", age_squared.outputs[0], None,
                         (400, -1160))
    half_gravity.inputs[1].default_value = 0.5
    vel_age = _vector(nodes, links, "SCALE", vel.outputs["Attribute"], None,
                      (400, -1280), scale=sample_age_pos.outputs[0])
    gravity_term = _vector(nodes, links, "SCALE", group_in.outputs["Gravity"],
                           None, (560, -1160), scale=half_gravity.outputs[0])
    ballistic_offset = _vector(nodes, links, "ADD", vel_age.outputs["Vector"],
                               gravity_term.outputs["Vector"], (560, -1280))
    ballistic_position = _vector(nodes, links, "ADD",
                                 pos0.outputs["Attribute"],
                                 ballistic_offset.outputs["Vector"], (720, -1280))
    inverse_ballistic = _math(nodes, links, "SUBTRACT", None,
                              ballistic.outputs[0], (400, -1040))
    inverse_ballistic.inputs[0].default_value = 1.0
    drag_weight = _vector(nodes, links, "SCALE", position.outputs["Vector"],
                          None, (720, -720), scale=inverse_ballistic.outputs[0])
    ballistic_weight = _vector(nodes, links, "SCALE",
                               ballistic_position.outputs["Vector"], None,
                               (720, -980), scale=ballistic.outputs[0])
    mixed_position = _vector(nodes, links, "ADD", drag_weight.outputs["Vector"],
                             ballistic_weight.outputs["Vector"], (880, -860))
    position_jitter = _vector(nodes, links, "ADD", mixed_position.outputs["Vector"],
                              jitter.outputs["Attribute"], (1000, -860))
    return {"position": position_jitter.outputs["Vector"],
            "sample_age": sample_age_pos.outputs[0],
            "head_age": head_age.outputs[0],
            "life": life.outputs["Attribute"]}


def _build_group(name, socket_specs):
    """Create a node group with the given interface sockets."""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    sockets = {}
    for socket_name, socket_type, default in socket_specs:
        socket = ng.interface.new_socket(name=socket_name, in_out="INPUT",
                                          socket_type=socket_type)
        if default is not None and socket_type == "NodeSocketFloat":
            socket.default_value = default
        sockets[socket_name.lower().replace(" ", "_")] = socket.identifier
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT",
                             socket_type="NodeSocketGeometry")
    return ng, sockets


def _remap_modifiers(old, new):
    """Point the modifiers of the old group to the new one."""
    remapped = 0
    for obj in bpy.data.objects:
        for modifier in obj.modifiers:
            if modifier.type == "NODES" and modifier.node_group is old:
                modifier.node_group = new
                remapped += 1
    return remapped


def _upgrade_group(name, builder, defaults):
    """Return the group of the current schema, migrating the old one."""
    existing = bpy.data.node_groups.get(name)
    if existing is not None and int(existing.get("ald_schema", 0)) == SCHEMA:
        return existing, _socket_ids(existing, defaults)
    old = existing
    if old is not None:
        # The old structure is kept aside until nothing uses it any more.
        old.name = "%s (schema %d)" % (name, int(old.get("ald_schema", 0)))
    group, sockets = builder()
    group["ald_schema"] = SCHEMA
    if old is not None:
        _remap_modifiers(old, group)
        if old.users == 0:
            bpy.data.node_groups.remove(old)
    return group, sockets


def build_burst_group():
    """Create (or reuse) the burst node group and return it with its sockets."""
    return _upgrade_group(GROUP_NAME, _create_burst_group, BURST_SOCKET_DEFAULTS)


def _create_burst_group():
    ng, sockets = _build_group(GROUP_NAME, (
        ("Geometry", "NodeSocketGeometry", None),
        ("Gravity", "NodeSocketVector", None),
        ("Material", "NodeSocketMaterial", None),
        ("Trail", "NodeSocketFloat", 0.0),
        ("Age Offset", "NodeSocketFloat", 0.0),
        ("Min Scale", "NodeSocketFloat", 0.35),
        ("Decay Power", "NodeSocketFloat", 1.0),
        ("Energy Power", "NodeSocketFloat", 1.0),
        ("Camera Position", "NodeSocketVector", None),
        ("Atmospheric Fade", "NodeSocketFloat", 0.0),
        ("Role Energy", "NodeSocketFloat", 1.0),
        ("Time Override", "NodeSocketFloat", 0.0),
        ("Use Time Override", "NodeSocketFloat", 0.0),
        ("Fade Window", "NodeSocketFloat", 0.0),
    ))
    ng["ald_fx"] = True
    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1900, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1500, 0)

    motion = _motion(nodes, links, group_in)
    rad = _attribute(nodes, links, "radius", "FLOAT", (-1700, -760))
    tau_attr = _attribute(nodes, links, "tau", "FLOAT", (-1700, -860))
    use_decay = _attribute(nodes, links, "use_decay", "FLOAT", (-1700, -1060))

    alive_a = _math(nodes, links, "GREATER_THAN", motion["sample_age"], None,
                    (-560, -340))
    alive_a.inputs[1].default_value = 0.0
    alive_b = _math(nodes, links, "LESS_THAN", motion["sample_age"],
                    motion["life"], (-560, -420))
    alive_sample = _math(nodes, links, "MULTIPLY", alive_a.outputs[0],
                         alive_b.outputs[0], (-400, -380))
    # The whole family dies with the star, not only with the sample.
    head_alive = _math(nodes, links, "LESS_THAN", motion["head_age"],
                       motion["life"], (-560, -460))
    alive = _math(nodes, links, "MULTIPLY", alive_sample.outputs[0],
                  head_alive.outputs[0], (-240, -400))

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (420, -200)
    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(motion["position"], set_pos.inputs["Position"])

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
    # Shape decay: s(u) = m + (1 - m) * (1 - u) ** p, with u = age / life.
    # The scale must shrink with the age, never grow.
    head_frac = _math(nodes, links, "DIVIDE", motion["head_age"],
                      motion["life"], (-880, -700))
    head_frac_low = _math(nodes, links, "MAXIMUM", head_frac.outputs[0], None,
                          (-720, -760))
    head_frac_low.inputs[1].default_value = 0.0
    head_frac_clamped = _math(nodes, links, "MINIMUM", head_frac_low.outputs[0],
                              None, (-560, -760))
    head_frac_clamped.inputs[1].default_value = 1.0
    one_minus = _math(nodes, links, "SUBTRACT", None,
                      head_frac_clamped.outputs[0], (-400, -760))
    one_minus.inputs[0].default_value = 1.0
    shape = _math(nodes, links, "POWER", one_minus.outputs[0],
                  group_in.outputs["Decay Power"], (-240, -760))
    span = _math(nodes, links, "SUBTRACT", None, group_in.outputs["Min Scale"],
                 (-400, -860))
    span.inputs[0].default_value = 1.0
    decay_scaled = _math(nodes, links, "MULTIPLY", shape.outputs[0],
                         span.outputs[0], (-80, -800))
    decay_base = _math(nodes, links, "ADD", decay_scaled.outputs[0],
                       group_in.outputs["Min Scale"], (80, -800))
    decay_mix = _math(nodes, links, "MULTIPLY", decay_base.outputs[0],
                      use_decay.outputs["Attribute"], (80, -760))
    decay_const = _math(nodes, links, "SUBTRACT", None,
                        use_decay.outputs["Attribute"], (80, -880))
    decay_const.inputs[0].default_value = 1.0
    decay_final = _math(nodes, links, "ADD", decay_mix.outputs[0],
                        decay_const.outputs[0], (240, -800))
    alive_decay = _math(nodes, links, "MULTIPLY", alive.outputs[0],
                        decay_final.outputs[0], (400, -800))

    # Energy decay: e(u) = (1 - u) ** q. The energy is an attribute, not a
    # scale: the geometry shrinks while the emission fades on its own curve.
    energy = _math(nodes, links, "POWER", one_minus.outputs[0],
                   group_in.outputs["Energy Power"], (240, -960))
    # Atmospheric fade: the emission is attenuated with the distance from the
    # camera, like the air between the viewer and the burst.
    to_camera = _vector(nodes, links, "SUBTRACT", motion["position"],
                        group_in.outputs["Camera Position"], (240, -1120))
    distance = _vector(nodes, links, "LENGTH", to_camera.outputs["Vector"], None,
                       (400, -1120))
    fade_scaled = _math(nodes, links, "MULTIPLY", distance.outputs["Value"],
                        group_in.outputs["Atmospheric Fade"], (560, -1120))
    fade_reference = _math(nodes, links, "DIVIDE", fade_scaled.outputs[0], None,
                            (720, -1120))
    fade_reference.inputs[1].default_value = 100.0
    fade_negative = _math(nodes, links, "MULTIPLY", fade_reference.outputs[0],
                           None, (880, -1120))
    fade_negative.inputs[1].default_value = -1.0
    fade_factor = _math(nodes, links, "EXPONENT", fade_negative.outputs[0], None,
                        (1040, -1120))
    energy_final = _math(nodes, links, "MULTIPLY", energy.outputs[0],
                         fade_factor.outputs[0], (1200, -960))
    # The role scales the emission: a filament is less energetic than a spark.
    role_energy = _math(nodes, links, "MULTIPLY", energy_final.outputs[0],
                         group_in.outputs["Role Energy"], (1360, -960))
    store = nodes.new("GeometryNodeStoreNamedAttribute")
    store.location = (620, -200)
    store.data_type = "FLOAT"
    store.domain = "POINT"
    store.inputs["Name"].default_value = "energy"
    links.new(set_pos.outputs["Geometry"], store.inputs["Geometry"])
    links.new(role_energy.outputs[0], store.inputs["Value"])

    # The material contract: age_norm and trail_u describe the state of the
    # particle along its life and along its trail.
    age_store = nodes.new("GeometryNodeStoreNamedAttribute")
    age_store.location = (620, -60)
    age_store.data_type = "FLOAT"
    age_store.domain = "POINT"
    age_store.inputs["Name"].default_value = "age_norm"
    links.new(store.outputs["Geometry"], age_store.inputs["Geometry"])
    links.new(head_frac_clamped.outputs[0], age_store.inputs["Value"])

    trail_ratio = _math(nodes, links, "DIVIDE", tau_attr.outputs["Attribute"],
                        group_in.outputs["Trail"], (240, -1200))
    trail_profile = _math(nodes, links, "SUBTRACT", None,
                          trail_ratio.outputs[0], (400, -1200))
    trail_profile.inputs[0].default_value = 1.0
    trail_clamped = _math(nodes, links, "MAXIMUM", trail_profile.outputs[0], None,
                          (560, -1200))
    trail_clamped.inputs[1].default_value = 0.0
    trail_store = nodes.new("GeometryNodeStoreNamedAttribute")
    trail_store.location = (620, -340)
    trail_store.data_type = "FLOAT"
    trail_store.domain = "POINT"
    trail_store.inputs["Name"].default_value = "trail_u"
    links.new(age_store.outputs["Geometry"], trail_store.inputs["Geometry"])
    links.new(trail_clamped.outputs[0], trail_store.inputs["Value"])

    scale_alive = _vector(nodes, links, "SCALE", scale_vec.outputs["Vector"],
                          None, (560, -800), scale=alive_decay.outputs[0])

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (740, -200)
    links.new(trail_store.outputs["Geometry"], instance.inputs["Points"])
    links.new(ico.outputs["Mesh"], instance.inputs["Instance"])
    links.new(scale_alive.outputs["Vector"], instance.inputs["Scale"])

    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.location = (960, -200)
    links.new(instance.outputs["Instances"], set_material.inputs["Geometry"])
    links.new(group_in.outputs["Material"], set_material.inputs["Material"])

    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    return ng, sockets


def build_trail_group():
    """Create (or reuse) the trail node group and return it with its sockets."""
    return _upgrade_group(TRAIL_GROUP_NAME, _create_trail_group,
                          TRAIL_SOCKET_DEFAULTS)


def _create_trail_group():
    ng, sockets = _build_group(TRAIL_GROUP_NAME, (
        ("Geometry", "NodeSocketGeometry", None),
        ("Gravity", "NodeSocketVector", None),
        ("Material", "NodeSocketMaterial", None),
        ("Trail", "NodeSocketFloat", 0.0),
        ("Age Offset", "NodeSocketFloat", 0.0),
        ("Radius", "NodeSocketFloat", 0.02),
        ("Fade Window", "NodeSocketFloat", 0.0),
        ("Time Override", "NodeSocketFloat", 0.0),
        ("Use Time Override", "NodeSocketFloat", 0.0),
        ("Energy Power", "NodeSocketFloat", 1.0),
        ("Role Energy", "NodeSocketFloat", 1.0),
    ))
    ng["ald_fx"] = True
    nodes = ng.nodes
    links = ng.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1900, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1500, 0)

    motion = _motion(nodes, links, group_in)
    rad = _attribute(nodes, links, "radius", "FLOAT", (-1700, -760))
    curve_id = _attribute(nodes, links, "curve_id", "INT", (-1700, -1160))
    weight = _attribute(nodes, links, "weight", "FLOAT", (-1700, -1260))
    tau_attr = _attribute(nodes, links, "tau", "FLOAT", (-1700, -860))

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (420, -200)
    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(motion["position"], set_pos.inputs["Position"])

    # Samples that are not born yet are removed: the tail grows with the age.
    # When no fade window is set the trail dies with the body.
    unborn = _math(nodes, links, "LESS_THAN", motion["sample_age"], None,
                   (420, -420))
    unborn.inputs[1].default_value = 0.0
    # The train dies with the body: the front of the train is frozen when
    # the body is dead, the residuals only fade.
    dead = _math(nodes, links, "GREATER_THAN", motion["head_age"],
                 motion["life"], (420, -520))
    no_fade = _math(nodes, links, "LESS_THAN", group_in.outputs["Fade Window"],
                    None, (420, -620))
    # Fade Window = 0 means explicitly no persistence: the train dies with
    # the body. There is no magic threshold.
    no_fade.inputs[1].default_value = 0.0001
    dead_gated = _math(nodes, links, "MULTIPLY", dead.outputs[0],
                       no_fade.outputs[0], (620, -560))
    remove = _math(nodes, links, "MAXIMUM", unborn.outputs[0],
                   dead_gated.outputs[0], (620, -420))
    delete = nodes.new("GeometryNodeDeleteGeometry")
    delete.location = (800, -200)
    delete.domain = "POINT"
    delete.mode = "ALL"
    links.new(set_pos.outputs["Geometry"], delete.inputs["Geometry"])
    links.new(remove.outputs[0], delete.inputs["Selection"])

    to_curves = nodes.new("GeometryNodePointsToCurves")
    to_curves.location = (980, -200)
    links.new(delete.outputs["Geometry"], to_curves.inputs["Points"])
    links.new(curve_id.outputs["Attribute"], to_curves.inputs["Curve Group ID"])
    links.new(weight.outputs["Attribute"], to_curves.inputs["Weight"])

    # Fade: the persistent train of a meteor thins out after the head dies.
    fade_safe = _math(nodes, links, "MAXIMUM", group_in.outputs["Fade Window"],
                      None, (620, -760))
    fade_safe.inputs[1].default_value = 0.0001
    fade_over = _math(nodes, links, "SUBTRACT", motion["head_age"],
                      motion["life"], (620, -860))
    fade_over_pos = _math(nodes, links, "MAXIMUM", fade_over.outputs[0], None,
                          (780, -860))
    fade_over_pos.inputs[1].default_value = 0.0
    fade_ratio = _math(nodes, links, "DIVIDE", fade_over_pos.outputs[0],
                       fade_safe.outputs[0], (940, -820))
    fade = _math(nodes, links, "SUBTRACT", None, fade_ratio.outputs[0],
                 (1060, -820))
    fade.inputs[0].default_value = 1.0
    fade_clamped = _math(nodes, links, "MAXIMUM", fade.outputs[0], None,
                         (1180, -820))
    fade_clamped.inputs[1].default_value = 0.0
    radius_scaled = _math(nodes, links, "MULTIPLY", rad.outputs["Attribute"],
                          fade_clamped.outputs[0], (1300, -820))

    set_radius = nodes.new("GeometryNodeSetCurveRadius")
    set_radius.location = (1420, -200)
    links.new(to_curves.outputs["Curves"], set_radius.inputs["Curve"])
    links.new(radius_scaled.outputs[0], set_radius.inputs["Radius"])

    # The energy of the trail: the material reads the attribute, so the
    # curve must write it. Without it the shader reads nothing and the
    # train stays dark.
    head_frac = _math(nodes, links, "DIVIDE", motion["head_age"],
                      motion["life"], (620, -960))
    head_frac_low = _math(nodes, links, "MAXIMUM", head_frac.outputs[0], None,
                          (780, -960))
    head_frac_low.inputs[1].default_value = 0.0
    head_frac_clamped = _math(nodes, links, "MINIMUM", head_frac_low.outputs[0],
                              None, (940, -960))
    head_frac_clamped.inputs[1].default_value = 1.0
    one_minus = _math(nodes, links, "SUBTRACT", None,
                      head_frac_clamped.outputs[0], (1100, -960))
    one_minus.inputs[0].default_value = 1.0
    energy = _math(nodes, links, "POWER", one_minus.outputs[0],
                   group_in.outputs["Energy Power"], (1260, -960))
    role_energy = _math(nodes, links, "MULTIPLY", energy.outputs[0],
                         group_in.outputs["Role Energy"], (1420, -960))
    energy_store = nodes.new("GeometryNodeStoreNamedAttribute")
    energy_store.location = (1240, -200)
    energy_store.data_type = "FLOAT"
    energy_store.domain = "POINT"
    energy_store.inputs["Name"].default_value = "energy"
    links.new(set_radius.outputs["Curve"], energy_store.inputs["Geometry"])
    links.new(role_energy.outputs[0], energy_store.inputs["Value"])

    age_store = nodes.new("GeometryNodeStoreNamedAttribute")
    age_store.location = (1400, -140)
    age_store.data_type = "FLOAT"
    age_store.domain = "POINT"
    age_store.inputs["Name"].default_value = "age_norm"
    links.new(energy_store.outputs["Geometry"], age_store.inputs["Geometry"])
    links.new(head_frac_clamped.outputs[0], age_store.inputs["Value"])

    trail_ratio = _math(nodes, links, "DIVIDE", tau_attr.outputs["Attribute"],
                        group_in.outputs["Trail"], (620, -1360))
    trail_profile = _math(nodes, links, "SUBTRACT", None,
                          trail_ratio.outputs[0], (780, -1360))
    trail_profile.inputs[0].default_value = 1.0
    trail_clamped = _math(nodes, links, "MAXIMUM", trail_profile.outputs[0], None,
                          (940, -1360))
    trail_clamped.inputs[1].default_value = 0.0
    trail_store = nodes.new("GeometryNodeStoreNamedAttribute")
    trail_store.location = (1560, -200)
    trail_store.data_type = "FLOAT"
    trail_store.domain = "POINT"
    trail_store.inputs["Name"].default_value = "trail_u"
    links.new(age_store.outputs["Geometry"], trail_store.inputs["Geometry"])
    links.new(trail_clamped.outputs[0], trail_store.inputs["Value"])

    circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
    circle.location = (1420, -520)
    if "Resolution" in circle.inputs:
        circle.inputs["Resolution"].default_value = 4
    links.new(group_in.outputs["Radius"], circle.inputs["Radius"])

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (1720, -200)
    links.new(trail_store.outputs["Geometry"], curve_to_mesh.inputs["Curve"])
    links.new(circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
    if "Fill Caps" in curve_to_mesh.inputs:
        curve_to_mesh.inputs["Fill Caps"].default_value = True

    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.location = (1880, -200)
    links.new(curve_to_mesh.outputs["Mesh"], set_material.inputs["Geometry"])
    links.new(group_in.outputs["Material"], set_material.inputs["Material"])

    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    return ng, sockets


def attach_burst_modifier(obj, group, sockets, gravity, material, trail=0.0,
                          age_offset=0.0, min_scale=0.35, decay_power=1.0,
                          energy_power=1.0, camera_position=None,
                          atmospheric_fade=0.0, role_energy=1.0,
                          time_override=0.0, use_time_override=0.0):
    """Add the burst modifier to a points object and set its inputs."""
    modifier = obj.modifiers.new("ALD FX Burst", "NODES")
    modifier.node_group = group
    modifier[sockets["gravity"]] = gravity
    modifier[sockets["material"]] = material
    modifier[sockets["trail"]] = float(trail)
    modifier[sockets["age_offset"]] = float(age_offset)
    modifier[sockets["min_scale"]] = float(min_scale)
    modifier[sockets["decay_power"]] = float(decay_power)
    modifier[sockets["energy_power"]] = float(energy_power)
    modifier[sockets["camera_position"]] = tuple(camera_position or
                                                 (0.0, 0.0, 0.0))
    modifier[sockets["atmospheric_fade"]] = float(atmospheric_fade)
    modifier[sockets["role_energy"]] = float(role_energy)
    modifier[sockets["time_override"]] = float(time_override)
    modifier[sockets["use_time_override"]] = float(use_time_override)
    return modifier


def set_look(obj, energy_power=None, camera_position=None,
             atmospheric_fade=None):
    """Update the look inputs of a burst modifier without a rebuild."""
    for modifier in obj.modifiers:
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        group = modifier.node_group
        if group.name != GROUP_NAME:
            continue
        defaults = BURST_SOCKET_DEFAULTS
        if energy_power is not None:
            identifier = _socket_ids(group, defaults)["energy_power"]
            if identifier in modifier:
                modifier[identifier] = float(energy_power)
        if camera_position is not None:
            identifier = _socket_ids(group, defaults)["camera_position"]
            if identifier in modifier:
                modifier[identifier] = tuple(camera_position)
        if atmospheric_fade is not None:
            identifier = _socket_ids(group, defaults)["atmospheric_fade"]
            if identifier in modifier:
                modifier[identifier] = float(atmospheric_fade)
    return True


def attach_trail_modifier(obj, group, sockets, gravity, material, trail=0.0,
                          age_offset=0.0, radius=0.02, fade_window=0.0,
                          time_override=0.0, use_time_override=0.0,
                          energy_power=1.0, role_energy=1.0):
    """Add the trail modifier to a points object and set its inputs."""
    modifier = obj.modifiers.new("ALD FX Trail", "NODES")
    modifier.node_group = group
    modifier[sockets["gravity"]] = gravity
    modifier[sockets["material"]] = material
    modifier[sockets["trail"]] = float(trail)
    modifier[sockets["age_offset"]] = float(age_offset)
    modifier[sockets["radius"]] = float(radius)
    modifier[sockets["fade_window"]] = float(fade_window)
    modifier[sockets["time_override"]] = float(time_override)
    modifier[sockets["use_time_override"]] = float(use_time_override)
    modifier[sockets["energy_power"]] = float(energy_power)
    modifier[sockets["role_energy"]] = float(role_energy)
    return modifier


def set_age_offset(obj, age):
    """Move an object in time by writing the age offset of its modifier.

    The geometry is not rebuilt: the node group reads the offset every frame.
    """
    for modifier in obj.modifiers:
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        group = modifier.node_group
        if group.name == GROUP_NAME:
            defaults = BURST_SOCKET_DEFAULTS
        elif group.name == TRAIL_GROUP_NAME:
            defaults = TRAIL_SOCKET_DEFAULTS
        else:
            continue
        identifier = _socket_ids(group, defaults)["age_offset"]
        if identifier in modifier:
            modifier[identifier] = float(age)
    return True


def set_clock(obj, age_offset, time_override=None, use_time_override=None):
    """Write the clock of a system on the modifiers of an object.

    The geometry is not rebuilt: the node group reads the clock every frame.
    """
    for modifier in obj.modifiers:
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        group = modifier.node_group
        if group.name == GROUP_NAME:
            defaults = BURST_SOCKET_DEFAULTS
        elif group.name == TRAIL_GROUP_NAME:
            defaults = TRAIL_SOCKET_DEFAULTS
        else:
            continue
        identifiers = _socket_ids(group, defaults)
        if identifiers["age_offset"] in modifier:
            modifier[identifiers["age_offset"]] = float(age_offset)
        if time_override is not None:
            if identifiers["time_override"] in modifier:
                modifier[identifiers["time_override"]] = float(time_override)
        if use_time_override is not None:
            if identifiers["use_time_override"] in modifier:
                modifier[identifiers["use_time_override"]] = float(
                    use_time_override)
    return True


#: vertices of the icosphere instance used by the group.
INSTANCE_VERTS = 12


def realized_instances(obj, depsgraph):
    """Evaluate the group and return (centre, radius) of every instance.

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
        instances = []
        for start in range(0, len(mesh.vertices), INSTANCE_VERTS):
            chunk = mesh.vertices[start:start + INSTANCE_VERTS]
            if len(chunk) < INSTANCE_VERTS:
                break
            total = Vector((0.0, 0.0, 0.0))
            for vertex in chunk:
                total += vertex.co
            center = total / len(chunk)
            radius = max((vertex.co - center).length for vertex in chunk)
            instances.append((center, radius))
        evaluated.to_mesh_clear()
        return instances
    finally:
        group.nodes.remove(realize)
        group.links.new(source, socket)


def realized_centers(obj, depsgraph):
    """Evaluate the group and return the centre of every instance."""
    return [center for center, _radius in realized_instances(obj, depsgraph)]


def realized_energy(obj, depsgraph):
    """Evaluate the group and return the energy attribute of every instance.

    The energy is the attribute the material reads: it is the proof that the
    particle fades on its own curve and not only with its size.
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
        attribute = mesh.attributes.get("energy")
        values = []
        if attribute is not None:
            for index in range(len(attribute.data)):
                values.append(float(attribute.data[index].value))
        evaluated.to_mesh_clear()
        return values
    finally:
        group.nodes.remove(realize)
        group.links.new(source, socket)
