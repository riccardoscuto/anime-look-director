# Spatial Clouds 2.0 — audit and result (v2.40.0)

Baseline audited: 2.39.0 (`6779001`). New code: this commit.

## Evidence classification

- **CONFIRMATO** — read from the code.
- **VISIVO** — observed in a render.
- **DA VALIDARE** — a risk that needed a Blender test.
- **PROPOSTA** — a recommended design, not implemented.

## P0 — the defect is reproduced

`preset_dev/clouds_baseline/` (commit `bbace26`) renders Cloud Amount
0 / 0.16 / 0.5 / 1.0 and Cloud Height 0.35 / 1.5, from the final camera and an
oblique diagnostic view. The result is unambiguous:

- 3 objects and **1536 polygons for every Amount** (512 quads per card);
- coverage **0.0000** at the final camera for every cell (the cards are out of
  frame because Height is a fraction of the depth), **0.4577** / **0.6607** in
  the oblique view, identical for all amounts;
- the oblique render shows the slabs.

The script runs against 2.39.0: after this change the API changed, so the
images and `metrics.json` are the frozen baseline.

## P1 — controls

| requirement | state | evidence |
| --- | --- | --- |
| Coverage changes the geometry | **CONFIRMATO** | 0.0 → 0 faces, 0.16 → 23 069, 0.5 → 84 024, 0.9 → 159 729 (3 layers) |
| Coverage 0 → no visible mass | **CONFIRMATO** | empty meshes, gate check |
| Altitude in world units, Anchor axis | **CONFIRMATO** | `_layout` uses `axis`; Y-up test moves the layers along Y |
| Depth separate from altitude | **CONFIRMATO** | depth along the creation forward, altitude along the axis |
| In-place updates | **CONFIRMATO** | a depth change keeps the object and mesh pointers and the face count; a coverage change rebuilds the mesh in place |
| UI names distinct | **CONFIRMATO** | "World Clouds" property group, "Spatial Clouds" box with Coverage, Layers, Altitude, Depth, Scale, Mode, Flash |
| Diagnostics | **CONFIRMATO** | `clouds.diagnostics` lists depth and polygons per layer |

## P2 — real silhouettes

The cards are generated from a deterministic density field: domain warp,
two fBm bands, a border envelope that prevents any rectangle, and a threshold
that is the Coverage value. The meshes are islands with real openings, not a
strip from the top to the bottom edge. The field is sampled on a coarse grid
and bilinearly on a finer mesh (1–6 px cells at 1080p).

Two representations were considered:

- **A. opaque geometric silhouette** — chosen. It writes depth, so the P1
  Cryptomatte occlusion works with no extra path.
- **B. soft alpha edge** — rejected for now: the dithered cutout does not zero
  the Cryptomatte samples, so the FX show through the edge; BLENDED does not
  write depth either. A soft edge needs a dedicated pass, not a material flag.

There is no P2-B "6–12 cards" addition: the layer count stays 1–5 and the
quality comes from the silhouette.

## P3 — coordinates and camera

- World placement is stored per layer (`origin`, `forward`, `right`, `axis`)
  and the persistent layer data is the source of truth.
- **SHOT_LOCKED**: the orientation is fixed at creation.
- **CAMERA_FACING**: `update_orientation` re-aims the card at the camera
  position, called from the camera depsgraph handler; a lateral camera move
  changes the rotation, the world position does not move.
- The Anchor axis, not the camera up, defines the vertical.
- Depth order diagnostic: `clouds.diagnostics`.

## P4 — material, palette, local light

- The material is emission with palette cloud colours and a noise mix; it is
  deliberately stylised, not a global light.
- **Local flash**: `update_flash` finds the strongest active burst
  (`event.glow` × the life decay), projects its world position into the card
  space and writes `ALD | Flash X/Y/Energy`; the shader adds an exponential
  falloff around that point. `event.glow` is therefore no longer a dead
  parameter. The gate checks that a burst in the card lights it and that
  disabling the flash clears the energy.
