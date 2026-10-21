# Changelog

## 2.0.0 - 2026-10-20
### Added
- FX particle architecture in `fx.py`: physically placed 3D fireworks and
  shooting-star trails with camera-space placement, gravity, parabolic droop,
  multi-shell depth, hoshi heads and saturated chemical-like palettes.
- Operators `ald.fx_fireworks`, `ald.fx_meteors` and `ald.fx_clear`, plus an
  FX Particles panel.
### Changed
- The sky/world shader remains responsible for clouds, stars, Milky Way and
  atmosphere; explosions and meteors now have real 3D depth and overlap.

## 1.1.4 - 2026-10-20
### Fixed
- Hanabi uses horizon-aligned local axes on the stereographic disk, a stronger
  parabolic weeping-willow droop, three radial spark shells and constant
  linear trail width, replacing flat single-ring bicycle-wheel geometry.
- Bright hoshi star-heads at outer, mid and inner radii add spherical depth;
  hot heads and trails use separate 5.5x/9.5x HDR boosts.
- Fireworks altitude mask widened so hero bursts remain visible near the
  horizon and in the upper sky.
- World gradient marker 27.

## 1.1.3 - 2026-10-20
### Fixed
- Hanabi fireworks use true 2D stereographic Voronoi grids, low randomness and
  a cell guard, eliminating 3D cell slicing, wallpaper repetition and hard
  clipping at cell boundaries.
- Fireworks are hollow expanding spark shells with fine beaded trails, hoshi
  tips, contrasting pistils, embers and tiny center cores instead of solid
  bicycle-wheel discs.
- High-chroma analogous palette families replace complementary color mixing;
  layers are summed as independent RGB vectors instead of a fixed 50/50 color
  mix, preserving saturation through AgX.
- World gradient marker 26.

## 1.1.2 - 2026-10-20
### Fixed
- Milky Way socket is now connected to its mask and its star-density boost;
  the Milky Way toggle really controls the galactic river.
- Fireworks use continuous 3D Voronoi cell centers projected onto the local
  tangent plane, eliminating the atan2 seam and tying Fireworks Scale to the
  cell geometry.
- Shooting stars are needle-thin with a small diffraction cross and zenith
  masking, eliminating horizon tadpoles.
- Fireworks color is separated into a hot core and saturated colored
  filaments/embers, avoiding AgX whiteout.
- World gradient marker 25.

## 1.1.1 - 2026-10-20
### Fixed
- Shooting stars and Hanabi fireworks now use true 2D Voronoi cells on
  stereographic/cylindrical sky coordinates, eliminating spherical 3D cell
  artifacts and round blobs.
- Added Milky Way: a warped galactic river with a dark dust rift, cyan/violet
  palette and star-density boost.
- Sun Beams threshold raised to 3.5 so beams originate from the sun disk, not
  from stars or fireworks.
- Fireworks use larger hero bursts, gravitational droop, radial spokes,
  peony/pistil rings, embers and a radial color gradient.
- World gradient marker 24.

## 1.1.0 - 2026-10-20
### Added
- Sun Beams and Sun Glow toggles directly in the Sun controls; Apply Palette
  disables stale God Rays from Stage Backlight and restores the preset glow.
- Procedural shooting stars with cell-local 3D trajectories, independent hash
  channels, phase animation and HDR meteor heads.
- Procedural Hanabi fireworks with radial Voronoi spokes, peony/pistil rings,
  soft burst glow and per-cell gold/magenta/cyan palette.
### Changed
- World gradient marker 23.

## 1.0.8 - 2026-10-20
### Fixed
- Stars are now anti-aliased PSF points: existence, magnitude and temperature
  use independent Voronoi Color channels (X/Y/Z), with two tiers at
  `Star Density * 1.30` and `* 0.72`, plus Airy hero stars at `* 0.36`.
  Magnitudes have a guaranteed floor and the final tint is 12x HDR.
- Cloud morphology uses Perlin-Worley coupling: macro envelope gates billow and
  Voronoi lobes so open sky stays clean and cumuli gain rounded edge lobes.
- World gradient marker 22.

