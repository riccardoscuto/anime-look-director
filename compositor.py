"""Non-destructive anime compositor stack (Blender 5.1 node-group compositor)."""

import bpy

GROUP_NAME = "ALD | Compositor Stack"
SCENE_TAG = "ald_scene"

NODE_HALATION = "ALD | Halation"
NODE_KUWAHARA = "ALD | Kuwahara"
NODE_DEPTH_RANGE = "ALD | Depth Range"
NODE_LIGHT_WRAP_BLUR = "ALD | Light Wrap Blur"
NODE_LIGHT_WRAP_MASK = "ALD | Light Wrap Mask"
NODE_LIGHT_WRAP_EDGE = "ALD | Light Wrap Edge"
NODE_LIGHT_WRAP_OVER = "ALD | Light Wrap Over"
NODE_LENS = "ALD | Lens"
NODE_GOD_RAYS = "ALD | God Rays"
NODE_INK_EDGE = "ALD | Ink Edge"
NODE_INK_FACTOR = "ALD | Ink Factor"
NODE_INK_LINES = "ALD | Ink Lines"
NODE_INK_COLOR = "ALD | Ink Color"
NODE_INK_GAIN = "ALD | Ink Gain"
NODE_INK_NORMAL = "ALD | Normal Edge"
NODE_INK_NORMAL_GAIN = "ALD | Normal Gain"
NODE_HAZE_RANGE = "ALD | Haze Range"
NODE_HAZE_STRENGTH = "ALD | Haze Strength"
NODE_HAZE_COLOR = "ALD | Haze Color"
NODE_HAZE_MIX = "ALD | Aerial Haze"


def _is_stack(ng):
    return (ng.bl_idname == "CompositorNodeTree"
            and (ng.get(SCENE_TAG) is not None
                 or ng.name == GROUP_NAME
                 or ng.name.startswith(GROUP_NAME + " | ")))


def _group_for_scene(scene, create=True):
    """One stack per scene; the first scene keeps the plain group name."""
    for ng in bpy.data.node_groups:
        if (ng.bl_idname == "CompositorNodeTree"
                and ng.get(SCENE_TAG) == scene.name):
            return ng

    legacy = bpy.data.node_groups.get(GROUP_NAME)
    if (legacy is not None and legacy.bl_idname == "CompositorNodeTree"
            and legacy.get(SCENE_TAG) is None):
        # Claim a stack created before per-scene groups.
        legacy[SCENE_TAG] = scene.name
        return legacy

    if not create:
        return None
    name = GROUP_NAME
    if bpy.data.node_groups.get(name) is not None:
        name = GROUP_NAME + " | " + scene.name
    ng = bpy.data.node_groups.new(name, "CompositorNodeTree")
    ng[SCENE_TAG] = scene.name
    return ng


def _mix_sockets(mix):
    """Pick the RGBA A/B/Result sockets of a ShaderNodeMix."""
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


def _smooth(node):
    try:
        items = [item.identifier for item in
                 node.bl_rna.properties["interpolation_type"].enum_items]
        if "SMOOTHSTEP" in items:
            node.interpolation_type = "SMOOTHSTEP"
    except Exception:
        pass


def _silhouette_mask(nodes, links, render_layers, clip_end):
    """Mask of rendered geometry, independent of world alpha.

    With an opaque world, render alpha is 1 everywhere, so the depth pass is
    used to separate geometry from the background. EEVEE writes clip_end for
    the world, Cycles writes ~1e10: both are above any visible geometry.
    """
    alpha = render_layers.outputs["Alpha"]
    depth = render_layers.outputs.get("Depth")
    if depth is None:
        return alpha
    near = nodes.new("ShaderNodeMath")
    near.location = (-1240, 300)
    near.operation = "LESS_THAN"
    near.inputs[1].default_value = max(1.0, clip_end)
    links.new(depth, near.inputs[0])
    combine = nodes.new("ShaderNodeMath")
    combine.location = (-1060, 300)
    combine.operation = "MULTIPLY"
    combine.use_clamp = True
    links.new(near.outputs[0], combine.inputs[0])
    links.new(alpha, combine.inputs[1])
    return combine.outputs[0]


