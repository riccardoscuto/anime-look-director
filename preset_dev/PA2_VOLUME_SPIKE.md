# PA2 volume spike — cards vs a native EEVEE volume

Research note, 2026-10-26. No add-on backend was changed: the spatial cloud
cards remain the default.

## Question

The PA2 reference look is a dense, three-dimensional cloud mass. Would a native
EEVEE volume (`Principled Volume` + procedural density) beat the production
cloud cards on look or cost, without porting any proprietary shader?

## Setup

`preset_dev/pa2_volume_spike.py`, 640x360, EEVEE, palette After School, fixed
camera looking up. The World clouds are switched **off after** `apply_palette`
(the preset re-enables them), so only the card/volume comparison is visible.

- **Card**: the production `clouds.create` layer at coverage 0.5, two layers.
- **Volume**: a box in the exact placement of the first card layer — depth
  180 m, altitude 90 m, lateral -18 %, 252 x 111.6 m, 22.3 m thick — with a
  noise-driven density (scale 3, detail 5, roughness 0.6) mapped to 0..density.
  Three densities were rendered: 0.02 / 0.06 / 0.15.
- **Shaped volume**: the same box with a faded border (local coordinates
  0.30..0.48 → 1..0), a noise threshold (scale 2.2, detail 6) and a colour ramp
  from cloud shadow to cloud light. Two densities (0.04 / 0.08) and a variant
  with emission 0.15.

## Result

| Render | Time | What it reads as |
|---|---|---|
| `card.png` | 2.16 s | irregular cloud mass, sky openings, lit fringe |
| `volume_0.02.png` | 1.09 s | almost invisible veil |
| `volume_0.06.png` | 1.05 s | soft rectangular slab, hard straight edges |
| `volume_0.15.png` | 1.06 s | darker rectangular slab, still hard edges |
| `volume_shaped_040.png` | 2.21 s | almost invisible blue band |
| `volume_shaped_080.png` | 1.06 s | faint diagonal band, no cloud body |
| `volume_shaped_080_glow.png` | 1.05 s | cream box with a straight edge |

The volume is cheaper to render (~1.1 s against 2.2 s at this resolution), but
it does not read as a cloud:

- the silhouette is the box: straight edges at the frame border, no islands and
  no sky openings. Fading the border hides the edge only at densities where the
  volume is nearly invisible; at readable densities the box returns;
- the interior is a flat absorption veil that darkens the sky instead of
  producing the sunward fringe and the anime contour. The emission variant is a
  cream box, not a lit cloud;
- the shaped density produces a diagonal band, not the layered mass of the
  cards; the 3D noise has no silhouette language.

The cards already produce the silhouette (deterministic density field) and the
stylised shading (fringe, rim boost, fog) at 2.2 s.

## Conclusion

- **Cards stay the default.** A volume backend needs a shaped density field, a
  volume lighting/contour model and a compositing path (the cyan/magenta FX
  isolation does not apply to environment volumes) before it can be compared to
  the cards at all. That is a separate research project, not a parameter change.
  The shaped variants confirm that a border fade and an emission lift are not
  enough: they remove the box only when the cloud disappears.
- The spike is kept as evidence: `metrics.json` and the PNGs live in
  `preset_dev/pa2_volume_spike/`.
- No PA2 asset, shader or node tree was copied; only the public EEVEE volume
  nodes were used.
