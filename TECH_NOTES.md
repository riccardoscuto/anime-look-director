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
- **Aerial blend / accent**: cloud color is independent from `Horizon Color`;
  optional `Sky Accent` paints a smooth band within
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

### v1.0.3 notes (envelope shading, outer fringe, atmosphere resets)
- The helper is now `(rho, envelope, warped_pos)`. The rho graph is unchanged
  from v1.0.2. The envelope is a second Noise Texture at `macro_scale` with
  Detail 2.0, Roughness 0.45 and Distortion 0.15.
- The solar derivative is `env_here - env_sun` with a 0.055 rad view-ray step;
  this removes the internal Cloud Light speckles caused by sixth-octave density
  wobble while keeping the silhouette pixel-identical.
- Body detail is 0.010; Shadow/Mid is -0.022..0.006. Fringe top is +0.022,
  fringe is squared and scaled by 0.95, sun edge maps 0.000..0.022, and a
  coverage presence gate keeps the rim on the cloud rather than in empty sky.
- Apply Palette now also resets horizon offset/softness, contrails, star
  strength and star density.
- Marker 17. Gate ratios: shadow 2.65 %, wrap 15.93 %, ink 3.48 %,
  haze 63.06 %, toon 1.62 %, rim 7.07 %.

### v1.0.4 notes (cloud/horizon decoupling, clustered stars, presets)
- Removed the `aerial_fade`/`aerial_factor`/`aerial_mix` branch. `cloud_mix`
  receives `cloud_glow_add.Result` directly; Horizon Color only enters through
  the alpha/altitude cloud mask.
- Custom colors no longer overwrite Cloud Shadow/Mid; Cloud Mid falls back to
  neutral `(0.6, 0.6, 0.7)`.
- Stars use a low-frequency 3.2-scale cluster mask, background micro-stars at
  `Star Density * 1.6`, hero stars at `Star Density * 0.42` with a soft halo,
  zenith 0.08..0.32, sun hide 0.95..0.995 and cloud coverage masks. The additive
  tint is `mix((1.0,0.98,0.94), Cloud Light, 0.38) * 2.6`.
- Every preset now carries contrails, sun glow, sky accent, horizon controls,
  star amount and star density; Apply Palette resets all of them.
- UI preset labels no longer contain franchise names.
- Marker 18. Gate ratios: shadow 2.62 %, wrap 15.81 %, ink 3.49 %,
  haze 63.04 %, toon 1.61 %, rim 7.05 %.

### v1.0.5 notes (cloud color overrides, hash-based stars)
- Custom Colors adds `custom_cloud_shadow`, `custom_cloud_mid` and
  `custom_cloud_light`. They sync from the selected preset when Custom Colors is
  enabled or the palette changes, and `effective()` applies them directly.
- The v1.0.4 one-octave Noise culling was replaced by per-cell Voronoi Color
  hashes. Three Voronoi tiers: density*2.2 (spot width .085, cull .35...98 to
  0...55), density*0.90 (translated by (1.73,-2.41,0.89), width .075, cull
  .55...98 to 0...85) and density*0.38 (translated by (-3.14,1.17,2.65),
  core .068, halo .22 at .30, cull .70...96).
- Star temperature mixes warm (1.0,0.91,0.78) and cool (0.78,0.91,1.0) by
  `vor1.Color.Z`, then mixes 25% Cloud Light and scales by 6.0.
- Marker 19. Gate ratios: shadow 2.63 %, wrap 15.81 %, ink 3.51 %,
  haze 63.03 %, toon 1.61 %, rim 7.01 %.

### v1.0.6 notes (reliable toggles, true star amount, readable stars)
- `apply_preset_style` resets world_gradient, sun_disk, clouds and stars; the
  cloud UI no longer disappears after a palette change.
- `star_strength` is the visible star amount. `_apply_gradient` reads it
  directly (no hidden preset multiplier), and the gate checks Golden/Neon sync.
- Custom color sync goes through `palette.sync_custom_colors()` behind
  `_syncing_style`, so palette changes with Custom Colors do not trigger
  repeated rebuilds.
