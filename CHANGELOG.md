# Changelog

## 2.63.0 - 2026-10-29
World Sky Edition release candidate: legacy safety, atmosphere/Sun, full
View3D mirror, shooting-star look and cloud Sun Scatter. The 12-preset review
is in progress; the identity revision is on `feature/preset-identity`
(per-preset cloud seeds 17/43/71/97; final lighting/softness pass) and 2.63.0
is not published or tagged.

Phase 0: legacy ALD safety.

### Fixed
- Legacy discovery uses the historical tags (`ald_fx_collection`,
  `ald_fx_owner`, `ald_clouds`, `ald_smoke`, `ald_fx`, `ald_fx_anchor`,
  `ald_fx_ground`) instead of names.
- Disable is scene-local and per view layer, stores the previous visibility,
  and has a separate Restore. It no longer changes global collection flags.
- Remove lists the planned collections/objects, requires explicit confirmation,
  removes nested collections leaf-first, and skips collections/objects shared
  with another scene or linked to user data.
- Standalone tagged FX anchor and ground objects are included in Remove when
  scene-local.
- The main gate now exercises the new Disable/Restore/Remove path.

### Evidence
- `preset_dev/legacy_fixture.py` - 36/36 PASS.
- `preset_dev/legacy_v256_check.py` - 9/9 PASS on a real v2.56.0 `.blend`.
- `preset_dev/legacy/README.md`.
- Phase 1 Cumulus baseline: `preset_dev/phase1/` (v1.0.3 vs v2.62 native and
  calibrated coverage); technical PASS, visual review pending.

### Phase 1A - Shooting Stars

**FINAL TECHNICAL REVIEW: PASS** on `phase-1a-shooting-stars` (merge authorization pending; not merged).

#### Fixed
- SS-01: Start Frame is the first visible frame and Duration the exact visible
  count. Start 10 / duration 24 is visible 10..33, absent 9 and 34; duration 2
  is defined. The star head is at the start at progress 0.
- SS-02: the gnomonic projection and the `z=0.05` clamp are gone. Each event is
  a great-circle arc between the start/end unit directions; thickness is an
  angular half-width, independent of elevation. The star's brightness is
  separate from the sky and cloud attenuation.
- SS-03: Add uses the camera direction, keeps the start just above the horizon
  gate, flips a descending bearing into the sky, and warns when the camera is
  on the ground, there is no camera, or clouds may hide the event.
- SS-04: Preview no longer sets the camera rotation, location, keyframes or
  animation. It moves the timeline and frames the event in the 3D viewport when
  one is available; otherwise it reports the timeline-only behavior.
- SS-05: Duplicate at four events reports the same warning as Add; the limit
  stays at four.

#### Changed
- `Direction` is a bearing in the local tangent plane (0 = horizontal,
  +90 = up); it is a true angle, not the old skewed gnomonic vector.
- The World gradient marker is 30, so existing groups rebuild with the new star
  geometry.
- **Compatibility:** old projects gain the start frame; the last visible frame
  is unchanged (start + duration - 1), so the count grows by one. Trajectories
  can point differently because `Direction` is now a true local bearing; this
  is a compatibility note, not full visual compatibility.

#### Evidence
- `preset_dev/phase1a_shooting_stars.py` - 37/37 checks: 1/5/40/85 deg geometry,
  horizon crossing, lifecycle, duration 2, four events in one frame, duplicate,
  keyed-camera Preview, scene duplicate, removal, scrubbing, persistence and
  linear brightness.
- `preset_dev/phase1a_shooting_stars/board.png`, `board_horizon.png`,
  `temporal.png`, `migration.png`, `backend.png`, `interactive.png`,
  `lifecycle.mp4`, `metrics.json`, `review.json`.
- Technical gate on both Eevee OpenGL and Vulkan: **37/37 PASS**; the earlier
  OpenGL context crash also hit a no-add-on scene and was environmental.
- `preset_dev/phase1a_perf.py` - master 540 nodes / 1.191 s build /
  0.380 s at 720p; Phase 1A 646 nodes / 1.596 s build / 0.370 s at 720p.
- Interactive Preview smoke test in a Blender 5.1.2 GUI: 5/5 PASS
  (viewport, keyed camera, Properties, no camera, persistence).
- Technical status: **FINAL TECHNICAL REVIEW: PASS**; PR #1 merged to
  `master` at `63ffa29`. No release.

### Phase 1B - Shooting Stars appearance candidate

Appearance candidate authorized after the visual assessment; no geometry,
operator or property changes.

#### Changed
- Head: radius `(0.8 + 0.8*glow) * thickness`, small core plus compact halo,
  boost `0.8 + 0.6*glow`; no isolated luminous sphere.
- Tail: terminal 18% smoothstep, brightness/width down to ~5% at the tip.
- Temporal envelope: fade-in 0.5 -> 1 over two frames, fade-out 1 -> 0.3 over
  the last three visible frames; SS-01 first/last frames remain visible.
- World gradient marker 30 -> 31; marker-29 and marker-30 scenes rebuild
  without losing events, properties or keyed camera animation.
- Component connectivity test samples at 2x instead of 4x; requirements and
  thresholds unchanged.

#### Evidence
- Phase 1A gate **37/37** on OpenGL and Vulkan; interactive Preview **5/5**;
  `verify_all` PASS; audit **44/44**; Phase 6 **17/17**; build PASS.
- SS-01 render: f9 0, f10 149, f33 829, f34 0; duration 2: 140 / 802.
- Performance: 646 -> 718 nodes, build 1.606 -> 2.016 s once, 720p +0.9%,
  1080p +0.4%.
- `preset_dev/phase1b_shooting_stars/` candidate boards, video, metrics,
  markers and performance.
