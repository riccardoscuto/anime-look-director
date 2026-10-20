# Anime Look Director

Atmospheric palettes and a non-destructive anime compositor stack for Blender 5.1+.

## What it does (v1.0.0)
- Seven atmosphere presets (Shinkai Golden Hour, **After School Sunset**, Ghibli
  Summer Noon, Rainy Tokyo, Cyberpunk Neon, Sakura Spring, Twilight Dusk) with a
  Scene-Linear Rec.709 color script calibrated for AgX.
- **Four-zone sky**: ground → horizon → mid-sky bridge → zenith, with a dedicated
  mid color that avoids muddy sunset midpoints.
- **Perspective planar anime clouds**: the view ray is projected onto a curved
  atmospheric deck, so clouds stretch into layered bands near the horizon.
  The **Cloud Flatness** control blends billowy Ghibli cumuli (0) and flat
  Persona strata (1). Perlin-Worley density gives compact lobes, while a solar
  finite difference drives violet/mauve cores and a thin silver-lining rim.
  **Delta Gain** and **Rim Boost** expose the painterly transfers; low clouds
  absorb the horizon tint and an optional **Sky Accent** paints a turquoise or
  coral band around the mid-sky stop.
- **Visible-sky / ambient split**: `World Strength` controls ambient light while
  the camera-visible sky stays vivid (Light Path `Is Camera Ray`).
- **Shadow Hue Lift**: a small additive tint veil so warm materials take the cool
  palette shadow instead of turning muddy olive.
- **Auto Sun**: applying a palette creates a sun light when the scene has none
  (can be disabled in the panel).
- Palette-driven **world gradient** with separate sky, horizon and ground colors,
  plus horizon offset and softness.
- **Sun disk** aligned with the sun direction, with size and strength.
- **Sun Elevation / Sun Azimuth** sliders, a two-lobe **Sun Glow** (narrow
  corona + wide horizon haze) and a one-click **Stage Backlight** operator that
  places the sun in front of the camera and enables the full backlight stack.
- **Anime clouds**: Perlin-Worley procedural clouds in palette colors, with
  amount, scale, **Cloud Flatness**, **Cloud Wind** animation and optional
  **Contrails**.
- **Micro starfield**: Voronoi points with magnitude variation, noise culling
  and a faint halo, masked by clouds and the sun disk, with Star Amount and Star
  Density; Golden Hour, After School, Neon Night and Twilight Dusk enable them.
- **Custom palette colors** for sky, horizon, sun and shadow (per scene).
  The custom Sun only drives the sun disk/light; cloud light stays on the preset.
- **Shadow tint** on scene materials: a reversible **multiplicative** node group
  that preserves texture detail while shifting shadowed areas toward the palette
  color. Turning it off zeroes AO but keeps Cel/Rim; the X button removes the
  group and disables Cel/Rim.
- **Cel terminator** driven by the palette sun (`N·L`), with Cel Shadow strength
  and Terminator sharpness; combined with AO for contact shadows.
- **Terminator Warmth**: a narrow warm subsurface band around `N·L = 0`, with a
  Skin preset boost.
- **Rim light** with Sun Side, 360 Contour and Backlight modes, tinted by the sun
  color; the HAIR preset gets a stronger angel-ring rim.
- **Rim emission** wired into Principled Emission Color (reversible), so rims read
  in backlight without being flattened by diffuse shading.
- **Real-time viewport updates**: moving the sun or camera updates the sky disk,
  God Rays and cel shading without a rebuild.
- **Light Wrap** around object silhouettes and environment edges.
- **Aerial Haze**: distant geometry loses contrast and takes the horizon/shadow
  color for painted anime backgrounds.
- **Anime Ink Lines**: thin depth + Normal-based outlines tinted by the palette
  shadow, including internal creases and hard corners.
- **God Rays** (optional Sun Beams glare anchored to the sun's screen position,
  refreshed on frame change).
- **Shot markers**: palettes driven by `ALD:<PALETTE>` timeline markers, with a
  `Mark Shot` button.
- **Per-camera palette overrides**: each camera can carry its own atmosphere;
  switching cameras applies it. Precedence: camera > marker > scene palette.
- **Material presets** (Skin, Hair, Fabric, Metal, Emission) for selected objects.
- **Material exclusion**: exclude the active material from the global tint sync
  without changing its shader.
- A node-group compositor stack, **one per scene**:
  `Render Layers → Glare (Bloom) → Sun Beams → Kuwahara (depth-mixed) → Light Wrap → Aerial Haze → Ink Lines → Lens Distortion → Group Output`.
- One-click enable of the viewport compositor.
- **Sidebar N panel** (`View3D > Anime Look`) for palette, world, shadow and
  compositor controls without leaving the viewport.

## Install (development)
The folder lives in `Blender/5.1/scripts/addons/anime_look_director`.
Enable it in Preferences → Add-ons (or keep it enabled in this profile).

## Look-dev
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python preset_dev\lookdev.py -- --out "C:\Temp\ald_lookdev"
```
Renders the seven palettes on a fixed scene, writes a 4-column contact sheet and
prints luminance, contrast and saturation per palette. It never saves a `.blend`.

## Verification
```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" -b --factory-startup `
  --python-exit-code 1 --python preset_dev\verify.py
```
Expected output: `ALD GATE: PASS`.

## Roadmap
- v0.1 — stack + palettes
- v0.2 — world gradient, material shadow tint, light wrap
- v0.2.1 — auto sun, per-scene stacks
- v0.3 — God Rays, shot markers, material presets
- v0.3.1 — God Rays refresh/size, Emission preset
- v0.3.2 — in-place sliders, multiplicative shadow tint, sidebar N panel
- v0.4.0 — sun disk, anime clouds, ink lines, Sakura/Twilight, custom colors
- v0.5.0 — cel terminator, directional rim light, hair angel ring
- v0.6.0 — per-camera palette overrides, effective look coordinator
- v0.6.1 — normalized sun disk, live transforms, ink gain, rim emission
- v0.6.2 — Camera Override panel icon fix
- v0.7.0 — Linear Rec.709 color script, mid-sky bridge, directional clouds, hue lift
- v0.8.0 - sun controls + Stage Backlight, stars/cloud wind, aerial haze,
  normal ink, terminator warmth, rim modes, material exclusion
- v0.8.1 - custom Sun no longer repaints the clouds
- v0.9.0 - After School palette, planar cloud deck, backlit silver-lining
  shading, micro starfield and new sky gradient mapping
- v0.9.1 - per-preset cloud morphology/style calibration from reference images
- v0.9.2 - Sidebar cloud amount/scale controls
- v0.9.3 - edge-local silver lining at full Cloud Amount
- v0.9.4 - zero Cloud Light body base + visible sidebar version
- v0.9.5 - world group marker 10 forces the new cloud graph to rebuild
- v0.9.6 - fix Sidebar panel draw/version label
- v0.9.7 - coverage-based Cloud Amount, corrected solar delta, isoline contrails
- v0.9.8 - domain-warped Perlin-Worley clouds, per-cloud lighting, planar contrails
- v0.9.9 - straight gnomonic contrails + group rebuild marker 13
- v1.0.0 - dome-sampled cloud density, fBm morphology, 3-band cel shading (current)

## Recap
Italian overview of the whole add-on: [`RECAP.md`](RECAP.md).
