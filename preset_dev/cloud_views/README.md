# Spatial cloud views — billboard evidence

The spatial cards are vertical, camera-facing planes. This folder records the
three views that explain the "walls" seen from a free viewport:

- `shot_locked.png`: the creation (shot) camera. The cards read as the intended
  cloud band at the top of the frame.
- `side_locked.png`: a camera at the side, `Shot Locked`. The same cards are
  seen as planes; the silhouette is a large tilted sheet.
- `side_facing.png`: the same side camera with `Camera Facing`. The cards are
  re-aimed at the active camera without moving their world positions; the sheet
  becomes front-facing.

`views.json` records the modes and the files. The World clouds are off so only
the spatial layer is visible; the scene, palette, coverage 0.5, three layers and
1280x720 are identical across the three renders.

## What this means

- From the shot camera the cards are the sky layer; from a free view they are
  billboards. That is the representation, not a broken orientation.
- `Shot Locked` keeps the creation orientation. If the camera moves, use
  `Camera Facing` (or recreate the layer) or the cards will be seen at an angle.
- The contour is interpolated and the border rim is deliberate; the flat body
  is the card material, not a normal-map problem.
- A true volumetric cloud is the PA2/volume research branch; the spike is a
  documented NO-GO for the current look.
