"""Operators for the World Sky Edition."""

import math

import bpy
from mathutils import Vector

from . import compositor, look, materials, palette, shots


def _sync_shadow(scene):
    settings = scene.ald
    if settings.shadow_tint or settings.toon_shading or settings.rim_light:
        strength = (settings.shadow_tint_strength
                    if settings.shadow_tint else 0.0)
        return materials.sync_scene(
            scene, palette.shadow_tint_for(scene), strength,
            settings.shadow_tint_distance)
    materials.clear_scene(scene)
    return 0


class ALD_OT_build(bpy.types.Operator):
    bl_idname = "ald.build"
    bl_label = "Build / Update Stack"
    bl_description = "Create or refresh the optional compositor stack"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        from . import ownership
        scene = context.scene
        repaired = ownership.repair(scene)
        compositor.build(scene)
        count = _sync_shadow(scene)
        text = "Anime Look Director: stack built, %d materials tinted" % count
        if repaired:
            text += " (scene ownership repaired)"
        self.report({"INFO"}, text)
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
    bl_description = "Apply the selected atmosphere to World, Sun and materials"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import ownership
        scene = context.scene
        repaired = ownership.repair(scene)
        key, _source = look.effective_palette(scene)
        if scene.ald.custom_colors:
            palette.sync_custom_colors(scene.ald, palette.preset(key))
        palette.apply_preset_style(scene, palette.effective(scene, key))
        key = look.apply(scene, force=True)
        text = "Anime Look Director: palette applied (%s)" % key
        if repaired:
            text += " (scene ownership repaired)"
        self.report({"INFO"}, text)
        return {"FINISHED"}


class ALD_OT_clear_shadow_tint(bpy.types.Operator):
    bl_idname = "ald.clear_shadow_tint"
    bl_label = "Clear Shadow Tint"
    bl_description = ("Remove the shadow tint group from every material and "
                      "disable Cel/Rim shading")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        count = materials.clear_scene(scene)
        scene.ald.toon_shading = False
        scene.ald.rim_light = False
        scene.ald.shadow_tint = False
        self.report({"INFO"},
                    "Anime Look Director: shadow tint cleared from %d materials"
                    % count)
        return {"FINISHED"}


class ALD_OT_toggle_exclude_material(bpy.types.Operator):
    bl_idname = "ald.toggle_exclude_material"
    bl_label = "Toggle Material Exclusion"
    bl_description = "Exclude or include the active material from the shadow tint sync"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj is not None and hasattr(obj, "active_material")
                and obj.active_material is not None)

    def execute(self, context):
        scene = context.scene
        mat = context.object.active_material
        if bool(mat.get("ald_exclude")):
            mat["ald_exclude"] = False
            materials.sync_one(scene, mat)
            self.report({"INFO"},
                        "Anime Look Director: %s included" % mat.name)
        else:
            mat["ald_exclude"] = True
            materials.remove_material(mat)
            self.report({"INFO"},
                        "Anime Look Director: %s excluded" % mat.name)
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


class ALD_OT_stage_backlight(bpy.types.Operator):
    bl_idname = "ald.stage_backlight"
    bl_label = "Stage Backlight"
    bl_description = "Place the sun in front of the camera and enable backlight effects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.scene.camera is not None

    def execute(self, context):
        scene = context.scene
        camera = scene.camera
        settings = scene.ald
        forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        yaw = math.degrees(math.atan2(forward.x, -forward.y))
        azimuth = yaw + 15.0
        while azimuth > 180.0:
            azimuth -= 360.0
        while azimuth < -180.0:
            azimuth += 360.0
        settings.sun_disk = True
        settings.god_rays = True
        settings.light_wrap = True
        settings.rim_light = True
        settings.sun_elevation = 12.0
        settings.sun_azimuth = azimuth
        palette.apply_sun_angles(scene, 12.0, azimuth)
        self.report({"INFO"},
                    "Anime Look Director: backlight staged at %.0f / %.0f"
                    % (settings.sun_elevation, settings.sun_azimuth))
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
                    if (space.type == "VIEW_3D"
                            and hasattr(space.shading, "use_compositor")):
                        space.shading.use_compositor = "ALWAYS"
                        count += 1
        self.report({"INFO"},
                    "Viewport compositor enabled on %d view(s)" % count)
        return {"FINISHED"}


class ALD_OT_remove_from_scene(bpy.types.Operator):
    bl_idname = "ald.remove_from_scene"
    bl_label = "Remove ALD from Scene"
    bl_description = ("Restore the World, the Sun, the materials, the passes "
                     "and the compositor to the state saved before the first "
                     "modification")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import ownership, snapshot
        scene = context.scene
        ownership.repair(scene)
        restored = snapshot.restore(scene)
        if restored:
            self.report({"INFO"},
                        "Anime Look Director: the scene was restored")
        else:
            self.report({"WARNING"},
                        "Anime Look Director: no original snapshot found; "
                        "the World/compositor was reset to a neutral state")
        return {"FINISHED"}


