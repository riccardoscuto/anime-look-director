"""Small helpers shared by the celestial shader groups."""

import bpy


def rgba_sockets(mix):
    """Return (A, B, Result) colour sockets of a ShaderNodeMix."""
    inputs = [socket for socket in mix.inputs if socket.type == "RGBA"]
    outputs = [socket for socket in mix.outputs if socket.type == "RGBA"]
    return inputs[0], inputs[1], outputs[0]


class Graph:
    """Minimal node builder: sockets in, sockets out, explicit links."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links

    def node(self, kind, x=0, y=0, **props):
        node = self.nodes.new(kind)
        node.location = (x, y)
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def feed(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        else:
            socket.default_value = value

    def math(self, op, a, b=None, clamp=False, x=0, y=0):
        node = self.node("ShaderNodeMath", x, y)
        node.operation = op
        node.use_clamp = clamp
        self.feed(node.inputs[0], a)
        if b is not None:
            self.feed(node.inputs[1], b)
        return node.outputs[0]

    def vmath(self, op, a, b=None, scale=None, x=0, y=0):
        node = self.node("ShaderNodeVectorMath", x, y)
        node.operation = op
        self.feed(node.inputs[0], a)
        if b is not None:
            self.feed(node.inputs[1], b)
        if scale is not None:
            self.feed(node.inputs["Scale"], scale)
        return node.outputs["Value" if op == "DOT_PRODUCT" else "Vector"]

    def maprange(self, value, fmin, fmax, tmin=0.0, tmax=1.0, x=0, y=0):
        node = self.node("ShaderNodeMapRange", x, y)
        node.clamp = True
        node.interpolation_type = "SMOOTHSTEP"
        self.feed(node.inputs["From Min"], fmin)
        self.feed(node.inputs["From Max"], fmax)
        self.feed(node.inputs["To Min"], tmin)
        self.feed(node.inputs["To Max"], tmax)
        self.feed(node.inputs["Value"], value)
        return node.outputs["Result"]

    def mix(self, factor, a, b, blend="MIX", x=0, y=0):
        node = self.node("ShaderNodeMix", x, y, data_type="RGBA",
                         blend_type=blend)
        a_sock, b_sock, result = rgba_sockets(node)
        self.feed(node.inputs["Factor"], factor)
        self.feed(a_sock, a)
        self.feed(b_sock, b)
        return result

    def scale_color(self, color, factor, x=0, y=0):
        return self.vmath("SCALE", color, scale=factor, x=x, y=y)
