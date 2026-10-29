# Anime Look Director - World Sky Edition validation

Current release: **2.62.0** (Blender 5.1.2, Windows 11).

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify_all.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_matrix.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_technical.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\build_release.py
& $blender -b --factory-startup --gpu-backend vulkan --python-exit-code 1 `
  --python preset_dev\phase1a_shooting_stars.py -- --out <dir>
```

## Latest results

| Category | Command / evidence | Result |
|---|---|---|
| World / structural / runtime | `verify.py` | **ALD GATE: PASS** |
| Lifecycle | `world_fixture.py` | **WORLD FIXTURE: PASS** |
| Source audit | `audit_world.py` | **ALD WORLD AUDIT 44/44 OK** |
| Whole chain | `verify_all.py` | **ALD ALL: PASS** |
| Phase 0 baseline | `world_baseline/contact_1280.png`, `contact_1920.png`, `contact_sun.png` | v1.0.3 / v1.1.0 / v2.56.0 compared |
| Phase 2 sky | `sky/contact.png`, `sky/metrics.json` | noon / sunset / dusk / night, clouds off |
| Phase 3 clouds | `cloud_families/contact.png`, `metrics.json` | Cumulus / Stratocumulus / Cirrus, same day sun |
| Phase 3 sunset | `cloud_sunset/contact.png`, `metrics.json` | GOLDEN_HOUR, side and backlit |
| Shooting stars (2.60.1) | `shooting_star/contact.png`, `metrics.json` | persistent event, frames 1/8/16/25/30 |
| Shooting stars Phase 1A (2.63) | `phase1a_shooting_stars/board.png`, `board_horizon.png`, `temporal.png`, `migration.png`, `backend.png`, `interactive.png`, `lifecycle.mp4`, `metrics.json`, `review.json` | **37/37 PASS** on Eevee OpenGL and Vulkan; interactive Preview **5/5 PASS**; temporal and four-event migration verified; **FINAL TECHNICAL REVIEW: PASS**; merged to `master` at `63ffa29` |
| Shooting stars Phase 1B (candidate) | `phase1b_shooting_stars/candidate_elevations.png`, `candidate_lifecycle.png`, `candidate_context.png`, `candidate_head_tip.png`, `candidate_lifecycle.mp4`, `candidate_metrics.json`, `markers.json`, `performance.json` | **37/37 PASS** on OpenGL and Vulkan; interactive **5/5**; markers 29/30 -> 31; **VISUAL APPROVED**; merged to `master` at `fe685d5` |
| Atmosphere / Sun Phase 2 (candidate) | `phase2_atmosphere/board_conditions.png`, `board_second.png`, `board_sweep.png`, `board_offsets.png`, `board_controls.png`, `board_ui.png`, `phase2_metrics.json`, `phase2_tests.json` | **37/37 PASS** both backends; interactive **5/5**; markers 29/30/31 -> 32; **TECHNICAL PASS - VISUAL REVIEW PENDING** |
| UI cleanup Phase 3 | `phase3_ui/sidebar_before.png`, `sidebar_after.png`, `properties_before.png`, `properties_after.png`, `empty_project.png`, `shooting_stars_before.png`, `shooting_stars_after.png`, `shooting_stars_added.png`, `compositor_inactive.png`, `compositor_disabled.png`, `compositor_active.png`, `legacy_project.png`, `sidebar_narrow.png` | full Scene Properties mirror in the sidebar, autonomous Shooting Stars, compositor states, empty project, legacy project and narrow layout |
| Phase 3 UI checks | `phase3_ui/phase3_ui.json` | **68 checks PASS** (panels, mirror, states, user group, lifecycle, legacy) |
| Phase 3 invariance | `phase3_ui/phase3_invariance.json`, `invariance_compare.png` | **pixel-identical, maxdiff 0**; World 719 / Compositor 31 nodes; marker 32 |
| Phase 3 regressions | `phase3_ui/logs/` | ALD ALL PASS; audit 44/44; Phase 6 17/17; Phase 1A 37/37; Phase 1B markers 29/30 -> 32; Phase 2 audit PASS; build PASS |
| Phase 4 star look | `star_thickness/`, `star_curvature/`, `cloud_sun_scatter/` | thickness cap 0.01 rad + head cap; per-event curvature; sun-facing scatter; **visual review pending** |
| Phase 4 checks | `star_curvature/phase1a_metrics.json`, logs | 68/68 UI; 37/37 Phase 1A; 44/44 audit; 17/17 Phase 6; ALD ALL; build PASS |
| Phase 6 matrix | `phase6/contact.png`, `phase6/metrics.json` | 22 cells: families x Sun, palettes, coverage, camera, wind, stars |
| Phase 6 technical | `phase6/technical.json` | **17/17 PASS** |
| Legacy migration (2.63 work) | `legacy/report.json`, `legacy/v256_report.json` | synthetic **36/36**; real v2.56.0 `.blend` **9/9** |
| Cumulus baseline (2.63 work) | `phase1/contact.png`, `phase1/contact_lighting.png`, `phase1/metrics.json` | v1.0.3 vs v2.62 native/calibrated; **TECHNICAL PASS / VISUAL REVIEW PENDING** |
| Palettes | `palettes/sheet.png` | 12 presets, same camera and light |
| UI | `preset_dev/phase3_ui/` | full Scene Properties mirror in the sidebar, autonomous Shooting Stars, compositor states; UI review pending |
| Package | `dist/anime_look_director-2.62.0.zip` | extension build PASS; 2.62.0 installed and enabled in an isolated config |

