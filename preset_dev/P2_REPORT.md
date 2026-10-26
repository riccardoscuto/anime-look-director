# P2 report — filament geometry (v2.32.0)

## Files changed

- `fx_nodes.py` — the trail group inserts `Mesh to Points`; `SCHEMA` 3 → 4.
- `fx.py` — `_world_per_pixel` / `_apparent_radius`, apparent width on every
  trail (fireworks, shell, meteors), secondary star population, per-star trail
  cap, dead writer removed.
- `properties.py` — `fx_trail_min_px`, `fx_trail_max_px`.
- `preset_dev/verify.py` — `check_fx_trail_width` also realizes the geometry.
- `preset_dev/trail_shape_spike.py`, `preset_dev/p2_age_strip.py` — evidence.
- `preset_dev/audit_plan.py` — five `VI-P2` requirements.

## Root cause: the filament never existed

The Geometry Nodes trail connected the mesh of loose vertices straight into
`Points to Curves`. That node consumes a **point cloud**, not the vertex domain
of a mesh, so its output was empty: `Curve to Mesh` received no curve. The only
visible FX were the beaded grains, which is why every render read as a field of
dots. The old gate checked the modifier width and never realized the geometry,
so it could not see the bug.

Measured on the same burst (37 spokes, 16 samples each):

| stage | before | after `Mesh to Points` |
| --- | --- | --- |
| `Delete Geometry` | 592 points | 592 points |
| `Curve to Mesh` | 0 vertices, 0 faces | 2368 vertices, 2294 faces |

`SCHEMA` 4 rebuilds the groups saved in existing files and remaps the
modifiers, so a file opened after the update is repaired on the next build.

## Apparent width (P2-A)

The physical radius (0.022 m) is sub-pixel at 55 m with a 800 px frame
(0.0495 m/px). `_apparent_radius` raises it to at least `fx_trail_min_px`
(1.5 px) and caps it at `fx_trail_max_px` (6 px), computed from the camera
(sensor, lens, resolution, perspective or orthographic). At the baseline the
radius becomes 0.0371 m = 1.5 px of diameter; the taper multiplies 0.25..1.15.

## Tube or ribbon (P2-C)

`preset_dev/trail_shape_spike.py` builds one vertical filament twice — with the
production circular profile and with a line profile — and renders it face-on
and edge-on:

| variant | face-on | edge-on | ratio |
| --- | --- | --- | --- |
| tube | 657 px | 657 px | 1.00 |
| ribbon | 654 px | 0 px | 0.00 |

A burst is three dimensional: some spokes are always edge-on, so a flat strip
would disappear at those angles. The hybrid (tube near the head, ribbon far)
inherits the same weakness and is not adopted. **Round tube.**

## Regularity (P2-D)

Two changes, both deterministic and shared by the two backends:

- about 35 % of the stars are a secondary population with 0.62× life and
  0.62× speed, so the burst has an inner shell instead of a single ring;
- every star keeps its own fraction (0.45..1.0) of the family trail, so the
  tails end at different distances.

## Tests

- Gate: the trail object is realized (`bpy.data.meshes.new_from_object`) and
  must produce at least `spokes × (SAMPLES - 1)` faces. This is the regression
  test for the empty filament.
- Gate: the modifier radius must be at least the apparent minimum and at least
  `fx_trail_min_px` pixels wide.
- Full gate `ALD GATE: PASS`; audit 45/45.
- `preset_dev/baseline_fx_p2/` — emission, glow and full at 800×450 and
  1920×1080, plus `age_012/030/060/110.png`: the filament is continuous with no
  glow at every age.

## Performance (same machine, EEVEE 32 samples)

| measure | P1 | P2 |
| --- | --- | --- |
| creation | 0.145 s | 0.150 s |
| frame evaluation | 0.007 s | 0.007 s |
| full 800×450 | 1.70 s | 1.81 s |
| full 1920×1080 | 8.00 s | 8.20 s |

The tubes add geometry that is now actually rendered, so the full render is
slightly more expensive. The frame evaluation is unchanged: the nodes evaluate
the same point count.

## Residual risks

- At the burst the tubes overlap at the centre and the core reads as a bright
  white knot. That is a shading/exposure problem (P3), not geometry.
- The tube is round with four profile points; a very close camera would see the
  facets. The apparent-width cap limits how close a burst can be framed.
- The per-star cap changes the deterministic geometry of every burst: seeds
  reproduce, but the images of older versions do not match.

## Commit

`P2: continuous filament geometry, apparent width and less regular bursts`
(this change).
