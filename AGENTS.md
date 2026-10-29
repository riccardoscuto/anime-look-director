# Anime Look Director — World Sky Edition

Blender add-on focused on **procedural anime skies** in the World shader. The
3D FX, Spatial Clouds, smoke and EXR pass systems were removed in v2.57.0.

## Target
- Blender **5.1.2** on Windows (compositor node-group API).
- Python 3.13 / NumPy inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **2.63.0**).

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

Phase 3 UI gate (on `phase-3-ui-cleanup`):
```powershell
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\phase3_ui.py
```
Expected: `PHASE3 UI {"status": "PASS", "failures": []}`. The render
invariance check is `preset_dev\phase3_invariance.py`.

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
  Clouds, Stars & Milky Way, Shooting Stars, Palette Customization,
  Materials & Shadows, Compositor, Advanced Settings. The View3D sidebar
  mirrors the same sections with the same drawing functions; the root panel
  holds the palette and the eight sub-panels are Atmosphere & Sun, World
  Clouds, Stars & Milky Way, Shooting Stars, Palette Customization, Materials
  & Shadows, Compositor and Advanced Settings.
- The compositor is inactive by default. Its panel distinguishes inactive,
  configured/render-disabled and active-in-render, reports the viewport
  preview state, never mistakes a user group for an ALD stack
  (`compositor.scene_stack`) and only enables on the explicit
  Enable Compositor action. The full controls are shown only for an ALD
  stack; the viewport operator is limited to the current 3D view.
- Seven original presets plus Soft Dawn, Blue Hour, Cloudy Afternoon, Stormy
  Sunset and Moonlit Night. All use the same World generator. Save as Custom
  copies the current colors into the custom fields without changing the preset.
- The first Phase 3 gate (Cumulus in daylight) is approved at 2.59.1; the
  sunset gate is approved at 2.59.1. The shooting-star gate is approved at
  2.60.1; its 2.63 Phase 1A reliability work is technical-only and has no
  aesthetic approval. Phase 5 (presets and compact UI) and Phase 6 (release
  matrix, technical gate, package) are complete at 2.62.0; 2.63.0 is the
  current release candidate on `master`.
- 2.63 work: Phase 0 legacy safety is complete (44/44 audit, 36/36 synthetic
  and 9/9 on a real v2.56.0 file); Phase 1 Cumulus baseline is complete at
  `preset_dev/phase1/` with the visual decision pending. The shooting-star
  Phase 0 audit is at `preset_dev/audit_shooting_stars/` (branch
  `audit/shooting-stars`, `85c8170`). Phase 1A is complete on
  `phase-1a-shooting-stars`: 37/37 technical checks and 5/5 interactive
  Preview checks, evidence in `preset_dev/phase1a_shooting_stars/`,
  **FINAL TECHNICAL REVIEW: PASS**; PR #1 is **merged to master** at `63ffa29`
  (Phase 1A technically complete). Phase 1B is merged at `fe685d5` (compact
  head, tapered tail, temporal envelope, marker 31). Phase 2 is complete and
  merged in 2.63.0: Sun Elevation -30..85, immediate World sync, sun disk
  1.0 deg / 4.0, ground-mask at the horizon, marker 32. Phase 3 UI cleanup is
  merged in 2.63.0: full sidebar mirror of Scene Properties, autonomous
  Shooting Stars, compositor states and grouped effects; 68 UI checks,
  pixel-identical render, World 719 / Compositor 31 nodes, marker 32; evidence
  in `preset_dev/phase3_ui/`. Phase 4 star/cloud look is merged in 2.63.0:
  thickness max 0.01 rad with a 0.012 rad head cap (marker 33), optional
  per-event `Curvature` with a sine bow and default 0 (marker 34), and
  `Cloud Sun Scatter` default 0 that boosts the sun-facing silver lining
  (marker 35). Evidence: `preset_dev/star_thickness/`,
  `preset_dev/star_curvature/`, `preset_dev/cloud_sun_scatter/`. 68 UI,
  37/37 Phase 1A, 44/44 audit, 17/17 Phase 6, Phase 1B markers 29/30 -> 35
  with events and animation preserved, Phase 2 audit, matrix 22 cells, ALD ALL
  and build PASS. Visual status: **APPROVED for 2.63.0**. The 12-preset review
  is on `feature/preset-identity`; status **IN REVIEW - not approved**;
  see `preset_dev/preset_identity/README.md`. 2.63.0 is not published/tagged.
