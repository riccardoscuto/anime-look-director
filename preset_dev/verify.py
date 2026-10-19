"""Headless gate for Anime Look Director.

Run:
  blender -b --factory-startup --python-exit-code 1 --python preset_dev/verify.py
"""

import os
import sys
import tempfile

import bpy

MODULE = "anime_look_director"
ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(message):
    print("ALD GATE: FAIL -", message)
    raise SystemExit(1)


def enable_addon():
    if hasattr(bpy.types.Scene, "ald"):
        return
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
    except Exception:
        parent = os.path.dirname(ADDON_PATH)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import importlib
        importlib.import_module(MODULE).register()


def main():
    enable_addon()
    scene = bpy.context.scene
    if not hasattr(scene, "ald"):
        fail("settings not registered")

    sun_data = bpy.data.lights.new("ALD_GATE_SUN", "SUN")
    sun = bpy.data.objects.new("ALD_GATE_SUN", sun_data)
    scene.collection.objects.link(sun)

    try:
        result = bpy.ops.ald.build()
        if "FINISHED" not in result:
            fail("build operator did not finish")

        ng = scene.compositing_node_group
        if ng is None or ng.name != "ALD | Compositor Stack":
            fail("compositor group not assigned")
        types = {node.bl_idname for node in ng.nodes}
        for required in ("CompositorNodeRLayers", "CompositorNodeGlare",
                         "CompositorNodeKuwahara", "CompositorNodeLensdist",
                         "NodeGroupOutput"):
            if required not in types:
                fail("missing node " + required)
        if not scene.view_layers[0].use_pass_z:
            fail("depth pass not enabled")

        bpy.ops.ald.apply_palette()
        if scene.world is None:
            fail("palette did not create a world")

        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 64
        scene.render.resolution_y = 64
        scene.render.resolution_percentage = 100
        path = os.path.join(tempfile.gettempdir(), "ald_gate.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            fail("render not produced")

        bpy.ops.ald.remove()
        if scene.compositing_node_group is not None:
            fail("stack not removed")
    finally:
        bpy.data.objects.remove(sun, do_unlink=True)

    print("ALD GATE: PASS")


if __name__ == "__main__":
    main()
