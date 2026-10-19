# Technical notes — Blender 5.1.2 spikes (2026-10-19)

Empirical results from live runtime tests. Target machine: Windows, Blender 5.1.2,
Python 3.13.9, NumPy 2.3.4, no SciPy/OpenCV inside Blender.

## Compositor
- `scene.compositing_node_group` exists and is assignable; `scene.node_tree` is `None`.
- `CompositorNodeComposite` does not exist; the output is `NodeGroupOutput` with an
  interface socket (`ng.interface.new_socket(..., in_out="OUTPUT", socket_type="NodeSocketColor")`).
- Glare node: properties are **inputs**. `Type` accepts `Bloom`, `Streaks`, `Fog Glow`,
  `Sun Beams`. Also available: `Threshold`, `Strength`, `Size`, `Saturation`, `Tint`,
  `Sun Position`, `Streaks`, `Iterations`, etc.
- `CompositorNodeKuwahara` exists: `Type` = `Classic` / `Anisotropic`, `Size`
  (default 6), `Uniformity`, `Sharpness`, `Eccentricity`, `High Precision`.
- `CompositorNodeLensdist` exists (`Distortion`, `Dispersion`, `Fit`).
- Render Layers outputs: `Image`, `Alpha` and — when passes are enabled —
  `Depth`, `Mist`. `view_layer.use_pass_z` / `use_pass_mist` are available.
- Generic `ShaderNodeMix`, `ShaderNodeMath`, `ShaderNodeMapRange` can be created in
  a compositor tree. `ShaderNodeSeparateColor` cannot; use `CompositorNodeSeparateColor`.
- Minimal 64×64 EEVEE render through a compositor group completed successfully.
- Viewport compositor: `View3DShading.use_compositor` enum = `DISABLED`, `CAMERA`, `ALWAYS`.

## Drivers
- Simple expressions (`1+2`, `frame/10`) work even with
  `preferences.filepaths.use_scripts_auto_execute = False`.
- Drivers on node sockets work: ShaderNodeValue output `default_value`, vector
  component (`Mapping.Location` index 0), Node Group input socket.
- `TRANSFORMS` driver variables: `LOCAL_SPACE` returned **0.0** for an Empty's
  rotation; `WORLD_SPACE` returned the correct value (1.0). Use `WORLD_SPACE`.
- `Texture Coordinate` node's `object` can target a control Empty.

## NumPy / images
- Chamfer distance transform in NumPy: 2048×2048 mask in **0.117 s** (3 sweeps).
- Image write via `image.pixels.foreach_set`: 1024×1024 RGBA in **0.003 s**;
  `image.pack()` works.

## Multi-channel painting
- Four images + packing work. `bpy.ops.paint.image_paint.poll()` is False without
  an active paint context, so brush UX must be tested in a GUI session.
- `ImagePaint` exposes `brush`, `canvas` in 5.1.

## Known environment noise
- `physical-starlight-atmosphere` render handlers raise when `scene.world` is None.
- `flip_fluids_addon` raises on file load in this profile (unrelated to this addon).

## v0.2 spikes (2026-10-19)

### Compositor nodes
- `CompositorNodeBlur`: `Size` is `FLOAT` with 2 components (default `(0, 0)`),
  not a scalar. `Type` enum: `Flat`, `Tent`, `Quadratic`, `Cubic`, `Gaussian`,
  `Fast Gaussian`, `Catrom`, `Mitch`. `Extend Bounds` is a boolean input.
- `CompositorNodeDilateErode`: `Type` = `Steps` / `Threshold` / `Distance` /
  `Feather`; `Falloff` = `Smooth` / `Sphere` / `Root` / `Inverse Square` /
  `Sharp` / `Linear`. Not needed for the current light wrap.
- `CompositorNodeSetAlpha`: `Type` = `Apply Mask` / `Replace Alpha`.
- `CompositorNodeAlphaOver` inputs: `Background`, `Foreground`, `Factor`, `Type`,
  `Straight Alpha`.
