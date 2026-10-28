# Phase 2D - morphological diagnosis A / P / R / PR

Status: **DIAGNOSIS COMPLETE / VISUAL REVIEW PENDING**

No variant is merged. `master` remains A (`f1e5f97`). The diagnostic code and
evidence live only on branch `phase-2d-diagnosis`.

## Variants

| Variant | Projection / Flatness | Density |
|---|---|---|
| **A** | current `family_flatness` (Cumulus has no planar blend) | current `macro + gated lobes` |
| **P** | v1.0.3 `Cloud Flatness` blend for Cumulus only: `flat_z = 1.25 + 3 * flatness`, planar weight = flatness, spherical weight = 1 - flatness | current |
| **R** | current | v1.0.3 sum `0.66 * macro + 0.22 * billow + 0.12 * puff`, no macro-envelope attenuation, Cumulus only |
| **PR** | P | R |

The one-hot `Cloud Cumulus` gate keeps Stratocumulus and Cirrus on the current
path. The lighting model is untouched; P necessarily changes the coordinates
sampled by the existing envelope/lighting, so the visible shading follows the
new projection. Compositor is off.

## Main comparison, calibrated coverage (seed 17)

| | v1.0.3 | A 0.78 | P 0.86 | R 0.66 | PR 0.78 |
|---|---|---|---|---|---|
| Coverage | 0.4195 | 0.4262 | 0.4118 | 0.4154 | 0.4356 |
| Components >0.2% | 6 | 3 | **4** | 3 | 3 |
| Largest component | 0.3451 | 0.4031 | **0.3727** | 0.3906 | 0.4071 |
| Perimeter / sqrt(area) | 14.392 | 10.432 | **11.556** | 10.763 | 11.510 |
| Perimeter / sqrt(W*H) | 9.321 | 6.810 | 7.416 | 6.937 | 7.597 |
| Vertical span | 0.644 | 0.697 | 0.678 | 0.696 | 0.685 |
| Vertical centroid | 0.320 | 0.327 | 0.339 | 0.318 | 0.337 |
| Image gradient mean (not perimeter) | 0.00302 | 0.00231 | 0.00277 | 0.00231 | 0.00284 |

P is the only variant that raises component count and perimeter and lowers the
dominant mass at comparable coverage. R barely changes the 3-component/0.39
bank; PR brings the largest share back to ~0.41.

## Native Cloud Amount curve (0.60 / 0.70 / 0.78)

| Variant | 0.60 | 0.70 | 0.78 |
|---|---|---|---|
| A | 0.279 / 5 / 0.183 | 0.364 / 4 / 0.321 | 0.426 / 3 / 0.403 |
| P | 0.199 / 8 / 0.108 | 0.286 / 5 / 0.237 | 0.354 / 4 / 0.329 |
| R | 0.365 / 5 / 0.321 | 0.451 / 3 / 0.423 | 0.529 / 2 / 0.521 |
| PR | 0.293 / 4 / 0.270 | 0.371 / 4 / 0.349 | 0.436 / 3 / 0.407 |

`coverage / components / largest`. P shifts the curve **down** (needs
calibration around 0.86 for 0.42 coverage); R shifts it **up** and merges.

## Spaced seeds (0, 7, 14, 21, 28, 35, 42, 49, 56, 63)

| | A at 0.78 | P at 0.86 |
|---|---|---|
| Coverage mean [min..max] | 0.323 [0.194..0.452] | 0.296 [0.212..0.412] |
| Coverage std | 0.089 | 0.072 |
| Largest mean / max | 0.278 / **0.453** | **0.236 / 0.401** |
| Components mean [min..max] | 2.9 [1..6] | **3.6 [1..6]** |
| Perimeter mean | 13.43 | 13.25 |

P reduces the worst dominant mass and increases the component count, but it
also lowers mean coverage and does not raise mean perimeter. The spaced-seed
sheet shows P is more fragmented on several seeds but too sparse on others
(seed 49 is one component). P is promising, not finished.

## Alternate view (seed 17, calibrated amounts)

| | Coverage | Components | Largest | Perimeter |
|---|---|---|---|---|
| A | 0.124 | 3 | 0.087 | 12.232 |
| P | 0.202 | 3 | 0.170 | 13.056 |
| R | 0.127 | 3 | 0.091 | 12.222 |
| PR | 0.229 | 5 | 0.180 | 12.478 |

P has more cloud and a larger mass in this view; PR is more fragmented here,
but that does not carry over to the main view. This is another reason to treat
P as a component, not a finished candidate.

## Diagnosis

1. **Projection / Cloud Flatness (P) is the component that controls
   articulation.** Restoring the v1.0.3 blend for Cumulus changes the sampling
   from a pure spherical ray to a spherical + planar-shell blend, with a
   Z scale of 2.0 instead of 1.25. At matched coverage it produces a fourth
   component, a smaller dominant mass and a higher mask perimeter. This is the
   difference most directly responsible for the v1.0.3 silhouette.
2. **The v1.0.3 density sum (R) is not the cause.** Removing the macro-envelope
   attenuation and using `0.66 macro + 0.22 billow + 0.12 puff` increases
   coverage and merges the bank; at matched coverage it is essentially A. The
   current gating is not what made the cloud a single bank at 0.42 coverage.
3. **PR is not additive.** P's extra articulation is lost once R's denser
   field is added; the main result returns to ~3 components and largest 0.407.
   Recover P, not R.

The remaining gap to v1.0.3 is real: P at matched coverage has 4 components vs
6, perimeter 11.56 vs 14.39, and its coverage curve is shifted down. P needs a
Cumulus-only coverage compensation and a broader seed gate before it can be
considered for a candidate; the current 10 spaced seeds already show
coverage 0.212–0.412.

## Recommendation

**Recover P (projection / Cloud Flatness), keep A's density/gating for now.**
Do not recover R. Pair P with a small Cumulus-only coverage calibration,
then repeat the 20+ spaced-seed and alternate-view gate. No merge until that
candidate is visually approved.

## Performance

| Variant | Apply | Render | Group nodes |
|---|---|---|---|
| A | 1.06 ms | 2360 ms | 540 |
| P | 1.30 ms | 2288 ms | 541 |
| R | 1.03 ms | 2285 ms | 548 |
| PR | 1.11 ms | 2354 ms | 549 |

No meaningful cost; P adds one MapRange node.

## Evidence

- `contact_variants.png` - v1.0.3 / A / P / R / PR at calibrated coverage.
- `contact_coverage.png` - native 0.60 / 0.70 / 0.78 curves.
- `contact_spaced.png` - A/P on 10 spaced seeds.
- `contact_spaced_alt.png` - A/P alternate view at seeds 0/28/56.
- `contact_alt.png` - A/P/R/PR alternate view at seed 17.
- `metrics.json` - all measurements and summaries.
- `mask_*.png` - main masks.

The diagnostic code is `phase2d_render.py` + the `CLOUD_DIAG` switch in
`palette.py` on this branch. It is not production code and is not merged.

## Decision

**Diagnosis: recover P; do not recover R.** P is not a finished candidate:
coverage compensation and a wider seed gate are required. No merge, no
release. Visual review is pending.
