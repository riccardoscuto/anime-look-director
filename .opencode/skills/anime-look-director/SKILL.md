---
name: Anime Look Director
description: Development of the Anime Look Director Blender add-on (atmospheric palettes, node-group compositor stack, Kuwahara/Glare/Lens). Use for this repository's code, compositor API, palette work, UI and verification.
---

# Anime Look Director (project skill)

Repository: `C:\Users\Riccardo\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\anime_look_director`.

## Start here
- Read `AGENTS.md` and `TECH_NOTES.md`.
- Verification gate:
  `blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py`
  → expect `ALD GATE: PASS`.

## Architecture
- `properties.py` → `Scene.ald` settings (palette, toggles, sliders).
- `palette.py` → world/sun/glare-tint presets.
- `compositor.py` → `ALD | Compositor Stack` (RLayers → Glare → Kuwahara with Depth
  mix → Lensdist → Group Output); idempotent rebuild; remove cleanly.
- `operators.py` → `ald.build`, `ald.remove`, `ald.apply_palette`,
  `ald.viewport_compositor`.
- `panels.py` → Scene properties panel.
- `preset_dev/verify.py` → headless gate.

## Blender 5.1 compositor facts (verified)
- `scene.compositing_node_group`; no `scene.node_tree`, no `CompositorNodeComposite`
  (use `NodeGroupOutput`).
- Glare is socket-driven; `Type` includes `Sun Beams` (no separate node).
- `CompositorNodeKuwahara` exists (`Classic` / `Anisotropic`).
- `Depth` / `Mist` outputs require the view-layer passes.
- Use `CompositorNodeSeparateColor` inside compositor trees.

## Rules
- Never save the user's `.blend` unless asked.
- Rebuilds must be idempotent; no duplicate groups.
- Verify with the gate after every change; test UI panels with a screenshot.
- Keep `bl_info` and `blender_manifest.toml` versions in sync.
