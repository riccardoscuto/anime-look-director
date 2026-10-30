# Celestial 2 - Gate 0 baseline and integration strategy

Branch `feature/celestial`, based on the released `v2.63.0` (`5d6725c`).
Phase 0 only: no shader or feature change in this step.

## Baseline (2.63.0, measured 2026-10-30)

World group `ALD | World Gradient`, clouds + stars + Milky Way active, lookdev
scene, native Sun, EEVEE / Vulkan, 32 samples, AgX, compositor off:

| Metric | Value |
|---|---|
| Nodes | **793** |
| Links | **1,215** |
| Group sockets | **89** |
| Group rebuild (`apply_palette`) | **2.71-3.07 s** |
| Render 1280x720 | 0.41-0.63 s |
| Render 1920x1080 | 0.55-0.56 s |
| Render 2560x1440 | 0.86-0.89 s |

Node types: 550 Math, 106 Vector Math, 56 Map Range, 24 Mix, 13 Noise,
5 Voronoi; the rest are coordinates, mapping and RGB. The group is built by a
single ~1,855-line function (`palette._build_gradient_group`) inside a
3,317-line module.

Reference renders: `baseline/renders/` (JPEG q92, small enough to open from the
repo). `baseline/metrics.json` has the numbers and file sizes. Memory was not
measured; it is deferred to the per-phase performance matrix (11.4).

Reproduce:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\celestial_baseline.py -- --out preset_dev\celestial\baseline
```

## Current coupling map

- **`apply_palette`** is the single entry point. It calls `snapshot.ensure`
  (first write), `ensure_sun` (scene Sun light: energy, color, rotation),
  `apply_preset_style` (scene.ald values, cloud seed), `_apply_gradient`
  (World group sockets) and `sync_sun_angles`.
- **Sun direction** is shared: `sun_toward(scene)` converts the Sun object
  rotation to a unit vector, wired to `Sun Direction`. The World uses it for
  the disk, the glow, the cloud lighting and the star solar mask. Object
  lighting uses the Sun object itself. One direction, two consumers.
- **Clouds** are evaluated inside the World group. The group exposes a cloud
  visibility signal used to mask stars, the Milky Way and shooting stars. Moon
  and Milky Way Phase 2 must reuse this mask, not recompute clouds.
- **Stars** read `Sun Direction` (hide the solar disk), the zenith and cloud
  coverage; the Milky Way boosts star density along its band.
- **Milky Way** is a hard-coded diagonal axis with a noise warp; no rotation,
  width, core or dust controls yet.
- **Compositor** is independent: `look.apply` builds it only when the user
  enables it, and the World never depends on it. Materials only consume the
  palette shadow tint.
- **Frame handler**: `update_sun_controls` rewrites `Sun Direction`/`Sun Color`
  from the Sun object, so animated Sun rotation reaches the shader.

## Separation rule (sky drawing vs object lighting)

The World shader only draws sky. It never claims to light the scene. A visible
disk needs a direction socket; object illumination needs a light object. Sun
keeps both because it already did. The Moon, when added, gets its own
`Moon Direction` socket and, only if the optional light is implemented, a
dedicated source with its own tag, owner and cleanup. No automatic second
light: the Moon visual and the Moon light are independent switches.

## Target module layout (Phase 1+)

Keep `palette.py` as presets + apply orchestration. Put new node logic in a
package, one module per feature, each returning a Blender node group:

```
shaders/__init__.py
shaders/common.py      node helpers (math, map range, mix, smooth)
shaders/sun.py         ALD | Sun Disk
shaders/moon.py        ALD | Moon
shaders/stars.py       ALD | Stars
shaders/milky_way.py   ALD | Milky Way
```

The World keeps one stable parent group, `ALD | World Gradient`, so the
external API does not change. The parent wires the child groups once; features
toggle through strength sockets, never by rebuilding topology. Existing cloud
and shooting-star builders stay where they are until a dedicated refactor;
they are not part of the Moon milestone.

## Group versioning and migration

- A scene integer `ald_sky_version` records the schema the group was built
  with (2.63.0 = 1). The group name stays `ALD | World Gradient`.
- Migration runs **only on explicit Apply**, never on file open. If the scene
  version is older, the group is rebuilt and every socket value is copied by
  name; new sockets take defaults. Shooting stars, markers, camera overrides
  and animations are untouched.
- A schema rebuild preserves the current values. It does not re-apply preset
  colours: that stays an artistic action.
- Old groups remain readable: a file opened without Apply renders exactly as
  before. Snapshot restore is unchanged.
- Identification adds a marker custom property on the group node so a user
  group with the same name is never mistaken for ALD.

## Gate 0

- [x] Development branch from the stable release (`feature/celestial`).
- [x] Baseline preserved by tag `v2.63.0`.
- [x] Node/link/socket counts, rebuild and render time measured.
- [x] Reference renders at 720p, 1080p and 1440p.
- [x] Shared-link map documented.
- [x] Sky/light separation principle documented.
- [x] Modular group layout defined.
- [x] Versioning and migration strategy defined.
- [x] Existing tests: `verify_all` **ALD ALL PASS**, World audit 44/44.

**Gate 0: PASS (strategy) - Phase 1 and 2A approved, 2B ready.**

Evidence in `preset_dev/moon/`: full disk, phase geometry and animation are
approved; earthshine/halo refinements await the final Gate 2 review. The Moon
milestone does not change the 12 presets, the clouds or the compositor.
