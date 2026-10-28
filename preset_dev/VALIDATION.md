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
| Shooting stars Phase 1A (2.63) | `phase1a_shooting_stars/board.png`, `board_horizon.png`, `temporal.png`, `migration.png`, `backend.png`, `interactive.png`, `lifecycle.mp4`, `metrics.json`, `review.json` | **37/37 PASS** on Eevee OpenGL and Vulkan; interactive Preview **5/5 PASS**; temporal and four-event migration verified; **FINAL TECHNICAL REVIEW: PASS** (merge authorization pending) |
| Phase 6 matrix | `phase6/contact.png`, `phase6/metrics.json` | 22 cells: families x Sun, palettes, coverage, camera, wind, stars |
| Phase 6 technical | `phase6/technical.json` | **17/17 PASS** |
| Legacy migration (2.63 work) | `legacy/report.json`, `legacy/v256_report.json` | synthetic **36/36**; real v2.56.0 `.blend` **9/9** |
| Cumulus baseline (2.63 work) | `phase1/contact.png`, `phase1/contact_lighting.png`, `phase1/metrics.json` | v1.0.3 vs v2.62 native/calibrated; **TECHNICAL PASS / VISUAL REVIEW PENDING** |
| Palettes | `palettes/sheet.png` | 12 presets, same camera and light |
| UI | `preset_dev/ui/` | Quick Look, Advanced Sky, full Scene sections |
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
| Phase 5 presets/UI | DONE | five presets, Quick Look + Advanced Sky, explicit compositor |
| Phase 6 release | DONE | 22-cell matrix, 17/17 technical gate, package and merge |
| Legacy disable/remove (2.63 Phase 0) | DONE | tag-based discovery, per-scene Disable/Restore, confirmed Remove |

## Pending 2.63 work

Phase 0 (legacy safety) and Phase 1 (Cumulus baseline) are complete in the
working tree; this is not a release. The Phase 1 comparison is technically
complete but its visual decision is pending. The version stays 2.62.0 until
the Cumulus gates and the final candidate are approved. See
`preset_dev/legacy/README.md` and `preset_dev/phase1/README.md`.

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
