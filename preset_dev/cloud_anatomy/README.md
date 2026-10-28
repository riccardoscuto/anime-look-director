# Cloud anatomy — hierarchical Cumulus silhouettes

Status: **VISUAL REVIEW PENDING**

Base: `experiment/cloud-distribution-2d` at `6cc8e86`. Work exists only on
`experiment/cloud-anatomy`; `master` remains `f1e5f97`. No merge, no release,
no change to the add-on, its palette, presets, UI, shooting stars or
compositor.

## 1. Single-mass experiment

Three morphologies, three specimens each, one isolated mass per mask. The
masks are black/white silhouettes only (no colour, shading or glow), rendered
directly from the same signed-distance field used in the World.

| Variant | What changes |
|---|---|
| `baseline` | The committed morphology: wide body, 5-7 evenly spread lobes, straight base cut. |
| `hierarchical` | Body + a dominant tower (4 stacked lobes with protruding caps), a secondary tower of lower height, flank bulges and 3 small edge lobes; soft, slightly wavy base. |
| `asymmetric` | One strongly off-centre leaning tower with a two-cap crown, a short secondary tower, a flank cluster and edge details; soft wavy base. |

All variants use the same specimen parameters (tall/width) and the same mass
size. The baseline keeps the old single-scale warp; the variants use a
three-scale warp (0.070 / 0.035 / 0.018 mass radii).

### Metrics (mean of three specimens)

| Variant | Height | Width | Area | Distinct summits | Asymmetry (1-IoU) | Base std | Perimeter norm |
|---|---|---|---|---|---|---|---|
| baseline | 1.384 | 1.971 | 2.215 | 0.0 | 0.163 | 0.0112 | 3.70 |
| **hierarchical** | **1.519** | 1.892 | 1.799 | **1.33** | 0.204 | 0.0212 | 4.02 |
| asymmetric | 1.496 | 1.765 | 1.690 | 0.67 | **0.339** | 0.0202 | 3.99 |

Height/width are in mass-radius units. "Distinct summits" counts local maxima
of the top contour with at least a 12-pixel prominence; the baseline's broad
shallow humps do not register, the hierarchical tower does. The base standard
deviation measures the bottom contour: 0 is a ruler line, 0.02 is a gentle
undulation.

### Verdict

The **hierarchical** silhouette is clearly more convincing than the baseline:
one dominant convective tower, a secondary development at a different height,
flank lobes and small contour details, a mostly horizontal but soft base, and
no capsule-like lateral cuts. The asymmetric variant is more dynamic but its
leaning tower reads as a single finger on a loaf; the hierarchical keeps a
better balance between mass and tower.

The first stop is passed: the hierarchical morphology goes to the panorama.

## 2. Panorama experiment

The hierarchical silhouette is inserted in the existing distribution without
changing the number of masses (92-94), their positions or strengths, the
Cloud Amount logic, or the render setup. Seeds 3, 17, 42; views main and
right; requested global coverage 0.42; 2048x1024 texture.

The variant reuses the baseline layout exactly (u/lat/strength identical);
its radii are ~9% larger because the union fit normalises the same 0.50
maximum footprint and the hierarchical silhouette is more compact. The
generated global coverage is 0.420 on every seed for both variants.

### Frame metrics (6 cells each)

| | Baseline | Hierarchical | v1.0.3 |
|---|---|---|---|
| Frame coverage mean [min..max] | 0.336 [0.277..0.372] | 0.335 [0.270..0.371] | 0.419 (main) |
| Components mean [min..max] | **6.33 [5..8]** | **4.50 [3..6]** | 6 |
| Largest mean / max | 0.139 / 0.213 | 0.184 / **0.333** | 0.345 |
| Cells with largest > 0.30 | 0 | **1** | 1 |
| Perimeter mean | 11.06 | 11.63 | 14.39 |

The morphology preserves the global coverage and the frame coverage, but it
**increases the unions between neighbouring masses**: about two fewer
components per frame, a 32% larger dominant mass on average, and the worst
cell (seed 42 right) collapses to 3 components with a 0.333 bank against the
baseline's 5 components / 0.213. The v1.0.3 historical reference is at 0.419
coverage with 6 components and a 0.345 dominant mass; the hierarchical's worst
cell is close to that dominant mass, with fewer components.

