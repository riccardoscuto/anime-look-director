# 2.39 cloud baseline vs 2.55

The operational plan asked for a 2.39 / current comparison on the same scene,
resolution and camera. The 2.39 source is still available at the
`v2.39.0` tag, so the summary "not reproducible" of the earlier audit is
superseded by this measurement.

## Method

- `git worktree add` at `v2.39.0`; the add-on files are copied into a temporary
  `BLENDER_USER_SCRIPTS/addons/anime_look_director`, so the current 2.55 add-on
  is not the one enabled. `BLENDER_USER_CONFIG` is also temporary.
- Same camera rotation `1.95`, palette `AFTER_SCHOOL`, `1280x720`, EEVEE, AgX,
  exposure 0.
- 2.39: `clouds.create(scene, amount=0.65, height=0.35)` (the three old wavy
  bands at 160 / 230 / 320 m).
- 2.55: the Final spatial cards, coverage 0.5, 3 layers (the benchmark entry
  `c0.50_l3`).
- Three runs per add-on; the first render is warm-up; the table reports the
  median.

## Result

| Add-on | Geometry | Creation | Render (median) |
|---|---|---|---|
| 2.39.0 | 1,536 quads (3 cards) | 0.0072 s | 3.275 s (first run 4.438 s) |
| 2.55 | 57,968 triangles (3 card layers) | 0.518 s | 2.723 s |

Raw records: `legacy_2_39.json`, `metrics.json`; the old render is
`legacy_2_39.png`, the new reference `c0.50_l3.png`.

## Caveats

- The old mesh is quads, the new one triangles; the new is about **19x** the
  triangles and **72x** the creation time. The render is comparable/slightly
  faster on this machine and scene, not a general performance win.
- The old amount 0.65 and the new coverage 0.5 are the closest artistic
  settings, not an exact same-coverage measurement.
- The 2.39 and 2.55 baseline scenes share the camera, resolution, palette key
  and render settings; the world/palette implementations and the add-on code
  differ by design.
- The old cards are the wavy bands, the new ones are the interpolated islands;
  the comparison is between the two looks, not only between two meshes.