## 1.0.7 - 2026-10-20
### Fixed
- Kuwahara Painterly is masked by geometry, so the sky and stars stay sharp
  instead of being smeared by the anisotropic filter.
- Pinpoint Poisson stars: no domain warp, two sharp Voronoi tiers with tight
  radii, severe per-cell hash culling and a 3.8x tint; no more oval blobs.
- Horizon Offset now truly shifts the horizon line, sky gradient, cloud fade
  and star zenith masks.
- Apply Palette resets Sun Size, Sun Strength and Cloud Wind and realigns
  Custom Colors to the preset.
- Contrails are tinted by Cloud Light and default to 0.0 in all presets.
- Removed the obsolete micro-star specification from AGENTS.md.
- World gradient marker 21.

## 1.0.6 - 2026-10-20
### Fixed
- Apply Palette now re-enables `world_gradient`, `sun_disk`, `clouds` and
  `stars`, so a palette change restores the cloud controls and the sky UI.
- Removed the hidden `star_amount * star_strength` double multiplication.
  `star_strength` is now the visible preset star amount and the shader reads it
  directly, so raising Star Amount to 1.0 gives 100% of the stars.
- Custom color synchronization is guarded with `_syncing_style`, avoiding seven
  consecutive world/material rebuilds when Custom Colors is active.
- Starfield stars are no longer sub-pixel: celestial domain warp, readable
  tier radii (0.14/0.12/0.10), hash culling and a 10x glow.
- Sidebar now includes Sun Disk Size/Strength and the shadow-tint X button,
  matching the Scene panel layout.
- World gradient marker 20.

## 1.0.5 - 2026-10-20
### Added
- Dedicated Custom Colors entries for Cloud Shadow, Cloud Mid and Cloud Light.
  They synchronize to the active preset when Custom Colors is enabled or the
  palette changes, and they update the world shader independently of Horizon,
  Sun and Shadow.
- Three-tier clustered starfield driven by per-cell Voronoi Color hashes:
  dense stardust (`Star Density * 2.2`), medium constellation stars (`* 0.90`)
  and soft hero stars (`* 0.38`), with translated grids, random warm/cool
  temperatures and a 6.0x palette-tinted glow. This fixes the near-invisible
  v1.0.4 stars caused by one-octave Perlin culling thresholds.
- World gradient marker 19.

## 1.0.4 - 2026-10-20
### Changed
- Cloud color is fully independent from Horizon Color: removed the aerial
  fade/mix, linked the cloud glow directly into the cloud layer, removed the
  custom-color overrides for Cloud Shadow/Mid, and made the Cloud Mid fallback
  neutral `(0.6, 0.6, 0.7)`.
- New clustered painterly starfield: low-frequency constellation mask, sparse
  background micro-stars, soft gouache hero stars with halo, zenith/sun/cloud
  masks, and a palette-tinted star glow based on Cloud Light.
- All seven presets now carry explicit contrail, sun glow, sky accent, horizon
  offset/softness, star amount and star density values; Apply Palette syncs
  Sky Accent and the atmosphere controls.
- Removed franchise names from the UI and documentation preset labels; Cloud
  Flatness now reads "0 = billowy cumuli, 1 = flat horizontal strata".
- World gradient marker 18.

## 1.0.3 - 2026-10-20
### Fixed
- `_sample_cloud_density()` now returns `(rho, envelope, warped_pos)`. The rho
  path is unchanged from v1.0.2, so the silhouette is pixel-identical. A
  low-frequency envelope (`Detail 2.0`, `Roughness 0.45`, `Distortion 0.15`,
  macro scale) drives the solar derivative, eliminating internal Cloud Light
  speckles caused by sixth-octave density wobble.
- Solar ray step is 0.055 rad; body detail is 0.010 and the Shadow -> Mid step
  is -0.022..0.006.
- Silver lining is restricted to the outer edge: fringe top +0.022, fringe
  squared and scaled by 0.95, sun edge 0.000..0.022, plus a coverage presence
  gate. Internal concavities are no longer filled by Cloud Light.
