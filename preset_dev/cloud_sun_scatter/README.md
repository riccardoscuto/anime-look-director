# Cloud Sun Scatter (Phase 4)

Merged in the 2.63.0 release candidate; visual status approved.

Adds a **Sun Scatter** control under World Clouds > Lighting. It boosts the
sun-facing silver lining of the clouds; it is procedural World shading, not a
volumetric light-transport system.

## Behaviour

- `Cloud Sun Scatter` default `0.0`: the existing render is unchanged.
- Range `0.0..1.0`; the shader uses a forward-scattering lobe
  (`max(view·sun, 0)^4`) and applies the boost only to the silver-lining/rim
  mix. The cloud body and the clear sky are not replaced by a warm veil.
- The existing `Cloud Sun Lighting`, `Delta Gain` and `Rim Boost` remain the
  main directional controls. Use `Rim Boost` for a stronger silver lining.
- True cloud shadows / god rays require volumetrics; this is not that.

## Evidence

- `off_0.png`: Sun Scatter 0.0.
- `half_0_5.png`: Sun Scatter 0.5.
- `full_1_0.png`: Sun Scatter 1.0.
- `compare.png`: three-way contact sheet.
- `metrics.json`: pixel difference between 0 and 1: 4,140 pixels over 1/255,
  mean absolute 0.021, max 7 — a deliberate accent, not a global exposure
  change.
- `scatter.json`: requested/property values.

## Full feature-branch regression

- Phase 1B markers 29/30 -> **35**; events/properties/animation preserved.
- Phase 2 audit PASS (cloudless; marker 35).
- Phase 6 matrix **22 cells** regenerated; Sun Scatter 0 in the matrix.
- Phase 1A 37/37; UI 68/68; audit 44/44; Phase 6 technical 17/17;
  ALD ALL PASS; build PASS.

Render fixture: EEVEE, 960x540, GOLDEN_HOUR, CUMULUS, cloud amount 0.78,
sun elevation 12°, camera aimed at the sun.

## UI and marker

- New `ALD_Settings.cloud_sun_scatter` property, default 0.0.
- World group socket `Cloud Sun Scatter`; marker `35`.
- Scene Properties and View3D sidebar both show it in Lighting.

## Reproduce

```powershell
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\cloud_sun_scatter.py -- <out>
```