- Status: **VISUAL APPROVED** and merged to `master` at `fe685d5`
  (PR #2); no release.



### Phase 2 - Atmosphere, Horizon and Sun Disk (candidate)

Cloudless World; no cloud generator, compositor or material changes.

#### Changed
- Sun Elevation range -5..85 -> -30..85, preserving the presets.
- Sun disk radius 1.5 -> 1.0 deg, strength 6 -> 4; disk masked by the ground
  gradient at the horizon so it is cut when Horizon Offset raises the horizon.
- `apply_sun_angles` refreshes the World disk immediately.
- World marker 31 -> 32.

#### Evidence
- `preset_dev/phase2_atmosphere/`: four conditions and second framing, Sun
  sweep +8..-8, Horizon Offset, Softness/Accent, UI before/after.
- 37/37 OpenGL/Vulkan, interactive 5/5, ALD ALL, audit 44/44, Phase 6 17/17,
  build PASS; markers 29/30/31 -> 32.
- Status: **VISUAL APPROVED - merged in 2.63.0**.

### Phase 3 - UI cleanup

UI-only; no World, Shooting Star, material or shader change.

#### Changed
- View3D sidebar mirrors the Scene Properties sections with the same drawing
  functions: palette root plus Atmosphere & Sun, World Clouds, Stars & Milky
  Way, Shooting Stars, Palette Customization, Materials & Shadows, Compositor
  and Advanced Settings. All sub-panels are open and scrollable.
- Scene Properties reordered: Atmosphere & Sun, grouped World Clouds, Stars &
  Milky Way, autonomous Shooting Stars, Palette Customization, Materials &
  Shadows, Compositor, Advanced Settings.
- Sun Beams removed from Atmosphere; it exists only in the Compositor effects.
- Shooting Stars uses the `ALD_UL_shooting_stars` list with Timing, Trajectory
  and Appearance groups; operators and shader unchanged.
- Compositor states are explicit through `compositor.scene_stack`: inactive,
  configured/render-disabled, active in render, plus a read-only viewport
  preview. A user compositor group is never treated as ALD. Applying a palette
  never enables the compositor.
- `ald.viewport_compositor` is limited to the current 3D view and is not called
  by the UI.

#### Evidence
- `preset_dev/phase3_ui/`: before/after sidebar, Scene Properties, Shooting
  Stars, compositor inactive/disabled/active/effects, legacy project and
  narrow layout screenshots; `phase3_ui.json` (68 checks), invariance JSON and
  comparison render, regression logs.
- Pixel-identical render (`maxdiff 0`); World 719 / Compositor 31 nodes; marker
  32 on both.
- ALD ALL PASS; audit 44/44; Phase 6 technical 17/17; Phase 1A 37/37; Phase 1B
  markers 29/30 -> 32; Phase 2 audit PASS; build PASS.
- Status: **VISUAL APPROVED - merged in 2.63.0**.

### Phase 4 - star look and cloud sun scatter (feature branch)

Feature branch `feature/star-cloud-look`, based on `4db6718`. Look and shader
changes; no merge or release.

#### Changed
- Shooting star `Thickness` maximum `0.05` -> `0.01 rad`; the shader clamps
  old events and caps the head radius at `0.012 rad`. The default `0.0018`
  is unchanged. Marker 33.
- New per-event `Curvature` (default `0.0`, range -1..1): a signed sine bow
  along the path normal, zero at the endpoints. Marker 34.
- New `Cloud Sun Scatter` (default `0.0`, range 0..1) under World Clouds >
  Lighting: a sun-facing silver-lining boost, not volumetric shadowing.
  Marker 35.
- Shooting Stars Trajectory shows `Curvature`; World Clouds Lighting shows
  `Sun Scatter`; Thickness slider max is 0.01.

#### Evidence
- `preset_dev/star_thickness/`: before/after 0.05, 0.01, default; compare and
  metrics.
- `preset_dev/star_curvature/`: 0/0.5/1.0/-1.0 curves; Phase 1A 37/37.
- `preset_dev/cloud_sun_scatter/`: 0/0.5/1.0; pixel difference and compare.
- 68/68 UI, 44/44 audit, Phase 6 17/17, Phase 1A 37/37, Phase 1B markers
  29/30 -> 35 with events/animation preserved, Phase 2 audit PASS, Phase 6
  matrix 22 cells, ALD ALL PASS, build PASS.
- Status: **VISUAL APPROVED - merged in 2.63.0**. The 12-preset review
  is in progress.


## 2.62.0 - 2026-10-27
Phase 6: final World Sky release.

### Added
- 22-cell release matrix: three cloud families x three Sun directions, three
  palettes, four coverage steps, two cameras, wind and two shooting stars.
- `phase6_technical.py`: 17 checks covering idempotent apply, deterministic
  generation, wind continuity, star-slot isolation, duplicate-scene ownership,
  save/reload persistence and resource cost.
- Phase 6 evidence in `preset_dev/phase6/` and source-audit gates.

### Changed
- Release version 2.62.0; the World Sky Edition is merged to `master`.
- Stratocumulus and Cirrus are documented in the release matrix; Cumulus
  remains the family with an explicit aesthetic approval.

### Evidence
- `preset_dev/phase6/contact.png`, `metrics.json`, `README.md`.
- Technical gate **17/17 PASS**; audit **40/40**.
- Extension 2.62.0 installed and enabled in an isolated config.

## 2.61.0 - 2026-10-27
Phase 5: presets and compact UI.

### Added
- Soft Dawn, Blue Hour, Cloudy Afternoon, Stormy Sunset and Moonlit Night.
- Reset Look and Save as Custom (the preset is never overwritten).
- Quick Look sidebar: preset, Apply/Reset, Sun elevation, cloud type/coverage/
  wind and stars.
- One collapsed Advanced Sky panel; full sections in Scene properties:
  Atmosphere & Sun, World Clouds, Stars & Milky Way + Shooting Stars,
  Palette Customization, Materials & Shadows, Compositor, Advanced Settings.
- Compositor: explicit Enable Compositor, inactive state without controls,
  viewport ALWAYS/CAMERA/DISABLED label.

### Evidence
- `preset_dev/palettes/sheet.png` with all 12 palettes.
- UI screenshots regenerated; World/compositor sections.
- Audit **38/38**.

## 2.60.1 - 2026-10-27
Shooting-star visibility and starfield consistency.

### Fixed
- Add places the event in the current camera view and 1/3 into its life, so it
  is visible immediately.
- Editing any event field refreshes the World via `_on_star`; before, the
  changes waited for a palette apply.
- New Preview operator moves the timeline into the event and aims the camera
  at its start.
- The star is now a thin tapered line with a short bright head, cool-white by
  default, instead of a thick white capsule.

### Evidence
- `preset_dev/shooting_star/` regenerated frames and contact.
- UI screenshot includes the Shooting Stars panel and Preview button.
- Audit **33/33**.

## 2.60.0 - 2026-10-27
Phase 4: controlled 2D shooting stars.

### Added
- Persistent `ALD_ShootingStar` events with start frame, duration, sky
  position, direction, angular length, trail, thickness, brightness, glow and
  color.
- Add / duplicate / remove operators and a Shooting Stars panel (max 4).
- Four World-shader slots evaluated in gnomonic sky coordinates with a frame
  driver; the head moves, the tail tapers and the event disappears after its
  duration. No objects or particles are created.
- Clouds attenuate the star through the World coverage mask.

### Evidence
- `preset_dev/shooting_star/` frames 1 / 8 / 16 / 25 / 30, contact and README.
- `world_fixture.py` saves and reloads the event.
- Audit **31/31**.

## 2.59.1 - 2026-10-27
Cumulus shape/lighting iteration.

### Changed
- Cumulus coverage/scale/breakup tuned for larger isolated masses.
- Body shading: height tone darkens the lower cloud, solar range widened to
  -0.030..0.004, default Sun Lighting 1.2.
- The family contact sheet and silhouettes were regenerated.

### Gate
- The first Cumulus day gate is still open: the masses are improved but the
  rounded top is not yet at the v1 reference level.

## 2.59.0 - 2026-10-27
Phase 3 first gate: World cloud families.

### Added
- `Cloud Type`: Cumulus, Stratocumulus, Cirrus.
- Controls: Vertical Development, Breakup, Detail, Seed, Sun Lighting.
- The same density drives the three family silhouettes: Cumulus lowers the
  effective flatness, Stratocumulus raises it, Cirrus stretches the sky ray
  and thins the field.

### Evidence
- `preset_dev/cloud_families/` - three color renders, silhouettes and
  `contact.png` under one day sky and camera.
- `Cloud Type`/Seed checks in the World gate.
- Audit **26/26**.

## 2.58.0 - 2026-10-27
Phase 2: cloudless sky consolidation.

### Changed
- Sky Accent is a broad, smooth band (0.20 half-width) instead of a narrow
  0.07 stripe: the dusk/night blue band is gone.
- `_sun_fade` gates the Sun disk below the horizon and fades the glow around
  -7 degrees; the frame handler uses the same gates.
- The legacy World fireworks and meteors were already removed from the
  operational path; their remaining shader blocks and settings are gone.

### Evidence
- `preset_dev/sky/` - noon, sunset, dusk, night with clouds off; before/after
  against v2.57.0, `contact.png`, `metrics.json`, README.
- World gate covers the Sun below-horizon response.
- Audit **23/23**.

## 2.57.0 - 2026-10-27
World Sky Edition: the World is now the product.

### Removed
- 3D fireworks, meteors, Geometry Nodes and the FX pass/Cryptomatte/cache.
- Spatial Clouds 2.5D, atmospheric smoke and their UI/handlers.
- World fireworks and World meteors: the shader amounts are forced to zero.
- FX panels, operators, cloud/smoke settings in the operational path.
- FX audit, fixtures and development scripts.

### Kept and adapted
- Four-zone World gradient, Sun disk/glow/beams, clouds, stars and Milky Way.
- Palette, camera override, shot markers, materials and optional compositor.
- Persistent scene identity, ownership repair and snapshot restore.
- Explicit Legacy ALD Data: disable or remove old collections; nothing is
  cleaned automatically.

### Evidence
- Phase 0 visual baseline against v1.0.3/v1.1.0 in `preset_dev/world_baseline/`.
- World gate, lifecycle fixture and World audit: `ALD GATE: PASS`,
  `WORLD FIXTURE: PASS`, `ALD WORLD AUDIT 20/20`.
- UI screenshots updated in `preset_dev/ui/`.

### Compatibility
- See `MIGRATION_2_57.md`; rollback is the `archive/v2.56.0-full` tag.

## 2.56.0 - 2026-10-27
P1 contract and framing, P2 light/cloud response, P3 full-stack evidence.

### Fixed
- Burst Duration is the solver lifetime (`_event_config`), not a UI-only field;
  the envelope and the cloud flash use it.
- Composition Offset and Burst Spread recompose an existing automatic show;
  the requested distance is stored on the system (`layout_distance`) so
  repeated updates do not drift.
- Intentional Crop is honoured by the recomposition.
- The framing envelope includes gravity, spark margin and the physical shell
  residual; the gate compares it with the actual sampled solver particles.
- The FX pass now carries the unoccluded coverage in its alpha; the compositor
  divides the visible Cryptomatte coverage by it (`ALD | FX Visibility`), so a
  particle behind a subpixel occluder edge loses exactly the hidden fraction.
  A legacy RGB pass keeps the binary fallback.
- The cloud rim is directional (`Cloud Sun Side/Face`), driven by the real sun
  and card orientation.
- The cloud flash uses the event colour, and the two simultaneous sources keep
  separate colours (`ALD | Flash Color`, `ALD | Flash Color2`).

### Evidence
- `check_fx_layout_contract`, `check_fx_envelope_solver`,
  `check_fx_subpixel_visibility`, cloud sun-side nodes.
- `preset_dev/validate_stack.py`: 3 palettes x fixed/travelling camera through
  the strict pass path, 800x450, `validation_stack/metrics.json`.
- `preset_dev/cloud_rim.py`: A/B sun azimuths, `cloud_rim/metrics.json`.
- `ALD GATE: PASS`, `DUP FIXTURE: PASS`, audit **143/143**.

## 2.55.5 - 2026-10-27
P0 pass-cache correctness and scene-copy safety.

### Fixed
- `fx_pass_state()` is the single authority of `compositor.build()`: only
  `READY` feeds `ALD | FX Pass`. A stale, missing, out-of-range or unsigned
  EXR is never read, even when the file exists.
- Strict mode with no valid pass skips punch, restore and FX glow: the output
  is the environment (B), pixel-identical to the no-FX render, instead of
  dark holes from `P(B) * (1 - A)`.
- Default pass paths use the persistent scene UUID
  (`ald_fx_pass_<uid>/fx.exr`) and an explicit `_f0001` frame suffix; Scene1
  and Scene2 no longer collide.
- Sequence state checks every frame file (EXR magic, non-empty) and every
  per-frame signature record, not only the endpoints.
- The signature includes camera shift, sensor height, pixel aspect, engine,
  film transparency, motion blur, shutter and EEVEE render samples.
- An animation pass is written to a staging directory and published with one
  directory rename: a failure at frame N keeps the previous sequence, files
  and manifest intact.
- Remove ALD restores `use_pass_cryptomatte_material` and
  `use_pass_object_index`.
- A material used by another scene is left untouched by Shadow Tint / Toon /
  Rim sync; a sun shared with another scene is never rotated.

### Evidence
- `preset_dev/verify.py`: `check_fx_pass_cache`, `check_fx_pass_names`,
  extended sequence test (middle file/signature), strict pixel comparison,
  camera-shift invalidation and render-pass restoration.
- `preset_dev/duplicate_fixture.py`: shared ordinary material and shared sun
  are not edited from the copy.
- `ALD GATE: PASS`, `DUP FIXTURE: PASS`, audit **135/135**.

## 2.55.4 - 2026-10-27
Cloud benchmark: colour, position, shape and memory separated.

### Changed
- Five runs per scenario; the table records the median and every run.
- The property update is the timed refresh (`clouds_depth`,
  `clouds_coverage`); the old code timed a no-op refresh after the callback.
- The memory probe is separate: `tracemalloc` slows the creation 5-8x and must
  not contaminate the timing table. The value is the Python peak, not GPU.
- Medians at 720p: creation 0.12-1.54 s, colour 0.16-0.78 ms, position
  1.0-3.6 ms, shape 0.12-1.40 s, render 2.13-3.41 s, Python peak 1.9-29.0 MB.
- The 2.39 comparison uses the 5-run 0.5 / 3-layer median: 0.569 s creation,
  2.905 s render against the old 0.0072 s / 3.275 s.

## 2.55.3 - 2026-10-27
Cloud billboard evidence.

### Added
- `preset_dev/cloud_views.py` and `preset_dev/cloud_views/`: shot camera,
  side camera with Shot Locked and side camera with Camera Facing, same scene,
  palette, coverage 0.5, three layers and 1280x720.
- `cloud_views/README.md` explains the billboard representation and the
  Camera Facing workflow.

### Notes
- No product code change.

## 2.55.2 - 2026-10-27
2.39 cloud baseline measured on the same camera.

### Evidence
- The `v2.39.0` tag is checked out in a temporary worktree and its add-on is
  enabled from a temporary `BLENDER_USER_SCRIPTS`: 3 wavy bands, 1,536 quads,
  creation 0.0072 s, render median 3.275 s at 1280x720, AFTER_SCHOOL, AgX.
- The 2.55 Final spatial cards (coverage 0.5, 3 layers): 57,968 triangles,
  creation 0.518 s, render median 2.723 s under the same camera/resolution.
- `preset_dev/clouds_bench/LEGACY_2_39.md`, `legacy_2_39.json`,
  `legacy_2_39.png`.

### Notes
- The old mesh is quads, the new is triangles: the new is about 19x the
  triangles and 72x the creation time; the render is comparable, not a general
  performance win. The two baseline scenes/world implementations differ; the
  comparison is between the two looks as well as the two meshes.

## 2.55.1 - 2026-10-27
Validation report and explicit legacy labelling.

### Added
- `preset_dev/VALIDATION.md`: the plan's Definition of Done mapped to the
  structural, runtime, FX isolation, lifecycle, visual and performance evidence.
- `verify_all` labels the three steps with their category.
- `preset_dev/emission_isolation/README.md` and the script docstring label the
  old FAIL as the expected legacy measurement; the current path is the gate.

### Notes
- No product code change; the package is rebuilt for the version.

## 2.55.0 - 2026-10-27
New FX from the UI require the pass.

### Changed
- The FX creation operators (Create Fireworks, Shooting Stars, Hero Meteor,
  Directed Show) set `fx_pass_required = True`: a render without a fresh pass
  hides the FX instead of using the contaminated main Emission. The direct
  Python API keeps the property unchanged for compatibility and tests.
- The gate checks that the operator sets the strict flag and that the stack
  uses `ALD | FX Strict Black`; the UI screenshot shows the checked toggle.

## 2.54.0 - 2026-10-27
ORTHO show fit by the lateral layout.

### Fixed
- `_spread_limit` uses the orthographic half-width for an ORTHO camera;
  `_fit_show` reduces the spread instead of increasing the distance, which
  cannot change the projected size in ORTHO. An oversized burst is reported by
  the measured fraction, never silently scaled.
- The gate creates a three-burst ORTHO show and requires 0.95.

## 2.53.1 - 2026-10-27
Atomic pass failure test.

### Added
- The gate renders a valid pass, then attempts a pass under a missing directory:
  the valid EXR hash must stay identical and no partial file may be published.

## 2.53.0 - 2026-10-27
Copy-on-write for old shared FX materials.

### Fixed
- `fx.ensure_materials` runs from `rebuild_registry` (load/save fixtures) and
  copies an ownerless FX material per scene, on the object slots and on the
  material inputs of the Geometry Nodes modifiers; the Cryptomatte matte is
  refreshed. New per-owner materials skip.
- The gate creates the same old material in two scenes, migrates both and
  requires distinct copies with distinct `ald_fx_owner`.

## 2.52.0 - 2026-10-27
Strict pass mode and pixel-aspect apparent widths.

### Added
- `fx_pass_required` (Require FX Pass) in the FX Pass box: with no valid pass
  the stack feeds a black FX contribution instead of the contaminated main
  Emission, so the FX are hidden rather than leaking. Default off for
  compatibility; the shot and animation operators generate the pass.
- `_world_per_pixel` includes `resolution_percentage` and the pixel aspect:
  the apparent trail width is stable at 50% renders and non-square pixels.

### Evidence
- The gate builds the stack with and without the strict flag and checks the
  `ALD | FX Strict Black` node; the UI screenshot shows the new toggle.

## 2.51.0 - 2026-10-27
Explicit shot and animation orchestration.

### Added
- `ald.fx_render_shot` and `ald.fx_render_animation`: render the FX pass (still
  or sequence), rebuild the stack, then render the composite to the scene
  output. The pass is generated by an explicit operator, never inside a render
  handler, so there is no nested render recursion.
- The FX Pass box exposes pass-only and composite buttons.
- The gate renders a two-frame shot and a two-frame animation through the new
  operators and checks the composite files and the pass range.

## 2.50.0 - 2026-10-27
Cloud card border rim and linked-copy fixture.

### Added
- `_cloud_mesh` writes `ald_edge` (1 on the contour vertices, 0 inside); the
  card material mixes Cloud Light with the vertical gradient through the
  attribute. The islands now have a soft border rim without alpha, a second
  pass or a change to the opaque Cryptomatte/Depth contract.
- The duplicate fixture asserts that the copy starts with the shared
  collections before the repair, so the linked/full case is explicit.

### Evidence
- `preset_dev/clouds/` regenerated with the rim; the showcase and the cloud
  benchmark are regenerated from the same build.

## 2.49.1 - 2026-10-26
Per-scene FX materials.

### Fixed
- `fx._material` includes the scene UUID in the material key and tags
  `ald_fx_owner`: two scenes with the same palette no longer share a mutable
  material, so retinting one cannot change the other. The gate creates two
  owners and requires distinct materials.
- Existing files with old, ownerless materials keep working; the next create
  uses the per-owner material.

## 2.49.0 - 2026-10-26
Solver-driven show framing and physical cloud light events.

### Changed
- `event_radius` uses the same family speed, drag, life and size as the solver;
  a firework in Physical mode uses the reached rise point, not the authored
  target. The old event speed default (30) no longer drives the envelope.
- The show layout is symmetric and the hero sits on the camera forward; the
  old left-biased layout required aiming at the hero and invalidated the fit.
- `_fit_show` grows the distance until every burst envelope is at least 95% in
  frame (12 steps); an ortho camera or a huge offset returns the measured
  fraction instead of silently scaling the burst.
- `fx_fit_override` (Intentional Crop) keeps the authored framing and is the
  only accepted exception in the gate, which now requires 0.95 instead of 0.15.

### Added
- `fx.light_events`: effect-independent light sources with the actual firework
  burst point, the meteor head at the current age, energy, radius and time.
  `cloud_flash` is a per-event multiplier separate from the screen glow.
- `clouds.update_flash` feeds two sources; the card shader sums them
  (`ALD | Flash X2/Y2/Energy2` + `total_energy`).

### Fixed
- `clouds.create` writes the quality into `ald_clouds_signature` too: the first
  refresh after a create no longer rebuilds every mesh (it was ~0.8 s; now
  1.7-6.6 ms at 1-5 layers in Final).

### Evidence
- `composition.json` regenerated: all 3- and 5-burst events `in_frame`, the
  hero at 0.5/0.5, fractions 0.954-1.0.
- `clouds_bench/metrics.json` regenerated with three runs and medians:
  creation 0.11-1.46 s, refresh 0.0017-0.0066 s, render 2.15-3.20 s at 720p,
  Windows 11, Blender 5.1.2. The 2.39 comparison is not reproducible: the code
  is not in the repository; the file records the hardware and the medians.

## 2.48.0 - 2026-10-26
FX pass hardening and spatial cloud controls.

### Fixed
- `_render_pass_still` renders to a temporary EXR and publishes it with
  `os.replace`: a failed render cannot truncate the valid pass already on disk.
  `scene.render.use_compositing` is saved and restored with the other render
  state.
- `_pass_layer` isolates the FX collection at any nesting depth, not only when
  it is a direct child of the scene.

### Added
- Spatial Clouds: `clouds_quality` (Preview / Final) and `clouds_world_blend`
  (0..1). The blend reduces the World cloud amount while the cards are active;
  Create and Remove reapply the World.
- The duplicate fixture saves the scene to a temporary `.blend`, reloads it and
  checks that the identities and the cloud collections stay independent;
  removing the reloaded copy keeps the original.
- Gate: World blend, Preview/Final and the nested/atomic pass checks.

### Evidence
- `preset_dev/clouds/` and `preset_dev/clouds_bench/` regenerated with Final
  quality; the benchmark counts are unchanged by the new cap.

## 2.47.0 - 2026-10-26
Continuous spatial-cloud contours.

### Changed
- `clouds._cloud_mesh` cuts the islands with **marching squares**: the boundary
  vertices sit on the interpolated iso-line, the mesh is triangulated and
  manifold, and the 10-20 px staircase at 1920 is gone. The field, the seed and
  the persistent layers are unchanged.
- The Coverage threshold is `0.98 - 1.02 * coverage` (clamped at 0): 0.9 and 1.0
  no longer produce the same mesh, so the top of the slider stays sensitive.
- `fx.pass_signature` includes the scene UUID: a pass copied from another scene
  is rejected as outdated, even when the FX systems and the camera match.

### Added
- The gate `check_cloud_contour` requires interpolated boundary vertices,
  triangles only, no non-manifold edge, and 1.0 denser than 0.9. It tests
  `_cloud_mesh` directly, no scene needed.

### Evidence
- `preset_dev/clouds/` regenerated (dusk off/on, night on); the cloud benchmark
  is regenerated from the same build: one layer 1,840 / 14,086 / 41,110 /
  46,784 faces at 0.16 / 0.5 / 0.9 / 1.0, five layers up to 258,876;
  creation 0.10-1.44 s, render 1.96-4.18 s at 720p.
- The new counts are **triangles**; the 2.44 benchmark counted quads. Do not
  compare the two series directly.

## 2.46.7 - 2026-10-26
Installable extension package.

### Added
- `LICENSE` with the full GPL-3.0 text, and a `[build]` exclusion list in the
  manifest: the package contains the add-on, the manifest, the license and the
  user docs, never the research evidence.
- `preset_dev/build_release.py` builds `dist/anime_look_director-<version>.zip`
  through `blender --command extension build` (about 240 KB against 71 MB with
  `preset_dev/` and `graphify-out/` included).

### Fixed
- `dist/` is ignored by git.

### Evidence
- The built zip installs and enables in an isolated user config
  (`BLENDER_USER_CONFIG` / `BLENDER_USER_EXTENSIONS`): version 2.46.7 and the
  new operators (`ald.repair_ownership`, `ald.fx_render_pass_animation`) are
  present. The package contains no `preset_dev/` or `graphify-out/`.

## 2.46.6 - 2026-10-26
World and sun ownership on duplicated scenes.

### Fixed
- `ownership.repair` gives the copy its own world when the world is shared: a
  palette applied to the copy no longer rewrites the original sky.
- The auto sun is tagged with the scene identity; a copy does not retint the
  original's shared sun. An older file with a single-user auto sun receives the
  tag on the next apply.
- The duplicate fixture applies a different palette to a copy and checks that
  the original's world gradient and sun are unchanged.

## 2.46.5 - 2026-10-26
Per-scene default path for the FX pass.

### Fixed
- `_default_pass_path` includes the scene name: two scenes without an explicit
  path no longer write and overwrite the same EXR files. A custom path stays the
  user's choice; a copied scene inherits it until it is changed.

## 2.46.4 - 2026-10-26
Per-frame pass signature for animated cameras.

### Fixed
- `render_fx_pass_animation` stores the signature of every frame in the
  sequence; `fx_pass_state` compares the current frame's entry. A static camera
  is valid at both ends and a moved camera invalidates only the frames it
  changed, instead of reporting the whole sequence as outdated.
- The gate checks the per-frame signature: the pass is ready at the start and
  the end, stale after a camera move, ready again after restoring it.

## 2.46.3 - 2026-10-26
Safe removal on duplicated scenes.

### Fixed
- `ald.remove_from_scene` and `ald.detach` repair a duplicated scene before
  acting: removing ALD through a copy no longer restores the shared materials.
- `snapshot.restore` never rewrites a world shared with another scene, and
  never modifies or removes a sun linked into another scene: the operator
  reports that the shared world was left unchanged instead of silently
  changing the original.
- The duplicate fixture removes ALD from a copy and checks that the original's
  clouds, FX, materials, material nodes and world are untouched.

## 2.46.2 - 2026-10-26
Automatic ownership repair on Build and Apply Palette.

### Fixed
- `ald.build` and `ald.apply_palette` repair a duplicated scene before touching
  it: the copy becomes independent without the manual Repair Ownership click.
  The panel warning still covers the window before the first action.
- The duplicate fixture copies the scene a second time and checks that the
  Build operator itself makes the copy independent.

## 2.46.1 - 2026-10-26
Content-aware pass state and a single verification command.

### Added
- `fx.pass_signature` + `fx_pass_signature`: a hash of the FX systems/events,
  palette, backend, style, age, camera pose, lens and resolution the pass was
  rendered with. `fx_pass_state` reports "outdated" when any of them changes,
  not only the frame.
- `preset_dev/verify_all.py`: runs the gate, the duplicate fixture and the audit
  in fresh factory-startup Blenders and exits 1 on any failure.

### Fixed
- `preset_dev/audit_plan.py` exits 1 when an item fails; it always returned 0.
- The gate checks that an FX edit marks the pass stale, on top of the sequence.

### Open
- With an animated camera the sequence signature uses the pose of the restored
  frame: the panel may report "outdated" on other frames even when the sequence
  is valid. It never reports "ready" for a pass that is not.
  (Fixed in 2.46.4: the signature is stored per frame.)

## 2.46.0 - 2026-10-26
Animated FX pass, scene-owned pass images and a real pass state.

### Added
- `compositor.render_fx_pass_animation` and `ald.fx_render_pass_animation`:
  one numbered EXR per frame of the scene range, and the `ALD | FX Pass` image
  node reads the files as a `SEQUENCE` (`frame_duration`, `frame_start`), so
  the compositor follows the animation. Cost: one extra render pass per frame.
- `fx_pass_frames` on the scene: the frame range of the rendered pass.
- `compositor.fx_pass_state` and the panel label: ready, stale (another frame),
  out of range or missing, with a real file check.
- The pass controls have their own FX Pass box in the FX section.

### Fixed
- The pass image is per scene (`ALD | FX Pass | <scene>`): two scenes no longer
  overwrite each other's pass.
- The still operator rebuilds the stack after the render, so the pass node is
  wired at once instead of waiting for a manual Build.
- The gate now renders a four-frame pass sequence and checks the node fields,
  the per-scene image and the frame difference.

## 2.45.0 - 2026-10-26
Scene-copy ownership repair and the PA2 volume spike.

### Added
- `ownership.py` and `ald.repair_ownership`: a duplicated scene gets its own
  ALD identity, detaches the shared collections and makes its objects, meshes
  and materials independent. When the collections are shared it rebuilds the
  clouds and the FX from the persistent data instead. The panel warns when
  another scene shares the ALD collections.
- `preset_dev/duplicate_fixture.py`: a dedicated duplicate-scene fixture
  (`DUP FIXTURE: PASS`) — the copy owns different collections and objects, the
  original objects/FX/collections survive, and removing the copy's clouds is
  safe.
- `preset_dev/pa2_volume_spike.py` and `preset_dev/PA2_VOLUME_SPIKE.md`: the
  production cards against a native EEVEE volume at the same placement, 640x360.
  Cards 2.07 s, volume 1.07-1.09 s; the volume reads as a soft rectangle with
  hard edges and no anime silhouette. Cards remain the default; no backend was
  changed.

### Fixed
- The scene-copy ownership item left open in 2.44.0: after `Repair Ownership`
  the copy no longer shares the cloud/FX collections and removing its clouds
  keeps the original intact.
- The duplicated `2.43.0` heading in this file.

## 2.44.0 - 2026-10-26
Cloud benchmark and the scene-copy guard.

### Added
- `preset_dev/bench_clouds.py`: creation, refresh, polygons and 720p render for
  coverage 0.16 / 0.5 / 0.9 / 1.0 with 1 / 3 / 5 layers; `metrics.json` and
  the renders in `preset_dev/clouds_bench/`. Measured: 829 to 159 729
  polygons (1 layer: 829 / 7 374 / 21 311), creation 0.06-0.12 s per layer,
  refresh ~1 ms, render 2.6-4.3 s at 720p.

### Fixed
- `clouds.remove` unlinks an object that belongs to another collection instead
  of deleting it: a scene copy that shares the object datablocks cannot lose
  the original cards.

### Open
- The scene-copy **collection** ownership is still shared: the dedicated
  duplicate-scene test shows that removing the copy's collection can remove the
  original collection. It needs retagging/new UIDs before it is safe; the test
  is not shipped green. Do not duplicate a scene with spatial clouds.
- PA2 volume research.

## 2.43.0 - 2026-10-26
Framing envelope: the whole burst is checked, not only its centre.

### Added
- `fx.event_radius`, `fx.event_envelope`, `fx.event_frame_fraction`: a
  conservative projected bounds of a burst from the family speed and life.
- The composition gate requires each burst envelope to be at least 15 % in
  frame (a gross cut fails) and prints the fractions; the composition report
  records `frame_fraction` and `in_frame` is the envelope at 95 %, no longer
  the centre.
- A multi-burst show fits its distance to the vertical FOV and caps the
  lateral spread so the edge bursts are not cut by the lens. The fit uses the
  lens, sensor fit and resolution at creation.

### Evidence
- `preset_dev/composition/` regenerated: the 3-burst dusk hero is 94.9 % in
  frame (reported as not in frame), the others 98–100 %; the 5-burst night
  Willow/Kamuro at the edges are cut and reported (52.5 % / 45 %), not hidden.

### Open
- Duplicate-scene test, cloud benchmark, PA2 volume research.

## 2.42.0 - 2026-10-26## 2.42.0 - 2026-10-26
P0 closed: the FX contribution is isolated by an external FX pass.

### Added
- `compositor.render_fx_pass` + `ald.fx_render_pass` + a panel button: the FX
  emission is rendered alone to an EXR (temporary view layer with only the FX
  collection), and the stack reads it through an `ALD | FX Pass` Image node.
  F now contains only the FX: a foreign emitter cannot enter it.
- `check_fx_pass_isolation` in the gate: a burst plus a very bright foreign
  emitter (40/20/4 x 3) behind it, the pass rendered with and without the
  emitter, the two EXRs must differ by less than 0.01 (measured 0.0), and the
  stack must read the pass image.

### Changed
- The pass is a two-step workflow: render it after changing the FX, camera or
  frame, then render the shot. For animations the pass is rendered per frame.
- When the pass file is missing the stack falls back to the main Emission
  (legacy path); the panel shows whether a pass is ready.
- The temporary FX view layer is created after the collections exist and
  excludes every child except the FX collection (with a `view_layer.update()`
  before reading the tree). This is the isolation that the compositor node
  group could not read reliably.

### Open
- The fallback (no pass) keeps the edge leak; the pass is not automatic.
- Motion blur and animation require one pass per frame.
- Framing envelope and duplicate-scene tests remain open.

## 2.41.0 - 2026-10-26## 2.41.0 - 2026-10-26
Consolidation patch after the 2.40 audit. NOT a milestone closure: the FX
emission isolation is a known, reproducible P0 FAIL.

### Fixed
- Cloud Coverage 1 no longer builds a full rectangle: the threshold is clamped
  positive and the comparison is strict, so the border stays empty.
- Shot Locked stores the creation rotation once; Camera Facing keeps its own
  rotation and switching back does not jump.
- The cloud mesh rebuild keeps the material; the LOD is computed after the
  layout at the final depth.
- Cloud objects are resolved by UID inside the scene's collection; a
  collection linked to another scene is skipped; width/palette updates and the
  Cryptomatte material list are scene-owned (the modifier material inputs are
  included, which fixes the missing instanced heads).
- Kuwahara depth and the environment filters read the base layer; the cloud
  flash attenuates with the world distance.
- `preset_dev/emission_isolation.py` is runnable on the HEAD, measures the
  `A < 0.1 / 0.1..0.9 / A >= 0.9` regions and exits 1 on FAIL.

### Open (P0)
- The FX contribution at partially covered pixels still contains the foreign
  emission: 0.995 mean / 1.0 max in the fringe region, 0.575 / 0.996 in the
  mixed region (extreme emitter 40/20/4 x 3). The Shader AOV is empty in
  EEVEE and Cycles in this environment; the FX-only layer fallback did not
  synchronise. See `preset_dev/CONSOLIDATION_2_41.md`.
- The framing envelope is not implemented.

## 2.40.0 - 2026-10-26## 2.40.0 - 2026-10-26
Spatial Clouds 2.0: real masses, working controls, persistent layers.

### Fixed
- **Coverage is the geometry**: the density-field threshold. 0 removes every
  face, 0.5 builds an intermediate mass, 1 the densest. Before, Cloud Amount
  did not enter the mesh at all (1536 polygons for every value).
- The slab is gone: the cards are islands with sky openings, cut by a
  deterministic field with a border envelope (no rectangle).
- Altitude is world units along the Sky/FX Anchor; depth is the distance from
  the creation camera. The old Height was a fraction of the depth and pushed
  the layers out of frame.
- In-place updates: a colour change never rebuilds, a depth/altitude change
  only moves, a coverage change rebuilds the mesh of the same object.
- The FX and the clouds no longer share an owner-only collection lookup: the
  FX objects landed in the cloud collection.
- The environment filters (Kuwahara mask, light wrap, ink, haze) read the base
  layer, so the particles cannot create edges in the environment.
- `event_color` receives the sky-tinted palette (it was white); `event.size`
  scales the star velocity and the 0.6-2.0 clamp is gone; the apparent trail
  width follows camera, focal and resolution; `event.glow` drives the cloud
  flash.
- Palette changes update the FX material tint in place.

### Added
- `ALD_CloudLayer` persistent data, `SHOT_LOCKED` / `CAMERA_FACING`, a local
  flash response, diagnostics, and a new Spatial Clouds panel.
- `preset_dev/clouds_baseline/` (the 2.39 defect), `preset_dev/clouds/`
  (after), `preset_dev/emission_isolation/` (the measured non-FX emission
  limit), `preset_dev/SPATIAL_CLOUDS_2.md`.

### Open (honest)
- Non-FX emission at partially covered FX pixels: measured up to 0.93 with an
  extreme foreign emitter; the dedicated FX-only layer attempt was reverted.
- The framing gate still checks the burst centres, not an envelope.
- A duplicated scene with clouds is not tested; the World duplication is not
  reduced.

## 2.39.0 - 2026-10-26## 2.39.0 - 2026-10-26
Showcase foreground.

### Added
- `preset_dev/showcase.py` builds a dark skyline (four blocks and a short
  antenna) at the bottom edge of the 1080p shot. It is scene content for the
  evidence, not an add-on feature: it gives scale to the sky and exercises the
  ink lines and the environment occlusion.
- The silhouette material is near-black (0.004) so the world ambient cannot
  lift it into a lit building.

## 2.38.0 - 2026-10-26## 2.38.0 - 2026-10-26
Integration showcase and cloud tuning.

### Changed
- The 2.5D cloud bands are thinner (0.30x the distance, was 0.55x), higher and
  with more noise contrast: they read as a depth layer instead of a wall in the
  middle of the sky. The palette light starts at 38 % of the band height.

### Added
- `preset_dev/showcase.py`: the whole stack in one frame at 1920x1080, a
  five-burst night show and a three-burst dusk show, both with the cloud layer
  and the full compositor. Evidence in `preset_dev/showcase/`.

### Evidence
- `preset_dev/clouds/` regenerated with the tuned bands (dusk off/on, night).

## 2.37.0 - 2026-10-26## 2.37.0 - 2026-10-26
Verification pass: the UI probe found a broken panel.

### Fixed
- The 2.5D Clouds box used the icon `CLOUD`, which does not exist in Blender
  5.1: `UILayout.label` raised and the whole World & Shadows panel failed to
  draw. The icon is now `WORLD`.
- `check_panel_icons` and `check_ui_parity` were defined in the gate but never
  called, which is why the broken icon passed. Both run now.
- `preset_dev/ui_probe.py` resolved a relative `--out` against Blender's
  working directory, so the screenshots landed outside the repository and the
  probe reported them missing. The path is resolved against the add-on.

### Added
- `preset_dev/temporal_strip.py`: six ages (0.10..2.20 s) for the
  Chrysanthemum and the Willow, a 6x2 sheet and the coverage curve. The
  Chrysanthemum peaks at 1.1 s (26 %) and is gone by 2.2 s (1.4 %); the Willow
  peaks at 1.6 s (27 %) and keeps 23 % at 2.2 s.
- UI screenshots in `preset_dev/ui/`: the 2.5D Clouds box draws in the Scene
  properties and in the sidebar.

## 2.36.0 - 2026-10-26## 2.36.0 - 2026-10-26
P6 of the visual integration milestone: the validation matrix.

### Added
- `preset_dev/validate_matrix.py`: 36 renders (3 palettes x 4 families x 3
  ages) at 800x450 with a background reference for the FX coverage, per-cell
  metrics (luminance, clipping, saturation, coverage, time) and a 6x6 contact
  sheet. 37/37 PASS, mean render 1.51 s.
- `preset_dev/P6_REPORT.md` with the criteria, the table and the findings.

### Fixed
- Beads and heads get the same 1.2 px apparent-size floor as the trails: a
  0.05 m bead is 0.65 px at 55 m with a 32 mm lens. The matrix found the Peony
  losing its sparkle at distance.

### Notes
- The first matrix run was shifted by `fx_age` (default 0.8 s); the tool now
  pins it to 0. The product clock was correct, the test was not.

## 2.35.0 - 2026-10-26## 2.35.0 - 2026-10-26
P5 of the visual integration milestone: 2.5D clouds.

### Added
- `clouds.py`: three opaque cloud bands at 160/230/320 m, built as wavy
  geometry strips (512 columns). They are real environment geometry, they
  write depth, and a firework behind a band is hidden by the visible render
  through the P1 Cryptomatte matte.
- Palette-synced cloud colours (`clouds.sync` on every palette apply),
  `Cloud Amount`/`Cloud Height`, `ald.clouds_create`/`ald.clouds_remove` in
  both UI surfaces.
- `Remove ALD from Scene` removes the cloud layer with the rest.

### Tests
- Gate: three opaque cards, cloud colours present, and the FX matte behind a
  card moved in front drops below 75 % of the free matte.
- Evidence: `preset_dev/clouds/` (dusk off/on, night on) and `clouds.json`.

## 2.34.0 - 2026-10-26## 2.34.0 - 2026-10-26
P4 of the visual integration milestone: composition and spatiality.

### Fixed
- The depth hierarchy was inverted: the secondary and distant bursts sat at
  0.78x and 0.58x the distance, so they were closer and appeared larger. They
  now sit at 1.18x and 1.42x and read smaller.
- The distant burst was born at 0.85 s and had not burst at the show age; the
  stagger is 0.25 / 0.55 s.

### Changed
- A multi-burst show gets room: distance x1.4 and lateral spread x1.3, so the
  tens-of-metres bursts do not overlap. A single burst keeps its framing.
- Event sizes follow the depth hierarchy (1.0 / 0.9 / 0.8).

### Evidence
- `preset_dev/composition/`: three 1280x720 shows (dusk 3, night 5, golden 3)
  with `composition.json` (birth, distance, apparent size, screen position).
- Gate: depths strictly increasing, births staggered, sizes ordered, every
  burst inside the frame, distinct screen positions.

## 2.33.0 - 2026-10-26## 2.33.0 - 2026-10-26
P3 of the visual integration milestone: shading, palette and glow.

### Fixed
- The FX punch-out mixed toward the default grey of an unlinked B socket
  (0.5): every particle carried a grey veil, which washed out the colours and
  hid the missing sparkle.
- The Emission pass is already coverage-weighted, so multiplying it by the
  fractional Cryptomatte matte squared the coverage: thin filaments lost more
  background than they added and read as dark lines. F now uses a binary
  presence mask; the punch keeps the fractional matte.
- Instanced heads, beads and sparks were black: instanced geometry does not
  inherit the instancer's attributes. They now have their own materials with
  `INSTANCER` attribute lookups; the trail tubes keep `GEOMETRY`.
- The FX glow was effectively inert (defaults 0.6 strength / 0.35 threshold on
  an emission that peaks at ~0.7): new defaults 1.0 strength, threshold 0.0,
  size 0.35, measured on the composite.

### Changed
- The tail fades to 0.35 of the head energy (`tail_u`), so the burst has depth
  without punching dark lines into the twilight sky.
- The FX palette is pulled 30 % toward the sun colour of the sky palette.
- FX materials carry a shader version and are rebuilt in place when it changes.
- T24 renders at 256x256: the 64x64 frame made the meteor head sub-pixel.

### Tests
- Gate: the punch-out is black; both attribute domains exist; the glow changes
  the composite; the composite adds light instead of darkening it.
- Audit 50/50.

## 2.32.0 - 2026-10-26
P2 of the visual integration milestone: filament geometry.

### Fixed
- The Geometry Nodes filament was **empty**: `Points to Curves` consumed the
  loose vertices of a mesh without a `Mesh to Points` conversion, so the tube
  never existed and the FX read as a field of dots. The trail group schema is 4:
  saved groups are rebuilt and the modifiers remapped.
- The apparent width of a filament is now computed from the camera (sensor,
  lens, resolution, depth, orthographic scale): physical radius 0.022 m was
  sub-pixel at 55 m. `Trail Min Pixels` (1.5) and `Trail Max Pixels` (6) bound it.

### Changed
- About 35 % of the stars are a secondary population with 0.62x life and speed;
  every star keeps its own 0.45..1.0 fraction of the family trail. The burst is
  less regular and has an inner shell.
- The filament is a round tube, not a ribbon: `preset_dev/trail_shape_spike.py`
  measures tube 1.00 and ribbon 0.00 coverage edge-on.

### Tests
- Gate: the trail geometry is realized and must produce at least
  `spokes x (SAMPLES - 1)` faces; the modifier radius must reach the apparent
  minimum in pixels.
- `preset_dev/baseline_fx_p2/` and `preset_dev/p2_age_strip.py`: emission, glow
  and full renders plus four ages, so continuity is judged without Bloom.
- Audit 45/45.

## 2.31.0 - 2026-10-26
P1 of the visual integration milestone (3D fireworks and anime sky).

### Changed
- The FX coverage is the **Cryptomatte Material matte** of the FX materials
  (`ALD | FX Matte`) on the main view layer, not `max(R,G,B)`. A very bright
  pixel no longer claims full geometric coverage.
- `F = Emission x A` (`ALD | FX Coverage` + `ALD | FX Emission`), premultiplied
  and already occluded by the visible render; `C = P(B)*(1-A) + F + Glare(F)`.
- Removed the `ALD FX Only` view layer, the transparent world override, the
  `max(R,G,B)` coverage and the depth-comparison visibility for opaque
  occluders. `ALD FX Base` remains the clean environment.
- The FX branch is always built: with no FX objects the matte is 0 and the
  recomposition is the identity, so the parameter updates and the gate see a
  stable stack.

### Tests
- Gate: wall in front hides head/trail/glow; wall behind does not; a partial
  occluder splits correctly; zero FX identity; a foreign emissive surface does
  not enter the matte; a single glow fed by the masked emission; no halos from
  invisible particles (behind diff 0.000000).
- P0-P3 audit 40/40.

## 2.30.1 - 2026-10-26
Verification pass after P3.

### Fixed
- **UI probe** — `region.active_panel_category` is read-only in Blender 5.1:
  the probe now opens the sidebar first, sets the category when supported,
  scrolls the Scene properties with `view2d.scroll_down`, restores the 3D view
  before the sidebar shot and always quits. Screenshots in `preset_dev/ui/`.
- **Milestone** — the "flash off / embers survive" check derives the late
  frame from the real spark lifetimes instead of a fixed frame; 13/13 again.
- **Smoke** — the volume is aligned with the ALD Sky/FX Anchor axis (Y-up and
  X-up included), not only Z-up.
- **FX panel** — a Visual Profile box exposes the system/event kind and the
  sub-role energies (`ROLE_ENERGY`).

### Added
- **P0-P3 audit** — `preset_dev/audit_plan.py` checks the new plan against the
  source and writes `preset_dev/audit_report.json`: 39/39 OK.
- Look-dev sheets regenerated (palettes, FX sequence, families, milestone).

## 2.30.0 - 2026-10-26
P3 of the operational plan: atmospheric smoke, aesthetic variants, directed
shows and benchmarks.

### Added
- **Atmospheric smoke** — a real volumetric object (`ShaderNodeVolumePrincipled`)
  in the `ALD | Smoke` collection, created/synced/removed by `smoke.py` and
  rendered by the environment, never by the additive FX path and never by a
  new World generator. Controls in both UI surfaces; Remove ALD removes it.
- **Aesthetic variants** — `fx_style` CLASSIC / SOFT / VIVID map to glow
  strength, glow size and atmospheric fade without rebuilding geometry.
- **Directed show** — `ald.fx_show` composes 3 or 5 bursts using the existing
  hero/secondary/distant staggering; deterministic from the seed.
- **Benchmarks** — `preset_dev/bench_fx.py` measures creation, parameter
  update, clock refresh, frame evaluation (GN and Python), memory and render,
  against budgets declared with the hardware and scenario in
  `preset_dev/benchmarks.json`.

### Measured on this machine (AMD64, Windows 11, Blender 5.1.2)
- creation 5 fireworks 0.271 s; 5 meteors 0.010 s;
- update system 0.005 s; clock refresh 0.004 s;
- frame evaluation 24 frames: GN 0.074 s, Python 2.621 s;
- memory: 70 objects, 17 832 vertices, 933 attributes, 14.0 MB Python peak;
- render 128x72 1.457 s.

### Gate
- New P3 check: smoke lifecycle and volume shader, 5-burst show, style changes
  without geometry rebuild. `ALD GATE: PASS`.

## 2.29.0 - 2026-10-26
P1 and P2 of the operational plan: one persistent model, one geometric
reference and clock, backend parity, visual profiles and calibration.

### Fixed
- **P1-A** — the runtime is rebuilt from the event UID and the explicit object
  role, never from names; `random_key` is stored per event and derived from
  `(seed, creation slot)` so enabling/disabling events never changes the others;
  `FX_SCHEMA` 2 migrates old files; `undo_post`/`redo_post` rebuild the registry.
- **P1-B** — gravity follows the ALD Sky/FX Anchor axis and units; the launcher
  uses the anchor axis and ground; Physical mode bursts at `p_shell(T)`; the
  clock refreshes on origin/timing changes without rebuilding; a creation
  starts at the current frame.
- **P1-C** — a failed Geometry Nodes event falls back to the Python writer for
  that event only; mixed systems evaluate both backends (`gn` = all, per-event
  skips); trail energy/colour travel via the Geometry domain attributes.
- **P2-A** — the material contract is real: `event_color`, `stable_noise`,
  `age_norm` and `trail_u` drive colour and energy. The FX glow threshold
  default is 0.35 so the small particles actually bloom.
- **P2-B** — `preset_dev/calibrate_fx.py` renders the comparison matrix (night
  and sunset × no/narrow/wide halo, AgX, fixed camera/seed/exposure, plus a
  Standard control) and writes `preset_dev/calibration/metrics.json`.

### Gate
- New checks: persistent model (rename/disabling/migration), anchor gravity,
  `p_shell(T)`, clock refresh without rebuild, GN→Python fallback. `ALD GATE:
  PASS`.

## 2.28.0 - 2026-10-26
P0 of the operational plan: data safety and a correct FX compositing contract.

### Fixed
- **P0-A** — `preset_dev/baseline.py` records the declared version, the hashes
  of every Python file, the node-group schemas and the public FX flows
  (`preset_dev/baseline.json`). `preset_dev/P0_BASELINE.md` documents the
  expected failures and the evidence.
- **P0-B** — `Update FX` rebuilds the selected system by UID
  (`fx.update_system`) instead of creating a new one through the legacy
  `ald_fx_config` path. `Remove System` and `Duplicate System` coordinate the
  persistent record and the geometry. `fx.compile_system` is atomic: the
  previous objects are stashed and restored if the build raises. The neutral
  reset only detaches an ALD-owned compositor, never a user stack.
- **P0-C** — `snapshot.ensure` runs before every first mutation, including
  `compositor.build`, `fx.create_*`, `fx.compile_system` and `fx.apply_backend`.
  Removal ends in the REMOVED state (`scene["ald_removed"]`), which blocks all
  automatic re-entry until an explicit Apply/Build. `Detach` no longer clears
  the material tint, so it really keeps the result. Shared collections are
  never removed.
- **P0-D** — real B/F/A FX isolation: `ALD FX Base` (environment) and
  `ALD FX Only` (FX against a transparent/black world override). Coverage is
  `max(R, G, B)` clamped to 0..1, zeroed where the environment depth is in
  front of the FX (`ALD | FX Occlusion`, `ALD | FX Visible Coverage`). The
  recomposition is `C = (1-A)*Painted_B + F + Glare(F)`: the punch-out is
  coverage-driven and `ALD | FX Restore` adds the premultiplied F with
  Factor 1 (no image scaling). Zero FX is now the identity; an opaque occluder
  hides the particles. Nested FX collections are handled and the ALD view
  layers/transparent world are cleaned up on removal.
- **P0-E** — the read-only diagnostic never touches the depsgraph and reports
  `UNKNOWN` instead of an unproven `OK`; only the explicit `ald.fx_diagnose`
  operator evaluates positions and caches the report.

### Gate
- New checks: FX system operators (update/duplicate/remove), read-only
  diagnostics, real occlusion (behind/free render difference) and the zero-FX
  identity. `ALD GATE: PASS`.

## 2.27.1 - 2026-10-22
Fixed "Remove ALD from Scene" doing nothing when no valid snapshot exists.

### Fixed
- `Remove ALD from Scene` previously did nothing when there was no snapshot
  (or the snapshot had been captured after ALD was already applied). The
  World and compositor were left in their ALD state. Now, when no valid
  snapshot exists, ALD removes its own nodes from the World (replacing the
  ALD World Gradient with a simple neutral Background) and clears the
  compositor, bringing the scene back to a neutral state.
- The operator message now clearly reports whether a full restore happened
  or a conservative neutral reset was performed.

## 2.27.0 - 2026-10-22
Critical bug fix in the FX Python writer plus completion of the T24 visual
profile acceptance test.

### Fixed
- `_update_meteors` crashed with `'NoneType' object has no attribute 'data'`
  because the non-GN path of `_build_meteors` stores trail/head/fragment
  objects per-event (in `system["events"]`) but `_update_meteors` tried to
  read them from `system["trail"]`, `system["heads"]`, `system["fragments"]`
  which were always None. The updater now iterates over `system["events"]`
  and uses each event's own objects.

### Added
- Gate test T24 (Sunset/night, three FX profiles): renders Firework, Meteor
  and Bolide at fixed exposure and Standard view transform, verifying each
  profile is visible without diffuse clipping.

## 2.26.0 - 2026-10-22
The ALD Sky/FX Anchor is completed with an explicit terrain object and the
camera/terrain conflict check now reads the real ground mesh.

### Added
- **Ground Object** (Fase 4 of the plan): a mesh plane at the anchor
  elevation used as the terrain reference for conflict checks. The pointer
  `Scene.ald.fx_ground_object` holds the terrain mesh; operators and UI
  controls to create and inspect it (both surfaces).
- The conflict warning (T15) now reads the ground object's world matrix when
  a terrain mesh is assigned, falling back to the numeric elevation.

## 2.25.0 - 2026-10-22
The v2.24 compositor isolation is consolidated: the registration crash is
fixed, the ALD Sky/FX Anchor is added, and the acceptance matrix T25-T28 is
covered by the gate.

### Fixed
- `AttributeError: Writing to ID classes in this context is not allowed`
  when `fx._scene_id` wrote `settings.fx_uid` during panel draw. The write is
  now best-effort (`try/except`): the identity lives in `scene[ald_fx_id]`
  and the settings cache is only updated when Blender allows it.

### Added
- **ALD Sky/FX Anchor** (Fase 4 of the plan): a persistent Empty world
  reference with vertical axis, ground elevation and units scale. Operators
  and UI controls to create and inspect it. The anchor survives geometry
  rebuilds and is identified by UID, not by name.
- **Conflict warning (T15)**: when the camera points below the ground or a
  burst target is under the terrain elevation, the panel reports the
  conflict instead of silently generating underground coordinates.
- **Gate tests T25-T28** (`preset_dev/verify.py`): migration from an older
  schema, undo/redo alignment, failed-build safety, and UI surface parity.

### Changed
- `fx._scene_id` no longer crashes in restricted contexts (panel draw).
- `panels.draw_fx_advanced` shows the Anchor controls; `panels.draw_fx_launch`
  shows the conflict warning when present.

## 2.24.0 - 2026-10-22
The compositor FX isolation is corrected: the broken DIFFERENCE-based
separation is replaced with a clean environment / FX-only / coverage
pipeline. The diagnostic panel tells why an effect is not visible.

### Added
- `diagnostics.py`: per-event visibility report (OK, NO_GEOMETRY,
  DISABLED, MISSING_ATTRIBUTE, NON_EMISSIVE, HIDDEN, FUTURE, ENDED,
  OFF_CAMERA, OFF_CLIPPING) shown in the FX panel "Diagnostics" section.
- `preset_dev/fixtures.py` and `preset_dev/diagnose.py`: temporary fixtures
  (one meteor, one firework, user scene with HDRI + compositor + emissive
  material) and the FX diagnostic report.
- `preset_dev/audit_plan.py` updated for the new builder names and FX layer
  functions.

### Changed
- **Compositor FX isolation**: replaced the algebraically invalid
  DIFFERENCE of two emission passes with `C = (1-A)*Painted_B + F +
  Glare(F)`, where B is rendered from a base layer (FX excluded), F from a
  dedicated FX-only layer, and A is the FX coverage derived from F's
  luminance. Foreign emissive surfaces no longer enter the FX mask.
- Two view layers replace one: `ALD FX Base` (environment only) and
  `ALD FX Only` (FX only). The main layer keeps all passes for the
  painterly filters.
- The `energy` attribute on trails is stored via Geometry domain (not
  Instancer), matching what the ShaderNodeAttribute actually reads.
- The gravity of the scene now reaches every solver: position, velocity,
  shell rise, and meteor fall all use the same gravity vector.
- The velocity is the exact derivative of the position: the small-drag
  series was corrected (`exp(-x)` instead of the A expansion).
- Child sparks inherit the parent star's trajectory (position and
  velocity at emission) instead of being born away from the star.