- Apply Palette now resets `horizon_offset`, `horizon_softness`, `contrails`,
  `star_strength`, `star_density` as well as the cloud/glow controls.
- World gradient marker 17.

## 1.0.2 - 2026-10-20
### Fixed
- Restored the organic v1.0.0 cloud morphology: `_sample_cloud_density` returns
  `(rho, warped_pos)` with macro 0.66 + billow 0.22 + Voronoi puff 0.12,
  Detail 6.0/5.0, Roughness 0.58/0.54, domain warp 0.28. The smooth v1.0.1
  banks are gone.
- Removed `crown_curve` and `rim_total`. Cloud Light now comes only from
  `fringe * 0.92 * sun_edge * gamma`, scaled by Cloud Rim Boost. The cloud body
  stays Cloud Shadow / Cloud Mid even at Delta Gain or Rim Boost 4.0.
- Solar derivative is back on the full density with a 0.045 rad view-ray step;
  detail is 0.018 contour and 0.016 body; body is a single -0.018..0.008
  Shadow -> Mid step.
- SUMMER_NOON restored to flatness 0.25, scale 3.2, amount 0.70 and the v1.0.0
  cumulus colors.
- Apply Palette resets Cloud Scale, Delta Gain and Rim Boost as well as the
  other per-preset cloud/glow controls.
- World gradient marker 16.

## 1.0.1 - 2026-10-20
### Fixed
- `_sample_cloud_density` now returns `(rho_shape, rho_smooth, warped_pos)`.
  Macro Detail dropped to 1.8 / Roughness 0.42, high-frequency Perlin removed
  from the silhouette; two Voronoi dome octaves are masked by the macro bank.
  This removes torn-paper edges and isolated Voronoi cells.
- Solar derivative uses the smooth density and a 0.08 rad view-ray step, so
  high-frequency octaves no longer fragment the internal shadow.
- Cloud shading uses two steps with a 0.55 half-shadow plateau, then a
  0.022..0.042 crown, for four discrete gouache bands.
- SUMMER_NOON recalibrated: flatness 0.18, scale 2.4, amount 0.65, lavender
  shadows and bright cumulus colors.
- Apply Palette now resets `cloud_delta_gain`, `sun_glow` and
  `sky_accent_amount` as well as the per-preset cloud style.
- World gradient marker 15.

## 1.0.0 - 2026-10-20
### Added
- `_sample_cloud_density()` helper: projects any sky-dome ray through the
  curved shell, applies domain warping and returns a multi-octave fBm density
  plus the warped cloud position.
- Cloud shape is now fBm-dominated: macro 0.66 + billow 0.22 + high-frequency
  Voronoi puff 0.12, with domain warp 0.28. The weights were calibrated from
  the first 62/24/14 + 0.42 test, which produced fragmented holes in the
  viewport; the requested morphology/structure is preserved without the
  spherical Voronoi grid.
- Solar finite difference is now computed on the **sky dome**: displace the
  view ray by 0.035 rad toward `normalize(sun + zenith*0.65)`, then call the
  same density helper again. No 3D cell mismatch.
- Crisp silhouette: `coverage_top = coverage_center + 0.018`; detail is
  injected into the contour (`*0.018`) and body (`*0.022`) separately.
- Three cel bands: tight `body_mix` -0.014..0.002, crown 0.014..0.028 at
  0.85, rim = MAX(crown, fringe*sun_edge*gamma), then Rim Boost.
- Contrails remain straight gnomonic filaments.
- World gradient marker 14.

## 0.9.9 - 2026-10-20
### Fixed
- Contrails now use gnomonic `X/Z`, `Y/Z` coordinates instead of the curved
  shell `planar_uv`; a constant-u filament stays straight in the sky rather
  than bending into arcs. World group marker 12 -> 13.

## 0.9.8 - 2026-10-20
### Changed
- Cloud overhaul: domain-warped coordinates (`warp_noise` at 0.55*Cloud Scale,
  centered and scaled 0.32), a low-frequency macro bank (0.42*Cloud Scale,
  weight 0.26), and a separate soft silhouette density (0.36 Worley + 0.38 N1
  + 0.26 macro). High-frequency detail is injected only into `body_signal`.
