# Phase 2 - Atmosphere, Horizon and Sun Disk

- Status: **TECHNICAL PASS - VISUAL REVIEW PENDING**
- Branch: `phase-2-atmosphere` (from `master` `fe685d5`)
- Scope: cloudless World, no compositor, no cloud generator change.
- Marker: **32**.

## Method

1280x720, Eevee 32 samples, AgX, look None, exposure 0, gamma 1, clouds off,
no compositor. Two framings: 32 mm sun-facing for the four conditions and
50 mm second framing; the night uses a sky framing. The fixed-camera sky
matrix is also covered by `preset_dev/sky_baseline.py` / `preset_dev/sky/`.

Comparison cells: noon (`SUMMER_NOON`, 35 deg), golden (`AFTER_SCHOOL`,
4 deg), twilight (`TWILIGHT_DUSK`, -2 deg), night (`NEON_NIGHT`, -18 deg).

## Demonstrated issues

1. **Sun Elevation UI range:** the property stopped at **-5 deg**, while the
   night setup uses **-18 deg**. The slider could not represent the preset
   condition; setting -18 clamped to -5.
2. **Sun disk size/strength:** the default disk was **1.5 deg radius**
   (3 deg diameter) at strength 6, reading as a large white moon with no
   compact solar presence.
3. **Sun disk and horizon:** the disk was added after the ground gradient,
   so at a raised Horizon Offset it could remain drawn over the ground
   instead of being cut by the shifted horizon.
4. **World sync hardening:** the World disk update is now explicit when the
   Sun Elevation/Azimuth property changes. The demonstrated defect was the
   UI range; the explicit update prevents a one-frame stale value.

## Changes

- `sun_elevation` min **-5 -> -30 deg**, preserving the presets.
- Sun disk default **1.5 -> 1.0 deg radius**, strength **6 -> 4**.
- Sun disk masked by the gradient ground (`ground_blend`), so it is cut when
  it crosses the shifted horizon.
- `apply_sun_angles` updates the World controls immediately.
- World marker **31 -> 32**.
- No changes to the cloud generator, palettes, atmospheric gradient, Sun
  light, materials or compositor.

## Results

### Four conditions

`board_conditions.png` and `board_second.png` compare before (1.5/6) and after
(1.0/4) in both framings. Noon/golden no longer carry a large white disk; the
twilight/night gradients are unchanged. The 2A gradient was already smooth and
needed no change.

### Sun across the horizon

`board_sweep.png` covers +8..-8 deg. The disk is visible at +8/+4/+2/+0,
fades through -1 and is gone by -2; the wide solar glow remains. The disk is
no longer a 3 deg sphere. `phase2_metrics.json` records the max luminance and
the distance between the expected Sun direction and the brightest pixel
(about 20 px at +4 deg).

### UI and sync

`board_ui.png`:

- before: requested -18, property **-5.00**, actual **-5.00**, World disk
  **-5.00**;
- after: requested -18, property **-18.00**, actual **-18.00**, World disk
  **-18.00**.

A separate 10 deg sync probe shows both the lamp and the World disk at 10 deg
in both builds; the explicit update remains as hardening.

### Horizon controls

`board_offsets.png` covers -0.5/0/+0.5 at golden hour. The after disk is cut
by the raised horizon at +0.5; the before disk is still fully drawn above it.
`board_controls.png` shows distinct softness (0.15/0.5/0.9) and accent
(0/0.3/0.6) results; no cloud contamination.

### Night

The NEON_NIGHT night remains readable with stars and the Milky Way; no change
is needed. 2D is a verification pass.

## Tests

- Phase 1A gate: **37/37 PASS** on OpenGL and Vulkan.
- Interactive Preview: **5/5 PASS**.
- `verify_all.py`: **ALD ALL: PASS**.
- `audit_world.py`: **44/44 OK**.
- `phase6_technical.py`: **17/17 PASS**.
- `build_release.py`: **PASS**.
- Marker 29/30/31 scenes: 4 events, properties and keyed camera preserved;
  all reopen at marker **32**.

## Evidence

- `board_conditions.png`, `board_second.png` - four conditions, two framings.
- `board_sweep.png` - Sun across the horizon.
- `board_offsets.png` - Horizon Offset.
- `board_controls.png` - Horizon Softness and Sky Accent.
- `board_ui.png` - Sun Elevation UI before/after.
- `phase2_metrics.json` - before/after values, marker and test results.
- `phase2_markers.json` - marker 29/30/31 migration.

## Limitations

- The Phase 2A gradient is verified, not retuned: it was already smooth and
  free of the old accent stripe; no change is claimed.
- The sun disk size/strength is a **visual choice** pending approval; 1.0/4
  is the candidate, not a final aesthetic sign-off.
- One palette pair and one camera pair; clouds off; cloud integration is a
  separate phase.
- No release, tag, version bump or merge.

**Decision: TECHNICAL PASS - VISUAL REVIEW PENDING.**
