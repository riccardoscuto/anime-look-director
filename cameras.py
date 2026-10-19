"""Per-camera palette overrides."""

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty

from .properties import PALETTES


def _on_camera(self, context):
    try:
        from . import look
        if context.scene is not None:
            look.apply(context.scene, force=True)
    except Exception:
        pass


class ALD_CameraSettings(bpy.types.PropertyGroup):
    override: BoolProperty(
        name="Palette Override",
        default=False,
        description="Use a camera-specific atmosphere",
        update=_on_camera,
    )
    palette: EnumProperty(
        name="Atmosphere",
        description="Palette used while this camera is active",
        items=PALETTES,
        default="GOLDEN_HOUR",
        update=_on_camera,
    )


def camera_override(scene):
    camera = scene.camera
    if camera is None or camera.data is None:
        return None
    settings = getattr(camera.data, "ald", None)
    if settings is not None and settings.override:
        return settings.palette
    return None


_last_camera = {}


def _on_depsgraph(scene, depsgraph=None):
    camera = scene.camera
    name = camera.name if camera is not None else ""
    override = camera_override(scene)
    state = (name, override)
    previous = _last_camera.get(scene.name)
    if previous == state:
        return
    _last_camera[scene.name] = state
    if override is None and (previous is None or previous[1] is None):
        return
    try:
        from . import look
        look.apply(scene, force=True)
    except Exception:
        pass


def register():
    bpy.utils.register_class(ALD_CameraSettings)
    bpy.types.Camera.ald = PointerProperty(type=ALD_CameraSettings)
    _last_camera.clear()
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)


def unregister():
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)
    _last_camera.clear()
    del bpy.types.Camera.ald
    bpy.utils.unregister_class(ALD_CameraSettings)
