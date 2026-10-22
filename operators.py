import math

import bpy
from mathutils import Vector

from . import compositor, fx, look, materials, palette, shots


def _sync_shadow(scene):
    settings = scene.ald
    if settings.shadow_tint or settings.toon_shading or settings.rim_light:
        strength = (settings.shadow_tint_strength
                    if settings.shadow_tint else 0.0)
        return materials.sync_scene(
            scene,
            palette.shadow_tint_for(scene),
            strength,
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
        key, _source = look.effective_palette(scene)
        if scene.ald.custom_colors:
            palette.sync_custom_colors(scene.ald, palette.preset(key))
        palette.apply_preset_style(scene, palette.effective(scene, key))
        key = look.apply(scene, force=True)
        self.report({"INFO"},
                    "Anime Look Director: palette applied (%s)" % key)
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
                    "Anime Look Director: shadow tint cleared from %d materials" % count)
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
        excluded = bool(mat.get("ald_exclude"))
        if excluded:
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
                    "Anime Look Director: backlight staged at %.0f° / %.0f°"
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
                    if space.type == "VIEW_3D" and hasattr(space.shading, "use_compositor"):
                        space.shading.use_compositor = "ALWAYS"
                        count += 1
        self.report({"INFO"}, "Viewport compositor enabled on %d view(s)" % count)
        return {"FINISHED"}


def _scene_time(scene):
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    return (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)


def _show_in_viewport(context):
    """Show the FX in the viewport: the camera view and the rendered shading.

    The FX are real objects: in the solid mode they are invisible.
    """
    scene = context.scene
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            if space.region_3d is not None and scene.camera is not None:
                space.region_3d.view_perspective = "CAMERA"
            space.shading.type = "RENDERED"
            area.tag_redraw()


class ALD_OT_fx_fireworks(bpy.types.Operator):
    bl_idname = "ald.fx_fireworks"
    bl_label = "Create Fireworks"
    bl_description = "Create physically placed 3D fireworks particles in camera space"
    bl_options = {"REGISTER", "UNDO"}

    count: bpy.props.IntProperty(name="Bursts", default=3, min=1, max=8)
    seed: bpy.props.IntProperty(name="Seed", default=7, min=0, max=99999)
    distance: bpy.props.FloatProperty(name="Distance", default=110.0,
                                      min=5.0, max=400.0)
    family: bpy.props.EnumProperty(
        name="Family", items=[(key, fx.FAMILY_LABELS[key], "")
                              for key in fx.FAMILIES], default="CHRYSANTHEMUM")
    age: bpy.props.FloatProperty(name="Age", default=0.8, min=0.0, max=6.0,
                                 description="Seconds after the burst")

    def execute(self, context):
        scene = context.scene
        scene.ald.fx_age = self.age
        time = _scene_time(scene) + self.age
        count = fx.create_fireworks(scene, self.count, self.seed,
                                    self.distance, time, family=self.family)
        # The persistent events are the source of truth: they are written by
        # the creation and they rebuild the system after a reload.
        scene["ald_fx_config"] = {
            "kind": "fireworks", "count": self.count, "seed": self.seed,
            "distance": self.distance, "family": self.family, "age": self.age,
        }
        _show_in_viewport(context)
        self.report({"INFO"}, "Anime Look Director: %d fireworks created" %
                    count)
        return {"FINISHED"}