- **Palette sync**: `look.apply` and `look.apply_world` call `clouds.sync`
  (colours only) and `fx.sync_palette` (FX material tint in place).
- **World duplication**: not implemented. The World keeps its own clouds; the
  spatial layer adds masses. A mask/reduction option is still a proposal.

## P5 — compositor

- The environment filters (Kuwahara mask, light wrap, ink, haze) now read the
  **base layer** (`environment_layers`), so the FX cannot create edges in the
  environment they are added to. The base layer also enables the normal and
  mist passes.
- **Non-FX emission (DEV-03) — measured, still open.** At the edge of a thin
  filament the Emission pass averages the FX with the background; with a very
  bright foreign emitter behind (emission 40×3) the FX contribution changes by
  up to 0.93 at partially covered pixels (`preset_dev/emission_isolation/`).
  The binary presence mask removes the foreign energy at fully covered pixels,
  not at the edge. A dedicated FX-only emission layer was attempted and
  reverted: a collection created after the stack is included by default in the
  view layer and the exclusion did not update reliably. The correct fix needs
  a dedicated render layer managed at the render start, or a per-object
  emission pass; it is not claimed as solved.
- **Transparency**: not used. The opaque silhouette keeps the Cryptomatte and
  depth passes correct. A soft edge remains a proposal with a dedicated pass.

## P6 — FX inconsistencies

| item | state |
| --- | --- |
| Size semantics | **partial**: the 0.6–2.0 internal clamp is removed (0.1–4.0), and the star velocity scales with `event.size`; the UI range and the world size are now coherent. The head and trail widths still have their own apparent floor. |
| Event Glow | **CONFIRMATO**: it drives the spatial cloud flash (measurable in the gate). It is not a per-event compositor glare. |
| Framing | **open**: the composition gate still projects the burst centre; an envelope estimate is not implemented. |
| Camera-dependent widths | **CONFIRMATO**: `fx.refresh_widths` updates the trail modifier/curve from the camera, resolution and focal, called by the camera handler; the gate changes the resolution and checks the new width. |
| Event colour | **CONFIRMATO**: `burst_population` now receives the sky-tinted family colours, so `event_color` is the particle colour, not the default white. |

## P7 — lifecycle

- Layers are persistent (`ALD_CloudLayer`: uid, index, seed, object name,
  origin/forward/right/axis, rotation) and the object identity is resolved by
  the stored name and uid, not by collection order.
- `create` is idempotent; `remove` is idempotent and clears the persistent
  layers; `rebuild` recreates the objects of a saved scene.
- The ownership key is shared with the FX: the **collection collision** was
  found and fixed (`fx._collection` and `compositor._fx_collection` now accept
  only the FX collection). Before the fix the FX objects landed in the cloud
  collection.
- Duplicate scenes and migration of pre-2.40 cloud data are **open**: the old
  module had no persistent layer data, so there is nothing to migrate, but a
  duplicated scene with clouds has not been tested.

## Tests

- Structural: audit 75/75.
- Runtime gate: coverage 0/0.5/0.9 monotonic, identity on transforms, Anchor
  Y-up, Camera Facing, flash on/off, occlusion of the FX matte by a card in
  front, widths follow the resolution, environment filters on the base layer.
- Visual: `preset_dev/clouds_baseline/` (before), `preset_dev/clouds/`
  (after), `preset_dev/showcase/` (whole stack), `preset_dev/temporal/`
  (frame-by-frame), `preset_dev/validation/` (36/36 matrix).
- `ALD GATE: PASS`.

## Open items (honest)

1. **DEV-03 / P5-B** non-FX emission at partially covered pixels (measured).
2. **DEV-07 / P6-C** projected envelope: still centres only.
3. **SC-08 / P7-B** duplicated scene with clouds.
4. **P4-B** reducing the World cloud duplication.
5. Performance: the new cloud build is not benchmarked against 2.39; the
   polygon counts are 0 / 23k / 84k / 160k for the four coverage values.
