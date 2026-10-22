import sys

import bpy


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
        s = scene.ald

        box = layout.box()
        box.label(text="Atmosphere", icon="WORLD")
        box.prop(s, "palette", text="")
        box.operator("ald.apply_palette", icon="FILE_REFRESH")
        row = box.row(align=True)
        row.prop(s, "use_shot_markers", toggle=True)
        row.operator("ald.mark_shot", text="Mark Shot", icon="MARKER")

        box = layout.box()
        box.label(text="Material Presets", icon="MATERIAL")
        row = box.row(align=True)
        row.prop(s, "material_preset", text="")
        row.operator("ald.apply_material_preset", text="Apply",
                     icon="CHECKMARK")
        obj = context.object
        mat = (getattr(obj, "active_material", None)
               if obj is not None else None)
        if mat is not None:
            excluded = bool(mat.get("ald_exclude"))
            box.operator("ald.toggle_exclude_material",
                         text="Include Material" if excluded else "Exclude Material",
                         icon="CHECKMARK" if excluded else "X")

        row = layout.row(align=True)
        row.operator("ald.build", icon="PLAY")
        row.operator("ald.remove", icon="TRASH")
        layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")

        if scene.compositing_node_group is None:
            layout.label(text="Stack not assigned", icon="INFO")
        else:
            layout.label(text="Stack: " + scene.compositing_node_group.name,
                         icon="CHECKMARK")
        effective = scene.get("ald_effective_palette", s.palette)
        source = scene.get("ald_effective_source", "scene")
        if source != "scene" or effective != s.palette:
            layout.label(text="Look: %s (%s)" % (effective, source),
                         icon="INFO")


class ALD_PT_world(bpy.types.Panel):
    bl_label = "World & Shadows"
    bl_idname = "ALD_PT_world"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -20

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        s = scene.ald
        count = scene.get("ald_shadow_materials", 0)

        box = layout.box()
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
        row.prop(s, "shooting_stars", toggle=True)
        if s.stars:
            col = box.column(align=True)
            col.prop(s, "star_strength")
            col.prop(s, "star_density")
            col.prop(s, "milky_way")
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

        box.separator()
        row = box.row(align=True)
        row.prop(s, "shadow_tint", toggle=True)
        row.label(text="%d mats" % count, icon="MATERIAL")
        row.operator("ald.clear_shadow_tint", text="", icon="X")
        if s.shadow_tint:
            col = box.column(align=True)
            col.prop(s, "shadow_tint_strength")
            col.prop(s, "shadow_tint_distance")
            col.prop(s, "shadow_hue_lift")

        box.separator()
        row = box.row(align=True)
        row.prop(s, "toon_shading", toggle=True)
        row.prop(s, "rim_light", toggle=True)
        if s.toon_shading:
            col = box.column(align=True)
            col.prop(s, "toon_strength")
            col.prop(s, "toon_sharpness")
            col.prop(s, "terminator_warmth")
        if s.rim_light:
            col = box.column(align=True)
            col.prop(s, "rim_strength")
            col.prop(s, "rim_width")
            col.prop(s, "rim_mode")
        if s.toon_shading or s.rim_light:
            box.prop(s, "rim_emission")

        cam = scene.camera
        if (cam is not None and cam.data is not None
                and hasattr(cam.data, "ald")):
            box = layout.box()
            box.label(text="Camera Override", icon="CAMERA_DATA")
            box.prop(cam.data.ald, "override", toggle=True)
            if cam.data.ald.override:
                box.prop(cam.data.ald, "palette", text="")


class ALD_PT_compositor(bpy.types.Panel):
    bl_label = "Compositor Stack"
    bl_idname = "ALD_PT_compositor"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = -10

    def draw(self, context):
        layout = self.layout
        s = context.scene.ald

        box = layout.box()
        row = box.row(align=True)
        row.prop(s, "halation", toggle=True)
        row.prop(s, "painterly", toggle=True)
        row = box.row(align=True)
        row.prop(s, "dispersion", toggle=True)
        row.prop(s, "light_wrap", toggle=True)
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
        if s.dispersion:
            col.prop(s, "dispersion_amount")
        if s.light_wrap:
            col.prop(s, "light_wrap_strength")
            col.prop(s, "light_wrap_size")
        if s.god_rays:
            col.prop(s, "god_rays_size")
        if s.ink_lines:
            col.prop(s, "ink_size")
            col.prop(s, "ink_normal_sensitivity")

        col.separator()
        col.prop(s, "depth_near")
        col.prop(s, "depth_far")


class ALD_PT_view3d(bpy.types.Panel):
    bl_label = "Anime Look"
    bl_idname = "ALD_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Anime Look"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        s = scene.ald
        module = sys.modules.get(__package__)
        version = getattr(module, "bl_info", {}).get("version")
        if version:
            layout.label(text="v%d.%d.%d" % tuple(version), icon="INFO")

        col = layout.column(align=True)
        col.prop(s, "palette", text="")
        col.operator("ald.apply_palette", icon="FILE_REFRESH")
        if scene.compositing_node_group is None:
            col.label(text="Stack not assigned", icon="INFO")
        else:
            col.label(text="Stack ready", icon="CHECKMARK")

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
        row.prop(s, "shooting_stars", toggle=True)
        if s.stars:
            col = box.column(align=True)
            col.prop(s, "star_strength")
            col.prop(s, "star_density")
            col.prop(s, "milky_way")
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

        cam = scene.camera
        if (cam is not None and cam.data is not None
                and hasattr(cam.data, "ald")):
            box = layout.box()
            box.label(text="Camera Override", icon="CAMERA_DATA")
            box.prop(cam.data.ald, "override", toggle=True)
            if cam.data.ald.override:
                box.prop(cam.data.ald, "palette", text="")

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

        row = layout.row(align=True)
        row.operator("ald.build", icon="PLAY")
        row.operator("ald.remove", icon="TRASH")
        layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")


class ALD_PT_fx(bpy.types.Panel):
    bl_label = "FX Particles"
    bl_idname = "ALD_PT_fx"
    bl_parent_id = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.scene.ald, "fx_backend")
        col.prop(context.scene.ald, "fx_age")
        col.prop(context.scene.ald, "fx_burst_spread")
        col.prop(context.scene.ald, "fx_composition_offset")
        col.prop(context.scene.ald, "fx_gn_prototype")
        col.prop(context.scene.ald, "fx_meteor_persistence")
        glow = layout.column(align=True)
        glow.prop(context.scene.ald, "fx_glow_strength")
        glow.prop(context.scene.ald, "fx_glow_size")
        col.operator("ald.fx_fireworks", icon="LIGHT")
        col.operator("ald.fx_meteors", icon="PARTICLE_DATA")
        col.operator("ald.fx_update", icon="FILE_REFRESH")
        col.operator("ald.fx_clear", icon="TRASH")
        config = context.scene.get("ald_fx_config")
        if config:
            layout.label(text="FX active: %s" % config.get("kind", "-"),
                         icon="DOT")
        from . import fx
        for kind, count in fx.systems_info(context.scene):
            row = layout.row(align=True)
            row.label(text="%s (%d)" % (kind.capitalize(), count),
                      icon="PARTICLE_DATA")
            op = row.operator("ald.fx_clear_kind", text="", icon="X")
            op.kind = kind


_classes = (ALD_PT_scene, ALD_PT_world, ALD_PT_compositor, ALD_PT_fx, ALD_PT_view3d)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
