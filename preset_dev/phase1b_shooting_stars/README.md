# Phase 1B - Shooting Stars Visual Assessment

- Status: **TECHNICAL PASS - VISUAL REVIEW PENDING** (candidate implemented)
- Historical assessment: **IMPROVEMENTS REQUIRED** (kept below)
- Branch: `phase-1b-shooting-stars` (from `master` `63ffa29`, Phase 1A merged)
- Code: appearance-only candidate in `palette.py`; geometry, properties and
  operators are the Phase 1A code already merged.
- Scope: appearance only. Geometry SS-01..SS-05, clouds, Sun, atmosphere,
  materials and compositor are untouched.

## Method and parameters

The same fixture was rendered on the historical `v2.60.1` tag and on Phase 1A
(`master` `63ffa29`):

- 1280x720, Eevee, 32 samples, AgX, look None, exposure 0, gamma 1;
- 32 mm camera at (0, -12, 3), clip 0.1..1000;
- clouds off, no compositor;
- event: az 120, elevation 1/5/40/85, direction +35, length 18, start 10,
  duration 24, trail 0.55, thickness 0.0018, brightness 3, glow 0.8, cool
  white;
- four-event scene at frame 20 with distinct trajectories/colors;
- twilight: `TWILIGHT_DUSK`, elevation 20; night: `NEON_NIGHT`, elevation 40.

Equivalent comparisons use the same camera, lens, resolution, exposure and
color management. The historical 2.60.1 is a baseline, not the target: it is
too faint/linear. The target is the schematic panel in `board_head.png`,
explicitly separate from the generated renders.

## Boards and animation

- `board_elevations.png` - 2.60.1 vs 1A at 1/5/40/85 deg, frame 18.
- `board_lifecycle.png` - frames 10/13/18/25/32/33/34, both versions.
- `board_context.png` - night, twilight and four events.
- `board_head.png` - head crop, 2.60.1 crop, target schematic and measured
  facts.
- `lifecycle_current.mp4` - 1A, 24 frames 10..33 at 24 fps; the
  immediately-after frame 34 is in `board_lifecycle.png`.
- `lifecycle_2601.mp4` - 2.60.1, same 24-frame range, for comparison.
- `phase1b_metrics.json` - parameters, shader facts and the decision.

## Five visual criteria

### 1. Head

- **Observation:** the 1A head is a large, isotropic white ball, ~0.7-0.9 deg
  across, while the trail is ~0.21 deg wide. It dominates both the single-event
  and four-event frames and reads as a comet/planet, not an anime shooting
  star.
- **Cause (verified):** `head_radius = (2 + 2*glow) * thickness`; at glow 0.8
  and thickness 0.0018 rad this is 0.371 deg radius (0.742 deg core), with a
  further exponential halo. `head_boost = glow + 1` gives a peak 2x the trail
  near the head. The head is centered on the trail end, so the trail enters a
  sphere rather than a small core.
- **Target:** small bright core, roughly 1.4-1.8x the trail full width at the
  visible edge, with a compact halo and a short blend into the trail.

### 2. Trail

- **Observation:** the trail is continuous and smooth; no artificial segments
  or irregular edges were found. The full width is constant over most of the
  visible length. The tail ends in a blunt, thin cap: the last part does not
  fade to zero, so the trail looks cut off.
- **Cause (verified):** `tail_fade = 0.35 + 0.55*fade` and
  `taper = 0.25 + 0.75*fade`; at the tail end (`fade=0`) the tip keeps 35%
  brightness and 25% width. The `along` gate ends at the same point, producing
  a hard cap.
- **Target:** continuous taper to near zero width and intensity; soft tip.

### 3. Movement

- **Observation:** the head advances smoothly along the great circle; the tail
  grows continuously. No jumps, loops or discontinuous segments in the
  24-frame sequence.
- **Temporal envelope:** the event appears at full brightness at the start
  (a head-only ball at frame 10) and disappears abruptly after frame 33; frame
  34 is empty. There is no fade-in or fade-out.
- **Cause (verified):** `progress` is linear and `alive` is binary; no life
  fade multiplier exists. The geometry is correct and must not change.

### 4. Contrast with the sky

- **Night:** high legibility; the white head is almost overexposed and the
  thin trail is clear.
