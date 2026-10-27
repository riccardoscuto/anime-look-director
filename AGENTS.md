# Anime Look Director — World Sky Edition

Blender add-on focused on **procedural anime skies** in the World shader. The
3D FX, Spatial Clouds, smoke and EXR pass systems were removed in v2.57.0.

## Target
- Blender **5.1.2** on Windows (compositor node-group API).
- Python 3.13 / NumPy inside Blender. No external dependencies.
- GPL-3.0-or-later. Version in `bl_info` and `blender_manifest.toml` must match
  (currently **2.59.1**).

## Verify
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify_all.py
& $blender -b --factory-startup --python preset_dev\build_release.py
```
Expected: `ALD GATE: PASS`, `ALD ALL: PASS`, `ALD BUILD: PASS`.

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
- `operators.py`, `properties.py`, `panels.py` — UI and actions.
- `preset_dev/verify.py` — World gate; `world_fixture.py` lifecycle;
  `audit_world.py` source audit.

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
- The first Phase 3 gate is Cumulus in daylight. Do not start sunset or
  Stratocumulus/Cirrus work until that image is approved.
- The sky accent is a broad band (`From Max 0.20`), not a narrow stripe.
  Keep the dusk/night transition smooth; the Phase 2 before/after is in
  `preset_dev/sky/contact.png`.
- `_sun_fade` hides the Sun disk below the horizon and fades the glow by
  about -7 degrees; `update_sun_controls` uses the same gates.
- The World is a node group (`ALD | World Gradient`, marker 28) with
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
- Old `.blend` files are **never cleaned automatically**. The Legacy ALD Data
  panel offers:
  - **Disable** — hide old `ald_fx`, `ald_clouds`, `ald_smoke` collections
    (reversible);
  - **Remove** — delete those collections and their objects (explicit, not
    reversible from the panel).
- Old FX/cloud properties are no longer registered: they are ignored,
  have no UI or handlers, and disappear when the file is saved. See
  `MIGRATION_2_57.md`.

## UI
- Scene properties parent: palette, Apply, material presets, stack actions.
- `World & Shadows`: World, Sun, clouds, stars, custom colors, Shadow/Cel/Rim.
- `Compositor Stack`: optional toggles and camera override.
- `Legacy ALD Data`: explicit disable/remove of old collections.
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
