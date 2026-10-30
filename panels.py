"""World Sky Edition panels.

Scene Properties keeps the complete set of sections. The View3D sidebar is
only the compact Quick Look surface; the advanced controls live in Scene
Properties. There is no FX or spatial-cloud section.
"""

import sys

import bpy


def _version_label(layout):
    module = sys.modules.get(__package__)
    version = getattr(module, "bl_info", {}).get("version")
    if version:
        layout.label(text="v%d.%d.%d" % tuple(version), icon="INFO")


def draw_palette(layout, context):
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Atmosphere Preset", icon="WORLD")
    box.prop(s, "palette", text="")
    row = box.row(align=True)
    row.operator("ald.apply_palette", icon="FILE_REFRESH")
    row.operator("ald.reset_look", text="Reset", icon="LOOP_BACK")
    effective = scene.get("ald_effective_palette", s.palette)
    source = scene.get("ald_effective_source", "scene")
    if source != "scene" or effective != s.palette:
        box.label(text="Look: %s (%s)" % (effective, source), icon="INFO")
    draw_camera_override(layout, context)


def draw_atmosphere(layout, context):
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Atmosphere & Sun", icon="LIGHT")
    row = box.row(align=True)
    row.prop(s, "world_gradient", toggle=True)
    row.prop(s, "auto_sun", toggle=True)
    if s.world_gradient:
        box.label(text="Horizon")
        col = box.column(align=True)
        col.prop(s, "horizon_offset")
        col.prop(s, "horizon_softness")
        box.label(text="Sky Accent")
        col = box.column(align=True)
        col.prop(s, "sky_accent")
        col.prop(s, "sky_accent_amount")
    row = box.row(align=True)
    row.prop(s, "sun_disk", toggle=True)
    if s.sun_disk:
        col = box.column(align=True)
        col.prop(s, "sun_disk_size")
        col.prop(s, "sun_disk_strength")
    row = box.row(align=True)
    row.prop(s, "sun_glow_enabled", text="Sun Glow", toggle=True)
    if s.sun_glow_enabled:
        box.prop(s, "sun_glow", text="Glow Strength")
    col = box.column(align=True)
    col.prop(s, "sun_elevation")
    col.prop(s, "sun_azimuth")
    box.operator("ald.stage_backlight", icon="LIGHT")


def draw_moon(layout, context):
    s = context.scene.ald
    box = layout.box()
    box.label(text="Moon", icon="LIGHT")
    box.prop(s, "moon_enabled", text="Enable Moon", toggle=True)
    if not s.moon_enabled:
        box.label(text="Moon is off", icon="INFO")
        return
    box.prop(s, "moon_style")
    box.label(text="Phase")
    box.prop(s, "moon_phase_mode")
    if s.moon_phase_mode == "MANUAL":
        col = box.column(align=True)
        col.prop(s, "moon_phase_name")
        col.prop(s, "moon_phase")
        col.prop(s, "moon_waxing")
        col.prop(s, "moon_lit_rotation")
    else:
        box.label(text="Phase follows the Sun", icon="INFO")
    box.prop(s, "moon_earthshine")
    box.label(text="Position")
    col = box.column(align=True)
    col.prop(s, "moon_size")
    col.prop(s, "moon_azimuth")
    col.prop(s, "moon_elevation")
    box.label(text="Surface")
    col = box.column(align=True)
    col.prop(s, "moon_color")
    col.prop(s, "moon_brightness")
    col.prop(s, "moon_surface_detail")
    col.prop(s, "moon_crater_strength")
    col.prop(s, "moon_surface_contrast")
    col.prop(s, "moon_seed")
    box.label(text="Atmosphere")
    col = box.column(align=True)
    col.prop(s, "moon_edge_softness")
    col.prop(s, "moon_glow")
    col.prop(s, "moon_halo_radius")
    col.prop(s, "moon_halo_color")


def draw_clouds(layout, context):
    s = context.scene.ald
    box = layout.box()
    box.label(text="World Clouds", icon="WORLD")
    box.prop(s, "clouds", text="Enable Clouds", toggle=True)
    if not s.clouds:
        box.label(text="Clouds are off", icon="INFO")
        return
    box.label(text="Distribution")
    col = box.column(align=True)
    row = col.row(align=True)
    row.label(text="Cloud Type")
    row.prop(s, "cloud_type", text="")
    col.prop(s, "cloud_amount")
    col.prop(s, "cloud_scale")
    col.prop(s, "cloud_seed")
    box.label(text="Shape")
    col = box.column(align=True)
    col.prop(s, "cloud_vertical")
    col.prop(s, "cloud_flatness")
    col.prop(s, "cloud_breakup")
    col.prop(s, "cloud_detail")
    box.label(text="Lighting")
    col = box.column(align=True)
    col.prop(s, "cloud_sun_lighting")
    col.prop(s, "cloud_sun_scatter")
    col.prop(s, "cloud_delta_gain")
    col.prop(s, "cloud_rim_boost")
    box.label(text="Animation")
    box.prop(s, "cloud_wind")
    box.label(text="Details")
    box.prop(s, "contrails")