- **Twilight:** the head is clearly readable, the trail is visible but lower
  contrast; the oversized head dominates the scene.
- **Horizon (1 deg):** the head remains a white ball against the bright
  horizon; the trail is thin and low contrast, though visible. The old 2.60.1
  horizon image is distorted by the retired gnomonic clamp and is not an
  aesthetic target.
- **Conclusion:** the main contrast problem is the head's overexposure and
  size, not the trail color. A smaller head with a small core should improve
  the horizon/twilight balance; the trail may need a modest body lift.

### 5. Composition

- **Single event:** the ball-and-line silhouette is unbalanced; the head
  carries most of the visual weight.
- **Four events:** the four trails are distinct and readable, but four large
  white balls dominate the frame and look like comets/fireflies. No trail
  overlap or confusion in this fixture.
- **Target:** reducing the head restores the shooting-star silhouette and
  makes the four-event composition read as streaks, not balls.

## Defects and proposed corrections (not implemented)

| # | Effect | Conditions | Cause | Proposed correction | Risk |
|---|---|---|---|---|---|
| 1 | Spherical, oversized head | All elevations; worst at twilight/horizon and with four events | Verified: head radius factor 3.6x thickness; boost 1.8 | Reduce head radius to ~1.4-1.8x thickness; reduce boost to ~1.2-1.5x trail peak; keep a small bright core and a compact halo | May become too faint at 1 deg/twilight; test before/after |
| 2 | Blunt tail cap | All frames with a visible trail | Verified: 35% brightness and 25% width at the tip | Fade tail brightness and width to ~0 at the tip over the last 15-20% | Shorter perceived trail; calibrate |
| 3 | Abrupt appearance/disappearance | Start and end of every event | Verified: binary `alive`; no temporal fade | Add a short, bounded life envelope: fade in over 1-2 frames, fade out over the last 2-3 frames, keeping a nonzero value at the first and last visible frames | Must not violate SS-01 (first/last frames remain visible) |
| 4 | Head/trail contrast imbalance | Twilight and horizon | Consequence of #1 (peak 2x, large area) | After #1, modestly lift the trail body (e.g. 0.9 -> 1.0 of brightness) only if the comparison still needs it | Do not make the trail a laser; keep the taper |
| 5 | Four-event visual weight | Four simultaneous events | Consequence of #1 | No separate change; verify after the head reduction | None beyond #1 |

No defect was found in the trajectory, continuity or elevation independence.

## Proposed candidate (for approval only)

A single, circumscribed **appearance pass** on the World star shader:

1. Head: replace the isotropic large glow with a small bright core + compact
   halo. Suggested range: head radius `(0.8 + 0.8*glow) * thickness` (1.44x at
   glow 0.8) instead of `(2 + 2*glow) * thickness` (3.6x); head peak
   `(0.8 + 0.6*glow)` instead of `(glow + 1)`.
2. Tail: `tail_fade` and `taper` from `0.35/0.25` at the tip to a smooth
   ~0.05/0.05, with a smoothstep near the tip; keep the head-side values.
3. Temporal: bounded fade-in/out multiplier; first and last visible frames
   keep a nonzero floor so SS-01 still passes.
4. Optional trail body lift only if the new comparison shows low contrast at
   the horizon/twilight.

The candidate changes appearance only: no geometry, operator, property,
cloud, Sun, atmosphere, material or compositor changes. The World group marker
would need a rebuild marker on implementation; version remains 2.62.0 until a
separate release authorization.

## Performance and compatibility impact

- Expected cost: a few additional math nodes and a bounded envelope; no
  per-frame geometry or object work. Must be measured against the 1A baseline;
  no relevant regression accepted.
- Compatibility: visual change for all events; no data migration; saved
  events, timing, positions and SS-01..SS-05 invariants remain.
- Risks: head visibility at 1 deg/twilight, tail length perception, and the
  SS-01 first/last frame visibility. All require the existing 37-check gate
  plus the interactive Preview test after implementation.

## Limitations

- The target panel is a schematic design reference, not an anime frame; no
  external copyrighted reference was supplied.
- One camera, one palette pair, clouds off; cloud integration is a separate
  phase.
- The 2.60.1 lifecycle starts at frame 11 and 1A at frame 10; the comparison
  boards use the same frame numbers and note the difference.
- Aesthetic judgment is qualitative; the technical facts above are verified
  from the shader and the renders.

