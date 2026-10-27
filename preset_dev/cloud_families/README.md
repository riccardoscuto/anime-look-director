# World cloud families - Phase 3 first gate

Three families under the same day sky, camera, palette (`SUMMER_NOON`),
resolution (1280x720), Sun and exposure. `cloud_families.py` regenerates the
set.

| Family | Coverage | Flatness | Vertical | Breakup | Scale |
|---|---:|---:|---:|---:|---:|
| Cumulus | 0.48 | 0.15 | 0.90 | 0.28 | 3.4 |
| Stratocumulus | 0.75 | 0.95 | 0.10 | 0.20 | 3.8 |
| Cirrus | 0.38 | 0.30 | 0.10 | 0.02 | 11.0 |

`contact.png` shows the color rows and the silhouettes extracted from the
luminance/neutrality mask. The silhouettes are the first gate evidence:
isolated rounded masses (Cumulus), horizontal bands and openings
(Stratocumulus), stretched thin structures (Cirrus).

## What the shader does

- One density field with a family transform: Cumulus lowers the effective
  flatness and increases vertical growth; Stratocumulus raises the flatness;
  Cirrus stretches the view ray along the wind and thins the result.
- All families use the same density for shape and body shading; the Sun
  derivative is still the lighting signal.
- `Breakup` erodes the field before the coverage threshold; `Detail` scales the
  boundary and body noise; `Cloud Seed` offsets the field deterministically.
- `Cloud Vertical` lowers the effective flatness; `Sun Lighting` scales the
  solar derivative. `Cloud Shadow/Mid/Light` remain the three colors.

## Gate

The first gate is **Cumulus in daylight**. This is the first lighting iteration:
the body has a height tone (the base is darker), a stronger solar range
(-0.030..0.004) and a default Sun Lighting of 1.2. The masses are still flatter
than the v1 reference and the Cirrus still reads more like altocumulus than a
true cirrus veil. Sunset, Stratocumulus and Cirrus are not started until this
day gate is accepted or the Cumulus shape is revised.
