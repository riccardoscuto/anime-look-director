# Changelog

## 0.6.0 — 2026-10-19
### Added
- **Per-camera palette overrides**: each Camera data-block can enable its own
  palette; switching the active camera applies it automatically.
- **Effective look coordinator** (`look.py`): precedence
  **camera > shot marker > scene base palette**.
- Effective look label in the Scene panel: `Look: <PALETTE> (camera|marker)`.
- Camera Override box in the Scene World & Shadows section and Sidebar N.
- Gate coverage for camera overrides and base-palette invariance.

### Changed
- Shot markers no longer overwrite `Scene.ald.palette`; they set the effective
  palette only. The base palette is preserved for non-marker shots.
- Palette changes, world controls and `Apply Palette` all resolve the effective
  palette instead of assuming the base.
- `compositor` glare tints and `shadow_tint_for` use the effective palette key.
- Version 0.6.0.

## 0.5.0 — 2026-10-19
### Added
- **Cel terminator** in the Shadow Tint group: `N·L` against the palette sun,
  combined with AO, with Cel Shadow strength and Terminator sharpness controls.
- **Directional rim light** on the sun-facing Fresnel edge, tinted by the sun
  color; Rim Strength and Rim Width controls. The HAIR preset gets an automatic
  angel-ring boost.
- Sun direction/color are pushed into every tinted material and refreshed on
  `frame_change_post`, without rebuilding materials.
- Gate render checks for the toon terminator and rim light, plus sun direction and
  hair rim boost.

### Changed
- Shadow Tint group upgraded with `Sun Direction`, `Sun Color`, `Toon Strength`,
  `Terminator Sharpness`, `Rim Strength` and `Rim Width`; the interface is
  extended without clearing, so existing texture links survive upgrades.
- Defaults: Cel Shadow 0.75, Terminator 0.035, Rim Strength 0.45, Rim Width 0.4.
- `materials.py` now registers a frame handler for the sun direction.

## 0.4.0 — 2026-10-19
### Added
- **Sun disk** in the world gradient, aligned with the sun direction; size and
  strength controls.
- **Anime clouds**: two-layer procedural noise, projected sky colors (shadow /
  horizon / sun), horizon fade and amount/scale controls.
- **Anime Ink Lines**: thin depth-discontinuity outlines composited with a dark
  shadow-tint color; strength and size.
- **Sakura Spring** and **Twilight Dusk** atmosphere presets.
- **Custom palette colors**: sky, horizon, sun and shadow overrides per scene,
  exposed in the Scene and Sidebar N panels.
- Gate coverage: sun direction/disk strength, cloud toggle, ink node + pixel test,
  custom colors and preset restore.

### Changed
- World gradient group upgraded (sun disk + clouds) with `ald_build = 3`.
- Sun/cloud frame updates run on `frame_change_post` so animated transforms are
  evaluated before reading sun matrices.
- Shadow tint colors for the new presets are normalized multiplier hues.
- Look-dev renders all six palettes in a 3×2 sheet.

## 0.3.2 — 2026-10-19
### Added
- **Sidebar N panel** (`VIEW_3D > Anime Look`) with palette, world, shadow tint,
  compositor toggles/sliders, build/remove and viewport compositor.
- Gate checks for in-place parameter updates, God Rays node creation with the sun
  behind the camera, and the multiplicative shadow tint.

### Changed
- **Slider performance**: float properties now call `compositor.update_params()`
  and rewrite only node sockets. Booleans still rebuild the topology. Kuwahara,
  halation, dispersion, light wrap, God Rays and depth range update in place.
- **Shadow tint is multiplicative**: `MULTIPLY` preserves texture detail in
  shadowed areas; palette shadow colors are normalized multiplier hues.
- **God Rays node is always created** when enabled; if the sun is behind the
  camera at build it starts at `(0.5, 0.5)` with strength 0 so the frame handler
  can bring it in later.
- Halation strength range corrected to 0–1 to match the Glare socket.

