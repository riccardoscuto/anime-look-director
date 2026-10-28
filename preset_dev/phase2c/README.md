# Phase 2C - hierarchical Cumulus, candidate C

Status: **REJECTED (Cloud Amount regression and bank-like silhouette) /
VISUAL REVIEW PENDING**

Candidate C is preserved on branch `phase-2c-candidate-c` for reference. It is
not merged into `master`; production remains A (v2.62.0 density, 0.78
calibration). No Phase 2B, Phase 3 or release was started.

## What C changes

Only the Cumulus coverage density in `palette.py`:

- A **low-frequency region gate** (`region_noise`, scale 0.95 x Cloud Scale)
  creates broad openings between groups.
- A **higher-frequency cell field** (`cell_noise`, scale 1.55 x Cloud Scale)
  creates several masses inside the open regions.
- The existing billow/puff lobes are applied inside the cell envelope.
- The C density is mixed with A by the one-hot `Cloud Cumulus` signal, so
  Stratocumulus and Cirrus stay on the A path.
- A small one-hot threshold calibration (`-0.070`) aligns the mean coverage.
- No lighting, sky, Sun, palette, UI or property change. The envelope used by
  the current lighting path is still A.

The C path adds 17 World-group nodes (540 -> 557).

## Main comparison (seed 17, 0.78)

| Metric | v1.0.3 | A | C |
|---|---|---|---|
| Coverage | 0.4195 | 0.4262 | 0.4315 |
| Components >0.2% | 6 | 3 | 3 |
| Largest component | 0.3451 | 0.4031 | 0.3482 |
| Perimeter / sqrt(area) | 14.392 | 10.432 | 11.078 |
| Vertical span | 0.644 | 0.697 | 0.697 |

At seed 17 C is closer to v1.0.3 in largest share (0.348 vs 0.403) and
perimeter (11.08 vs 10.43), with a visible central opening.

## 20-seed gate

All seeds 0..19 at 0.78, same camera, palette, Sun and samples.

| Metric | A | C |
|---|---|---|
| Coverage mean | 0.3852 | **0.4047** |
| Coverage min / max | 0.292 / 0.439 | **0.366 / 0.432** |
| Coverage std | 0.0384 | **0.0242** |
| Largest mean | **0.3491** | 0.3591 |
| Largest max | 0.4392 | **0.3754** |
| Components mean | 2.2 | **2.6** |
| Components min / max | 1 / 3 | **2 / 3** |
| Perimeter mean | 10.401 | **11.069** |
| Perimeter min | 9.265 | **9.769** |

Worst cases:

- A worst largest: seed 19, coverage 0.439, **1 component, largest 0.439**.
- A worst coverage: seed 00, coverage 0.292.
- C worst largest: seed 08, coverage 0.406, 2 components, largest 0.375.
- C worst coverage: seed 02, coverage 0.366.

C is more stable and its worst cases are better than A. **But the morphology
is still a broad bank**: every C seed reads as one large mass with a central
or lateral opening, not the several cumulus masses of v1.0.3. The 20-seed
sheet shows this clearly; the numbers do not replace the visual decision.

## Fatal regression: Cloud Amount

| Amount | A coverage | C coverage |
|---|---|---|
| 0.60 | 0.279 | **0.416** |
| 0.70 | 0.364 | **0.424** |
| 0.78 | 0.426 | **0.424** |

C is already at 0.416 at the low setting and is almost flat from 0.60 to 0.78.
The Cloud Amount control no longer provides a predictable coverage
progression. This is a hard rejection criterion, independent of the visual
result.

## Alternate view

| Candidate | Coverage | Components | Largest | Perimeter |
|---|---|---|---|---|
| A | 0.124 | 3 | 0.087 | 12.232 |
| C | 0.296 | **1** | 0.297 | 9.420 |

C covers more of the alternate view but collapses to one component; A is
sparser but more distributed there.

## Regression and performance

- Stratocumulus: A and C renders **pixel-identical** (`max_delta = 0`).
- Cirrus: A and C renders **pixel-identical** (`max_delta = 0`).
- Warm render median: A 1108 ms, C 1330 ms (+20%).
- Cold first frame (standalone): A 2335 ms, C 4984 ms (+2.6 s shader setup).
- Group nodes: 540 -> 557.

## Evidence

- `contact_main.png` - v1.0.3 / A / C seed 17 and masks.
- `contact_20seeds.png` - A and C, seeds 00..19.
- `contact_20seeds_A.png`, `contact_20seeds_C.png` - per-candidate grids.
- `contact_worst.png` - four worst C seeds against A at the same seeds.
- `contact_coverage.png` - low/medium/high at seed 17.
- `contact_alt.png` - alternate view.
- `metrics.json` - per-seed metrics, summaries, timing, regression.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\phase2c_render.py -- `
  --out preset_dev\phase2c\raw\C --candidate C --amount 0.78 --count 20
# A uses the temporary A package at f1e5f97:
& $blender -b --factory-startup --python preset_dev\phase2c_render.py -- `
  --out preset_dev\phase2c\raw\A --candidate A --module ald_a `
  --module-path <temp-parent> --amount 0.78 --count 20
python preset_dev\phase2c_compare.py
```

## Decision

**Candidate C: REJECTED.** The 20-seed gate shows better worst-case stability
than A, but the Cloud Amount curve is flat and the silhouette remains a bank.
C is not proposed for merge. `master` remains A (`f1e5f97`). Phase 2B, Phase 3
and any further candidate require a new explicit decision.
