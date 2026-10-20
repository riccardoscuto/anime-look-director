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

### v0.3.2 notes (Step 1)
- **In-place slider updates**: `compositor.update_params(scene)` finds nodes by
  fixed names (`ALD | Halation`, `ALD | Kuwahara`, `ALD | Depth Range`,
  `ALD | Light Wrap Blur/Mask/Edge/Over`, `ALD | Lens`, `ALD | God Rays`) and
  rewrites only their sockets. Measured on the live scene: **0.34 ms average**
  (max 0.53 ms) vs **5.28 ms average** (max 6.72 ms) for a full rebuild. The
  compositor shader is not recompiled on slider drags.
- Float properties call `_on_params`; booleans and the palette still call
  `_on_stack` / rebuild because the node topology or tints change.
- **God Rays fallback**: when enabled with the sun behind the camera, the Sun
  Beams node is still created at `(0.5, 0.5)` with strength 0. The frame handler
  can then find it and bring it in when the sun enters the frame.
- **Shadow tint MULTIPLY**: the Mix node now uses `MULTIPLY`, and palette
  `shadow_tint` values are normalized multiplier hues (max component 1), so a
  texture connected to Base Color keeps its pattern in shadowed areas instead of
  being replaced by a flat color. The gate checks the blend type.
- **Sidebar N panel**: `ALD_PT_view3d` in `VIEW_3D > UI > Anime Look`; in tests,
  `region.active_panel_category = "Anime Look"` selects the tab (there is no
  `SpaceView3D` category property).
- Gate additions: in-place parameter updates keep the node count constant and
  update Kuwahara/Halation/Light Wrap/Depth/Lens values; God Rays build with the
  sun behind; shadow tint is multiplicative.

### v0.4.0 notes (Step 2)
- **Sun disk**: the world shader compares `Generated` (view direction) with
  `Sun Direction = -light_direction`. The disk uses `cos(radius)` thresholds:
  `Sun Inner = cos(radius)`, `Sun Outer = cos(radius + 0.25*radius)` and a
  smoothstep MapRange. A 2.5° disk at strength 12 rendered white through AgX; at
  1.5°/6.0 it keeps a warm core and a soft halo. The disk is behind clouds (cloud
  mix overlays it).
- **First-apply order matters**: `ensure_sun` must run before `_apply_gradient`,
  otherwise a freshly created scene writes no sun direction/strength on the first
  palette apply. The frame handler runs on `frame_change_post` so sun matrices are
  evaluated before projection.
- **Clouds**: the first version used 3D noise + a static 3-tone ramp and looked
  like smoke. A plane projection (`x/z`, `y/z`) gave repeating rows/camo, even
  with clamped coordinates. The final version uses two 3D Noise layers on
  `Generated`, weights 0.75/0.25, coverage 0.48–0.56 and narrow tone MapRanges
  0.46–0.48 / 0.57–0.59; clouds read as soft stylized masses without projection
  artifacts. Palette colors are group sockets (Cloud Shadow/Mid/Light).
- **Ink lines**: `_depth_edges` was generalized to accept `band_size` and
  `edge_size`; light wrap uses a wide band, ink uses `band_size=0` plus a 1.5–2 px
  depth blur. The line is a `MULTIPLY` mix with `shadow_tint * 0.25`. Gate pixel
  evidence: ink changes ~2.5 % of the 128×128 frame, edge-local.
- **Custom colors**: `effective(scene, key)` merges overrides into the preset dict;
  `shadow_tint_for(scene)` is the single source for material tint sync. The gate
  toggles custom colors and verifies world, sun and material tint, then restores
  the preset.
- **New presets**: SAKURA_SPRING (soft pink horizon, blue sky, warm light) and
  TWILIGHT_DUSK (deep blue/indigo sky, orange horizon). Look-dev now renders six
  palettes in a 3×2 sheet.
- Gate: world sun direction/strength, sun-disk toggle, clouds toggle, ink node and
  pixel test, custom colors and preset restore.

### v0.5.0 notes (Step 3)
- **Directional terminator**: `Geometry.Normal` is world space; `Sun Direction` is
  `-light_direction` (toward the sun). `N·L` feeds a MapRange from
  `-sharpness..sharpness` to `1..0`, multiplied by Cel Shadow strength and
  combined with the AO factor via `MAXIMUM`. The mix remains a `MULTIPLY` tint, so
  textures keep their detail.
