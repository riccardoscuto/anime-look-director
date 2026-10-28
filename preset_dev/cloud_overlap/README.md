# Cloud overlap diagnosis — morphology vs radius fit

Status: **VISUAL REVIEW PENDING**

Base: `experiment/cloud-anatomy` at `2a8c925`. Work exists only on
`experiment/cloud-overlap`; `master` remains `f1e5f97`. No merge, no release,
no new anatomy, no preset, shading, UI or coverage fix. The previous anatomy
renders remain unchanged in `preset_dev/cloud_anatomy/`.

## Question and configurations

The previous phase measured fewer connected clouds at 0.42 with the
hierarchical anatomy and a ~9% larger radius fit. This phase separates the two
causes:

| Config | Anatomy | Radii |
|---|---|---|
| A | baseline | baseline (from the A run) |
| B | hierarchical | baseline (from the A run) |
| C | baseline | hierarchical (from the D run) |
| D | hierarchical | hierarchical (from the D run) |

All four share the same seeds, centres, strengths, mass order and Cloud
Amount logic. Only the anatomy and the per-mass radii change. The radii are
copied from the final 2048 A/D runs; the masses are rasterised at 2048.

Two selection modes:

- **standard**: each config solves its own threshold for the 0.42 request
  (the normal behaviour). The active set can differ.
- **fixed**: D's 0.42 threshold is applied to all four. The same strengths
  are active, so the comparison isolates the geometry.

Metrics: active masses, overlapping pairs, solid-angle overlap area (sum of
the pairwise overlap), panorama connected components and dominant component,
global and per-frame coverage. The colour panels show each mass in a distinct
hue and the overlap pixels in white.

## Standard selection (mean of 3 seeds)

| Config | Active | Global | Frame cov | Frame comps | Largest | Largest max | Pairs | Overlap | Pano comps | Pano dom |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 92-94 | 0.420 | 0.348 | 5.83 | 0.178 | 0.321 | 42.7 | 0.0252 | 49.3 | 0.053 |
| B | 94 | 0.420 | 0.351 | **4.50** | 0.191 | **0.345** | 49.3 | 0.0239 | 43.7 | 0.061 |
| C | 80-85 | 0.416 | 0.302 | 4.83 | 0.160 | 0.256 | 44.7 | **0.0308** | 38.7 | 0.080 |
| D | 94 | 0.420 | 0.347 | **4.50** | 0.189 | 0.344 | 49.7 | 0.0247 | 39.3 | **0.096** |

The B threshold falls to 0.03-0.08: its compact silhouette only reaches 0.42
with all masses at their outer contour, i.e. at the union ceiling. C keeps
only 80-85 masses active because its larger masses already reach 0.42; its
frame coverage is lower.

## Fixed selection (D's threshold)

| Config | Coverage | Overlap | Pairs | Pano comps | Pano dominant |
|---|---|---|---|---|---|
| A | 0.4281 | 0.0268 | 43.3 | 48.0 | 0.0581 |
| B | 0.3613 | **0.0147** | 36.0 | **54.0** | **0.0438** |
| C | 0.4933 | **0.0446** | **61.3** | **32.3** | **0.1403** |
| D | 0.4200 | 0.0247 | 49.7 | 39.3 | 0.0964 |

Relative overlap (overlap / coverage): A 6.3%, **B 4.1%**, C 9.0%, D 5.9%.

## Visual diagnosis

- `contact_overlap.png` - 4 configs x 3 seeds x 2 views, colour-coded masses.
- `contact_overlap_masks.png` - the same cells as binary masks.
- `contact_overlap_panorama.png` - the four configs on the full sky.

The white patches sit on the broad flanks in A and C (body-to-body contact,
the wide loaves), and on the summits in B and D (tower/cap contact, the
hierarchical developments). C shows the most white and the largest coloured
shapes: the +9% radius fit expands the wide bodies. B shows the smallest
patches: at the same radii the hierarchical silhouette is more compact. The
standard C hides 9-14 masses, so its frames look emptier while its full
geometry (the fixed selection) has the worst overlap.

