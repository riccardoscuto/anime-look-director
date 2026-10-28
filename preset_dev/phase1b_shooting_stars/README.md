# Phase 1B - Shooting Stars Visual Assessment

- Status: **VISUAL REVIEW PENDING**
- Suggested decision: **IMPROVEMENTS REQUIRED**
- Branch: `phase-1b-shooting-stars` (from `master` `63ffa29`, Phase 1A merged)
- Code: **not modified**; shader, properties and operators are the Phase 1A
  code already merged.
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