- **Rim light**: the first implementation fed raw `Layer Weight.Facing` into the
  rim mask; with strength 0.8 it changed **68 %** of the 128×128 gate frame
  (broad haze over the ground). The fix routes Facing through a MapRange
  `1 - Rim Width .. 1` before multiplying by `max(N·L, 0)`, `Rim Strength` and
  `Sun Color`. Gate ratio is now **6.5 %**, edge-local. Terminator ratio is ~1.3 %.
- **Sun sync**: `materials._look(scene)` builds the sun direction/color and
  toon/rim values; `sync_material` writes them to the group node. `update_sun`
  refreshes every tinted material on `frame_change_post`, no rebuild. The sun must
  exist before the first palette apply (already fixed in 0.4.0).
- **Upgrade safety**: the Shadow Tint interface is extended with `_ensure_socket`
  and is **not cleared**, so a texture link into the group node's `Color` input
  survives a v0.4 → v0.5 group rebuild.
- **Hair angel ring**: `ALD | Hair` gets `+0.3` rim strength and `Rim Width` capped
  at 0.35 in `_set_look`; the gate checks the boost.
- Defaults tuned by look-dev: Cel Shadow 0.75, Terminator 0.035, Rim Strength
  0.45, Rim Width 0.4. The six-palette sheet shows a readable terminator on the
  spheres while keeping soft Ghibli-style light.
- The shadow-tint pixel test disables toon/rim so the AO comparison stays isolated;
  separate toon and rim renders validate the new stages.

### v0.6.0 notes (per-camera overrides)
- **Effective palette** precedence: camera override > `ALD:` marker > scene base.
  `look.py` owns resolution/apply; `look.apply_world` only touches world/sun for
  horizon/cloud controls, while `look.apply` also syncs materials and rebuilds the
  stack when needed.
- **Base palette invariant**: markers and camera overrides no longer write
  `Scene.ald.palette`. `look.apply` stores `ald_effective_palette` and
  `ald_effective_source`; `shadow_tint_for` and compositor glare tints read the
  effective key. `Mark Shot` still uses the base dropdown, so the artist sets the
  palette to be marked explicitly.
- **Camera data property**: `Camera.ald` holds `override` and `palette`. The camera
  switch handler caches `(camera_name, override_key)`; if both the previous and
  current cameras have no override it returns without rebuilding, so temporary test
  cameras do not trigger palette resets.
- **Registration trap**: `bpy.data` is `_RestrictData` during add-on registration.
  Building the camera cache from `bpy.data.scenes` at register time raises; the
  cache is now initialized lazily and the handler tolerates a missing previous
  state.
- Gate: camera B with Rainy override, switch to Sakura, back to A restores the base
  palette; the base palette value is never mutated. Marker test now checks
  `ald_effective_palette`/`source` and base invariance instead of `settings.palette`.
- UI: Camera Override box in Scene > World & Shadows and Sidebar N; effective look
  label in the main panel.

### v0.6.1 notes
- **Normalized sun disk**: `Generated` (view direction) and `Sun Direction` now
  pass through `Vector Math → Normalize` before `DOT_PRODUCT`. The sun threshold is
  `cos(radius)` ~0.9997; without unit vectors the disk could disappear or deform.
  World group marker bumped to `ald_build = 4`.
- **Real-time viewport**: `cameras._on_depsgraph` now also calls
  `update_transforms(scene)`, which caches the sun Z axis/color and the camera
  Z/location/lens/shift/sensor. On a change it calls `palette.update_sun_controls`,
  `materials.update_sun` and `compositor.update_god_rays`, all socket-only. Rotating
  the sun with R or moving the camera updates sky disk, God Rays and cel shading
  without Apply Palette or a frame change.
- **Ink gain**: for `band_size == 0` (ink), the 0.05 m threshold is multiplied by
  8 and clamped. Outer silhouettes were already 1.0; internal 15–20 cm steps were
  ~0.1 and nearly invisible. Gate ink ratio moved from 2.46 % to 2.76 %.