class ALD_OT_fx_meteors(bpy.types.Operator):
    bl_idname = "ald.fx_meteors"
    bl_label = "Create Shooting Stars"
    bl_description = "Create parallel radiant 3D meteor trails in camera space"
    bl_options = {"REGISTER", "UNDO"}

    count: bpy.props.IntProperty(name="Meteors", default=4, min=1, max=12)
    seed: bpy.props.IntProperty(name="Seed", default=21, min=0, max=99999)
    distance: bpy.props.FloatProperty(name="Distance", default=140.0,
                                      min=5.0, max=400.0)
    age: bpy.props.FloatProperty(name="Age", default=0.6, min=0.0, max=6.0,
                                 description="Seconds after the event")

    def execute(self, context):
        scene = context.scene
        scene.ald.fx_age = self.age
        time = _scene_time(scene) + self.age
        count = fx.create_meteors(scene, self.count, self.seed, self.distance,
                                  time)
        scene["ald_fx_config"] = {
            "kind": "meteors", "count": self.count, "seed": self.seed,
            "distance": self.distance, "age": self.age,
        }
        _show_in_viewport(context)
        self.report({"INFO"}, "Anime Look Director: %d shooting stars created" %
                    count)
        return {"FINISHED"}


class ALD_OT_remove_from_scene(bpy.types.Operator):
    bl_idname = "ald.remove_from_scene"
    bl_label = "Remove ALD from Scene"
    bl_description = ("Restore the world, the sun, the materials, the passes "
                     "and the compositor to the state saved before the first "
                     "modification, and remove the FX")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import snapshot
        scene = context.scene
        restored = snapshot.restore(scene)
        if restored:
            self.report({"INFO"},
                        "Anime Look Director: the scene was restored")
        else:
            self.report({"WARNING"},
                        "Anime Look Director: the FX were removed but the "
                        "original state was not registered, the world, the "
                        "materials and the compositor were kept")
        return {"FINISHED"}


class ALD_OT_detach(bpy.types.Operator):
    bl_idname = "ald.detach"
    bl_label = "Detach and Keep Result"
    bl_description = ("Keep the current look but stop managing the scene: the "
                     "FX objects, the markers and the internal properties are "
                     "removed, the world, the materials and the compositor stay")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import snapshot
        snapshot.detach(context.scene)
        self.report({"INFO"},
                    "Anime Look Director: the look was kept and detached")
        return {"FINISHED"}


class ALD_OT_fx_select_system(bpy.types.Operator):
    bl_idname = "ald.fx_select_system"
    bl_label = "Select System"
    bl_description = "Select the system edited in the panel"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0, min=0, max=256)

    def execute(self, context):
        context.scene.ald.fx_selected_system = self.index
        context.scene.ald.fx_selected_event = 0
        return {"FINISHED"}


class ALD_OT_fx_select_event(bpy.types.Operator):
    bl_idname = "ald.fx_select_event"
    bl_label = "Select Event"
    bl_description = "Select the event edited in the panel"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=0, min=0, max=256)

    def execute(self, context):
        context.scene.ald.fx_selected_event = self.index
        return {"FINISHED"}


class ALD_OT_fx_duplicate_system(bpy.types.Operator):
    bl_idname = "ald.fx_duplicate_system"
    bl_label = "Duplicate System"
    bl_description = "Duplicate the selected FX system and its events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import uuid
        settings = context.scene.ald
        index = int(settings.fx_selected_system)
        if index < 0 or index >= len(settings.fx_systems):
            return {"CANCELLED"}
        source = settings.fx_systems[index]
        copy = settings.fx_systems.add()
        copy.uid = uuid.uuid4().hex
        copy.kind = source.kind
        copy.enabled = source.enabled
        copy.seed = source.seed
        copy.timing_mode = source.timing_mode
        copy.origin_frame = source.origin_frame
        copy.origin_time = source.origin_time
        copy.material_profile = source.material_profile
        copy.glow_profile = source.glow_profile
        copy.isolation_mode = source.isolation_mode
        for event in source.events:
            new_event = copy.events.add()
            new_event.uid = uuid.uuid4().hex
            new_event.kind = event.kind
            new_event.enabled = event.enabled
            new_event.seed = event.seed
            new_event.birth = event.birth
            new_event.family = event.family
            new_event.size = event.size
            new_event.count = event.count
            new_event.pistil = event.pistil
            new_event.sparks = event.sparks
            new_event.launch_mode = event.launch_mode
            new_event.launcher = tuple(event.launcher)
            new_event.target = tuple(event.target)
            new_event.direction = tuple(event.direction)
            new_event.speed = event.speed
            new_event.life = event.life
            new_event.duration = event.duration
            new_event.glow = event.glow
        settings.fx_selected_system = len(settings.fx_systems) - 1
        self.report({"INFO"}, "Anime Look Director: the system was duplicated")
        return {"FINISHED"}


