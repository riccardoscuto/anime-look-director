# Phase 3 - UI Cleanup (2.63)

Branch: `phase-3-ui-cleanup`, based on `d8a94d8` (Phase 2 atmosphere candidate).
Blender 5.1.2. Version stays 2.62.0. No merge, tag or release.

**Status: TECHNICAL PASS - UI REVIEW PENDING.**

## Scope

Interface-only cleanup. The World shader, cloud generator, shooting-star
shader, materials, presets and compositor graph are unchanged. The expected
result is the same render as the base branch.

## What changed

- View3D sidebar: Quick Look only (preset, Apply/Reset, Sun Elevation, Clouds
  on/off, Cloud Type, Cloud Amount, Cloud Wind, Stars). Removed the duplicated
  Advanced Sky panel and the compositor panel.
- Scene Properties order: Atmosphere & Sun, World Clouds, Stars & Milky Way,
  Shooting Stars, Palette Customization, Materials & Shadows, Compositor,
  Advanced Settings.
- Sun Beams moved out of Atmosphere & Sun; it exists only in Compositor >
  Light Effects. Sun Glow stays in the World.
- World Clouds grouped as Distribution / Shape / Lighting / Animation.
- Shooting Stars is an autonomous panel with the event list and Timing /
  Trajectory / Appearance groups. The four operators and the four-event limit
  are unchanged.
- Compositor has explicit states through `compositor.scene_stack()`:
  - Inactive: no ALD stack; only Enable Compositor is offered.
  - Configured / render disabled: the ALD stack exists, `Use in Render` is off.
  - Active in render: the stack is used by the final render.
  - Viewport preview: read-only status from the 3D view shading; the UI does
    not force a shading mode and never enables the compositor automatically.
  - A user compositor group is never reported, changed or removed as ALD.
- `ald.viewport_compositor` is limited to the current 3D viewport and is not
  invoked by any UI control.
- Advanced Settings separates reversible actions (Disable/Restore legacy
  visibility) from destructive ones (Remove Permanently, scene actions).

## Screenshots

All images are captures of Blender 5.1.2 with the same fixture: NEON_NIGHT,
clouds on, stars on, one shooting star, camera at the default framing.

| File | Shows |
|---|---|
| `sidebar_before.png` | Base `d8a94d8`: Quick Look + Advanced Sky + Compositor, no Clouds toggle |
| `sidebar_after.png` | Current: compact Quick Look, Clouds toggle and cloud controls |
| `sidebar_narrow.png` | Current at 1200x900: no control clipped or overlapped |
| `properties_top_before.png` | Base Scene Properties top |
| `properties_top_after.png` | Current Scene Properties top |
| `properties_before.png` | Base: Sun Glow and Sun Beams in the same row; ungrouped clouds |
| `properties_after.png` | Current: Sun Beams gone; grouped clouds and stars |
| `shooting_stars_before.png` | Base: Shooting Stars inline in Stars & Milky Way |
| `shooting_stars_after.png` | Current: autonomous Shooting Stars with the event list |
| `shooting_stars_controls.png` | Current: Timing, Trajectory and Appearance |
| `compositor_inactive.png` | Inactive: no ALD stack |
| `compositor_disabled.png` | Configured; render disabled |
| `compositor_active.png` | Active in render |
| `compositor_effects.png` | Light Effects, Stylization, Atmospheric Post Effects |
| `legacy_project.png` | Real pre-2.57 project with four events, loaded in the new UI |
| `invariance_current.png` / `invariance_base.png` | Render comparison |
| `invariance_compare.png` | Side-by-side with the pixel result |

The before set is generated from `d8a94d8` with an isolated
`BLENDER_USER_SCRIPTS`; the current set is generated from this branch. Both
use the same startup fixture and window layout.

## Results

| Check | Result |
|---|---|
| Panel registration, states and operators | 54/54 checks PASS (`phase3_ui.json`) |
| Scenario A: preset with no compositor | PASS |
| Scenario B: Sun, horizon, clouds, stars | PASS |
| Scenario C: add / duplicate / preview / remove and four-event cap | PASS |
| Scenario D/E: inactive, foreign group, disabled, active | PASS |
| Scenario F: real legacy project (4 events, marker 29, no stack) | PASS |
| Scenario G: narrow and wide layout | PASS; see the screenshots |
| Render invariance | pixel-identical, `maxdiff 0` |
| World / Compositor nodes | 719 / 31 on base and current |
| World marker | 32 on both |
| `verify.py` | `ALD GATE: PASS` |
| `verify_all.py` | `ALD ALL: PASS` |
| `audit_world.py` | `44/44 OK` |
| `phase6_technical.py` | `17/17 PASS` |
| `phase1a_shooting_stars.py` | `37/37 PASS` |
| `phase1b_markers.py` | markers 29/30 -> 32; events, properties and animation preserved |
| `phase2_audit.py` | PASS; UI elevation values sync to the World |
| `build_release.py` | `ALD BUILD: PASS` |

Logs are in `logs/`. `phase3_invariance.json`, `phase1a_metrics.json`,
`phase1b_markers.json` and `phase2_audit.json` keep the machine-readable output.

## Reproduce

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase3_ui.py
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\phase3_invariance.py -- <out> current
# Run the same invariance script on d8a94d8 with an isolated scripts path.
```

The GUI screenshots need a user config with `show_splash = False`; the harness
does not call `read_factory_settings` in the GUI timer. See
`preset_dev/phase3_screenshots.py` for the arguments.

## Limitations

- The viewport preview line is status only. It reports the first 3D view's
  `Compositor` shading option; it does not switch the viewport to Rendered.
- The compositor is still optional and manual. This phase did not add automatic
  enable, depth-of-field, or a new effect.
- The legacy project is not rewritten on load. Its shader marker remains 29
  until the user applies a palette; the World, four events, names and values
  are preserved.
- No aesthetic review of the UI was performed. This is a technical pass only.
- The narrow capture is the full 1200x900 window; the sidebar is fixed-width
  and remains fully visible. No 12-preset review was started.
