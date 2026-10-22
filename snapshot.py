"""Reversibility: the snapshot of the user state and the full removal.

The add-on modifies the world, the sun, the compositor, the render passes and
the materials of the scene. Before the first modification the original state
is saved, so that ``ald.remove_from_scene`` can restore the scene exactly as
the user left it.

The snapshot lives in the scene as a JSON string: it is explicit, serializable
and it survives a save.
"""

import json

import bpy

SNAPSHOT_KEY = "ald_snapshot"
MAINTENANCE_KEY = "ald_maintenance"

#: The internal properties of the add-on, removed after a successful restore.
INTERNAL_KEYS = (
    "ald_last_palette", "ald_effective_palette", "ald_effective_source",
    "ald_world_bg_color", "ald_world_bg_strength", "ald_fx_config",
    "ald_shadow_materials", "ald_fx_id", "ald_maintenance",
)


def is_maintenance(scene):
    """True while the add-on restores the scene: the handlers stay quiet."""
    return bool(scene.get(MAINTENANCE_KEY))


def _world_state(scene):
    world = scene.world
    if world is None:
        return {"has_world": False}
    state = {"has_world": True, "name": world.name,
             "use_nodes": world.use_nodes}
    if not world.use_nodes or world.node_tree is None:
        return state
    background = next((node for node in world.node_tree.nodes
                        if node.bl_idname == "ShaderNodeBackground"), None)
    if background is None:
        return state
    state["bg_color"] = list(background.inputs["Color"].default_value)
    state["bg_strength"] = float(background.inputs["Strength"].default_value)
    if background.inputs["Color"].is_linked:
        link = background.inputs["Color"].links[0]
        state["bg_link"] = {"node": link.from_node.name,
                            "output": link.from_socket.name}
    else:
        state["bg_link"] = None
    return state


def _sun_state(scene):
    sun = next((obj for obj in scene.objects
                 if obj.type == "LIGHT" and obj.data is not None
                 and obj.data.type == "SUN"), None)
    if sun is None:
        return {"exists": False}
    return {"exists": True, "name": sun.name, "energy": float(sun.data.energy),
            "color": list(sun.data.color),
            "rotation": [float(value) for value in sun.rotation_euler],
            "is_ald": bool(sun.get("ald_auto_sun"))}


def _compositor_state(scene):
    group = scene.compositing_node_group
    return {"group": group.name if group is not None else None,
            "use_compositing": bool(scene.render.use_compositing)}


def _view_layer_state(scene):
    states = []
    for view_layer in scene.view_layers:
        states.append({
            "name": view_layer.name,
            "use_pass_z": bool(view_layer.use_pass_z),
            "use_pass_emit": bool(view_layer.use_pass_emit),
            "use_pass_normal": bool(view_layer.use_pass_normal),
            "use_pass_combined": bool(view_layer.use_pass_combined),
        })
    return states


def ensure(scene):
    """Save the state of the scene before the first ALD modification."""
    if SNAPSHOT_KEY in scene:
        return snapshot(scene)
    data = {
        "world": _world_state(scene),
        "sun": _sun_state(scene),
        "compositor": _compositor_state(scene),
        "view_layer": _view_layer_state(scene),
    }
    scene[SNAPSHOT_KEY] = json.dumps(data)
    return data


def snapshot(scene):
    """The saved state, or an empty one."""
    raw = scene.get(SNAPSHOT_KEY)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def _restore_world(scene, state):
    world = scene.world
    if not state.get("has_world"):
        if world is not None:
            scene.world = None
        return
    if world is None:
        world = bpy.data.worlds.get(state.get("name", ""))
        if world is None:
            world = bpy.data.worlds.new(state.get("name", "World"))
        scene.world = world
    world.use_nodes = bool(state.get("use_nodes", True))
    if not world.use_nodes or world.node_tree is None:
        return
    background = next((node for node in world.node_tree.nodes
                        if node.bl_idname == "ShaderNodeBackground"), None)
    if background is None:
        return
    for link in list(background.inputs["Color"].links):
        world.node_tree.links.remove(link)
    link_state = state.get("bg_link")
    if link_state:
        source = world.node_tree.nodes.get(link_state.get("node", ""))
        if source is not None:
            socket = source.outputs.get(link_state.get("output", ""))
            if socket is not None:
                world.node_tree.links.new(socket,
                                          background.inputs["Color"])
    if "bg_color" in state:
        background.inputs["Color"].default_value = tuple(state["bg_color"])
    if "bg_strength" in state:
        background.inputs["Strength"].default_value = float(
            state["bg_strength"])


def _restore_sun(scene, state):
    sun = next((obj for obj in scene.objects
                 if obj.type == "LIGHT" and obj.data is not None
                 and obj.data.type == "SUN"), None)
    if not state.get("exists"):
        if sun is not None and sun.get("ald_auto_sun"):
            light = sun.data
            bpy.data.objects.remove(sun, do_unlink=True)
            if light is not None and light.users == 0:
                bpy.data.lights.remove(light)
        return
    if sun is None:
        name = state.get("name", "Sun")
        light = bpy.data.lights.get(name)
        if light is None:
            light = bpy.data.lights.new(name, type="SUN")
        sun = bpy.data.objects.new(name, light)
        scene.collection.objects.link(sun)
    sun.data.energy = float(state.get("energy", sun.data.energy))
    if "color" in state:
        sun.data.color = tuple(state["color"])
    if "rotation" in state:
        sun.rotation_euler = tuple(state["rotation"])
    if "is_ald" in state and not state["is_ald"]:
        if "ald_auto_sun" in sun:
            del sun["ald_auto_sun"]


def _restore_compositor(scene, state):
    name = state.get("group")
    group = bpy.data.node_groups.get(name) if name else None
    scene.compositing_node_group = group
    scene.render.use_compositing = bool(state.get("use_compositing", True))


def _restore_view_layer(scene, states):
    for state in states:
        view_layer = scene.view_layers.get(state.get("name", ""))
        if view_layer is None:
            continue
        view_layer.use_pass_z = bool(state.get("use_pass_z"))
        view_layer.use_pass_emit = bool(state.get("use_pass_emit"))
        view_layer.use_pass_normal = bool(state.get("use_pass_normal"))
        view_layer.use_pass_combined = bool(state.get("use_pass_combined", True))


def restore(scene):
    """Restore the state saved before the first ALD modification."""
    from . import fx, materials

    state = snapshot(scene)
    if not state:
        return False
    scene[MAINTENANCE_KEY] = True
    try:
        # The FX systems and the objects they own.
        fx.clear(scene)
        # The materials: the original base colour and emission come back.
        materials.clear_scene(scene)
        _restore_world(scene, state.get("world", {}))
        _restore_sun(scene, state.get("sun", {}))
        _restore_compositor(scene, state.get("compositor", {}))
        _restore_view_layer(scene, state.get("view_layer", []))
        # The internal properties are removed only after a successful restore.
        for key in INTERNAL_KEYS:
            if key in scene:
                del scene[key]
        if SNAPSHOT_KEY in scene:
            del scene[SNAPSHOT_KEY]
    finally:
        scene[MAINTENANCE_KEY] = False
    return True