- Per-cloud self-shadow: `light_dir = normalize(sun + zenith*0.65)` with a
  `0.38/Cloud Scale` step applied after Mapping; `mu_weight` removed.
  Crown highlight adds `0.35 * smoothstep(0.03, 0.11, body_signal) * sun_edge`
  to the rim.
- Contrails rebuilt in planar space: straight `u = 0.82X + 0.57Y` filaments
  with `v = -0.57X + 0.82Y` length fade, not spherical level sets.
- World gradient marker bumped 11 -> 12.

## 0.9.7 - 2026-10-20
### Fixed
- **Cloud Amount is now coverage, not opacity.** It drives the density
  threshold `tau0 = 0.68..0.42`, plus a tiny 0..0.03 gate. Low Amount leaves
  fewer compact opaque clouds instead of transparent ghosts.
- **Solar finite difference moved after Mapping** and scaled by
  `0.12 / Cloud Scale`. Detail is shared between both samples, so the step no
  longer spans a full noise period and no longer creates random light patches.
- **Contrails are an isoline**: `abs(noise - 0.60)` mapped 0..0.008 -> 1..0,
  instead of a monotonic MapRange that filled a third of the sky.
- World gradient marker bumped 10 -> 11 to force existing scenes to rebuild.

## 0.9.6 - 2026-10-20
### Fixed
- The Sidebar version label used `bpy.context.preferences.addons[...].module`,
  which is a path string in Blender 5.1, so `addon.module.bl_info` raised on
  every panel draw and made the N panel disappear. It now reads
  `sys.modules[__package__].bl_info`.
- Version 0.9.6.

## 0.9.5 - 2026-10-20
### Fixed
- Bumped the world-gradient group marker from 9 to 10. The 0.9.4 shader change
  was not rebuilding existing scenes because `ald_build` had not changed, so
  Blender kept the old beige-cloud graph. Reloading with 0.9.5 now forces the
  new edge-only Cloud Light graph.

## 0.9.4 - 2026-10-20
### Fixed
- Removed the remaining 8 % Cloud Light body base. The silver lining is now
  strictly `fringe * sun_edge * gamma`, so Cloud Amount 1.0 keeps the full
  violet/mauve body instead of turning beige.
- Sidebar N now prints the loaded add-on version (`v0.9.4`) so stale Python
  modules are immediately visible.

## 0.9.3 - 2026-10-20
### Fixed
- Cloud **Cloud Light** had a 35 % baseline across the whole cloud body, so
  increasing Cloud Amount toward 1.0 exposed a flat beige interior. The rim
  is now edge-local: 92 % fringe weighting plus an 8 % body base. Full coverage
  keeps the violet/mauve body and a thin silver lining.
- Version 0.9.3.

## 0.9.2 - 2026-10-20
### Fixed
- Sidebar N panel now exposes **Cloud Amount** and **Cloud Scale** alongside
  Cloud Flatness, so the cloud controls match the Scene panel.

## 0.9.1 - 2026-10-20
### Added
- **Per-preset cloud style**: `cloud_flatness`, `cloud_scale`,
  `cloud_rim_boost` and `cloud_amount` are stored in each preset and applied
  only when the effective palette key changes. Manual slider changes survive
  world/cloud refreshes on the same palette.
- AFTER_SCHOOL now uses flatness 0.90, scale 4.0, rim 2.0 and amount 0.90 for
  layered Persona-style bands; SUMMER_NOON uses flatness 0.25, scale 4.0 and
  amount 0.75 for small cumuli.
- Cloud Flatness now blends the raw spherical view (billowy) with the curved
  planar shell (strata), so 0 and 1 are genuinely different morphology, not
  just a Z stretch.
- Reference QA: P3R After School bands, cyan/white cumulus reference and the
  Oga/Persona artbooks were used to choose the per-preset values.

### Changed
- Palette changes sync style values behind a `style_syncing()` guard, so
  property update callbacks cannot recurse.
- Version 0.9.1.