- The train no longer travels after the head dies: the front of the train
  is frozen at the body's last position; residuals only fade.
- Negative ages are clamped so particles never move backwards before
  birth.
- The clock of a system is real: Timeline reads the origin frame, Preview
  is frame-independent, and the Burst Age shifts every system.
- Two systems of the same kind never collide: the runtime registry is
  keyed by system identity.
- Launchers are found by system/event identity and survive geometry
  rebuilds.
- Event counts are three distinct numbers: primary stars, pistil stars,
  and child sparks (the burst count is the number of bursts).

### Fixed
- The FX compositor isolation no longer produces false contributions from
  revealed surfaces behind FX (the N06 algebraic counterexample).
- The trails are emissive: they write the `energy` attribute the material
  reads and feed the FX glow.

## 2.23.0 - 2026-10-22
The audit plan of the user is applied: the events drive the geometry, the
clock of a system is real and the diagnostics say why an effect is not
visible.

### Added
- `diagnostics.py`: the report of the FX. Every event has a state:
  `OK`, `NO_GEOMETRY`, `DISABLED`, `MISSING_ATTRIBUTE`, `NON_EMISSIVE`,
  `HIDDEN`, `FUTURE`, `ENDED`, `OFF_CAMERA`, `OFF_CLIPPING`. The panel shows
  it in the "Diagnostics" section of the selected event.
