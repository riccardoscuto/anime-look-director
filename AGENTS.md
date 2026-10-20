# Anime Look Director — project instructions

Blender add-on: atmospheric palettes + non-destructive anime compositor stack.

## Target
- Blender **5.1.2** on Windows (compositor node-group API `scene.compositing_node_group`).
- Python 3.13 / NumPy available inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **0.9.0**).

## Verify (run after every change)
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
```
Expected output: `ALD GATE: PASS`.

For live work: Blender Lab MCP bridge on `localhost:9876` (keep calls short).
If window screenshots are black, the Blender window may be off-screen (see
TECH_NOTES); move it on-screen before capturing.

## Architecture
- `properties.py` — `Scene.ald` settings (palette, toggles, sliders, update hooks;
  floats update in place, toggles rebuild the stack).
- `palette.py` — atmospheric presets, world gradient (sun disk + clouds), custom
  color overrides, world + sun apply.
- `look.py` — effective palette resolution and apply (camera > marker > base).
- `cameras.py` — per-camera palette overrides and camera-switch handler.
- `compositor.py` — builds/removes one `ALD | Compositor Stack` per scene
  (Render Layers → Glare → Sun Beams (optional) → Kuwahara (depth-mixed) →
  Light Wrap → Ink Lines (optional) → Lensdist → Group Output); also refreshes
  God Rays and the world sun on frame changes.
- `materials.py` — Shadow Tint group (AO + directional terminator + rim),
  material presets, and the per-frame sun sync.
- `shots.py` — timeline marker palette overrides and the frame-change handler.
- `operators.py` - `ald.build`, `ald.remove`, `ald.apply_palette`,
  `ald.clear_shadow_tint`, `ald.stage_backlight`, `ald.toggle_exclude_material`,
  `ald.viewport_compositor`.
- `panels.py` — Scene properties panel plus the View3D sidebar panel.
- `preset_dev/verify.py` — headless gate.
- `preset_dev/lookdev.py` — renders all palettes on a fixed scene + contact sheet.
- `RECAP.md` — Italian end-to-end overview for the user.

## Look-dev
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\lookdev.py -- --out "$env:TEMP\ald_lookdev"
```
Prints luminance / contrast / saturation per palette and writes `sheet.png`.

## Hard-won API facts (Blender 5.1.2) — do not regress
- Compositor is a **node group**: `scene.compositing_node_group`. `scene.node_tree` is gone; there is no `CompositorNodeComposite`, use `NodeGroupOutput`.
- **Glare is socket-driven**: `Type` accepts `Bloom`, `Streaks`, `Fog Glow`, `Sun Beams`. No separate Sun Beams node.
- **Kuwahara exists**: `CompositorNodeKuwahara` with `Type` = `Classic` / `Anisotropic`.
- `Render Layers` exposes `Depth` and `Mist` only when `view_layer.use_pass_z` / `use_pass_mist` are enabled.
- Inside compositor trees use `CompositorNodeSeparateColor`; `ShaderNodeMix/Math/MapRange` do work.
- Viewport compositor: `View3DShading.use_compositor` = `DISABLED` / `CAMERA` / `ALWAYS`.
- Drivers: simple expressions work with "Auto Run Python Scripts" off. `TRANSFORMS` variables work in **WORLD_SPACE**; LOCAL_SPACE returned 0 for an Empty.
- `CompositorNodeBlur` `Size` is a 2-float vector; `Type` = `Flat`, `Tent`,
  `Quadratic`, `Cubic`, `Gaussian`, `Fast Gaussian`, `Catrom`, `Mitch`.
- `CompositorNodeSetAlpha` `Type` = `Apply Mask` / `Replace Alpha`.
- Render Layers **Alpha is 1 everywhere when the world is opaque**: never use it as
  a silhouette mask. EEVEE writes world depth = `camera.clip_end + 0.55`; Cycles
  writes ~1e10. Threshold the Depth pass with the clip end read at build time.
