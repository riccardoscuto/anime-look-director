# Phase 3 - Sun System 2.0

Branch `feature/celestial`, based on the Gate 2 Moon work. The Sun disk and
glow are now configurable independently of the Sun light. Existing presets and
their default render are preserved.

## What changed

- **Angular size** is explicit: `Sun Size (deg)` is the disk radius, range
  **0.1-15 deg** (was 0.1-10).
- **Edge softness** is an absolute width in degrees (0.02-3.0), independent of
  the size. The default 0.25 deg reproduces the old 1 deg preset disk exactly.
- **Glow extent** is `Glow Radius` (4-45 deg, default 18). It scales the wide
  and core falloff exponents; 18 deg reproduces the old 3.5 / 16 exponents.
- **Glow intensity** remains `Sun Glow`, plus a hidden style gain used by
  Anime Cinematic so the broader glow does not wash the sky.
- **Disk Color** tints only the visible disk, never the Sun light.
- **Sun Style**: `Sun Clean` (edge 0.25, radius 18, neutral tint, no limb
  warmth) and `Anime Cinematic` (edge 0.6, radius 22, gain 0.65, warm tint,
  limb warmth 0.35). Styles do not touch size, energy or direction.
- **Limb warmth**: a subtle warm tint toward the disk edge, used by Cinematic.
- **Horizon Fade** (0.5-20 deg, default 7) scales the existing disk/glow fade
  widths. The default preserves the old behaviour exactly.
- **Camera-only sun**: the disk and glow are removed from the ambient branch,
  so enlarging the disk cannot change object lighting. Only the visible sky
  changes.

Controls live in `Atmosphere & Sun`; the View3D sidebar uses the same draw
function. The Sun light energy, color and rotation are never written by any of
these controls.

## Defaults are neutral

`preset_dev/sun_legacy_file.py` renders a real 2.63.0 scene;
`preset_dev/sun_default_check.py` opens it with the current build and compares
the pixels:

| Check | Result |
|---|---|
| Legacy build -> current build | 35 -> **40** |
| Max pixel delta, default Sun | **0.00392** (JPEG-scale, sky only) |
| Sun light energy / rotation after size 1 -> 12 | unchanged |
| Object region delta, size 1 -> 12 | **0.0** |

The default Sun therefore matches the released look, and resizing the disk is
purely visual.

## Boards

- `phase3/sizes_board.jpg` - radius 0.5 / 2 / 6 / 12 deg, Clean, elevation 25.
- `phase3/styles_board.jpg` - Clean vs Anime Cinematic at 3 and 10 deg.
- `phase3/horizon_board.jpg` - elevation -2 / 0.5 / 3 / 8 deg, radius 4.

Individual renders are produced by `preset_dev/sun_phase3.py`; only the boards
and metrics are kept.

## Technical checks

`preset_dev/sun_phase3_check.py` -> `phase3/check.json`:

| Check | Result |
|---|---|
| Sun light energy/rotation on resize | unchanged (4.2, same rotation) |
| Object lighting on resize | delta **0.0** |
| Cinematic values | edge 0.6, radius 22, gain 0.65, limb 0.35 |
| Clean values | edge 0.25, radius 18, gain 1.0 |
| Horizon -2 vs +0.5 | luma **0.449 -> 0.471** |
| Save/reopen | fade/color kept, pixel delta **0.0** |
| World nodes / build | **812 / 2.84 s** |

Existing gates: `verify_all` **ALD ALL PASS**, Phase 3 UI **68/68 PASS**.

## Known limits

- The glow remains a Mie-style artistic falloff, not a physical atmosphere.
- No date/time/place Sun position; the elevation/azimuth stay manual.
- The style changes edge, glow radius/gain and disk tint; it deliberately does
  not change size or light energy.
- The Moon light remains deferred; this phase only touches the Sun.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\sun_phase3.py -- --out preset_dev\sun\phase3
python preset_dev\sun_phase3_board.py

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\sun_phase3_check.py
```

The default comparison needs a 2.63.0 `.blend`:
`sun_legacy_file.py` (run with the 2.63.0 package under an isolated
`BLENDER_USER_SCRIPTS`) then `sun_default_check.py`.

## Gate 3

**Technical PASS. Visual approval pending.** The size/style boards and the
horizon strip are the review material.
