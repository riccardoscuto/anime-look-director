# Anime Look Director

Atmospheric palettes and a non-destructive anime compositor stack for Blender 5.1+.

## What it does (v0.5.0)
- Six atmosphere presets (Shinkai Golden Hour, Ghibli Summer Noon, Rainy Tokyo,
  Cyberpunk Neon, Sakura Spring, Twilight Dusk) driving world, sun, shadow tint
  and halation tint.
- **Auto Sun**: applying a palette creates a sun light when the scene has none
  (can be disabled in the panel).
- Palette-driven **world gradient** with separate sky, horizon and ground colors,
  plus horizon offset and softness.
- **Sun disk** aligned with the sun direction, with size and strength.
- **Anime clouds**: two-layer procedural clouds in palette colors, with amount
  and scale controls.
- **Custom palette colors** for sky, horizon, sun and shadow (per scene).
- **Shadow tint** on scene materials: a reversible **multiplicative** node group
  that preserves texture detail while shifting shadowed areas toward the palette
  color.
- **Cel terminator** driven by the palette sun (`N·L`), with Cel Shadow strength
  and Terminator sharpness; combined with AO for contact shadows.
- **Directional rim light** on the sun-facing edge, tinted by the sun color;
  the HAIR preset gets a stronger angel-ring rim.
- **Light Wrap** around object silhouettes and environment edges.
- **Anime Ink Lines**: thin depth-based outlines tinted by the palette shadow.
- **God Rays** (optional Sun Beams glare anchored to the sun's screen position,
  refreshed on frame change).
- **Shot markers**: palettes driven by `ALD:<PALETTE>` timeline markers, with a
  `Mark Shot` button.
- **Material presets** (Skin, Hair, Fabric, Metal, Emission) for selected objects.
- A node-group compositor stack, **one per scene**:
  `Render Layers → Glare (Bloom) → Sun Beams → Kuwahara (depth-mixed) → Light Wrap → Ink Lines → Lens Distortion → Group Output`.
- One-click enable of the viewport compositor.
- **Sidebar N panel** (`View3D > Anime Look`) for palette, world, shadow and
  compositor controls without leaving the viewport.

## Install (development)
The folder lives in `Blender/5.1/scripts/addons/anime_look_director`.
Enable it in Preferences → Add-ons (or keep it enabled in this profile).

## Look-dev
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python preset_dev\lookdev.py -- --out "C:\Temp\ald_lookdev"
```
Renders the six palettes on a fixed scene, writes a 3×2 contact sheet and prints
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
- v0.2.1 — auto sun, per-scene stacks
- v0.3 — God Rays, shot markers, material presets
- v0.3.1 — God Rays refresh/size, Emission preset
- v0.3.2 — in-place sliders, multiplicative shadow tint, sidebar N panel
- v0.4.0 — sun disk, anime clouds, ink lines, Sakura/Twilight, custom colors
- v0.5.0 — cel terminator, directional rim light, hair angel ring (current)
- v1.0 — store release (legacy ZIP + Extension), presets and docs

## Recap
Italian overview of the whole add-on: [`RECAP.md`](RECAP.md).