## Cause conclusion

1. **The radius rescaling is the main cause of the overlap quantity.** C, the
   baseline anatomy at the hierarchical radii, is worst at the fixed
   selection: overlap +66%, pairs +42%, panorama components -33%, dominant
   +141% against A. At the same threshold, the expanded bodies touch more.
2. **The hierarchical morphology is more compact, not more overlapping, at
   the same radii.** B halves the relative overlap (4.1% vs 6.3%), raises the
   components (54 vs 48) and lowers the dominant (0.044 vs 0.058).
3. **The connected banks at the 0.42 request are the morphology's.** The
   frame loss is A 5.83 -> B 4.50 / C 4.83 / D 4.50; the largest frame mass is
   B 0.345 / D 0.344 against A 0.321 and C 0.256. The panorama dominant is
   D 0.096 against A 0.053. B and D sit at the union ceiling, so their towers
   and edge details bridge; C's selection hides masses and avoids the big
   frame banks.
4. **D (the previous phase) combines both.** Its overlap area is like A (the
   compact silhouette offsets the expansion), but it has the largest sky
   component and the fewest frame components: the towers bridge at high
   coverage.

## Experiment 3 — the one conditional correction

The rescaling is the main cause of the overlap *quantity*, so the correction
tested is **B: the hierarchical silhouette at the original baseline radii**.

B's fixed-selection geometry is the best of the four (overlap 0.0147,
components 54, dominant 0.044). At the standard 0.42 request B keeps the
requested coverage (0.420, all 94 masses active) and a frame coverage like A
(0.351 vs 0.348), but its compact union is at the ceiling and the standard
frames still bridge (largest max 0.345 vs A 0.321, panorama dominant 0.061 vs
0.053).

The correction therefore removes the rescaling penalty but not the
high-coverage bridging. That residual needs a **footprint-aware distribution**
(spacing/selection aware of each mass's silhouette footprint); it is
documented here and deliberately not implemented. No clouds were added to
compensate coverage, and no new anatomy was introduced.

## Limits

- The diagnostic textures are 2048; the camera renders use the Standard view
  transform and flat per-mass colours, not the SUMMER_NOON look. The absolute
  frame coverage differs slightly from the look evidence (look A 0.336 vs
  diagnostic A 0.348); the four configs are internally consistent.
- The colour texture has hard edges; the anti-aliasing is not applied. Edge
  pixels can add a small overlap, equally for all configs.
- The panorama components are computed on a 4x downsampled grid; dominant
  values are approximate. The frame metrics use the 1280x720 renders.
- Overlap area is the solid-angle fraction of the sky covered by two or more
  masses at the threshold; the pairwise overlap sums the pair areas. The
  body/tower attribution is visual, not a per-pixel classifier.
- No wind, shading, transparency, UI, presets, merge or release.

## Files

- `contact_overlap.png` - colour-coded masses, 4 configs x 6 cells.
- `contact_overlap_masks.png` - the binary masks of the same cells.
- `contact_overlap_panorama.png` - the four configs x three seeds.
- `diagnostic.json` - raw per-mass overlap records (standard and fixed).
- `metrics.json` - frame metrics and the summary tables.
- Scripts: `preset_dev/cloud_overlap_diagnostic.py`,
  `preset_dev/cloud_overlap_compare.py`;
  `preset_dev/cloud_distribution_proto.py` (`--radii-from`).

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_overlap_diagnostic.py -- `
  --out <diag> --radii-base <A run> --radii-hier <D run> `
  --seeds 3,17,42 --views main,right --renders 1
python preset_dev\cloud_overlap_compare.py -- --diag <diag> --out preset_dev\cloud_overlap
```

## Decision

The diagnosis is resolved: **radius fit -> overlap quantity; hierarchical
towers -> connected banks at high coverage**. The conditional correction
(hierarchical at the original radii) is the better geometry but is at its
union ceiling at 0.42; the high-coverage case needs a footprint-aware
distribution. **Visual review pending; no integration.**
