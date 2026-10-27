# Anime Look Director — World Sky Edition

Procedural anime skies for Blender 5.1.2. The World is the product: four-zone
gradient, Sun, clouds, stars and Milky Way, with optional material and
compositor tools.

The 3D FX, Spatial Clouds, atmospheric smoke and FX EXR pass of 2.56.0 are
gone. The full previous version is preserved at the tag
`archive/v2.56.0-full` and in the `v2.56.0` tag.

## What it does

- Seven atmospheric palettes, applied to the World and Sun without touching the
  compositor.
- Four-zone sky: Ground, Horizon, Mid Sky, Zenith, with horizon offset and
  softness.
- Sun disk, Sun Glow, Sun Beams, elevation/azimuth and backlight staging.
- World clouds: amount, scale, vertical/flatness, wind, contrails, delta gain,
  rim boost, custom cloud colors.
- Stars, density, Milky Way.
- Optional Shadow Tint / Cel / Rim and material presets.
- Optional general compositor: halation, painterly, light wrap, dispersion,
  sun beams, ink, aerial haze.
- Camera overrides and timeline palette markers.
- Reversible removal and explicit handling of legacy ALD data.

## Install

Build the extension:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\build_release.py
```

Install `dist/anime_look_director-2.57.0.zip` in Blender 5.1.2:
`Edit > Preferences > Extensions > Install from Disk`.

The add-on is also usable from the source directory as a legacy add-on.

## Quick start

1. Open the Scene properties or the View3D sidebar (`N > Anime Look`).
2. Choose a palette.
3. **Apply Palette**. The World and Sun update immediately; no Build Stack is
   required.
4. Adjust World, Sun, clouds and stars in **World & Shadows**.
5. Enable the compositor only if you want the optional art filters.

## Version 2.57.0 scope

- World-only operational path.
- No FX objects, collections, Geometry Nodes, smoke volumes or EXR pass.
- The compositor is optional and contains only general effects.
- Old `.blend` files are not cleaned automatically. Use the **Legacy ALD Data**
  panel: **Disable** hides the old ALD collections (reversible), **Remove**
  deletes them after an explicit action. See `MIGRATION_2_57.md`.

## Verification

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify_all.py
```

The Phase 0 comparison against v1.0.3 and v1.1.0 is in
`preset_dev/world_baseline/` (`contact_1280.png`, `contact_1920.png`,
`contact_sun.png`, README with the findings).

## License

GPL-3.0-or-later. See `LICENSE`.
