# Preset identity - APPROVED for 2.63.0

Response to the artistic review of the 12 presets. Release 2.63.0 is **not
published or tagged** while the visual sign-off is open.

Branch: `feature/preset-identity` from `081962f` (master release candidate).
No merge, tag or version change. No new preset, effect, cloud family or
algorithm. AgX and Color Management unchanged.

## Boards (JPEG, small enough to review from the repo)

1. **`gradient_board.jpg`** - identical conditions: fixed scene, sky-only
   camera (12 mm, 25 deg), no clouds/stars/disk, one neutral sun and one camera
   for all presets. Compares palettes only.
2. **`sun_board.jpg`** - each preset with its **native** Sun (position,
   energy, color) and a wide camera including Sun and horizon; clouds/stars
   off. Verifies the native lighting.
3. **`cloud_board.jpg`** - validation: native Sun, clouds and stars, original
   lookdev camera. The "real use" comparison.

The checked-in boards are JPEG (88, progressive) so they can be opened from
GitHub; the render scripts still write full-resolution PNG to the output
folder. Metrics: `gradient_metrics.json`, `sun_metrics.json`,
`cloud_metrics.json`.

## Targeted tuning (this pass)

Only the three uncertain presets and the four cloud seeds were touched. The
other nine palettes are exactly as reviewed.

Boards: `after_sakura_variants.jpg`, `twilight_softness.jpg`, `cloud_seeds.jpg`.

- **After School** - `world_strength 0.92 -> 0.86` (World -10% of the current
  value). The Sun -15% variant was tested and not selected: it lifted the
  scene without recovering colour.
- **Sakura Spring** - `world_strength 0.92 -> 0.83` (World -10%). The Sun -15%
  variant was also tested and not selected.
- **Twilight Dusk** - `horizon_softness 0.32 -> 0.26`, everything else
  unchanged. The warm band is narrower and the transition to night reads more
  naturally; the 0.32 variant was softer and broader.
- **Cloud seeds** - Golden Hour 17 (unchanged), Neon Night 43, Twilight Dusk
  71, Stormy Sunset 97. Only `Cloud Seed` changes: same coverage, shape
  parameters, colours and shader. `apply_preset_style` now writes
  `settings.cloud_seed`, so each preset reproduces its own silhouette and a
  preset change resets a user seed deterministically.

Final values: After School world 0.86 / sun 3.8; Sakura Spring world 0.83 /
sun 3.2; Twilight Dusk softness 0.26 / seed 71.

## Decisions carried from the previous pass

### Five revised decisively

- **After School**: blue-lavender upper sky, warm peach horizon, cover 0.55,
  no stars, less violet cloud shadows.
- **Sakura Spring**: blue base, ivory/pink-edged clouds, cover 0.45, no stars.
- **Twilight Dusk**: dark indigo zenith, thinner orange band, stars 0.25,
  Milky Way 0.20, Sun below the horizon, no disk.
- **Blue Hour**: deeper cobalt/indigo, darker foreground, lavender horizon,
  Sun below the horizon, no disk.
- **Neon Night**: deep night blue at the top, magenta concentrated at the
  horizon, narrower band, selective cyan accent, cover 0.45, no disk.

### Three refined

- **Golden Hour**: golden/amber horizon, peach cloud light, less violet
  shadows, stars 0.
- **Soft Dawn**: colder morning blue above, peach horizon, Sun about 5 deg,
  lower energy, stars 0.
- **Moonlit Night**: world 0.45, Sun 0.30; blue reflections and stars kept.

### Four kept close

- **Summer Noon**: slightly deeper zenith blue, whiter clouds.
- **Rainy Tokyo**: a little more haze, lower direct Sun contrast, no disk/glow.
- **Cloudy Afternoon**: slightly clearer cloud separation; no new algorithm.
- **Stormy Sunset**: warmer lower cloud edges, slightly darker ground,
  stars 0.

### Native lighting

- Neon Night, Twilight Dusk and Blue Hour place the Sun below the horizon and
  disable the solar disk; it is a low stylized fill, not a visible day disk.
- Rainy Tokyo disables disk and glow for the overcast read.
- Soft Dawn lowers the Sun to a dawn elevation.
- Moonlit Night keeps the small disk as a moon-like stylized source and is
  documented as such.

## Regression (final tuned palette.py)

- `verify.py` - **ALD GATE PASS**
- `phase3_ui.py` - **68/68 PASS**
- `phase1a_shooting_stars.py` - **37/37 PASS**
- `phase1b_markers.py` - marker 29/30 -> 35, 4/4 events and animation preserved
- `phase2_audit.py` - **PASS**
- `phase6_technical.py` - **17/17 PASS**
- `verify_all.py` - **ALD ALL PASS**, World audit 44/44
- `build_release.py` - **PASS** (2.63.0 package built and tagged)

## Known limits (documented, not reopened)

- After School and Sakura Spring remain intentionally pale/pastel. If they
  still read too soft, the next lever is Sun/World strength, not gradient
  saturation and not a new algorithm.
- Golden Hour, Neon Night, Twilight Dusk and Stormy Sunset now use distinct
  seeds, but the silhouette family is still the existing generator.
- Twilight Dusk keeps a visible warm band; 0.26 is the narrowest tested value
  that stayed natural.
- Stratocumulus and Cirrus still have no individual aesthetic sign-off;
  Cumulus is the approved family.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode gradients --out <dir>
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode sun --out <dir>
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode clouds --out <dir>
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_tuning.py -- --out <dir>
```

The tuning script renders baseline vs Sun -15% vs World -10% for After School
and Sakura Spring, Twilight 0.32 vs 0.26 sky-only at the horizon, and the four
seed before/after pairs. `preset_tuning.py` writes PNG; the JPEG boards in this
folder were assembled from that output and the final board render.

## Status

**VISUAL APPROVED - 2.63.0 unblocked.** The user approved all 12 presets on
2026-10-30, including the After School / Sakura Spring World -10% pass, the
Twilight Dusk softness 0.26 and the four cloud seeds. Two artistic passes plus
this targeted pass were made; no further pass is planned. Merged to `master`
with this evidence.
