"""Non-destructive anime compositor stack (Blender 5.1 node-group compositor)."""

import bpy

GROUP_NAME = "ALD | Compositor Stack"


def _group(create=True):
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if ng is not None and ng.bl_idname != "CompositorNodeTree":
        bpy.data.node_groups.remove(ng)
        ng = None
    if ng is None and create:
        ng = bpy.data.node_groups.new(GROUP_NAME, "CompositorNodeTree")
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


def _silhouette_mask(nodes, links, render_layers):
    """Mask of rendered geometry, independent of world alpha.

    With an opaque world, render alpha is 1 everywhere, so the depth pass is
    used to separate geometry from the background.
    """
    alpha = render_layers.outputs["Alpha"]
    depth = render_layers.outputs.get("Depth")
    if depth is None:
        return alpha
    near = nodes.new("ShaderNodeMath")
    near.location = (-1240, 300)
    near.operation = "LESS_THAN"
    near.inputs[1].default_value = 1.0e6
    links.new(depth, near.inputs[0])
    combine = nodes.new("ShaderNodeMath")
    combine.location = (-1060, 300)
    combine.operation = "MULTIPLY"
    combine.use_clamp = True
    links.new(near.outputs[0], combine.inputs[0])
    links.new(alpha, combine.inputs[1])
    return combine.outputs[0]


def _light_wrap(nodes, links, image, render_layers, settings):
    """Add blurred scene light inside the silhouette's edge band."""
    size = max(1.0, settings.light_wrap_size)
    strength = settings.light_wrap_strength
    mask_value = _silhouette_mask(nodes, links, render_layers)

    light = nodes.new("CompositorNodeBlur")
    light.location = (-500, -220)
    light.inputs["Type"].default_value = "Gaussian"
    light.inputs["Size"].default_value = (size, size)
    light.inputs["Extend Bounds"].default_value = True
    links.new(image, light.inputs["Image"])

    # White image carrying the silhouette, blurred to widen the edge.
    white = nodes.new("CompositorNodeRGB")
    white.location = (-1240, 480)
    white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)

    set_alpha = nodes.new("CompositorNodeSetAlpha")
    set_alpha.location = (-1050, 480)
    set_alpha.inputs["Type"].default_value = "Replace Alpha"
    links.new(white.outputs[0], set_alpha.inputs["Image"])
    links.new(mask_value, set_alpha.inputs["Alpha"])

    mask = nodes.new("CompositorNodeBlur")
    mask.location = (-860, 480)
    mask.inputs["Type"].default_value = "Gaussian"
    mask.inputs["Size"].default_value = (size, size)
    links.new(set_alpha.outputs["Image"], mask.inputs["Image"])

    separate = nodes.new("CompositorNodeSeparateColor")
    separate.location = (-670, 520)
    links.new(mask.outputs["Image"], separate.inputs["Image"])

    # mask - blurred_mask: positive inside the silhouette, clipped outside.
    rim = nodes.new("ShaderNodeMath")
    rim.location = (-480, 540)
    rim.operation = "SUBTRACT"
    rim.use_clamp = True
    links.new(mask_value, rim.inputs[0])
    links.new(separate.outputs["Alpha"], rim.inputs[1])

    boost = nodes.new("ShaderNodeMath")
    boost.location = (-290, 540)
    boost.operation = "MULTIPLY"
    boost.use_clamp = True
    boost.inputs[1].default_value = 1.6
    links.new(rim.outputs[0], boost.inputs[0])

    wrapped = nodes.new("CompositorNodeSetAlpha")
    wrapped.location = (-80, -220)
    wrapped.inputs["Type"].default_value = "Replace Alpha"
    links.new(light.outputs["Image"], wrapped.inputs["Image"])
    links.new(boost.outputs[0], wrapped.inputs["Alpha"])

    over = nodes.new("CompositorNodeAlphaOver")
    over.location = (160, 0)
    over.inputs["Factor"].default_value = strength
    links.new(image, over.inputs["Background"])
    links.new(wrapped.outputs["Image"], over.inputs["Foreground"])
    return over.outputs["Image"]


def build(scene):
    """Create or refresh the stack and assign it to the scene."""
    settings = getattr(scene, "ald", None)
    if settings is None:
        raise RuntimeError("Anime Look Director settings are not registered")

    for layer in scene.view_layers:
        layer.use_pass_z = True

    ng = _group()
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

    if settings.halation:
        from . import palette as palette_module
        glare = nodes.new("CompositorNodeGlare")
        glare.location = (-1250, 0)
        glare.inputs["Type"].default_value = "Bloom"
        glare.inputs["Threshold"].default_value = 0.9
        glare.inputs["Strength"].default_value = settings.halation_strength
        if "Size" in glare.inputs:
            glare.inputs["Size"].default_value = 0.6
        if "Saturation" in glare.inputs:
            glare.inputs["Saturation"].default_value = 1.1
        if "Tint" in glare.inputs:
            glare.inputs["Tint"].default_value = palette_module.glare_tint(
                settings.palette)
        links.new(current, glare.inputs["Image"])
        current = glare.outputs["Image"]

    if settings.painterly:
        kuwahara = nodes.new("CompositorNodeKuwahara")
        kuwahara.location = (-1000, -220)
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
            depth_range.clamp = True
            depth_range.inputs["From Min"].default_value = settings.depth_near
            depth_range.inputs["From Max"].default_value = max(
                settings.depth_far, settings.depth_near + 0.001)
            depth_range.inputs["To Min"].default_value = 0.0
            depth_range.inputs["To Max"].default_value = 1.0
            links.new(depth, depth_range.inputs["Value"])
            links.new(depth_range.outputs["Result"], factor)
        else:
            factor.default_value = 1.0
        current = result_sock

    if settings.light_wrap:
        current = _light_wrap(nodes, links, current, rl, settings)

    if settings.dispersion:
        lens = nodes.new("CompositorNodeLensdist")
        lens.location = (420, 0)
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
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if scene.compositing_node_group is ng:
        scene.compositing_node_group = None
    if ng is not None:
        bpy.data.node_groups.remove(ng)
