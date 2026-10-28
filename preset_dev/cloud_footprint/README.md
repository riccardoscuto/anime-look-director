# Cloud footprint — fixed silhouettes and an occupancy-aware distribution

Status: **VISUAL REVIEW PENDING**

Base: `experiment/cloud-overlap` at `0afb5e3`. Work exists only on
`experiment/cloud-footprint`; `master` remains `f1e5f97`. No merge, no release,
no new anatomy, shading, preset, UI or 3D geometry. The previous anatomy and
overlap evidence is unchanged.

## Phase A — geometry separated from Cloud Amount

The diagnostic now has two independent properties:

- **Silhouette**: the alpha is `clip(0.5 - d/0.02)` on the signed distance, so
  the contour is fixed (d = 0) with a constant 0.02-radius anti-aliasing band.
  The shader threshold is fixed at 0.5.
- **Activation**: masses are ordered by their seed-given strength;
  Cloud Amount selects a prefix of that order. The texture of a selected mass
  is its fixed alpha; changing the amount adds masses, it never edits an
  existing contour.

The check is in the tables: the mean silhouette area of an active mass is
**constant** for B and F across 0.18/0.30/0.42 (0.00337 of the hemisphere),
while the old A system grows it from 0.00193 to 0.00477 (+147%) as the
density threshold drops. The colour panorama rows show the same masses with
the same colours and shapes from 0.18 to 0.42; only new masses appear.

Whole-mass activation still produces small coverage steps: one mass is about
0.34% of the hemisphere, so the requests land at 0.183 / 0.301 / 0.422. This
is documented, not animated.

### Feasibility check (fixed silhouettes, current 92-94 elements)

Hierarchical anatomy, baseline radii, 2048x1024:

| Seed | Masses | Mean radius | Sum of silhouette areas | Union of current layout |
|---|---|---|---|---|
| 3 | 92 | 7.45 deg | 0.3020 | 0.2993 |
| 17 | 94 | 7.38 deg | 0.3242 | 0.3100 |
| 42 | 94 | 7.38 deg | 0.3190 | 0.3099 |

The **sum before overlap is 0.302-0.324, below 0.42**: even a perfect
repositioning of the current element count cannot reach the target. The
geometric threshold is not lowered. Candidate F therefore raises the mass
budget.

## Phase B — candidate F