- `CompositorNodeAlphaOver` needs `Straight Alpha = True` when the foreground alpha
  was replaced (SetAlpha) on a premultiplied render, otherwise the full blurred RGB
  leaks across the frame.
- Light Wrap mask = outer silhouette band + depth-discontinuity band (normalize
  depth by 100 m, blur 4 px, abs diff ×100, threshold 0.05 m, blur by wrap size,
  multiply by the geometry mask).
- Compositor stacks are **per scene**: `_group_for_scene` looks up the group tagged
  `ald_scene`, the first scene keeps `ALD | Compositor Stack`, later scenes get
  `ALD | Compositor Stack | <scene>`. `ald.remove` deletes only the assigned group,
  and only if no other scene references it.
- Palette auto-Sun creates `ALD | Sun` tagged `ald_auto_sun` only when the scene has
  no SUN light. Never delete or retint a user sun that is linked from a library.
- A full stack rebuild costs ~5–8 ms on the target machine, so slider updates can
  rebuild synchronously; no debounce is needed.
- Glare `Sun Position` is normalized screen space (0..1, **y up**). Project the
  sun with `world_to_camera_view(camera.translation - light_direction * 1000)`;
  skip the node when `co.z <= 0` (sun behind the camera). The position is baked at
  build time.
- Shot markers use `frame_change_pre`, `ALD:<PALETTE>` names and the
  `ald_active_shot` scene property to avoid applying the same palette every frame.
- Material presets are shared fake-user materials named `ALD | <Preset>`; skip
  linked objects and linked data.
- God Rays are refreshed on `frame_change_pre` by `update_god_rays` without
  rebuilding: it rewrites `Sun Position` and mutes `Strength` to 0 when the sun is
  behind the camera. `Size`, `Iterations` (6) and `Fade` (0.95) are set at build.
  The Sun Beams node is **always created** when `god_rays` is on; with the sun
  behind, it starts at `(0.5, 0.5)` and strength 0 so the handler can find it.
- Float sliders use `compositor.update_params(scene)`, which finds nodes by fixed
  names (`ALD | Halation`, `ALD | Kuwahara`, `ALD | Depth Range`,
  `ALD | Light Wrap Blur/Mask/Edge/Over`, `ALD | Lens`, `ALD | God Rays`,
  `ALD | Ink Normal Gain`, `ALD | Haze Range/Strength/Color`) and rewrites
  sockets. Measured 0.34 ms vs 5.3 ms for a full rebuild.
- Light Wrap, Ink and Aerial Haze share one `_silhouette_mask` call in `build`;
  pass the mask down. `_depth_edges(..., y_offset=-1600)` keeps the ink chain
  visually separate in the Node Editor.
- Normal ink needs `view_layer.use_pass_normal = True`; `_normal_edges` blurs the
  Normal pass by 1.5 px, subtracts, takes vector length, curves 0.01..0.14 and
  multiplies by the normal sensitivity and geometry mask. Combine with the depth
  edge via `MAXIMUM`.
- World gradient group marker is **9**. Inputs include `Star Amount`, `Star
  Density` (Voronoi scale, default 180), `Cloud Flatness` and `Cloud Offset`
  (vector). Exact shell point is `(Vx*t, Vy*t, Vz)` with
  `t=0.55/(max(Z,0.015)+0.18)`, then Mapping
  `Scale=(0.75, 0.75, 1.25 + 3.0 * Cloud Flatness)`; Cloud Offset feeds the
  Mapping location (`frame * cloud_wind * (0.02, 0.005, 0)`). Stars use the
  unoffset view vector. `Cloud Flatness=0.65` reproduces Z=3.2.
- Micro stars: Voronoi Scale = `Star Density * 2.5`; distance curve 0..0.040,
  POWER 2.5, multiplied by a 45-scale Noise -> MapRange 0.48..0.78 magnitude
  mask, plus a 0.24-wide halo at 0.22, then zenith 0.06..0.28, sun hide
  0.96..0.995 and `1 - cloud_amount`. Star color is (12.0, 12.5, 15.0).