## 0.9.0 - 2026-10-20
### Added
- **AFTER_SCHOOL** ("After School Sunset") palette: salmon-pink horizon,
  lavender-indigo zenith and backlit violet cloud bands, calibrated for AgX.
- **Sun Glow**: two Mie lobes around the sun - a narrow corona
  (`gamma+^16 * 0.65`) and a wide horizon-weighted haze
  (`gamma+^3.5 * smoothstep(0.75, 0.0, |Vz|) * 0.45`), summed, scaled by the
  new Sun Glow input (normalized to 0.45), tinted by Sun Color and added before
  the clouds. The opposite horizon stays cool.
- **Cloud Flatness**: exact curved-shell point
  `(Vx*t, Vy*t, Vz)` with `t=0.55/(max(Z,0.015)+0.18)` and Mapping scale
  `(0.75, 0.75, 1.25+3.0*Cloud Flatness)`; 0 = billowy Ghibli cumuli,
  0.65 = current 3.2 strata, 1 = Persona bands.
- **Perlin-Worley cloud density**: inverted Voronoi F1 lobes (0.38) plus two
  Perlin layers (0.44 base, 0.18 erosion) remove the sponge/camouflage look.
- **Solar finite difference**: full density is resampled at
  `p_cloud + 0.12 * L`; `delta = rho_here - rho_toward_sun` drives the
  Shadow/Mid body split and the sunward Silver Lining. The former hidden
  `x3` delta and `x2` rim transfers are now explicit `Delta Gain` and
  `Rim Boost` sliders, default 1.0.
- **Aerial blending + accent**: low clouds blend chromatically toward
  `Horizon Color`; an optional `Sky Accent` color/amount paints the
  turquoise/coral band around the mid-sky stop.
- **Micro starfield**: Voronoi density is multiplied by 2.5, the core is
  0.040 with POWER 2.5, and a Scale-45 noise magnitude mask (0.48..0.78) culls
  dim cells and varies star brightness. A low-intensity halo keeps the core
  legible at 1080p.
- **Optional contrails**: a high-altitude, horizontally stretched noise ribbon
  with its own `Contrails` control, off by default.
- New ground/horizon/mid-sky gradient mapping: ground is constrained below
  `Z = 0` (transition -0.08..0.01), mid-sky peak is clamped 0.05..0.65, and
  the zenith transition is clamped by Softness.
- `mu_s = L.z` gates the narrow corona below the horizon.
- Palette registry gate verifies `PALETTES` and `PRESETS` agree, that
  `AFTER_SCHOOL` is exposed in the scene enum, and that Sun Glow, Sky Accent,
  Cloud Flatness, Delta Gain, Rim Boost and Contrails are present and synced.

### Changed
- Recalibrated the six existing palettes for the new planar cloud deck and
  backlit shading; all preset cloud triads and star amounts were updated.
- Look-dev now renders all seven palettes in a 4-column contact sheet.

### Fixed
- Custom Sun still only affects the sun disk/light; cloud light remains the
  preset value (the 0.8.1 regression test remains in the gate).

## 0.8.1 - 2026-10-20
### Fixed
- Custom Colors: changing **Sun** no longer repaints the clouds. The custom
  sun color now only drives the sun disk/light and sun-based material/compositor
  tints; the cloud light stays on the selected preset's `cloud_light` value.
- Added a regression check that changes only `custom_sun` and verifies
  `Cloud Shadow`, `Cloud Mid` and `Cloud Light` are unchanged.


## 0.8.0 - 2026-10-20
### Added
- **Sun Elevation / Sun Azimuth** sliders with two-way synchronization to the
  active sun, plus a one-click **Stage Backlight** operator that frames the sun
  ahead of the camera (+12 deg / 15 deg side) and enables Sun Disk, God Rays,
  Light Wrap and Rim Light.
- **Starfield** in the world group: Voronoi points masked by the zenith, hidden
  by clouds and near the sun disk. Per-preset star amounts (Neon Night 0.8,
  Twilight Dusk 0.7) and Star Amount / Star Density controls.
- **Cloud Wind**: the cloud noise is driven by a frame-based Cloud Offset, so
  stars remain static while clouds drift during animation.