class ALD_OT_fx_remove_system(bpy.types.Operator):
    bl_idname = "ald.fx_remove_system"
    bl_label = "Remove System"
    bl_description = "Remove the selected FX system and its events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.ald
        index = int(settings.fx_selected_system)
        if index < 0 or index >= len(settings.fx_systems):
            return {"CANCELLED"}
        settings.fx_systems.remove(index)
        settings.fx_selected_system = max(0, index - 1)
        return {"FINISHED"}


class ALD_OT_fx_bolide(bpy.types.Operator):
    bl_idname = "ald.fx_bolide"
    bl_label = "Create Hero Meteor"
    bl_description = ("Create a cinematic bolide: bigger, brighter, with a "
                     "long persistent train")
    bl_options = {"REGISTER", "UNDO"}

    count: bpy.props.IntProperty(name="Bolides", default=1, min=1, max=4)
    seed: bpy.props.IntProperty(name="Seed", default=33, min=0, max=99999)
    distance: bpy.props.FloatProperty(name="Distance", default=90.0,
                                      min=5.0, max=400.0)
    age: bpy.props.FloatProperty(name="Age", default=0.6, min=0.0, max=6.0,
                                 description="Seconds after the event")

    def execute(self, context):
        scene = context.scene
        scene.ald.fx_age = self.age
        time = _scene_time(scene) + self.age
        count = fx.create_meteors(scene, self.count, self.seed, self.distance,
                                  time, kind="BOLIDE")
        scene["ald_fx_config"] = {
            "kind": "meteors", "count": self.count, "seed": self.seed,
            "distance": self.distance, "age": self.age, "preset": "BOLIDE",
        }
        _show_in_viewport(context)
        self.report({"INFO"},
                    "Anime Look Director: %d bolides created" % count)
        return {"FINISHED"}


