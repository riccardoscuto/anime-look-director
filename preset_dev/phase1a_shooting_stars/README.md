# Shooting Stars - Phase 1A technical gate

- Status: **TECHNICAL REVIEW PENDING**
- Branch: `phase-1a-shooting-stars` (base `master` at `f1e5f97`, v2.62.0)
- Review date: 2026-10-28
- Authorization: Phase 1A only. No merge, no release, no Phase 1B.

This README supersedes the first gate report at `5c7e7ab`. The only corrected
statement is the lifecycle compatibility note (old projects do **not** lose the
last frame); the original measurements and images are retained.

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

## Temporal compatibility (verified on old and new code)

The old add-on was rendered from `master` in an isolated add-on path; the new
code from this branch. Same scene (NEON_NIGHT, clouds off, 960x540), event
azimuth 120 / elevation 40 / direction +35 / length 18.

| Case | old visible | new visible | added | removed | old count | new count |
|---|---|---|---|---|---|---|
| start 10, duration 24 | 11..33 | **10..33** | 10 | none | 23 | 24 |
| start 10, duration 2 | 11 | **10..11** | 10 | none | 1 | 2 |
| start 1, duration 24 | 2..24 | **1..24** | 1 | none | 23 | 24 |

Old logic: `phase = (frame - start) / duration`, alive when `0 < phase < 1`;
first visible `start + 1`, last visible `start + duration - 1`, count
`duration - 1`. New logic: alive when `start <= frame < start + duration`;
first visible `start`, last visible `start + duration - 1`, count `duration`.

**Correction:** the previous report said old projects gain the first frame and
lose the last. That was wrong. They gain the start frame; the last visible
frame is unchanged. No frame is removed. The earlier `metrics.json`/README
statement is superseded by this table and `temporal.json`.

## Legacy scene migration (verified)

A scene with **four events** was built and saved by the old add-on (marker 29):
different starts (10/15/20/25), durations (24/30/12/18), azimuths
(100..140), elevations (20..60), directions (-90..120), lengths (16..22),
colors and brightness. Old and new renders:

- marker **29 -> 30**; the World node is relinked to the new group, node tree
  valid; **4 events preserved**, no duplicates, no loss;
- starts, durations, azimuths, elevations, colors and the other properties are
  exactly equal before and after; save/reopen with the new code keeps 4 events
  and a **pixel-identical** frame-26 render;
- new wide render has **4 components** (3526 px); the old wide render has
  2 detectable components (436 px) only because the old trail is much fainter,
  but all four old per-event renders are present (131/167/96/42 px);
- start directions are identical (delta 0 deg). End directions change because
  `Direction` is now a true local bearing: Legacy A 14.824 deg, B 18.753 deg,
  C 11.315 deg, D 34.755 deg. This is the intentional SS-02 geometry change,
  not a data loss;
- **no automatic migration**: changing `Direction`/`Length` to reproduce the
  old distorted trajectory would preserve the defect and silently overwrite
  user values. Structural compatibility is complete; visual/trajectory
  compatibility is not claimed. Projects should review the direction after
  opening.

## Eevee OpenGL / Vulkan

Environment: Blender **5.1.2** (hash ec6e62d40fa9, built 2026-05-19
01:37:34), Windows 11 Pro 10.0.26200, NVIDIA GeForce RTX 3060 Ti, driver
32.0.16.1714 (2026-09-17); a Meta Virtual Monitor adapter is also present.

The earlier session had a transient OpenGL EEVEE context crash
(`EXCEPTION_ACCESS_VIOLATION` in `DRW_gpu_context_create`) that also hit a
**minimal scene with no add-on**; the master before-board was re-rendered on
OpenGL in this review (10 images, same metrics). The same no-add-on smoke and
the full gate now run on OpenGL. The full 37-check gate passes on both
backends:

