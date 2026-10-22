import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, FloatVectorProperty, IntProperty,
                       PointerProperty, StringProperty)

#: Version of the persistent FX layout: a scene saved with an older schema is
#: migrated when the add-on is enabled.
FX_SCHEMA = 1

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
        if palette.style_syncing():
            return
        scene = context.scene
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


def _on_fx_age(self, context):
    """Move the FX systems in time without rebuilding the geometry."""
    try:
        from . import fx
        if _in_maintenance(context):
            return
        scene = context.scene
        config = scene.get("ald_fx_config")
        if isinstance(config, dict):
            config["age"] = self.fx_age
            scene["ald_fx_config"] = config
        if not fx.set_age(scene, self.fx_age):
            fx.update(scene)
    except Exception:
        pass


def _on_fx_backend(self, context):
    """Apply the backend semantics: the three modes are really exclusive."""
    try:
        from . import fx
        if _in_maintenance(context):
            return
        fx.apply_backend(context.scene)
    except Exception:
        pass


def _on_fx_rebuild(self, context):
    """Recompile the FX systems when the composition changes.

    The persistent events are not touched: only the geometry is rebuilt from
    them.
    """
    try:
        from . import fx
        if _in_maintenance(context):
            return
        scene = context.scene
        config = scene.get("ald_fx_config")
        if isinstance(config, dict):
            config["age"] = self.fx_age
            scene["ald_fx_config"] = config
        fx.update_all(scene)
    except Exception:
        pass


def _on_shots(self, context):
    try:
        from . import shots
        if self.use_shot_markers and context.scene is not None:
            shots.apply_for_frame(context.scene, force=True)
    except Exception:
        pass


class ALD_FX_Event(bpy.types.PropertyGroup):
    """One firework or meteor event, persistent in the .blend file."""

    uid: StringProperty(
        name="UID", default="",
        description="Stable identity of the event")
    kind: EnumProperty(
        name="Kind",
        items=[("FIREWORK", "Firework", "A firework with a launcher and a burst"),
               ("METEOR", "Meteor", "A meteor with a start region"),
               ("BOLIDE", "Bolide",
                "A cinematic meteor: bigger, brighter, with a long train")],
        default="FIREWORK")
    enabled: BoolProperty(
        name="Enabled", default=True,
        description="The event takes part in the render")
    seed: IntProperty(
        name="Seed", default=0, min=0, max=99999,
        description="Deterministic seed of the event")
    birth: FloatProperty(
        name="Birth", default=0.0, min=-10.0, max=600.0,
        description="Seconds after the origin of the system")
    family: EnumProperty(
        name="Family",
        items=[("CHRYSANTHEMUM", "Chrysanthemum", ""),
               ("PEONY", "Peony", ""),
               ("WILLOW", "Willow", ""),
               ("KAMURO", "Kamuro", "")],
        default="CHRYSANTHEMUM",
        description="Shape family of the event")
    size: FloatProperty(
        name="Size", default=1.0, min=0.1, max=4.0,
        description="Scale of the event")
    count: IntProperty(
        name="Bursts", default=1, min=1, max=16,
        description="Number of bursts of the event")
    spokes: IntProperty(
        name="Primary Stars", default=0, min=0, max=400,
        description=("Number of primary stars of the burst. Zero means the "
                     "default of the family"))
    pistil: IntProperty(
        name="Pistil", default=0, min=0, max=64,
        description="Number of stars of the inner pistil")
    sparks: IntProperty(
        name="Child Sparks", default=0, min=0, max=8,
        description="Number of child sparks emitted by every star")
    launch_mode: EnumProperty(
        name="Launch",
        items=[("DIRECTOR", "Director",
                "The burst target and the rise time define the shot"),
               ("PHYSICAL", "Physical",
                "The launcher and the initial speed define the shot")],
        default="DIRECTOR",
        description="How the firework reaches its burst point")
    rise_time: FloatProperty(
        name="Rise Time", default=1.2, min=0.05, max=12.0,
        description="Seconds the shell takes to reach the burst point")
    drag: FloatProperty(
        name="Drag", default=1.3, min=0.0, max=8.0,
        description="Linear drag of the rising shell")
    speed: FloatProperty(
        name="Speed", default=26.0, min=0.0, max=200.0,
        description="Initial speed of the shell in physical mode")
    gravity: FloatVectorProperty(
        name="Gravity", size=3, subtype="DIRECTION",
        default=(0.0, 0.0, -9.81),
        description="World gravity of the FX")
    launcher: FloatVectorProperty(
        name="Launcher", size=3, subtype="TRANSLATION",
        description="World position the firework starts from")
    target: FloatVectorProperty(
        name="Target", size=3, subtype="TRANSLATION",
        description="World position the firework bursts at")
    direction: FloatVectorProperty(
        name="Direction", size=3, subtype="DIRECTION",
        default=(1.0, 0.0, 0.0),
        description="World direction of a meteor")
    speed: FloatProperty(
        name="Speed", default=30.0, min=0.0, max=200.0,
        description="Speed of a meteor in world units per second")
    life: FloatProperty(
        name="Life", default=1.0, min=0.05, max=20.0,
        description="Lifetime of a meteor")
    duration: FloatProperty(
        name="Duration", default=1.0, min=0.05, max=20.0,
        description="Duration of the burst of a firework")
    glow: FloatProperty(
        name="Glow", default=0.6, min=0.0, max=3.0,
        description="Glow profile of the event")