- `preset_dev/fixtures.py` and `preset_dev/diagnose.py`: the temporary
  fixtures (one meteor, one firework, a scene with an HDRI, a custom
  compositor and an emissive material) and the report of the FX.

### Changed
- **The persistent events are the source of truth**. The creation writes the
  events, the geometry is compiled from them and an update never rewrites
  them. The identity of a system and of its events is stable.
- The runtime registry is keyed by the identity of the system: two systems
  of the same kind never collide.
- The clock of a system is real: `Timeline` reads the origin frame,
  `Preview` is independent of the frame and the Burst Age is the director
  control. The two backends read the same clock.
- The launchers are the manipulators of the events: they are found by their
  identity and they survive the rebuild of the geometry.
- The counts of an event are three different numbers: the primary stars, the
  stars of the pistil and the child sparks.

### Fixed
- The velocity was not the derivative of the position: the series of the
  small drag was wrong.
- The child sparks did not inherit the trajectory of the parent: they were
  born away from the star that emitted them.
- The train of a particle continued to travel along the trajectory of the
  head after its death. The front of the train is now the last position of
  the body.
- The trails did not write the `energy` attribute the material reads: the
  curves were dark and did not feed the glow.
- A negative age moved the particles backwards along the trajectory before
  their birth.
- The gravity of the scene did not reach the solver: the position and the
  velocity used the global constant.

