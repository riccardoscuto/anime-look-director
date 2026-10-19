# Anime Look Director

Atmospheric palettes and a non-destructive anime compositor stack for Blender 5.1+.

## What it does (v0.2.1)
- Four atmosphere presets (Shinkai Golden Hour, Ghibli Summer Noon, Rainy Tokyo,
  Cyberpunk Neon) driving world, sun, shadow tint and halation tint.
- **Auto Sun**: applying a palette creates a sun light when the scene has none
  (can be disabled in the panel).
- Palette-driven **world gradient** with separate sky, horizon and ground colors,
  plus horizon offset and softness.
- **Shadow tint** on scene materials: a reversible node group mixes Base Color
  toward the palette shadow color where ambient occlusion is low.
- **Light Wrap** around object silhouettes and environment edges, using a
  depth-derived mask plus depth-discontinuity edges.
- A node-group compositor stack, **one per scene**:
  `Render Layers → Glare (Bloom) → Kuwahara (depth-mixed) → Light Wrap → Lens Distortion → Group Output`.
- One-click enable of the viewport compositor.

## Install (development)
The folder lives in `Blender/5.1/scripts/addons/anime_look_director`.
Enable it in Preferences → Add-ons (or keep it enabled in this profile).

## Look-dev
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python preset_dev\lookdev.py -- --out "C:\Temp\ald_lookdev"
```
Renders the four palettes on a fixed scene, writes a 2×2 contact sheet and prints
luminance, contrast and saturation per palette. It never saves a `.blend`.

## Verification
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python-exit-code 1 --python preset_dev\verify.py
```
Expected output: `ALD GATE: PASS`.

## Roadmap
- v0.1 — stack + palettes
- v0.2 — world gradient, material shadow tint, light wrap
- v0.2.1 — auto sun, per-scene stacks (current)
- v0.3 — God Rays presets, per-shot overrides, material presets
- v1.0 — store release (legacy ZIP + Extension), presets and docs
