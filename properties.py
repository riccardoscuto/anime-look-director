import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, PointerProperty)

PALETTES = [
    ("GOLDEN_HOUR", "Shinkai Golden Hour", "Warm backlight, orange halation"),
    ("SUMMER_NOON", "Ghibli Summer Noon", "Bright sky, clean high-key light"),
    ("RAINY_TOKYO", "Rainy Tokyo Night", "Cool rain-soaked night"),
    ("NEON_NIGHT", "Cyberpunk Neon", "Magenta and cyan artificial light"),
    ("SAKURA_SPRING", "Sakura Spring", "Soft pink skies and warm spring light"),
    ("TWILIGHT_DUSK", "Twilight Dusk", "Deep blue sky, low orange sun"),
]

MATERIALS = [
    ("SKIN", "Skin", "Warm neutral skin base"),
    ("HAIR", "Hair", "Dark hair base"),
    ("FABRIC", "Fabric", "Matte cloth"),
    ("METAL", "Metal", "Polished metal"),
    ("EMISSION", "Emission", "Neon emissive surface"),
]


def _on_palette(self, context):
    try:
        from . import palette, materials, compositor
        scene = context.scene
        if scene is None:
            return
        palette.apply_palette(scene, self.palette)
        if self.shadow_tint:
            materials.sync_scene(scene, palette.shadow_tint_for(scene),
                                 self.shadow_tint_strength,
                                 self.shadow_tint_distance)
        if scene.compositing_node_group:
            compositor.build(scene)
    except Exception:
        pass


def _on_world(self, context):
    try:
        from . import palette
        scene = context.scene
        if scene is not None:
            palette.apply_palette(scene, self.palette)
    except Exception:
        pass


def _on_custom(self, context):
    try:
        from . import palette
        if self.custom_colors:
            p = palette.preset(self.palette)
            self.custom_sky = p["sky_color"]
            self.custom_horizon = p["horizon_color"]
            self.custom_sun = p["sun_color"]
            self.custom_shadow = p["shadow_tint"]
        _on_world(self, context)
    except Exception:
        pass


def _on_shadow(self, context):
    try:
        from . import palette, materials
        scene = context.scene
        if scene is None:
            return
        if self.shadow_tint:
            materials.sync_scene(scene, palette.shadow_tint_for(scene),
                                 self.shadow_tint_strength,
                                 self.shadow_tint_distance)
        else:
            materials.clear_scene(scene)
    except Exception:
        pass


def _on_stack(self, context):
    try:
        from . import compositor
        scene = context.scene
        if scene is not None and scene.compositing_node_group:
            compositor.build(scene)
    except Exception:
        pass


def _on_params(self, context):
    try:
        from . import compositor
        scene = context.scene
        if scene is not None and scene.compositing_node_group:
            compositor.update_params(scene)
    except Exception:
        pass


def _on_shots(self, context):
    try:
        from . import shots
        if self.use_shot_markers and context.scene is not None:
            shots.apply_for_frame(context.scene, force=True)
    except Exception:
        pass


