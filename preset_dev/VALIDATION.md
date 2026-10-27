# Anime Look Director - World Sky Edition validation

Current release: **2.62.0** (Blender 5.1.2, Windows 11).

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify_all.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_matrix.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_technical.py
& $blender -b --factory-startup --python preset_dev\build_release.py
```

## Latest results

| Category | Command / evidence | Result |
|---|---|---|
| World / structural / runtime | `verify.py` | **ALD GATE: PASS** |
| Lifecycle | `world_fixture.py` | **WORLD FIXTURE: PASS** |
| Source audit | `audit_world.py` | **ALD WORLD AUDIT 40/40 OK** |
| Whole chain | `verify_all.py` | **ALD ALL: PASS** |
| Phase 0 baseline | `world_baseline/contact_1280.png`, `contact_1920.png`, `contact_sun.png` | v1.0.3 / v1.1.0 / v2.56.0 compared |
| Phase 2 sky | `sky/contact.png`, `sky/metrics.json` | noon / sunset / dusk / night, clouds off |
| Phase 3 clouds | `cloud_families/contact.png`, `metrics.json` | Cumulus / Stratocumulus / Cirrus, same day sun |
| Phase 3 sunset | `cloud_sunset/contact.png`, `metrics.json` | GOLDEN_HOUR, side and backlit |
| Shooting stars | `shooting_star/contact.png`, `metrics.json` | persistent event, frames 1/8/16/25/30 |
| Phase 6 matrix | `phase6/contact.png`, `phase6/metrics.json` | 22 cells: families x Sun, palettes, coverage, camera, wind, stars |
| Phase 6 technical | `phase6/technical.json` | **17/17 PASS** |
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
