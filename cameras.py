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
_last_transforms = {}


def _transform_state(scene):
    sun = next((o for o in scene.objects
                if o.type == "LIGHT" and o.data is not None
                and o.data.type == "SUN"), None)
    camera = scene.camera
    sun_key = None
    if sun is not None and sun.data is not None:
        matrix = sun.matrix_world
        sun_key = (tuple(matrix.col[2][:3]), tuple(sun.data.color))
    cam_key = None
    if camera is not None and camera.data is not None:
        matrix = camera.matrix_world
        data = camera.data
        cam_key = (tuple(matrix.col[2][:3]), tuple(matrix.translation),
                   float(data.lens), float(data.shift_x), float(data.shift_y),
                   float(data.sensor_width))
    return sun_key, cam_key


def update_transforms(scene, force=False):
    """Push sun/camera transforms into world, materials and God Rays."""
    state = _transform_state(scene)
    if not force and _last_transforms.get(scene.name) == state:
        return False
    _last_transforms[scene.name] = state
    from . import palette, materials, compositor
    palette.update_sun_controls(scene)
    materials.update_sun(scene)
    compositor.update_god_rays(scene)
    palette.sync_sun_angles(scene)
    return True


def _on_depsgraph(scene, depsgraph=None):
    try:
        camera = scene.camera
        name = camera.name if camera is not None else ""
        override = camera_override(scene)
        state = (name, override)
        previous = _last_camera.get(scene.name)
        if previous != state:
            _last_camera[scene.name] = state
            if not (override is None
                    and (previous is None or previous[1] is None)):
                from . import look
                look.apply(scene, force=True)
    except Exception:
        pass
    try:
        update_transforms(scene)
    except Exception:
        pass


def register():
    bpy.utils.register_class(ALD_CameraSettings)
    bpy.types.Camera.ald = PointerProperty(type=ALD_CameraSettings)
    _last_camera.clear()
    _last_transforms.clear()
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)


def unregister():
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)
    _last_camera.clear()
    _last_transforms.clear()
    del bpy.types.Camera.ald
    bpy.utils.unregister_class(ALD_CameraSettings)