def _depth_edges(nodes, links, render_layers, geometry, band_size,
                 edge_size=4.0, blur_name=None, y_offset=0.0):
    """Depth-discontinuity mask, optionally widened into an edge band."""
    before = {node.name for node in nodes}
    depth = render_layers.outputs.get("Depth")
    if depth is None:
        return None

    scale = 100.0
    normalized = nodes.new("ShaderNodeMath")
    normalized.location = (-1220, 700)
    normalized.operation = "DIVIDE"
    normalized.inputs[1].default_value = scale
    links.new(depth, normalized.inputs[0])

    image = nodes.new("ShaderNodeMix")
    image.location = (-1030, 700)
    image.data_type = "RGBA"
    image.blend_type = "MIX"
    a_sock, b_sock, result_sock = _mix_sockets(image)
    a_sock.default_value = (0.0, 0.0, 0.0, 1.0)
    b_sock.default_value = (1.0, 1.0, 1.0, 1.0)
    links.new(normalized.outputs[0], image.inputs["Factor"])

    blur = nodes.new("CompositorNodeBlur")
    blur.location = (-840, 700)
    if blur_name is not None:
        blur.name = blur_name
    blur.inputs["Type"].default_value = "Gaussian"
    blur.inputs["Size"].default_value = (edge_size, edge_size)
    links.new(result_sock, blur.inputs["Image"])

    separate = nodes.new("CompositorNodeSeparateColor")
    separate.location = (-650, 740)
    links.new(blur.outputs["Image"], separate.inputs["Image"])

    diff = nodes.new("ShaderNodeMath")
    diff.location = (-470, 740)
    diff.operation = "SUBTRACT"
    links.new(normalized.outputs[0], diff.inputs[0])
    links.new(separate.outputs["Red"], diff.inputs[1])

    absolute = nodes.new("ShaderNodeMath")
    absolute.location = (-290, 740)
    absolute.operation = "ABSOLUTE"
    links.new(diff.outputs[0], absolute.inputs[0])

    meters = nodes.new("ShaderNodeMath")
    meters.location = (-110, 740)
    meters.operation = "MULTIPLY"
    meters.inputs[1].default_value = scale
    links.new(absolute.outputs[0], meters.inputs[0])

    threshold = nodes.new("ShaderNodeMath")
    threshold.location = (70, 740)
    threshold.operation = "SUBTRACT"
    threshold.use_clamp = True
    threshold.inputs[1].default_value = 0.05
    links.new(meters.outputs[0], threshold.inputs[0])

    if band_size > 0.0:
        edge_image = nodes.new("ShaderNodeMix")
        edge_image.location = (250, 740)
        edge_image.data_type = "RGBA"
        edge_image.blend_type = "MIX"
        a_sock, b_sock, result_sock = _mix_sockets(edge_image)
        a_sock.default_value = (0.0, 0.0, 0.0, 1.0)
        b_sock.default_value = (1.0, 1.0, 1.0, 1.0)
        links.new(threshold.outputs[0], edge_image.inputs["Factor"])

        band = nodes.new("CompositorNodeBlur")
        band.location = (440, 740)
        band.name = NODE_LIGHT_WRAP_EDGE
        band.inputs["Type"].default_value = "Gaussian"
        band.inputs["Size"].default_value = (band_size, band_size)
        links.new(result_sock, band.inputs["Image"])

        band_separate = nodes.new("CompositorNodeSeparateColor")
        band_separate.location = (630, 780)
        links.new(band.outputs["Image"], band_separate.inputs["Image"])
        edge_value = band_separate.outputs["Red"]
    else:
        gain = nodes.new("ShaderNodeMath")
        gain.location = (250, 740)
        gain.name = NODE_INK_GAIN
        gain.operation = "MULTIPLY"
        gain.use_clamp = True
        gain.inputs[1].default_value = 8.0
        links.new(threshold.outputs[0], gain.inputs[0])
        edge_value = gain.outputs[0]

    clipped = nodes.new("ShaderNodeMath")
    clipped.location = (820, 780)
    clipped.operation = "MULTIPLY"
    clipped.use_clamp = True
    links.new(edge_value, clipped.inputs[0])
    links.new(geometry, clipped.inputs[1])
    if y_offset:
        for node in nodes:
            if node.name not in before:
                node.location.y += y_offset
    return clipped.outputs[0]


