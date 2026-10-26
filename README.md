# Anime Look Director

Atmospheric palettes and a non-destructive anime compositor stack for Blender 5.1+.

## What it does (v2.35.0)
- Seven atmosphere presets (Golden Hour, **After School Sunset**, Summer Noon,
  Rainy Tokyo, Cyberpunk Neon, Sakura Spring, Twilight Dusk) with a
  Scene-Linear Rec.709 color script calibrated for AgX.
- **Four-zone sky**: ground → horizon → mid-sky bridge → zenith, with a dedicated
  mid color that avoids muddy sunset midpoints.
- **Perspective planar anime clouds**: the view ray is projected onto a curved
  atmospheric deck, so clouds stretch into layered bands near the horizon.
  The **Cloud Flatness** control blends billowy cumuli (0) and flat horizontal
  strata (1). Perlin-Worley density gives compact lobes, while a solar
  finite difference drives violet/mauve cores and a thin silver-lining rim.
  **Delta Gain** and **Rim Boost** expose the painterly transfers; cloud color is
  independent from the horizon tint and an optional **Sky Accent** paints a turquoise or
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
- **Three-tier clustered painterly starfield**: dense stardust, medium
  constellation stars and soft gouache hero stars with halos, using per-cell
  Voronoi Color hashes, translated grids, warm/cool temperatures and a
  palette-tinted glow; masked by clouds and the sun disk.
- **Custom cloud colors**: dedicated Cloud Shadow, Cloud Mid and Cloud Light
  controls in Custom Colors, independent from Horizon, Sun and Shadow.
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
- v1.0.0 - dome-sampled cloud density, fBm morphology, 3-band cel shading
- v1.0.1 - cauliflower clouds, 4-band gouache, Apply Palette slider reset
- v1.0.2 - restored organic fBm clouds; Cloud Light confined to the sun fringe
- v1.0.3 - envelope-driven shading, internal Cloud Light suppression, atmosphere resets
- v1.0.4 - cloud/horizon decoupling, clustered painterly stars, richer presets, neutral UI names
- v1.0.5 - dedicated cloud color controls and three-tier hash-based starfield
- v1.0.6 - reliable sky toggles, true Star Amount, warped readable stars, panel parity
- v1.0.7 - sharp Kuwahara-masked sky, pinpoint stars, true horizon shift, tinted contrails
- v1.0.8 - anti-aliased PSF stars with X/Y/Z hash channels and Perlin-Worley clouds
- v1.1.0 - Sun Beams/Glow quick toggles, shooting stars and anime fireworks
- v1.1.1 - 2D stereographic meteors, Milky Way river and Hanabi bursts
- v1.1.2 - tangent-plane meteors/fireworks, Milky Way fix and vivid Hanabi colors
- v1.1.3 - stereographic hollow Hanabi shells with high-chroma palettes
- v1.1.4 - spherical foreshortened Hanabi shells, constant-width trails and hot hoshi heads
- v2.0.0 - 3D FX particle fireworks/meteors with real depth and overlap
- v2.0.1 - tapered physical firework trails, hollow shells and stronger droop
- v2.1.0 - deterministic FX solver, per-scene ownership, FX backend selector
- v2.2.0 - FX compositing separation with dedicated glow
- v2.3.0 - animated in-place FX, burst roles and staggered families
- v2.4.0 - beaded spark trails and a live Burst Age control
- v2.5.0 - inner pistil population, FX system editor, verified occlusion
- v2.6.0 - granular trails, meteor fragments and composition controls
- v2.7.0 - Geometry Nodes prototype for the burst heads
- v2.8.0 - Geometry Nodes evaluation of the whole burst population, verified
  against the Python solver
- v2.9.0 - the trails, the flash and the meteors are evaluated by the nodes
  too: the frame handler writes no geometry any more
- v2.9.1 - drag free limit in the node group and the missing mandatory gate
  tests of the technical guide
- v2.9.2 - FX lookdev comparison renders with the recorded metadata, FX panel
  listing fix and UI verified with real screenshots
- v2.10.0 - the caches are invalidated when a new file is loaded and the
  frame handler no longer touches the node group systems
- v2.10.1 - family comparison renders (Chrysanthemum, Peony and Willow with
  the same palette and seed)
- v2.11.0 - the Burst Age slider moves the systems without rebuilding the
  geometry: real time, 189 times faster
- v2.11.1 - the UI verification is a tool of the repository
  (`preset_dev/ui_probe.py`)
- v2.12.0 - phase P0-A of the operational plan: the decay, the composition
  rule, the meteor geometry and the child origins are corrected and the two
  backends share the same deterministic data
- v2.13.0 - phase P0-B: persistent systems and events, robust scene identity
  with duplication handling, registry rebuilt from the saved configuration
- v2.14.0 - phase P1-A: one interface for both surfaces, exclusive backends
  (OFF / Legacy World / FX 3D), the FX system editor and the look controls
