import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, PointerProperty)

PALETTES = [
    ("GOLDEN_HOUR", "Shinkai Golden Hour", "Warm backlight, cobalt zenith and golden clouds"),
    ("AFTER_SCHOOL", "After School Sunset", "Persona-style salmon-pink sky with backlit violet cloud bands"),
    ("SUMMER_NOON", "Ghibli Summer Noon", "Deep cerulean sky, crisp white cumulus with lavender shadows"),
    ("RAINY_TOKYO", "Rainy Tokyo Night", "Cool rain-soaked slate night"),
    ("NEON_NIGHT", "Cyberpunk Neon", "Deep night sky with magenta-cyan rim-lit clouds"),
    ("SAKURA_SPRING", "Sakura Spring", "Cornflower sky, warm sakura horizon and soft lilac clouds"),
    ("TWILIGHT_DUSK", "Twilight Dusk", "Prussian blue dusk, vermilion horizon and starfield"),
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
        from . import look, palette
        scene = context.scene
        if scene is None:
            return
        if self.custom_colors:
            p = palette.preset(self.palette)
            self.custom_sky = p["sky_color"]
            self.custom_horizon = p["horizon_color"]
            self.custom_sun = p["sun_color"]
            self.custom_shadow = p["shadow_tint"]
        look.apply(scene, force=True)
    except Exception:
        pass


def _on_world(self, context):
    try:
        from . import look, palette
        if palette.style_syncing():
            return
        scene = context.scene
        if scene is not None:
            look.apply_world(scene)
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
        _on_custom_color(self, context)
    except Exception:
        pass


def _on_custom_color(self, context):
    _on_world(self, context)
    try:
        from . import materials, palette
        scene = context.scene
        if scene is not None and self.shadow_tint:
            materials.sync_scene(scene, palette.shadow_tint_for(scene),
                                 self.shadow_tint_strength,
                                 self.shadow_tint_distance)
    except Exception:
        pass
    try:
        from . import compositor
        if context.scene is not None:
            compositor.update_params(context.scene)
    except Exception:
        pass


def _on_shadow(self, context):
    try:
        from . import palette, materials
        scene = context.scene
        if scene is None:
            return
        if self.shadow_tint:
            strength = self.shadow_tint_strength
        elif self.toon_shading or self.rim_light:
            strength = 0.0
        else:
            materials.clear_scene(scene)
            return
        materials.sync_scene(scene, palette.shadow_tint_for(scene),
                             strength,
                             self.shadow_tint_distance)
    except Exception:
        pass


def _on_sun_angles(self, context):
    try:
        from . import palette
        if palette.angles_syncing():
            return
        if context.scene is not None:
            palette.apply_sun_angles(context.scene,
                                     self.sun_elevation,
                                     self.sun_azimuth)
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
        update=_on_custom_color,
    )
    custom_horizon: FloatVectorProperty(
        name="Horizon",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.55, 0.28),
        update=_on_custom_color,
    )
    custom_sun: FloatVectorProperty(
        name="Sun",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.65, 0.35),
        update=_on_custom_color,
    )
    custom_shadow: FloatVectorProperty(
        name="Shadow",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.44, 0.53, 1.0),
        update=_on_custom_color,
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
    sun_glow: FloatProperty(
        name="Sun Glow", default=0.45, min=0.0, max=2.0,
        description="Mie-style anisotropic glare around the sun",
        update=_on_world)
    sky_accent: FloatVectorProperty(
        name="Accent Color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.05, 0.32, 0.42),
        update=_on_world)
    sky_accent_amount: FloatProperty(
        name="Accent Amount", default=0.0, min=0.0, max=1.0,
        description="Optional turquoise/coral band between horizon and mid sky",
        update=_on_world)
    sun_elevation: FloatProperty(
        name="Sun Elevation", default=35.0, min=-5.0, max=85.0,
        description="Sun height above the horizon in degrees",
        update=_on_sun_angles)
    sun_azimuth: FloatProperty(
        name="Sun Azimuth", default=0.0, min=-180.0, max=180.0,
        description="Sun horizontal angle in degrees",
        update=_on_sun_angles)
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
    cloud_flatness: FloatProperty(
        name="Cloud Flatness", default=0.65, min=0.0, max=1.0,
        description="0 = billowy Ghibli cumuli, 1 = flat Persona strata",
        update=_on_world)
    contrails: FloatProperty(
        name="Contrails", default=0.0, min=0.0, max=1.0,
        description="Optional high-altitude contrail streaks",
        update=_on_world)
    cloud_delta_gain: FloatProperty(
        name="Delta Gain", default=1.0, min=0.0, max=4.0,
        description="Solar finite-difference gain (1 = raw theory)",
        update=_on_world)
    cloud_rim_boost: FloatProperty(
        name="Rim Boost", default=1.0, min=0.0, max=4.0,
        description="Silver Lining transfer gain (1 = raw theory)",
        update=_on_world)
    cloud_wind: FloatProperty(
        name="Cloud Wind", default=0.0, min=0.0, max=1.0,
        description="Animate the clouds across the sky over time",
        update=_on_world)
    stars: BoolProperty(
        name="Stars",
        default=True,
        description="Procedural starfield in the upper sky",
        update=_on_world)
    star_strength: FloatProperty(
        name="Star Amount", default=1.0, min=0.0, max=1.0,
        description="Multiplier for the preset star density",
        update=_on_world)
    star_density: FloatProperty(
        name="Star Density", default=180.0, min=50.0, max=400.0,
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
    shadow_hue_lift: FloatProperty(
        name="Hue Lift", default=0.18, min=0.0, max=0.5,
        description="Additive tint veil so warm materials can take cool shadows",
        update=_on_shadow)
    toon_shading: BoolProperty(
        name="Cel Shading",
        default=True,
        description="Directional toon terminator driven by the sun",
        update=_on_shadow,
    )
    toon_strength: FloatProperty(
        name="Cel Shadow", default=0.75, min=0.0, max=1.0,
        description="Strength of the directional shadow tint",
        update=_on_shadow)
    toon_sharpness: FloatProperty(
        name="Terminator", default=0.035, min=0.005, max=0.5,
        description="Width of the terminator (smaller = harder cel edge)",
        update=_on_shadow)
    rim_light: BoolProperty(
        name="Rim Light",
        default=True,
        description="Fresnel rim on the sun-facing side",
        update=_on_shadow,
    )
    rim_strength: FloatProperty(
        name="Rim Strength", default=0.45, min=0.0, max=1.0,
        update=_on_shadow)
    rim_width: FloatProperty(
        name="Rim Width", default=0.4, min=0.0, max=1.0,
        update=_on_shadow)
    rim_emission: FloatProperty(
        name="Rim Emission", default=0.5, min=0.0, max=2.0,
        description="Emission strength for rim light and shadow color",
        update=_on_shadow)
    terminator_warmth: FloatProperty(
        name="Terminator Warmth", default=0.2, min=0.0, max=1.0,
        description="Warm subsurface band at the terminator",
        update=_on_shadow)
    rim_mode: EnumProperty(
        name="Rim Mode",
        description="Where the rim light appears",
        items=[
            ("SUN", "Sun Side", "Kick rim on the sun-facing side"),
            ("CONTOUR", "360° Contour", "Rim around the whole silhouette"),
            ("BACK", "Backlight", "Rim on the shadow side, opposite the sun"),
        ],
        default="SUN",
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
    aerial_haze: BoolProperty(name="Aerial Haze", default=False,
                              description="Tint distant surfaces toward the horizon",
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
    ink_normal_sensitivity: FloatProperty(name="Ink Normal", default=0.6,
                                          min=0.0, max=1.0,
                                          update=_on_params)
    haze_strength: FloatProperty(name="Haze Strength", default=0.5,
                                 min=0.0, max=1.0, update=_on_params)
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