def _light_wrap(nodes, links, image, render_layers, settings, clip_end,
                geometry):
    """Add blurred scene light inside the silhouette's edge band."""
    size = max(1.0, settings.light_wrap_size)
    strength = settings.light_wrap_strength

    light = nodes.new("CompositorNodeBlur")
    light.location = (-500, -220)
    light.name = NODE_LIGHT_WRAP_BLUR
    light.inputs["Type"].default_value = "Gaussian"
    light.inputs["Size"].default_value = (size, size)
    light.inputs["Extend Bounds"].default_value = True
    links.new(image, light.inputs["Image"])

    # Encode the float mask as a grayscale image: the Blur node is reliable on
    # RGB, while alpha handling differs between engines.
    white = nodes.new("ShaderNodeMix")
    white.location = (-860, 480)
    white.data_type = "RGBA"
    white.blend_type = "MIX"
    a_sock, b_sock, result_sock = _mix_sockets(white)
    a_sock.default_value = (0.0, 0.0, 0.0, 1.0)
    b_sock.default_value = (1.0, 1.0, 1.0, 1.0)
    links.new(geometry, white.inputs["Factor"])

    mask = nodes.new("CompositorNodeBlur")
    mask.location = (-650, 480)
    mask.name = NODE_LIGHT_WRAP_MASK
    mask.inputs["Type"].default_value = "Gaussian"
    mask.inputs["Size"].default_value = (size, size)
    links.new(result_sock, mask.inputs["Image"])

    separate = nodes.new("CompositorNodeSeparateColor")
    separate.location = (-460, 520)
    links.new(mask.outputs["Image"], separate.inputs["Image"])

    # mask - blurred_mask: positive inside the silhouette, clipped outside.
    rim = nodes.new("ShaderNodeMath")
    rim.location = (-280, 540)
    rim.operation = "SUBTRACT"
    rim.use_clamp = True
    links.new(geometry, rim.inputs[0])
    links.new(separate.outputs["Red"], rim.inputs[1])

    edge_mask = _depth_edges(nodes, links, render_layers, geometry, size)
    if edge_mask is not None:
        combined = nodes.new("ShaderNodeMath")
        combined.location = (-100, 540)
        combined.operation = "MAXIMUM"
        combined.use_clamp = True
        links.new(rim.outputs[0], combined.inputs[0])
        links.new(edge_mask, combined.inputs[1])
        rim_value = combined.outputs[0]
    else:
        rim_value = rim.outputs[0]

    boost = nodes.new("ShaderNodeMath")
    boost.location = (80, 540)
    boost.operation = "MULTIPLY"
    boost.use_clamp = True
    boost.inputs[1].default_value = 1.6
    links.new(rim_value, boost.inputs[0])

    wrapped = nodes.new("CompositorNodeSetAlpha")
    wrapped.location = (-80, -220)
    wrapped.inputs["Type"].default_value = "Replace Alpha"
    links.new(light.outputs["Image"], wrapped.inputs["Image"])
    links.new(boost.outputs[0], wrapped.inputs["Alpha"])

    over = nodes.new("CompositorNodeAlphaOver")
    over.location = (160, 0)
    over.name = NODE_LIGHT_WRAP_OVER
    over.inputs["Factor"].default_value = strength
    over.inputs["Straight Alpha"].default_value = True
    links.new(image, over.inputs["Background"])
    links.new(wrapped.outputs["Image"], over.inputs["Foreground"])
    return over.outputs["Image"]


def _sun_screen_position(scene):
    """Project the sun direction to normalized screen coordinates (0..1)."""
    camera = scene.camera
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    if camera is None or sun is None:
        return None

    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view

    direction = sun.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    point = camera.matrix_world.translation - direction * 1000.0
    co = world_to_camera_view(scene, camera, point)
    if co.z <= 0.0:
        return None
    return (max(0.0, min(1.0, co.x)), max(0.0, min(1.0, co.y)))


