# Controlled shooting star - Phase 4 gate

One persistent event, rendered at frames 1, 8, 16, 25 and 30 with the World
clouds off so the trajectory is unambiguous. `contact.png` shows all five.

## Event

- Start frame 1, duration 24 frames (24 fps).
- Start azimuth 120, elevation 35, direction -35, angular length 22.
- Trail 0.60, thickness 0.0018, brightness 3.0, glow 0.8,
  cool-white color to match the starfield.
- The shader uses gnomonic sky coordinates, not a Voronoi field.
- The head is a short bright band; the tail is a thin, tapered line.
- No object, particle or collection is created; the event is a World-shader
  value.

## Gate

- Frame 1: no star (birth).
- Frame 8 and 16: a tapered tail with a bright head; the head moves.
- Frame 25 and 30: the star is gone (life ended).
- The event survives save/reload (world fixture).
- The list and the add/duplicate/remove controls are in World & Shadows >
  Shooting Stars.

This is the third visual gate; it was approved on 2.60.1.
The UI has a Preview button that moves the timeline into the event and aims
the camera at its start. Editing a field refreshes the World immediately.