class ALD_FX_System(bpy.types.PropertyGroup):
    """A system of events with its own seed, timing and origin."""

    uid: StringProperty(
        name="UID", default="",
        description="Stable identity of the system")
    kind: EnumProperty(
        name="Kind",
        items=[("FIREWORKS", "Fireworks", "A system of firework bursts"),
               ("METEORS", "Meteors", "A system of shooting stars")],
        default="FIREWORKS",
        description="Type of the system")
    enabled: BoolProperty(
        name="Enabled", default=True,
        description="The system takes part in the render")
    seed: IntProperty(
        name="Seed", default=0, min=0, max=99999,
        description="Deterministic seed of the system")
    timing_mode: EnumProperty(
        name="Timing",
        items=[("TIMELINE", "Timeline",
                "The event time follows the frame of the timeline"),
               ("PREVIEW", "Preview",
                "The event time is set by hand, independently of the timeline")],
        default="TIMELINE",
        description="How the time of the system is read")
    origin_frame: IntProperty(
        name="Origin Frame", default=1, min=-100000, max=100000,
        description="Frame the system starts from")
    origin_time: FloatProperty(
        name="Origin Time", default=0.0, min=-100.0, max=100.0,
        description="Seconds the system starts from in preview mode")
    events: CollectionProperty(type=ALD_FX_Event)
    material_profile: StringProperty(
        name="Material Profile", default="",
        description="Name of the material profile of the system")
    glow_profile: StringProperty(
        name="Glow Profile", default="",
        description="Name of the glow profile of the system")
    isolation_mode: EnumProperty(
        name="Isolation",
        items=[("EMISSION", "Emission Pass", "The emission pass isolates the FX"),
               ("AOV", "Dedicated AOV", "A dedicated pass isolates the FX")],
        default="EMISSION",
        description="How the compositor isolates the FX layer")


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
    cloud_flatness: FloatProperty(
        name="Cloud Flatness", default=0.65, min=0.0, max=1.0,
        description="0 = billowy cumuli, 1 = flat horizontal strata",
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
    shooting_stars: BoolProperty(
        name="Shooting Stars", default=False,
        description="Procedural anime shooting stars / meteors in the sky",
        update=_on_world)
    shooting_star_amount: FloatProperty(
        name="Meteor Amount", default=0.65, min=0.0, max=1.0,
        description="Density of active shooting stars",
        update=_on_world)
    shooting_star_length: FloatProperty(
        name="Trail Length", default=0.55, min=0.1, max=1.0,
        description="Length of the ionized meteor tail",
        update=_on_world)
    shooting_star_angle: FloatProperty(
        name="Meteor Angle", default=32.0, min=-180.0, max=180.0,
        description="Trajectory angle in degrees",
        update=_on_world)
    shooting_star_phase: FloatProperty(
        name="Meteor Phase", default=0.0, min=0.0, max=100.0,
        description="Phase offset along the trajectory",
        update=_on_world)
    fireworks: BoolProperty(
        name="Fireworks (Hanabi)", default=False,
        description="Procedural anime fireworks bursts above the horizon",
        update=_on_world)
    fireworks_amount: FloatProperty(
        name="Fireworks Amount", default=0.60, min=0.0, max=1.0,
        description="Fraction of active firework bursts",
        update=_on_world)
    fireworks_scale: FloatProperty(
        name="Fireworks Scale", default=2.2, min=1.0, max=6.0,
        description="Scale of firework shells (lower = larger hero bursts)",
        update=_on_world)
    fireworks_phase: FloatProperty(
        name="Burst Phase", default=0.80, min=0.2, max=1.0,
        description="Expansion stage of the firework shells",
        update=_on_world)
    fx_backend: EnumProperty(
        name="FX Backend",
        items=[("OFF", "Disabled", "No procedural fireworks in the sky shader"),
               ("LEGACY", "Legacy World", "Procedural fireworks in the sky shader"),
               ("FX3D", "FX 3D", "Physical particles created in the scene")],
        default="FX3D",
        description="Which fireworks backend stays active",
        update=_on_fx_backend)
    fx_age: FloatProperty(
        name="Burst Age", default=0.8, min=0.0, max=6.0,
        description="Seconds after the burst shown by the FX system",
        update=_on_fx_age)
    fx_composition_offset: FloatVectorProperty(
        name="Composition Offset", size=3, subtype="TRANSLATION",
        default=(0.0, 0.0, 0.0),
        description="World-space offset applied to the whole firework group",
        update=_on_fx_rebuild)
    fx_burst_spread: FloatProperty(
        name="Burst Spread", default=1.0, min=0.2, max=3.0,
        description="Horizontal and vertical spread of the bursts",
        update=_on_fx_rebuild)
    fx_gn_prototype: BoolProperty(
        name="GN Particles (Prototype)", default=True,
        description="Evaluate the burst particles with Geometry Nodes "
                    "instead of the Python solver",
        update=_on_fx_rebuild)
    fx_meteor_persistence: FloatProperty(
        name="Meteor Persistence", default=0.32, min=0.0, max=2.0,
        description="Seconds the train of a meteor survives the head; "
                    "0 means no persistence at all",
        update=_on_fx_age)
    fx_schema: IntProperty(
        name="Schema", default=FX_SCHEMA, min=0,
        description="Version of the persistent FX layout")
    bypass: BoolProperty(
        name="Bypass", default=False,
        description="The add-on stops touching the scene: the current look is "
                    "kept and nothing is updated any more")
    detached: BoolProperty(
        name="Detached", default=False,
        description="The look was kept but the add-on does not manage it any "
                    "more")
    fx_uid: StringProperty(
        name="Scene UID", default="",
        description="Stable identity of the scene for the FX ownership")
    fx_systems: CollectionProperty(type=ALD_FX_System)
    fx_selected_system: IntProperty(
        name="Selected System", default=0, min=0, max=64,
        description="Index of the system edited in the panel")
    fx_selected_event: IntProperty(
        name="Selected Event", default=0, min=0, max=256,
        description="Index of the event edited in the panel")
    developer_mode: BoolProperty(
        name="Developer Mode", default=False,
        description="Shows the debug controls of the add-on")
    fx_energy_head: FloatProperty(
        name="Head Energy", default=1.0, min=0.0, max=4.0,
        description="Exponent of the energy decay of the star heads",
        update=_on_fx_age)
    fx_energy_grain: FloatProperty(
        name="Grain Energy", default=1.0, min=0.0, max=4.0,
        description="Exponent of the energy decay of the trail grains",
        update=_on_fx_age)
    fx_energy_ember: FloatProperty(
        name="Ember Energy", default=1.0, min=0.0, max=4.0,
        description="Exponent of the energy decay of the embers and fragments",
        update=_on_fx_age)
    fx_atmospheric_fade: FloatProperty(
        name="Atmospheric Fade", default=0.0, min=0.0, max=1.0,
        description="Fades the FX with the distance, like the atmosphere",
        update=_on_fx_age)
    fx_gravity: FloatVectorProperty(
        name="FX Gravity", size=3, subtype="DIRECTION",
        default=(0.0, 0.0, -9.81),
        description="World gravity used by the FX",
        update=_on_fx_age)
    fx_glow_strength: FloatProperty(
        name="FX Glow", default=0.6, min=0.0, max=3.0,
        description="Dedicated glow for the 3D FX layer",
        update=_on_params)
    fx_glow_size: FloatProperty(
        name="FX Glow Size", default=0.7, min=0.0, max=1.0,
        description="Size of the dedicated FX glow",
        update=_on_params)
    fx_glow_threshold: FloatProperty(
        name="FX Glow Threshold", default=1.0, min=0.0, max=10.0,
        description="Luminance threshold of the dedicated FX glow",
        update=_on_params)

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


_classes = (ALD_FX_Event, ALD_FX_System, ALD_Settings)


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
