# Shooting Stars — Phase 0 audit

Status: **AUDIT REVIEW PENDING**

Base: `master` at `f1e5f97` (v2.62.0). Work exists only on
`audit/shooting-stars`. The add-on code is **not modified**; this is a
read-only audit of the existing implementation.

## Method

Fixture: factory settings + add-on, `NEON_NIGHT`, Eevee 32 samples, AgX, no
compositor, 1280x720, 32 mm camera at (0, -12, 3). The events are created and
edited through the existing operators (`bpy.ops.ald.*`) and properties. Each
frame is compared with the same-camera, same-frame render with the events
disabled; the star mask is the pixel difference above 0.02. The video is
960x540, 25 frames, 24 fps.

## A. Lifecycle

Event: start 10, duration 24, azimuth 120, elevation 40, direction -35,
length 18, trail 0.55, thickness 0.0018, brightness 3.0.

| Frame | Star pixels | Max | Note |
|---|---|---|---|
| 8 | 0 | 0.00 | before |
| 9 | 0 | 0.00 | before |
| 10 | 0 | 0.00 | **Start Frame: invisible** |
| 11 | 39 | 0.82 | first visible |
| 12 | 74 | 0.82 | |
| 18 | 267 | 0.82 | mid |
| 32 | 476 | 0.83 | |
| 33 | 475 | 0.82 | last visible |
| 34 | 0 | 0.00 | **invisible (phase 1)** |
| 35 | 0 | 0.00 | after |
| 36 | 0 | 0.00 | after |

The shader computes `phase = (frame - start) / duration` and `alive` as
`phase > 0 and phase < 1` (strict). Consequently the Start Frame itself is
invisible, the first visible frame is **start + 1**, the last is
**start + duration - 1**, and the effective life is **duration - 1 frames**
(23 here). This is the off-by-one to decide on.

Forward, backward and manual playhead: frame 33 rendered in all three orders
is pixel-identical. The star time driver is stateless (`frame`), so scrubbing
does not accumulate state. **PASS.**

## B. Multiple events

- One, two and four events: each keeps its own azimuth, elevation, direction,
  length and timing; the events render independently.
- A fifth Add is **CANCELLED** with a warning (the 4-event cap is enforced).
- A Duplicate at four events is **CANCELLED silently**: no warning is
  reported.
- Removing the second event leaves the properties of the other three
  unchanged (verified list before/after).
- Duplicate copies the trajectory and adds **+12 frames** to the start; the
  copy appears later on the same path. Intended, but worth documenting.

## C. Positioning

- **Add from a horizon camera**: the event is placed at azimuth -17.19,
  elevation **5.0**; the rendered star is 76 px with max 0.15 (faint, partly
  behind the horizon clouds). The Add clamps the camera elevation to 5-80; a
  camera looking at the horizon therefore yields a near-invisible event.
- **Elevation 5**: 80 px, max 0.11. **Elevation 40**: 267 px, max 0.82.
  **Elevation 85**: 410 px, max 0.87, short star; the zenith orientation is
  usable.
- **Elevation 1** (below the shader's z clamp of 0.05, i.e. below about 2.9
  degrees): the star becomes a **curved arc** spanning a 99x248 px bbox
  (583 px), crossing the horizon/ground. The gnomonic clamp distorts both the
  trajectory and the width.
- The star's apparent width is in gnomonic units: it scales with the
  elevation, so the same event is much thinner/fainter near the horizon than
  at 40 degrees. This is the main cause of the Add/horizon defects.
- **Camera rotation**: the star moves in the frame but remains fixed in the
  World. Back-projecting the mask centroids gives 122.9/39.4 and 122.0/36.8
  degrees (the ~3 degree residual is the screen-space centroid of the
  projected tail, not a World move); the visual comparison confirms the
  anchor.
- Clouds occlude the stars through the existing `cloud_visibility` factor;
  the audit's horizon views include the NEON_NIGHT clouds.

## D. Preview

The Preview sets the frame to `start + duration // 3` (18 here) and
**overwrites the active camera's rotation** to look at the event start. It
does not restore the previous rotation. In the fixture the working camera
moved from (75, 0, 0) to (130, 0, -120) degrees: the current view is lost
unless the user undoes. The operator's label/description say it aims the
camera, so the behaviour is documented, but it is destructive on the working
camera. Not tested: an animated/keyed camera (the assignment would be
overwritten by the animation on the next frame change).

