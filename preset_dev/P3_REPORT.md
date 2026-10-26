# P3 report — shading, palette and glow (v2.33.0)

## Files changed

- `fx.py` — instancer/geometry material split, tail falloff (`tail_u`),
  shader version and in-place rebuild, sky-tinted palette.
- `fx_nodes.py` — `tail_u` in the burst and trail groups; `SCHEMA` 4 → 5.
- `compositor.py` — binary presence for F, black punch, glow defaults.
- `properties.py` — `fx_glow_strength` 1.0, `fx_glow_threshold` 0.0,
  `fx_glow_size` 0.35.
- `preset_dev/verify.py` — `check_fx_p3_shading`, punch-black check, T24 at
  256×256.
- `preset_dev/glow_variants.py` — the three comparison renders.

## Three real defects, found by measuring the composite

### 1. The grey veil (`ALD | FX Painted Punch`)

The Mix node that removes the background had an **unlinked B socket**, and the
Blender default for that socket is 0.5 grey. Every FX pixel was therefore
`B*(1-A) + 0.5*A`: at the hottest pixel in the test frame the matte was 0.4954
and the veil added exactly `0.5 × 0.4954 = 0.2477`. That is why the burst looked
washed out and desaturated, and why the glow appeared to do nothing — it was
added on top of a grey floor. The B socket is now black.

### 2. Double coverage (dark trails)

The `Emission` pass is already weighted by the geometric coverage: a 1.5 px
filament carries only `A` of its radiance. `F = Emission × A` squared the
coverage, so a half-covered pixel lost `A` of the sky but gained only `A²` of
the filament: `A=0.5` gives `0.5` sky removed and `0.25` filament added. The
trails read as dark lines and the tails had to be kept artificially bright.
`F` now multiplies the pass by a **binary presence** (`matte > 0.001`), which
keeps the anti-aliasing of the pass; the punch keeps the fractional matte.

### 3. Black instances (missing sparkle)

The heads, beads, pistil and sparks are instanced geometry. A material with
`ShaderNodeAttribute` in the `GEOMETRY` domain reads the *instance* mesh, which
has no attributes, so `energy` was 0 and the beads were black. Controlled test
(two instanced spheres, energy 0.2 and 1.0):

| attribute type | left | right |
| --- | --- | --- |
| GEOMETRY | 0.0 | 0.0 |
| INSTANCER | 0.2 | 1.0 |

There are now two material sets per colour: `INSTANCER` for the points objects,
`GEOMETRY` for the trail tubes and the Python fallback. The material key carries
`|I` and both are tagged `ald_fx_material`, so the Cryptomatte matte covers both.

## Tail falloff

`tail_u` is 0 at the head and 1 at the end of the tail; the shader maps it
1.0 → 0.35. A missing attribute is 0, so heads and the Python fallback keep full
energy. The floor is 0.35, not 0.12: a dimmer tail is darker than the twilight
sky and the punch turns it into a black line (measured, then reverted).

## Glow calibration

The FX emission in this scene peaks at ~0.71 linear. The Glare threshold is
applied to that value, so the old 0.35 threshold left almost nothing to bloom
and the default 0.6 strength was invisible. Measured with threshold 0 (F is
already the FX only, so it needs no threshold), size 0.35:

| strength | peak delta | lit pixels (400×225) |
| --- | --- | --- |
| 0.2 | 0.039 | 35 |
| 0.5 | 0.078 | 1762 |
| 1.0 | 0.129 | 7018 |
| 2.0 | 0.204 | 16803 |

Defaults: strength 1.0, threshold 0.0, size 0.35. The three final composites are
in `preset_dev/calibration_p3/` (`full_g0.00_s0.35.png`,
`full_g1.00_s0.35.png`, `full_g1.00_s0.70.png`).

## Palette

`_sky_tinted_colors` pulls the family colours 30 % toward the sun colour of the
effective sky palette. The twilight baseline is now amber/pink instead of a
fixed rainbow, while the three-colour identity remains.

## Tests

- Punch B is black and unlinked.
- Both attribute domains exist in the live materials.
- The glow changes the composite (peak > 0.02, > 50 pixels).
- The composite adds light: the mean delta over the FX is positive.
- T24 at 256×256: at 64×64 a meteor head at 15 m is sub-pixel; the old test was
  measuring the grey veil.
- Full gate `ALD GATE: PASS`; audit 50/50.

## Performance

| measure | P2 | P3 |
| --- | --- | --- |
| creation | 0.150 s | 0.141 s |
| frame evaluation | 0.007 s | 0.007 s |
| full 800×450 | 1.81 s | 1.49 s |
| full 1920×1080 | 8.20 s | 7.28 s |

The composite is faster because the grey veil is gone; the geometry is the same.

## Residual risks

- The burst still reads regular: 110 spokes at one speed are a chrysanthemum,
  but the silhouette is still spiky. Composition and multiple bursts are P4.
- The meteor visibility depends on the framing: a 0.18 m head at 15 m is about
  half a pixel at 64×64. Production shots need realistic distances/resolutions.
- The sky tint is applied at creation; changing the palette later rebuilds the
  FX only when they are recreated, not on a palette swap.

## Commit

`P3: punch, coverage and instancer shading, tail falloff, calibrated glow`
(this change).
