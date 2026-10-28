# 2D Cloud Distribution — initial prototype

Status: **VISUAL REVIEW PENDING**

Independent research prototype on branch `experiment/cloud-distribution-2d`.
`master` stays at A (`f1e5f97`). No merge, no release, no change to the add-on,
its palette, presets, UI, shooting stars or compositor.

## What the prototype does

- Builds a **2048x1024 equirectangular density panorama** in NumPy from a
  jittered Fibonacci lattice over the visible hemisphere: 92-94 individual
  masses, uniform by solid angle, no latitude bands and no grid. The seed
  draws a new lattice, radii, strengths and lobes; it is not a translation of
  one noise field.
- Each mass is the signed-distance union of a low body, 5-7 rounded lobes and
  a flat-base half-plane. A two-channel fBm warp (48x24, 3 octaves, +/-0.10
  mass radii) perturbs the outline only; it does not define the mass.
- The density is a solid plateau with a ~1 degree outer ramp. **Cloud Amount
  selects whole masses** by a strength tag (`field > threshold`), so a mass is
  never semi-transparent and never fragmented into detached lobes.
- Coverage is the requested **global coverage of the visible hemisphere**,
  weighted by the angular area of each pixel (`cos(lat)`). The threshold is
  solved against that distribution; there is no per-camera or per-frame
  compensation.
- The panorama is packed into the `.blend` as a 32-bit float, Non-Color EXR
  and sampled with `ShaderNodeTexEnvironment` (default view-direction vector).
  No geometry, no camera input: the clouds are fixed in the World.
- The cloud colour is the flat `SUMMER_NOON` `cloud_mid`; there is no
  lighting, silver lining, compositor or palette work. This is a silhouette
  study, not a look candidate.

Prototype script: `preset_dev/cloud_distribution_proto.py`. The add-on is
imported only to build the base `SUMMER_NOON` sky.

## First comparison

Palette `SUMMER_NOON`, no compositor, 1280x720, AgX, 32 TAA samples.
Seeds 3, 17, 42; Cloud Amount 0.18 / 0.30 / 0.42 (global); views `main` and
`right`; A at its standard 0.78.

### Comparable-coverage cells (seed 3 main, 0.42 vs 0.78)

| | v1.0.3 | A 0.78 | prototype 0.42 |
|---|---|---|---|
| Frame coverage | 0.419 | 0.348 | 0.316 |
| Components | 6 | **2** | **6** |
| Largest component | 0.345 | 0.276 | 0.157 |
| Perimeter (normalized) | 14.39 | 11.93* | 11.06* |

`*` perimeter is averaged over the 6 A/prototype cells, not this cell.

### Six cells at the standard comparison

| | A 0.78 | prototype 0.42 |
|---|---|---|
| Frame coverage mean [min..max] | 0.307 [0.136..0.426] | 0.336 [0.277..0.372] |
| Components mean [min..max] | 2.83 [1..6] | **6.33 [5..8]** |
| Largest mean / max | 0.274 / **0.409** | 0.139 / **0.213** |
| Perimeter mean | 11.93 | 11.06 |

At a slightly higher frame coverage the prototype keeps more than twice the
components and about half the dominant mass. The clearest controlled pair is
seed 42 right: A 0.409 coverage in **one** component (largest 0.409); the
prototype 0.368 in **five** (largest 0.213).

The prototype is deliberately not coverage-matched per cell: its frame
coverage depends on where the camera looks. The labels on every sheet report
the achieved frame coverage and the global request.

### Amount progression (prototype, 6 cells per amount)

| Global request | Frame coverage mean [min..max] | Components mean | Largest mean |
|---|---|---|---|
| 0.18 | 0.091 [0.056..0.150] | 3.17 | 0.053 |
| 0.30 | 0.228 [0.179..0.285] | 5.50 | 0.106 |
| 0.42 | 0.336 [0.277..0.372] | 6.33 | 0.139 |

### Cloud Amount -> global coverage (seed 17)

| Request | 0.05 | 0.10 | 0.15 | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 |
|---|---|---|---|---|---|---|---|---|---|---|
| Achieved | 0.049 | 0.098 | 0.145 | 0.199 | 0.250 | 0.300 | 0.349 | 0.399 | 0.450 | 0.494 |

The global curve is essentially the identity. Whole-mass selection quantizes
the result by one mass (~0.5-1.5%); the 0.18 request achieved 0.175-0.179 on
the three seeds. The frame coverage instead varies widely by design; see
`contact_curve.png`.

## Costs

Measured on the same machine, Eevee, 1280x720, 32 samples.

| Item | 1024x512 | 2048x1024 |
|---|---|---|
| Generation (union fit, up to 3 passes) | 268 ms | 995-1042 ms (mean 1021) |
| Density field (float32) | 2.0 MiB | 8.0 MiB |
| Runtime image (float RGBA) | 8.0 MiB | 32.0 MiB |
| Packed EXR | 8.0 MiB | 32.0 MiB |

