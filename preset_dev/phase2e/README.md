# Phase 2E - recovered Cumulus projection

Status: **CANDIDATE STOPPED / VISUAL REVIEW PENDING**

P is not merged. `master` remains A (`f1e5f97`). The projection change and its
evidence exist only on branch `phase-2e-projection`. No release and no further
variant were started.

## What changed

Only the Cumulus projection/Cloud Flatness path, plus one global Cumulus-only
coverage compensation:

- `p_flatness = mix(family_flatness, Cloud Flatness, Cloud Cumulus)`.
- `flat_z = 1.25 + 3 * p_flatness`; planar weight = `p_flatness`; spherical
  weight = `1 - p_flatness`.
- Coverage threshold bias `-0.015`, one-hot Cumulus, to compensate the lower P
  coverage.
- Density, macro-envelope, lobes, lighting, sky, Sun, palettes, UI, presets,
  shooting stars and compositor are untouched.
- No `CLOUD_DIAG` and no diagnostic switch in production code.

Group nodes: A 540, P 543. Warm render median: A 1137 ms, P 1152 ms. No
performance regression.

## Cloud Amount calibration (seed 17)

| Amount | A coverage | P coverage |
|---|---|---|
| 0.20 | 0.052 | 0.058 |
| 0.40 | 0.130 | 0.135 |
| 0.60 | 0.279 | 0.272 |
| 0.70 | 0.364 | 0.356 |
| 0.78 | 0.426 | 0.414 |
| 0.90 | 0.526 | 0.488 |
| 1.00 | 0.585 | 0.551 |

Cloud Amount 0 is identical to the clouds-off image. The curve is progressive
with no flat stretch. The standard 0.78 is within 0.012 of A. The high end is
compressed by 0.034-0.038; a single global bias cannot match the nonlinear top
without overfilling the low/mid range.

## 20 seeds x 3 camera views

Seeds: 0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84, 91, 98, 105, 112,
119, 126, 133. Views: main, left, right. Seed is a translation of the same
procedural field; these are correlated samples, not independent realizations.

### Same control (0.78)

| | A | P |
|---|---|---|
| Coverage mean [min..max] | 0.234 [0.014..0.468] | 0.280 [0.090..0.449] |
| Coverage std | 0.125 | 0.100 |
| Largest mean / max | 0.180 / **0.469** | 0.224 / **0.440** |
| Components mean [min..max] | 3.35 [1..7] | 3.90 [1..8] |
| Perimeter mean | 12.68 | **14.75** |

P improves the average perimeter and worst largest share, but both fields
collapse to nearly empty skies at some translations (A min 0.014, P min 0.090).
The coverage is not stable across the seed range.

### Per-case matched diagnostic (target 0.42, up to three adjustments)

| | A | P |
|---|---|---|
| Coverage mean [min..max] | 0.334 [0.072..0.434] | 0.358 [0.175..0.435] |
| Largest max | 0.433 | 0.434 |
| Components mean | 2.55 | **3.13** |
| Perimeter mean | 11.19 | **12.72** |

The per-case matching is diagnostic only and does not affect normal add-on
behavior. It could not reach 0.42 on many left-view/low-density seeds even at
amount 1.0. The matched table therefore shows the achieved coverage on every
cell instead of pretending the pairs are equivalent.

## Representative cells (matched diagnostic)

`coverage / components / largest`

| Cell | A | P |
|---|---|---|
| main seed 00 | 0.416 / 2 / 0.400 | 0.433 / 5 / 0.287 |
| main seed 49 | 0.406 / 1 / 0.408 | 0.297 / 2 / 0.295 |
| main seed 84 | 0.425 / 1 / 0.424 | 0.407 / 2 / 0.354 |
| worst main seed 98 | 0.433 / 1 / 0.433 | 0.435 / 1 / 0.434 |
| left seed 49 | 0.156 / 4 / 0.103 | 0.183 / 5 / 0.106 |

At seed 17 main the seed-17 curve gives P 0.414 / 4 / 0.374 / perimeter 11.56
versus A 0.426 / 3 / 0.403 / 10.43. The improvement is real there, but it is
not consistent across the seed/view matrix: seed 98 main is one bank for both,
and left seed 49 is far below the coverage target for both.

## Diagnosis and limits

1. **P is the projection component that carries articulation at seed 17.** It
   produces a fourth component, a smaller dominant mass and a longer mask
   perimeter at comparable coverage. This confirms the Phase 2D diagnosis.
2. **The seed translation dominates the 20-seed matrix.** The same procedural
   field is shifted into low-density regions; A drops to 0.014 coverage and P
   to 0.090. A global Cloud Amount bias cannot repair that per seed, and a
   per-case amount search cannot always reach 0.42 because the maximum coverage
   at amount 1.0 is still below target.
3. **The morphology improvement is not consistent across the matrix.** P is
   better on several main-view cells but the worst cases collapse to one bank
   for both. The visual table includes the worst case and the poor left view,
   not only the seed-17 success.
4. **Stop criterion met:** one global calibration preserves a useful curve at
   the standard seed but does not yield robust coverage and a convincing
   morphology improvement across 20 correlated seeds and three views. The
   candidate is stopped rather than tuned further.

## Recommendation

Do not recover P as a product candidate yet. The projection is the right
**component** to investigate, but the seed/coverage sampling must be made
stationary first; otherwise a projection change is judged through a moving
coverage target. No further algorithm or variant was started. `master` remains
A (`f1e5f97`).

## Regressions

- Stratocumulus: A/P renders **pixel-identical** (`max_delta = 0`).
- Cirrus: A/P renders **pixel-identical** (`max_delta = 0`).
- Cloud Amount 0: P is **pixel-identical** to the clouds-off image.
- UI, presets, shooting stars and compositor were not modified.
- Warm render cost: A 1137 ms, P 1152 ms; +1.2%. Nodes 540 -> 543.

## Evidence

- `contact_main.png` - v1.0.3 / A / P at seed 17, with masks.
- `contact_table.png` - A/P matched at three seeds, worst case and left view.
- `contact_masks.png` - masks for the table cells.
- `contact_20seeds.png` - native 0.78, A and P across 20 seeds (main view).
- `contact_curve.png` - Cloud Amount curve, A vs P.
- `metrics.json` - all curve/native/matched records and summaries.
- `regression.json` - family/zero/timing checks.

## Decision

**CANDIDATE STOPPED / VISUAL REVIEW PENDING.** No merge and no release. P is not
a robust improvement yet; the next useful step would be to address seed/coverage
stationarity before another morphology candidate, and that requires a new
explicit authorization.