## E. Persistence and duplicated scenes

- Save/reopen with the event: 1 event after reload; the render at frame 26 is
  pixel-identical to the pre-save render (the star time driver and the group
  slots survive).
- `bpy.ops.scene.new(type='FULL_COPY')`: the World is **not shared**
  (`world_shared: false`), the events are copied, and editing the copy's event
  changes only the copy's render (`render_identical: false`). Independence
  holds for the full copy.
- Not tested: a linked/shared-World duplicate; the add-on's ownership repair
  path for that case.

## Defect matrix

| ID | Expected | Observed | Repro | Severity | Responsible |
|---|---|---|---|---|---|
| SS-01 | Start Frame visible; event alive for `duration` frames | Start invisible, first visible start+1, last start+`duration`-1, `duration`-1 frames | lifecycle frames | Medium | `_build_shooting_stars` (`alive` strict), `_apply_star_slots` |
| SS-02 | Constant shape/brightness at every elevation | 5 deg: max 0.11/80 px vs 0.82/267 px at 40; 1 deg: curved 99x248 px arc | elevation renders | High | `_build_shooting_stars` (thickness in gnomonic units), `_star_endpoints` (z clamp 0.05) |
| SS-03 | Add places a perceptible star in the current view | Horizon camera -> event at 5 deg, 76 px, max 0.15 | Add test | High | `ALD_OT_shooting_star_add` (5-80 clamp) + SS-02 |
| SS-04 | Preview does not alter the working camera | Active camera rotation overwritten, no restore | Preview test | Medium | `ALD_OT_shooting_star_preview` |
| SS-05 | The 4-event cap is communicated | Add warns; Duplicate at 4 is silently cancelled | multiple test | Low | `ALD_OT_shooting_star_duplicate` |
| SS-06 | Event independence and safe removal | 4 events independent; removal leaves the others unchanged; 5th Add blocked | multiple test | Pass | - |
| SS-07 | Playhead forward/backward/manual consistent | Frame 33 identical in all orders | playhead test | Pass | - |
| SS-08 | Persistence of events, colours, driver | 1 event after reload; render identical | save/reopen | Pass | - |
| SS-09 | Duplicated scenes independent | FULL_COPY: World not shared; edited copy renders differently | duplicate test | Pass | - |
| SS-10 | Stars anchored in the World under camera rotation | Star moves in frame, stays in the World (centroid back-projection within ~3 deg) | anchor test | Pass | - |
| SS-11 | Anime trail: head, tapered continuous tail, smooth fade | Tail fades 0.9 -> 0.35 then ends in a cap; width depends on elevation (SS-02) | lifecycle renders | Low (1B) | `_build_shooting_stars` |

## Evidence

- `contact_lifecycle.png` — frames 8, 10 (start, empty), 11 (first visible),
  18, 33 (last visible), 34 (after, empty).
- `contact_position.png` — Add at the horizon, elevation 5, elevation 1 (the
  distorted arc), elevation 85.
- `contact_multiple.png` — 1, 4 and 3 events after removal.
- `contact_preview_persistence.png` — Preview camera before/after, save/reopen,
  original vs duplicated scene.
- `lifecycle.mp4` — 25-frame 960x540 test sequence of the single event.
- `metrics.json` — raw per-frame pixels/bboxes, preview rotation, limit results,
  persistence and duplicate checks.

## Limitations

- The camera sees only one event in the multiple-event render; the other
  events are outside the 40-degree frame. Their independence is verified from
  the property list and the remove test, not from a single wide image.
- The anchor metric uses the screen-space centroid of the projected tail; its
  ~3 degree residual is a measurement limitation, not a World drift.
- The fixture uses `NEON_NIGHT` with clouds on; cloud occlusion affects the
  star visibility. Only one palette and one camera position were used.
- The animated/keyed camera case was not exercised.
- No timeline performance/scalability measurement beyond the stateless
  playhead check.
- Images are evidence for the audit, not an aesthetic verdict.

## Decision

No code was changed. The reproducible defects are SS-01 to SS-05; the event
independence, playhead, persistence, full-copy duplicate and World anchor
pass. The next step is the user's selection of the problems to fix in
Phase 1. Status: **AUDIT REVIEW PENDING**.
