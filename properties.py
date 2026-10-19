import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty

PALETTES = [
    ("GOLDEN_HOUR", "Shinkai Golden Hour", "Warm backlight, orange halation"),
    ("SUMMER_NOON", "Ghibli Summer Noon", "Bright sky, clean high-key light"),
    ("RAINY_TOKYO", "Rainy Tokyo Night", "Cool rain-soaked night"),
    ("NEON_NIGHT", "Cyberpunk Neon", "Magenta and cyan artificial light"),
]

MATERIALS = [
    ("SKIN", "Skin", "Warm neutral skin base"),
    ("HAIR", "Hair", "Dark hair base"),
    ("FABRIC", "Fabric", "Matte cloth"),
    ("METAL", "Metal", "Polished metal"),
]


def _on_palette(self, context):
    try:
        from . import palette, materials, compositor
        scene = context.scene
        if scene is None:
            return
        palette.apply_palette(scene, self.palette)
        if self.shadow_tint:
            materials.sync_scene(scene, palette.shadow_tint(self.palette),
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


def _on_shadow(self, context):
    try:
        from . import palette, materials
        scene = context.scene
        if scene is None:
            return
        if self.shadow_tint:
            materials.sync_scene(scene, palette.shadow_tint(self.palette),
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
        description="How strongly occluded areas take the palette shadow color",
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
    halation_strength: FloatProperty(name="Halation Strength", default=0.6,
                                     min=0.0, max=5.0, update=_on_stack)
    kuwahara_size: FloatProperty(name="Kuwahara Size", default=6.0,
                                 min=1.0, max=32.0, update=_on_stack)
    dispersion_amount: FloatProperty(name="Dispersion", default=0.01,
                                     min=0.0, max=1.0, update=_on_stack)
    light_wrap_strength: FloatProperty(name="Light Wrap Strength", default=0.4,
                                       min=0.0, max=1.0, update=_on_stack)
    light_wrap_size: FloatProperty(name="Light Wrap Size", default=24.0,
                                   min=1.0, max=256.0, update=_on_stack)
    god_rays_strength: FloatProperty(name="God Rays Strength", default=0.35,
                                     min=0.0, max=1.0, update=_on_stack)
    depth_near: FloatProperty(name="Depth Near", default=4.0, min=0.0,
                              max=1000.0, subtype="DISTANCE",
                              update=_on_stack)
    depth_far: FloatProperty(name="Depth Far", default=35.0, min=0.0,
                             max=10000.0, subtype="DISTANCE",
                             update=_on_stack)


_classes = (ALD_Settings,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ald = PointerProperty(type=ALD_Settings)


def unregister():
    del bpy.types.Scene.ald
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