- **Aerial Haze**: distant geometry is tinted toward the horizon/shadow color
  using the depth range, masked to the scene silhouette.
- **Normal Ink Lines**: a Normal-pass discontinuity extractor is combined with
  the depth edges to ink creases, furniture and internal hard corners.
- **Terminator Warmth**: a narrow warm subsurface band around `N.L = 0`, with a
  Skin preset boost.
- **Rim Mode**: Sun Side, 360 Contour and Backlight rim selection through a
  single group input.
- **Material exclusion**: the active material can be excluded from the global
  sync (`mat["ald_exclude"]`); excluded materials are skipped by Apply/Build and
  retain their original shading until included again.

### Changed
- Light Wrap and Ink Lines now share one silhouette/depth geometry graph;
  `_depth_edges` receives a vertical offset for the ink chain, removing duplicate
  overlapping nodes.
- Turning **Shadow Tint** off zeroes only the AO Strength while keeping Cel and
  Rim shading active. The **X Clear Shadow Tint** button removes the group and
  disables Cel/Rim shading for a fully clean material state.
- `sun_toward` uses `matrix_world` when the sun has constraints, so Track To and
  other constraint-driven suns work.
- Auto-sun preset rotation is reapplied only when the palette key changes;
  manual slider angles and Stage Backlight survive world/cloud/weather refreshes.
- World gradient group marker is 7; old groups rebuild automatically.

### Gate
- New checks for sun angle movement, Stage Backlight, angle persistence across
  world updates, star amount/density, cloud wind offset, aerial haze, normal ink,
  terminator warmth/rim bias, and material exclusion.
- Pixel gate adds aerial haze; expected `ALD GATE: PASS`.


## 0.7.0 — 2026-10-19
### Added
- **Scientific 6-preset color script** calibrated in Scene-Linear Rec.709 for AgX,
  with a dedicated `mid_sky_color` bridge, cloud triads and `sun_rotation` per
  atmosphere.
- **Four-zone sky gradient**: ground → horizon → mid sky → zenith, removing the
  muddy blue/orange midpoint in sunset palettes.
- **Directional anime clouds**: the cloud color signal combines noise density with
  the sun dot product (`sun_bias`), so the sun side reads brighter and the target /
  fried-egg artifact is removed.
- **Visible sky vs ambient split**: `World Strength` now scales only non-camera
  rays inside the world group (`Light Path > Is Camera Ray`), keeping the visible
  sky vivid while controlling ambient light. Background strength is 1.0 when the
  gradient is active.
- **Shadow Hue Lift** (default 0.18): after the MULTIPLY tint, a small additive
  tint veil lets warm/dark materials take the blue/violet shadow atmosphere while
  preserving texture detail.
- Auto sun applies the preset `sun_rotation`; user suns keep their rotation.

### Fixed
- Changing palette while `Custom Colors` was active now refreshes the custom
  sky/horizon/sun/shadow colors to the newly selected preset.

### Gate
- Checks mid-sky, `World Strength`, background strength, hue lift, and custom
  color refresh on palette switch.

## 0.6.2 — 2026-10-19
### Fixed
- Camera Override panels used the invalid icon name `CAMERA`; Blender 5.1 accepts
  `CAMERA_DATA`. The invalid enum raised on every panel draw, which is why the
  traceback appeared after Remove Stack / Clear Shadow Tint triggered a redraw.
  Both the Scene and Sidebar N panels are fixed; the operations themselves were
  unaffected.

## 0.6.1 — 2026-10-19
### Fixed
- Sun disk: `Generated` view direction and `Sun Direction` are normalized before
  the dot product, so the cosine thresholds are stable and the angular radius is
  exact.
- Internal ink edges: `band_size == 0` now applies an 8× clamped gain, so 15–20 cm
  internal depth steps read as solid lines like the outer silhouette.
- Custom Colors now update halation/god-ray tints and the ink color immediately
  in the compositor, not only world/materials.

### Added
- **Real-time viewport updates**: a depsgraph transform cache pushes sun/camera
  changes into the world sun disk, material terminators/rim and God Rays without
  rebuilding nodes (no frame change required).