- **Custom color sync**: `compositor.update_params` now updates the halation and
  god-ray `Tint` (via `_glare_color`, using `custom_sun` when custom colors are on)
  and `ALD | Ink Color` (shadow tint × 0.25). `_on_custom_color` calls it, so the
  color pickers update bloom, rays and ink live.
- **Rim emission**: Shadow Tint has a second output `Emission` = rim color +
  0.12 × shadow tint × combined factor. `_wire_emission` connects it to Principled
  `Emission Color`, sets `Emission Strength` to `rim_emission` (default 0.5), and
  stores the original color/strength in `ald_em_color`/`ald_em_strength`. Materials
  with emission strength >0.05 or a different emission link are skipped; clearing
  shadow tint removes the link and restores the originals. This keeps the rim
  visible in backlight (emission bypasses diffuse attenuation).
- Gate: normalized nodes present; `cameras.update_transforms` updates world and
  material sun directions and then skips an unchanged state; ink gain node = 8;
  custom sun/shadow reach halation/ink; emission is wired and restored.
- Gate pixel ratios: ink 2.76 %, rim 8.09 %, toon 1.31 %; look-dev six-palette sheet
  shows brighter rims and preserved terminator shading.

### v0.6.2 notes
- `UILayout.label(icon="CAMERA")` raises: Blender 5.1's icon enum has
  `CAMERA_DATA`, not `CAMERA`. The invalid enum aborted every panel draw, so the
  traceback surfaced after Remove Stack / Clear Shadow Tint forced a redraw; the
  operators themselves were fine.
- Both Camera Override labels (Scene panel and Sidebar N) now use `CAMERA_DATA`.
  Panel draw verified with a screenshot after the fix.
- Valid icon identifiers can be checked at runtime with
  `bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items`.
  The headless gate does not execute panel draws, so GUI changes still need the
  screenshot check.

### v0.7.0 notes (color-science pass)
- **Presets** are now authored in Scene-Linear Rec.709 for AgX, with HDR horizon
  values (up to 1.25) and a dedicated `mid_sky_color` bridge. The six palettes are
  GOLDEN_HOUR, SUMMER_NOON, RAINY_TOKYO, NEON_NIGHT, SAKURA_SPRING and
  TWILIGHT_DUSK. Look-dev luma/saturation changed visibly (Golden saturation
  0.14 → 0.27; Twilight 0.20 → 0.31).
- **Four-zone sky**: the old ground→horizon→sky mix was replaced by
  ground→horizon (0..0.5), horizon→mid (0.5..0.74), mid→zenith (0.70..1.0). This
  avoids the gray/brown midpoint when blue and orange complementaries mix.
- **Visible sky vs ambient**: `World Strength` was moved into the group. The world
  output mixes `gradient * World Strength` for non-camera rays with the full
  gradient for camera rays (`ShaderNodeLightPath > Is Camera Ray`). Background
  Strength is 1.0 while the gradient is active; flat worlds use the preset strength.
  This keeps the sky vivid without washing out cel shadows.
- **Directional clouds**: `sun_bias` maps `N·L` (-0.5..0.9) to (-0.06..0.08) and is
  added to the density before the 0.50–0.53 / 0.56–0.59 tone bands. Coverage is
  0.49–0.55. The bullseye/fried-egg look from using density alone for all three
  colors is gone; look-dev shows sun-side highlights and deeper cloud bases.
- **Shadow Hue Lift**: after the MULTIPLY shadow tint, an additive
  `Tint * combined * 0.18` veil is applied. Pure multiply on warm/yellow materials
  cannot produce a blue shadow (low blue channel times blue = low blue); the lift
  gives the Iro-Shitei hue veil while keeping texture detail. Exposed as `Hue Lift`.
- **Custom Colors palette switch**: `_on_palette` now refreshes custom
  sky/horizon/sun/shadow from the new preset before `look.apply`, so switching from
  Golden to Neon with Custom Colors on no longer keeps the old Golden overrides.
- **Sun rotation**: each preset supplies `sun_rotation`; it is applied only to
  auto-tagged `ALD | Sun`, not user suns. `sun_toward` uses `rotation_euler` for an
  unparented auto sun (avoids stale matrices) and `ensure_sun` no longer forces a
  view-layer update (depsgraph re-entrancy).
