# Phase 1 - Cumulus baseline (v1.0.3 vs v2.62.0)

Status: **TECHNICAL PASS / VISUAL REVIEW PENDING**

No cloud or World shader was modified. This is the comparison that must be
accepted before Phase 2 starts.

## Conditions

- Blender 5.1.2, EEVEE, 32 samples, AgX, exposure 0, frame 1, 24 fps.
- Camera location `(0, -12, 3)`, rotation `(1.75, 0, 0.45)`, lens 32 mm.
- Palette `SUMMER_NOON`, same Sun rotation, compositor off, no FX or Spatial
  Clouds.
- 1280x720 and 1920x1080; the only variable is the World cloud generator.
- Cloud masks come from a clouds-off reference rendered by the same add-on at
  the same camera, palette and Sun, not from a heuristic sky threshold.

Both native presets request `cloud_amount = 0.70`. The generators interpret
that number differently, so a second current render was calibrated to the
apparent coverage of v1.0.3. The calibration changes only the current
`cloud_amount`; it does not claim that the internal parameters are equivalent.

## Calibration

Cloud coverage is the fraction of pixels that differ from the clouds-off
reference by more than 0.02 (max RGB delta), with a 3x3 close/open cleanup.

| Current amount | Coverage (1280) |
|---|---|
| 0.60 | 0.279 |
| 0.70 native | 0.364 |
| 0.78 chosen | 0.426 |
| 0.80 | 0.443 |
| 0.90 | 0.525 |
| v1.0.3 native | 0.419 |

`0.78` is the closest current setting at 1280 and 1920; it is the calibrated
row. The native row remains in the comparison because it is the current
preset's actual behaviour.

## Metrics

1280x720:

| Metric | v1.0.3 | v2.62 native | v2.62 cal 0.78 |
|---|---|---|---|
| Cloud coverage | 0.420 | 0.364 | 0.426 |
| Cloud components > 0.2% | 6 | 4 | 3 |
| Largest component (share of frame) | 0.345 | 0.321 | 0.403 |
| Edge density | 0.00302 | 0.00236 | 0.00231 |
| Cloud luma p50 | 0.757 | 0.724 | 0.724 |
| Cloud luma p90 | 0.760 | 0.760 | 0.760 |
| Cloud luma std | 0.0605 | 0.0616 | 0.0623 |
| Rim / interior luma | 0.864 | 0.883 | 0.878 |
| Sky luma | 0.635 | 0.628 | 0.636 |

1920x1080 shows the same ordering: coverage 0.419 / 0.364 / 0.426,
components 6 / 4 / 3, largest 0.344 / 0.320 / 0.403, edge density
0.00239 / 0.00195 / 0.00192.

## Findings

### Silhouette

- v1.0.3 reads as **several separate cumulus masses**: a large central group,
  a lower-left group, a top-right group and small secondary pieces. The
  largest component covers 34.5% of the frame; six components exceed 0.2%.
- v2.62 at matched coverage reads as **one dominant bank**: the largest
  component covers 40.3%; only three components are significant. The extra
  coverage mostly enlarges the same bank instead of creating new masses.
- v2.62's border is smoother: edge density is about 20-23% lower at both
  resolutions. The top is a long ridge with a few bumps; v1.0.3 has more
  rounded, differently sized domes and secondary lobes.
- v1.0.3's bases are flat per mass and broken by sky openings. v2.62 has a
  clean flat base, but it is one continuous base under a single bank. That
  clean base is a quality to keep; the lack of subdivision is the problem.

### Lighting

- The tonal spread is **not lower** in v2.62: cloud luma std is 0.0616
  (native) / 0.0623 (calibrated) versus 0.0605 in v1.0.3. The older baseline
  note that v2.62 has lower internal contrast is not supported by the pixels.
- The difference is where the tones sit. v1.0.3 has a broad bright plateau
  (p50 0.757, p90 0.760). v2.62 has the same brightest value but a lower
  median (p50 0.724), because a large continuous mid/shadow area occupies the
  underside of the single bank.
- v1.0.3's shadows sit under individual lobes, so the light/shadow separation
  follows the form. v2.62's shadow is a broad slab under one mass; it reads as
  a gray-blue underside rather than a set of shaded lobes.