## 2.22.1 - 2026-10-22
The add-on survives a reload of Blender, and the compliance with the
operational plan is now a script that can be run at any time.

### Fixed
- `register_class(...): already registered as a subclass 'ALD_FX_Event'` when
  Blender reloaded the add-on (it happens automatically when the files change
  on disk while the add-on is enabled): the registration is now idempotent.
  The classes are unregistered in the reverse order before being registered
  again, and the pointer on the scene is removed first, otherwise the settings
  class cannot be released.
- The camera and the sun of the transform state used the raw `matrix_world`:
  a stale matrix (or a missing constraint) was sent to the world, to the
  materials and to the God Rays. The evaluated matrix is used now.

### Added
- `preset_dev/audit_plan.py`: the audit of the operational plan, requirement
  by requirement (the eight invariants, the phases P0 to P3, the file map, the
  test matrix, the documentation and the Definition of Done). It prints
  `ALD PLAN AUDIT 69/70`: the only open item is the optional atmospheric
  smoke, that the plan asks to build only when it is really necessary.
- The gate checks the occlusion of the burst with the motion blur on: the
  particles stay behind the geometry.
- The gate checks that the meteors really cross the screen, not only that they
  are not aligned with the line of sight.

## 2.22.0 - 2026-10-22
The three actions on the scene are separated and the FX are visible at once.

### Added
- The three actions of the plan on the scene itself, in a "Scene" section of
  both surfaces:
  - **Bypass**: the add-on stops touching the scene, the look is kept;
  - **Remove ALD from Scene**: the complete removal, the scene comes back to
    the state registered before the first modification;
  - **Detach and Keep Result**: the look is kept but the add-on stops
    managing it (the FX objects, the markers and the internal properties are
    removed, the world, the materials and the compositor stay).
- The creation of the FX puts the 3D viewport in the camera view with the
  rendered shading: the bursts are visible at once instead of an empty sky in
  the solid mode.
- The gate verifies the three actions and the removal of the collection, of
  the orphan materials and of the node groups.

### Fixed
- The panel used the icon `EVENT`, which does not exist in Blender 5.1: the
  whole FX panel broke at draw time. The gate now validates the icons against
  the real list of the layout (1017 icons) instead of a curated one.
- "Remove ALD from Scene" did nothing when the original state was not
  registered (an old scene, a direct call without a palette): the removal now
  always happens and the limit is reported, as the plan requires.
- The removal of the internal properties changed the identity of the scene
  before the ownership was resolved, so the collection of the add-on survived.

## 2.21.0 - 2026-10-22
The two surfaces are now exactly the same.

### Changed
- The View3D sidebar and the Scene properties draw **the same controls with
  the same operators**: the "compact" mode is gone. Every control of the World,
  of the Shadows, of the Compositor, of the Camera Override and of the FX
  section is available in both surfaces, with the same values.
- The sidebar has the same structure as the Scene properties: the parent panel
  with the atmosphere, the material presets and the stack buttons, then the
  sub panels World & Shadows, Compositor Stack and FX Particles.
- The FX section of the sidebar shows the backend, the timing, the launch, the
  explosion, the look, the advanced controls and the actions, with the same
  fields as the Scene properties.

### Added
- The gate compares the controls drawn by the two surfaces and fails when
  they diverge, and it fails when a drawing function keeps a compact mode.

## 2.20.1 - 2026-10-22
### Fixed
- The legacy shooting stars of the world shader stayed active with the FX 3D
  backend: the old comets were still rendered together with the new ones.
  The backend now turns them off, like the legacy world fireworks.
- The legacy controls (the world fireworks and the world shooting stars) only
  appear in the Legacy World backend, in both the Scene properties and the
  View3D sidebar.
- The FX section is the first section of the View3D sidebar: the systems and
  the actions are reachable without scrolling.

## 2.20.0 - 2026-10-22
The milestone of the operational plan: a single complete and reversible
firework, with the Definition of Done verified by a script.

### Added
- `preset_dev/milestone.py`: the acceptance of the Definition of Done of the
  plan, point by point, with the filmstrip of the event and a JSON report.
  The thirteen checks: the visible launcher, the continuous rise, the burst
  at the expected point, the transfer of the position and the velocity to the
  stars, the decay of every component, the flash that turns off and the embers
  that survive, the energy that fades in time, the isolation of the FX layer,
  the systems manageable from both interfaces, the configuration kept by a
  reopened project, the restoration of the registered state by "Remove ALD
  from Scene" and the absence of a global purge.
- The launcher of a burst is a visible empty in the world: the user can grab
  it and the build reads its position back, so the shell really starts from
  the launcher. "Update FX" rebuilds the system and applies the new position.

### Fixed
- The persistent configuration is written by every path: `create_fireworks` and
  `create_meteors` store the system and its events, not only the operators. A
  project saved after a direct call keeps its configuration.

## 2.19.0 - 2026-10-22
Phase P3 of the operational plan: the cleanups and the refinements.

### Fixed
- The solver is numerically stable for a small drag: the closed form
  `p0 + v_inf a + (v0 - v_inf) A` cancels two large terms, the stable form
  `p0 + v0 A + g (a - A) / k` is used instead, with `expm1` and a series
  expansion of A for the small `k a`. The velocity uses the same form.
- The camera frame is read from the evaluated matrix: a camera with a
  constraint or a parent is followed correctly, with no stale matrix.
- The drift of the clouds and the phase of the legacy shooting stars follow
  the time in seconds, not the frame counter: the same state at 24, 30 and 60
  fps.
- The phase of the legacy shooting stars is independent from the wind of the
  clouds: the two movements are separated.
- The custom colours accept the HDR range (up to 4.0), like the palettes.
- The backend is chosen before any allocation: the two paths never build the
  same geometry twice, and the Python meshes are only created when the
  Python writer is the chosen backend.

### Added
- The Kamuro family: few thick stars, a long drooping tail and a warm core.
- The gate runs the P3 tests: the stability of the solver (the closed form
  and the series must agree, the velocity must match the position), the
  camera with a constraint, the time in seconds of the clouds and of the
  legacy stars and the Kamuro family.

## 2.18.0 - 2026-10-22
Phase P2 of the operational plan: the material contract of the particles and
the isolation of the FX layer in the compositor.

### Added
- The material contract of the plan: the points carry `role` (head, filament,
  grain, ember, flash, shell, pistil, spark, meteor), `age_norm`, `energy`,
  `trail_u`, `stable_noise` and `event_color`. The static ones are written by
  Python, the dynamic ones by the node group.
- The visual profile of every role (`fx.ROLE_ENERGY`): the head is the
  brightest, the filament is thinner and less energetic than the sparks, the
  embers fade slowly, the flash is a very short impulse.
- The dedicated view layer "ALD FX": the collection of the add-on is excluded
  from it, so the difference between the two emission passes is exactly the
  contribution of the FX. The other emissive surfaces of the scene never
  enter the mask.
- The punch out: the painterly filters receive a base without the FX, then
  the particles are recomposed with their exact coverage and the dedicated
  glow is added once, on the FX only.
- The FX Glow Threshold is exposed in the FX section.
- The gate verifies the isolation: an emissive surface that is not ALD keeps
  the same value with and without the bursts.

### Changed
- The mask of the FX is not the emission pass any more (it also contained the
  other emissive surfaces of the scene) but the difference between the main
  layer and the dedicated FX layer.
- The cost of the isolation is one more view layer in the render.

## 2.17.0 - 2026-10-22
Phase P1-D of the operational plan: the meteors are events and the Hero
Meteor has its own preset.

### Added
- The meteor presets (`fx.METEOR_PRESETS`): a normal meteor and the
  **Bolide**, the cinematic one: bigger head, brighter emission, longer life,
  a long persistent train, more fragments and a smaller angular jitter.
- The operator `ald.fx_bolide` ("Create Hero Meteor") and its button in the
  FX section.
- The gate verifies the preset: the bolide is more than twice as big, it
  lives longer, its train is more than twice as long and outlives the head,
  it leaves more fragments and the velocities of the shower stay almost
  parallel, so the radiant emerges.

### Changed
- The meteors are built from the preset: the birth spacing, the life range,
  the speed range, the drag, the radius of the head, the length of the train
  and the number of fragments follow the chosen kind.
- The event kind of the persistent schema knows the `BOLIDE`.

## 2.16.0 - 2026-10-22
Phase P1-C of the operational plan: the firework is a complete event.

### Added
- The rising shell: the firework now starts from a launcher, climbs with a
  short trail and bursts at the target. The shell is a body of the node group
  (and of the Python writer) with its own birth, drag and lifetime.
- The operational equations of the plan, in `fx._rise_velocity()`:
  `v_inf = w + g/k`, `A(T) = (1 - exp(-kT))/k`,
  `v0 = v_inf + (pB - pL - v_inf T)/A(T)` and the stable limit without drag
  `v0 = (pB - pL - 0.5 g T^2)/T`.
- The continuity at the burst: the stars are born exactly at `p_rise(T)` and
  their initial velocity includes the residual velocity of the shell
  (`v_star0 = v_rise(T) + s_i d_i`).
- The event properties: the launch mode (Director or Physical), the rise
  time, the drag, the speed and the gravity of the FX.
- The gate runs the acceptance condition of the phase: the shell reaches the
  burst point, the stars are born there, they inherit the velocity of the
  shell, the shell disappears at the burst and the event is identical after a
  frame jump.

### Changed
- The burst happens at the end of the rise: the lookdev renders follow the
  new timing (the sequence shows the launch, the rise, the burst and the
  expansion).

## 2.15.0 - 2026-10-22
Phase P1-B of the operational plan: the scene can be restored.

### Added
- `snapshot.py`: the state of the user is saved before the first ALD
  modification (the world and its background link, the strength and the
  colour, the sun with its ownership, the compositor group and the render
  passes). The snapshot is a JSON string in the scene: it is explicit and it
  survives a save.
- The operator `ald.remove_from_scene` ("Remove ALD from Scene"): it removes
  the FX systems and the objects they own, restores the materials, the world,
  the sun, the passes and the compositor from the snapshot, and removes the
  internal properties only after a successful restore.
- The maintenance mode suspends the handlers and the callbacks while the
  scene is restored, so nothing re-applies the look in the middle.
