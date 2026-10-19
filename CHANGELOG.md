# Changelog

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