| Check | OpenGL | Vulkan |
|---|---|---|
| Gate | **37/37 PASS** | **37/37 PASS** |
| Width p95 1/5/40/85 | 0.088/0.093/0.104/0.104 | 0.088/0.093/0.104/0.104 |
| Four events | 6776 px, 4 components | 6776 px, 4 components |
| Linear 5 deg / 40 deg | 7.573 / 7.576 | 7.569 / 7.576 |
| PNG diff | max 1/255, mean 0.0 | - |

Conclusion: the crash was environmental/transient, not caused by the Phase 1A
code; both backends are supported and produce matching geometry, positions and
brightness. No pixel-identity requirement is implied.

## Regression and performance

- Phase 1A gate: **37/37 PASS** on OpenGL and Vulkan.
- `verify.py`: **ALD GATE: PASS**; `verify_all.py`: **ALD ALL: PASS**.
- `audit_world.py`: **44/44 OK**; `phase6_technical.py`: **17/17 PASS**.
- `build_release.py`: **ALD BUILD: PASS** (package, no release published).
- Preview, four-event limit, persistence and scrubbing re-checked in the gate.

Same perf script on both checkouts, Eevee Vulkan, one event, 5 renders at
1280x720 and 3 at 1920x1080 (medians of 3 runs):

| Metric | master | Phase 1A |
|---|---|---|
| World nodes | 540 | 646 (+19.6%) |
| First group build | 1.191 s | 1.596 s (+0.41 s, once) |
| Apply palette | 1.8 ms | 1.5 ms |
| Render 1280x720 | 0.380 s | 0.370 s |
| Render 1920x1080 | 0.786 s | 0.772 s |

The extra nodes are the per-slot great-circle basis, arc and head glow; the
steady-state apply is unchanged and the render time is within noise.

## Evidence

- `board.png` - before/after at 1/5/40/85 deg, clouds off, frame 18.
- `board_horizon.png` - before/after horizon crossing, 3 deg, frame 33.
- `temporal.png` / `temporal.json` - old/new frames 9/10/11/33/34 and the
  interval table above.
- `migration.png` / `migration.json` - four-event legacy scene, marker 29->30,
  per-event pixels, endpoint deltas and persistence.
- `backend.png` / `backend.json` - OpenGL vs Vulkan at 1/5/40/85 and the
  environment data.
- `review.json` - combined temporal, migration and backend review.
- `lifecycle.mp4` - 25 frames (10..34), 960x540, 24 fps.
- `metrics.json` - 37 checks plus a `review` block with the three sections.

Commands:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
# 37-check gate; omit --gpu-backend to use OpenGL
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\phase1a_shooting_stars.py -- --out <dir>
# legacy temporal comparison (run on master and on the branch)
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\phase1a_temporal.py -- --out <dir> --tag <tag>
# legacy scene build (master) and migration (branch)
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\phase1a_migration.py -- --mode old --out <dir> --blend <legacy.blend>
& $blender -b --factory-startup --python-exit-code 1 `
  --python preset_dev\phase1a_migration.py -- --mode new --out <dir> --blend <legacy.blend>
```

## Compatibility and limits

- Start Frame now includes the start frame: a start-10/duration-24 event is
  visible **10..33** instead of 11..33. The last frame is unchanged; the count
  grows by one (duration - 1 -> duration). Start 1/duration 24 is 1..24 instead
  of 2..24; duration 2 is 10..11 instead of 11 only.
- `Direction` is a true local bearing; saved events keep their azimuth and
  elevation but can point differently (11..35 deg endpoint change in the
  four-event fixture). No automatic migration is applied; this is a
  compatibility note, not full visual compatibility.
- The viewport framing in Preview cannot be exercised headlessly; the camera
  non-destructiveness and the keyed-camera case are tested. Without a 3D
  viewport or in camera view the operator only moves the timeline and reports
  it.
- One palette (`NEON_NIGHT`), one camera position and clouds off for geometry.
  Four events are verified in one frame; a cloud-on aesthetic pass is Phase 2.
- No aesthetic verdict: the head is still the 2.60 style glow, pending 1B.
- OpenGL is verified now; the earlier failure is documented as an environment
  event. No outstanding backend risk is known.
