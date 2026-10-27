# Sunset gate - Cumulus 2.59.1

The approved Cumulus field is rendered at sunset with `GOLDEN_HOUR`, Sun
elevation 4 degrees, azimuth 25, 1280x720, 32 samples, AgX, exposure 0.
`contact.png` has the fixed-camera side view and the camera-at-the-sun view.

## Findings

- Side view: the warm horizon and the pink/violet cloud mid-tones read as a
  sunset; the lit edge is visible on the sunward side.
- Backlit view: the clouds are silhouettes with a thin warm rim around the
  solar side. The sun disk is clean and the sky is not washed out.
- The cloud silhouette is the approved 2.59.1 Cumulus. It is still flatter
  than the v1 reference; this gate is about the sunset response, not a new
  shape.
- No compositor is used.

## Gate

This is the second visual gate. It is a candidate, not approved: the user must
accept the sunset response before the shooting-star phase starts.
