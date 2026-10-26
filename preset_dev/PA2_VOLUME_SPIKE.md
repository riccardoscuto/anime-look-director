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

## Result

| Render | Time | What it reads as |
|---|---|---|
| `card.png` | 2.07 s | irregular cloud mass, sky openings, lit fringe |
| `volume_0.02.png` | 1.09 s | almost invisible veil |
| `volume_0.06.png` | 1.09 s | soft rectangular slab, hard straight edges |
| `volume_0.15.png` | 1.07 s | darker rectangular slab, still hard edges |

The volume is cheaper to render (~1.1 s against 2.07 s at this resolution), but
it does not read as a cloud:

- the silhouette is the box: straight edges at the frame border, no islands and
  no sky openings;
- the interior is a flat absorption veil that darkens the sky instead of
  producing the sunward fringe and the anime contour;
- raising the density only darkens the rectangle; it never grows a shape.

The cards already produce the silhouette (deterministic density field) and the
stylised shading (fringe, rim boost, fog) at 2.07 s.

## Conclusion

- **Cards stay the default.** A volume backend needs a shaped density field, a
  volume lighting/contour model and a compositing path (the cyan/magenta FX
  isolation does not apply to environment volumes) before it can be compared to
  the cards at all. That is a separate research project, not a parameter change.
- The spike is kept as evidence: `metrics.json` and the four PNGs live in
  `preset_dev/pa2_volume_spike/`.
- No PA2 asset, shader or node tree was copied; only the public EEVEE volume
  nodes were used.
