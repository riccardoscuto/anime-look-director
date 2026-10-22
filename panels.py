import sys

import bpy


# ---------------------------------------------------------------------------
# shared drawing functions
#
# The Scene properties and the View3D sidebar draw exactly the same data with
# the same operators: the user never has to choose which panel is the real
# one, and no control exists in one surface and not in the other.
# ---------------------------------------------------------------------------

def draw_atmosphere(layout, context):
    """The palette and the state of the compositor stack."""
    scene = context.scene
    s = scene.ald
    col = layout.column(align=True)
    col.prop(s, "palette", text="")
    col.operator("ald.apply_palette", icon="FILE_REFRESH")
    if scene.compositing_node_group is None:
        col.label(text="Stack not assigned", icon="INFO")
    else:
        col.label(text="Stack ready", icon="CHECKMARK")


def draw_material_presets(layout, context):
    """The material presets and the exclusion of a material."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Material Presets", icon="MATERIAL")
    row = box.row(align=True)
    row.prop(s, "material_preset", text="")
    row.operator("ald.apply_material_preset", text="Apply", icon="CHECKMARK")
    obj = context.object
    mat = (getattr(obj, "active_material", None)
           if obj is not None else None)
    if mat is not None:
        excluded = bool(mat.get("ald_exclude"))
        box.operator("ald.toggle_exclude_material",
                     text="Include Material" if excluded else "Exclude Material",
                     icon="CHECKMARK" if excluded else "X")


def draw_stack_actions(layout, context):
    """The stack buttons."""
    row = layout.row(align=True)
    row.operator("ald.build", icon="PLAY")
    row.operator("ald.remove", icon="TRASH")
    layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")


def draw_world(layout, context):
    """The world, the sun, the clouds and the stars."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="World", icon="WORLD")
    row = box.row(align=True)
    row.prop(s, "world_gradient", toggle=True)
    row.prop(s, "auto_sun", toggle=True)
    if s.world_gradient:
        col = box.column(align=True)
        col.prop(s, "horizon_offset")
        col.prop(s, "horizon_softness")
    row = box.row(align=True)
    row.prop(s, "sun_disk", toggle=True)
    row.prop(s, "clouds", toggle=True)
    if s.sun_disk:
        col = box.column(align=True)
        col.prop(s, "sun_disk_size")
        col.prop(s, "sun_disk_strength")
    row = box.row(align=True)
    row.prop(s, "sun_glow_enabled", text="Sun Glow", toggle=True)
    row.prop(s, "god_rays", text="Sun Beams", toggle=True)
    if s.sun_glow_enabled:
        box.prop(s, "sun_glow", text="Glow Strength")
    if s.god_rays:
        col = box.column(align=True)
        col.prop(s, "god_rays_strength", text="Beam Strength")
        col.prop(s, "god_rays_size", text="Beam Size")
    col = box.column(align=True)
    col.prop(s, "sky_accent")
    col.prop(s, "sky_accent_amount")
    if s.clouds:
        col = box.column(align=True)
        col.prop(s, "cloud_amount")
        col.prop(s, "cloud_scale")
        col.prop(s, "cloud_flatness")
        col.prop(s, "cloud_wind")
        col.prop(s, "contrails")
        col.prop(s, "cloud_delta_gain")
        col.prop(s, "cloud_rim_boost")
    row = box.row(align=True)
    row.prop(s, "stars", toggle=True)
    if s.stars:
        col = box.column(align=True)
        col.prop(s, "star_strength")
        col.prop(s, "star_density")
        col.prop(s, "milky_way")
    # The legacy world meteors and fireworks belong to the Legacy World
    # backend: the 3D ones are in the FX section.
    if s.fx_backend == "LEGACY":
        row = box.row(align=True)
        row.prop(s, "shooting_stars", toggle=True)
        if s.shooting_stars:
            col = box.column(align=True)
            col.prop(s, "shooting_star_amount")
            col.prop(s, "shooting_star_length")
            col.prop(s, "shooting_star_angle")
            col.prop(s, "shooting_star_phase")
        row = box.row(align=True)
        row.prop(s, "fireworks", toggle=True)
        if s.fireworks:
            col = box.column(align=True)
            col.prop(s, "fireworks_amount")
            col.prop(s, "fireworks_scale")
            col.prop(s, "fireworks_phase")
    col = box.column(align=True)
    col.prop(s, "sun_elevation")
    col.prop(s, "sun_azimuth")
    box.operator("ald.stage_backlight", icon="LIGHT")
    row = box.row()
    row.prop(s, "custom_colors", toggle=True)
    if s.custom_colors:
        col = box.column(align=True)
        col.prop(s, "custom_sky")
        col.prop(s, "custom_horizon")
        col.prop(s, "custom_sun")
        col.prop(s, "custom_shadow")
        col.separator()
        col.prop(s, "custom_cloud_shadow")
        col.prop(s, "custom_cloud_mid")
        col.prop(s, "custom_cloud_light")


