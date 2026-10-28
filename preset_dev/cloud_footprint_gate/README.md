# Cloud Footprint — final visual gate

Status: **STOPPED — USER VISUAL REVIEW**

Base: `experiment/cloud-footprint` at `5409527`. Work exists only on
`experiment/cloud-footprint-gate`; `master` remains `f1e5f97`. Candidate F is
unchanged. No merge, no release, no add-on change, no new distribution
solution, no further tuning of radii, count, soft relaxation or Cloud Amount.

## Inspection

F at Cloud Amount 0.42, 1920x1080, SUMMER_NOON, no compositor, AgX.
Camera elevations 0/30/60/85 degrees, azimuths 0/90, seeds 3/17/42.
Global coverage: seed 3 **0.4219** (136 masses), seed 17 **0.4237** (139),
seed 42 **0.4206** (124). Masks and per-frame coverages included.

| Elevation | Mean frame coverage | Min | Max |
|---|---|---|---|
| 0 deg | 0.159 | 0.124 | 0.205 |
| 30 deg | 0.414 | 0.350 | 0.514 |
| 60 deg | **0.500** | 0.466 | 0.547 |
| 85 deg | **0.484** | 0.425 | 0.523 |

The 0 deg frame includes the ground (about half the image); its sky-only
coverage is about 0.32. The global 0.42 is met, but the distribution is not
uniform with elevation: the horizon is under-covered and the upper sky is
systematically over-covered at 0.48-0.55.

## Visible problems

1. **Extended artificial banks.** At 60 and 85 degrees the sky is dominated by
   large connected masses with long arms, bays and straight or diagonal runs.
   The seed-17 zenith is a single "map-island" silhouette; the seed-42 60-degree
   cells are long banks. This is the explicit failure condition of the brief.
2. **Systematic elevation gradient.** The area-uniform placement does not
   prevent the fixed silhouettes near the pole from overlapping: the 60/85
   frames are 0.48-0.55 covered while the horizon is ~0.16-0.20 (0.32 sky-only).
3. **Tower repetition.** Every mass repeats the same stepped tower and cap
   structure. It is visible in the isolated horizon clouds; in the merged banks
   it becomes a row of repeated bumps.
4. **Unnatural silhouettes at the zenith.** The flat, hard SDF unions read as
   maps or islands rather than cumulus. The v1.0.3 detail shows articulated,
   soft-edged clouds at a comparable native crop; the problem is the
   silhouette, not the flat colour (no shading was added, as required).
5. **The fixed-contour mechanism itself works**: the per-mass silhouettes are
   constant across the amounts and the activation adds whole masses. The
   failure is in the distribution/footprint geometry near the pole, not in the
   activation logic.

## Decision

**Candidate F is stopped.** It presents both extended artificial banks and a
visibly repetitive mass structure; the brief's stop condition is met. No
compensation was developed, no radii/count/soft/Cloud Amount iteration was
started, and the distribution is not reusable as the production system in its
current form. The fixed-silhouette + whole-mass activation concept remains a
documented experiment; it is not integrated.

The earlier A/B/F comparison and the anatomy/overlap evidence remain valid as
research records.

## Files

- `contact_gate_az000.png` / `contact_gate_az090.png` - 4 elevations x 3 seeds
  each, 640x360 cells, F at 0.42.
- `contact_gate_masks.png` - the binary masks, 8 camera cells x 3 seeds.
- `contact_gate_detail.png` - native 1:1 crops: the 85/60/30-degree banks, two
  v1.0.3 crops, one isolated F tower.
- `metrics.json` - per-cell and per-elevation coverages, global values.
- `preset_dev/cloud_footprint_gate.py`,
  `preset_dev/cloud_footprint_gate_compare.py`.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_footprint_gate.py -- `
  --out <gate> --count 184 --soft 0.9
python preset_dev\cloud_footprint_gate_compare.py -- `
  --gate <gate> --out preset_dev\cloud_footprint_gate
```

## Next action

None. This is the mandatory user visual review; the candidate is stopped and
no further distribution work is authorised.