- Phase 6 evidence is `preset_dev/phase6/contact.png` (22 cells),
  `metrics.json` and `technical.json` (17/17). The technical gate covers
  idempotence, determinism, wind, star isolation, ownership, persistence and
  cost. Stratocumulus and Cirrus are documented but have no individual
  aesthetic sign-off; Cumulus is the approved family.
- A field edit calls `_on_star` and refreshes the World immediately; Add
  places the event in the current camera direction at the current frame, and
  Preview moves the timeline to 1/3 of the event and frames it in the 3D view
  without changing the camera.
- The star head is a short bright band, the tail is a thin tapered line and
  the color is cool white by default, matching the starfield.
- Shooting stars are persistent `ALD_ShootingStar` events: start frame,
  duration, azimuth/elevation, direction, angular length, `Curvature`, trail,
  thickness, brightness, glow and color. Start Frame is the first visible frame
  and Duration the exact count (progress uses `duration - 1`; a 2-frame event
  is valid). Existing events start one frame earlier after the marker-30
  rebuild; their last visible frame is unchanged. The World shader evaluates
  four fixed slots as great-circle arcs between the start/end unit directions
  (azimuth/elevation in degrees) with a frame driver. `Curvature` is a signed
  sine bow along the path normal; 0 keeps the great-circle arc. Thickness is an
  angular half-width, independent of elevation, with no gnomonic `z` clamp;
  the UI max is 0.01 rad and the head radius is capped at 0.012 rad. `Direction`
  is a local bearing (0 horizontal, +90 up). Add uses the camera direction with
  a 1-degree horizon floor and flips a descending bearing; Preview never writes
  the camera. The event list is capped at 4 and survives save/reload.
- The sky accent is a broad band (`From Max 0.20`), not a narrow stripe.
  Keep the dusk/night transition smooth; the Phase 2 before/after is in
  `preset_dev/sky/contact.png`.
- `_sun_fade` hides the Sun disk below the horizon and fades the glow by
  about -7 degrees; `update_sun_controls` uses the same gates.
- The World is a node group (`ALD | World Gradient`; marker 32 on Phase 3,
  marker 35 on the Phase 4 feature branch) with `Ground`, `Horizon`, `Mid Sky`,
  `Zenith` plus Sun, clouds, stars, Milky Way, contrails and sky accent.
  Palette colors are wired through group sockets, never baked into ColorRamp
  stops.
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
- `Atmosphere & Sun`, `World Clouds` (Distribution / Shape / Lighting /
  Animation), `Stars & Milky Way`, `Shooting Stars` (Timing / Trajectory /
  Appearance), `Palette Customization`, `Materials & Shadows`, `Compositor`
  (Light Effects / Stylization / Atmospheric Post Effects), `Advanced
  Settings` (reversible versus destructive actions).
- Shooting Stars Trajectory includes `Curvature`; Appearance `Thickness` is
  capped at 0.01 rad. World Clouds Lighting includes `Sun Scatter` (default
  0.0), a sun-facing silver-lining boost; it is not volumetric shadowing.
- The compositor panel is state-driven: inactive with only Enable Compositor,
  configured/render-disabled with the Use in Render toggle, active with the
  effects, and a read-only viewport preview line. Sun Beams lives only here.
- `ALD_UL_shooting_stars` is the event list; the four-event cap and operators
  are unchanged.
- The View3D sidebar mirrors the Scene Properties sections with the same
  drawing functions and open sub-panels; the root palette is shared.
- Panel icons must come from the real Blender 5.1 enum; `CLOUD` does not exist,
  `WORLD` does.

## Rules
- Do not introduce FX, Spatial Clouds, smoke or EXR-pass code again.
- Do not make the compositor mandatory: applying a palette must work without
  `Build Stack`. Never auto-enable it.
- Identify an ALD stack only through `compositor.scene_stack`; a user
  compositor group is never modified, removed or presented as ALD.
- Never silently modify a user World, HDRI, Sun or material. Use snapshot.
- Palette changes and shots go through `look.apply`/`look.apply_world`.
- Float slider updates use `compositor.update_params`; rebuild only for
  topology/toggle changes.
- Preserve the four-zone gradient and the visible/ambient separation.
- Prefer one capability at a time and a before/after render for every look
  change. Numeric PASS is not aesthetic approval.
- Never save the user's `.blend` unless asked.
- `bl_info`, manifest, README, CHANGELOG and version tags stay aligned.
