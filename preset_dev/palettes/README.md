> **Superseded by `preset_dev/preset_identity/README.md`.** The identity
> revision is **IN REVIEW - not approved**; this board is the first review.

# 12 presets - 2.63.0 review

Status: **IN REVIEW - pending user sign-off.** No preset values were changed in
this pass.

The board `review.png` uses the fixed look-dev scene from
`preset_dev/lookdev.py`: same camera, ground, spheres, sun and colour
management for all 12 presets. `sheet.png` is the raw 4x3 sheet; `review.json`
contains the per-preset luma/contrast/saturation metrics and status.

| # | Preset | Intent | Observation | Status |
|---|---|---|---|---|
| 01 | Golden Hour | Warm sunset, violet clouds | Warm horizon, strong orange/violet separation | Pending |
| 02 | After School | Peach/pink late afternoon | Soft peach; close to Sakura Spring in hue | Pending |
| 03 | Summer Noon | Clear blue noon | Bright cyan sky, white clouds, high key | Pending |
| 04 | Rainy Tokyo | Cool overcast rain | Desaturated grey/teal, low contrast | Pending |
| 05 | Neon Night | Magenta/blue night | Strong magenta horizon, deep blue zenith | Pending |
| 06 | Sakura Spring | Pale pink spring | Light pink, soft clouds; close to After School | Pending |
| 07 | Twilight Dusk | Deep orange/purple dusk | Warmer/darker than Golden Hour; more magenta | Pending |
| 08 | Soft Dawn | Pale lavender dawn | Very soft pastel; close to Blue Hour in value | Pending |
| 09 | Blue Hour | Cool blue hour | Cooler and deeper than Soft Dawn | Pending |
| 10 | Cloudy Afternoon | Bright overcast | Pale, low saturation, readable spheres | Pending |
| 11 | Stormy Sunset | Dark storm sunset | Dark mauve, dramatic clouds | Pending |
| 12 | Moonlit Night | Deep blue night | Dark, star field, cool highlights | Pending |

## Preliminary notes

- All 12 render without visible banding, clipped sun or lost sphere silhouettes
  at the look-dev framing.
- The clearest differentiation questions are:
  - **After School vs Sakura Spring** - both pink; Sakura is lighter and
    cloudier.
  - **Soft Dawn vs Blue Hour** - both cool pastels; Blue Hour is deeper.
  - **Golden Hour vs Twilight Dusk** - both warm; Twilight is darker/more
    magenta.
- The work is intentionally limited to review: no preset overrides, no shader
  changes, no version bump beyond the 2.63.0 candidate.
- The release tag is not created until this review is signed off.

## Evidence

- `review.png` - labelled 4x3 board.
- `review.json` - 12 entries with intent, observation metrics and `pending`
  status.
- `sheet.png` - original unlabelled sheet.
- `0_golden_hour.png` ... `11_moonlit_night.png` - individual renders.

## Reproduce

```powershell
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\lookdev.py -- --out preset_dev\palettes
```
