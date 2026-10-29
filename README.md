# Anime Look Director — World Sky Edition

Procedural anime skies for Blender 5.1.2. The World is the product: four-zone
gradient, Sun, clouds, stars and Milky Way, with optional material and
compositor tools.

The 3D FX, Spatial Clouds, atmospheric smoke and FX EXR pass of 2.56.0 are
gone. The full previous version is preserved at the tag
`archive/v2.56.0-full` and in the `v2.56.0` tag.

## What it does

- Twelve atmospheric palettes (seven original + Soft Dawn, Blue Hour,
  Cloudy Afternoon, Stormy Sunset, Moonlit Night), applied to the World and Sun without touching the
  compositor.
- Four-zone sky: Ground, Horizon, Mid Sky, Zenith, with horizon offset and
  softness.
- Sun disk, Sun Glow, elevation/azimuth and backlight staging.
  Sun Beams lives in the optional compositor.
- World clouds: three families (Cumulus, Stratocumulus, Cirrus),
  coverage, scale, vertical, flatness, breakup, detail, seed, sun lighting,
  wind, contrails, rim boost and custom colors.
- Stars, density, Milky Way.
- Four controlled shooting stars in the World (no objects or particles):
  start, duration, position, direction, angular length, curvature, trail,
  thickness, brightness, glow and color. Thickness is capped at 0.01 rad and
  curvature is an optional per-event sine bow.
- Optional Shadow Tint / Cel / Rim and material presets.
- Optional general compositor: halation, painterly, light wrap, dispersion,
  sun beams, ink, aerial haze.
- Cloud Sun Scatter: an optional sun-facing silver-lining accent under World
  Clouds > Lighting.
- View3D sidebar mirrors the full Scene Properties sections; compositor
  inactive / configured / active states are explicit.
- Camera overrides and timeline palette markers.
- Reversible removal and explicit handling of legacy ALD data.

## Install

Build the extension:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\build_release.py
```

Install `dist/anime_look_director-2.63.0.zip` in Blender 5.1.2:
`Edit > Preferences > Extensions > Install from Disk`.

The add-on is also usable from the source directory as a legacy add-on.

## Quick start

1. Open the Scene properties or the View3D sidebar (`N > Anime Look`).
2. Choose a palette.
3. **Apply Palette**. The World and Sun update immediately; no Build Stack is
   required.
4. Adjust Sun, clouds and stars in **Atmosphere & Sun** and **World Clouds**.
5. Enable the compositor only if you want the optional art filters.

## Shooting stars

- **Start Frame** is the first visible frame. **Duration** is the exact number
  of visible frames: start 10 with duration 24 is visible at frames 10..33 and
  absent at 9 and 34. The minimum duration is 2.
- **Direction** is a bearing in the local sky: 0 is horizontal, +90 is up.
  **Angular Length** is the length of the great-circle path in degrees.
- **Add Shooting Star** places the event in the current camera direction and
  warns when the camera looks at the ground, there is no camera, or clouds may
  hide it. It never uses a high minimum elevation to avoid geometry problems.
- **Preview** moves the timeline into the event and frames it in the 3D
  viewport when one is available. The camera, its keyframes and its animation
  are not changed.
- Four events maximum; Add and Duplicate both report the limit.
- Events saved before 2.63 gain the start frame; the last visible frame is
  unchanged: start 10 / duration 24 was visible 11..33 and becomes 10..33.
  The count grows from duration - 1 to duration. `Direction` is now a true
  local bearing, so review old trajectories after opening. `Curvature`
  defaults to 0 (straight great-circle arc); thickness is capped at 0.01 rad.

## Version 2.63.0 scope

- World-only operational path.
- No FX objects, collections, Geometry Nodes, smoke volumes or EXR pass.
- The compositor is optional and contains only general effects.
- Phase 2 cloudless sky: broad sky-accent transition and Sun below-horizon fade.
- Phase 3 first gate: Cumulus / Stratocumulus / Cirrus silhouettes under the same sun.
- Phase 6 release matrix: 22 cells covering families, Sun direction, palettes,
  coverage, camera, wind and shooting stars (`preset_dev/phase6/`).
- 17-check technical gate: idempotence, determinism, wind, event isolation,
  scene ownership, persistence and cost.
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
