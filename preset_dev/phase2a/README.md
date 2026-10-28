# Phase 2A - Cumulus morphology, candidate B

Status: **REJECTED (seed-dependent morphology) / VISUAL REVIEW PENDING**

Candidate B is preserved on branch `phase-2a-candidate-b` for reference. It is
not merged into `master`; production remains candidate A (v2.62.0 density with
the 0.78 coverage calibration). No Phase 2B, Phase 3 or lighting change was
started.

## What B changes

Only the Cumulus density path in `palette.py`:

- `macro_gain`: one-hot `Cloud Cumulus` remaps the macro noise scale from
  0.55 (A) to 0.72 (B). At `Cloud Cumulus = 0` it is exactly 0.55.
- `macro_weight_gain`: one-hot `Cloud Cumulus` remaps the macro weight from
  0.62 to 0.64. At `Cloud Cumulus = 0` it is exactly 0.62.
- `coverage_bias`: one-hot `Cloud Cumulus` lowers the coverage threshold by
  0.033 so the Cloud Amount -> coverage curve stays close to A.

No lighting, sky, Sun, palette, UI, property or other family change. The
extra nodes are +6 in the World group (540 -> 546).

The earlier v1-weight-only experiment was discarded: it increased the bank
instead of splitting it. The splitter experiment was also discarded: a
subtract of 0.08 collapsed coverage to 0.15. The delivered B is the
high-macro-frequency + coverage-bias version.

## Main comparison

All images 1280x720, EEVEE 32 samples, AgX, exposure 0, `SUMMER_NOON`, same
camera and Sun, compositor off. Masks are the difference from a clouds-off
reference at the same camera and version.

| Metric | v1.0.3 | A (0.78) | B (0.78) |
|---|---|---|---|
| Coverage | 0.4195 | 0.4262 | 0.4253 |
| Significant components (>0.2%) | 6 | 3 | 4 |
| Component shares | 0.345, 0.051, 0.014, 0.005, 0.003, 0.002 | 0.403, 0.021, 0.002 | 0.330, 0.052, 0.040, 0.003 |
| Largest component | 0.345 | 0.403 | 0.330 |
| Mask perimeter / sqrt(area) | 14.392 | 10.432 | 11.644 |
| Mask perimeter / sqrt(W*H) | 9.321 | 6.810 | 7.594 |
| Vertical span | 0.644 | 0.697 | 0.697 |
| Vertical centroid | 0.320 | 0.327 | 0.304 |
| Image-gradient mean (not perimeter) | 0.00302 | 0.00231 | 0.00244 |
| Cloud luma p50 | 0.757 | 0.724 | 0.717 |
| Cloud luma std | 0.0605 | 0.0623 | 0.0649 |

At seed 17 B is **closer to v1.0.3 in component count and largest share**:
4 components and 0.330 largest versus A's 3 and 0.403. The true mask
perimeter increases by 11.6% over A, but remains 19% below v1.0.3. The visual
sheet shows a left bank, a right bank and smaller openings, not the single
continuous bank of A.

The broad gray underside remains. That is an illumination/shadow-distribution
issue, not morphology; it is deliberately untouched in Phase 2A.

## Seed robustness - the reason B is rejected

Same amount 0.78:

| Seed | A coverage / components / largest | B coverage / components / largest |
|---|---|---|
| 07 | 0.401 / 2 / 0.349 | **0.486 / 2 / 0.480** |
| 17 | 0.426 / 3 / 0.403 | 0.425 / 4 / 0.330 |
| 31 | 0.393 / 4 / 0.355 | **0.353 / 1 / 0.353** |

Matched coverage (B amount adjusted per seed):

| Seed | B amount | B coverage / components / largest |
|---|---|---|
| 07 | 0.70 | 0.426 / 3 / 0.398 |
| 17 | 0.78 | 0.425 / 4 / 0.330 |
| 31 | 0.85 | 0.394 / 1 / 0.394 |

