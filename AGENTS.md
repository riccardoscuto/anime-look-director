# Anime Look Director — project instructions

Blender add-on: atmospheric palettes + non-destructive anime compositor stack.

## Target
- Blender **5.1.2** on Windows (compositor node-group API `scene.compositing_node_group`).
- Python 3.13 / NumPy available inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match.

## Verify (run after every change)
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
```
Expected output: `ALD GATE: PASS`.

For live work: Blender Lab MCP bridge on `localhost:9876` (keep calls short).

## Architecture
- `properties.py` — `Scene.ald` settings (palette, toggles, sliders).
- `palette.py` — atmospheric presets (world + sun + glare tint).
- `compositor.py` — builds/removes `ALD | Compositor Stack` (Render Layers → Glare → Kuwahara (depth-mixed) → Lensdist → Group Output).
- `operators.py` — `ald.build`, `ald.remove`, `ald.apply_palette`, `ald.viewport_compositor`.
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

## Rules
- Never save the user's `.blend` unless asked.
- No destructive edits to materials in v0.1; scene world/sun only.
- Test GUI panels with a screenshot before claiming UI works.
- Keep the stack idempotent: rebuilding must not duplicate groups or nodes.

See `TECH_NOTES.md` for the full spike results.