def update_god_rays(scene):
    """Follow the sun/camera without rebuilding the whole stack."""
    ng = scene.compositing_node_group
    if (ng is None or not _is_stack(ng)
            or ng.get(SCENE_TAG) != scene.name):
        return
    beams = next((n for n in ng.nodes
                  if n.bl_idname == "CompositorNodeGlare"
                  and n.inputs["Type"].default_value == "Sun Beams"), None)
    if beams is None:
        return

    settings = getattr(scene, "ald", None)
    strength = settings.god_rays_strength if settings is not None else 0.35
    position = _sun_screen_position(scene)
    if position is None:
        beams.inputs["Strength"].default_value = 0.0
        return
    beams.inputs["Sun Position"].default_value = position
    beams.inputs["Strength"].default_value = strength


def update_params(scene):
    """Update existing node values without rebuilding the stack."""
    settings = getattr(scene, "ald", None)
    ng = scene.compositing_node_group
    if (settings is None or ng is None or not _is_stack(ng)
            or ng.get(SCENE_TAG) != scene.name):
        return
    nodes = ng.nodes

    node = nodes.get(NODE_HALATION)
    if node is not None:
        node.inputs["Strength"].default_value = settings.halation_strength

    node = nodes.get(NODE_KUWAHARA)
    if node is not None:
        node.inputs["Size"].default_value = settings.kuwahara_size

    node = nodes.get(NODE_DEPTH_RANGE)
    if node is not None:
        node.inputs["From Min"].default_value = settings.depth_near
        node.inputs["From Max"].default_value = max(
            settings.depth_far, settings.depth_near + 0.001)

    node = nodes.get(NODE_LENS)
    if node is not None and "Dispersion" in node.inputs:
        node.inputs["Dispersion"].default_value = settings.dispersion_amount

    size = (settings.light_wrap_size, settings.light_wrap_size)
    for name in (NODE_LIGHT_WRAP_BLUR, NODE_LIGHT_WRAP_MASK,
                 NODE_LIGHT_WRAP_EDGE):
        node = nodes.get(name)
        if node is not None:
            node.inputs["Size"].default_value = size

    node = nodes.get(NODE_LIGHT_WRAP_OVER)
    if node is not None:
        node.inputs["Factor"].default_value = settings.light_wrap_strength

    node = nodes.get(NODE_GOD_RAYS)
    if node is not None:
        node.inputs["Size"].default_value = settings.god_rays_size
        node.inputs["Strength"].default_value = settings.god_rays_strength
        update_god_rays(scene)

    from . import palette as palette_module
    palette_key = scene.get("ald_effective_palette", settings.palette)
    tint = _glare_color(scene, settings, palette_module, palette_key)
    node = nodes.get(NODE_HALATION)
    if node is not None and "Tint" in node.inputs:
        node.inputs["Tint"].default_value = tint
    node = nodes.get(NODE_GOD_RAYS)
    if node is not None and "Tint" in node.inputs:
        node.inputs["Tint"].default_value = tint
    node = nodes.get(NODE_INK_COLOR)
    if node is not None:
        ink = tuple(component * 0.25 for component in
                    palette_module.shadow_tint_for(scene))
        node.outputs[0].default_value = (*ink, 1.0)

    node = nodes.get(NODE_INK_EDGE)
    if node is not None:
        node.inputs["Size"].default_value = (settings.ink_size,
                                             settings.ink_size)
    node = nodes.get(NODE_INK_FACTOR)
    if node is not None:
        node.inputs[1].default_value = settings.ink_strength
    node = nodes.get(NODE_INK_NORMAL_GAIN)
    if node is not None:
        node.inputs[1].default_value = settings.ink_normal_sensitivity

    node = nodes.get(NODE_HAZE_RANGE)
    if node is not None:
        node.inputs["From Min"].default_value = settings.depth_near
        node.inputs["From Max"].default_value = max(
            settings.depth_far, settings.depth_near + 0.001)
    node = nodes.get(NODE_HAZE_STRENGTH)
    if node is not None:
        node.inputs[1].default_value = settings.haze_strength
    node = nodes.get(NODE_HAZE_COLOR)
    if node is not None:
        key = scene.get("ald_effective_palette", settings.palette)
        p = palette_module.effective(scene, key)
        haze = tuple(0.65 * h + 0.35 * s for h, s in
                     zip(p["horizon_color"], p["shadow_tint"]))
        node.outputs[0].default_value = (*haze, 1.0)


def _on_frame_change(scene, *_args):
    try:
        update_god_rays(scene)
    except Exception:
        pass


def register():
    if _on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame_change)


def unregister():
    if _on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame_change)