def draw_shadows(layout, context):
    """The shadow tint, the toon shading and the rim light."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    row = box.row(align=True)
    row.prop(s, "shadow_tint", toggle=True)
    count = scene.get("ald_shadow_materials", 0)
    row.label(text="%d mats" % count, icon="MATERIAL")
    row.operator("ald.clear_shadow_tint", text="", icon="X")
    if s.shadow_tint:
        col = box.column(align=True)
        col.prop(s, "shadow_tint_strength")
        col.prop(s, "shadow_hue_lift")
    row = box.row(align=True)
    row.prop(s, "toon_shading", toggle=True)
    row.prop(s, "rim_light", toggle=True)
    if s.toon_shading:
        col = box.column(align=True)
        col.prop(s, "toon_strength")
        col.prop(s, "terminator_warmth")
    if s.rim_light:
        col = box.column(align=True)
        col.prop(s, "rim_strength")
        col.prop(s, "rim_mode")
    if s.toon_shading or s.rim_light:
        box.prop(s, "rim_emission")


def draw_camera_override(layout, context):
    """The palette override of the render camera."""
    scene = context.scene
    cam = scene.camera
    if cam is None or cam.data is None or not hasattr(cam.data, "ald"):
        return
    box = layout.box()
    box.label(text="Camera Override", icon="CAMERA_DATA")
    box.prop(cam.data.ald, "override", toggle=True)
    if cam.data.ald.override:
        box.prop(cam.data.ald, "palette", text="")


def draw_compositor(layout, context):
    """The controls of the compositor stack."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Compositor", icon="NODETREE")
    row = box.row(align=True)
    row.prop(s, "halation", toggle=True)
    row.prop(s, "painterly", toggle=True)
    row = box.row(align=True)
    row.prop(s, "light_wrap", toggle=True)
    row.prop(s, "dispersion", toggle=True)
    row = box.row(align=True)
    row.prop(s, "god_rays", toggle=True)
    if s.god_rays:
        row.prop(s, "god_rays_strength", text="Strength")
    row = box.row(align=True)
    row.prop(s, "ink_lines", toggle=True)
    if s.ink_lines:
        row.prop(s, "ink_strength", text="Strength")
    row = box.row(align=True)
    row.prop(s, "aerial_haze", toggle=True)
    if s.aerial_haze:
        row.prop(s, "haze_strength", text="Strength")

    col = box.column(align=True)
    if s.halation:
        col.prop(s, "halation_strength")
    if s.painterly:
        col.prop(s, "kuwahara_size")
    if s.light_wrap:
        col.prop(s, "light_wrap_strength")
        col.prop(s, "light_wrap_size")
    if s.god_rays:
        col.prop(s, "god_rays_size")
    if s.ink_lines:
        col.prop(s, "ink_size")
        col.prop(s, "ink_normal_sensitivity")


def _selected_system(context):
    """The system and the event selected in the panel."""
    scene = context.scene
    settings = getattr(scene, "ald", None)
    if settings is None:
        return None, None
    index = int(settings.fx_selected_system)
    if index < 0 or index >= len(settings.fx_systems):
        return None, None
    system = settings.fx_systems[index]
    event = None
    event_index = int(settings.fx_selected_event)
    if 0 <= event_index < len(system.events):
        event = system.events[event_index]
    return system, event


