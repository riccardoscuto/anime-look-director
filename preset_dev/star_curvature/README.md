# Shooting star curvature (Phase 4)

Adds an optional per-event bend to the shooting-star path. The default is
`0.0`, so existing events and the original render are unchanged.

## Behaviour

- The path remains a great-circle arc at `Curvature 0`.
- A signed `Curvature` in `[-1, 1]` adds a sine-shaped offset along the path
  normal: maximum at the middle of the arc, zero at the start/end.
- The head and the trail use the same offset, so the star bends as one piece.
- Positive values bend the test path downward (toward the horizon in the
  sample framing); negative values invert the bow.
- The maximum bow is `0.35 * arc_length` at `|Curvature| = 1`.

## UI and data

- Trajectory group: `Curvature` after `Angular Length`.
- `ALD_ShootingStar.curvature`: default 0, range -1..1, saved with the event.
- World group socket `Star0..Star3 Curvature`; the four event slots are written
  by the Shooting Stars panel.
- World marker `34`; the group rebuilds once.

## Evidence

- `straight_0.png`: curvature 0, original great-circle arc.
- `curved_0_5.png`: gentle bend.
- `curved_1_0.png`: strong downward bow.
- `curved_-1_0.png`: opposite bow.
- `compare.png`: 2x2 contact sheet.
- `curvature.json`: requested/property values.
- `phase1a_metrics.json` / `phase1a.log`: Phase 1A gate on this branch;
  **37/37 PASS** with curvature defaults at 0.

## Full feature-branch regression

- Phase 1B markers: real marker-29/30 scenes reopen, rebuild to marker **35**,
  4 events and animation preserved (`phase1b_markers.json`, `phase1b.log`).
- Phase 2 audit: PASS with marker 35; cloudless Sun/horizon values sync.
- Phase 6 matrix: **22 cells** regenerated with the new shaders at default
  values (`phase6/contact.png`, `phase6/metrics.json`, `phase6/matrix.log`).
- UI: 68/68; audit 44/44; Phase 6 technical 17/17; ALD ALL PASS; build PASS.

Render fixture: EEVEE, 960x540, NEON_NIGHT, clouds off, one event at
azimuth/elevation 120/40, length 30 deg, trail 0.85, frame 20.

## Reproduce

```powershell
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\star_curvature.py -- <out>
```
