# Anime Look Director — project instructions

Blender add-on: atmospheric palettes + non-destructive anime compositor stack.

## Target
- Blender **5.1.2** on Windows (compositor node-group API `scene.compositing_node_group`).
- Python 3.13 / NumPy available inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **0.2.0**).

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
- `properties.py` — `Scene.ald` settings (palette, toggles, sliders, update hooks).
- `palette.py` — atmospheric presets, world gradient group, world + sun apply.
- `compositor.py` — builds/removes `ALD | Compositor Stack` (Render Layers → Glare
  → Kuwahara (depth-mixed) → Light Wrap → Lensdist → Group Output).
- `materials.py` — shared `ALD | Shadow Tint` group, reversible Base Color insertion.
- `operators.py` — `ald.build`, `ald.remove`, `ald.apply_palette`,
  `ald.clear_shadow_tint`, `ald.viewport_compositor`.
- `panels.py` — Scene properties panel.
- `preset_dev/verify.py` — headless gate.

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
  a silhouette mask. Use `Depth < 1e6` (world depth is ~1e10).
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
- Keep the stack idempotent: rebuilding must not duplicate groups or nodes.
- `bl_info`, `blender_manifest.toml`, `README.md`, `CHANGELOG.md` versions stay aligned.

See `TECH_NOTES.md` for the full spike results.
