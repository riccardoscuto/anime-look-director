import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, FloatVectorProperty, IntProperty,
                       IntVectorProperty, PointerProperty, StringProperty)

PALETTES = [
    ("GOLDEN_HOUR", "Golden Hour", "Warm backlight, cobalt zenith and golden clouds"),
    ("AFTER_SCHOOL", "After School Sunset", "Salmon-pink sunset sky with backlit violet cloud bands"),
    ("SUMMER_NOON", "Summer Noon", "Deep cerulean sky, crisp white cumulus with lavender shadows"),
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
            palette.sync_custom_colors(self, palette.preset(self.palette))
        look.apply(scene, force=True)
    except Exception:
        pass


def _in_maintenance(context):
    """True while the add-on restores the scene: the callbacks stay quiet."""
    try:
        from . import snapshot
        scene = getattr(context, "scene", None)
        return scene is not None and snapshot.is_inactive(scene)
    except Exception:
        return False


def register_class(cls):
    """Register a class, tolerating a registration that already exists.

    Blender reloads an add-on when its files change on disk: the sub modules
    keep their registered classes and the second registration would raise
    "already registered as a subclass".
    """
    try:
        bpy.utils.register_class(cls)
    except RuntimeError as exc:
        if "already registered" not in str(exc):
            raise
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)


def register_classes(classes):
    """Register a list of classes, tolerating a previous registration.

    Blender reloads an add-on when its files change on disk: the sub modules
    keep their registered classes and the second registration would raise
    "already registered as a subclass". The classes are unregistered in the
    reverse order first, so a class that references another one (a
    CollectionProperty of a PropertyGroup) is always released before it.
    """
    for cls in reversed(list(classes)):
        unregister_class(cls)
    for cls in classes:
        register_class(cls)


def unregister_class(cls):
    """Unregister a class, ignoring the ones that are not registered."""
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass


def remove_property(owner, name):
    """Remove a pointer property, ignoring the ones that are not there."""
    try:
        delattr(owner, name)
    except (AttributeError, TypeError):
        pass


def _on_world(self, context):
    try:
        from . import look, palette
        if palette.style_syncing() or _in_maintenance(context):
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
            palette.sync_custom_colors(self, palette.preset(self.palette))
        _on_custom_color(self, context)
    except Exception:
        pass


def _on_custom_color(self, context):
    try:
        from . import palette
        if palette.style_syncing():
            return
    except Exception:
        pass
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
        from . import compositor, palette
        if palette.style_syncing() or _in_maintenance(context):
            return
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


def _on_star(self, context):
    """Refresh the World when a shooting-star event is edited."""
    try:
        from . import look
        if context.scene is not None:
            if not len(context.scene.ald.shooting_star_events):
                return
            look.apply_world(context.scene)
    except Exception:
        pass