def draw_fx_systems(layout, context):
    """The list of the persistent systems and of their events."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Systems", icon="OUTLINER")
    if not s.fx_systems:
        box.label(text="No FX system", icon="INFO")
    for index, system in enumerate(s.fx_systems):
        row = box.row(align=True)
        row.prop(system, "enabled", text="", icon="CHECKBOX_HLT")
        row.label(text="%s (%d)" % (system.kind.capitalize(),
                                   len(system.events)))
        op = row.operator("ald.fx_select_system", text="",
                          icon="RESTRICT_SELECT_OFF")
        op.index = index
    if s.fx_systems:
        row = box.row(align=True)
        row.operator("ald.fx_duplicate_system", icon="DUPLICATE")
        row.operator("ald.fx_remove_system", icon="X")
    system, event = _selected_system(context)
    if system is not None and system.events:
        col = box.column(align=True)
        col.label(text="Events", icon="KEYFRAME_HLT")
        for index, item in enumerate(system.events):
            row = col.row(align=True)
            row.prop(item, "enabled", text="", icon="CHECKBOX_HLT")
            row.label(text="%s %d" % (item.kind.capitalize(), index))
            op = row.operator("ald.fx_select_event", text="",
                              icon="RESTRICT_SELECT_OFF")
            op.index = index


def draw_fx_timing(layout, context):
    """The timing of the selected system."""
    scene = context.scene
    s = scene.ald
    system, _event = _selected_system(context)
    box = layout.box()
    box.label(text="Timing", icon="TIME")
    col = box.column(align=True)
    col.prop(s, "fx_backend")
    if system is not None:
        col.prop(system, "timing_mode")
        if system.timing_mode == "TIMELINE":
            col.prop(system, "origin_frame")
        else:
            col.prop(system, "origin_time")
    col = box.column(align=True)
    col.prop(s, "fx_age", text="Burst Age")
    col.prop(s, "fx_burst_spread", text="Burst Spread")
    col.prop(s, "fx_composition_offset", text="Offset")


def draw_fx_launch(layout, context):
    """The launcher and the target of the selected event."""
    system, event = _selected_system(context)
    box = layout.box()
    box.label(text="Launch", icon="EMPTY_AXIS")
    if event is None:
        box.label(text="No event selected", icon="INFO")
        return
    col = box.column(align=True)
    if event.kind == "METEOR":
        col.prop(event, "direction")
        col.prop(event, "speed")
        col.prop(event, "life")
    else:
        col.prop(event, "launch_mode")
        col.prop(event, "launcher")
        col.prop(event, "target")
        col.prop(event, "rise_time", text="Rise Time")
        col.prop(event, "drag")
        col.prop(event, "duration", text="Burst Duration")
        col.prop(event, "birth", text="Birth")


def draw_fx_explosion(layout, context):
    """The shape of the selected event."""
    system, event = _selected_system(context)
    box = layout.box()
    box.label(text="Explosion", icon="PARTICLE_DATA")
    if event is None:
        box.label(text="No event selected", icon="INFO")
        return
    col = box.column(align=True)
    if event.kind == "FIREWORK":
        col.prop(event, "family")
    col.prop(event, "seed")
    col.prop(event, "size")
    col.prop(event, "count", text="Primary Count")
    col.prop(event, "pistil")
    col.prop(event, "sparks")


def draw_fx_look(layout, context):
    """The look of the selected event."""
    scene = context.scene
    s = scene.ald
    system, event = _selected_system(context)
    box = layout.box()
    box.label(text="Look", icon="COLOR")
    col = box.column(align=True)
    col.prop(s, "fx_glow_strength", text="FX Glow")
    col.prop(s, "fx_glow_size", text="Glow Size")
    col.prop(s, "fx_glow_threshold", text="Glow Threshold")
    col.prop(s, "fx_energy_head", text="Head Energy")
    col.prop(s, "fx_energy_grain", text="Grain Energy")
    col.prop(s, "fx_energy_ember", text="Ember Energy")
    col.prop(s, "fx_atmospheric_fade", text="Atmospheric Fade")
    if event is not None:
        col.prop(event, "glow", text="Event Glow")


def draw_fx_advanced(layout, context):
    """The debug controls, only in developer mode."""
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Advanced", icon="PREFERENCES")
    row = box.row(align=True)
    row.prop(s, "developer_mode", toggle=True)
    if not s.developer_mode:
        box.label(text="Developer mode off", icon="INFO")
        return
    col = box.column(align=True)
    col.prop(s, "fx_gn_prototype")
    col.prop(s, "fx_meteor_persistence")
    col.prop(s, "fx_schema")
    col.label(text="UID %s" % (s.fx_uid or "-"))


def draw_scene_actions(layout, context):
    """The three actions of the plan on the scene itself.

    Bypass: the add-on stops touching the scene, the look is kept.
    Remove ALD from Scene: the complete removal, the scene comes back to the
    state registered before the first modification.
    Detach and Keep Result: the look is kept but the add-on stops managing it.
    """
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Scene", icon="SCENE")
    col = box.column(align=True)
    col.prop(s, "bypass", toggle=True)
    col.operator("ald.remove_from_scene", icon="TRASH")
    col.operator("ald.detach", icon="UNLINKED")
    if s.bypass:
        box.label(text="Bypassed: the scene is not touched", icon="INFO")
    if s.detached:
        box.label(text="Detached: the look is kept", icon="INFO")


def draw_fx_actions(layout, context):
    """The FX actions."""
    box = layout.box()
    box.label(text="Actions", icon="PLAY")
    col = box.column(align=True)
    col.operator("ald.fx_fireworks", icon="LIGHT")
    col.operator("ald.fx_meteors", icon="PARTICLE_DATA")
    col.operator("ald.fx_bolide", icon="TRIA_RIGHT_BAR")
    col.operator("ald.fx_update", icon="FILE_REFRESH")
    col.operator("ald.fx_clear", icon="TRASH")
    box.label(text="The FX are 3D objects: use the rendered viewport "
                    "(Z > Rendered) or render the frame", icon="INFO")


def draw_fx(layout, context):
    """The whole FX section: the same in the two surfaces."""
    draw_fx_systems(layout, context)
    draw_fx_timing(layout, context)
    draw_fx_launch(layout, context)
    draw_fx_explosion(layout, context)
    draw_fx_look(layout, context)
    draw_fx_advanced(layout, context)
    draw_fx_actions(layout, context)
    draw_scene_actions(layout, context)


def draw_all(layout, context):
    """The whole interface: the same in the Scene properties and the sidebar."""
    draw_atmosphere(layout, context)
    draw_material_presets(layout, context)
    draw_stack_actions(layout, context)
    draw_fx(layout, context)
    draw_world(layout, context)
    draw_shadows(layout, context)
    draw_camera_override(layout, context)
    draw_compositor(layout, context)


class ALD_PT_scene(bpy.types.Panel):
    bl_label = "Anime Look Director"
    bl_idname = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -10

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if not hasattr(scene, "ald"):
            layout.label(text="Settings not registered", icon="ERROR")
            return
        draw_atmosphere(layout, context)
        draw_material_presets(layout, context)
        draw_stack_actions(layout, context)
        effective = scene.get("ald_effective_palette", scene.ald.palette)
        source = scene.get("ald_effective_source", "scene")
        if source != "scene" or effective != scene.ald.palette:
            layout.label(text="Look: %s (%s)" % (effective, source), icon="INFO")


class ALD_PT_world(bpy.types.Panel):
    bl_label = "World & Shadows"
    bl_idname = "ALD_PT_world"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -20

    def draw(self, context):
        draw_world(self.layout, context)
        draw_shadows(self.layout, context)


class ALD_PT_compositor(bpy.types.Panel):
    bl_label = "Compositor Stack"
    bl_idname = "ALD_PT_compositor"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -10

    def draw(self, context):
        draw_compositor(self.layout, context)
        draw_camera_override(self.layout, context)


class ALD_PT_fx(bpy.types.Panel):
    bl_label = "FX Particles"
    bl_idname = "ALD_PT_fx"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        draw_fx(self.layout, context)


class ALD_PT_view3d(bpy.types.Panel):
    bl_label = "Anime Look"
    bl_idname = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        layout = self.layout
        module = sys.modules.get(__package__)
        version = getattr(module, "bl_info", {}).get("version")
        if version:
            layout.label(text="v%d.%d.%d" % tuple(version), icon="INFO")
        draw_atmosphere(layout, context)
        draw_material_presets(layout, context)
        draw_stack_actions(layout, context)


class ALD_PT_view3d_world(bpy.types.Panel):
    bl_label = "World & Shadows"
    bl_idname = "ALD_PT_view3d_world"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        draw_world(self.layout, context)
        draw_shadows(self.layout, context)


class ALD_PT_view3d_compositor(bpy.types.Panel):
    bl_label = "Compositor Stack"
    bl_idname = "ALD_PT_view3d_compositor"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        draw_compositor(self.layout, context)
        draw_camera_override(self.layout, context)


class ALD_PT_view3d_fx(bpy.types.Panel):
    bl_label = "FX Particles"
    bl_idname = "ALD_PT_view3d_fx"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        draw_fx(self.layout, context)


_classes = (ALD_PT_scene, ALD_PT_world, ALD_PT_compositor, ALD_PT_fx,
             ALD_PT_view3d, ALD_PT_view3d_world, ALD_PT_view3d_compositor,
             ALD_PT_view3d_fx)


def register():
    from .properties import register_classes
    register_classes(_classes)


def unregister():
    from .properties import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
