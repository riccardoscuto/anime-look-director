# Phase 4 - Milky Way 2.0

Branch `feature/celestial`. The band is rebuilt as a structured galactic great
circle, still entirely in the World shader. Existing presets are untouched; the
look changes only where the Milky Way intensity is above zero (Twilight Dusk,
Blue Hour, Moonlit Night).

## Geometry and structure

- **Great-circle plane**: the galactic pole is set by `Rotation` and
  `Elevation`; the bulge is placed along the band by `Core Position`. The
  shader evaluates the signed latitude and the longitude around the core.
- **Width** (5-40 deg), **Core Strength**, **Dust Contrast**, **Dust Density**,
  **Detail**, **Star Concentration**, **Seed**.
- Structure noise uses cylinder coordinates `(cos lon, sin lon, lat)`, so there
  is no seam at 360 degrees.
- A warm bulge, a cooler outer band, a main dust rift and weaker secondary
  branches. Dust darkens the band and reduces the extra stars inside it.
- **Styles**: `Scientific Inspired` (12 deg, warm core, stronger dust) and
  `Anime Cinematic` (14 deg, warmer core, freer color/contrast). Style writes
  width, structure and colors; it does not touch intensity.
- **Enable Milky Way** is separate from the star field; turning it off removes
  only the band and its star boost, never the normal stars.
- **Horizon Fade** (0-20 deg, default 6) is the angular fade at the horizon.

## Integration

- Clouds pass in front: the band is multiplied by the cloud visibility mask and
  the star boost by `1 - dust`.
- The Moon is composited after the band, so the disc is opaque to it.
- Shooting stars are drawn after the band and are unchanged.
- Presets with Milky Way 0 are pixel-equivalent (no color, no star boost).

## Board

`phase4/board.jpg` - eight cells: Moonlit Night Scientific/Cinematic, Blue
Hour, Twilight Dusk, dust contrast 0.20/0.95, core close-up (50 mm) and the band
behind clouds. 16 mm panorama aimed at the core, 900x600.

## Technical checks

`preset_dev/milky_way_phase4_check.py` -> `phase4/check/check.json`:

| Check | Result |
|---|---|
| Stars outside the band, MW on vs off | delta **0.00392** |
| Moon disc, MW on vs off | delta **0.0** |
| Save/reopen | style/dust kept, pixel delta **0.0** |
| World / Milky Way nodes | **790 / 89** |
| Build time | **2.59 s** (2.63.0 baseline 2.71-3.07 s) |

Existing gates: `verify_all` **ALD ALL PASS**, Phase 3 UI **68/68 PASS**.

## Known limits

- The band is a stylised great-circle model, not an astronomical map; the
  scientific style is inspired by the observable structure.
- No date/place calculation of the galactic plane.
- The 360 seam is continuous by construction (cos/sin cylinder coordinates);
  no equirectangular seam render is included.
- Moonlit Night, Blue Hour and Twilight Dusk change by design; the other nine
  presets have Milky Way 0 and keep their look.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\milky_way_phase4.py -- --out preset_dev\milky_way\phase4
python preset_dev\milky_way_phase4_board.py

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\milky_way_phase4_check.py
```

## Gate 4

**Technical PASS. Visual approval pending.** The board is the review material.