- Sun Glow has two lobes: narrow `gamma+^16 * 0.65` gated by `mu_s=L.z`
  (smoothstep -0.08..0.08), and wide
  `gamma+^3.5 * smoothstep(0.75,0,abs(Vz)) * 0.45`; sum scaled by
  `Sun Glow/0.45`, tinted by Sun Color, ADDed before clouds.
- Solar delta uses the full rho resampled at `p+0.12L`; `Cloud Delta Gain` and
  `Cloud Rim Boost` are explicit group inputs (default 1.0), not hidden
  multipliers. Low clouds mix toward Horizon Color by `(1-horizon)*0.65`.
- Optional contrails use a stretched view-vector noise (0.12,5.0,0.12),
  noise Scale 9, band 0.60..0.615, altitude 0.08..0.30, group input
  `Contrails`, default 0, factor 0.18. `Sky Accent`/`Sky Accent Amount` add an
  optional band within 0.07 of the mid-sky stop.
- `ensure_sun` only reapplies the preset `sun_rotation` when
  `ald_last_palette` changes. `sync_sun_angles` writes the elevation/azimuth UI
  fields behind `_syncing_angles`; `apply_sun_angles` moves the sun and calls
  `cameras.update_transforms`. Stage Backlight sets its toggles before applying
  the final angles, because Sun Disk can trigger a world refresh.
- `sun_toward` uses `matrix_world` when the sun has any constraint; only an
  unparented, unconstrained auto sun uses `rotation_euler`.
- Shadow Tint off = AO strength 0 while Cel/Rim stay on; the X operator removes the
  group and disables Cel/Rim. Material exclusion uses `mat["ald_exclude"]` and is
  respected by `sync_scene`, `sync_one` and material preset apply.
- Rim Bias maps Sun=1, Contour=0, Backlight=-1. Terminator Warmth is an additive
  `Sun Color * smoothstep(0..0.12, abs(N.L))` band; Skin is boosted to 0.35.
- Gate pixel ratios: shadow ~2.60 %, wrap ~16.06 %, ink ~3.45 %, haze ~63.04 %
  (gate plane fills the frame), toon ~1.59 %, rim ~7.12 %.
- Shadow tint uses a `MULTIPLY` Mix on Base Color; palette `shadow_tint` colors are
  normalized (max component 1) so textures keep their detail in shadows.
- Material presets include `EMISSION`; set `Emission Color` / `Emission Strength`,
  and reset emission strength to 0 for non-emissive presets.
- Sidebar N panel: `bl_space_type="VIEW_3D"`, `bl_region_type="UI"`,
  `bl_category="Anime Look"`. In tests set
  `region.active_panel_category = "Anime Look"` to select it.
- World gradient (`ald_build = 8`) also hosts the sun disk, stars and clouds. Inputs:
  `Sun Direction` (toward the sun, i.e. `-light_direction`), `Sun Inner/Outer`
  (cosine thresholds), `Sun Color/Strength`, `Cloud Shadow/Mid/Light`,
  `Cloud Amount/Scale`. Palette colors are wired through these sockets, never
  baked into ColorRamp stops.
- Create/tint the sun **before** applying the world gradient, otherwise the first
  apply sees no sun and writes a zero sun direction. Sun/cloud frame updates run
  on `frame_change_post` so matrices are evaluated.
- Anime clouds: Perlin-Worley density, weights 0.38 inverted Voronoi F1 +
  0.44 N1 + 0.18 N2, coverage 0.50..0.535. The old raw 3D noise produced
  vertical camouflage; a naive plane projection (`x/z`, `y/z`) produced rows,
  so use the normalized projected vector plus the curved shell and dynamic
  Z flatness. Shading is directional: `delta = N1(p) - N1(p + 0.12 L)` drives
  Cloud Shadow/Mid; fringe 0.50..0.545, sun edge -0.01..0.04 and gamma factor
  drive Cloud Light. Do not put Cloud Light at the dense center.
