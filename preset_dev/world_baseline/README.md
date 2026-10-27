# World Sky Edition — Phase 0 baseline

This folder is the frozen visual comparison for the World-only redesign. It is
the evidence for the first gate: **do not remove the FX systems before this
baseline is accepted**.

## What is compared

| Version | Source | World |
|---|---|---|
| v1.0.3 | tag `v1.0.3`, isolated `BLENDER_USER_SCRIPTS` | original four-zone World + original clouds |
| v1.1.0 | tag `v1.1.0`, isolated `BLENDER_USER_SCRIPTS` | same World, later sun/beam additions |
| v2.56.0 | frozen tag `v2.56.0` | current World + reworked cloud shading |

The archived add-ons are activated from a temporary `BLENDER_USER_SCRIPTS`
with a temporary `BLENDER_USER_CONFIG`, so the current add-on is never the one
running for the old rows. No `.blend` is saved.

## Reproducible conditions

- 1280x720 and 1920x1080, EEVEE, 32 samples, AgX, exposure 0
- frame 1, 24 fps
- camera location `(0, -12, 3)`, rotation `(1.75, 0, 0.45)`, lens 32 mm
- palettes: `SUMMER_NOON`, `AFTER_SCHOOL`, `NEON_NIGHT`
- World clouds and stars on; Spatial Clouds, 3D FX and the compositor off
- sun baseline: camera aimed at the active sun, `GOLDEN_HOUR` and
  `AFTER_SCHOOL`, 1280x720

Commands:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\world_baseline.py -- --out preset_dev\world_baseline\current --tag v2.56.0
& $blender -b --factory-startup --python preset_dev\world_sun_baseline.py -- --out preset_dev\world_baseline\current\sun --tag v2.56.0
```

For an archived tag, check it out in a temporary worktree, copy its `.py` files
into a temporary `BLENDER_USER_SCRIPTS/addons/anime_look_director`, set a
temporary `BLENDER_USER_CONFIG`, and run the same scripts. The JSON next to the
images records the tag and the render metadata.

## Files

- `contact_1280.png`, `contact_1920.png`: rows = palettes, columns = versions
- `contact_sun.png`: rows = `GOLDEN_HOUR`, `AFTER_SCHOOL`; columns = versions
- `<version>/world_baseline.json`, `<version>/<palette>_<res>.png`
- `<version>/sun/world_sun_baseline.json`, `<version>/sun/sun_<palette>_1280x720.png`

## Reading the comparison

### Day (`SUMMER_NOON`)

- v1.0.3 / v1.1.0: isolated cumulus-like masses with rounded tops, clear
  openings and a readable white top / grey-lavender underside. The blue is
  deeper and the cloud silhouette is more legible.
- v2.56.0: the clouds read as a flatter veil or stratus band. The silhouette
  is softer and the internal contrast is lower; the sky is paler and more
  uniform.

### Sunset (`AFTER_SCHOOL`)

- v1.x: the clouds keep a strong pink illuminated side and a violet shadow
  side; the openings are clear and the horizon transition is warm.
- v2.56.0: the same cloud field is flatter and more uniform. The gradient is
  smoother and the horizon is cleaner, but the individual masses have less
  volume and less light-side/shadow-side separation.

### Night (`NEON_NIGHT`)

- v1.x: dark cloud silhouettes with a thin rim and a more uniform magenta sky.
- v2.56.0: a stronger blue-cyan horizon band and a softer cloud body. The
  gradient is more controlled, but the cloud shapes are less defined.

### Sun

- Both generations show the disk and a glow.
- v2.56.0 has a softer, cleaner halo and a more controlled horizon light.
- v1.x keeps a slightly stronger local contrast around the cloud edges.
- No version has a dedicated moon; the night test does not assume one.

## Recommendation before Phase 1

Keep the v2.56.0 technical base:

- four-zone World group and palette wiring;
- sun controls, elevation/azimuth, snapshot and per-scene ownership;
- persistent scene identity and reversible removal.

Recover from v1.x, inside the new World Sky system:

- the billowy, readable cloud masses;
- the light-side / shadow-side separation;
- the deeper day blue and the clear openings.

Do not copy the old node tree blindly: the new three-family generator must
produce the shape and then the shading from the same density field.

The first approval is **day Cumulus**: a blue sky with natural, clearly
structured clouds. If that gate is not convincing, sunset and shooting stars
are not started. The second gate is the same family at sunset; the third gate
is a single controlled shooting star.