- Prototype render median: **1145 ms**; A reference median: **1138 ms**
  (+0.6%). The texture is **not** cheaper than the procedural A: it adds
  ~32 MiB of image and ~1 s of generation at 2048.
- Sample `.blend` at 1024: **339 KiB on disk** (the packed EXR is 8,397,217 B;
  the zero-heavy data compresses under Blender's zstd). Reopened without the
  external EXR it renders **pixel-identical** to the original (max delta 0).
- Overlay: 11 World nodes; the production World group is untouched.

## Checks

- **Seam**: the field is a function of direction, so the u=0 column and the
  last column are adjacent directions. Max column delta at the seam:
  0.066-0.154, against a normal neighbour max of 0.288-0.310. No seam line in
  the renders; the thin vertical gaps visible between some masses are clear
  slots between separate masses, not a texture seam.
- **Resolution**: 1024 and 2048 produce the same layout (mask IoU 0.985).
  2048 has cleaner edges; see `contact_resolution.png` (full frame plus a 2x
  crop).
- **Camera independence**: the texture is sampled by view direction; no
  camera node feeds it. The two views and the panorama show the same masses
  at the same World positions.
- **Determinism**: the same seed and size reproduce the same field; seeds
  differ by layout, sizes, strengths and lobes, not by a translation.

## Limits

1. **Maximum coverage ~0.495**: the union of all masses is the ceiling. Cloud
   Amount above ~0.50 saturates; this is a scattered-cumulus prototype, not
   an overcast generator.
2. **Whole-mass selection**: the achieved global coverage steps by one mass
   (up to ~1.5% at low amounts). The 0.18 request gives 0.175-0.179.
3. **Per-frame variation is large**: 0.056-0.372 at the standard cells. That
   is the intended camera independence, but it means the director must choose
   the camera/seed, not only Cloud Amount.
4. **No shading**: flat `cloud_mid` silhouettes; lighting, silver lining and
   palette are intentionally untouched. This is not an aesthetic verdict.
5. **Polar projection**: the top of the equirect panorama is compressed; the
   mass count per solid angle is uniform, but the zenith can show overlapping
   masses. The comparison views (0-30 degrees elevation) are unaffected.
6. **Wind is not implemented**. The field is direction-indexed, so a future
   longitude offset would move the masses without regenerating shapes, but
   this is a design property, not tested animation.
7. **Texture memory**: a 32-bit float mask at 2048 costs 32 MiB unpacked. A
   production version would need 16-bit or tiled storage; the prototype does
   not claim that a texture is free.

## Recommendation

The prototype does what the current generator does not: at comparable frame
coverage it keeps 5-8 separate masses with flat bases and lobed tops, instead
of collapsing into one or two large banks. The global Cloud Amount control is
predictable and exact within one mass.

The visual decision is the user's. Do **not** integrate the mask into the
production World yet. The next step, if approved, would be a look test
(shading/silver lining) on the same silhouettes, and a decision on the
coverage ceiling and the per-camera variation. No further variant was started.

## Evidence

- `contact_main.png` - v1.0.3 / A / prototype at comparable coverage, masks.
- `contact_seeds.png` - A vs prototype 0.42, 3 seeds main + seed 42 right,
  masks; the worst-coverage cell is labelled.
- `contact_amounts.png` - prototype 0.18 / 0.30 / 0.42 x 3 seeds, main.
- `contact_views.png` - seed 17, three amounts x main/right.
- `contact_curve.png` - Cloud Amount -> global and frame coverage.
- `contact_resolution.png` - 1024 vs 2048 and a 2x edge crop.
- `contact_panorama.png` - the three fields, all masses (strength shown).
- `field_s03.png`, `field_s17.png`, `field_s42.png` - panorama previews.
- `mask_*.png` - v1.0.3 / A / prototype masks for the main comparison.
- `metrics.json` - all per-cell metrics, curve, costs, seam data.
- `prototype_s03_1024x512.blend` - standalone sample with the packed mask.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
foreach ($seed in 3, 17, 42) {
  & $blender -b --factory-startup --python-exit-code 1 `
    --python preset_dev\cloud_distribution_proto.py -- `
    --out <dir> --seed $seed --width 2048 --height 1024 `
    --amounts 0.18,0.30,0.42 --views main,right
}
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\cloud_distribution_reference.py -- `
  --out <dir> --seeds 3,17,42 --views main,right --amount 0.78
python preset_dev\cloud_distribution_compare.py -- `
  --out <dir> --final <dir> --curve <curve dir> `
  --preview <panorama previews> --resolution <1024 run>
```

`cloud_distribution_reload.py` verifies the packed mask after reopening;
`cloud_distribution_preview.py` exports the panorama PNG previews.