- Ink lines reuse `_depth_edges(..., band_size=0, edge_size=ink_size)`, multiply
  the image by a dark `shadow_tint * 0.25` color; the gate pixel ratio is ~2.5 %.
- Custom colors: `palette.effective(scene, key)` applies overrides and
  `palette.shadow_tint_for(scene)` must be used by every material sync path.
- Shadow Tint v2 inputs: `Color`, `Tint`, `Strength`, `Distance`, `Sun Direction`,
  `Sun Color`, `Toon Strength`, `Terminator Sharpness`, `Rim Strength`,
  `Rim Width`. Terminator = MapRange(`N·L`, -sharpness..sharpness → 1..0),
  combined with AO via `MAXIMUM`, then a `MULTIPLY` mix on Base Color.
- Rim = `Layer Weight.Facing` through a MapRange `1 - Rim Width .. 1` (narrow
  Fresnel band), multiplied by `max(N·L, 0)` and `Rim Strength`, then `Sun Color`
  scaled and added to the shaded color. A broad Layer Weight rim covered 68 % of
  the gate frame; the threshold curve brought it to ~6.5 %.
- `Geometry.Normal` is world space; `Sun Direction` is **toward** the sun. The sun
  direction/color are refreshed by `materials.update_sun` on `frame_change_post`.
- Shadow Tint interface upgrades must **not** clear the interface: `_ensure_socket`
  adds the new sockets so external texture links to the group node survive.
- HAIR preset rim boost: `+0.3` strength and width capped at 0.35, applied by
  material name in `_set_look`.
- Gate toon/rim pixel ratios at 128×128: terminator ~1.3 %, rim ~6.5 % (edge-local).
- Effective palette precedence: **camera override > `ALD:` marker > `Scene.ald.palette`**.
  `look.effective_palette` resolves it, `look.apply` applies palette + materials +
  stack, `look.apply_world` updates only world/sun for horizon/cloud controls.
- `Camera.ald` is a PointerProperty on **camera data**; the active camera is
  `scene.camera`. The camera handler caches `(camera_name, override_key)` and skips
  when both previous and current cameras have no override, so temporary test
  cameras do not trigger rebuilds.
- Markers must **not** write `Scene.ald.palette`: the base palette stays intact.
  `look.apply` stores `ald_effective_palette`, `ald_effective_source` and
  `ald_active_shot`. `palette.shadow_tint_for` and the compositor glare tints use
  the effective key.
- Do not touch `bpy.data` during add-on registration (it is `_RestrictData`);
  initialize handler caches lazily instead.
- Sun disk vectors must be **normalized** before `DOT_PRODUCT` (`Vector Math →
  Normalize` on `Generated` and `Sun Direction`); near-1 cosine thresholds are
  unstable otherwise.
- World group marker is **6**. Inputs include `Mid Sky Color` and `World Strength`.
  The sky uses a 4-zone mix (ground → horizon → mid → zenith); presets are
  Scene-Linear Rec.709 and may exceed 1.0 (HDR), never sRGB.
- Visible sky vs ambient: `Light Path → Is Camera Ray` mixes
  `gradient * World Strength` (ambient) with the full gradient (camera rays).
  Background Strength is 1.0 when the gradient is active; flat worlds keep the
  preset strength.
- Cloud shading uses the full-rho solar finite difference: `body_mix` from
  `delta*DeltaGain + 0.15*(Vz-0.3)` blends Shadow -> Mid; the
  fringe/sun-edge/gamma product, optionally scaled by RimBoost, blends Cloud
  Light on the sunward edge. This replaced density-only bands.