- The gate runs the acceptance condition of the plan: a scene with an HDRI
  world, a custom sun, an emissive material and a pre-existing compositor
  stack returns to the registered state.

## 2.14.0 - 2026-10-22
Phase P1-A of the operational plan: one interface, one backend semantics.

### Added
- Shared drawing functions: the Scene properties and the View3D sidebar draw
  the same data with the same operators (`draw_atmosphere`, `draw_world`,
  `draw_shadows`, `draw_camera_override`, `draw_compositor`, `draw_fx`,
  `draw_stack_actions`). The sidebar is more compact, the state is the same.
- The FX section follows the structure of the plan: Systems, Timing, Launch,
  Explosion, Look, Advanced and Actions, with the list of the persistent
  systems and events (selection, enabled, duplicate, remove).
- The operators `ald.fx_select_system`, `ald.fx_select_event`,
  `ald.fx_duplicate_system` and `ald.fx_remove_system`.
- The look controls: the energy decay of the heads, of the grains and of the
  embers, plus the atmospheric fade (the emission is attenuated with the
  distance from the camera, in the nodes and in the Python writer).
- `Developer Mode` hides the debug controls (the Geometry Nodes or Python
  backend) from the normal interface.
- The gate checks the backend exclusivity, the parity of the two surfaces and
  the icons used by the panels.

### Fixed
- The backend is really exclusive: `OFF` hides the 3D systems and the legacy
  shader and preserves the data, `Legacy World` enables the legacy shader and
  hides the systems, `FX 3D` does the opposite. The change applies at once.
- The legacy world controls only appear in the Legacy World backend.
- The panel used an icon that does not exist in Blender 5.1 and broke the
  whole FX panel at draw time: the gate now validates the icons.

## 2.13.0 - 2026-10-22
Phase P0-B of the operational plan: the state is persistent and the identity
is robust.

### Added
- Persistent schema: `ALD_FX_System` and `ALD_FX_Event` (PropertyGroup and
  CollectionProperty) describe the systems and their events. The scene holds
  the schema version and its own UUID; a system holds its UUID, its type, its
  enabled flag, its seed, its timing mode and its origin; an event holds the
  launcher, the target, the family, the size, the birth, the duration, the
  speed and the glow profile.
- `fx.store_system()` writes the configuration after a creation: the runtime
  registry is only a cache, the saved file is the source of truth.
- `fx.rebuild_registry()` rebuilds the runtime state from the persistent
  configuration, the collection ownership, the object tags and the ALD
  modifiers. It runs after `load_post` and reuses the geometry saved in the
  file: nothing is regenerated.
- The node groups carry a build marker (`ald_schema`): a group saved with an
  older marker is rebuilt, the modifiers are remapped on the new structure and
  the old group is removed only when nothing uses it any more.
- The gate runs the P0-B tests: the fixture (save, reopen, list, sliders,
  clear per kind, animation), the scene duplication and the migration of an
  old node group.

### Changed
- The identity of a scene is a persistent UUID and not the hash of its name.
  The first scene that claims an identity keeps it: a duplicated scene
  receives a new one and an independent copy of the systems, and the clear of
  the copy never touches the original.

## 2.12.0 - 2026-10-22
Phase P0-A of the operational plan: the dynamics are corrected and the two
backends share the same deterministic data.

### Fixed
- **FX-01**: the Geometry Nodes decay was inverted: the scale grew with the
  age instead of shrinking, and the flash grew until the death. The shape
  decay is now `s(u) = m + (1 - m) * (1 - u) ** p` with `u = age / life`.
- **FX-01**: the brightness is no longer only a scale: the energy
  `e(u) = (1 - u) ** q` is written as the `energy` attribute and the material
  multiplies the emission strength by it.
- **FX-02**: the number of samples of the grains overwrote the number of
  bursts, so the composition rule used a wrong total and every burst was
  pushed to the left of the frame. The names are now `burst_count`,
  `spoke_count` and `sample_count`.
- **FX-03**: the meteors moved along their own line of sight. The start
  points are now spread on a distant plane and the velocities are almost
  parallel in world space, so the radiant emerges perspectively and the
  meteors cross the screen.
- **FX-04**: the head, the train and the fragments share a single
  `event_birth`; the train lifetime derives from the body and from the
  persistence window. `Fade Window = 0` means explicitly no persistence.
- **FX-05**: the origin of the child sparks and of the fragments is computed
  once at the emission instant and reused by both backends.

### Added
- `fx.burst_population()` builds the deterministic initial conditions of a
  burst once: the Geometry Nodes attributes and the Python writer consume the
  same data, so the backends cannot diverge.
- The gate runs the P0-A tests: the decay at u = 0, .25, .5, .75 and 1 for the
  head and the flash, the parity of the positions and the scales between the
  two backends, the future event (nothing visible and no overflow before the
  birth), the composition rule with 1, 3 and 5 bursts, the meteor timing and
  the screen travel of the meteors.
- `Meteor Persistence` in the FX panel.

## 2.11.1 - 2026-10-22
### Added
- `preset_dev/ui_probe.py`: the UI verification is now a tool of the
  repository. It opens a fresh Blender, enables the add-on, creates the FX
  systems and writes the screenshots of the sidebar panel and of the Scene
  properties (Anime Look Director, World & Shadows, Compositor Stack and FX
  Particles). The `--wait` argument gives the time to scroll the properties
  before the capture.

## 2.11.0 - 2026-10-22
### Changed
- The Burst Age slider no longer rebuilds the FX system: it writes the age
  offset of the node group modifiers, so the deterministic data stays
  untouched and the slider is real time (2.3 ms instead of 428 ms per step,
  189 times faster). The Composition Offset is applied immediately as well.
- The spread, the composition offset and the Geometry Nodes toggle keep the
  rebuild, because they change the geometry itself.
### Added
- The gate checks that the Burst Age slider moves the burst without creating
  a single object and without rewriting the deterministic data.

## 2.10.1 - 2026-10-22
### Added
- `preset_dev/lookdev_families.py`: renders Chrysanthemum, Peony and Willow
  with the same palette, the same camera and the same seed, so the families
  can be compared by shape alone (acceptance condition of the phase 5 of the
  technical guide), with a contact sheet and the recorded metadata.

## 2.10.0 - 2026-10-22
### Fixed
- Opening a new file no longer leaves a stale FX system in the panel: the FX
  registry and the camera/transform caches are cleared by a `load_post`
  handler. The scene identity is the name of the scene, so a new file with the
  same scene name used to inherit the systems of the previous one.
### Changed
- The frame handler skips the systems evaluated by the node group: in the
  Geometry Nodes path it does not touch a single vertex.
### Added
- The gate runs the last mandatory test of the technical guide: opening a new
  file with the add-on active must keep the handlers registered, clear the
  caches and still allow the palette, the stack and the FX to be built.

## 2.9.2 - 2026-10-22
### Fixed
- The objects built by the Geometry Nodes path are tagged with their kind:
  the FX panel listed the fireworks system as empty and the per system
  clear button could not remove them.
### Added
- `preset_dev/lookdev_fx.py`: the comparison renders required by the technical
  guide (with and without the dedicated FX glow, with an occluder, with motion
  blur and a short animated sequence) plus a `metadata.json` with the
  resolution, the camera, the seed, the exposure, the view transform and the
  renderer.
- The gate checks that the FX systems are listed by the panel and that every
  node group object carries its kind.
- The UI was verified with real screenshots of the sidebar panel and of the
  Scene properties (Anime Look Director, World & Shadows, Compositor Stack
  and FX Particles).

## 2.9.1 - 2026-10-22
### Added
- The node group reproduces the drag free limit with the ballistic solution
  (`p0 + v0 * a + 0.5 * g * a²`), exactly like the Python solver: the closed
  form loses precision when the drag goes to zero.
- The gate now runs the mandatory tests of the technical guide that were still
  missing: identical state after a frame jump, the same physical state at 24,
  30 and 60 fps, the drag free and gravity free limits, the child sparks that
  outlive the head of the star and the occlusion of the burst behind a
  building.

## 2.9.0 - 2026-10-22
### Added
- New `ALD | FX Trail GN` group: the thin filament of every star is now a
  curve tube evaluated by the nodes (Points to Curves + Curve to Mesh), with
  the same taper and the same growth of the tail.
- The central flash of a burst is evaluated by the node group too, with the
  `Decay Power` input that reproduces the `sqrt` falloff of the flash.
- The meteors (head, persistent train and burning fragments) are evaluated by
  the node groups; the Python writer is no longer used by default.
- The train retracts when the body dies
  (`train = max(0, min(age, trail) - (age - life))`) and the persistent train
  of a meteor thins out with the new `Fade Window` input.
### Changed
- The frame handler no longer writes any geometry in the Geometry Nodes path:
  the whole FX system is evaluated by the nodes (2.5 ms per frame against
  121.7 ms for the Python writer, measured with 4 bursts and 4 meteors).
- The gate verifies the meteors too: the node evaluation must match the
  Python solver within 1 mm and no Python meteor may stay in the scene.
- The `GN Particles (Prototype)` toggle keeps the Python writer available as
  a fallback.

## 2.8.0 - 2026-10-22
### Added
- The Geometry Nodes group now evaluates the whole burst population, not only
  the heads: the trail grains, the inner pistil (heads and grains) and the
  child sparks are all computed by `ALD | FX Burst GN`.
- New per point attributes: `tau` (age offset of the sample), `jitter`
  (constant scatter of a grain) and `use_decay` (follow the head brightness
  decay or keep the baked size). The group exposes `Trail`, `Age Offset` and
  `Min Scale` so the node evaluation matches the Python solver exactly.
- The child sparks are now emitted from the position and velocity the parent
  star had at the emission instant: a spark is a body of its own, not a
  particle of a moving source.
- The gate measures the parity between the node evaluation and the Python
  solver (heads, grains, pistil, pistil grains and sparks must agree within
  1 mm) and checks that the Python path is still available as a fallback.
- `GN Particles (Prototype)` toggle in the FX panel.

## 2.7.0 - 2026-10-22
### Added
- Geometry Nodes prototype for the burst heads: the deterministic data
  (birth, lifetime, velocity, drag, radius) lives in point attributes and the
  analytic motion is evaluated every frame by `ALD | FX Burst GN`
  (Scene Time, Set Position, Instance on Points) instead of Python.
- `GN Heads (Prototype)` toggle in the FX panel; the gate now verifies that the
  node group exists, contains the expected nodes and is attached to a burst.

## 2.6.0 - 2026-10-22
### Added
- Denser, more granular spark trails: 16 samples per star with per-grain
  jitter and brightness variation, so the strings read as embers and not as
  dotted lines.
- Meteors now leave burning fragments and a persistent train that outlives the
  head before fading out.
- Composition controls in the FX panel: `Burst Spread` and a world-space
  `Composition Offset` to frame the bursts by hand.

## 2.5.0 - 2026-10-22
### Added
- Inner contrasting **pistil** population for every burst: a smaller, slower
  shell with its own colour and beaded trail, as in the Hanabi references.
- The FX panel now lists the systems present in the scene and can clear
  fireworks and meteors independently.
### Verified
- Occlusion: a solid object placed in front of a burst hides the particles
  (the emission pass is depth tested), confirmed with a render sample.

## 2.4.0 - 2026-10-22
### Added
- Beaded spark trails: every star now leaves a granular string of emissive
  grains that thins out towards the tail, with a faint filament for cohesion.
  This replaces the continuous ribbon look of v2.3.0.
- `Burst Age` control (0..6 s) in the FX panel: the whole system can be
  scrubbed through the explosion phase without touching the timeline.
### Fixed
- The FX frame handler now reads the authoritative `fx_age` setting, so the
  burst phase stays consistent while scrubbing frames.

## 2.3.0 - 2026-10-22
### Added
- Animated FX: geometry is allocated once and updated in place from the
  analytic solver, so the fireworks and meteors evolve over the timeline
  without recreating objects every frame.
- Burst composition with roles: the first burst is the hero, the others are
  secondary or distant, with staggered birth times and different families
  (Chrysanthemum, Peony, Willow).
- Fireworks and meteors now live in independent per-scene systems and can be
  created, updated and cleared separately.
### Fixed
- FX placement no longer reads a stale camera matrix, so bursts land in frame
  when the camera has just been moved.
- Dead particles are parked with a non-zero radius, avoiding degenerate
  faces that crashed EEVEE.

## 2.2.0 - 2026-10-21
### Added
- Compositor separation for the 3D FX: an emission-pass mask restores the
  particle cores after the painterly filters, so Kuwahara, Ink and Haze never
  blur the fireworks while the environment stays painted.
- Dedicated FX glow with its own strength, size and threshold controls,
  independent from the sun-tinted atmospheric halation.

## 2.1.0 - 2026-10-21
### Added
- Deterministic FX solver: analytic linear-drag motion in seconds, stable
  zero-drag limit, hashed per-particle randomness, and frame-jump safety.
- Firework families (Chrysanthemum, Peony, Willow) with tapered trails, child
  sparks, an ephemeral central flash and configurable burst age.
- Meteors sharing one radiant direction, as in a real shower.
- FX Backend selector (Disabled / Legacy World / FX 3D) so the two generators
  are never active at the same time.
- Gate coverage for the FX system: per-scene ownership, clear isolation,
  reproducibility, frame-rate independence and orphan control.
### Fixed
- FX collections are owned per scene and clearing one scene never touches
  another; orphan ALD datablocks are cleaned without global purges.
- Disabling the world gradient restores the original background colour.
- `ald.remove` no longer detaches a compositing tree that does not belong to
  ALD; frame and depsgraph handlers are now persistent.

## 2.0.1 - 2026-10-20
### Fixed
- FX fireworks now use tapered trails, hollow shell starts, stronger droop and
  compact spark clouds for more physically legible bursts.

## 2.0.0 - 2026-10-20
### Added
- FX particle architecture in `fx.py`: physically placed 3D fireworks and
  shooting-star trails with camera-space placement, gravity, parabolic droop,
  multi-shell depth, hoshi heads and saturated chemical-like palettes.
- Operators `ald.fx_fireworks`, `ald.fx_meteors` and `ald.fx_clear`, plus an
  FX Particles panel.
### Changed
- The sky/world shader remains responsible for clouds, stars, Milky Way and
  atmosphere; explosions and meteors now have real 3D depth and overlap.

## 1.1.4 - 2026-10-20
### Fixed
- Hanabi uses horizon-aligned local axes on the stereographic disk, a stronger
  parabolic weeping-willow droop, three radial spark shells and constant
  linear trail width, replacing flat single-ring bicycle-wheel geometry.
- Bright hoshi star-heads at outer, mid and inner radii add spherical depth;
  hot heads and trails use separate 5.5x/9.5x HDR boosts.
- Fireworks altitude mask widened so hero bursts remain visible near the
  horizon and in the upper sky.
- World gradient marker 27.

## 1.1.3 - 2026-10-20
### Fixed
- Hanabi fireworks use true 2D stereographic Voronoi grids, low randomness and
  a cell guard, eliminating 3D cell slicing, wallpaper repetition and hard
  clipping at cell boundaries.
- Fireworks are hollow expanding spark shells with fine beaded trails, hoshi
  tips, contrasting pistils, embers and tiny center cores instead of solid
  bicycle-wheel discs.