- Gate now checks `Mid Sky Color`, `World Strength`, background strength, `Hue Lift`
  and custom-color refresh on palette switch. Pixel ratios: shadow 2.1 %, wrap
  15.8 %, ink 2.6 %, toon 1.6 %, rim 7.2 %; `ALD GATE: PASS`.
- The new colors are intentionally more saturated; AgX still compresses highlights,
  and HDR values above 1.0 are expected for horizon/sun/cloud light colors.

### v0.8.0 notes (direction, depth and material control)
- **Shared geometry**: `build()` calls `_silhouette_mask()` once when Light Wrap,
  Ink or Aerial Haze is active and passes the mask to each stage. `_depth_edges`
  accepts `y_offset`; the ink chain is shifted down 1600 units so its nodes no
  longer overlap the light-wrap chain in the Node Editor.
- **Normal ink**: when `ink_lines` is on, every view layer gets
  `use_pass_normal = True`. `_normal_edges` blurs the Normal pass by 1.5 px,
  subtracts it from the original, takes the vector length, curves 0.01..0.14,
  multiplies by `ink_normal_sensitivity` and the geometry mask, then combines the
  result with the depth edge via `MAXIMUM`. This inks creases and internal hard
  corners that have no depth discontinuity.
- **Aerial haze**: depth is mapped through `depth_near..depth_far` (0..1), masked
  by the silhouette and `haze_strength`, then mixed toward
  `0.65 * horizon + 0.35 * shadow_tint`. The sky is excluded by the geometry mask.
  The range, strength and color nodes are refreshed in place by `update_params`.
- **Sun angle sync**: `rotation_from_angles` uses
  `(radians(90 - elevation), 0, radians(azimuth))`; the inverse reads the actual
  `sun_toward` direction. `sync_sun_angles` writes the UI properties behind a
  module guard, and the property update calls `apply_sun_angles`. `ensure_sun`
  resets the auto-sun rotation only when `ald_last_palette` differs from the
  applied key, so Stage Backlight and manual sliders survive cloud/world refreshes.
  `sun_toward` uses `matrix_world` whenever the sun has constraints.
- **Stage Backlight**: reads the active camera forward vector, sets elevation 12
  and azimuth = camera yaw + 15, enables Sun Disk/God Rays/Light Wrap/Rim, then
  applies the angles. Toggles are set **before** the final angle application,
  because the Sun Disk update can call `look.apply_world` and reapply the palette.
- **Stars**: `ShaderNodeTexVoronoi` (Distance) at the Star Density scale; the
  point curve is 0..0.22 (attempts at 0.03 were sub-pixel and invisible). The mask
  is zenith (Z 0.08..0.25), sun hide (dot 0.96..0.995) and cloud hide
  (`1 - cloud_amount`), multiplied by Star Amount. Presets carry `star_amount`
  (Neon 0.8, Twilight 0.7); the UI Star Amount multiplies it. Star color is a
  fixed cool white (1.4, 1.55, 1.9) added to the sky before the visible/ambient mix.
- **Cloud wind**: a Mapping node sits between the normalized view vector and the
  two cloud noises. `Cloud Offset` is a group vector input set from
  `frame * cloud_wind * (0.02, 0.005, 0)`. Stars use the unoffset view vector, so
  they stay fixed while clouds drift.
- **Terminator Warmth**: `abs(N.L)` through a smooth MapRange 0..0.12 -> 1..0,
  multiplied by the group input and `Sun Color`, then added to the shaded base.
  `_set_look` boosts Skin to at least 0.35.
- **Rim modes**: `Rim Bias` (-1..1) maps three weights:
  `sun=max(bias,0)`, `back=max(-bias,0)`, `contour=1-abs(bias)`. The Fresnel band
  is multiplied by `sun * max(N.L,0) + back * max(-N.L,0) + contour`. UI modes map
  Sun=1, Contour=0, Backlight=-1.
- **Shadow Tint semantics**: toggle off keeps the group and sets the AO Strength
  to 0.0 while Cel/Rim remain active; the X operator clears the group and turns
  Cel/Rim off. `look.apply`, `_sync_shadow` and `_on_shadow` all use the same
  strength rule.
