# Consolidation 2.41.0 — audit outcome

Baseline: 2.40.0 (`d0d83a5`). This patch closes the actionable P0/P1 items and
leaves the FX emission isolation **explicitly open**: the release does not
claim a global PASS.

## C0 — the emission test is runnable again

`preset_dev/emission_isolation.py` no longer calls the removed
`compositor.sync_fx_layers`, runs from the current HEAD, writes the images and
`metrics.json`, and **exits with code 1 on FAIL**. It measures the masked
contribution `F = Emission x presence` with three regions of the Cryptomatte
matte (`A < 0.1`, `0.1 <= A < 0.9`, `A >= 0.9`) and a foreign emitter behind
and in front of the burst.

Result on this scene (960x540, extreme foreign emitter 40/20/4 x 3):

| region | pixels | contamination mean | max |
| --- | ---: | ---: | ---: |
| clean (A < 0.1) | 43 823 | 0.995276 | 1.000000 |
| mixed (0.1..0.9) | 16 522 | 0.574968 | 0.996078 |
| covered (A >= 0.9) | 0 | — | — |

The `clean` region contains FX **fringe** pixels: the binary presence threshold
(`matte > 0.001`) turns a pixel with a trace of FX into full coverage, so the
whole background emission enters F there. This is the P0 defect, now
reproducible and quantified.

## C0-bis — the real stack F, measured

The earlier probe rendered a temporary compositor, where `render_pre` does not
run: it did not measure the F the stack actually adds. `preset_dev/real_f_probe.py`
rewires the **real** stack output to the `ALD | FX Emission` result and renders
it with and without a foreign emitter behind the burst (640x360, EXR linear,
Standard).

Result: **delta mean 3.987258, max 119.937431, 9 792 lit pixels**. The foreign
emitter (40/20/4 x 3) enters F directly. The same measurement with the FX-only
emission layer (recreated at `render_pre`) is **identical**: the Render Layers
node does not pick up the recreated layer (removing a view layer invalidates
the node's layer reference; assigning the same name does not re-resolve it).
This is the most direct evidence of the P0 and the reason the fallback is not
shipped.

## C1 — the AOV spike failed

The API exists: `ViewLayer.aovs` accepts a COLOR AOV, `ShaderNodeOutputAOV`
has `aov_name`, and the Render Layers node exposes `ald_fx`. A controlled test
(two emissive planes, one writing the AOV, a black world, Standard view
transform) returns **0 in EEVEE and 0 in Cycles**. The node's Color input was
fed by an RGB x strength (not by the Emission shader output). Conclusion: the
Shader AOV is not usable in this target environment for the FX source.

The fallback (a dedicated FX-only view layer used as the emission source,
rebuilt at `render_pre`) was implemented twice and reverted: the view layer
does not reliably exclude collections created after the build, and the
measured contamination did not change. The correct fix needs a dedicated pass
managed outside the material/view-layer exclusions, or an engine that writes
the AOV. Not claimed as solved.

## C2 — scene safety

- Cloud objects are resolved by `ald_cloud_uid` inside the scene's owned
  collection, never by `bpy.data.objects.get(name)`.
- A collection linked to another scene is skipped by `_collection`: removing or
  refreshing one scene cannot clear the other's cards.
- `fx.refresh_widths` and `fx.sync_palette` iterate the scene's FX objects and
  the scene's FX materials only.
- The Cryptomatte material list is built from the scene's FX collection,
  **including the materials stored in the Geometry Nodes modifier inputs**.
  This last part fixes a regression found by the gate: the instanced heads
  disappeared from the matte because their material lives in the modifier, not
  in a mesh slot.
- A duplicated scene sharing the collection is skipped (the copy keeps its own
  data or no clouds). A dedicated duplicate-scene test is still open.

## C3 — clouds

- Coverage 1 no longer builds a full rectangle: the threshold is clamped to a
  positive value and the comparison is strict, so the border (field 0) stays
  empty. 0 / 0.5 / 0.9 / 1 are checked by the gate; 0.16..0.9 by the audit.
- Shot Locked stores the creation rotation **once** (`rotation_valid`), and
  Camera Facing keeps `current_rotation`; switching back to Shot Locked uses
  the creation orientation, not the last camera-facing one.
- The mesh rebuild keeps the material (it is appended to the new mesh before
  the old mesh is freed); the LOD is computed after the layout, at the final
  depth.
- The painterly depth mapping now reads the **base layer**, like the other
  environment masks.
- The flash has a world-distance attenuation (`1 / (1 + (d / 120)^2)`) on top
  of the local XY falloff.

## C4 — FX

- `event.size` 0.1–4.0 scales the star velocity; the trail width follows the
  camera and resolution (`refresh_widths`, tested at two resolutions).
- `event_color` receives the sky-tinted palette.
- The environment filters read the base layer; the Kuwahara depth too.
- The framing envelope is **not implemented**: the composition gate still
  checks the centres. Open.

## Gate status (three levels)

| level | result |
| --- | --- |
| STRUCTURAL | **PASS** — audit 83/83 |
| RUNTIME | **PASS** — `ALD GATE: PASS` |
| VISUAL / INTEGRATION | **FAIL** — `emission_isolation` exits 1 (P0 open) |

Per the operational plan, this release is a consolidation patch, not a
milestone closure: the FAIL is reported in the release notes and no global
`PASS` is claimed.

## Open

1. **P0** FX emission isolation at partially covered pixels (C1).
2. Framing envelope (C4).
3. A dedicated duplicate-scene test (the shared-collection skip is in place).
4. PA2-inspired volume research: **not started**, as instructed while a P0 is
   open.
