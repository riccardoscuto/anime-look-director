# Phase 1-2 - Procedural Moon

Branch `feature/celestial`. Phase 1 (full disk and four styles) is **visually
approved**; Phase 2 (phases, earthshine, Sun link) is implemented and ready for
its visual gate. The Moon is **off by default**: existing files and the twelve
presets are unchanged.

## Phase 1 (approved)

- Node group `ALD | Moon`, nested inside `ALD | World Gradient`. Moon logic in
  `shaders/moon.py`, shared helpers in `shaders/common.py`; `palette.py` only
  adds the group node, the sockets and the final composite.
- Angular disk from `dot(view, direction)` against `cos(radius)`, size in
  degrees, independent soft edge, orthographic sky-cap projection (circular at
  any position, no camera-distance dependence).
- Surface: maria, two crater layers with per-cell radius and rim strength,
  micro grain, warm/cool tint, spherical limb darkening, deterministic seed.
- Four styles: Anime Clean, Anime Painterly, Detailed Moon, Ethereal Moon.
  Clean and Detailed were approved in the first review; Painterly and Ethereal
  were refined after it (lower glow/halo, sharper edge, more contrast).
- Compositing: disk and halo are separate premultiplied layers; the halo is
  multiplied by `1 - disk_alpha` and never lifts the surface. One mix in the
  World. Clouds pass in front, stars/Milky Way never show through the disk.
- File migration: World group `ald_build 37`, Moon group `ald_moon_version 2`;
  a real 2.63.0 file rebuilds on explicit Apply with pixel delta 0.0 and the
  Moon then works (see Migration below).

Evidence: `styles/moon_styles.jpg` (4 styles x 1.2/3/6 deg) and the older
`checks/` images; style metrics in `styles/metrics.json`.

## Phase 2 (implemented)

- Eight phases plus continuous illumination: New, Waxing Crescent, First
  Quarter, Waxing Gibbous, Full, Waning Gibbous, Last Quarter, Waning Crescent;
  the `Illumination` slider covers everything in between. Selecting a named
  phase writes the slider; moving the slider switches the menu to Custom.
- The lit fraction comes from a sphere normal and a light vector, not a dark
  circle overlay. The terminator is a true great circle; its soft band lives on
  the dark side only, so the approved full Moon stays fully lit.
- Modes: **Manual** (illumination, waxing/waning, lit-side rotation) and
  **Sun Linked** (light direction from the Sun and Moon sky directions; not an
  ephemeris simulation).
- Earthshine: a faint fill on the unlit side. The Moon body stays opaque at any
  visible phase, so stars never shine through it; at New the disk fades out.
- Halo: tight + wide terms, scaled by illumination, dimmed by clouds.
- Animation: the phase property is keyframable; the frame handler refreshes
  the World each frame. Verified 0 -> 1 over keyframes.

Controls: Enable, Style, Phase Mode, Phase, Illumination, Waxing, Lit Side
Rotation, Earthshine, Size, Azimuth, Elevation, Brightness, Color, Surface
Detail, Crater Strength, Surface Contrast, Edge Softness, Glow, Halo Radius,
Halo Color, Surface Seed. Scene panel and View3D sidebar share `draw_moon`.

## Boards

- `phases/named_board.jpg` - the eight phases, Detailed Moon, 4 deg, same sky
  and camera.
- `phases/sweep_board.jpg` - continuous illumination 0.0 -> 1.0 in nine steps.
- `phases/sun_linked_quarter.png` - Sun 90 deg from the Moon: quarter phase,
  lit toward the Sun.
- `phases/check/crescent_context.png` - waxing crescent with stars and clouds
  in front; no star shines through the disk.
- `styles/moon_styles.jpg` - the approved Phase 1 style board.

Only boards and metrics are kept in the repo; individual renders are produced
by the scripts.

## Technical checks

Phase 1: `preset_dev/moon_phase1_check.py` -> `checks/checks.json`.

| Check | Result |
|---|---|
| Disk circular at 22 deg and at 60 deg | aspect **1.004 / 1.000** |
| Moon below the horizon | pixel delta **0.0** vs Moon off |
| Save/reopen | pixel delta **0.0** |
| Full Moon vs Phase 1 | unchanged (lit = 1 across the disk) |

Phase 2: `preset_dev/moon_phase2_check.py` -> `phases/check/check.json`.

| Check | Result |
|---|---|
| Lit area fractions 0/0.25/0.5/0.75/1 | **0.0 / 0.259 / 0.511 / 0.759 / 1.0** |
| Waxing / waning side | centroid **0.622 / 0.376** |
| Sun Linked, Sun 90 deg away | fraction **0.44**, lit toward the Sun |
| Phase animation, frames 1/8/16/24 | **0.0 / 0.23 / 0.73 / 1.0** |
| Persistence | phase/waxing kept, pixel delta **0.0** |
| World group / Moon group | **798 / 143** nodes |
| Build time | **2.70 s** (2.63.0 baseline 2.71-3.07 s) |

Existing gates: `verify_all` **ALD ALL PASS**, Phase 3 UI **68/68 PASS**.

## Migration from 2.63.0

`preset_dev/moon_legacy_file.py` builds a real 2.63.0 `.blend` from the
published package; `preset_dev/moon_migration_check.py` opens it with the
current build. Evidence: `migration/migration.json`,
`migration/legacy_before.png`, `migration/legacy_moon.png`.

- legacy file: `ald_build 35`, no Moon socket, no `ALD | Moon`;
- after explicit Apply: `ald_build 37`, Moon sockets, `ald_moon_version 2`;
- render before/after with the Moon off: pixel delta **0.0**;
- enabling the Moon: disk visible, no errors.

Migration happens only on Apply, never on file open. Bump `ald_build` and
`ald_moon_version` together on the next Moon schema change.

## Known limits

- Sun Linked is a direction-based artistic link, not date/place astronomy.
- The halo is still a ring around the whole disk at crescent phases; the lit
  limb glow and the dark-limb ring are not separated yet.
- The Moon light for object illumination is **not implemented**. The disk is
  World-only; existing Sun lights are untouched. That optional extension needs
  its own identification/ownership/cleanup and is deferred.
- Craters remain stylised rather than photographic.
- `Moonlit Night` still uses its stylised Sun disk; enabling the real Moon
  there remains a later preset decision.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\moon_phases.py -- --out preset_dev\moon\phases
python preset_dev\moon_phases_board.py

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\moon_phase2_check.py
```

Phase 1 commands are unchanged (`moon_styles.py`, `moon_styles_board.py`,
`moon_phase1_check.py`).

## Gate status

**Gate 1: VISUAL APPROVED** (full disk and the four styles).
**Gate 2: READY - awaiting visual approval.** Phase 3 (Sun System 2.0) does not
start until the phase board and the crescent-in-context render are approved.