- `CompositorNodeRGB` has a single output named `Color` (no Alpha); pair it with
  `SetAlpha` when a matte image is needed.
- `CompositorNodeSeparateColor` outputs `Red`, `Green`, `Blue`, `Alpha`.

### Light wrap mask
- With an opaque world, `Render Layers.Alpha` is **1 across the whole frame**, so
  an alpha-derived silhouette is empty.
- Raw Depth pass values measured with the default camera: **EEVEE = 1000.55**
  (camera `clip_end` 1000 + 0.55), **Cycles = 1e10**. A fixed 1e6 threshold therefore
  fails on EEVEE; use the camera clip end read at build time.
- Outer silhouette mask: `Depth < clip_end` multiplied by `Alpha`, then
  `mask - blur(mask)` for the inner band.
- Object-on-object silhouettes are found with a depth-discontinuity mask:
  normalize depth by 100 m, blur 4 px, `abs(depth - blurred) * 100`, subtract a
  0.05 m threshold, blur by the wrap size, multiply by the geometry mask. The
  result is combined with the outer band via `MAXIMUM`.
- **Premultiplication matters**: the render is premultiplied. `SetAlpha` replaces
  alpha but leaves RGB full, so a premultiplied `AlphaOver` leaks the blurred RGB
  over the whole frame. Set `AlphaOver.Straight Alpha = True` (or premultiply RGB
  explicitly). This was the cause of a global haze in the first look-dev pass.
- Blur the foreground image with `Extend Bounds` on, replace its alpha with the
  combined edge mask, then `AlphaOver` at the chosen strength.
- Gate pixel evidence at 128×128: shadow tint changes 1.8 % of pixels; light wrap
  changes 15.4 % of pixels and stays below the 80 % global-blur guard.

### World gradient
- `Texture Coordinate.Generated` works in world shaders and gives the view
  direction; `Separate XYZ.Z` runs -1..1.
- A ColorRamp has static element colors: setting the *group input node* defaults
  does not drive ramp stops. Build the sky/horizon/ground blend with `ShaderNodeMix`
  (RGBA) plus Map Range weights so palette colors are socket-driven.
- Horizon warp: map Z to 0..1, then remap `horizon - softness/2 .. horizon +
  softness/2` to 0..1, then blend ground→horizon (0..0.5) and horizon→sky (0.5..1).

### Shadow tint
- `ShaderNodeAmbientOcclusion` works in **EEVEE Next and Cycles** on 5.1.2. A
  sphere-on-plane emission test (AO → Emission) produced min 0.4627 in EEVEE and
  0.3922 in Cycles, so the node returns real occlusion in both engines.
- Group: `factor = (1 - AO) * strength`, then Mix Base Color toward the palette
  shadow color. Distance and strength are group inputs.
- Insertion is reversible: remember whether Base Color was linked and, when not,
  store its default color in an ID property (`ald_st_color`). Removal restores the
  upstream link or the stored value.
- Insert only into materials with a Principled BSDF; skip linked-library materials.

### Testing notes
- Blender may return different Python wrappers for the same node after an operator
  call; `link.from_node is node` can be False. Compare `as_pointer()`.
- The gate now includes render-level checks: three 128×128 EEVEE renders (base,
  shadow tint, light wrap) with NumPy pixel diffs. Structural checks alone missed a
  light-wrap bug that blurred the whole image.
- The MCP/Blender window screenshot returns a black image when the window is
  positioned off-screen (e.g. x=1912 on a 1920-wide desktop). Move the window
  on-screen before capturing; `render_viewport_to_path` still works.
- The panel is taller than the Scene tab; `bl_order = -10` puts it above the
  default Scene panels. Keep the toggle rows at two buttons to avoid clipped labels.
- `preset_dev/lookdev.py` builds a 2×2 contact sheet by loading the rendered PNGs
  into NumPy and writing a new image; its pixels are linear, so the sheet saves
  with the expected sRGB transform.