- Preset `sun_rotation` is applied only to auto-tagged suns; user suns keep their
  rotation. `sun_toward` reads `rotation_euler` for an unparented auto sun to avoid
  stale matrices; `ensure_sun` no longer calls `view_layer.update()` (depsgraph
  re-entrancy).
- Shadow Hue Lift (group input, default 0.18) adds `Tint * combined * lift` after
  the MULTIPLY tint, so warm materials take the cool shadow hue without losing
  texture.
- Changing the palette while `custom_colors` is active refreshes the custom
  sky/horizon/sun/shadow values from the newly selected preset.
- `cameras._on_depsgraph` also calls `update_transforms(scene)`, caching
  `(sun Z, sun color, camera Z/location/lens/shift/sensor)` and pushing updates to
  `palette.update_sun_controls`, `materials.update_sun`,
  `compositor.update_god_rays` without rebuilding. Unchanged states skip.
- Ink internal edges: when `band_size == 0`, multiply the 0.05 m threshold by 8
  (clamped) so 15–20 cm depth steps read as solid lines.
- Custom colors: `compositor.update_params` refreshes `ALD | Ink Color` and the
  halation/god-ray `Tint` via `_glare_color`, which uses `custom_sun` when active.
- Rim emission: Shadow Tint has a second `Emission` output (rim + 0.12 × shadow
  tint × combined). `_wire_emission` links it to Principled Emission Color, stores
  `ald_em_color`/`ald_em_strength`, skips materials with existing emission, and
  restores on clear.
- Gate pixel ratios: ink ~3.45 %, rim ~7.12 % (edge-local);
  shadow ~2.60 %, toon ~1.59 %.
- UI sub-panels use `bl_parent_id`; the parent keeps the actions and stack status.
- ColorRamp element colors are static; palette colors must be wired through group
  sockets (Mix nodes), not baked into ramp stops.
- The AO node does produce occlusion in both EEVEE and Cycles in 5.1 (see TECH_NOTES).
- Comparing two Python node wrappers with `is` can return False for the same node
  after operators run. Compare `as_pointer()` in tests.

## Rules
- Never save the user's `.blend` unless asked.
- Shadow tint is opt-in and must stay reversible: clearing it restores the original
  Base Color link or value. Do not touch linked-library materials.
- Test GUI panels with a screenshot before claiming UI works.
- Float sliders must use `compositor.update_params`, never rebuild the stack;
  rebuild only for topology, palette or toggle changes.
- Keep the stack idempotent: rebuilding must not duplicate groups, nodes or scenes'
  stacks.
- Auto-Sun may create a light; tag it `ald_auto_sun` and never remove user lights.
- Rebuild the stack after changing the render camera's clip end: the light-wrap
  depth threshold is baked at build time.
- Moving the sun/camera without changing frames still requires Build when God Rays
  are on; animated moves refresh through the frame handler.
- Shot markers are opt-in and must never apply a palette on every frame; respect
  `ald_active_shot`.
- Material presets only touch selected, non-library objects.
- Use `palette.shadow_tint_for(scene)` (not `shadow_tint(key)`) wherever materials
  are synced, so custom palette colors are respected.
- Sun disk/cloud controls call `apply_palette` (world inputs), not a compositor
  rebuild.
- Keep the rim edge-local: use the `1 - Rim Width` Fresnel threshold, not raw
  Layer Weight Facing.
- `sync_scene`/`sync_material` must pass the `_look` dict so toon/rim values stay
  in sync; never rebuild materials from the frame handler.
- Palette changes and shots go through `look.apply`/`look.apply_world`, never a
  direct `settings.palette = key` for temporary overrides.
- Never overwrite existing emission on materials; the rim emission wiring must
  stay reversible and skip emissive presets.
- Keep the depsgraph transform handler socket-only; never rebuild nodes from it.
- `bl_info`, `blender_manifest.toml`, `README.md`, `CHANGELOG.md` versions stay aligned.

See `TECH_NOTES.md` for the full spike results.