- Same hierarchical anatomy, same local proportions, radii **5.0-9.9 deg**
  (the baseline's final range; no global radius increase as in D).
- **181 masses** (184 Fibonacci candidates, 3 below the horizon removed).
- Centres placed with a **footprint-aware relaxation**: the footprint is
  0.65 x radius (area-equivalent angular extent), the soft factor 0.9, 40
  deterministic iterations on the sphere. The jitter remains, so the result
  is even but not gridded; some overlap is allowed.
- Availability (union of all fixed silhouettes): **0.573**; sum of the areas
  0.61. The 0.42 request is 73% of the availability.
- Activation as above; the 0.42 request selects 133 of the 181 masses.

## A/B/F comparison

Seeds 3, 17, 42; views main and right; global requests 0.18 / 0.30 / 0.42.
SUMMER_NOON, no compositor, 1280x720; diagnostic colours and binary masks.
Means over the six cells per config/amount.

| Config | Amount | Global | Active | Overlap | Pano comps | Pano dom | Frame cov | Frame comps | Frame largest | Frame max | Mean mass area |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.18 | 0.176 | 42.0 | 0.0042 | 33.0 | 0.016 | 0.091 | 3.17 | 0.053 | 0.109 | 0.00193 |
| A | 0.30 | 0.296 | 68.3 | 0.0129 | 45.7 | 0.027 | 0.228 | 5.50 | 0.106 | 0.199 | 0.00331 |
| A | 0.42 | 0.420 | 93.3 | 0.0252 | 49.3 | 0.053 | 0.336 | 6.33 | 0.139 | 0.213 | 0.00477 |
| B | 0.18 | 0.183 | 53.7 | 0.0033 | 43.0 | 0.013 | 0.114 | 4.00 | 0.051 | 0.085 | 0.00337 |
| B | 0.30 | 0.301 | 91.3 | 0.0086 | 63.3 | 0.023 | 0.242 | 6.83 | 0.085 | 0.141 | 0.00337 |
| B | 0.42 | **0.306** | 93.3 | 0.0087 | 64.3 | 0.023 | 0.247 | 6.83 | 0.085 | 0.141 | 0.00337 |
| F | 0.18 | 0.183 | 55.0 | 0.0036 | 38.7 | 0.014 | 0.101 | 3.33 | 0.042 | 0.057 | 0.00337 |
| F | 0.30 | 0.301 | 93.3 | 0.0116 | 44.7 | 0.051 | 0.192 | 5.17 | 0.078 | 0.161 | 0.00337 |
| F | 0.42 | **0.422** | 133.0 | 0.0241 | 38.0 | 0.137 | 0.264 | **7.33** | **0.099** | 0.215 | 0.00337 |

Readings:

- **B cannot honour 0.42**: it saturates at 0.306 (all 94 masses). Its 0.30
  request is exactly its ceiling; the 0.42 cell is the same image.
- **F honours 0.42** (0.422; a 0.002 activation jump) and its 0.42 frames keep
  more components and a smaller mean dominant mass than A: 7.33 vs 6.33
  components, 0.099 vs 0.139 dominant, with the worst frame at 0.215 vs A
  0.213. The F frames show individual cumulus with towers rather than
  inflated banks.
- **F's frame coverage at 0.42 is lower than A's** (0.264 vs 0.336) at the
  same global request: fixed silhouettes are not inflated by the threshold and
  the distribution is even. This is expected and not compensated per camera.
- **F's panorama dominant is larger** (0.137 vs A 0.053): at sky scale the
  fixed masses form chains outside the camera windows (the polar band). The
  frames do not show them; the caveat is recorded.
- F's overlap at 0.42 is 0.0241, close to A (0.0252) despite 133 masses vs 93;
  the footprint-aware placement keeps the overlap area bounded. B stays at
  0.0087 because it cannot reach 0.42.

## Fundamental check

- The per-mass silhouette area is constant for B and F (0.00337) across the
  three amounts; A grows it by 147%. The fixed contour is real.
- `contact_footprint_panorama.png` shows the B and F rows: the same colours
  and shapes at 0.18, 0.30 and 0.42, with only new masses appearing. A's row
  shows the same colours but visibly inflated shapes.
- `contact_footprint_masks.png` shows the same binary silhouettes for the
  masses active at multiple amounts.

## Performance

Measured in the diagnostic (2048x1024, per seed, all three amounts, including
the per-mass analysis and the composite textures):

| Config | Generation (mean) |
|---|---|
| A | 2207 ms |
| B | 3043 ms |
| F | 3673 ms |

F is +66% vs A and +21% vs B. The placement adds the relaxation; the 181
masses double the primitive count. Memory: one 32 MiB float EXR per amount for
B/F (three in the diagnostic); A reuses one density texture. The render time
is unchanged (texture sampling dominates). This is an offline bake; a
production version could pack the per-mass rank and the fixed alpha in one
RGBA texture, but that is not part of this phase.

## Stop criteria

- Coverage only by deforming silhouettes: **not violated** (constant
  per-mass area; activation only).
- Large connected banks in most frames: **not in the frames** (7.33
  components, mean dominant 0.099, worst 0.215 against A's 6.33 / 0.139 /
  0.213); the panorama-scale chains are the recorded caveat.
- Visibly too regular: the distribution is even (Fibonacci + relaxation) but
  not gridded; the masses vary. Visual review required.
- Disproportionate cost: +66% vs A for the added budget and placement; not
  judged disproportionate for an offline bake, but it is a real cost.
- Visual result: the A/B/F sheets are provided; the verdict is the user's.

## Limits

- Activation steps are whole masses (~0.34% of the sky); no animated
  transition, as allowed by the brief.
- F's frame coverage at 0.42 is lower than A's; the global coverage is 0.422.
- F's sky-scale dominant component (0.137) is larger than A's; the polar
  chains are outside the tested cameras.
- The diagnostic regenerates one composite texture per amount; no rank
  texture or shader activation is implemented.
- 181 masses: availability 0.573, above the 0.48-0.50 preference; the extra
  budget is the margin for higher amounts. No new variant was started.
- No wind, shading, UI, presets, merge or release.

## Files

- `contact_footprint_panorama.png` - A/B/F x seed x amount, diagnostic colours
  and white overlaps.
- `contact_footprint_look.png` - the SUMMER_NOON renders, both views.
- `contact_footprint_masks.png` - the binary frame masks.
- `feasibility.json` - Phase A sums/unions.
- `footprint.json` - raw A/B/F records.
- `metrics.json` - the summary and frame metrics.
- Scripts: `preset_dev/cloud_footprint.py`,
  `preset_dev/cloud_footprint_feasibility.py`,
  `preset_dev/cloud_footprint_compare.py`.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_footprint_feasibility.py -- `
  --out <feas> --radii-base <A run> --seeds 3,17,42
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_footprint.py -- `
  --out <run> --radii-base <A run> --seeds 3,17,42 `
  --views main,right --amounts 0.18,0.30,0.42 `
  --count 184 --soft 0.9 --stage full
python preset_dev\cloud_footprint_compare.py -- `
  --diag <run> --out preset_dev\cloud_footprint
```

## Decision

The Phase A limit is proven: the current 92-94 fixed silhouettes total
0.302-0.324, so repositioning alone cannot reach 0.42. Candidate F raises the
budget, keeps the fixed contours and reaches 0.422 with more frame components
and a smaller mean dominant mass than A. Its frame coverage is lower at the
same global request and its sky-scale chains need a zenith check. **Visual
review pending; no integration.**