class ALD_OT_fx_anchor_create(bpy.types.Operator):
    bl_idname = "ald.fx_anchor_create"
    bl_label = "Create Sky/FX Anchor"
    bl_description = ("Create the ALD Sky/FX Anchor empty: the persistent "
                     "world reference for FX placement (origin, vertical "
                     "axis, ground elevation, units scale)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        settings = scene.ald
        name = "ALD Sky/FX Anchor"
        anchor = bpy.data.objects.get(name)
        if anchor is None:
            anchor = bpy.data.objects.new(name, None)
            anchor.empty_display_type = "PLAIN_AXES"
            anchor.empty_display_size = 2.0
            scene.collection.objects.link(anchor)
        anchor["ald_fx_anchor"] = True
        anchor["ald_fx_axis"] = settings.fx_anchor_axis
        anchor["ald_fx_ground"] = float(settings.fx_anchor_ground_elevation)
        anchor["ald_fx_scale"] = float(settings.fx_anchor_units_scale)
        settings.fx_anchor_created = True
        self.report({"INFO"},
                    "Anime Look Director: sky/FX anchor created")
        return {"FINISHED"}


class ALD_OT_fx_ground_create(bpy.types.Operator):
    bl_idname = "ald.fx_ground_create"
    bl_label = "Create Ground Plane"
    bl_description = ("Create a mesh plane at the anchor elevation to serve "
                     "as the terrain reference for conflict checks")
    bl_options = {"REGISTER", "UNDO"}

    size: bpy.props.FloatProperty(name="Size", default=200.0, min=1.0)

    def execute(self, context):
        scene = context.scene
        settings = scene.ald
        name = "ALD FX Ground"
        ground = bpy.data.objects.get(name)
        if ground is None:
            mesh = bpy.data.meshes.new(name)
            from mathutils import Vector
            bpy.ops.mesh.primitive_plane_add(size=self.size)
            ground = context.active_object
            ground.name = name
            ground["ald_fx_ground"] = True
            # Place at the anchor elevation along the vertical axis.
            axis = settings.fx_anchor_axis
            axis_index = {"Z": 2, "Y": 1, "X": 0,
                          "-Z": 2, "-Y": 1, "-X": 0}.get(axis, 2)
            sign = -1.0 if axis.startswith("-") else 1.0
            ground.location = (0.0, 0.0, 0.0)
            ground.location[axis_index] = sign * float(
                settings.fx_anchor_ground_elevation)
        settings.fx_ground_object = ground
        self.report({"INFO"},
                    "Anime Look Director: ground plane created")
        return {"FINISHED"}


class ALD_OT_fx_update(bpy.types.Operator):
    bl_idname = "ald.fx_update"
    bl_label = "Update FX"
    bl_description = ("Rebuild the FX systems: a moved launcher or a new "
                     "setting is applied to the shot")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        config = scene.get("ald_fx_config")
        if not config:
            self.report({"WARNING"}, "Anime Look Director: no FX system")
            return {"CANCELLED"}
        fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
        age = float(getattr(scene.ald, "fx_age", config.get("age", 0.8)))
        time = (scene.frame_current + scene.frame_subframe) / max(fps, 1e-6)
        time += age
        if config.get("kind") == "meteors":
            fx.create_meteors(scene, config.get("count", 4),
                              config.get("seed", 21),
                              config.get("distance", 140.0), time,
                              kind=config.get("preset", "METEOR"))
        else:
            fx.create_fireworks(scene, config.get("count", 3),
                                config.get("seed", 7),
                                config.get("distance", 110.0), time,
                                family=config.get("family", "CHRYSANTHEMUM"))
        return {"FINISHED"}


class ALD_OT_fx_clear(bpy.types.Operator):
    bl_idname = "ald.fx_clear"
    bl_label = "Clear FX"
    bl_description = "Remove temporary fireworks and shooting-star objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        count = fx.clear(scene)
        scene["ald_fx_config"] = None
        self.report({"INFO"}, "Anime Look Director: %d FX objects removed" %
                    count)
        return {"FINISHED"}


class ALD_OT_fx_clear_kind(bpy.types.Operator):
    bl_idname = "ald.fx_clear_kind"
    bl_label = "Clear FX System"
    bl_description = "Remove one FX system (fireworks or meteors) from the scene"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Kind", items=[("fireworks", "Fireworks", ""),
                            ("meteors", "Meteors", "")], default="fireworks")

    def execute(self, context):
        count = fx.clear(context.scene, kind=self.kind)
        self.report({"INFO"}, "Anime Look Director: %d FX objects removed" %
                    count)
        return {"FINISHED"}


_classes = (ALD_OT_build, ALD_OT_remove, ALD_OT_apply_palette,
            ALD_OT_clear_shadow_tint, ALD_OT_toggle_exclude_material,
            ALD_OT_apply_material_preset, ALD_OT_mark_shot,
            ALD_OT_stage_backlight, ALD_OT_viewport_compositor,
            ALD_OT_fx_fireworks, ALD_OT_fx_meteors, ALD_OT_fx_bolide,
            ALD_OT_fx_anchor_create, ALD_OT_fx_ground_create,
            ALD_OT_fx_update,
            ALD_OT_fx_clear, ALD_OT_fx_clear_kind, ALD_OT_fx_select_system,
            ALD_OT_fx_select_event, ALD_OT_fx_duplicate_system,
            ALD_OT_fx_remove_system, ALD_OT_remove_from_scene,
            ALD_OT_detach)


def register():
    from .properties import register_classes
    register_classes(_classes)


def unregister():
    from .properties import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