def _aerial_haze(nodes, links, image, render_layers, settings, geometry,
                 haze_color):
    """Tint distant geometry toward the horizon color."""
    depth = render_layers.outputs.get("Depth")
    if depth is None:
        return image
    depth_range = nodes.new("ShaderNodeMapRange")
    depth_range.location = (-700, -1500)
    depth_range.name = NODE_HAZE_RANGE
    depth_range.clamp = True
    depth_range.inputs["From Min"].default_value = settings.depth_near
    depth_range.inputs["From Max"].default_value = max(
        settings.depth_far, settings.depth_near + 0.001)
    depth_range.inputs["To Min"].default_value = 0.0
    depth_range.inputs["To Max"].default_value = 1.0
    links.new(depth, depth_range.inputs["Value"])

    mask = nodes.new("ShaderNodeMath")
    mask.location = (-500, -1500)
    mask.operation = "MULTIPLY"
    mask.use_clamp = True
    links.new(depth_range.outputs["Result"], mask.inputs[0])
    links.new(geometry, mask.inputs[1])

    strength = nodes.new("ShaderNodeMath")
    strength.location = (-300, -1500)
    strength.name = NODE_HAZE_STRENGTH
    strength.operation = "MULTIPLY"
    strength.use_clamp = True
    links.new(mask.outputs[0], strength.inputs[0])
    strength.inputs[1].default_value = settings.haze_strength

    color = nodes.new("CompositorNodeRGB")
    color.location = (-300, -1660)
    color.name = NODE_HAZE_COLOR
    color.outputs[0].default_value = (*haze_color, 1.0)

    mix = nodes.new("ShaderNodeMix")
    mix.location = (-80, -1500)
    mix.name = NODE_HAZE_MIX
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    a_sock, b_sock, result_sock = _mix_sockets(mix)
    links.new(image, a_sock)
    links.new(color.outputs[0], b_sock)
    links.new(strength.outputs[0], mix.inputs["Factor"])
    return result_sock


def _normal_edges(nodes, links, render_layers, geometry, sensitivity):
    """Normal-discontinuity mask for creases and hard internal corners."""
    normal = render_layers.outputs.get("Normal")
    if normal is None:
        return None
    blur = nodes.new("CompositorNodeBlur")
    blur.location = (-700, -2400)
    blur.inputs["Type"].default_value = "Gaussian"
    blur.inputs["Size"].default_value = (1.5, 1.5)
    links.new(normal, blur.inputs["Image"])

    difference = nodes.new("ShaderNodeVectorMath")
    difference.location = (-500, -2400)
    difference.operation = "SUBTRACT"
    links.new(normal, difference.inputs[0])
    links.new(blur.outputs["Image"], difference.inputs[1])

    length = nodes.new("ShaderNodeVectorMath")
    length.location = (-300, -2400)
    length.operation = "LENGTH"
    links.new(difference.outputs["Vector"], length.inputs[0])

    curve = nodes.new("ShaderNodeMapRange")
    curve.location = (-100, -2400)
    curve.clamp = True
    _smooth(curve)
    curve.inputs["From Min"].default_value = 0.01
    curve.inputs["From Max"].default_value = 0.14
    curve.inputs["To Min"].default_value = 0.0
    curve.inputs["To Max"].default_value = 1.0
    links.new(length.outputs["Value"], curve.inputs["Value"])

    gain = nodes.new("ShaderNodeMath")
    gain.location = (100, -2400)
    gain.name = NODE_INK_NORMAL_GAIN
    gain.operation = "MULTIPLY"
    gain.use_clamp = True
    links.new(curve.outputs["Result"], gain.inputs[0])
    gain.inputs[1].default_value = sensitivity

    mask = nodes.new("ShaderNodeMath")
    mask.location = (300, -2400)
    mask.operation = "MULTIPLY"
    mask.use_clamp = True
    links.new(gain.outputs[0], mask.inputs[0])
    links.new(geometry, mask.inputs[1])
    mask.name = NODE_INK_NORMAL
    return mask.outputs[0]