- **Rim emission**: the Shadow Tint group has an `Emission` output wired to
  Principled `Emission Color`, with a `Rim Emission` control. Wiring is reversible,
  skips materials with existing emission, and restores the original values.
- Gate: normalized sun vectors, depsgraph transform updates, ink gain, custom
  color tint sync, emission wiring/restoration.

## 0.6.0 — 2026-10-19
### Added
- **Per-camera palette overrides**: each Camera data-block can enable its own
  palette; switching the active camera applies it automatically.
- **Effective look coordinator** (`look.py`): precedence
  **camera > shot marker > scene base palette**.
- Effective look label in the Scene panel: `Look: <PALETTE> (camera|marker)`.
- Camera Override box in the Scene World & Shadows section and Sidebar N.
- Gate coverage for camera overrides and base-palette invariance.

### Changed
- Shot markers no longer overwrite `Scene.ald.palette`; they set the effective
  palette only. The base palette is preserved for non-marker shots.
- Palette changes, world controls and `Apply Palette` all resolve the effective
  palette instead of assuming the base.
- `compositor` glare tints and `shadow_tint_for` use the effective palette key.
- Version 0.6.0.

## 0.5.0 — 2026-10-19
### Added
- **Cel terminator** in the Shadow Tint group: `N·L` against the palette sun,
  combined with AO, with Cel Shadow strength and Terminator sharpness controls.
- **Directional rim light** on the sun-facing Fresnel edge, tinted by the sun
  color; Rim Strength and Rim Width controls. The HAIR preset gets an automatic
  angel-ring boost.
- Sun direction/color are pushed into every tinted material and refreshed on
  `frame_change_post`, without rebuilding materials.
- Gate render checks for the toon terminator and rim light, plus sun direction and
  hair rim boost.

### Changed
- Shadow Tint group upgraded with `Sun Direction`, `Sun Color`, `Toon Strength`,
  `Terminator Sharpness`, `Rim Strength` and `Rim Width`; the interface is
  extended without clearing, so existing texture links survive upgrades.
- Defaults: Cel Shadow 0.75, Terminator 0.035, Rim Strength 0.45, Rim Width 0.4.
- `materials.py` now registers a frame handler for the sun direction.

## 0.4.0 — 2026-10-19
### Added
- **Sun disk** in the world gradient, aligned with the sun direction; size and
  strength controls.
- **Anime clouds**: two-layer procedural noise, projected sky colors (shadow /
  horizon / sun), horizon fade and amount/scale controls.
- **Anime Ink Lines**: thin depth-discontinuity outlines composited with a dark
  shadow-tint color; strength and size.
- **Sakura Spring** and **Twilight Dusk** atmosphere presets.
- **Custom palette colors**: sky, horizon, sun and shadow overrides per scene,
  exposed in the Scene and Sidebar N panels.
- Gate coverage: sun direction/disk strength, cloud toggle, ink node + pixel test,
  custom colors and preset restore.

### Changed
- World gradient group upgraded (sun disk + clouds) with `ald_build = 3`.
- Sun/cloud frame updates run on `frame_change_post` so animated transforms are
  evaluated before reading sun matrices.
- Shadow tint colors for the new presets are normalized multiplier hues.
- Look-dev renders all six palettes in a 3×2 sheet.

## 0.3.2 — 2026-10-19
### Added
- **Sidebar N panel** (`VIEW_3D > Anime Look`) with palette, world, shadow tint,
  compositor toggles/sliders, build/remove and viewport compositor.
- Gate checks for in-place parameter updates, God Rays node creation with the sun
  behind the camera, and the multiplicative shadow tint.

### Changed
- **Slider performance**: float properties now call `compositor.update_params()`
  and rewrite only node sockets. Booleans still rebuild the topology. Kuwahara,
  halation, dispersion, light wrap, God Rays and depth range update in place.
- **Shadow tint is multiplicative**: `MULTIPLY` preserves texture detail in
  shadowed areas; palette shadow colors are normalized multiplier hues.