class ALD_ShootingStar(bpy.types.PropertyGroup):
    """A controlled 2D shooting star in the World shader."""

    name: StringProperty(name="Name", default="Shooting Star")
    enabled: BoolProperty(name="Enabled", default=True, update=_on_star)
    start_frame: IntProperty(name="Start Frame", default=1, min=-100000,
                             max=100000, update=_on_star)
    duration: IntProperty(name="Duration", default=24, min=2, max=240,
                          update=_on_star)
    azimuth: FloatProperty(name="Azimuth", default=120.0, min=-180.0,
                           max=180.0, description="Degrees around the sky",
                           update=_on_star)
    elevation: FloatProperty(name="Elevation", default=40.0, min=-10.0,
                             max=89.0, description="Degrees above the horizon",
                             update=_on_star)
    direction: FloatProperty(name="Direction", default=-35.0, min=-180.0,
                             max=180.0, description="Trajectory angle in degrees",
                             update=_on_star)
    length: FloatProperty(name="Angular Length", default=18.0, min=1.0,
                          max=90.0, description="Trajectory length in degrees",
                          update=_on_star)
    trail: FloatProperty(name="Trail", default=0.55, min=0.0, max=0.95,
                         update=_on_star)
    thickness: FloatProperty(name="Thickness", default=0.0018, min=0.0005,
                             max=0.05, update=_on_star)
    brightness: FloatProperty(name="Brightness", default=3.0, min=0.0,
                              max=30.0, update=_on_star)
    glow: FloatProperty(name="Glow", default=0.8, min=0.0, max=3.0,
                        update=_on_star)
    color: FloatVectorProperty(name="Color", size=3, subtype="COLOR",
                               default=(0.88, 0.94, 1.0), min=0.0, max=10.0,
                               update=_on_star)


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
        description="Override sky, horizon, sun, shadow and cloud colors",
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
    custom_cloud_shadow: FloatVectorProperty(
        name="Cloud Shadow",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=2.0,
        default=(0.09, 0.07, 0.22),
        update=_on_custom_color,
    )
    custom_cloud_mid: FloatVectorProperty(
        name="Cloud Mid",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=2.0,
        default=(0.38, 0.15, 0.24),
        update=_on_custom_color,
    )
    custom_cloud_light: FloatVectorProperty(
        name="Cloud Light",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=2.0,
        default=(1.30, 0.58, 0.16),
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
    sun_glow_enabled: BoolProperty(
        name="Sun Glow", default=True,
        description="Enable Mie atmospheric glow around the sun",
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
    cloud_type: EnumProperty(
        name="Cloud Type",
        items=[("CUMULUS", "Cumulus", "Rounded, vertically developed masses"),
               ("STRATOCUMULUS", "Stratocumulus",
                "Horizontal bands, irregular openings"),
               ("CIRRUS", "Cirrus", "Thin, stretched filaments")],
        default="CUMULUS",
        description="Morphological family of the World clouds",
        update=_on_world)
    cloud_flatness: FloatProperty(
        name="Flatness", default=0.60, min=0.0, max=1.0,
        description="0 = billowy cumuli, 1 = flat horizontal strata",
        update=_on_world)
    cloud_vertical: FloatProperty(
        name="Vertical Development", default=0.55, min=0.0, max=1.0,
        description="Vertical growth of the masses",
        update=_on_world)
    cloud_breakup: FloatProperty(
        name="Breakup", default=0.35, min=0.0, max=1.0,
        description="Fragmentation and openings between groups",
        update=_on_world)
    cloud_detail: FloatProperty(
        name="Detail", default=0.60, min=0.0, max=1.0,
        description="Fine erosion of the cloud borders",
        update=_on_world)
    cloud_seed: IntProperty(
        name="Seed", default=17, min=0, max=99999,
        description="Deterministic cloud configuration",
        update=_on_world)
    cloud_sun_lighting: FloatProperty(
        name="Sun Lighting", default=1.2, min=0.0, max=2.0,
        description="Strength of the light/dark variation inside the clouds",
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
        description="Visible star amount for the preset",
        update=_on_world)
    star_density: FloatProperty(
        name="Star Density", default=180.0, min=50.0, max=400.0,
        update=_on_world)
    milky_way: FloatProperty(
        name="Milky Way", default=0.0, min=0.0, max=1.0,
        description="Luminous anime Galactic River with dark cosmic dust rift",
        update=_on_world)
    shooting_star_events: CollectionProperty(type=ALD_ShootingStar)
    shooting_star_selected: IntProperty(
        name="Selected Shooting Star", default=0, min=0, max=7,
        update=_on_world)
    bypass: BoolProperty(
        name="Bypass", default=False,
        description="The add-on stops touching the scene: the current look is "
                    "kept and nothing is updated any more")
    detached: BoolProperty(
        name="Detached", default=False,
        description="The look was kept but the add-on does not manage it any "
                    "more")
    developer_mode: BoolProperty(
        name="Developer Mode", default=False,
        description="Shows the debug controls of the add-on")

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


_classes = (ALD_ShootingStar, ALD_Settings)


def register():
    # The pointer on the scene holds a reference to the settings class: it is
    # removed first, otherwise the class cannot be unregistered.
    remove_property(bpy.types.Scene, "ald")
    register_classes(_classes)
    bpy.types.Scene.ald = PointerProperty(type=ALD_Settings)


def unregister():
    remove_property(bpy.types.Scene, "ald")
    for cls in reversed(_classes):
        unregister_class(cls)
