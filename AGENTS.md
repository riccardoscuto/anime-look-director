# Anime Look Director — project instructions

Blender add-on: atmospheric palettes + non-destructive anime compositor stack.

## Target
- Blender **5.1.2** on Windows (compositor node-group API `scene.compositing_node_group`).
- Python 3.13 / NumPy available inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **0.6.1**).

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
- `operators.py` — `ald.build`, `ald.remove`, `ald.apply_palette`,
  `ald.clear_shadow_tint`, `ald.viewport_compositor`.
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
  `ALD | Light Wrap Blur/Mask/Edge/Over`, `ALD | Lens`, `ALD | God Rays`) and
  rewrites sockets. Measured 0.34 ms vs 5.3 ms for a full rebuild.
- Shadow tint uses a `MULTIPLY` Mix on Base Color; palette `shadow_tint` colors are
  normalized (max component 1) so textures keep their detail in shadows.
- Material presets include `EMISSION`; set `Emission Color` / `Emission Strength`,
  and reset emission strength to 0 for non-emissive presets.
- Sidebar N panel: `bl_space_type="VIEW_3D"`, `bl_region_type="UI"`,
  `bl_category="Anime Look"`. In tests set
  `region.active_panel_category = "Anime Look"` to select it.
- World gradient (`ald_build = 3`) also hosts the sun disk and clouds. Inputs:
  `Sun Direction` (toward the sun, i.e. `-light_direction`), `Sun Inner/Outer`
  (cosine thresholds), `Sun Color/Strength`, `Cloud Shadow/Mid/Light`,
  `Cloud Amount/Scale`. Palette colors are wired through these sockets, never
  baked into ColorRamp stops.
- Create/tint the sun **before** applying the world gradient, otherwise the first
  apply sees no sun and writes a zero sun direction. Sun/cloud frame updates run
  on `frame_change_post` so matrices are evaluated.
- Anime clouds: two 3D Noise layers on `Generated` (weights 0.75/0.25), coverage
  0.48–0.56, three tone bands via MapRange 0.46–0.48 and 0.57–0.59. A plane
  projection (`x/z`, `y/z`) produced rows/camo on the sky dome; keep 3D noise.
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
- Gate pixel ratios after the ink gain: ink ~2.8 %, rim ~8.1 % (edge-local).
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