class ALD_Settings(bpy.types.PropertyGroup):
    palette: EnumProperty(
        name="Atmosphere",
        description="Global atmospheric palette",
        items=PALETTES,
        default="GOLDEN_HOUR",
        update=_on_palette,
    )
    use_shot_markers: BoolProperty(
        name="Shot Markers",
        default=False,
        description="Apply the palette from markers named ALD:<PALETTE>",
        update=_on_shots,
    )
    material_preset: EnumProperty(
        name="Material",
        description="Material preset assigned to selected objects",
        items=MATERIALS,
        default="SKIN",
    )

    # --- World gradient -------------------------------------------------
    world_gradient: BoolProperty(
        name="World Gradient",
        default=True,
        description="Sky / horizon / ground gradient driven by the palette",
        update=_on_world,
    )
    auto_sun: BoolProperty(
        name="Auto Sun",
        default=True,
        description="Create a sun light when the scene has none",
        update=_on_world,
    )
    custom_colors: BoolProperty(
        name="Custom Colors",
        default=False,
        description="Override sky, horizon, sun and shadow colors",
        update=_on_custom,
    )
    custom_sky: FloatVectorProperty(
        name="Sky",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.22, 0.30, 0.62),
        update=_on_world,
    )
    custom_horizon: FloatVectorProperty(
        name="Horizon",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.55, 0.28),
        update=_on_world,
    )
    custom_sun: FloatVectorProperty(
        name="Sun",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.65, 0.35),
        update=_on_world,
    )
    custom_shadow: FloatVectorProperty(
        name="Shadow",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.44, 0.53, 1.0),
        update=_on_world,
    )
    horizon_offset: FloatProperty(
        name="Horizon",
        default=0.0,
        min=-0.9,
        max=0.9,
        description="Raise or lower the horizon in the world gradient",
        update=_on_world,
    )
    horizon_softness: FloatProperty(
        name="Horizon Softness",
        default=0.5,
        min=0.02,
        max=1.0,
        description="Width of the horizon blend",
        update=_on_world,
    )
    sun_disk: BoolProperty(
        name="Sun Disk",
        default=True,
        description="Draw a sun disk aligned with the sun direction",
        update=_on_world,
    )
    sun_disk_size: FloatProperty(
        name="Sun Size", default=1.5, min=0.1, max=10.0,
        description="Angular radius of the sun disk in degrees",
        update=_on_world)
    sun_disk_strength: FloatProperty(
        name="Sun Strength", default=6.0, min=0.0, max=50.0,
        description="Brightness of the sun disk",
        update=_on_world)
    clouds: BoolProperty(
        name="Anime Clouds",
        default=True,
        description="Procedural stylized clouds in the sky",
        update=_on_world)
    cloud_amount: FloatProperty(
        name="Cloud Amount", default=0.6, min=0.0, max=1.0,
        update=_on_world)
    cloud_scale: FloatProperty(
        name="Cloud Scale", default=2.5, min=0.5, max=12.0,
        update=_on_world)

    # --- Shadow tint ----------------------------------------------------
    shadow_tint: BoolProperty(
        name="Shadow Tint",
        default=True,
        description="Tint contact shadows on scene materials with the palette color",
        update=_on_shadow,
    )
    shadow_tint_strength: FloatProperty(
        name="Shadow Tint",
        default=0.35,
        min=0.0,
        max=1.0,
        description="How strongly shadowed areas take the palette tint",
        update=_on_shadow,
    )
    shadow_tint_distance: FloatProperty(
        name="Shadow Distance",
        default=0.6,
        min=0.0,
        max=100.0,
        subtype="DISTANCE",
        description="Ambient-occlusion distance used by the shadow tint",
        update=_on_shadow,
    )

    # --- Compositor stack ----------------------------------------------
    halation: BoolProperty(name="Halation", default=True,
                           description="Warm bloom around highlights (Glare/Bloom)",
                           update=_on_stack)
    painterly: BoolProperty(name="Painterly (Kuwahara)", default=True,
                            description="Kuwahara filter mixed in by depth",
                            update=_on_stack)
    dispersion: BoolProperty(name="Chromatic dispersion", default=True,
                             description="Subtle lens dispersion",
                             update=_on_stack)
    light_wrap: BoolProperty(name="Light Wrap", default=True,
                             description="Bleed background light around silhouettes",
                             update=_on_stack)
    god_rays: BoolProperty(name="God Rays", default=False,
                           description="Sun beams from the sun's screen position",
                           update=_on_stack)
    ink_lines: BoolProperty(name="Anime Ink Lines", default=False,
                            description="Thin depth-based ink outlines",
                            update=_on_stack)
    halation_strength: FloatProperty(name="Halation Strength", default=0.6,
                                     min=0.0, max=1.0, update=_on_params)
    kuwahara_size: FloatProperty(name="Kuwahara Size", default=6.0,
                                 min=1.0, max=32.0, update=_on_params)
    dispersion_amount: FloatProperty(name="Dispersion", default=0.01,
                                     min=0.0, max=1.0, update=_on_params)
    light_wrap_strength: FloatProperty(name="Light Wrap Strength", default=0.4,
                                       min=0.0, max=1.0, update=_on_params)
    light_wrap_size: FloatProperty(name="Light Wrap Size", default=24.0,
                                   min=1.0, max=256.0, update=_on_params)
    god_rays_strength: FloatProperty(name="God Rays Strength", default=0.35,
                                     min=0.0, max=1.0, update=_on_params)
    god_rays_size: FloatProperty(name="God Rays Size", default=0.5,
                                 min=0.0, max=1.0, update=_on_params)
    ink_strength: FloatProperty(name="Ink Strength", default=0.6,
                                min=0.0, max=1.0, update=_on_params)
    ink_size: FloatProperty(name="Ink Size", default=1.5,
                            min=0.5, max=8.0, update=_on_params)
    depth_near: FloatProperty(name="Depth Near", default=4.0, min=0.0,
                              max=1000.0, subtype="DISTANCE",
                              update=_on_params)
    depth_far: FloatProperty(name="Depth Far", default=35.0, min=0.0,
                             max=10000.0, subtype="DISTANCE",
                             update=_on_params)


_classes = (ALD_Settings,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ald = PointerProperty(type=ALD_Settings)


def unregister():
    del bpy.types.Scene.ald
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