- The rim/interior ratio is similar (0.864 vs 0.878); the current rim is not
  weaker, it is broader and softer. The silhouette, not the rim strength, is
  the issue.
- The Sun direction is coherent in both. No lighting-direction defect was
  found; the defect is the spatial distribution of the shadow.

### Composition

- Native v2.62 has visibly more clear sky (0.364 vs 0.419 coverage); the
  calibrated 0.78 restores the sky/cloud ratio but not the distribution.
- v1.0.3 spreads masses across the frame and leaves several readable
  openings. v2.62 concentrates the mass in the upper half and leaves a large
  clear lower area; the calibrated version enlarges the upper bank.
- No obvious repeated motif was found in either version. The current field's
  problem is dominance, not tiling.

## What to recover and what to keep

**Recover from v1.0.3**

- Multiple macro masses and secondary lobes instead of one connected bank.
- Rounded, articulated tops and a more varied silhouette; higher edge detail.
- Openings that separate masses, not just a larger empty area at the frame
  edge.
- Lobe-scale shadows under the illuminated tops; keep the bright top plateau.
- More even mass distribution and stronger variation between primary and
  secondary clouds.

**Keep from v2.62.0**

- The four-zone sky, palette wiring, Sun and the exact sky luma (0.635 vs
  0.636 at the calibrated coverage).
- The clean flat cloud base, but subdivide it into several bases.
- The cool shadow hue, if Phase 3 keeps it; the current issue is the shadow
  area, not its colour family.
- Deterministic seed/wind, scene ownership, optional compositor and the
  current performance baseline.

## Probable causes of the loss

1. **Macro threshold / distribution.** At `cloud_amount 0.70`, seed 17 and
   scale 3.2, the current macro field crosses its threshold as one connected
   bank. v1.0.3's field has more high-frequency modulation, so it breaks into
   separate masses. Raising the amount to 0.78 only enlarges the bank; it does
   not restore fragmentation.
2. **Silhouette detail.** The current border/erosion detail is too soft or too
   low-frequency to articulate the top into domes. The 20-23% lower edge
   density is the measurable symptom.
3. **Shading over a single mass.** The current solar/height shading is applied
   over a large connected density region, producing one broad mid/shadow slab.
   v1.0.3's shading follows smaller lobes, so its shadows are local. The tone
   range is adequate; the spatial mapping from density to shadow is not.
4. **Scale and seed.** A wide, low-frequency mass at this camera/seed makes
   the bank dominate the frame. This is a contributor, not the only cause;
   changing the seed alone would move the bank, not fragment it.

## Evidence

- `contact.png` - primary 1280 plate: v1.0.3 native, v2.62 native, v2.62
  calibrated; second row is the corresponding cloud mask.
- `contact_1920x1080.png` - same plate at 1920.
- `contact_lighting.png` - 1:1 crop of the main mass for the underside and
  rim.
- `mask_*.png` - white cloud / black sky masks.
- `metrics.json` - coverage, components, luma, edge and rim metrics for both
  resolutions.
- `../baseline_2_63/` - raw on/off renders, coverage sweep and metadata.
- `../phase1/summer_noon_v2.62_calibrated_on_amount_078_1920x1080.png` - the
  1920 calibrated source used by the sheet.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
# current native, off reference and coverage sweep
& $blender -b --factory-startup --python preset_dev\phase1_render.py -- `
  --out preset_dev\baseline_2_63 --tag v2.62.0 --res 1280x720 --clouds on --amount 0.70
& $blender -b --factory-startup --python preset_dev\phase1_render.py -- `
  --out preset_dev\baseline_2_63 --tag v2.62.0 --res 1280x720 --clouds off
# v1.0.3 off reference (temporary package built from tag v1.0.3)
& $blender -b --factory-startup --python preset_dev\phase1_render.py -- `
  --out preset_dev\baseline_2_63 --tag v1.0.3 --res 1280x720 --clouds off `
  --module v103 --module-path <temp-parent>
python preset_dev\phase1_compare.py
```

## Decision

The comparison is technically complete. The visual decision is **pending**:
Phase 2 must not start until the user accepts this baseline and the recovered
target. No `APPROVED` or `ARTISTIC GATE PASSED` status is claimed.
