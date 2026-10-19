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
        if s.clouds:
            col = box.column(align=True)
            col.prop(s, "cloud_amount")
            col.prop(s, "cloud_scale")

        row = box.row()
        row.prop(s, "custom_colors", toggle=True)
        if s.custom_colors:
            col = box.column(align=True)
            col.prop(s, "custom_sky")
            col.prop(s, "custom_horizon")
            col.prop(s, "custom_sun")
            col.prop(s, "custom_shadow")

        box.separator()
        row = box.row(align=True)
        row.prop(s, "shadow_tint", toggle=True)
        row.label(text="%d mats" % count, icon="MATERIAL")
        row.operator("ald.clear_shadow_tint", text="", icon="X")
        if s.shadow_tint:
            col = box.column(align=True)
            col.prop(s, "shadow_tint_strength")
            col.prop(s, "shadow_tint_distance")

        box.separator()
        row = box.row(align=True)
        row.prop(s, "toon_shading", toggle=True)
        row.prop(s, "rim_light", toggle=True)
        if s.toon_shading:
            col = box.column(align=True)
            col.prop(s, "toon_strength")
            col.prop(s, "toon_sharpness")
        if s.rim_light:
            col = box.column(align=True)
            col.prop(s, "rim_strength")
            col.prop(s, "rim_width")

        cam = scene.camera
        if (cam is not None and cam.data is not None
                and hasattr(cam.data, "ald")):
            box = layout.box()
            box.label(text="Camera Override", icon="CAMERA")
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
        row = box.row()
        row.prop(s, "custom_colors", toggle=True)
        if s.custom_colors:
            col = box.column(align=True)
            col.prop(s, "custom_sky")
            col.prop(s, "custom_horizon")
            col.prop(s, "custom_sun")
            col.prop(s, "custom_shadow")

        box = layout.box()
        row = box.row(align=True)
        row.prop(s, "shadow_tint", toggle=True)
        count = scene.get("ald_shadow_materials", 0)
        row.label(text="%d mats" % count, icon="MATERIAL")
        if s.shadow_tint:
            col = box.column(align=True)
            col.prop(s, "shadow_tint_strength")
        row = box.row(align=True)
        row.prop(s, "toon_shading", toggle=True)
        row.prop(s, "rim_light", toggle=True)
        if s.toon_shading:
            col = box.column(align=True)
            col.prop(s, "toon_strength")
        if s.rim_light:
            col = box.column(align=True)
            col.prop(s, "rim_strength")

        cam = scene.camera
        if (cam is not None and cam.data is not None
                and hasattr(cam.data, "ald")):
            box = layout.box()
            box.label(text="Camera Override", icon="CAMERA")
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

        row = layout.row(align=True)
        row.operator("ald.build", icon="PLAY")
        row.operator("ald.remove", icon="TRASH")
        layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")


_classes = (ALD_PT_scene, ALD_PT_world, ALD_PT_compositor, ALD_PT_view3d)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