- **Material exclusion**: `mat["ald_exclude"] = True` removes the group and is
  checked by `sync_scene`, `sync_one` and material-preset apply; Include restores
  the group for that material.
- Gate now covers sun controls/stage, star amount/density, cloud offset, haze,
  normal pass/ink gain, warmth/bias and material exclusion. Gate pixel ratios:
  shadow 2.62 %, wrap 15.78 %, ink 3.36 %, haze 63.04 %, toon 1.57 %, rim 7.18 %.
  Haze ratio is high because the gate plane fills most of the frame; the
  structural mask prevents it from tinting the sky.

### v0.8.1 note (custom sun / cloud coupling)
- Bug: `effective()` overwrote `cloud_light` with the custom `sun` color, so
  dragging the Custom Colors > Sun picker repainted the clouds. The line is
  removed; `cloud_light` stays on the selected preset, while the custom sun only
  affects the sun disk/light and sun-driven rim/glare tints.
- Gate regression: capture `Cloud Shadow/Mid/Light`, change only `custom_sun`,
  verify the three cloud inputs are unchanged and the sun data color changed.

### v0.9.0 notes (After School, planar clouds, micro stars)
- **AFTER_SCHOOL** is the seventh preset: salmon-gold horizon, salmon/mauve mid
  sky and indigo-lavender zenith. `PALETTES`/`PRESETS` are checked against each
  other and against the scene enum in the gate.
- **Sun Glow**: `gamma_plus = max(dot(V,L),0)`. Narrow corona
  `gamma_plus^16 * 0.65` plus wide lobe
  `gamma_plus^3.5 * smoothstep(0.75, 0.0, abs(Vz)) * 0.45`; the sum is scaled by
  `Sun Glow / 0.45` (default 0.45), tinted by `Sun Color`, and added before the
  clouds. The opposite horizon stays cool.
- **Planar clouds**: exact shell point
  `p=(Vx*t, Vy*t, Vz)` with `t=0.55/(max(Z,0.015)+0.18)`, then Mapping
  `Scale=(0.75, 0.75, 1.25 + 3.0 * Cloud Flatness)`; flatness 0.65 gives 3.2.
  Cloud Flatness also blends the raw spherical view (billowy) with the planar
  shell: 0 = cumuli, 1 = strata. Cloud Offset still drives the Mapping location.
- **Per-preset style**: each preset stores `cloud_flatness`, `cloud_scale`,
  `cloud_rim_boost` and `cloud_amount`. `apply_palette()` applies them only on
  a key change behind `palette.style_syncing()`; `_on_world` returns while the
  guard is active. Manual overrides persist on world refreshes.
- **Cloud noise**: domain warp noise at `0.55*Cloud Scale`, Color centered at
  0.5 and scaled 0.32, added to the mapped position; a macro bank at
  `0.42*Cloud Scale`; then inverted Voronoi F1 0.36 + N1 0.38 + macro 0.26.
  The high-frequency N2 is not part of the silhouette; it is centered at 0.5,
  scaled 0.06 and added only to `body_signal`.
- **Cloud Amount = coverage**: `tau0 = 0.68 - 0.26*CloudAmount`; coverage uses
  `tau0..tau0+0.055`, fringe uses `tau0..tau0+0.045`. A 0..0.03 gate makes
  Amount 0 truly empty. Amount no longer multiplies the final cloud opacity,
  so 0.2 gives few compact opaque clouds, not transparent ghosts.
- **Solar derivative / silver lining**: per-cloud light direction is
  `normalize(sun + (0,0,0.65))`; the `0.38/Cloud Scale` step is applied after
  the cloud Mapping, warp included. Detail is common between samples, so
  `delta` captures the primary Worley/N1/macro shapes. `Delta Gain` (default
  1.0) is explicit. `body_mix = smoothstep(-0.04, 0.04, delta + detail_gain)`
  blends Shadow -> Mid without any `Vz` term. `fringe = smoothstep(0.545,
  0.50, rho)`, `sun_edge = smoothstep(-0.01, 0.06, delta)`, rim is
  `fringe * sun_edge * (0.35+0.65*gamma_plus^2)`, plus a crown highlight
  `0.35 * smoothstep(0.03,0.11,body_signal) * sun_edge`. No body base; the
  old 0.35/0.08 baseline washed the opaque cloud beige at Cloud Amount=1.
  `Rim Boost` is explicit before Cloud Light.