def _ink_lines(nodes, links, image, render_layers, settings, clip_end,
               geometry, ink_color):
    """Thin dark depth edges over the composited image."""
    edge = _depth_edges(nodes, links, render_layers, geometry, 0.0,
                        settings.ink_size, NODE_INK_EDGE,
                        y_offset=-1600.0)
    if edge is None:
        return image

    normal_edge = _normal_edges(nodes, links, render_layers, geometry,
                                settings.ink_normal_sensitivity)
    if normal_edge is not None:
        combined = nodes.new("ShaderNodeMath")
        combined.location = (-460, -1600)
        combined.operation = "MAXIMUM"
        combined.use_clamp = True
        links.new(edge, combined.inputs[0])
        links.new(normal_edge, combined.inputs[1])
        edge = combined.outputs[0]

    factor = nodes.new("ShaderNodeMath")
    factor.location = (-260, -1040)
    factor.name = NODE_INK_FACTOR
    factor.operation = "MULTIPLY"
    factor.use_clamp = True
    links.new(edge, factor.inputs[0])
    factor.inputs[1].default_value = settings.ink_strength

    color = nodes.new("CompositorNodeRGB")
    color.location = (-260, -1200)
    color.name = NODE_INK_COLOR
    color.outputs[0].default_value = (*ink_color, 1.0)

    mix = nodes.new("ShaderNodeMix")
    mix.location = (0, -1040)
    mix.name = NODE_INK_LINES
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    a_sock, b_sock, result_sock = _mix_sockets(mix)
    links.new(image, a_sock)
    links.new(color.outputs[0], b_sock)
    links.new(factor.outputs[0], mix.inputs["Factor"])
    return result_sock


def _glare_color(scene, settings, palette_module, key):
    if settings is not None and settings.custom_colors:
        return (*settings.custom_sun, 1.0)
    return palette_module.glare_tint(key)