The improvement is specific to seed 17. At seed 07 B is a larger bank than A
(its main component is 0.480 of the frame, **98.8% of B's total 0.486
coverage**); at seed 31 it collapses to one connected mass, even after
coverage recalibration. The seed-31 failure is structural, not just a
threshold shift. Calibrating coverage per seed does not recover the
fragmentation. This is a **seed-dependent result**, so B cannot be accepted as
a robust replacement for A.

## Cloud Amount progression

| Amount | A coverage | B coverage |
|---|---|---|
| 0.60 | 0.279 | 0.298 |
| 0.70 | 0.364 | 0.366 |
| 0.78 | 0.426 | 0.425 |

The coverage bias preserves the medium/high curve within 0.001; the low end is
**0.019 higher** in B, so the control is close but not perfectly invariant.
The control remains monotonic; B's seed sensitivity is the larger problem.

## Alternate view

At the alternate camera (`rotation 1.62, 0, -0.35`, amount 0.78, seed 17):

| Candidate | Coverage | Components | Largest | Perimeter norm |
|---|---|---|---|---|
| A | 0.124 | 3 | 0.087 | 12.232 |
| B | 0.179 | 5 | 0.124 | 16.688 |

B is more distributed in this view, which supports the morphology idea, but it
does not outweigh the seed failure.

## Regression

- Stratocumulus: A and B renders are **pixel-identical** (max delta 0).
- Cirrus: A and B renders are **pixel-identical** (max delta 0).
- The one-hot gains return exactly 0.55/0.62 at `Cloud Cumulus = 0`; the
  coverage bias returns 0. No other family or UI change.

## Performance

| Candidate | Apply median | Render median | First render | Group nodes |
|---|---|---|---|---|
| A | 1.07 ms | 2276 ms | 2335 ms | 540 |
| B | 1.08 ms | 2270 ms | 2316 ms | 546 |

Within measurement noise; +6 shader nodes.

## Evidence

- `contact_main.png` - v1.0.3 / A / B images and masks (1280 cells).
- `contact_coverage.png` - A/B low, medium, high.
- `contact_seeds.png` - A/B at seeds 07/17/31, amount 0.78.
- `contact_alt.png` - A/B alternate view.
- `metrics.json` - all measurements, timing, regression.
- `raw/` - source renders and metadata.
- `regression/` - Stratocumulus/Cirrus A/B renders.

The old Phase 1 `edge_density` key is corrected to `image_gradient_mean` in
commit `f1e5f97`; it is a tonal gradient and is not used as cloud perimeter.
Phase 2A adds true mask perimeter and normalized perimeter.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
# A: temporary package built from b688ae5; B: this branch
& $blender -b --factory-startup --python preset_dev\phase2a_render.py -- `
  --out preset_dev\phase2a\raw --candidate A --module ald_a --module-path <temp-parent> `
  --amount 0.78 --seed 17 --view main
# B:
& $blender -b --factory-startup --python preset_dev\phase2a_render.py -- `
  --out preset_dev\phase2a\raw --candidate B --amount 0.78 --seed 17 --view main
python preset_dev\phase2a_compare.py
```

## Future C gate (not authorized)

Candidate C should target a **hierarchical/multiscale mass distribution**, not
just a wider noise amplitude. Before any merge, the acceptance test is at least
**20 seeds** at the calibrated coverage, comparing:

- coverage;
- number and size distribution of components;
- largest component share;
- true mask perimeter / sqrt(area);
- worst-case seeds, not only the median.

A candidate that only improves one seed, or that loses the Cloud Amount curve,
is rejected regardless of its best image. C and the later phases are **not
authorized** at this point.

## Decision

**Candidate B: REJECTED.** The user confirmed the rejection: the seed-17
improvement does not generalize, seed 07 merges into a single mass (98.8% of
coverage), and seed 31 is structurally one component. The low-coverage Cloud
Amount value is +0.019 versus A, so the control is close but not perfectly
invariant.

B is preserved only on branch `phase-2a-candidate-b`. `master` remains on
candidate A (`f1e5f97`). Phase 2B, Phase 3 and candidate C are not started and
are not authorized.