- **God Rays node is always created** when enabled; if the sun is behind the
  camera at build it starts at `(0.5, 0.5)` with strength 0 so the frame handler
  can bring it in later.
- Halation strength range corrected to 0–1 to match the Glare socket.

## 0.3.1 — 2026-10-19
### Added
- God Rays **Size** control.
- God Rays live refresh on frame change: the Sun Position follows the camera and
  sun during animation; the node is muted (strength 0) when the sun goes behind
  the camera and restored when it comes back.
- **Emission** material preset (neon surface) with Emission Color/Strength; other
  presets explicitly reset emission strength.
- `RECAP.md`: an Italian end-to-end recap of the add-on.

### Changed
- Sun Beams defaults: 6 iterations, fade 0.95.
- Version 0.3.1.

## 0.3.0 — 2026-10-19
### Added
- **God Rays**: optional Sun Beams glare placed at the sun's projected screen
  position, with a strength control. The node is skipped when the sun is behind
  the camera.
- **Shot markers**: opt-in per-shot palette changes from timeline markers named
  `ALD:<PALETTE>`; the `Mark Shot` operator writes/updates the marker at the
  current frame.
- **Material presets**: Skin, Hair, Fabric and Metal, assigned to selected
  objects and integrated with the shadow tint.
- Sub-panels for World & Shadows and Compositor Stack; the main panel keeps
  Atmosphere, Material Presets, build/remove and stack status visible.
- Gate coverage for the Sun Beams node and projected sun position, shot markers
  and material presets.

### Changed
- Version bump to 0.3.0; README, AGENTS.md and TECH_NOTES.md updated.

## 0.2.1 — 2026-10-19
### Added
- Auto Sun: applying a palette creates a tagged sun light when the scene has
  none; toggle in the World & Shadows panel section.
- Per-scene compositor stacks: each scene gets its own `ALD | Compositor Stack`
  group (suffixed when names collide), so multiple scenes no longer fight over
  one Render Layers node.
- Gate checks for auto-sun creation/toggle and for two scenes with independent
  stacks (build, Render Layers scene, removal isolation).

### Changed
- `ald.remove` unassigns the scene's stack and deletes it only when no other scene
  uses it; custom compositor groups are left untouched.

## 0.2.0 — 2026-10-19
### Added
- Palette-driven world gradient (sky / horizon / ground) with horizon offset and
  softness, built in the shared `ALD | World Gradient` node group.
- Shadow tint on scene materials through the shared `ALD | Shadow Tint` group:
  an AO mask mixes Base Color toward the palette shadow color.
- Light Wrap stage in the compositor stack, using a depth-derived silhouette
  mask, depth-discontinuity edges and blurred scene light.
- Gate checks for gradient, shadow tint insert/remove/restore, light wrap graph,
  rebuild idempotency and `bl_info` / manifest version consistency.
- Render-level gate checks: shadow tint and light wrap must change pixels, and the
  light wrap must stay edge-local.
- `preset_dev/lookdev.py` renders all four palettes on a fixed scene and builds a
  contact sheet for look development.

### Changed
- `ald.build` and `ald.apply_palette` also sync the shadow tint on scene materials.
- `ald.clear_shadow_tint` restores every touched Base Color link or value.
- Light wrap is composited as straight alpha, so the blurred image cannot leak
  over the whole frame.
- The world depth threshold follows the camera clip end (EEVEE writes
  `clip_end + 0.55`, Cycles writes ~1e10).
- Horizon softness now maps to a tighter falloff, so the sky gradient reads in a
  normal framing.
- Summer Noon is slightly less milky; Neon Night has a blue-violet zenith.

### Fixed
- World gradient colors are socket-driven (Mix + Map Range) instead of a static
  ColorRamp that ignored the palette.
- Light wrap no longer blurs the whole image because of premultiplied alpha.
- Depth-based light wrap now detects object-on-object silhouettes, not only
  geometry against the world.

## 0.1.0 — 2026-10-19
- Initial skeleton: Scene settings, four atmosphere presets, compositor node-group
  stack (Glare, Kuwahara with depth mix, Lens Distortion), operators and Scene panel.
- Headless gate `preset_dev/verify.py`.