- Stars use a domain warp (Noise 4.2, 0.14), tier scales *1.15/*0.55/*0.24,
  readable radii 0.14/0.12/0.10 and a 10x glow. Voronoi Color hashes cull
  stars per cell.
- Sidebar now matches Scene panel: Sun Disk Size/Strength and shadow-tint X.
- Marker 20. Gate ratios: shadow 2.64 %, wrap 15.75 %, ink 3.51 %,
  haze 63.04 %, toon 1.61 %, rim 7.01 %.

### v1.0.7 notes (sharp sky, pinpoint stars, horizon shift)
- Kuwahara now multiplies its depth factor by the geometry silhouette mask, so
  the procedural sky and stars are excluded from the painterly filter.
- Stars are pure `view_norm` Poisson points: two Voronoi tiers at density*2.6
  and *1.45, tight 0.042/0.048 radii, POWER 3.0/3.2 and Color-hash culling.
  Star tint is 25% Cloud Light at 3.8x; no domain warp or giant halos.
- Horizon Offset shifts `shifted_z` by `0.22 * Horizon Offset` for ground,
  sky, cloud horizon and star zenith masks; mid-sky peak is fixed at 0.22.
- Apply Palette resets sun_disk_size/strength/cloud_wind and realigns custom
  colors. Contrails mix white with Cloud Light at 45% and default to 0.0.
- Marker 21. Gate ratios: shadow 2.62 %, wrap 15.78 %, ink 3.39 %,
  haze 62.96 %, toon 1.62 %, rim 7.31 %.

### v1.0.8 notes (PSF stars, Perlin-Worley clouds)
- Star existence, magnitude and temperature use independent Voronoi Color
  channels X/Y/Z. Tier scales are density*1.30, *0.72 and *0.36 with radii
  0.115, 0.105 and core/skirt 0.085/0.16. `star_tint_scale` is 12.0.
- `_sample_cloud_density()` gates billow and Voronoi lobes with a macro
  envelope (`0.28..0.56 -> 0.20..1.0`); macro weight 0.62, puff 0.16 at
  `Cloud Scale * 1.55`, billow 0.22. Open sky stays clean.
- Marker 22. Gate ratios: shadow 2.60 %, wrap 15.99 %, ink 3.34 %,
  haze 62.95 %, toon 1.60 %, rim 7.32 %.

### v1.1.0 notes (sun beam toggles, shooting stars, Hanabi)
- Sun Glow is gated by `sun_glow_enabled`; God Rays reset to false on Apply
  Palette so Stage Backlight cannot leave a stale Sun Beams effect.
- World gradient has shooting-star and firework generators with independent
  amount/length/angle/phase and amount/scale/phase sockets. Their phase is
  animated through `update_sun_controls` when Cloud Wind is active.
- Fireworks use cell-local radial Voronoi spokes, peony/pistil rings, burst
  glow and per-cell gold/magenta/cyan colors at 16x; shooting stars use a
  cell-local 3D trajectory with a bright 18x PSF head.

### v1.1.1 notes (2D generators, Milky Way, Hanabi)
- Shooting stars use stereographic 2D coordinates and `voronoi_dimensions =
  "2D"` anisotropic cells, with tapered 1.5px trails and a cross flare.
- Milky Way is a warped diagonal river with a dark dust rift and cyan/violet
  tint, exposed as the `Milky Way` socket.
- Fireworks use two cylindrical 2D layers with gravitational droop, continuous
  radial spokes, peony/pistil rings, embers and radial color gradient. Sun
  Beams threshold is 3.5.
- Marker 24. Gate ratios: shadow 2.63 %, wrap 15.70 %, ink 3.41 %,
  haze 62.85 %, toon 1.57 %, rim 7.21 %.

### v1.1.2 notes (tangent plane, vivid Hanabi)
- `tan_h = normalize(-Vy, Vx, 0)` and `tan_v = normalize(tan_h x V)` form the
  local tangent basis; 3D Voronoi cell centers projected into it remove radial
  error and atan2 seams. Fireworks Scale is wired into both layers.
- Milky Way is multiplied by its socket and boosts the cluster mask for stars.
  Shooting stars use 0.0007..0.0022 needle widths and zenith masking.
- Hanabi chromatic layers use 2.4x while hot cores use a separate brighter
  term, preventing AgX whiteout.

### v1.1.3 notes (stereographic hollow Hanabi)
- Fireworks use true 2D stereographic Voronoi cells (Randomness 0.35), a cell
  guard at r 0.31..0.36, hollow radial envelopes and crisp binary existence
  thresholds. No 3D slicing or atan2 seam.
- Fine spark trails, hoshi tips, inner 24-spoke pistils, detached embers and a
  tiny center core replace the solid bicycle-wheel disc.
- Colors select three analogous high-chroma families (gold/vermilion,
  magenta/violet, emerald/cyan); each layer returns premultiplied RGB and the
  layers sum directly instead of a 50/50 color mix.
- Marker 26. Gate ratios: shadow 2.60 %, wrap 15.99 %, ink 3.34 %,
  haze 62.95 %, toon 1.60 %, rim 7.32 %.

### v1.1.4 notes (spherical foreshortened Hanabi)
- Fireworks use horizon-aligned local axes on the stereographic plane, strong
  parabolic droop, and three radial shell bands (outer/mid/inner) with bright
  hoshi heads to introduce spherical depth. Trail width is compensated by
  max(norm_r, 0.28) so filaments do not fan into wedges.
- Chromatic shells use 5.5x HDR, with separate hot head boost up to 9.5x.
- Firework altitude masks are widened to -0.02..0.05 and 0.48..0.72.
- Marker 27. Gate ratios: shadow 2.60 %, wrap 15.99 %, ink 3.34 %,
  haze 62.95 %, toon 1.60 %, rim 7.32 %.

### v2.0.0 notes (3D FX particle architecture)
- x.py creates temporary ALD | FX objects in camera space: firework
  trails use parabolic gravity, three shell scales, hoshi heads and saturated
  emission materials; meteors use parallel radiant trajectories and needle
  trails. Objects are physical, so depth, overlap and perspective work.
- Operators: ld.fx_fireworks, ld.fx_meteors, ld.fx_clear; panel FX
  Particles exposes the buttons. World shader remains responsible for sky,
  clouds, stars and Milky Way.

### v2.1.0 notes (deterministic FX solver and ownership)
- fx.py evaluates every particle analytically: p(a) = p0 + v_inf a + (v0 - v_inf)(1-e^-ka)/k
  with a stable ballistic limit for k ~ 0. Time is expressed in seconds.
- Randomness comes from H(seed, burst, particle, channel), so results never
  depend on the number of previous bursts or on the frame history.
- Trails, child sparks and the central flash are separate subsystems; the
  flash is ephemeral and the sparks keep living after the head dies.
- FX data is owned per scene (scene id on the collection); clear() only removes
  the owner's objects and its own orphan datablocks.
- x_backend selects Disabled / Legacy World / FX 3D so both generators are
  never active at the same time.

### v2.2.0 notes (FX compositing separation)
- The view layer enables the Emission pass; ALD | FX Mask (RGB to BW of the
  emission pass) restores the particle cores after Kuwahara, Ink and Haze, so
  the environment stays painterly while the fireworks stay sharp.
- ALD | FX Glow blooms the emission pass only, with independent strength,
  size and threshold, instead of the sun-tinted atmospheric halation.

### v2.3.0 notes (animated in-place FX)
- FX geometry is created once and updated in place: the frame handler
  re-evaluates the analytic solver for the current time (frame time plus the
  configured age offset), so the timeline animates without object churn.
- Fireworks and meteors are independent systems per scene and can be created,
  updated and cleared separately.
- Burst composition assigns roles (hero, secondary, distant) with staggered
  birth times and rotating families.
- The camera basis is read from the local transform, so bursts placed right
  after moving the camera land in frame.

### v2.4.0 notes (beaded trails and burst age)
- Each primary star leaves a chain of small emissive grains (SAMPLES per
  star, radius shrinking towards the tail) plus a thin filament for cohesion.
- x_age (0..6 s) is the authoritative phase of the burst: the frame handler
  and the Update FX operator both use it, so scrubbing the timeline never
  changes the phase of the explosion.

### v2.5.0 notes (pistil, system editor, occlusion)
- Every burst grows a second, smaller and slower population with its own colour
  and beaded trail: the inner pistil of the Hanabi references.
- The FX panel lists the systems owned by the scene and can clear fireworks and
  meteors separately (ld.fx_clear_kind).
- Occlusion is preserved because ALD | FX Restore reads the depth tested
  emission pass; a box in front of a burst hides the particles (verified with a
  render sample of the covered pixel).

### v2.6.0 notes (granular trails, meteor debris, composition)
- Trails use 16 samples per star with per-grain jitter and brightness
  variation, so the strings read as scattered embers.
- Meteors emit burning fragments and keep a persistent train for a short
  while after the head is gone.
- x_burst_spread and x_composition_offset let the user frame the group
  by hand; changing them rebuilds the system with the new placement.

### v2.7.0 notes (Geometry Nodes prototype)
- x_nodes.py builds ALD | FX Burst GN: the Python side writes the
  deterministic data as point attributes (birth, life, vel, drag, radius,
  pos0) and the node group evaluates the analytic motion every frame
  (Scene Time -> Set Position -> Instance on Points) with the same linear drag
  solution and the 1/k guard.
- The prototype runs on one burst (GN Heads (Prototype) toggle) and is
  verified by the gate: the group must exist, contain Set Position / Instance on
  Points / Scene Time, and be attached to a real FX object.
- Next step: move the trail beads to Points to Curves (Curve Group ID = parent
  id, Weight = sample time) and then convert the whole system.

### v2.8.0 notes (Geometry Nodes for the whole burst population)
- x_nodes.py owns ALD | FX Burst GN; the same group evaluates the star
  heads, the trail grains, the inner pistil and the child sparks.
- Per point attributes: irth, life, el, drag, pos0, adius,
  	au (age offset of the sample), jitter (constant scatter), use_decay
  (follow the head decay or keep the baked size).
- Group inputs: Geometry, Gravity, Material, Trail, Age Offset,
  Min Scale. Trail reproduces 	rail_time = min(age, trail), Age Offset
  reproduces the x_age shift of the Python solver, Min Scale reproduces
  the  .35 + 0.65 * (1 - age / life) head fade.
- The child sparks are emitted from the position and the velocity the parent
  had at the emission instant (a spark is a body of its own).
- The gate realizes the instances and compares the node evaluation with the
  Python solver: heads, grains, pistil, pistil grains and sparks must agree
  within 1 mm (x_nodes.realized_centers).
- The Python path stays available: GN Particles (Prototype) off rebuilds the
  system with the mesh writer.

### v2.9.0 notes (trails, flash and meteors in Geometry Nodes)
- New group ALD | FX Trail GN: Set Position -> Delete Geometry (samples that
  are not born yet) -> Points to Curves (Curve Group ID = curve_id, Weight =
  weight) -> Set Curve Radius -> Curve to Mesh (Curve Circle) -> Set
  Material. The group inputs are Geometry, Gravity, Material, Trail,
  Age Offset, Radius and Fade Window.
- The train factor is now
  	rain = max(0, min(age, trail) - max(0, age - life)): the tail retracts
  when the body dies, exactly like the Python solver.
- Fade Window > 0 keeps the train alive after the death and thins it out
  (the persistent train of a meteor); with 0 the trail dies with the body and
  the dead samples are deleted.
- Decay Power on the burst group reproduces the sqrt falloff of the
  central flash (min_scale + (1 - min_scale) * (1 - age / life) ** power).
- The meteors are evaluated by the nodes too: head, persistent train and
  burning fragments. The fragment origin is the parent position at the
  emission instant.
- The frame handler still exists for the Python fallback but it writes no
  geometry in the Geometry Nodes path: measured 2.5 ms/frame against
  121.7 ms/frame for the Python writer (4 bursts + 4 meteors).

### v2.9.1 notes (limits and mandatory gate tests)
- The node group uses the ballistic solution when the drag is below 1e-4:
  the closed form p0 + v_inf * a + (v0 - v_inf) * (1 - e^(-k a)) / k cancels
  huge numbers when k -> 0 and loses precision. The group mixes the two
  solutions with the drag < 1e-4 test, like the Python solver.
- New gate tests (mandatory list of the guide):
  - identical state after a frame jump (the node evaluation is repeated);
  - the same physical state at 24, 30 and 60 fps;
  - the drag free and gravity free limits (p0 + v0 * a + 0.5 * g * a^2);
  - the child sparks stay alive when the head of the star is gone (the
    realized instance radius is read with x_nodes.realized_instances);
  - the burst behind a building is hidden (the occluder is a plane between
    the camera and the burst, the gate geometry is hidden for the render).

### v2.9.2 notes (FX lookdev renders and UI verification)
- `preset_dev/lookdev_fx.py` renders the comparison set required by the
  guide: `fx_noglow.png`, `fx_glow.png`, `fx_occluder.png`,
  `fx_motionblur.png` and the sequence `seq_XX.png`, plus `sheet.png`,
  `sequence.png` and `metadata.json` (resolution, camera, seed, exposure,
  view transform, renderer, frame range, FX settings).
- The occluder render places a building between the camera and the burst, on
  the direction of the hero burst, so the occlusion is visible in the sheet.
- UI verification with real screenshots: the Blender window must be restored
  and moved on screen (`ShowWindow(hwnd, 9)` then `MoveWindow`), otherwise the
  capture is black. The MCP screenshot of an area works once the window is
  visible; the Properties editor can be maximised with
  `bpy.ops.screen.screen_full_area` under a `temp_override`.
- The screenshot revealed a real bug: the objects built by the Geometry Nodes
  path had no `ald_fx_kind` tag, so the FX panel listed the fireworks system
  as empty and the per system clear could not remove it. The gate now checks
  the listing.
- Re-registering the panels at runtime (add-on reload) leaves the sub panels
  of the Properties editor out of the panel list: verify the UI in a fresh
  Blender instance.

### v2.10.0 notes (new file resets the caches)
- The FX systems are keyed by the hash of the scene name (`ald_fx_id`), the
  same key stored in the `ALD | FX` collection so the ownership survives a
  save. A new file whose scene has the same name therefore collided with the
  systems of the previous file: the panel showed a phantom system and the
  frame handler updated objects that no longer existed.
- Fix: a persistent `load_post` handler in `fx.py` clears the `SYSTEMS`
  registry and a second one in `cameras.py` clears the camera and transform
  caches. The gate now opens a new file and checks that the handlers are
  still registered, that the caches are empty, that the palette, the stack and
  the FX can still be built.
- The frame handler skips the systems evaluated by the node group: in the
  Geometry Nodes path it never touches a vertex.
### v2.10.1 notes (family comparison)
- `preset_dev/lookdev_families.py` renders the three families with the same
  palette, camera, seed and frame: the Chrysanthemum is a dense sphere with
  long trails and a visible pistil, the Peony is a set of short bright dashes
  (high drag, no trail), the Willow has few spokes with long drooping trails
  (low drag, long life). The families are readable without the colours, the
  acceptance condition of the phase 5 of the guide.
### v2.11.0 notes (the Burst Age slider does not rebuild)
- `fx.set_age(scene, age)` writes the `Age Offset` input of the node group
  modifiers of the scene: the deterministic data (birth, life, velocity,
  drag, radius, pos0, tau, jitter) is never rewritten and no object is
  created or destroyed. The Python path is re-evaluated at the new instant.
- Measured on the reference machine with 4 bursts and 4 meteors: 2.3 ms per
  slider step instead of 428 ms for a full rebuild, 189 times faster. The
  slider is now usable while dragging.
- The spread, the composition offset and the Geometry Nodes toggle keep the
  rebuild path (`_on_fx_rebuild`): they change the geometry itself.
- The gate verifies that the slider moves the burst, keeps the same objects
  and the same attributes.
### v2.11.1 notes (the UI probe is a repository tool)
- `preset_dev/ui_probe.py` reproduces the UI verification: it enables the
  add-on in a fresh Blender, creates the FX systems, maximises the Scene
  properties with `bpy.ops.screen.screen_full_area` and writes the
  screenshots of the properties and of the sidebar.
- The window must be on screen: restore a minimized window with
  `ShowWindow(hwnd, 9)` and move it with `MoveWindow`, otherwise the capture
  is black. The `--wait` argument leaves the time to scroll the properties
  with the mouse wheel before the capture.
### v2.12.0 notes (phase P0-A of the operational plan)
- The shape decay was inverted in the node group: the chain computed
  `m + (1 - m) * (1 - (1 - u) ** p)`, so the scale grew with the age and the
  flash reached its maximum size at the death. The correct law is
  `s(u) = m + (1 - m) * (1 - u) ** p`: full size at the birth, the minimum at
  the death.
- The energy is now a separate curve: `e(u) = (1 - u) ** q` is written as the
  `energy` attribute by a Store Named Attribute node and the material
  multiplies the Emission Strength by it. The geometry shrinks while the
  emission fades on its own law.
- The number of samples of the grains overwrote the `count` of the bursts:
  the composition rule (`-0.18 + 0.36 * (index + 0.5) / total`) was computed
  with the sample count, so every burst was pushed to the left of the frame.
  The rule uses the burst count and the gate checks it with 1, 3 and 5 bursts.
- The meteors started along their own velocity, so they moved away from the
  camera. The start points are now spread on a plane at the camera distance
  and the velocities are almost parallel in world space (a lateral shower
  direction with a small jitter): the radiant emerges perspectively and the
  meteors cross the screen.
- The head, the train and the fragments of a meteor share one `event_birth`.
  The train lifetime is the lifetime of the body plus the persistence window
  and `Fade Window = 0` means explicitly no persistence (the magic 0.5
  threshold is gone).
- The child sparks and the fragments compute their origin once, at the
  emission instant: the Python writer used the current age, so the origin
  moved with the parent.
- `fx.burst_population()` is now the single source of the deterministic data:
  the Geometry Nodes attributes and the Python writer consume the same
  particles, and the gate compares the positions and the scales of the two
  backends (within 1 mm and 2 mm).
### v2.13.0 notes (phase P0-B: persistent state and migrations)
- The persistent schema: `Scene.ald.fx_systems` is a collection of
  `ALD_FX_System` (uid, kind, enabled, seed, timing mode, origin frame and
  time, material and glow profile, isolation mode) and every system holds a
  collection of `ALD_FX_Event` (uid, kind, enabled, seed, birth, family,
  size, count, launcher, target, direction, speed, life, duration, glow).
  The schema version lives in `Scene.ald.fx_schema`.
- `fx.store_system()` writes the description of a system and of its events
  after a creation: the runtime registry (`fx.SYSTEMS`) is only a cache.
- `fx.rebuild_registry()` rebuilds the runtime state from the persistent
  configuration, the collection ownership, the object tags and the ALD
  modifiers. It runs in the `load_post` handler and reuses the geometry saved
  in the file: nothing is regenerated.
- The identity of a scene is a persistent UUID stored in `ald_fx_id`. The
  first scene that claims an identity keeps it (`fx._CLAIMED`): a duplicated
  scene receives a new one and an independent copy of the systems. A
  collection linked to more than one scene never owns the systems, so the
  clear of a copy never touches the original.
- The node groups carry the build marker `ald_schema`. A group saved with an
  older marker is rebuilt, the modifiers are remapped on the new structure
  and the old group is removed only when nothing uses it any more.
- The gate runs the P0-B tests: the fixture (save, reopen, list, sliders,
  clear per kind, animation), the duplication and the migration of an old
  group.
### v2.14.0 notes (phase P1-A: one interface, exclusive backends)
- `panels.py` now exposes the drawing functions (`draw_atmosphere`,
  `draw_world`, `draw_shadows`, `draw_camera_override`, `draw_compositor`,
  `draw_fx`, `draw_stack_actions`) and the panels only call them: the Scene
  properties and the View3D sidebar show the same state with the same
  operators, the sidebar is only more compact.
- The FX section follows the structure of the plan: Systems (the list of the
  persistent systems and events with the selection, the enabled flag, the
  duplicate and the remove), Timing (Timeline or Preview, the origin frame
  and the preview time), Launch (the launcher, the target, the duration, the
  birth), Explosion (the family, the seed, the size, the primary count, the
  pistil, the child sparks), Look (the glow, the energies of the heads, the
  grains and the embers, the atmospheric fade), Advanced (the debug backend,
  only in developer mode) and Actions.
- The backend is exclusive and applied immediately by `fx.apply_backend`:
  OFF hides the 3D systems and the legacy shader and preserves the data,
  LEGACY enables the legacy shader and hides the systems, FX3D does the
  opposite. The legacy world controls only appear in LEGACY.
- The energy of every role is a separate exponent (head, grain, ember) and
  the atmospheric fade attenuates the emission with the distance from the
  camera: the nodes take the camera position and the fade as inputs, the
  Python writer applies the same law.
- The panel used the icon `OUTLINER_OB_DATA`, which does not exist in
  Blender 5.1: the whole FX panel broke at draw time. The gate now validates
  the icons against a curated list.
### v2.15.0 notes (phase P1-B: reversibility)
- `snapshot.py` saves the state of the user before the first modification:
  the world (with the link of the background, the default colour, the
  strength and `use_nodes`), the sun (existence, ownership, energy, colour,
  rotation), the compositor group and `use_compositing`, and the render
  passes of every view layer. The materials keep their own reversible
  bookkeeping (`ald_st_color`, `ald_em_color`, `ald_em_strength`).
- The snapshot is a JSON string in the scene (`ald_snapshot`): it is explicit,
  serializable and it survives a save.
- `ald.remove_from_scene` restores everything and removes the internal
  properties only after a successful restore. The maintenance flag
  (`ald_maintenance`) suspends the frame handler, the depsgraph handler, the
  shot handler and the property callbacks while the scene is restored, so the
  look is never re-applied in the middle.
- The gate runs the acceptance condition of the plan: a scene with a world of
  its own, a custom sun, an emissive material and a pre-existing compositor
  stack returns to the registered state after the removal.
### v2.16.0 notes (phase P1-C: the complete firework event)
- The event now has a launcher, a rising shell and a burst point. The shell is
  a body of the node group with its own birth (the launch), drag and lifetime
  (the rise time) and a short trail; it disappears at the burst.
- The initial velocity follows the equations of the plan: with a linear drag
  and a constant wind, `v_inf = w + g/k`, `A(T) = (1 - exp(-kT))/k` and
  `v0 = v_inf + (pB - pL - v_inf T)/A(T)`; without drag the limit is
  `v0 = (pB - pL - 0.5 g T^2)/T`. The branch stays stable for `k` close to
  zero.
- The continuity at the burst is structural: the stars are born exactly at
  `p_rise(T)` and their initial velocity includes the residual velocity of
  the shell (`v_star0 = v_rise(T) + s_i d_i`). The population builder takes
  the `shell_velocity` and adds it to every star.
- The launcher sits below the burst point in the world space: a launcher on
  the line of sight makes the shell read as an object coming towards the
  camera instead of an ascent.
- The burst happens at the end of the rise: the `Burst Age` measures the
  time since the launch, the lookdev renders follow the new timing and the
  sequence shows the launch, the rise, the burst and the expansion.
### v2.17.0 notes (phase P1-D: the meteors are events, the Hero Meteor)
- `fx.METEOR_PRESETS` holds the two kinds: a normal meteor and the Bolide,
  the cinematic one (head radius 0.18 against 0.5, emission 9 against 16,
  life 0.55-1.15 s against 1.6-2.4 s, train 0.32 s against 1.2 s, three
  fragments against eight, jitter 0.03 against 0.012).
- The operator `ald.fx_bolide` creates the Hero Meteor, and the kind is part
  of the persistent event (`ALD_FX_Event.kind`).
- The gate verifies the preset and the geometry of the shower: the velocities
  stay almost parallel in the world space (the radiant emerges from their
  convergence) and the meteors cross the screen.
- A meteor is never called a comet in the technical model: a real comet, with
  a nucleus and a coma, is a separate feature.
### v2.18.0 notes (phase P2: the material contract and the FX isolation)
- The material contract of the plan: the points carry `role` (an integer
  code), `age_norm` (the normalised age), `energy` (the emissive energy,
  independent of the scale), `trail_u` (the profile along the trail),
  `stable_noise` (a deterministic variation, never a per frame flicker) and
  `event_color`. Python writes the static ones, the node group writes the
  dynamic ones.
- `fx.ROLE_ENERGY` holds the visual profile of every role: the head is the
  brightest, the filament is less energetic than the sparks, the embers fade
  slowly, the flash is a very short impulse. The value is applied both by the
  node group (the `Role Energy` input) and by the Python writer.
- The FX mask is not the emission pass any more: the emission pass contains
  every emissive surface of the scene. The dedicated view layer `ALD FX`
  excludes the collection of the add-on, so the difference between the two
  emission passes is exactly the contribution of the FX. The Object Index
  pass would be cleaner but the Render Layers node of Blender 5.1 does not
  expose it.
- The painterly filters receive a base without the FX (`ALD | FX Punch Out`),
  then the particles are recomposed with their exact coverage (`ALD | FX
  Restore`) and the dedicated glow is added once, on the FX only.
- The gate verifies the isolation: an emissive surface that is not ALD keeps
  the same value with and without the bursts.
- The cost of the isolation is one more view layer in the render.
### v2.19.0 notes (phase P3: the cleanups and the refinements)
- The solver: the closed form `p0 + v_inf a + (v0 - v_inf) A` cancels two
  large terms when the drag is small (`v_inf = g/k` and `A = (1 - e^(-k a))/k`
  both blow up). The stable form is `p = p0 + v0 A + g (a - A) / k`, with
  `A` computed by `expm1` and a series expansion (`A = a (1 - x/2 + x^2/6 -
  x^3/24)`, `(a - A)/k = a^2 (1/2 - x/6 + x^2/24)`) when `x = k a` is small.
  The velocity uses the same form: `v = v0 e^(-k a) + g A`.
- The camera frame comes from the evaluated matrix
  (`camera.evaluated_get(depsgraph).matrix_world`): a camera with a
  Track To constraint or with a parent is followed correctly and the matrix is
  never stale.
- The clouds and the legacy shooting stars follow the time in seconds
  (`palette._scene_seconds`): the same state at 24, 30 and 60 fps. The phase
  of the legacy stars is separated from the wind of the clouds.
- The custom colours accept the HDR range (max 4.0), like the palettes.
- The backend is chosen before any allocation: `_build_python_objects` is
  only called when the Python writer is the chosen backend, and the Geometry
  Nodes path no longer creates and deletes the Python meshes.
- The Kamuro family: 48 thick stars, a slow speed, a low drag, a 2.2 s trail
  and a small pistil: a few bold strokes with a long drooping tail.
### v2.20.0 notes (the milestone of the plan)
- `preset_dev/milestone.py` verifies the Definition of Done point by point
  (thirteen checks) and writes the filmstrip of the event plus a JSON
  report. It never saves the .blend of the user: the fixture lives in the
  temporary directory and it is removed at the end.
- The launcher of a burst is a visible empty (`ALD FX Launcher <n>`): the user
  can grab it in the viewport, the build reads its position back and "Update
  FX" rebuilds the system to apply the new position. The empty is tagged with
  the kind of the system, so it is removed with it and it is not counted in
  the system list.
- Every path writes the persistent configuration: `fx.create_fireworks` and
  `fx.create_meteors` call `store_system`, not only the operators. A project
  saved after a direct call keeps its systems and its events.
- The shell is a visible ball (`0.20 * size_scale`): the rising body and its
  short trail must be readable in the shot.
### v2.20.1 notes (the backend owns the legacy effects)
- The legacy world effects follow the backend: `fx.apply_backend` turns off the
  shader shooting stars together with the shader fireworks when the backend is
  not the Legacy World. Before this the old comets were rendered together with
  the new ones.
- The legacy controls only appear in the Legacy World backend, in both the
  Scene properties and the View3D sidebar: the world meteors and the world
  fireworks are one block of the World section, behind the backend test.
- The FX section is now the first section of the View3D sidebar, so the
  systems and the actions are reachable without scrolling.
- An add-on already loaded in memory is never updated by the changes on disk:
  it has to be reloaded (or Blender restarted) before judging the interface.
### v2.21.0 notes (the two surfaces are the same)
- The "compact" mode of the drawing functions is gone. It was hiding
  controls in the View3D sidebar (the horizon softness, the contrails, the
  cloud delta gain and rim boost, the hue lift, the burst spread and the
  offset, the pistil and the child sparks, the glow size and threshold, the
  energies and the atmospheric fade) and it moved the backend selector out of
  the timing section: the two surfaces ended up showing different things.
- Both surfaces now draw the same controls with the same operators, and the
  sidebar mirrors the structure of the Scene properties: the parent panel with
  the atmosphere, the material presets and the stack buttons, then the sub
  panels World & Shadows, Compositor Stack and FX Particles.
- The gate compares the controls drawn by the two surfaces (the set of the
  shared functions called by the panels) and fails when they diverge or when
  a drawing function keeps a compact mode.
### v2.22.0 notes (the three actions on the scene)
- The plan asks for three distinct actions: a temporary bypass, a complete
  removal from the scene and a detach that keeps the result. They are now
  three buttons in a "Scene" section, in both surfaces:
  - **Bypass** (`Scene.ald.bypass`): the handlers and the callbacks do
    nothing, the scene keeps the look;
  - **Remove ALD from Scene** (`ald.remove_from_scene`): the snapshot is
    restored and the datablocks of the add-on are removed (the objects, the
    collection, the orphan materials, the node groups, the markers and the
    internal properties);
  - **Detach and Keep Result** (`ald.detach`): the world, the materials, the
    lights and the compositor stay as they are, the FX objects, the markers
    and the internal properties go away and the scene is marked as detached.
- The removal always happens: when the original state was never registered
  (an old scene, a direct call without a palette) the conservative clean up
  is done and the operator reports the limit, as the plan requires.
- The identity of the scene (`ald_fx_id`) is not one of the internal
  properties: it is the ownership key of the collection of the add-on and
  deleting it changed the identity before the ownership was resolved.
- The panel used the icon `EVENT`, which does not exist in Blender 5.1: the
  whole FX panel broke at draw time. The gate now validates the icons
  against the real list of the layout (`UILayout.label` exposes 1017 of them)
  instead of a curated list.
- The FX are real objects with a material: in the solid mode they are
  invisible. The creation of the FX now puts the 3D viewport in the camera
  view with the rendered shading.

### v2.22.1 notes (the reload and the plan audit)
- `register_class(...): already registered as a subclass 'ALD_FX_Event'` was
  raised when Blender reloaded the add-on. Blender does it automatically when
  the files change on disk while the add-on is enabled: the package is
  reloaded, but the sub modules keep their registered classes, and the second
  registration of the same PropertyGroup raises.
- The registration is now idempotent (`properties.register_classes`): the
  classes are unregistered in the reverse order first (a class that
  references another one, like `ALD_FX_System` with its CollectionProperty of
  `ALD_FX_Event`, must be released before the one it points to) and the
  pointer `Scene.ald` is removed before the settings class is unregistered
  (a pointer property holds a reference to its class: the unregister fails
  with "missing bl_rna attribute" otherwise).
- `cameras._transform_state` used the raw `matrix_world`: it can be stale
  right after a move and it ignores the constraints. The evaluated matrix
  (`obj.evaluated_get(depsgraph).matrix_world`) is used now, like the FX
  already did in `fx._camera_basis`.
- `preset_dev/audit_plan.py` audits the operational plan in the source: the
  eight invariants, the phases P0 to P3, the file map, the test matrix, the
  documentation and the Definition of Done. The result is 69/70: the only
  open item is the optional atmospheric smoke ("solo se davvero necessario").
- The gate gained two checks: the occlusion of the burst with the motion
  blur on, and the real travel of the meteors across the screen (not only
  the alignment of the velocities).


### v2.55.5 notes (the pass cache and the scene copy)
- `compositor.build` used to accept any existing EXR: `fx_pass_state` said
  STALE and the graph still loaded the file. The build now consumes only
  `READY`; a stale/missing/range/unsigned pass is ignored even when the file
  exists. The negative gate renders the strict case and compares pixels with
  the no-FX environment, not only the nodes.
- Strict mode used to replace only F with black, leaving
  `C = P(B) * (1 - A)`: the particles became dark holes. Strict now skips the
  whole FX branch (matte, punch, restore, glow), so C is B. The old
  `ALD | FX Strict Black` node is gone.
- `_pass_stem` treated any trailing digits as a frame number. `Scene1` and
  `Scene2` both mapped to `ald_fx_pass_Scene1.exr` at frame 1. Default paths
  now use the scene UUID (`ald_fx_pass_<uid>/fx.exr`) and the explicit
  `_f0001` suffix; the sequence validator checks every file (EXR magic) and
  every per-frame record.
- The pass sequence is staged in a temporary directory and published with one
  directory rename. A forced failure at frame 2 keeps the previous files,
  hash and manifest. Old versioned directories are not deleted automatically.
- A plain `Scene.copy()` shares ordinary objects, meshes and materials. The
  add-on now leaves a material used by another scene untouched instead of
  editing the original through the copy; a shared sun is not rotated. A
  complete independent copy would require a deep copy of all user objects:
  that is a deliberate limit, not something the add-on does silently.
- `snapshot` now saves and restores `use_pass_cryptomatte_material` and
  `use_pass_object_index`; the old restore left the Cryptomatte pass on.


### v2.56.0 notes (contract, framing and the subpixel pass)
- `event.duration` used to be written at creation and then ignored by
  `_event_config`: the slider changed a saved value, not the burst. The
  config now uses the duration as `life`; the duration callback rebuilds, but
  it stays quiet while a new system is being written (the compile at the end
  already sees the value).
- `layout_distance` stores the requested distance of an automatic show.
  `relayout_system` recomputes the targets and launchers from that distance,
  the current spread and the current offset. Without it, offset and spread
  were creation-only controls and Update FX rewrote geometry from stale
  positions.
- The framing radius now includes the gravity drop and the spark margin; in
  Physical mode it also includes the shell residual, bounded by the drag
  terminal distance. Director mode does not add its residual: its authored
  burst point is the frame target. The gate samples the real particles from
  `burst_population` and requires the radius to cover them.
- The FX pass is now RGBA. The compositor `CombineColor` writes the Emission
  pass in RGB and the Render Layers Alpha in A with `film_transparent` during
  the pass render. This alpha is the unoccluded FX coverage, not the visible
  matte. `ALD | FX Visibility` divides the visible Cryptomatte matte by the
  unoccluded alpha and multiplies F. At a subpixel occluder edge the FX loses
  exactly the hidden fraction instead of the old binary `matte > 0.001`
  presence. A 3-channel legacy pass keeps the binary path.
- The subpixel gate renders the same frame twice, with the visibility factor
  0 and 1; the corrected image is never brighter and the edge differs by more
  than 0.02. This is a measurement of the correction, not only a node check.
- The cloud rim multiplies `ald_edge` by a sun-side range and a face range
  written per card from `palette.sun_toward` and the card basis. The two
  flash sources have separate colours; `update_flash` writes `Flash Color`
  and `Flash Color2` from the event palette.
- `validation_stack.py` is the full path matrix: strict pass, clouds, World
  and composite, three palettes, fixed and travelling camera. It is stricter
  than the old FX-only matrix because a stale pass cannot be consumed.


### v2.57.0 notes (World Sky reduction)
- The FX/cloud/smoke modules were removed, not merely hidden. `identity.py`
  now owns the persistent UUID (`ald_fx_id`, kept for compatibility); palette,
  ownership and snapshot no longer import `fx`.
- A plain palette apply does not create a compositor group: `look.apply` only
  rebuilds an existing stack. The gate asserts this.
- The compositor lost the FX branch, Cryptomatte, pass image, FX layers and
  FX glow. `build()` is now Render Layers -> optional general filters ->
  Output; the FX view layers are not created.
- The old World fireworks/meteors are forced off at the shader inputs. The
  node groups still exist in `palette.py`; Phase 4 will replace them with
  controlled 2D shooting stars.
- `snapshot.restore` no longer calls the FX/cloud/smoke modules. It restores
  World, Sun, materials, passes and compositor; legacy ALD collections are
  handled only by the explicit Legacy ALD Data operators.
- `ownership.repair` now only gives a duplicated scene a new identity and its
  own World. It no longer rebuilds FX/cloud collections.
- The World-only gate covers palette precedence, World inputs, Sun owner and
  angles, custom colors, compositor optionality, no FX objects, legacy
  disable/remove, render, ownership and snapshot restore.
- The World baseline was rendered by checking out v1.0.3/v1.1.0 in temporary
  worktrees and enabling the old add-on from a temporary
  `BLENDER_USER_SCRIPTS`. The comparison is in `preset_dev/world_baseline/`.


### v2.58.0 notes (cloudless sky)
- The Sky Accent was a narrow 0.07 band. At dusk and night it read as a hard
  blue stripe across the sky. The band is now 0.20 wide; the transition reads
  as atmosphere. The before/after matrix is `preset_dev/sky/contact.png`.
- The Sun disk stayed at full strength below the horizon. `_sun_fade` now
  gates the disk between -0.015 and +0.02 in view-space Z and the glow between
  -0.12 and +0.02; `update_sun_controls` uses the same gates during animation.
- The cloudless matrix renders noon/sunset/dusk/night with clouds off. Noon and
  sunset are unchanged; dusk/night lost the stripe.
- The remaining legacy World firework/meteor shader blocks and settings were
  removed; the World group schema is now 28. The Phase 4 shooting-star system
  will be a new controlled generator, not the old Voronoi field.


### v2.59.0 notes (cloud families)
- The three families share one density field. `family_flatness` subtracts
  0.62 * Cumulus, adds 0.20 * Stratocumulus and subtracts 0.16 * Vertical.
  Cirrus stretches the view ray by 2.4 on X and 0.32 on Y; the cirrus gain
  removes only 5% of the density so it stays visible.
- `Cloud Breakup` subtracts up to 0.10 from the density before the threshold;
  `Cloud Detail` scales the border/body noise; `Cloud Sun Lighting` scales the
  solar derivative; `Cloud Seed` offsets the field by a deterministic vector.
- The family weights are one-hot group inputs set by `cloud_type`; preparse
  flatness is lowered by the family formula, so a Cumulus does not inherit the
  flat preset default.
- The Cumulus silhouette is still flatter than the v1 reference. The first
  visual gate is in `preset_dev/cloud_families/contact.png`; it is not
  approved. The next iteration should raise the rounded top and vertical
  shading before any sunset work.


### v2.59.1 notes (Cumulus lighting)
- The Cumulus body was too uniformly white. The solar body range is now
  -0.030..0.004 and a height tone maps the lower sky to 0.62..1.0, so the
  cloud base darkens while the top stays light.
- The Cumulus defaults are coverage 0.48, scale 3.4, breakup 0.28; they produce
  larger isolated masses than 2.59.0 without filling the frame.
- The family contact sheet was regenerated; the gate is still open because the
  top is not as rounded as the v1 reference.
