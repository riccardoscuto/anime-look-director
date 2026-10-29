# Star thickness cap (Phase 4)

Merged in the 2.63.0 release candidate; visual status approved.

The `Thickness` slider is an angular radius in radians. The old maximum
`0.05 rad` (about 2.86 deg) produced a huge tapered wedge, with the head glow
reaching about 4.7 deg. This fix caps the useful range and decouples the head
glow from a linear thickness blow-up.

## Changes

- `Thickness` property maximum: `0.05` -> **`0.01 rad`** (about 0.57 deg);
  default `0.0018` unchanged.
- Shader: effective thickness clamped to `0.01` for old saved events too.
- Shader: head radius capped at `0.012 rad`; the body keeps the requested
  thickness. A thick trail stays a trail instead of becoming a giant disc.
- World marker `33`; the group rebuilds on load.

## Evidence

- `before_0_05.png`: base `4db6718` with `Thickness 0.05`.
- `after_0_05.png`: same request on this branch; property and shader socket
  both read `0.01`.
- `after_0_01.png`: explicit maximum.
- `after_0_0018.png`: default, unchanged.
- `compare.png`: 2x2 comparison.
- `metrics.json`: requested/property/shader values.

Render fixture: EEVEE, 960x540, NEON_NIGHT, clouds off, one star at
azimuth/elevation 120/40, frame 20. The only difference between before and
after is the thickness clamp/head cap.

## Reproduce

```powershell
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\star_thickness.py -- <out>
```

Run the same script on a `4db6718` worktree for the before images.
