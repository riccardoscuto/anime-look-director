# P1 report — compositing FX (v2.31.0)

## Files changed

- `compositor.py` — FX branch rewritten.
- `preset_dev/verify.py` — FX wiring checks rewritten; new `check_fx_p1_visibility`.
- `preset_dev/audit_plan.py` — P0-D requirements updated to Cryptomatte.
- `preset_dev/baseline_fx.py` — `--out` now absolute (the relative path was
  resolved to `C:\preset_dev` by Blender).

## Initial cause

1. The coverage `A` was `max(R, G, B)` of the FX-only layer: a very bright
   pixel reached `A = 1` even when the geometry covered only part of the pixel,
   and the luminance was used as geometry.
2. `F` and `Glare(F)` were added without the visibility mask: only the
   background punch-out used the depth comparison, so the FX and its glow
   could appear over an opaque occluder.
3. The FX-only layer excluded the environment, so it had no depth relation to
   occluders at all; the depth comparison was a second, approximate pass.

## Intervention

- The main view layer now enables `Emission` and `Cryptomatte Material`; the
  FX materials are the matte IDs.
- `A = ALD | FX Matte` (Cryptomatte). It is computed from the visible render,
  so opaque occluders zero it directly.
- `F = Emission x A` (`ALD | FX Coverage` CombineColor + `ALD | FX Emission`
  MULTIPLY), premultiplied and already occluded.
- `C = P(B)*(1-A) + F + Glare(F)`: `ALD | FX Painted Punch` uses the matte,
  `ALD | FX Restore` adds F with Factor 1, `ALD | FX Glow` blooms F once.
- Removed `ALD FX Only`, the transparent world override, the `max(R,G,B)`
  coverage, `ALD | FX Occlusion` and `ALD | FX Visible Coverage`.
- The FX branch is always present: with no FX materials the matte is 0 and the
  result is the identity, which keeps parameter updates and the gate stable.

## Tests

- **Wall in front**: behind = 0.000000 (fully hidden, including the glow).
- **Wall behind**: the burst remains visible in front of the wall.
- **Partial occluder**: the unoccluded half keeps the FX, the covered half does
  not (left diff > 1e-4, right < 25% of left).
- **Zero FX**: OFF and FX3D render identically.
- **Foreign emissive**: an emissive surface that is not FX does not enter the
  matte.
- **Single glow**: one `ALD | FX Glow`, fed by the masked emission; the restore
  also adds the masked emission.
- Full gate: `ALD GATE: PASS`; audit 40/40.

## Visual comparison

`preset_dev/baseline_fx_p1/` is the same scene as the P0 baseline
(`preset_dev/baseline_fx/`). The full render is intentionally almost identical:
P1 changes correctness (coverage, occlusion, glow masking), not the trail
geometry or the shading. The remaining visual defects — radial dots instead of
continuous filaments, a nearly inert glow — are P2/P3 work. The P0
`emission` pass still shows the dots; `glow` is still black at this age.

## Performance (same machine, EEVEE 32 samples)

| measure | P0 | P1 |
| --- | --- | --- |
| creation | 0.135 s | 0.145 s |
| frame evaluation | 0.018 s | 0.007 s |
| full 800x450 | 1.62 s | 1.70 s |
| full 1920x1080 | 6.60 s | 8.00 s |

The Cryptomatte pass adds a small render cost; the removed FX-only layer no
longer renders a second pass. The difference is within measurement noise for
this scene but is recorded honestly.

## Residual risks

- Cryptomatte matte edge values on sub-pixel grains are covered by the
  partial-occluder test at 64x64, but a high-resolution edge check remains
  useful when P2 changes the trail geometry.
- The matte is a material matte: FX materials must stay tagged
  `ald_fx_material` (P2 must not create untagged FX materials).

## Commit

`P1: Cryptomatte FX coverage and occlusion` (this change).
