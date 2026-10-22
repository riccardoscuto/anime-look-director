# Changelog

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
