# Preset identity - review 1 (IN REVIEW, not approved)

This is the response to the artistic review of the 12 presets. The release
2.63.0 is **not published or tagged** while this review is open.

Branch: `feature/preset-identity` from `081962f` (master release candidate).
No merge, tag or version change in this pass. No new preset added. AgX and
Color Management are unchanged. No new cloud algorithm.

## Two comparison boards

The requested boards are in this folder:

1. **`gradient_board.png`** - identical conditions: fixed lookdev scene,
   sky-only camera, no clouds/stars/sun disk, one neutral sun for all presets.
   This isolates the palette and gradient.
2. **`sun_board.png`** - each preset with its **native** Sun (position,
   energy, color) and a wide camera including Sun and horizon; clouds/stars off.
3. **`cloud_board.png`** - validation: native Sun, clouds and stars, original
   lookdev camera. This is the "real use" comparison.

Metrics: `gradient_metrics.json`, `sun_metrics.json`, `cloud_metrics.json`.

## First-pass decisions

### Five presets revised more decisively

- **After School**: blue-lavender upper sky, warm peach horizon, lower cloud
  cover (0.55), no stars, less violet cloud shadows. Nostalgic rather than a
  fully pink sky.
- **Sakura Spring**: predominantly blue sky, ivory clouds with a pink edge,
  lower cloud cover (0.45), no stars. Pink is an accent, not the sky base.
- **Twilight Dusk**: dark indigo zenith, thinner orange band
  (`horizon_softness 0.32`), fewer stars (0.25) and less Milky Way (0.20),
  lower Sun and no solar disk.
- **Blue Hour**: deeper cobalt/indigo, darker foreground, cooler lavender
  horizon, lower Sun and no solar disk.
- **Neon Night**: deep night blue at the top, magenta concentrated near the
  horizon, narrower band, selective cyan accent, lower cloud cover (0.45),
  no solar disk.

### Three refined

- **Golden Hour**: more golden/amber horizon, less uniform pink; peach cloud
  light and less violet shadows; stars removed.
- **Soft Dawn**: colder morning blue above, peach horizon; lower Sun (about
  5 deg), lower energy; stars removed.
- **Moonlit Night**: lower world strength (0.45) and Sun energy (0.30); blue
  reflections and stars preserved.

### Four kept intentionally close

- **Summer Noon**: slightly deeper zenith blue and whiter clouds.
- **Rainy Tokyo**: a little more haze, lower direct Sun contrast, no solar
  disk/glow.
- **Cloudy Afternoon**: slightly clearer cloud-mass separation, no new
  algorithm.
- **Stormy Sunset**: warmer lower cloud edges and slightly darker ground.

### Native lighting

- **Neon Night**, **Twilight Dusk** and **Blue Hour** now place the Sun below
  the horizon and disable the solar disk; the Sun is a low stylized fill, not
  a visible daytime disk.
- **Rainy Tokyo** disables the solar disk and glow for an overcast read.
- **Soft Dawn** lowers the Sun to a dawn elevation.
- **Moonlit Night** keeps the small disk as a moon-like stylized source and is
  documented as such.

Parameter experiments from the review:
Golden Hour stars 0; After School cloud 0.55 / stars 0; Sakura cloud 0.45;
Neon cloud 0.45; Twilight stars 0.25 / Milky Way 0.20; Soft Dawn stars 0;
Stormy Sunset stars 0.

## What still looks weak

- **After School** and **Sakura Spring** are still deliberately pale/pastel.
  The gradient board shows the intended separation; the native/cloud board
  remains soft. If this is too washed out, the next lever is the Sun energy /
  World strength, not a new algorithm.
- **Golden Hour, Neon Night, Twilight Dusk and Stormy Sunset** still share
  large dark cloud masses in the upper frame. Coverage was reduced, but the
  silhouette family is the existing generator; no new distribution/noise was
  introduced, as requested.
- **Twilight Dusk** still has a fairly broad warm band. It was reduced once;
  the next decision is aesthetic, not technical.
- The native board shows the Sun/horizon but the spheres are not always in the
  wide framing; `cloud_board.png` is the material/lighting validation.

## Method / reproducibility

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode gradients `
  --out preset_dev\preset_identity\gradients

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode sun `
  --out preset_dev\preset_identity\sun

& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\preset_identity.py -- --mode clouds `
  --out preset_dev\preset_identity\clouds
```

The current checked-in boards are in this folder; the per-mode folders are
reproducible output.

## Status

**IN REVIEW - not approved.** Two artistic passes were made (gradient/identity
and cloud/lighting refinement). No further pass should be made until the user
chooses which candidates need another direction. No tag, release or merge.
