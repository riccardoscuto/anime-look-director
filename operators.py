import bpy

from . import compositor, materials, palette, shots


def _sync_shadow(scene):
    settings = scene.ald
    if settings.shadow_tint:
        return materials.sync_scene(
            scene,
            palette.shadow_tint_for(scene),
            settings.shadow_tint_strength,
            settings.shadow_tint_distance,
        )
    materials.clear_scene(scene)
    return 0


class ALD_OT_build(bpy.types.Operator):
    bl_idname = "ald.build"
    bl_label = "Build / Update Stack"
    bl_description = "Create or refresh the non-destructive anime compositor stack"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene
        compositor.build(scene)
        count = _sync_shadow(scene)
        self.report({"INFO"},
                    "Anime Look Director: stack built, %d materials tinted" % count)
        return {"FINISHED"}


class ALD_OT_remove(bpy.types.Operator):
    bl_idname = "ald.remove"
    bl_label = "Remove Stack"
    bl_description = "Unassign and delete the Anime Look Director compositor stack"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        compositor.remove(context.scene)
        self.report({"INFO"}, "Anime Look Director: stack removed")
        return {"FINISHED"}


class ALD_OT_apply_palette(bpy.types.Operator):
    bl_idname = "ald.apply_palette"
    bl_label = "Apply Palette"
    bl_description = "Apply the selected atmosphere to world, sun, shadows and halation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        palette.apply_palette(scene, scene.ald.palette)
        count = _sync_shadow(scene)
        if scene.compositing_node_group is not None:
            compositor.build(scene)
        self.report({"INFO"},
                    "Anime Look Director: palette applied, %d materials tinted" % count)
        return {"FINISHED"}


class ALD_OT_clear_shadow_tint(bpy.types.Operator):
    bl_idname = "ald.clear_shadow_tint"
    bl_label = "Clear Shadow Tint"
    bl_description = "Remove the shadow tint from every material and restore Base Color"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = materials.clear_scene(context.scene)
        context.scene.ald.shadow_tint = False
        self.report({"INFO"},
                    "Anime Look Director: shadow tint cleared from %d materials" % count)
        return {"FINISHED"}


class ALD_OT_apply_material_preset(bpy.types.Operator):
    bl_idname = "ald.apply_material_preset"
    bl_label = "Apply Material Preset"
    bl_description = "Create or assign the selected material preset to selected objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene
        count, mat = materials.apply_preset_to_selected(
            scene, scene.ald.material_preset)
        if count == 0:
            self.report({"WARNING"},
                        "Anime Look Director: select a mesh object first")
            return {"CANCELLED"}
        self.report({"INFO"},
                    "Anime Look Director: %s applied to %d object(s)"
                    % (mat.name, count))
        return {"FINISHED"}


class ALD_OT_mark_shot(bpy.types.Operator):
    bl_idname = "ald.mark_shot"
    bl_label = "Mark Shot"
    bl_description = "Add or update a palette marker at the current frame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene
        key = scene.ald.palette
        name = shots.marker_name(key)
        marker = next((m for m in scene.timeline_markers
                       if m.frame == scene.frame_current
                       and shots.palette_from_marker(m.name)), None)
        if marker is None:
            scene.timeline_markers.new(name, frame=scene.frame_current)
        else:
            marker.name = name

        was_enabled = scene.ald.use_shot_markers
        scene.ald.use_shot_markers = True
        if was_enabled:
            shots.apply_for_frame(scene, force=True)
        self.report({"INFO"},
                    "Anime Look Director: shot marker at frame %d"
                    % scene.frame_current)
        return {"FINISHED"}


class ALD_OT_viewport_compositor(bpy.types.Operator):
    bl_idname = "ald.viewport_compositor"
    bl_label = "Enable Viewport Compositor"
    bl_description = "Set every 3D Viewport shading to always show the compositor result"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = 0
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D" and hasattr(space.shading, "use_compositor"):
                        space.shading.use_compositor = "ALWAYS"
                        count += 1
        self.report({"INFO"}, "Viewport compositor enabled on %d view(s)" % count)
        return {"FINISHED"}


_classes = (ALD_OT_build, ALD_OT_remove, ALD_OT_apply_palette,
            ALD_OT_clear_shadow_tint, ALD_OT_apply_material_preset,
            ALD_OT_mark_shot, ALD_OT_viewport_compositor)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