## Decision

**IMPROVEMENTS REQUIRED** - implement the circumscribed appearance candidate
only after approval. No code was changed in this assessment.

## Candidate implementation (authorized)

Implemented after the assessment, appearance only; geometry SS-01..SS-05 and
the World trajectory math are unchanged.

### Changes

- **Head:** `head_radius = (0.8 + 0.8*glow) * thickness` (0.149 deg at the
  default glow/thickness instead of 0.371 deg); a small core
  (`0.35 * head_radius` Gaussian) plus a compact halo; head boost
  `0.8 + 0.6*glow` (1.28 instead of 1.8). Nominal diameter 0.297 deg vs trail
  0.206 deg (1.44x); peak 3.84 vs 2.7 near the trail (1.42x).
- **Tail:** terminal 18% smoothstep; `tail_fade` and `taper` fall from 1.0 at
  the head to 5% / 6% at the tip. No hard cap; the arc length and trail
  parameter are unchanged.
- **Temporal envelope:** fade-in from 0.5 to 1.0 over the first 2 frames;
  fade-out from 1.0 to 0.3 over the last 3 visible frames; `alive` remains the
  SS-01 window. First and last visible frames stay non-zero.
- **Marker 30 -> 31:** group topology changed; old marker-29 and marker-30
  scenes rebuild automatically.
- No new properties or panels; no changes to `Glow`, `Trail`, `Thickness` or
  `Brightness` semantics.

### Before/after evidence

- `candidate_elevations.png` - 1A vs candidate, 1/5/40/85 deg.
- `candidate_lifecycle.png` - frames 9/10/11/13/18/25/31/32/33/34.
- `candidate_context.png` - night, twilight, four events.
- `candidate_head_tip.png` - head crop 4x, tail-tip crop 4x, target, facts.
- `candidate_lifecycle.mp4` - 24 frames 10..33 at 24 fps.
- `candidate_metrics.json` - values, tests, markers, performance.
- `candidate_interactive.png`, `candidate_interactive_preview.png`,
  `candidate_interactive.json` - GUI Preview 5/5.
- `markers.json` - marker 29/30 migration with a keyed camera.
- `performance.json` - candidate vs master 1A.

Original 1B boards (`board_*`, `lifecycle_*`, `phase1b_metrics.json`) are
preserved unchanged.

### Test results

- Phase 1A gate: **37/37 PASS** on Eevee OpenGL and Vulkan.
- Interactive Preview: **5/5 PASS** (viewport, keyed camera, Properties, no
  camera, persistence at marker 31).
- `verify_all.py`: **ALD ALL: PASS**; audit **44/44**; Phase 6 **17/17**;
  build **PASS**.
- SS-01 render check (start 10, duration 24): f9 = 0 px, f10 = 149 px,
  f33 = 829 px, f34 = 0 px. Duration 2: f10 = 140 px, f11 = 802 px.
- Four events: 2214 px, **4 components**; every head at its expected
  position. The component connectivity uses 2x sampling instead of 4x because
  the thinner trail broke into a fragment on the coarse grid; the 4-event
  requirement and all thresholds are unchanged.
- Marker 29 and 30 scenes: 4 events preserved, properties and keyed camera
  animation equal before/after/reopen; marker becomes 31.
- Linear brightness 5/40 deg: 1.503 / 1.521 (ratio 1.012).

### Performance (Eevee Vulkan, medians of 3 runs)

| Metric | master 1A | candidate |
|---|---|---|
| World nodes | 646 | 718 (+11.1%) |
| First group build | 1.606 s | 2.016 s (+0.41 s, one-time) |
| Apply palette | 1.4 ms | 1.2 ms |
| Render 1280x720 | 0.3696 s | 0.3729 s (+0.9%) |
| Render 1920x1080 | 0.7725 s | 0.7758 s (+0.4%) |

The render delta is below 5%; the one-time build increase is documented and
is not a per-frame cost.

### Candidate limitations

- Visual approval is still required; this is not a final aesthetic sign-off.
- One palette pair and camera; clouds off. Twilight and 1 deg were checked,
  but a wider aesthetic pass remains future work.
- The target panel is a schematic, not an external anime frame.
- No merge, release, tag or version change. SS-01..SS-05 and the great-circle
  geometry are untouched.