def draw_stars(layout, context):
    s = context.scene.ald
    box = layout.box()
    box.label(text="Stars & Milky Way", icon="LIGHT")
    box.prop(s, "stars", text="Enable Stars", toggle=True)
    if s.stars:
        col = box.column(align=True)
        col.prop(s, "star_strength")
        col.prop(s, "star_density")
        col.prop(s, "milky_way")


def draw_shooting_stars(layout, context):
    s = context.scene.ald
    box = layout.box()
    box.label(text="Shooting Stars", icon="LIGHT")
    row = box.row(align=True)
    row.operator("ald.shooting_star_add", text="Add", icon="ADD")
    row.operator("ald.shooting_star_duplicate", text="Duplicate",
                 icon="DUPLICATE")
    row.operator("ald.shooting_star_remove", text="Remove", icon="REMOVE")
    box.operator("ald.shooting_star_preview", icon="PLAY")
    if not len(s.shooting_star_events):
        box.label(text="No controlled event (max 4)", icon="INFO")
        return
    box.template_list("ALD_UL_shooting_stars", "", s,
                      "shooting_star_events", s,
                      "shooting_star_selected", rows=4)
    index = max(0, min(s.shooting_star_selected,
                       len(s.shooting_star_events) - 1))
    event = s.shooting_star_events[index]
    row = box.row(align=True)
    row.prop(event, "name", text="")
    row.prop(event, "enabled", text="On", toggle=True)
    box.label(text="Timing")
    col = box.column(align=True)
    col.prop(event, "start_frame")
    col.prop(event, "duration")
    box.label(text="Trajectory")
    col = box.column(align=True)
    col.prop(event, "azimuth")
    col.prop(event, "elevation")
    col.prop(event, "direction")
    col.prop(event, "length")
    col.prop(event, "curvature")
    box.label(text="Appearance")
    col = box.column(align=True)
    col.prop(event, "trail")
    col.prop(event, "thickness")
    col.prop(event, "brightness")
    col.prop(event, "glow")
    col.prop(event, "color")


def draw_custom_colors(layout, context):
    s = context.scene.ald
    box = layout.box()
    box.label(text="Palette Customization", icon="COLOR")
    box.prop(s, "custom_colors", toggle=True)
    box.operator("ald.save_custom_palette", icon="FILE_TICK")
    box.label(text="Stored in this .blend")
    box.label(text="The preset is unchanged", icon="INFO")
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


def draw_material_presets(layout, context):
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Materials", icon="MATERIAL")
    row = box.row(align=True)
    row.prop(s, "material_preset", text="")
    row.operator("ald.apply_material_preset", text="Apply", icon="CHECKMARK")
    obj = context.object
    mat = getattr(obj, "active_material", None) if obj is not None else None
    if mat is not None:
        excluded = bool(mat.get("ald_exclude"))
        box.operator("ald.toggle_exclude_material",
                     text="Include Material" if excluded else "Exclude Material",
                     icon="CHECKMARK" if excluded else "X")


def draw_shadows(layout, context):
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Shadows & Toon", icon="MATERIAL")
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
    scene = context.scene
    cam = scene.camera
    if cam is None or cam.data is None or not hasattr(cam.data, "ald"):
        return
    box = layout.box()
    box.label(text="Camera Override", icon="CAMERA_DATA")
    box.prop(cam.data.ald, "override", toggle=True)
    if cam.data.ald.override:
        box.prop(cam.data.ald, "palette", text="")