def build(scene):
    """Create or refresh the stack and assign it to the scene."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        raise RuntimeError("Anime Look Director settings are not registered")

    for layer in scene.view_layers:
        layer.use_pass_z = True
        if settings.ink_lines:
            layer.use_pass_normal = True

    clip_end = 1000.0
    if scene.camera is not None and scene.camera.data is not None:
        clip_end = float(scene.camera.data.clip_end)

    ng = _group_for_scene(scene)
    ng[SCENE_TAG] = scene.name
    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    outputs = [item for item in ng.interface.items_tree
               if getattr(item, "in_out", "") == "OUTPUT"]
    if not outputs:
        ng.interface.new_socket(name="Image", in_out="OUTPUT",
                                socket_type="NodeSocketColor")

    layer_name = scene.view_layers[0].name
    rl = nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    rl.layer = layer_name
    rl.location = (-1500, 0)
    current = rl.outputs["Image"]
    depth = rl.outputs.get("Depth")

    from . import palette as palette_module
    palette_key = scene.get("ald_effective_palette", settings.palette)

    if settings.halation:
        glare = nodes.new("CompositorNodeGlare")
        glare.location = (-1250, 0)
        glare.name = NODE_HALATION
        glare.inputs["Type"].default_value = "Bloom"
        glare.inputs["Threshold"].default_value = 0.9
        glare.inputs["Strength"].default_value = settings.halation_strength
        if "Size" in glare.inputs:
            glare.inputs["Size"].default_value = 0.6
        if "Saturation" in glare.inputs:
            glare.inputs["Saturation"].default_value = 1.1
        if "Tint" in glare.inputs:
            glare.inputs["Tint"].default_value = _glare_color(
                scene, settings, palette_module, palette_key)
        links.new(current, glare.inputs["Image"])
        current = glare.outputs["Image"]

    if settings.god_rays:
        position = _sun_screen_position(scene)
        beams = nodes.new("CompositorNodeGlare")
        beams.location = (-1150, 220)
        beams.name = NODE_GOD_RAYS
        beams.inputs["Type"].default_value = "Sun Beams"
        beams.inputs["Threshold"].default_value = 3.5
        beams.inputs["Strength"].default_value = (
            settings.god_rays_strength if position is not None else 0.0)
        beams.inputs["Size"].default_value = settings.god_rays_size
        beams.inputs["Iterations"].default_value = 6
        beams.inputs["Fade"].default_value = 0.95
        beams.inputs["Color Modulation"].default_value = 0.15
        beams.inputs["Saturation"].default_value = 1.0
        if "Tint" in beams.inputs:
            beams.inputs["Tint"].default_value = _glare_color(
                scene, settings, palette_module, palette_key)
        beams.inputs["Sun Position"].default_value = (
            position if position is not None else (0.5, 0.5))
        links.new(current, beams.inputs["Image"])
        current = beams.outputs["Image"]

    if (settings.painterly or settings.light_wrap or settings.ink_lines
            or settings.aerial_haze):
        geometry = _silhouette_mask(nodes, links, rl, clip_end)
    else:
        geometry = None

    if settings.painterly:
        kuwahara = nodes.new("CompositorNodeKuwahara")
        kuwahara.location = (-1000, -220)
        kuwahara.name = NODE_KUWAHARA
        kuwahara.inputs["Type"].default_value = "Anisotropic"
        kuwahara.inputs["Size"].default_value = settings.kuwahara_size
        if "Sharpness" in kuwahara.inputs:
            kuwahara.inputs["Sharpness"].default_value = 0.5
        links.new(current, kuwahara.inputs["Image"])

        mix = nodes.new("ShaderNodeMix")
        mix.location = (-760, 0)
        mix.data_type = "RGBA"
        a_sock, b_sock, result_sock = _mix_sockets(mix)
        if a_sock is None or b_sock is None or result_sock is None:
            raise RuntimeError("Could not resolve ShaderNodeMix RGBA sockets")
        links.new(current, a_sock)
        links.new(kuwahara.outputs["Image"], b_sock)
        factor = mix.inputs[0]
        if depth is not None:
            depth_range = nodes.new("ShaderNodeMapRange")
            depth_range.location = (-1000, -500)
            depth_range.name = NODE_DEPTH_RANGE
            depth_range.clamp = True
            depth_range.inputs["From Min"].default_value = settings.depth_near
            depth_range.inputs["From Max"].default_value = max(
                settings.depth_far, settings.depth_near + 0.001)
            depth_range.inputs["To Min"].default_value = 0.0
            depth_range.inputs["To Max"].default_value = 1.0
            links.new(depth, depth_range.inputs["Value"])
            if geometry is not None:
                kuwahara_factor = nodes.new("ShaderNodeMath")
                kuwahara_factor.location = (-880, -500)
                kuwahara_factor.name = "ALD | Kuwahara Geometry"
                kuwahara_factor.operation = "MULTIPLY"
                kuwahara_factor.use_clamp = True
                links.new(depth_range.outputs["Result"],
                          kuwahara_factor.inputs[0])
                links.new(geometry, kuwahara_factor.inputs[1])
                links.new(kuwahara_factor.outputs[0], factor)
            else:
                links.new(depth_range.outputs["Result"], factor)
        else:
            factor.default_value = 1.0
        current = result_sock

    if settings.light_wrap:
        current = _light_wrap(nodes, links, current, rl, settings, clip_end,
                              geometry)

    if settings.aerial_haze:
        key = scene.get("ald_effective_palette", settings.palette)
        p = palette_module.effective(scene, key)
        haze = tuple(0.65 * h + 0.35 * s for h, s in
                     zip(p["horizon_color"], p["shadow_tint"]))
        current = _aerial_haze(nodes, links, current, rl, settings,
                               geometry, haze)

    if settings.ink_lines:
        ink_color = tuple(component * 0.25 for component in
                          palette_module.shadow_tint_for(scene))
        current = _ink_lines(nodes, links, current, rl, settings, clip_end,
                             geometry, ink_color)

    if settings.dispersion:
        lens = nodes.new("CompositorNodeLensdist")
        lens.location = (420, 0)
        lens.name = NODE_LENS
        if "Dispersion" in lens.inputs:
            lens.inputs["Dispersion"].default_value = settings.dispersion_amount
        links.new(current, lens.inputs["Image"])
        current = lens.outputs["Image"]

    output = nodes.new("NodeGroupOutput")
    output.location = (680, 0)
    links.new(current, output.inputs[0])

    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    return ng


def remove(scene):
    """Unassign the scene's stack and delete it if unused by other scenes."""
    ng = scene.compositing_node_group
    if ng is None:
        return
    scene.compositing_node_group = None
    if not _is_stack(ng):
        return
    if any(other.compositing_node_group == ng for other in bpy.data.scenes):
        return
    bpy.data.node_groups.remove(ng)
