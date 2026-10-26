# P1 spike — alpha and occlusion

Baseline: `preset_dev/baseline_fx/` (commit `feeb5e9`, Blender 5.1.2, EEVEE,
AgX, single Chrysanthemum, seed 13, frame 44, 800x450 and 1920x1080).

## What the baseline shows

- `emission_*.png`: the burst is a set of radial **dots**, not continuous
  filaments. The trail meshes are sub-pixel at the baseline framing.
- `glow_*.png`: **completely black**. The FX pixels are too dim/small to cross
  the Glare threshold (0.35) at this age; the dedicated glow is effectively
  inert for this event.
- `full_*.png`: the burst is visible and integrated, but still reads as dots
  with a faint core; the glow does not enlarge it.

## P1-A — true alpha

Verified with a 32x32 probe (bright plane, transparent world, EEVEE 1 sample):

| setting | center alpha | corner alpha |
| --- | --- | --- |
| `film_transparent = False` (current stack) | 1.0 | 1.0 |
| `film_transparent = True` | 1.0 | 0.0 |

So EEVEE **does** write a correct alpha; it was disabled by
`film_transparent=False`. The `max(R,G,B)` workaround is therefore not
required by the engine: it is required only because the scene-level film
setting cannot be changed per view layer.

## P1-B/P1-C — Cryptomatte works, and it is occluded

Probe: emissive plane + opaque cube in front of its left half, EEVEE,
`use_pass_cryptomatte_object=True`, legacy `CompositorNodeCryptomatte` wired to
`CryptoObject00..02`, `matte_id="FXPlane"`.

| sample | matte |
| --- | --- |
| center (FX visible) | 0.773 |
| corner (no FX) | 0.0 |
| left (cube in front) | 0.0 |

Cryptomatte isolates the FX and **the occluder already zeroes the matte**,
because the matte is computed from the visible render. This removes the need
for the depth-comparison visibility pass for opaque occluders.

## Chosen architecture for P1

Use the **main view layer** with `Emission` + `Cryptomatte Object` passes, and
keep `ALD FX Base` for the clean environment:

- `B` = `ALD FX Base` image (FX collection excluded);
- `A` = Cryptomatte matte of all FX objects (`matte_id` = list of object names,
  regenerated at build time);
- `F` = `Emission` pass × `A` (premultiplied FX emission; occluded FX is not in
  the emission pass and the matte is 0 behind occluders);
- `C = P(B) × (1 - A) + F + Glare(F)`;
- no `ALD FX Only` layer, no transparent world override, no `max(R,G,B)`, no
  depth-comparison visibility for opaque occluders;
- the punch-out uses `A`; the gate's "visible coverage" node becomes the
  Cryptomatte matte.

Remaining risk: Cryptomatte's matte is a coverage value (0.773 at the probe's
center, not 1.0), so the exact edge/centre convention must be validated on the
FX particles (especially sub-pixel grains) before removing the depth pass. The
P1 implementation will compare a Cryptomatte matte and a depth-based visibility
on the same burst, as the plan requires, and will keep only one production
path.

## Next

1. Rewrite the FX section of `compositor.py` to the Cryptomatte architecture.
2. Add gate checks: wall in front hides head/trail/glow; wall behind does not;
   zero FX identity; HDR energy does not change coverage; no double glow.
3. Only after P1 passes, move to P2 (trail geometry).
