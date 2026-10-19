# Anime Look Director — project instructions

Blender add-on: atmospheric palettes + non-destructive anime compositor stack.

## Target
- Blender **5.1.2** on Windows (compositor node-group API `scene.compositing_node_group`).
- Python 3.13 / NumPy available inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **0.3.2**).

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
- `palette.py` — atmospheric presets, world gradient group, world + sun apply.
- `compositor.py` — builds/removes one `ALD | Compositor Stack` per scene
  (Render Layers → Glare → Sun Beams (optional) → Kuwahara (depth-mixed) →
  Light Wrap → Lensdist → Group Output); also refreshes God Rays on frame change.
- `materials.py` — shared `ALD | Shadow Tint` group plus material presets.
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
- `bl_info`, `blender_manifest.toml`, `README.md`, `CHANGELOG.md` versions stay aligned.

See `TECH_NOTES.md` for the full spike results.
