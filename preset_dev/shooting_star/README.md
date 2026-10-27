# Controlled shooting star - Phase 4 gate

One persistent event, rendered at frames 1, 8, 16, 25 and 30 with the World
clouds off so the trajectory is unambiguous. `contact.png` shows all five.

## Event

- Start frame 1, duration 24 frames (24 fps).
- Start azimuth 120, elevation 35, direction -35, angular length 22.
- Trail 0.40, thickness 0.005, brightness 0.9, glow 2.0.
- The shader uses gnomonic sky coordinates, not a Voronoi field.
- No object, particle or collection is created; the event is a World-shader
  value.

## Gate

- Frame 1: no star (birth).
- Frame 8 and 16: a tapered tail with a bright head; the head moves.
- Frame 25 and 30: the star is gone (life ended).
- The event survives save/reload (world fixture).
- The list and the add/duplicate/remove controls are in World & Shadows >
  Shooting Stars.

This is the third visual gate; it is a candidate, not approved.
