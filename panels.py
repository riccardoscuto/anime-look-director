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
        count = scene.get("ald_shadow_materials", 0)

        box = layout.box()
        box.label(text="Atmosphere", icon="WORLD")
        box.prop(s, "palette", text="")
        box.operator("ald.apply_palette", icon="FILE_REFRESH")

        box = layout.box()
        box.label(text="World & Shadows", icon="LIGHT_SUN")
        row = box.row()
        row.prop(s, "world_gradient", toggle=True)
        if s.world_gradient:
            col = box.column(align=True)
            col.prop(s, "horizon_offset")
            col.prop(s, "horizon_softness")

        box.separator()
        row = box.row(align=True)
        row.prop(s, "shadow_tint", toggle=True)
        row.label(text="%d mats" % count, icon="MATERIAL")
        row.operator("ald.clear_shadow_tint", text="", icon="X")
        if s.shadow_tint:
            col = box.column(align=True)
            col.prop(s, "shadow_tint_strength")
            col.prop(s, "shadow_tint_distance")

        box = layout.box()
        row = box.row()
        row.label(text="Compositor Stack", icon="NODETREE")
        if scene.compositing_node_group is None:
            row.label(text="Not assigned", icon="INFO")
        else:
            row.label(text="Assigned", icon="CHECKMARK")
        row = box.row(align=True)
        row.prop(s, "halation", toggle=True)
        row.prop(s, "painterly", toggle=True)
        row = box.row(align=True)
        row.prop(s, "dispersion", toggle=True)
        row.prop(s, "light_wrap", toggle=True)

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

        col.separator()
        col.label(text="Kuwahara depth range")
        col.prop(s, "depth_near")
        col.prop(s, "depth_far")

        row = layout.row(align=True)
        row.operator("ald.build", icon="PLAY")
        row.operator("ald.remove", icon="TRASH")
        layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")


_classes = (ALD_PT_scene,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