## Definition of done

| Item | Status | Evidence |
|---|---|---|
| World applies without FX objects | DONE | `verify.py` |
| World applies without the compositor | DONE | palette applied with no stack assigned |
| No Spatial Clouds / smoke / FX pass | DONE | modules removed; source audit |
| No FX UI or operators in the path | DONE | panels/operators/source audit |
| Persistent identity and Sun protection | DONE | `identity.py`, `ownership.py`, technical gate |
| Snapshot restore | DONE | gate snapshot fixture |
| Legacy data is explicit and reversible | DONE | Disable/Remove operators, `MIGRATION_2_57.md` |
| Old files are not auto-cleaned | DONE | documented, source audit |
| Phase 0 visual baseline | DONE | `preset_dev/world_baseline/` |
| Phase 2 cloudless sky | DONE | broad accent, Sun fade, `preset_dev/sky/` |
| Phase 3 cloud families | DONE | Cumulus gate approved; the 22-cell matrix covers all three |
| Phase 3 sunset | APPROVED | GOLDEN_HOUR side/backlit |
| Shooting stars | APPROVED | controlled event, Preview, starfield-consistent line |
| Phase 5 presets/UI | DONE | five presets, Quick Look, full Scene sections |
| Phase 6 release | DONE | 22-cell matrix, 17/17 technical gate, package and merge |
| Phase 3 UI cleanup (2.63) | TECHNICAL PASS | full Scene Properties mirror in the sidebar, autonomous Shooting Stars, compositor states, 68 checks, pixel-identical; **UI review pending** |
| Phase 4 star look (2.63) | TECHNICAL PASS | thickness cap, curvature, cloud sun scatter; 68 UI, 37/37 Phase 1A, 44/44 audit, 17/17 Phase 6, build PASS; **visual review pending** |
| Legacy disable/remove (2.63 Phase 0) | DONE | tag-based discovery, per-scene Disable/Restore, confirmed Remove |

## Pending 2.63 work

Phase 0 (legacy safety), Phase 1 (Cumulus baseline), Phase 1A/1B (shooting
stars) and Phase 2 (atmosphere, technical) are complete in the working tree;
this is not a release. The Phase 1 comparison and Phase 2 atmosphere are
technically complete but their visual decisions are pending.

Phase 3 UI cleanup is on `phase-3-ui-cleanup` from `d8a94d8`: the viewport
sidebar mirrors the full Scene Properties sections, Shooting Stars is
autonomous, and the compositor states are explicit. The render is pixel-identical
to the base. **TECHNICAL PASS - UI REVIEW PENDING**; no merge or release. The
version stays 2.62.0 until the gates and the final candidate are approved. See
`preset_dev/phase3_ui/README.md`.

Phase 4 star/cloud look is on `feature/star-cloud-look` from `4db6718`:
Shooting Star thickness cap/head cap, per-event `Curvature` (default 0) and
`Cloud Sun Scatter` (default 0). Evidence in `star_thickness/`,
`star_curvature/` and `cloud_sun_scatter/`. **TECHNICAL PASS - VISUAL REVIEW
PENDING**; no merge or release.

## Open aesthetic point

Stratocumulus and Cirrus are documented in `phase6/contact.png` but do not have
an individual user sign-off; Cumulus is the approved family. The matrix is the
reference for that decision.

## Deliberate limits

- The optional compositor is kept for general art filters; it is not part of
  the sky and is not required.
- Old FX/cloud settings are no longer registered; old data is ignored and has
  no UI, handlers or runtime effect.
- The Old World fireworks/meteors are disabled; the controlled shooting stars
  are the supported system.
- The world has no dedicated moon; Moonlit Night uses the Sun disk and a cool
  palette.
- Cirrus wisps can partially occlude the Sun disk; that is expected for the
  family, not a broken disk.
- Legacy Disable hides tagged collections per view layer; standalone anchor and
  ground helpers are only deleted by the confirmed Remove.
- Remove never deletes a collection or object shared with another scene.
