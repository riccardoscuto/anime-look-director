# Phase 1-2 - Procedural Moon

Branch `feature/celestial`. Phase 1 (full disk, four styles) and Phase 2A
(phase geometry, animation) are visually approved. Phase 2B (earthshine and
halo) is implemented and ready for the final Gate 2 review. The Moon is **off
by default**: existing files and the twelve presets are unchanged.

## Phase 1 (approved)

- Node group `ALD | Moon` inside `ALD | World Gradient`; Moon logic in
  `shaders/moon.py`, helpers in `shaders/common.py`.
- Angular disk from `dot(view, direction)` against `cos(radius)`, size in
  degrees, independent edge softness, orthographic sky-cap projection.
- Surface: maria, two crater layers, micro grain, warm/cool tint, spherical
  limb darkening, deterministic seed.
- Four styles: Anime Clean, Anime Painterly, Detailed Moon, Ethereal Moon.
- Compositing: disk and halo are separate premultiplied layers; the halo is
  multiplied by `1 - disk_alpha`, so it never flattens the surface. Clouds pass
  in front; stars/Milky Way never show through the disk.
- Evidence: `styles/moon_styles.jpg`, metrics in `styles/metrics.json`.

## Phase 2A (approved) - phases and animation

- Eight phases plus continuous illumination. Named phases write the slider;
  moving the slider switches the menu to Custom.
- The lit fraction is a sphere normal against a light vector, not a dark circle
  overlay. The terminator is a great circle; its soft band is on the dark side
  only, so the full Moon stays fully lit.
- Manual mode: illumination, waxing/waning, lit-side rotation. Sun Linked mode:
  light direction from the Sun and Moon sky directions (artistic, not an
  ephemeris).
- The phase property is keyframable; the frame handler refreshes the World.
- Evidence: `phases/named_board.jpg`, `phases/sweep_board.jpg`,
  `phases/sun_linked_quarter.png`.

## Phase 2B (this pass)

- **Earthshine reuses the surface**: the dark side is multiplied by the same
  maria/crater/grain modulation as the lit side, so the surface is faintly
  recognisable instead of a uniform grey disk. Default **0.05** (was 0.12);
  candidates 0.12 / 0.05 / 0.02 are in `phases/2b/earthshine_board.jpg`.
- **Halo follows the lit limb**: a transverse light term weights the halo
  toward the lit side and suppresses the dark-side ring for every style;
  at full phase the term vanishes and the halo stays symmetric. Ethereal keeps
  its wider radius.
- **New Moon has no residual halo**: the halo is gated to zero as the
  illuminated fraction reaches 0.
- **Alpha union corrected**: alpha = disk + halo x (1 - disk), clamped, instead
  of `max`. The premultiplied colour is composited once by the World; the wide
  soft edge test shows no dark ring or double attenuation.
- **Cloud occlusion**: a cloud crossing the disk is rendered in
  `phases/2b/final/crescent_clouds.png`; the disk is hidden where the cloud
  passes, with no abnormal transparency.

## Boards (final review)

- `phases/2b/final_board.jpg` - New, Waxing Crescent, First Quarter, Full,
  Waning Crescent and the crescent with clouds.
- `phases/2b/earthshine_board.jpg` - 0.12 / 0.05 / 0.02.
- `phases/named_board.jpg`, `phases/sweep_board.jpg` - full phase set and the
  continuous sweep, regenerated with the 2B shader.
- `phases/sun_linked_quarter.png`, `phases/2b/final/crescent_clouds.png`.
- Phase 1: `styles/moon_styles.jpg`.

Only boards and metrics are kept; individual renders are produced by the
scripts.

## Technical checks

Phase 1: `preset_dev/moon_phase1_check.py` -> `checks/checks.json`.

| Check | Result |
|---|---|
| Disk circular at 22 deg and 60 deg | aspect **1.004 / 1.000** |
| Moon below the horizon | pixel delta **0.0** |
| Save/reopen | pixel delta **0.0** |

Phase 2: `preset_dev/moon_phase2_check.py` -> `phases/check/check.json`.

| Check | Result |
|---|---|
| Lit area 0/0.25/0.5/0.75/1 | **0.0 / 0.256 / 0.505 / 0.751 / 1.0** |
| Waxing / waning side | centroid **0.622 / 0.376** |
| Sun Linked, Sun 90 deg away | fraction **0.435**, lit toward the Sun |
| Animation frames 1/8/16/24 | **0.0 / 0.227 / 0.723 / 1.0** |
| Alpha edge (soft 0.6 deg) | disk 0.736, sky 0.276, min **0.271**, no undershoot |
| Persistence | phase/waxing kept, pixel delta **0.0** |
| World / Moon nodes | **798 / 173** |
| Build time | **2.78 s** (2.63.0 baseline 2.71-3.07 s) |

Existing gates: `verify_all` **ALD ALL PASS**, Phase 3 UI **68/68 PASS**.

## Migration from 2.63.0

World group `ald_build 38`, Moon group `ald_moon_version 3`; bump both together
on the next schema change. A real 2.63.0 file (`preset_dev/moon_legacy_file.py`)
opens with build 35 and no Moon; after explicit Apply it becomes build 38 /
Moon version 3, render delta **0.0**, and the Moon renders. Evidence:
`migration/migration.json`, `migration/legacy_before.png`,
`migration/legacy_moon.png`. Migration only on Apply, never on open.

## Known limits

- Sun Linked is a direction-based artistic link, not date/place astronomy.
- The optional Moon light for object illumination is **not implemented**; the
  disk is World-only and existing lights are untouched.
- Earthshine at 0.05 is intentionally faint; the surface is only just readable
  on the dark side. 0.12 is available if a stronger earthshine is wanted.
- Craters remain stylised, not photographic.
- `Moonlit Night` still uses its stylised Sun disk.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\moon_phase2b.py -- --out preset_dev\moon\phases\2b
python preset_dev\moon_phase2b_board.py

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\moon_phase2_check.py
```

Phase 1 and 2A commands are unchanged (`moon_styles.py`, `moon_phases.py`,
`moon_phase1_check.py`).

## Gate status

**Gate 1: APPROVED.** **Phase 2A: APPROVED.**
**Phase 2B: READY - awaiting the final reduced-board review.** Phase 3
(Sun System 2.0) starts only after Gate 2 is closed.
