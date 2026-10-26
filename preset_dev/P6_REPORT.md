# P6 report — validation matrix (v2.36.0)

## What the matrix is

36 renders: 3 palettes (TWILIGHT_DUSK, NEON_NIGHT, GOLDEN_HOUR) x 4 families
(CHRYSANTHEMUM, PEONY, WILLOW, KAMURO) x 3 ages (0.25, 0.70, 1.40 s after the
burst), at 800x450, full compositor stack, fixed camera (32 mm), seed 17,
exposure 0, AgX. Every cell also renders the same frame without FX: the
difference is the FX coverage.

`preset_dev/validation/` holds the 36 PNGs, `metrics.json` and `sheet.png`
(6x6 contact sheet: two rows per palette, families across, ages within).

## Acceptance criteria

| metric | limit | why |
| --- | --- | --- |
| clipped fraction | <= 2 % | no diffuse clipping |
| mean saturation | >= 0.08 | the FX must not wash the frame grey |
| FX coverage | >= 0.2 % | a burst must be visible |
| render time | <= 6 s | usable interactive update |

These are deliberately coarse: they catch an empty, clipped or desaturated
frame, not a subjective look. The look is judged on the sheet.

## Result

**36 / 36 PASS**, mean render 1.51 s (1.43–2.65 s).

| family | coverage range |
| --- | --- |
| CHRYSANTHEMUM | 8.5 % – 32.4 % |
| PEONY | 1.3 % – 18.4 % |
| WILLOW | 7.9 % – 32.4 % |
| KAMURO | 6.0 % – 22.9 % |

Maximum luminance 0.94 (no clipping), minimum mean saturation 0.42, clipped
fraction 0.0 in every cell.

The sheet reads consistently: the Chrysanthemum and Willow fill the frame, the
Peony is a compact globe, the Kamuro is a warm, slower burst. The three palettes
stay distinct.

## What the matrix found

1. **The Peony at 1.4 s was black in the first run.** The cause was the test,
   not the product: `Scene.ald.fx_age` defaults to 0.8 s and the matrix never
   reset it, so every cell was rendered 0.8 s later than its label. The matrix
   now pins `fx_age = 0.0`; the product clock was correct.
2. **Beads and heads are sub-pixel at distance.** The trails already had an
   apparent-width floor (P2), the beads did not: a 0.05 m bead is 0.65 px at
   55 m with a 32 mm lens. The particle radii now have the same 1.2 px floor as
   the trails, which the 800x450 matrix confirms (the Peony keeps its sparkle).

## Residual risks

- The matrix renders one burst per cell, not the 3/5 shows; the composition
  phase has its own evidence (`preset_dev/composition/`).
- The thresholds are global image statistics: a local defect (one dead spoke)
  can hide behind a healthy frame. The gate covers geometry and occlusion.
- Only AgX at exposure 0 is validated; Standard was the diagnostic control of
  the P2 calibration, not a delivery target.
- The matrix takes ~2 minutes; it is a development tool, not part of the gate.

## Commit

`P6: validation matrix, metrics, contact sheet; apparent size floor for the
beads` (this change).