- High-chroma analogous palette families replace complementary color mixing;
  layers are summed as independent RGB vectors instead of a fixed 50/50 color
  mix, preserving saturation through AgX.
- World gradient marker 26.

## 1.1.2 - 2026-10-20
### Fixed
- Milky Way socket is now connected to its mask and its star-density boost;
  the Milky Way toggle really controls the galactic river.
- Fireworks use continuous 3D Voronoi cell centers projected onto the local
  tangent plane, eliminating the atan2 seam and tying Fireworks Scale to the
  cell geometry.
- Shooting stars are needle-thin with a small diffraction cross and zenith
  masking, eliminating horizon tadpoles.
- Fireworks color is separated into a hot core and saturated colored
  filaments/embers, avoiding AgX whiteout.
- World gradient marker 25.

## 1.1.1 - 2026-10-20
### Fixed
- Shooting stars and Hanabi fireworks now use true 2D Voronoi cells on
  stereographic/cylindrical sky coordinates, eliminating spherical 3D cell
  artifacts and round blobs.
- Added Milky Way: a warped galactic river with a dark dust rift, cyan/violet
  palette and star-density boost.
- Sun Beams threshold raised to 3.5 so beams originate from the sun disk, not
  from stars or fireworks.
- Fireworks use larger hero bursts, gravitational droop, radial spokes,
  peony/pistil rings, embers and a radial color gradient.
- World gradient marker 24.

## 1.1.0 - 2026-10-20
### Added
- Sun Beams and Sun Glow toggles directly in the Sun controls; Apply Palette
  disables stale God Rays from Stage Backlight and restores the preset glow.
- Procedural shooting stars with cell-local 3D trajectories, independent hash
  channels, phase animation and HDR meteor heads.
- Procedural Hanabi fireworks with radial Voronoi spokes, peony/pistil rings,
  soft burst glow and per-cell gold/magenta/cyan palette.
### Changed
- World gradient marker 23.

## 1.0.8 - 2026-10-20
### Fixed
- Stars are now anti-aliased PSF points: existence, magnitude and temperature
  use independent Voronoi Color channels (X/Y/Z), with two tiers at
  `Star Density * 1.30` and `* 0.72`, plus Airy hero stars at `* 0.36`.
  Magnitudes have a guaranteed floor and the final tint is 12x HDR.
- Cloud morphology uses Perlin-Worley coupling: macro envelope gates billow and
  Voronoi lobes so open sky stays clean and cumuli gain rounded edge lobes.
- World gradient marker 22.

## 1.0.7 - 2026-10-20
### Fixed
- Kuwahara Painterly is masked by geometry, so the sky and stars stay sharp
  instead of being smeared by the anisotropic filter.
- Pinpoint Poisson stars: no domain warp, two sharp Voronoi tiers with tight
  radii, severe per-cell hash culling and a 3.8x tint; no more oval blobs.
- Horizon Offset now truly shifts the horizon line, sky gradient, cloud fade
  and star zenith masks.
- Apply Palette resets Sun Size, Sun Strength and Cloud Wind and realigns
  Custom Colors to the preset.
- Contrails are tinted by Cloud Light and default to 0.0 in all presets.
- Removed the obsolete micro-star specification from AGENTS.md.
- World gradient marker 21.

## 1.0.6 - 2026-10-20
### Fixed
- Apply Palette now re-enables `world_gradient`, `sun_disk`, `clouds` and
  `stars`, so a palette change restores the cloud controls and the sky UI.
- Removed the hidden `star_amount * star_strength` double multiplication.
  `star_strength` is now the visible preset star amount and the shader reads it
  directly, so raising Star Amount to 1.0 gives 100% of the stars.
- Custom color synchronization is guarded with `_syncing_style`, avoiding seven
  consecutive world/material rebuilds when Custom Colors is active.
- Starfield stars are no longer sub-pixel: celestial domain warp, readable
  tier radii (0.14/0.12/0.10), hash culling and a 10x glow.
- Sidebar now includes Sun Disk Size/Strength and the shadow-tint X button,
  matching the Scene panel layout.
- World gradient marker 20.

## 1.0.5 - 2026-10-20
### Added
- Dedicated Custom Colors entries for Cloud Shadow, Cloud Mid and Cloud Light.
  They synchronize to the active preset when Custom Colors is enabled or the
  palette changes, and they update the world shader independently of Horizon,
  Sun and Shadow.
- Three-tier clustered starfield driven by per-cell Voronoi Color hashes:
  dense stardust (`Star Density * 2.2`), medium constellation stars (`* 0.90`)
  and soft hero stars (`* 0.38`), with translated grids, random warm/cool
  temperatures and a 6.0x palette-tinted glow. This fixes the near-invisible
  v1.0.4 stars caused by one-octave Perlin culling thresholds.
- World gradient marker 19.

## 1.0.4 - 2026-10-20
### Changed
- Cloud color is fully independent from Horizon Color: removed the aerial
  fade/mix, linked the cloud glow directly into the cloud layer, removed the
  custom-color overrides for Cloud Shadow/Mid, and made the Cloud Mid fallback
  neutral `(0.6, 0.6, 0.7)`.
- New clustered painterly starfield: low-frequency constellation mask, sparse
  background micro-stars, soft gouache hero stars with halo, zenith/sun/cloud
  masks, and a palette-tinted star glow based on Cloud Light.
- All seven presets now carry explicit contrail, sun glow, sky accent, horizon
  offset/softness, star amount and star density values; Apply Palette syncs
  Sky Accent and the atmosphere controls.
- Removed franchise names from the UI and documentation preset labels; Cloud
  Flatness now reads "0 = billowy cumuli, 1 = flat horizontal strata".
- World gradient marker 18.

## 1.0.3 - 2026-10-20
### Fixed
- `_sample_cloud_density()` now returns `(rho, envelope, warped_pos)`. The rho
  path is unchanged from v1.0.2, so the silhouette is pixel-identical. A
  low-frequency envelope (`Detail 2.0`, `Roughness 0.45`, `Distortion 0.15`,
  macro scale) drives the solar derivative, eliminating internal Cloud Light
  speckles caused by sixth-octave density wobble.
- Solar ray step is 0.055 rad; body detail is 0.010 and the Shadow -> Mid step
  is -0.022..0.006.
- Silver lining is restricted to the outer edge: fringe top +0.022, fringe
  squared and scaled by 0.95, sun edge 0.000..0.022, plus a coverage presence
  gate. Internal concavities are no longer filled by Cloud Light.
- Apply Palette now resets `horizon_offset`, `horizon_softness`, `contrails`,
  `star_strength`, `star_density` as well as the cloud/glow controls.
- World gradient marker 17.

## 1.0.2 - 2026-10-20
### Fixed
- Restored the organic v1.0.0 cloud morphology: `_sample_cloud_density` returns
  `(rho, warped_pos)` with macro 0.66 + billow 0.22 + Voronoi puff 0.12,
  Detail 6.0/5.0, Roughness 0.58/0.54, domain warp 0.28. The smooth v1.0.1
  banks are gone.
- Removed `crown_curve` and `rim_total`. Cloud Light now comes only from
  `fringe * 0.92 * sun_edge * gamma`, scaled by Cloud Rim Boost. The cloud body
  stays Cloud Shadow / Cloud Mid even at Delta Gain or Rim Boost 4.0.
- Solar derivative is back on the full density with a 0.045 rad view-ray step;
  detail is 0.018 contour and 0.016 body; body is a single -0.018..0.008
  Shadow -> Mid step.
- SUMMER_NOON restored to flatness 0.25, scale 3.2, amount 0.70 and the v1.0.0
  cumulus colors.
- Apply Palette resets Cloud Scale, Delta Gain and Rim Boost as well as the
  other per-preset cloud/glow controls.
- World gradient marker 16.

## 1.0.1 - 2026-10-20
### Fixed
- `_sample_cloud_density` now returns `(rho_shape, rho_smooth, warped_pos)`.
  Macro Detail dropped to 1.8 / Roughness 0.42, high-frequency Perlin removed
  from the silhouette; two Voronoi dome octaves are masked by the macro bank.
  This removes torn-paper edges and isolated Voronoi cells.
- Solar derivative uses the smooth density and a 0.08 rad view-ray step, so
  high-frequency octaves no longer fragment the internal shadow.
- Cloud shading uses two steps with a 0.55 half-shadow plateau, then a
  0.022..0.042 crown, for four discrete gouache bands.
- SUMMER_NOON recalibrated: flatness 0.18, scale 2.4, amount 0.65, lavender
  shadows and bright cumulus colors.
- Apply Palette now resets `cloud_delta_gain`, `sun_glow` and
  `sky_accent_amount` as well as the per-preset cloud style.
- World gradient marker 15.

## 1.0.0 - 2026-10-20
### Added
- `_sample_cloud_density()` helper: projects any sky-dome ray through the
  curved shell, applies domain warping and returns a multi-octave fBm density
  plus the warped cloud position.
- Cloud shape is now fBm-dominated: macro 0.66 + billow 0.22 + high-frequency
  Voronoi puff 0.12, with domain warp 0.28. The weights were calibrated from
  the first 62/24/14 + 0.42 test, which produced fragmented holes in the
  viewport; the requested morphology/structure is preserved without the
  spherical Voronoi grid.
- Solar finite difference is now computed on the **sky dome**: displace the
  view ray by 0.035 rad toward `normalize(sun + zenith*0.65)`, then call the
  same density helper again. No 3D cell mismatch.
- Crisp silhouette: `coverage_top = coverage_center + 0.018`; detail is
  injected into the contour (`*0.018`) and body (`*0.022`) separately.
- Three cel bands: tight `body_mix` -0.014..0.002, crown 0.014..0.028 at
  0.85, rim = MAX(crown, fringe*sun_edge*gamma), then Rim Boost.
- Contrails remain straight gnomonic filaments.
- World gradient marker 14.

## 0.9.9 - 2026-10-20
### Fixed
- Contrails now use gnomonic `X/Z`, `Y/Z` coordinates instead of the curved
  shell `planar_uv`; a constant-u filament stays straight in the sky rather
  than bending into arcs. World group marker 12 -> 13.

## 0.9.8 - 2026-10-20
### Changed
- Cloud overhaul: domain-warped coordinates (`warp_noise` at 0.55*Cloud Scale,
  centered and scaled 0.32), a low-frequency macro bank (0.42*Cloud Scale,
  weight 0.26), and a separate soft silhouette density (0.36 Worley + 0.38 N1
  + 0.26 macro). High-frequency detail is injected only into `body_signal`.
- Per-cloud self-shadow: `light_dir = normalize(sun + zenith*0.65)` with a
  `0.38/Cloud Scale` step applied after Mapping; `mu_weight` removed.
  Crown highlight adds `0.35 * smoothstep(0.03, 0.11, body_signal) * sun_edge`
  to the rim.
- Contrails rebuilt in planar space: straight `u = 0.82X + 0.57Y` filaments
  with `v = -0.57X + 0.82Y` length fade, not spherical level sets.
- World gradient marker bumped 11 -> 12.

## 0.9.7 - 2026-10-20
### Fixed
- **Cloud Amount is now coverage, not opacity.** It drives the density
  threshold `tau0 = 0.68..0.42`, plus a tiny 0..0.03 gate. Low Amount leaves
  fewer compact opaque clouds instead of transparent ghosts.
- **Solar finite difference moved after Mapping** and scaled by
  `0.12 / Cloud Scale`. Detail is shared between both samples, so the step no
  longer spans a full noise period and no longer creates random light patches.
- **Contrails are an isoline**: `abs(noise - 0.60)` mapped 0..0.008 -> 1..0,
  instead of a monotonic MapRange that filled a third of the sky.
- World gradient marker bumped 10 -> 11 to force existing scenes to rebuild.

## 0.9.6 - 2026-10-20
### Fixed
- The Sidebar version label used `bpy.context.preferences.addons[...].module`,
  which is a path string in Blender 5.1, so `addon.module.bl_info` raised on
  every panel draw and made the N panel disappear. It now reads
  `sys.modules[__package__].bl_info`.
- Version 0.9.6.

## 0.9.5 - 2026-10-20
### Fixed
- Bumped the world-gradient group marker from 9 to 10. The 0.9.4 shader change
  was not rebuilding existing scenes because `ald_build` had not changed, so
  Blender kept the old beige-cloud graph. Reloading with 0.9.5 now forces the
  new edge-only Cloud Light graph.

## 0.9.4 - 2026-10-20
### Fixed
- Removed the remaining 8 % Cloud Light body base. The silver lining is now
  strictly `fringe * sun_edge * gamma`, so Cloud Amount 1.0 keeps the full
  violet/mauve body instead of turning beige.
- Sidebar N now prints the loaded add-on version (`v0.9.4`) so stale Python
  modules are immediately visible.

## 0.9.3 - 2026-10-20
### Fixed
- Cloud **Cloud Light** had a 35 % baseline across the whole cloud body, so
  increasing Cloud Amount toward 1.0 exposed a flat beige interior. The rim
  is now edge-local: 92 % fringe weighting plus an 8 % body base. Full coverage
  keeps the violet/mauve body and a thin silver lining.
- Version 0.9.3.

## 0.9.2 - 2026-10-20
### Fixed
- Sidebar N panel now exposes **Cloud Amount** and **Cloud Scale** alongside
  Cloud Flatness, so the cloud controls match the Scene panel.

## 0.9.1 - 2026-10-20
### Added
- **Per-preset cloud style**: `cloud_flatness`, `cloud_scale`,
  `cloud_rim_boost` and `cloud_amount` are stored in each preset and applied
  only when the effective palette key changes. Manual slider changes survive
  world/cloud refreshes on the same palette.
- AFTER_SCHOOL now uses flatness 0.90, scale 4.0, rim 2.0 and amount 0.90 for
  layered Persona-style bands; SUMMER_NOON uses flatness 0.25, scale 4.0 and
  amount 0.75 for small cumuli.
- Cloud Flatness now blends the raw spherical view (billowy) with the curved
  planar shell (strata), so 0 and 1 are genuinely different morphology, not
  just a Z stretch.
- Reference QA: P3R After School bands, cyan/white cumulus reference and the
  Oga/Persona artbooks were used to choose the per-preset values.

### Changed
- Palette changes sync style values behind a `style_syncing()` guard, so
  property update callbacks cannot recurse.
- Version 0.9.1.


## 0.9.0 - 2026-10-20
### Added
- **AFTER_SCHOOL** ("After School Sunset") palette: salmon-pink horizon,
  lavender-indigo zenith and backlit violet cloud bands, calibrated for AgX.
- **Sun Glow**: two Mie lobes around the sun - a narrow corona
  (`gamma+^16 * 0.65`) and a wide horizon-weighted haze
  (`gamma+^3.5 * smoothstep(0.75, 0.0, |Vz|) * 0.45`), summed, scaled by the
  new Sun Glow input (normalized to 0.45), tinted by Sun Color and added before
  the clouds. The opposite horizon stays cool.
- **Cloud Flatness**: exact curved-shell point
  `(Vx*t, Vy*t, Vz)` with `t=0.55/(max(Z,0.015)+0.18)` and Mapping scale
  `(0.75, 0.75, 1.25+3.0*Cloud Flatness)`; 0 = billowy Ghibli cumuli,
  0.65 = current 3.2 strata, 1 = Persona bands.