- **Aerial blend / accent**: low clouds mix toward `Horizon Color` by
  `(1-horizon)*0.65`; optional `Sky Accent` paints a smooth band within
  `|Vz - z_mid| < 0.07`.
- **mu_s**: `L.z` through smoothstep(-0.08,0.08) gates the narrow solar corona.
- **Sky mapping**: ground transitions at Z -0.08..0.01; the mid peak is
  `clamp(0.22 + 0.16 * Horizon Offset, 0.05, 0.65)`; the zenith transition
  starts at `mid_peak + max(0.55 * Softness, 0.05)` and is clamped to 1.0.
  Ground never leaks above Z=0.
- **Stars**: `Star Density` is multiplied by 2.5 before the Voronoi Scale; the
  distance curve is 0..0.040, POWER 2.5, then multiplied by a Scale-45 Noise /
  MapRange 0.48..0.78 magnitude mask. A 0.24-wide halo at 0.22 strength keeps
  the core legible at 1080p; star color is (12.0, 12.5, 15.0), zenith
  0.06..0.28, sun hide 0.96..0.995, and clouds hide the field with
  `1 - cloud_amount`.
- **Contrails**: gnomonic `X/Z`, `Y/Z` (not the curved shell, which bends
  lines into arcs). `u=0.82X+0.57Y + 0.06*noise`, `v=-0.57X+0.82Y`;
  `abs(u-0.15)` mapped 0..0.012 -> 1..0; length fade
  `smoothstep(-1.2,0.2,v)*smoothstep(1.8,0.4,v)`; altitude 0.08..0.45;
  factor 0.18; off by default.
- **Gate**: palette registry, AFTER_SCHOOL and the new Sun Glow / Sky Accent /
  Cloud Flatness / Delta Gain / Rim Boost / Contrails sockets are checked.
  Gate pixel ratios are shadow 2.59 %, wrap 15.72 %, ink 3.50 %, haze 63.02 %,
  toon 1.59 %, rim 7.03 %. Look-dev renders all seven palettes in a 4-column
  sheet; the eighth cell stays empty (black).

### v0.9.0 reference study
- **Oga Kazuo Art Collection** pp. 97, 100, 117: high-key cyan sky, compact white
  cumulus with flat bases and lavender-gray shadow sides; this confirms the
  Perlin-Worley + directional shading direction, not a volumetric raymarch.
- **Persona 3 Official Artbook** p. 96 (main visual) and p. 106: pale
  yellow-green horizon against dark silhouettes, plus blue/gold interior light.
  The original P3 artbook does not contain the later P3 Reload "After School"
  sky, so the table values remain the calibration source.
- **Persona 5 Royal / Persona 5 Design Works**: sampled character and prop
  sheets; almost no atmospheric backgrounds, so they were not used for cloud
  color calibration.
- **80.lv / GDC / SIGGRAPH reading**: Ghibli-style limited palettes and
  Kuwahara finishing; Nubis Perlin-Worley and Beer-Powder; Genshin's 2D
  `(mu_v, gamma)` sky parameterization; iQuilez fBm/domain-warping and
  double-tint aerial perspective. The implemented equivalents are the planar
  shell, three-tone cloud transfer, full-density solar derivative, Mie lobes,
  aerial cloud/horizon blend and contrail layer.

### v1.0.0 notes (dome-sampled clouds, three cel bands)
- `_sample_cloud_density(nodes, links, ray_socket, group_in, flat_scale,
  flat_inv, y_offset)` builds projection, flatness blend, Mapping, warp and
  fBm for any sky ray. It returns `(rho, warped_pos)`.
- Density is 0.66 macro (Detail 6, Roughness 0.58, Distortion 0.18) + 0.22
  billow (Detail 5, Roughness 0.54, Distortion 0.22) + 0.12 high-frequency
  Voronoi puff (0..0.65 inverted). Domain warp: 0.85*Cloud Scale, centered,
  offset 0.28. This is a deliberate calibration from the first 62/24/14 +
  0.42 test, which produced fragmented holes.
