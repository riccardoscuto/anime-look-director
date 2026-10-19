# Anime Look Director

Atmospheric palettes and a non-destructive anime compositor stack for Blender 5.1+.

## What it does (v0.1)
- Four atmosphere presets (Shinkai Golden Hour, Ghibli Summer Noon, Rainy Tokyo,
  Cyberpunk Neon) that drive world color, sun color/energy and halation tint.
- A node-group compositor stack:
  `Render Layers → Glare (Bloom) → Kuwahara (depth-mixed) → Lens Distortion → Group Output`.
- One-click enable of the viewport compositor.

## Install (development)
The folder lives in `Blender/5.1/scripts/addons/anime_look_director`.
Enable it in Preferences → Add-ons (or keep it enabled in this profile).

## Verification
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python-exit-code 1 --python preset_dev\verify.py
```

## Roadmap
- v0.1 — stack + palettes (current skeleton)
- v0.2 — UI polish, world gradients, material shadow-tint sync
- v0.3 — Light Wrap, God Rays presets, per-shot overrides
- v1.0 — store release (legacy ZIP + Extension), presets and docs