class ALD_OT_detach(bpy.types.Operator):
    bl_idname = "ald.detach"
    bl_label = "Detach and Keep Result"
    bl_description = ("Keep the current look but stop managing the scene: "
                     "markers and internal properties are removed; World, "
                     "materials and compositor stay")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import ownership, snapshot
        ownership.repair(context.scene)
        snapshot.detach(context.scene)
        self.report({"INFO"},
                    "Anime Look Director: the look was kept and detached")
        return {"FINISHED"}


class ALD_OT_repair_ownership(bpy.types.Operator):
    bl_idname = "ald.repair_ownership"
    bl_label = "Repair Ownership"
    bl_description = ("Give this duplicated scene its own identity and World")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import ownership
        count = ownership.repair(context.scene)
        if count:
            self.report({"INFO"},
                        "Anime Look Director: repaired the scene ownership")
        else:
            self.report({"INFO"},
                        "Anime Look Director: no duplicated scene identity")
        return {"FINISHED"}


class ALD_OT_shooting_star_add(bpy.types.Operator):
    bl_idname = "ald.shooting_star_add"
    bl_label = "Add Shooting Star"
    bl_description = "Add a controlled 2D shooting star (maximum 4)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.ald
        if len(settings.shooting_star_events) >= 4:
            self.report({"WARNING"},
                        "Anime Look Director: at most 4 shooting stars")
            return {"CANCELLED"}
        event = settings.shooting_star_events.add()
        event.name = "Shooting Star %d" % len(settings.shooting_star_events)
        event.start_frame = context.scene.frame_current
        settings.shooting_star_selected = len(settings.shooting_star_events) - 1
        look.apply_world(context.scene)
        return {"FINISHED"}


class ALD_OT_shooting_star_duplicate(bpy.types.Operator):
    bl_idname = "ald.shooting_star_duplicate"
    bl_label = "Duplicate Shooting Star"
    bl_description = "Duplicate the selected shooting star"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.ald
        events = settings.shooting_star_events
        index = settings.shooting_star_selected
        if index < 0 or index >= len(events) or len(events) >= 4:
            return {"CANCELLED"}
        source = events[index]
        event = events.add()
        for key in ("enabled", "start_frame", "duration", "azimuth",
                    "elevation", "direction", "length", "trail",
                    "thickness", "brightness", "glow", "color"):
            setattr(event, key, getattr(source, key))
        event.name = source.name + " Copy"
        event.start_frame += 12
        settings.shooting_star_selected = len(events) - 1
        look.apply_world(context.scene)
        return {"FINISHED"}


class ALD_OT_shooting_star_remove(bpy.types.Operator):
    bl_idname = "ald.shooting_star_remove"
    bl_label = "Remove Shooting Star"
    bl_description = "Remove the selected shooting star"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.ald
        events = settings.shooting_star_events
        index = settings.shooting_star_selected
        if index < 0 or index >= len(events):
            return {"CANCELLED"}
        events.remove(index)
        settings.shooting_star_selected = max(0, min(index, len(events) - 1))
        look.apply_world(context.scene)
        return {"FINISHED"}


class ALD_OT_legacy_disable(bpy.types.Operator):
    bl_idname = "ald.legacy_disable"
    bl_label = "Disable Legacy ALD Objects"
    bl_description = ("Hide the old ALD FX/cloud/smoke collections without "
                      "deleting them (reversible)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = 0
        for collection in _legacy_collections():
            collection.hide_render = True
            collection.hide_viewport = True
            count += 1
        self.report({"INFO"},
                    "Anime Look Director: %d legacy collection(s) hidden"
                    % count)
        return {"FINISHED"}


class ALD_OT_legacy_remove(bpy.types.Operator):
    bl_idname = "ald.legacy_remove"
    bl_label = "Remove Legacy ALD Objects"
    bl_description = ("Delete the old ALD FX, Spatial Clouds and smoke objects "
                      "and collections. This cannot be undone from the panel")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = 0
        for collection in list(_legacy_collections()):
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
            count += 1
        self.report({"INFO"},
                    "Anime Look Director: %d legacy collection(s) removed"
                    % count)
        return {"FINISHED"}


def _legacy_collections():
    tags = ("ald_fx", "ald_clouds", "ald_smoke")
    for collection in bpy.data.collections:
        if any(collection.get(tag) for tag in tags):
            yield collection


_classes = (ALD_OT_build, ALD_OT_remove, ALD_OT_apply_palette,
            ALD_OT_shooting_star_add, ALD_OT_shooting_star_duplicate,
            ALD_OT_shooting_star_remove,
            ALD_OT_clear_shadow_tint, ALD_OT_toggle_exclude_material,
            ALD_OT_apply_material_preset, ALD_OT_mark_shot,
            ALD_OT_stage_backlight, ALD_OT_viewport_compositor,
            ALD_OT_remove_from_scene, ALD_OT_detach,
            ALD_OT_repair_ownership, ALD_OT_legacy_disable,
            ALD_OT_legacy_remove)


def register():
    from .properties import register_classes
    register_classes(_classes)


def unregister():
    from .properties import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