- Solar derivative: `light_dir = normalize(sun + (0,0,0.65))`;
  `view_sun_norm = normalize(view + 0.035*light_dir)`; both rays use the same
  helper. The mapped point is never displaced into another Voronoi cell.
- Coverage: `coverage_center = 0.58..0.40` over Cloud Amount, top +0.018.
  Detail is split: contour `detail_edge=0.018`, body `detail_body=0.022`.
  `body_mix` is the tight -0.014..0.002 step; crown is
  `smoothstep(0.014,0.028,body_signal)` at 0.85. Rim is
  `fringe*0.92*sun_edge*(0.45+0.55*gamma^2)`, combined with the crown via
  `MAXIMUM`, then Rim Boost.
- Contrails use gnomonic `X/Z,Y/Z` straight filaments; the old spherical and
  curved-shell projections produce arcs.
- Marker is 14. Gate ratios: shadow 2.62 %, wrap 14.68 %, ink 3.56 %,
  haze 63.00 %, toon 1.60 %, rim 6.67 %. Look-dev: all seven palettes.

### v1.0.1 notes (cauliflower domes, four bands, reset)
- `_sample_cloud_density()` now returns `(rho_shape, rho_smooth, warped_pos)`.
  Macro Detail 1.8 / Roughness 0.42 at 0.38*Scale; warp 0.45*Scale at 0.22.
  Two Voronoi domes (0.95*Scale and 2.05*Scale) are masked by the macro bank.
  Shape = 0.52 macro + 0.34 masked puffs + 0.14 billow. Smooth = 0.72 macro +
  0.28 primary-puff*mask.
- Solar derivative uses rho_smooth and a 0.08 rad view-ray step. High-frequency
  detail is excluded from the silhouette and only perturbs contour (0.010) and
  body (0.012).
- Gouache four bands: two MapRange steps with a 0.55 plateau at
  -0.012..0.002, then the 0.022..0.042 crown at 0.90, combined with the rim by
  MAXIMUM.
- SUMMER_NOON: flatness 0.18, scale 2.4, amount 0.65, lavender shadow
  (0.42,0.56,0.86), bright cumulus.
- Apply Palette resets delta gain, sun glow and accent amount in addition to
  per-preset cloud style; same-key Apply is handled in the operator.
- Marker 15. Gate ratios: shadow 2.62 %, wrap 15.39 %, ink 3.57 %,
  haze 63.01 %, toon 1.59 %, rim 6.84 %.

### v1.0.2 notes (restored organic fBm, fringe-only Cloud Light)
- `_sample_cloud_density()` is back to the v1.0.0 two-value contract:
  `(rho, warped_pos)`. Warp 0.85*Scale / 0.28; macro 0.55*Scale, Detail 6.0,
  Roughness 0.58, Distortion 0.18, weight 0.66; billow 1.35*Scale, Detail 5.0,
  Roughness 0.54, Distortion 0.22, weight 0.22; Voronoi puff 1.60*Scale,
  dist 0..0.65 smoothstep reversed, weight 0.12.
- The solar derivative samples that full density with a 0.045 rad view-ray
  step. Coverage maps Cloud Amount 0..1 to 0.58..0.40; top +0.018 and fringe
  +0.038. Detail is 0.018 contour and 0.016 body.
- `body_mix` is a single -0.018..0.008 Shadow -> Mid step. `crown_curve` and
  `rim_total` are removed. `rim_boosted` receives the fringe factor directly,
  so Cloud Light cannot flood the body at high Delta Gain or Rim Boost.
- SUMMER_NOON restored to flatness 0.25, scale 3.2, amount 0.70, shadow
  (0.28,0.40,0.68), mid (0.90,0.93,0.96), light (1.20,1.16,1.05).
- Apply Palette resets cloud scale/rim/amount/flatness, delta gain, sun glow
  and accent amount; same-key Apply is handled in the operator.
- Marker 16. Gate ratios: shadow 2.63 %, wrap 15.86 %, ink 3.47 %,
  haze 63.04 %, toon 1.61 %, rim 7.02 %.