## 0.3.1 — 2026-10-19
### Added
- God Rays **Size** control.
- God Rays live refresh on frame change: the Sun Position follows the camera and
  sun during animation; the node is muted (strength 0) when the sun goes behind
  the camera and restored when it comes back.
- **Emission** material preset (neon surface) with Emission Color/Strength; other
  presets explicitly reset emission strength.
- `RECAP.md`: an Italian end-to-end recap of the add-on.

### Changed
- Sun Beams defaults: 6 iterations, fade 0.95.
- Version 0.3.1.

## 0.3.0 — 2026-10-19
### Added
- **God Rays**: optional Sun Beams glare placed at the sun's projected screen
  position, with a strength control. The node is skipped when the sun is behind
  the camera.
- **Shot markers**: opt-in per-shot palette changes from timeline markers named
  `ALD:<PALETTE>`; the `Mark Shot` operator writes/updates the marker at the
  current frame.
- **Material presets**: Skin, Hair, Fabric and Metal, assigned to selected
  objects and integrated with the shadow tint.
- Sub-panels for World & Shadows and Compositor Stack; the main panel keeps
  Atmosphere, Material Presets, build/remove and stack status visible.
- Gate coverage for the Sun Beams node and projected sun position, shot markers
  and material presets.

### Changed
- Version bump to 0.3.0; README, AGENTS.md and TECH_NOTES.md updated.

## 0.2.1 — 2026-10-19
### Added
- Auto Sun: applying a palette creates a tagged sun light when the scene has
  none; toggle in the World & Shadows panel section.
- Per-scene compositor stacks: each scene gets its own `ALD | Compositor Stack`
  group (suffixed when names collide), so multiple scenes no longer fight over
  one Render Layers node.
- Gate checks for auto-sun creation/toggle and for two scenes with independent
  stacks (build, Render Layers scene, removal isolation).

### Changed
- `ald.remove` unassigns the scene's stack and deletes it only when no other scene
  uses it; custom compositor groups are left untouched.

## 0.2.0 — 2026-10-19
### Added
- Palette-driven world gradient (sky / horizon / ground) with horizon offset and
  softness, built in the shared `ALD | World Gradient` node group.
- Shadow tint on scene materials through the shared `ALD | Shadow Tint` group:
  an AO mask mixes Base Color toward the palette shadow color.
- Light Wrap stage in the compositor stack, using a depth-derived silhouette
  mask, depth-discontinuity edges and blurred scene light.
- Gate checks for gradient, shadow tint insert/remove/restore, light wrap graph,
  rebuild idempotency and `bl_info` / manifest version consistency.
- Render-level gate checks: shadow tint and light wrap must change pixels, and the
  light wrap must stay edge-local.
- `preset_dev/lookdev.py` renders all four palettes on a fixed scene and builds a
  contact sheet for look development.

### Changed
- `ald.build` and `ald.apply_palette` also sync the shadow tint on scene materials.
- `ald.clear_shadow_tint` restores every touched Base Color link or value.
- Light wrap is composited as straight alpha, so the blurred image cannot leak
  over the whole frame.
- The world depth threshold follows the camera clip end (EEVEE writes
  `clip_end + 0.55`, Cycles writes ~1e10).
- Horizon softness now maps to a tighter falloff, so the sky gradient reads in a
  normal framing.
- Summer Noon is slightly less milky; Neon Night has a blue-violet zenith.

### Fixed
- World gradient colors are socket-driven (Mix + Map Range) instead of a static
  ColorRamp that ignored the palette.
- Light wrap no longer blurs the whole image because of premultiplied alpha.
- Depth-based light wrap now detects object-on-object silhouettes, not only
  geometry against the world.

## 0.1.0 — 2026-10-19
- Initial skeleton: Scene settings, four atmosphere presets, compositor node-group
  stack (Glare, Kuwahara with depth mix, Lens Distortion), operators and Scene panel.
- Headless gate `preset_dev/verify.py`.