- v2.15.0 - phase P1-B: the state of the user is snapshotted before the first
  modification and "Remove ALD from Scene" restores the world, the sun, the
  materials, the passes and the compositor
- v2.16.0 - phase P1-C: the firework is a complete event, from the launcher
  to the rising shell, the burst without discontinuity and the residuals
- v2.17.0 - phase P1-D: the meteors are events and the Hero Meteor (Bolide)
  has its own preset, bigger and with a long persistent train
- v2.18.0 - phase P2: the material contract of the particles (role, age_norm,
  energy, trail_u, stable_noise, event_color) and the isolation of the FX
  layer in the compositor
- v2.19.0 - phase P3: a numerically stable solver, the evaluated camera
  frame, the clouds and the legacy stars in seconds, the Kamuro family and the
  backend chosen before the allocation
- v2.20.0 - the milestone of the plan: a single complete and reversible
  firework, the visible launcher and the Definition of Done verified by
  `preset_dev/milestone.py`
- v2.20.1 - the legacy world meteors follow the backend, the legacy controls
  only appear in the legacy backend and the FX section comes first in the
  sidebar
- v2.21.0 - the View3D sidebar and the Scene properties expose exactly the
  same controls, with the same structure
- v2.22.0 - the three actions on the scene (Bypass, Remove ALD from Scene,
  Detach and Keep Result), the FX are visible at once after the creation and
  the icons of the panels are validated against the real list
- v2.22.1 - the registration survives the reload of Blender, the camera and
  the sun use the evaluated transform and `preset_dev/audit_plan.py` audits
  the compliance with the operational plan
- v2.24.0 - the compositor FX isolation is replaced with a clean
  environment/FX-only/coverage pipeline (`C = (1-A)*Painted_B + F + Glare(F)`),
  per-event visibility diagnostics, corrected physics (gravity, velocity
  derivative, sparks inheritance, train decay, negative age clamp) and a real
  per-system clock
- v2.25.0 - fixes the `Writing to ID classes` crash during panel draw, adds the
  ALD Sky/FX Anchor (vertical axis, ground elevation, units scale), the camera
  below-ground conflict warning (T15) and the acceptance tests T25-T28
  (migration, undo/redo, failed build, UI screenshots)
- v2.26.0 - completes the ALD Sky/FX Anchor with an explicit terrain object:
  the conflict warning reads the ground mesh world matrix when assigned,
  falling back to the numeric elevation
- v2.27.0 - critical bug fix in the FX Python writer: `_update_meteors`
  crashed with `'NoneType' object has no attribute 'data'` because the
  non-GN path stores trail/head/fragment objects per-event but the updater
  read them from the wrong place. Gate test T24 (three FX profiles at fixed
  exposure) added
- v2.28.0 - P0 of the operational plan: safe FX operators (update by UID,
  atomic compile, record/geometry coordinated), snapshot on every mutation
  path with the REMOVED lifecycle state, real B/F/A FX isolation with
  depth-based occlusion and zero-FX identity, read-only diagnostics with
  explicit `UNKNOWN`
- v2.29.0 - P1-P2: persistent model (UID + roles, stable random keys,
  migration, undo/redo), anchor gravity and `p_shell(T)`, GN→Python per-event
  fallback, material contract (`event_color`, `stable_noise`, `age_norm`,
  `trail_u`) and AgX calibration matrix
- v2.30.0 - P3: volumetric atmospheric smoke, FX Style variants, directed 3/5
  burst show, benchmarks with declared budgets and hardware
- v2.30.1 - verification pass: UI probe fixed for Blender 5.1 (screenshots in
  `preset_dev/ui/`), milestone 13/13, smoke aligned to the Anchor, Visual
  Profile panel, P0-P3 audit 39/39
- v2.31.0 - P1 of the visual integration milestone: real FX coverage from the
  Cryptomatte Material pass, F = Emission x A, occlusion inherited from the
  visible render; removed the ALD FX Only layer, the transparent world override,
  the max(R,G,B) coverage and the depth comparison for opaque occluders
- v2.32.0 - P2: the filament tube was empty (`Points to Curves` needs a point
  cloud: added `Mesh to Points`), apparent width in pixels, round tube chosen
  over ribbon by measurement, secondary stars and per-star trail caps
- v2.33.0 - P3: fixed the grey punch veil, the double coverage and the black
  instanced particles; tail falloff, sky-tinted FX palette, calibrated glow
  (1.0 / 0.0 / 0.35)
- v2.34.0 - P4: depth hierarchy (hero 1.0x, secondary 1.18x, distant 1.42x),
  show spacing, earlier distant birth, composition renders and gate
- v2.35.0 - P5: 2.5D cloud bands at 160/230/320 m, opaque and depth-writing,
  palette-synced, removed by Remove ALD; they occlude the FX behind them (current)

## Recap
Italian overview of the whole add-on: [`RECAP.md`](RECAP.md).