- **Perlin-Worley cloud density**: inverted Voronoi F1 lobes (0.38) plus two
  Perlin layers (0.44 base, 0.18 erosion) remove the sponge/camouflage look.
- **Solar finite difference**: full density is resampled at
  `p_cloud + 0.12 * L`; `delta = rho_here - rho_toward_sun` drives the
  Shadow/Mid body split and the sunward Silver Lining. The former hidden
  `x3` delta and `x2` rim transfers are now explicit `Delta Gain` and
  `Rim Boost` sliders, default 1.0.
- **Aerial blending + accent**: low clouds blend chromatically toward
  `Horizon Color`; an optional `Sky Accent` color/amount paints the
  turquoise/coral band around the mid-sky stop.
- **Micro starfield**: Voronoi density is multiplied by 2.5, the core is
  0.040 with POWER 2.5, and a Scale-45 noise magnitude mask (0.48..0.78) culls
  dim cells and varies star brightness. A low-intensity halo keeps the core
  legible at 1080p.
- **Optional contrails**: a high-altitude, horizontally stretched noise ribbon
  with its own `Contrails` control, off by default.
- New ground/horizon/mid-sky gradient mapping: ground is constrained below
  `Z = 0` (transition -0.08..0.01), mid-sky peak is clamped 0.05..0.65, and
  the zenith transition is clamped by Softness.
- `mu_s = L.z` gates the narrow corona below the horizon.
- Palette registry gate verifies `PALETTES` and `PRESETS` agree, that
  `AFTER_SCHOOL` is exposed in the scene enum, and that Sun Glow, Sky Accent,
  Cloud Flatness, Delta Gain, Rim Boost and Contrails are present and synced.

### Changed
- Recalibrated the six existing palettes for the new planar cloud deck and
  backlit shading; all preset cloud triads and star amounts were updated.
- Look-dev now renders all seven palettes in a 4-column contact sheet.

### Fixed
- Custom Sun still only affects the sun disk/light; cloud light remains the
  preset value (the 0.8.1 regression test remains in the gate).

## 0.8.1 - 2026-10-20
### Fixed
- Custom Colors: changing **Sun** no longer repaints the clouds. The custom
  sun color now only drives the sun disk/light and sun-based material/compositor
  tints; the cloud light stays on the selected preset's `cloud_light` value.
- Added a regression check that changes only `custom_sun` and verifies
  `Cloud Shadow`, `Cloud Mid` and `Cloud Light` are unchanged.


## 0.8.0 - 2026-10-20
### Added
- **Sun Elevation / Sun Azimuth** sliders with two-way synchronization to the
  active sun, plus a one-click **Stage Backlight** operator that frames the sun
  ahead of the camera (+12 deg / 15 deg side) and enables Sun Disk, God Rays,
  Light Wrap and Rim Light.
- **Starfield** in the world group: Voronoi points masked by the zenith, hidden
  by clouds and near the sun disk. Per-preset star amounts (Neon Night 0.8,
  Twilight Dusk 0.7) and Star Amount / Star Density controls.
- **Cloud Wind**: the cloud noise is driven by a frame-based Cloud Offset, so
  stars remain static while clouds drift during animation.
- **Aerial Haze**: distant geometry is tinted toward the horizon/shadow color
  using the depth range, masked to the scene silhouette.
- **Normal Ink Lines**: a Normal-pass discontinuity extractor is combined with
  the depth edges to ink creases, furniture and internal hard corners.
- **Terminator Warmth**: a narrow warm subsurface band around `N.L = 0`, with a
  Skin preset boost.
- **Rim Mode**: Sun Side, 360 Contour and Backlight rim selection through a
  single group input.
- **Material exclusion**: the active material can be excluded from the global
  sync (`mat["ald_exclude"]`); excluded materials are skipped by Apply/Build and
  retain their original shading until included again.

### Changed
- Light Wrap and Ink Lines now share one silhouette/depth geometry graph;
  `_depth_edges` receives a vertical offset for the ink chain, removing duplicate
  overlapping nodes.
- Turning **Shadow Tint** off zeroes only the AO Strength while keeping Cel and
  Rim shading active. The **X Clear Shadow Tint** button removes the group and
  disables Cel/Rim shading for a fully clean material state.
- `sun_toward` uses `matrix_world` when the sun has constraints, so Track To and
  other constraint-driven suns work.
- Auto-sun preset rotation is reapplied only when the palette key changes;
  manual slider angles and Stage Backlight survive world/cloud/weather refreshes.
- World gradient group marker is 7; old groups rebuild automatically.

### Gate
- New checks for sun angle movement, Stage Backlight, angle persistence across
  world updates, star amount/density, cloud wind offset, aerial haze, normal ink,
  terminator warmth/rim bias, and material exclusion.
- Pixel gate adds aerial haze; expected `ALD GATE: PASS`.


## 0.7.0 — 2026-10-19
### Added
- **Scientific 6-preset color script** calibrated in Scene-Linear Rec.709 for AgX,
  with a dedicated `mid_sky_color` bridge, cloud triads and `sun_rotation` per
  atmosphere.
- **Four-zone sky gradient**: ground → horizon → mid sky → zenith, removing the
  muddy blue/orange midpoint in sunset palettes.
- **Directional anime clouds**: the cloud color signal combines noise density with
  the sun dot product (`sun_bias`), so the sun side reads brighter and the target /
  fried-egg artifact is removed.
- **Visible sky vs ambient split**: `World Strength` now scales only non-camera
  rays inside the world group (`Light Path > Is Camera Ray`), keeping the visible
  sky vivid while controlling ambient light. Background strength is 1.0 when the
  gradient is active.
- **Shadow Hue Lift** (default 0.18): after the MULTIPLY tint, a small additive
  tint veil lets warm/dark materials take the blue/violet shadow atmosphere while
  preserving texture detail.
- Auto sun applies the preset `sun_rotation`; user suns keep their rotation.

### Fixed
- Changing palette while `Custom Colors` was active now refreshes the custom
  sky/horizon/sun/shadow colors to the newly selected preset.

### Gate
- Checks mid-sky, `World Strength`, background strength, hue lift, and custom
  color refresh on palette switch.

## 0.6.2 — 2026-10-19
### Fixed
- Camera Override panels used the invalid icon name `CAMERA`; Blender 5.1 accepts
  `CAMERA_DATA`. The invalid enum raised on every panel draw, which is why the
  traceback appeared after Remove Stack / Clear Shadow Tint triggered a redraw.
  Both the Scene and Sidebar N panels are fixed; the operations themselves were
  unaffected.

## 0.6.1 — 2026-10-19
### Fixed
- Sun disk: `Generated` view direction and `Sun Direction` are normalized before
  the dot product, so the cosine thresholds are stable and the angular radius is
  exact.
- Internal ink edges: `band_size == 0` now applies an 8× clamped gain, so 15–20 cm
  internal depth steps read as solid lines like the outer silhouette.
- Custom Colors now update halation/god-ray tints and the ink color immediately
  in the compositor, not only world/materials.

### Added
- **Real-time viewport updates**: a depsgraph transform cache pushes sun/camera
  changes into the world sun disk, material terminators/rim and God Rays without
  rebuilding nodes (no frame change required).
- **Rim emission**: the Shadow Tint group has an `Emission` output wired to
  Principled `Emission Color`, with a `Rim Emission` control. Wiring is reversible,
  skips materials with existing emission, and restores the original values.
- Gate: normalized sun vectors, depsgraph transform updates, ink gain, custom
  color tint sync, emission wiring/restoration.

## 0.6.0 — 2026-10-19
### Added
- **Per-camera palette overrides**: each Camera data-block can enable its own
  palette; switching the active camera applies it automatically.
- **Effective look coordinator** (`look.py`): precedence
  **camera > shot marker > scene base palette**.
- Effective look label in the Scene panel: `Look: <PALETTE> (camera|marker)`.
- Camera Override box in the Scene World & Shadows section and Sidebar N.
- Gate coverage for camera overrides and base-palette invariance.

### Changed
- Shot markers no longer overwrite `Scene.ald.palette`; they set the effective
  palette only. The base palette is preserved for non-marker shots.
- Palette changes, world controls and `Apply Palette` all resolve the effective
  palette instead of assuming the base.
- `compositor` glare tints and `shadow_tint_for` use the effective palette key.
- Version 0.6.0.

## 0.5.0 — 2026-10-19
### Added
- **Cel terminator** in the Shadow Tint group: `N·L` against the palette sun,
  combined with AO, with Cel Shadow strength and Terminator sharpness controls.
- **Directional rim light** on the sun-facing Fresnel edge, tinted by the sun
  color; Rim Strength and Rim Width controls. The HAIR preset gets an automatic
  angel-ring boost.
- Sun direction/color are pushed into every tinted material and refreshed on
  `frame_change_post`, without rebuilding materials.
- Gate render checks for the toon terminator and rim light, plus sun direction and
  hair rim boost.

### Changed
- Shadow Tint group upgraded with `Sun Direction`, `Sun Color`, `Toon Strength`,
  `Terminator Sharpness`, `Rim Strength` and `Rim Width`; the interface is
  extended without clearing, so existing texture links survive upgrades.
- Defaults: Cel Shadow 0.75, Terminator 0.035, Rim Strength 0.45, Rim Width 0.4.
- `materials.py` now registers a frame handler for the sun direction.

## 0.4.0 — 2026-10-19
### Added
- **Sun disk** in the world gradient, aligned with the sun direction; size and
  strength controls.
- **Anime clouds**: two-layer procedural noise, projected sky colors (shadow /
  horizon / sun), horizon fade and amount/scale controls.
- **Anime Ink Lines**: thin depth-discontinuity outlines composited with a dark
  shadow-tint color; strength and size.
- **Sakura Spring** and **Twilight Dusk** atmosphere presets.
- **Custom palette colors**: sky, horizon, sun and shadow overrides per scene,
  exposed in the Scene and Sidebar N panels.
- Gate coverage: sun direction/disk strength, cloud toggle, ink node + pixel test,
  custom colors and preset restore.

### Changed
- World gradient group upgraded (sun disk + clouds) with `ald_build = 3`.
- Sun/cloud frame updates run on `frame_change_post` so animated transforms are
  evaluated before reading sun matrices.
- Shadow tint colors for the new presets are normalized multiplier hues.
- Look-dev renders all six palettes in a 3×2 sheet.

## 0.3.2 — 2026-10-19
### Added
- **Sidebar N panel** (`VIEW_3D > Anime Look`) with palette, world, shadow tint,
  compositor toggles/sliders, build/remove and viewport compositor.
- Gate checks for in-place parameter updates, God Rays node creation with the sun
  behind the camera, and the multiplicative shadow tint.

### Changed
- **Slider performance**: float properties now call `compositor.update_params()`
  and rewrite only node sockets. Booleans still rebuild the topology. Kuwahara,
  halation, dispersion, light wrap, God Rays and depth range update in place.
- **Shadow tint is multiplicative**: `MULTIPLY` preserves texture detail in
  shadowed areas; palette shadow colors are normalized multiplier hues.
- **God Rays node is always created** when enabled; if the sun is behind the
  camera at build it starts at `(0.5, 0.5)` with strength 0 so the frame handler
  can bring it in later.
- Halation strength range corrected to 0–1 to match the Glare socket.

## 0.3.1 — 2026-10-19
### Added
- God Rays **Size** control.
- God Rays live refresh on frame change: the Sun Position follows the camera and
  sun during animation; the node is muted (strength 0) when the sun goes behind
  the camera and restored when it comes back.
- **Emission** material preset (neon surface) with Emission Color/Strength; other
  presets explicitly reset emission strength.
- `RECAP.md`: an Italian end-to-end recap of the add-on.

### Changed
- Sun Beams defaults: 6 iterations, fade 0.95.
- Version 0.3.1.

## 0.3.0 — 2026-10-19
### Added
- **God Rays**: optional Sun Beams glare placed at the sun's projected screen
  position, with a strength control. The node is skipped when the sun is behind
  the camera.
- **Shot markers**: opt-in per-shot palette changes from timeline markers named
  `ALD:<PALETTE>`; the `Mark Shot` operator writes/updates the marker at the
  current frame.
- **Material presets**: Skin, Hair, Fabric and Metal, assigned to selected
  objects and integrated with the shadow tint.
- Sub-panels for World & Shadows and Compositor Stack; the main panel keeps
  Atmosphere, Material Presets, build/remove and stack status visible.
- Gate coverage for the Sun Beams node and projected sun position, shot markers
  and material presets.

### Changed
- Version bump to 0.3.0; README, AGENTS.md and TECH_NOTES.md updated.

## 0.2.1 — 2026-10-19
### Added
- Auto Sun: applying a palette creates a tagged sun light when the scene has
  none; toggle in the World & Shadows panel section.
- Per-scene compositor stacks: each scene gets its own `ALD | Compositor Stack`
  group (suffixed when names collide), so multiple scenes no longer fight over
  one Render Layers node.
- Gate checks for auto-sun creation/toggle and for two scenes with independent
  stacks (build, Render Layers scene, removal isolation).

### Changed
- `ald.remove` unassigns the scene's stack and deletes it only when no other scene
  uses it; custom compositor groups are left untouched.

## 0.2.0 — 2026-10-19
### Added
- Palette-driven world gradient (sky / horizon / ground) with horizon offset and
  softness, built in the shared `ALD | World Gradient` node group.
- Shadow tint on scene materials through the shared `ALD | Shadow Tint` group:
  an AO mask mixes Base Color toward the palette shadow color.
- Light Wrap stage in the compositor stack, using a depth-derived silhouette
  mask, depth-discontinuity edges and blurred scene light.
- Gate checks for gradient, shadow tint insert/remove/restore, light wrap graph,
  rebuild idempotency and `bl_info` / manifest version consistency.
- Render-level gate checks: shadow tint and light wrap must change pixels, and the
  light wrap must stay edge-local.
- `preset_dev/lookdev.py` renders all four palettes on a fixed scene and builds a
  contact sheet for look development.

### Changed
- `ald.build` and `ald.apply_palette` also sync the shadow tint on scene materials.
- `ald.clear_shadow_tint` restores every touched Base Color link or value.
- Light wrap is composited as straight alpha, so the blurred image cannot leak
  over the whole frame.
- The world depth threshold follows the camera clip end (EEVEE writes
  `clip_end + 0.55`, Cycles writes ~1e10).
- Horizon softness now maps to a tighter falloff, so the sky gradient reads in a
  normal framing.
- Summer Noon is slightly less milky; Neon Night has a blue-violet zenith.

### Fixed
- World gradient colors are socket-driven (Mix + Map Range) instead of a static
  ColorRamp that ignored the palette.
- Light wrap no longer blurs the whole image because of premultiplied alpha.
- Depth-based light wrap now detects object-on-object silhouettes, not only
  geometry against the world.

## 0.1.0 — 2026-10-19
- Initial skeleton: Scene settings, four atmosphere presets, compositor node-group
  stack (Glare, Kuwahara with depth mix, Lens Distortion), operators and Scene panel.
- Headless gate `preset_dev/verify.py`.
