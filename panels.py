import bpy


class ALD_PT_scene(bpy.types.Panel):
    bl_label = "Anime Look Director"
    bl_idname = "ALD_PT_scene"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

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

        box = layout.box()
        box.label(text="Compositor Stack", icon="NODETREE")
        row = box.row(align=True)
        row.prop(s, "halation", toggle=True)
        row.prop(s, "painterly", toggle=True)
        row.prop(s, "dispersion", toggle=True)
        col = box.column(align=True)
        col.prop(s, "halation_strength")
        col.prop(s, "kuwahara_size")
        col.prop(s, "dispersion_amount")
        col.separator()
        col.label(text="Kuwahara depth range")
        col.prop(s, "depth_near")
        col.prop(s, "depth_far")

        row = layout.row(align=True)
        row.operator("ald.build", icon="PLAY")
        row.operator("ald.remove", icon="TRASH")
        layout.operator("ald.viewport_compositor", icon="RESTRICT_VIEW_OFF")

        if scene.compositing_node_group is None:
            layout.label(text="Stack not assigned", icon="INFO")
        else:
            layout.label(text="Stack: " + scene.compositing_node_group.name, icon="CHECKMARK")


_classes = (ALD_PT_scene,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
