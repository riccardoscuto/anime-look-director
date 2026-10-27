# Phase 2 cloudless sky

Four conditions, clouds off, 1280x720, EEVEE 32 samples, AgX, exposure 0,
camera `(0,-12,3)`, rotation `(1.75,0,0.45)`, lens 32 mm.

| Cell | Palette | Sun elevation | Sun azimuth | Stars |
|---|---|---:|---:|---|
| noon | SUMMER_NOON | 35 | -25 | off |
| sunset | AFTER_SCHOOL | 4 | 25 | off |
| dusk | TWILIGHT_DUSK | -6 | 25 | off |
| night | NEON_NIGHT | -18 | 25 | on |

`before/` is the frozen v2.57.0 World; `after/` is the Phase 2 World with the
softened sky-accent band and the Sun below-horizon fade. `contact.png` compares
the two rows in the same order.

## Findings

- The v2.57.0 dusk and night images show a hard blue horizontal band from the
  narrow Sky Accent (0.07 half-width). The Phase 2 band is 0.20 and smooth:
  the transition reads as atmosphere, not as a stripe.
- The Sun disk and glow now fade when the elevation drops below the horizon
  (`Sun Strength` goes to 0 at -8 degrees; `Sun Glow` fades by -7 degrees).
- Noon and sunset are intentionally unchanged: both were already clean.
- The clouds are off in every cell. This is the cloudless criterion; the
  three-family cloud gate is Phase 3.
