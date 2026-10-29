# Phase 3 - UI Cleanup (2.63)

Branch: `phase-3-ui-cleanup`, based on `d8a94d8` (Phase 2 atmosphere candidate).
Blender 5.1.2. Version stays 2.62.0. No merge, tag or release.

**Status: TECHNICAL PASS - UI REVIEW PENDING.**

## Scope

Interface-only cleanup. The World shader, cloud generator, shooting-star
shader, materials, presets and compositor graph are unchanged. The expected
result is the same render as the base branch.

## What changed

- View3D sidebar: mirrors the Scene Properties sections with the same drawing
  functions. The root holds the palette and the sub-panels are Atmosphere &
  Sun, World Clouds, Stars & Milky Way, Shooting Stars, Palette Customization,
  Materials & Shadows, Compositor and Advanced Settings. The sub-panels are
  open and scrollable.
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

## Internal shader slots

The `Star0`..`Star3` sockets on the `ALD | World Gradient` node group (Start
U/V, End U/V, Start Frame, Duration, Trail, Thickness, Brightness, Glow,
Enabled) are internal shader slots for the four controlled events. They are
not add-on controls: the Shooting Stars panel writes them. They are visible
only if the node group interface is opened in the Shader Editor and should not
be edited by hand.

## Screenshots

All images are captures of Blender 5.1.2. The standard fixture is NEON_NIGHT,
clouds on, stars on, one shooting star, camera at the default framing. The
`empty_*` images use a fresh scene with no objects; the `shooting_stars_*`
sequence uses the standard scene with the event list cleared first.

| File | Shows |
|---|---|
| `sidebar_before.png` | Base `d8a94d8`: Quick Look + Advanced Sky + Compositor, no Clouds toggle |
| `sidebar_after.png` | Current: full Scene Properties mirror in the sidebar (palette root + open sections) |
| `sidebar_narrow.png` | Current at 1200x900: full mirror, no control clipped or overlapped |
| `properties_top_before.png` | Base Scene Properties top |
| `properties_top_after.png` | Current Scene Properties top |
| `properties_before.png` | Base: Sun Glow and Sun Beams in the same row; ungrouped clouds |
| `properties_after.png` | Current: Sun Beams gone; grouped clouds and stars |
| `empty_project.png` | Scenario A: fresh scene after Apply Palette; sidebar only, no compositor |
| `empty_compositor.png` | Scenario A: the same scene with the compositor panel inactive |
| `shooting_stars_before.png` | Base: Shooting Stars inline in Stars & Milky Way |
| `shooting_stars_after.png` | Current: autonomous Shooting Stars with the event list |
| `shooting_stars_controls.png` | Current: Timing, Trajectory and Appearance |
| `shooting_stars_empty.png` | Scenario C: no controlled event |
| `shooting_stars_added.png` | Scenario C: Add creates the selected event |
| `shooting_stars_duplicated.png` | Scenario C: Duplicate creates a copy at +12 frames |
| `shooting_stars_preview.png` | Scenario C: Preview moves the timeline and frames the event |
| `shooting_stars_removed.png` | Scenario C: Remove deletes the selected event |
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
| Panel registration, states and operators | 68/68 checks PASS (`phase3_ui.json`) |
| Scenario A: preset with no compositor | PASS; `empty_project.png` and `empty_compositor.png` |
| Scenario B: Sun, horizon, clouds, stars | PASS |
| Scenario C: add / duplicate / preview / remove and four-event cap | PASS; GUI sequence `shooting_stars_*` and `shooting_stars_lifecycle.json` |
| Scenario D/E: inactive, foreign group, disabled, active | PASS |
| Scenario F: real legacy project (4 events, marker 29, no stack) | PASS |
| Scenario G: narrow and wide layout | PASS; full mirror at 1200x900 and 1920x1009 |
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
`phase1b_markers.json`, `phase2_audit.json`, `screenshots.json` and
`shooting_stars_lifecycle.json` keep the machine-readable output.

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
`preset_dev/phase3_screenshots.py` for the arguments. Example:

```powershell
& $blender --python preset_dev\phase3_screenshots.py -- `
  --out <dir> --variant current --state inactive --steps 0,20,38,46,62
& $blender --python preset_dev\phase3_screenshots.py -- `
  --out <dir> --variant empty --state empty --steps 0,62
& $blender --python preset_dev\phase3_screenshots.py -- `
  --out <dir> --variant stars --state stars --steps 0
```

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
  and the full mirror is scrollable, with no control clipped horizontally. No
  12-preset review was started.
