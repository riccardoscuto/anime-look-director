# Shooting Stars - Phase 1A technical gate

Status: **TECHNICAL REVIEW PENDING**  
Branch: `phase-1a-shooting-stars` (base `master` at `f1e5f97`, v2.62.0)  
Authorization: Phase 1A only. No merge, no release, no Phase 1B.

## Defects fixed

| ID | Defect (Phase 0 audit) | Fix |
|---|---|---|
| SS-01 | Start Frame invisible; life `duration - 1` frames | `alive` is `start <= frame < start + duration`; progress uses `duration - 1`; 2-frame events are defined |
| SS-02 | Gnomonic distortion, `z=0.05` clamp, elevation-dependent thickness | Great-circle arc between start/end unit directions; angular thickness; no clamp; linear brightness separated from the sky |
| SS-03 | Add from a horizon camera placed a nearly invisible 5 deg event | Add uses the camera direction, keeps the start just above the horizon gate, flips a descending bearing, and warns for ground/clouds/no camera |
| SS-04 | Preview overwrote the working camera | Preview moves the timeline and rotates only the 3D viewport; the camera, its keyframes and its animation are untouched |
| SS-05 | Duplicate at four was silent | Duplicate reports the same 4-event warning as Add |

## Geometry

The World shader builds a great-circle arc between the start and end directions
from the existing four `StarN` slots. The slots `Start U/V` and `End U/V` now
hold azimuth/elevation in degrees. `Thickness` is an angular half-width in
radians, so the apparent thickness does not depend on the elevation. The
horizon gate fades the star below about 0.6 degrees. Clouds still attenuate the
star through the coverage mask; all geometry comparisons use clouds off.

`Direction` is now a bearing in the local tangent plane: 0 = horizontal,
+90 = up. This is a visible change for old projects (same one-frame rebuild as
the World group marker 30).

## Results (`metrics.json`, 37/37 PASS)

- Add from a horizon camera: elevation 1.00, direction +35,
  974 px at the creation frame (SS-03).
- Elevations 1/5/40/85: width p95 **0.088 / 0.093 / 0.104 / 0.104 deg**
  (ratio 1.18), angular span **8.1..18.9 deg** (trail + head), head error
  **<= 0.05 deg**.
- Horizon crossing: width p95 0.069 deg; the visible part stops at the horizon
  (along max 8.63 deg), no arc or loop.
- Lifecycle (start 10, duration 24): frame 9 = 0 px, 10 = 1277 px,
  33 = 2224 px, 34/35 = 0 px; head at the start within 0.05 deg.
- Duration 2: 9 = 0, 10 = 1277, 11 = 2224, 12 = 0 px.
- Four events in one frame: **6776 px, 4 components** (112/107/105/101 cells
  at 4x downsample), each head at its expected screen position.
- Remove the second of four: the other three properties are unchanged and the
  render has 3 components.
- Duplicate at four: CANCELLED with the 4-event warning; at three it copies the
  properties and offsets the start by +12 frames.
- Preview on a keyed camera: frame 18, camera matrices at frames 1/20/60
  unchanged.
- World anchor under a 15 deg camera yaw: 0.01 deg.
- Save/reopen: 4 events and a pixel-identical frame 20 render.
- FULL_COPY duplicate: separate World, originals unchanged, edited copy differs.
- Scrubbing: frame 33 pixel-identical after seeking 33 -> 10 -> 18 -> 33.
- Linear brightness (EXR, clouds off): peak **7.569 at 5 deg vs 7.576 at
  40 deg** (ratio 1.001). The display difference (0.58 vs 0.91) is the bright
  horizon sky behind the star, not a geometry attenuation.

## Performance vs `master`

Same script on both checkouts, Eevee Vulkan, one event, 5 renders at 1280x720
and 3 at 1920x1080 (medians of 3 runs):

| Metric | master | Phase 1A |
|---|---|---|
| World nodes | 540 | 646 (+19.6%) |
| First group build | 1.191 s | 1.596 s (+0.41 s, once) |
| Apply palette | 1.8 ms | 1.5 ms |
| Render 1280x720 | 0.380 s | 0.370 s |
| Render 1920x1080 | 0.786 s | 0.772 s |

The extra nodes are the per-slot great-circle basis, arc and head glow; the
steady-state apply is unchanged and the render time is within noise. The
one-time build cost is not repeated per frame.

## Evidence

- `board.png` - before/after at 1/5/40/85 deg, clouds off, frame 18, camera
  aimed at the event start.
- `board_horizon.png` - before/after horizon crossing, 3 deg, direction -20,
  frame 33.
- `lifecycle.mp4` - 25 frames (10..34), 960x540, 24 fps, clouds off.
- `metrics.json` - raw checks, masks, EXR values and render paths.

Commands:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\phase1a_shooting_stars.py -- --out <dir>
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase1a_perf.py
```

The final gate run used `--gpu-backend vulkan` because the machine's OpenGL
Eevee context crashed during the session; the World output and checks are the
same. The boards were rendered before that crash with the OpenGL backend; the
gate was re-run on Vulkan with identical measurements.

## Compatibility and limits

- Start Frame now includes the start frame: a start-10/duration-24 event is
  visible 10..33 instead of 11..33. Old projects gain one visible frame at the
  beginning and lose one at the end; the documented default is the new
  behavior.
- `Direction` is a true local bearing; old trajectories can point slightly
  differently after the marker-30 rebuild.
- The viewport framing in Preview cannot be exercised headlessly; the camera
  non-destructiveness and the keyed-camera case are tested. Without a 3D
  viewport the operator only moves the timeline and reports it.
- One palette (`NEON_NIGHT`), one camera position and clouds off for geometry.
  Four events are verified in one frame; a cloud-on aesthetic pass is Phase 2.
- No aesthetic verdict: the head is still the 2.60 style glow, pending 1B.
