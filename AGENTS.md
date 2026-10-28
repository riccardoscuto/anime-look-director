# Anime Look Director — World Sky Edition

Blender add-on focused on **procedural anime skies** in the World shader. The
3D FX, Spatial Clouds, smoke and EXR pass systems were removed in v2.57.0.

## Target
- Blender **5.1.2** on Windows (compositor node-group API).
- Python 3.13 / NumPy inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **2.62.0**).

## Verify
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify_all.py
& $blender -b --factory-startup --python preset_dev\build_release.py
```
Expected: `ALD GATE: PASS`, `ALD ALL: PASS`, `ALD BUILD: PASS`.

Phase 6 release evidence and technical gate:
```powershell
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_matrix.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_technical.py
```
Expected: `P6 SHEET`, `ALD PHASE6 TECHNICAL 17/17 PASS`.

World-only visual baseline (Phase 0 evidence) and Phase 2 sky matrix:
```powershell
& $blender -b --factory-startup --python preset_dev\world_baseline.py -- `
  --out preset_dev\world_baseline\current --tag v2.57.0
& $blender -b --factory-startup --python preset_dev\world_sun_baseline.py -- `
  --out preset_dev\world_baseline\current\sun --tag v2.57.0
```

## Architecture
- `palette.py` — the four-zone World gradient, Sun, World clouds, stars,
  Milky Way, custom colors and the World shader node groups.
- `look.py` — effective palette: **camera override > ALD marker > scene**.
- `cameras.py` — per-camera palette override and evaluated transform refresh.
- `shots.py` — timeline markers (`ALD:<PALETTE>`); never writes the base palette.
- `materials.py` — optional Shadow Tint / Cel / Rim and material presets.
- `compositor.py` — optional general compositor stack (halation, painterly,
  light wrap, dispersion, sun beams, ink, aerial haze). Never required by the
  World.
- `identity.py` — persistent scene UUID (`ald_fx_id`, kept for compatibility).
- `ownership.py` — duplicate-scene repair: new identity and own World.
- `snapshot.py` — reversible removal of the ALD look.
- `legacy.py` - tag-based discovery and scene-local Disable/Restore/Remove for
  pre-2.57 FX, Spatial Clouds and smoke data.
- `operators.py`, `properties.py`, `panels.py` — UI and actions.
- `preset_dev/verify.py` — World gate; `world_fixture.py` lifecycle;
  `audit_world.py` source audit; `legacy_fixture.py` and
  `legacy_v256_check.py` legacy safety; `phase1_render.py` and
  `phase1_compare.py` Cumulus baseline.

## World invariants
- The three cloud families are one-hot group inputs `Cloud Cumulus`,
  `Cloud Stratocumulus`, `Cloud Cirrus`; `cloud_type` in the UI selects one.
  `family_flatness` reduces the vertical organization for Cumulus, raises it
  for Stratocumulus, and the Cirrus view is stretched along X/Y.
- `Cloud Breakup` erodes density before the threshold; `Cloud Detail` scales
  the border/body noise; `Cloud Vertical` lowers effective flatness; `Cloud
  Sun Lighting` scales the solar derivative; `Cloud Seed` offsets the field.
- Cumulus lighting adds a height tone (lower cloud darker) and a stronger
  solar body range (-0.030..0.004); the default Sun Lighting is 1.2.
- The Scene properties are the complete surface: Atmosphere & Sun, World
  Clouds, Stars & Milky Way + Shooting Stars, Palette Customization,
  Materials & Shadows, Compositor, Advanced Settings. The View3D sidebar is
  Quick Look (preset, Apply/Reset, Sun elevation, cloud type/coverage/wind,
  stars) plus one collapsed Advanced Sky panel; no compositor or material
  controls in the quick area.
- The compositor is inactive by default. Its panel shows Enable Compositor
  when no stack is assigned and the full controls only when active; the viewport
  state is reported as ALWAYS / CAMERA / DISABLED.
- Seven original presets plus Soft Dawn, Blue Hour, Cloudy Afternoon, Stormy
  Sunset and Moonlit Night. All use the same World generator. Save as Custom
  copies the current colors into the custom fields without changing the preset.
- The first Phase 3 gate (Cumulus in daylight) is approved at 2.59.1; the
  sunset gate is approved at 2.59.1. The shooting-star gate is approved at
  2.60.1; its 2.63 Phase 1A reliability work is technical-only and has no
  aesthetic approval. Phase 5 (presets and compact UI) and Phase 6 (release
  matrix, technical gate, package) are complete at 2.62.0; `master` carries the
  World Sky Edition.
- 2.63 work: Phase 0 legacy safety is complete (44/44 audit, 36/36 synthetic
  and 9/9 on a real v2.56.0 file); Phase 1 Cumulus baseline is complete at
  `preset_dev/phase1/` with the visual decision pending. The shooting-star
  Phase 0 audit is at `preset_dev/audit_shooting_stars/` (branch
  `audit/shooting-stars`, `85c8170`). Phase 1A is complete on
  `phase-1a-shooting-stars`: 37/37 technical checks, evidence in
  `preset_dev/phase1a_shooting_stars/`, **TECHNICAL REVIEW PENDING**. No merge,
  release or Phase 1B. No 2.63 release.
- Phase 6 evidence is `preset_dev/phase6/contact.png` (22 cells),
  `metrics.json` and `technical.json` (17/17). The technical gate covers
  idempotence, determinism, wind, star isolation, ownership, persistence and
  cost. Stratocumulus and Cirrus are documented but have no individual
  aesthetic sign-off; Cumulus is the approved family.
- A field edit calls `_on_star` and refreshes the World immediately; Add
  places the event in the current camera view and 1/3 into its life, and the
  Preview operator moves the timeline and aims the camera at the start.
- The star head is a short bright band, the tail is a thin tapered line and
  the color is cool white by default, matching the starfield.
- Shooting stars are persistent `ALD_ShootingStar` events: start frame,
  duration, azimuth/elevation, direction, angular length, trail, thickness,
  brightness, glow and color. Start Frame is the first visible frame and
  Duration the exact count (progress uses `duration - 1`; a 2-frame event is
  valid). Existing events start one frame earlier after the marker-30 rebuild;
  their last visible frame is unchanged. The World shader evaluates four fixed
  slots as great-circle arcs
  between the start/end unit directions (azimuth/elevation in degrees) with a
  frame driver; thickness is an angular half-width, independent of elevation,
  with no gnomonic `z` clamp. `Direction` is a local bearing (0 horizontal,
  +90 up). Add uses the camera direction with a 1-degree horizon floor and
  flips a descending bearing; Preview never writes the camera. The event list is
  capped at 4 and survives save/reload.
- The sky accent is a broad band (`From Max 0.20`), not a narrow stripe.
  Keep the dusk/night transition smooth; the Phase 2 before/after is in
  `preset_dev/sky/contact.png`.
- `_sun_fade` hides the Sun disk below the horizon and fades the glow by
  about -7 degrees; `update_sun_controls` uses the same gates.
- The World is a node group (`ALD | World Gradient`, marker 29) with
  `Ground`, `Horizon`, `Mid Sky`, `Zenith` plus Sun, clouds, stars, Milky Way,
  contrails and sky accent. Palette colors are wired through group sockets,
  never baked into ColorRamp stops.
- Visible sky vs ambient: `Light Path → Is Camera Ray` mixes the gradient with
  the full gradient for camera rays. Background Strength is 1.0 when the
  gradient is active.
- `Horizon Offset` shifts `Z - 0.22 * offset` for ground/sky/clouds/stars.
- Sun disk vectors are normalized before the dot product. `sun_toward` returns
  a tuple; use `identity.scene_id` for the owner tag.
- `ensure_sun` only reapplies the preset `sun_rotation` when the palette
  changes; user suns keep their rotation. A shared sun is never rotated by a
  scene copy.
- World clouds are a World-shader feature. Coverage, scale, flatness, wind,
  delta gain and rim boost are the supported controls.
- The legacy World fireworks and meteors are retired: their amounts are forced
  to 0. The new shooting-star system is a later phase.
- World clouds are shaded by a deterministic density field; the current form is
  `fBm macro + billow + Voronoi puff` with an envelope for the sunward fringe.
  Do not reintroduce an unmasked crown or a body base that washes the cloud.

## Persistent state and compatibility
- `identity.scene_id(scene)` is the persistent UUID; a duplicated scene gets a
  new one. `ownership.repair` copies the World if shared.
- `snapshot.ensure` runs before the first modification of World/Sun/materials.
  `snapshot.restore` restores the World (including the HDRI background link),
  the Sun, materials, render passes and the compositor. A shared World or Sun
  is left alone and the limit is reported.
- Old `.blend` files are **never cleaned automatically**. Legacy discovery is
  tag-based, never name-based: `ald_fx_collection`/`ald_fx_owner`,
  `ald_clouds`, `ald_smoke`, `ald_fx`, `ald_fx_anchor`, `ald_fx_ground`.
  The Legacy ALD Data panel offers:
  - **Disable** - exclude tagged collections in every view layer of the
    active scene only and store the previous visibility;
  - **Restore** - return the saved per-view-layer visibility;
  - **Remove Permanently** - list the planned collections/objects in a
    confirmation dialog, remove them only when scene-local and safe, and skip
    shared collections/objects or user children. Standalone tagged anchor and
    ground helpers are included in Remove.
  A user collection with an ALD-like name is never touched; a shared
  collection is never deleted.
- Old FX/cloud properties are no longer registered: they are ignored,
  have no UI or handlers, and disappear when the file is saved. See
  `MIGRATION_2_57.md`.

## UI
- Scene properties parent: palette, Apply, material presets, stack actions.
- `World & Shadows`: World, Sun, clouds, stars, custom colors, Shadow/Cel/Rim.
- `Compositor Stack`: optional toggles and camera override.
- `Legacy ALD Data`: explicit Disable/Restore and a confirmed Remove
  of old collections and standalone FX helpers.
- The View3D sidebar uses the same drawing functions as the Scene properties:
  `draw_world`, `draw_compositor`, `draw_shadows`.
- Panel icons must come from the real Blender 5.1 enum; `CLOUD` does not exist,
  `WORLD` does.

## Rules
- Do not introduce FX, Spatial Clouds, smoke or EXR-pass code again.
- Do not make the compositor mandatory: applying a palette must work without
  `Build Stack`.
- Never silently modify a user World, HDRI, Sun or material. Use snapshot.
- Palette changes and shots go through `look.apply`/`look.apply_world`.
- Float slider updates use `compositor.update_params`; rebuild only for
  topology/toggle changes.
- Preserve the four-zone gradient and the visible/ambient separation.
- Prefer one capability at a time and a before/after render for every look
  change. Numeric PASS is not aesthetic approval.
- Never save the user's `.blend` unless asked.
- `bl_info`, manifest, README, CHANGELOG and version tags stay aligned.