A scale check (union target 0.43 and 0.46 instead of 0.50) did **not** reduce
the merging: the components stay at 4.5 and the dominant mass even grows at
0.43. The effect is morphological (taller shapes and edge details bridging),
not an artefact of the size normalisation.

## 3. Costs

| | Baseline | Hierarchical |
|---|---|---|
| Primitives per mass | 7-8 | 15 |
| Generation 1024x512 | 268 ms | 488 ms |
| Generation 2048x1024 | 936-1063 ms (mean 1000) | 1706-1772 ms (mean 1733) |
| Field / image / EXR at 2048 | 8 / 32 / 32 MiB | unchanged |

Generation is **+73%** at 2048. Memory is unchanged; the render cost is
dominated by the World texture sampling (~1.15 s at 2048 for both). The
texture is not cheaper than the procedural A.

## 4. Limits and open points

- **Merging regression**: at the 0.42 global request the taller shapes bridge
  more often. This is measured, not hidden; the user must decide whether the
  silhouette gain justifies it.
- **Discrete Cloud Amount**: whole-mass selection makes a mass appear or
  disappear at a threshold step (one mass is roughly 0.5-1.5% of the global
  coverage). A future animation would pop; it is documented, not addressed in
  this phase.
- **Stacked-lobe look**: the towers are unions of 4 lobes; in some specimens
  the joints read as small horizontal steps. More organic tower construction
  is future work.
- **Aspect**: the single-mass masks do not apply the per-mass aspect
  (0.66-0.95) used in the panorama, so the in-frame towers are slightly
  flatter than the sheet suggests.
- **No shading, silver lining, wind, transparency, UI or new artistic
  controls.** The v1.0.3 images are the historical reference, not re-rendered.
- The v1.0.3 comparison is a single main-view cell; the other cells are the
  same-camera distribution comparison.

## 5. Files

- `contact_anatomy.png` — 3 variants x 3 specimens, full silhouettes.
- `contact_anatomy_detail.png` — specimen 1: full, summit detail, base detail.
- `masks/` — the nine single-mass masks and `anatomy.json`.
- `anatomy_metrics.json` — per-specimen and summary metrics.
- `contact_distribution.png` — baseline vs hierarchical, 3 seeds x 2 views and
  masks.
- `contact_distribution_detail.png` — same-camera 1:1 crop and mask crop.
- `contact_v103.png` — v1.0.3 image and mask.
- `metrics.json` — per-cell frame metrics, global coverage, generation times.
- Scripts: `preset_dev/cloud_anatomy.py`,
  `preset_dev/cloud_anatomy_compare.py`,
  `preset_dev/cloud_distribution_morphology_compare.py`,
  `preset_dev/cloud_distribution_proto.py` (`--variant`, `--union`).

The baseline remains pixel-identical to the committed 2D prototype: a seed-3,
1024x512, 0.30 main render after the refactor has max delta 0 against the
saved reference.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_anatomy.py -- --out preset_dev\cloud_anatomy\masks
python preset_dev\cloud_anatomy_compare.py -- `
  --anatomy preset_dev\cloud_anatomy\masks --out preset_dev\cloud_anatomy

foreach ($variant in @("baseline", "hierarchical")) {
  foreach ($seed in 3, 17, 42) {
    & $blender -b --factory-startup --python-exit-code 1 `
      --python preset_dev\cloud_distribution_proto.py -- `
      --out <run> --seed $seed --width 2048 --height 1024 `
      --variant $variant --amounts 0.42 --views main,right
  }
}
python preset_dev\cloud_distribution_morphology_compare.py -- `
  --base <baseline run> --hier <hierarchical run> --out preset_dev\cloud_anatomy
```

## Decision

The hierarchical morphology is a credible improvement of the single Cumulus
silhouette. The panorama preserves the coverage but pays with more unions at
0.42. **Do not integrate.** No merge, no release; the visual decision and any
follow-up (distribution-aware spacing or a milder tower) require explicit
user approval.