### v0.2.1 notes
- **Auto Sun**: a palette apply creates `ALD | Sun` (tagged `ald_auto_sun`) only
  when the scene has no SUN light. It is created once and reused; disabling
  `auto_sun` stops creation but leaves an existing sun in place.
- **Per-scene stacks**: one compositor group per scene. The first scene keeps the
  base name `ALD | Compositor Stack`; later scenes get
  `ALD | Compositor Stack | <scene>`. The group carries an `ald_scene` tag so scene
  renames still find the right stack, while `Render Layers.Scene` points at the
  owning scene. `ald.remove` unassigns only the current scene and deletes the
  group only if no other scene references it.
- A legacy single group without `ald_scene` is claimed by the first scene that
  builds, so upgrading a 0.2.0 file does not duplicate it.
- Rebuild timing on the target machine: min 5.05 ms, average 5.85 ms, max 8.63 ms
  over 20 builds. Slider updates rebuild synchronously; no debounce needed.
- The gate now creates a second scene and checks that both stacks exist, that each
  Render Layers node points at its own scene, and that removing one leaves the
  other intact.

### v0.3 notes
- **Glare Sun Beams**: `Sun Position` is a 2-component vector in normalized screen
  space, **0..1 with y up**. A 256×256 test with the bright source at screen
  center rendered a radial glow at `(0.5, 0.5)`, a cone at `(0.2, 0.5)` and a
  vertical beam at `(0.5, 0.8)`, confirming the convention.
- **Sun projection**: take the sun light's forward direction
  (`matrix_world.to_quaternion() @ (0, 0, -1)`), place a point 1000 m along the
  opposite direction from the camera and project it with
  `bpy_extras.object_utils.world_to_camera_view`. If `co.z <= 0` the sun is behind
  the camera and the God Rays node is skipped. The position is baked at build time.
- **Shot markers**: a `frame_change_pre` handler reads the last
  `ALD:<PALETTE>` marker at or before the current frame. `ald_active_shot` prevents
  re-applying the same palette every frame; `Mark Shot` creates/updates a marker at
  the current frame and enables the opt-in toggle. Changing `settings.palette`
  reuses the existing `_on_palette` path.
- **Material presets**: `ALD | Skin/Hair/Fabric/Metal` are shared fake-user
  materials with Base Color/Roughness/Metallic. Applying to selected objects
  appends the slot only once and runs the shadow-tint sync; linked objects/data are
  skipped. Re-applying updates the tint node's stored Color so the preset stays
  correct.
- **UI**: World & Shadows and Compositor Stack are sub-panels (`bl_parent_id`);
  the parent keeps Atmosphere, Material Presets, Build/Remove, viewport and stack
  status. Children can be collapsed when the panel is too tall.
- **Gate**: verifies the Sun Beams node exists and its projected position is
  ~`(0.5, 0.5)` for a sun placed in front of a test camera, applies shot markers A
  and B and checks the world changed, and applies the Metal/Skin presets including
  shadow tint and slot idempotency.

### v0.3.1 notes
- **God Rays refresh**: `update_god_rays(scene)` looks up the existing Sun Beams
  node and rewrites `Sun Position` and `Strength` on `frame_change_pre`; it does
  not rebuild the stack. When the projected sun is behind the camera it sets
  `Strength` to 0 and restores the setting value when the sun comes back. Manual
  sun/camera moves between frames still need Build.
- Sun Beams now use `Size` from `god_rays_size` (default 0.5), 6 iterations and
  fade 0.95. The handler is registered by `compositor.register()` after the shot
  marker handler, so a palette change and its rebuild happen first.
- **Emission preset**: `ALD | Emission` sets `Emission Color` and
  `Emission Strength` (3.0); other presets reset emission strength to 0 so a
  reused preset material cannot keep a stale glow.
- Gate additions: God Rays mute/restore after rotating the sun behind/in front of
  the camera, and the Emission preset must have a positive Emission Strength.