def _viewport_compositor(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            if hasattr(space.shading, "use_compositor"):
                return space.shading.use_compositor, space.shading.type
    return None, None


def draw_compositor(layout, context):
    from . import compositor
    scene = context.scene
    s = scene.ald
    box = layout.box()
    box.label(text="Compositor", icon="NODETREE")
    box.label(text="Optional post-production", icon="INFO")
    box.label(text="The World renders without it")
    stack = compositor.scene_stack(scene)
    assigned = scene.compositing_node_group
    if stack is None:
        if assigned is not None:
            box.label(text="Non-ALD compositor group", icon="ERROR")
            box.label(text="ALD leaves it untouched", icon="INFO")
        else:
            box.label(text="Inactive: no ALD stack", icon="INFO")
            box.operator("ald.build", text="Enable Compositor", icon="PLAY")
        return
    if scene.render.use_compositing:
        box.label(text="Active in render", icon="CHECKMARK")
    else:
        box.label(text="Configured; render disabled", icon="INFO")
        box.label(text="Enable Compositor in the render", icon="INFO")
    row = box.row(align=True)
    row.prop(scene.render, "use_compositing", text="Use in Render",
             toggle=True)
    row.operator("ald.remove", text="Remove Stack", icon="TRASH")
    view, shading = _viewport_compositor(context)
    if view is None:
        box.label(text="Viewport preview: no 3D view", icon="INFO")
    else:
        box.label(text="Viewport preview: %s" % view,
                  icon="RESTRICT_VIEW_OFF")
        if shading != "RENDERED":
            box.label(text="Rendered shading is required", icon="INFO")
    box.label(text="Viewport Shading > Compositor", icon="INFO")

    light = box.column(align=True)
    light.label(text="Light Effects")
    row = light.row(align=True)
    row.prop(s, "halation", toggle=True)
    if s.halation:
        light.prop(s, "halation_strength")
    row = light.row(align=True)
    row.prop(s, "light_wrap", toggle=True)
    if s.light_wrap:
        light.prop(s, "light_wrap_strength")
        light.prop(s, "light_wrap_size")
    row = light.row(align=True)
    row.prop(s, "god_rays", text="Sun Beams / God Rays", toggle=True)
    if s.god_rays:
        light.prop(s, "god_rays_strength")
        light.prop(s, "god_rays_size")

    style = box.column(align=True)
    style.label(text="Stylization")
    row = style.row(align=True)
    row.prop(s, "painterly", toggle=True)
    if s.painterly:
        style.prop(s, "kuwahara_size")
    row = style.row(align=True)
    row.prop(s, "ink_lines", toggle=True)
    if s.ink_lines:
        style.prop(s, "ink_strength")
        style.prop(s, "ink_size")
        style.prop(s, "ink_normal_sensitivity")
    row = style.row(align=True)
    row.prop(s, "dispersion", toggle=True)
    if s.dispersion:
        style.prop(s, "dispersion_amount")

    post = box.column(align=True)
    post.label(text="Atmospheric Post Effects")
    row = post.row(align=True)
    row.prop(s, "aerial_haze", toggle=True)
    if s.aerial_haze:
        post.prop(s, "haze_strength")


def draw_legacy(layout, context):
    from . import legacy
    scene = context.scene
    box = layout.box()
    box.label(text="Legacy ALD Data", icon="INFO")
    box.label(text="No automatic legacy cleanup")
    found = len(legacy.legacy_collections(scene))
    if found:
        box.label(text="%d tagged collection(s) in this scene" % found,
                  icon="INFO")
    if legacy.has_state(scene):
        box.label(text="Disabled: visibility saved for restore",
                  icon="CHECKMARK")
    box.label(text="Reversible")
    row = box.row(align=True)
    row.operator("ald.legacy_disable", text="Disable", icon="HIDE_ON")
    row.operator("ald.legacy_restore", text="Restore", icon="HIDE_OFF")
    box.label(text="Destructive")
    box.operator("ald.legacy_remove", text="Remove Permanently...",
                 icon="TRASH")
    box.label(text="Maintenance")
    box.operator("ald.repair_ownership", icon="FILE_REFRESH")


def draw_ownership_warning(layout, context):
    from . import ownership
    if ownership.has_shared(context.scene):
        box = layout.box()
        box.label(text="Scene copy shares the original World", icon="ERROR")
        box.operator("ald.repair_ownership", icon="FILE_REFRESH")


def draw_scene_actions(layout, context):
    box = layout.box()
    box.label(text="Scene Actions", icon="SCENE_DATA")
    box.label(text="Destructive actions", icon="ERROR")
    box.operator("ald.remove_from_scene", icon="TRASH")
    box.operator("ald.detach", icon="UNLINKED")


class ALD_UL_shooting_stars(bpy.types.UIList):
    bl_idname = "ALD_UL_shooting_stars"

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        if item is not None:
            layout.label(text=item.name or "Shooting Star", icon="LIGHT")


# ---------------------------------------------------------------------------
# Scene Properties
# ---------------------------------------------------------------------------

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
        draw_ownership_warning(layout, context)
        draw_palette(layout, context)


class ALD_PT_atmosphere(bpy.types.Panel):
    bl_label = "Atmosphere & Sun"
    bl_idname = "ALD_PT_atmosphere"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -50

    def draw(self, context):
        draw_atmosphere(self.layout, context)


class ALD_PT_moon(bpy.types.Panel):
    bl_label = "Moon"
    bl_idname = "ALD_PT_moon"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -48
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        draw_moon(self.layout, context)


class ALD_PT_clouds(bpy.types.Panel):
    bl_label = "World Clouds"
    bl_idname = "ALD_PT_clouds"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -45

    def draw(self, context):
        draw_clouds(self.layout, context)


class ALD_PT_stars(bpy.types.Panel):
    bl_label = "Stars & Milky Way"
    bl_idname = "ALD_PT_stars"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -40

    def draw(self, context):
        draw_stars(self.layout, context)


class ALD_PT_shooting_stars(bpy.types.Panel):
    bl_label = "Shooting Stars"
    bl_idname = "ALD_PT_shooting_stars"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -35

    def draw(self, context):
        draw_shooting_stars(self.layout, context)


class ALD_PT_custom(bpy.types.Panel):
    bl_label = "Palette Customization"
    bl_idname = "ALD_PT_custom"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -30

    def draw(self, context):
        draw_custom_colors(self.layout, context)


class ALD_PT_materials(bpy.types.Panel):
    bl_label = "Materials & Shadows"
    bl_idname = "ALD_PT_materials"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -25

    def draw(self, context):
        draw_material_presets(self.layout, context)
        draw_shadows(self.layout, context)


class ALD_PT_compositor(bpy.types.Panel):
    bl_label = "Compositor"
    bl_idname = "ALD_PT_compositor"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -20

    def draw(self, context):
        draw_compositor(self.layout, context)


class ALD_PT_advanced(bpy.types.Panel):
    bl_label = "Advanced Settings"
    bl_idname = "ALD_PT_advanced"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 10

    def draw(self, context):
        draw_legacy(self.layout, context)
        draw_scene_actions(self.layout, context)


# ---------------------------------------------------------------------------
# View3D sidebar: the same sections as Scene Properties
# ---------------------------------------------------------------------------

class ALD_PT_view3d(bpy.types.Panel):
    bl_label = "Anime Look"
    bl_idname = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        _version_label(self.layout)
        draw_ownership_warning(self.layout, context)
        draw_palette(self.layout, context)


class ALD_PT_view3d_atmosphere(bpy.types.Panel):
    bl_label = "Atmosphere & Sun"
    bl_idname = "ALD_PT_view3d_atmosphere"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -50

    def draw(self, context):
        draw_atmosphere(self.layout, context)


class ALD_PT_view3d_clouds(bpy.types.Panel):
    bl_label = "World Clouds"
    bl_idname = "ALD_PT_view3d_clouds"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -45

    def draw(self, context):
        draw_clouds(self.layout, context)


class ALD_PT_view3d_moon(bpy.types.Panel):
    bl_label = "Moon"
    bl_idname = "ALD_PT_view3d_moon"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -48
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        draw_moon(self.layout, context)


class ALD_PT_view3d_stars(bpy.types.Panel):
    bl_label = "Stars & Milky Way"
    bl_idname = "ALD_PT_view3d_stars"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -40

    def draw(self, context):
        draw_stars(self.layout, context)


class ALD_PT_view3d_shooting_stars(bpy.types.Panel):
    bl_label = "Shooting Stars"
    bl_idname = "ALD_PT_view3d_shooting_stars"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -35

    def draw(self, context):
        draw_shooting_stars(self.layout, context)


class ALD_PT_view3d_custom(bpy.types.Panel):
    bl_label = "Palette Customization"
    bl_idname = "ALD_PT_view3d_custom"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -30

    def draw(self, context):
        draw_custom_colors(self.layout, context)


class ALD_PT_view3d_materials(bpy.types.Panel):
    bl_label = "Materials & Shadows"
    bl_idname = "ALD_PT_view3d_materials"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -25

    def draw(self, context):
        draw_material_presets(self.layout, context)
        draw_shadows(self.layout, context)


class ALD_PT_view3d_compositor(bpy.types.Panel):
    bl_label = "Compositor"
    bl_idname = "ALD_PT_view3d_compositor"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = -20

    def draw(self, context):
        draw_compositor(self.layout, context)


class ALD_PT_view3d_advanced(bpy.types.Panel):
    bl_label = "Advanced Settings"
    bl_idname = "ALD_PT_view3d_advanced"
    bl_parent_id = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"
    bl_order = 10

    def draw(self, context):
        draw_legacy(self.layout, context)
        draw_scene_actions(self.layout, context)


_classes = (ALD_UL_shooting_stars, ALD_PT_scene, ALD_PT_atmosphere,
            ALD_PT_moon, ALD_PT_clouds,
            ALD_PT_stars, ALD_PT_shooting_stars, ALD_PT_custom,
            ALD_PT_materials, ALD_PT_compositor, ALD_PT_advanced,
            ALD_PT_view3d, ALD_PT_view3d_atmosphere, ALD_PT_view3d_moon,
            ALD_PT_view3d_clouds,
            ALD_PT_view3d_stars, ALD_PT_view3d_shooting_stars,
            ALD_PT_view3d_custom, ALD_PT_view3d_materials,
            ALD_PT_view3d_compositor, ALD_PT_view3d_advanced)


def register():
    from .properties import register_classes
    register_classes(_classes)


def unregister():
    from .properties import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
