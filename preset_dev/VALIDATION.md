# Anime Look Director — World Sky Edition validation

Current release: **2.58.0** (Blender 5.1.2, Windows 11).

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python preset_dev\verify_all.py
& $blender -b --factory-startup --python preset_dev\build_release.py
```

## Latest results

| Category | Command / evidence | Result |
|---|---|---|
| World / structural / runtime | `verify.py` | **ALD GATE: PASS** |
| Lifecycle | `world_fixture.py` | **WORLD FIXTURE: PASS** |
| Source audit | `audit_world.py` | **ALD WORLD AUDIT 23/23 OK** |
| Whole chain | `verify_all.py` | **ALD ALL: PASS** |
| Phase 0 baseline | `world_baseline/contact_1280.png`, `contact_1920.png`, `contact_sun.png` | v1.0.3 / v1.1.0 / v2.56.0 compared |
| Phase 2 sky | `sky/contact.png`, `sky/metrics.json` | noon / sunset / dusk / night, clouds off |
| UI | `preset_dev/ui/ui_properties.png`, `ui_sidebar.png`, `ui_compositor.png` | panels draw; no FX section |
| Package | `dist/anime_look_director-2.58.0.zip` | extension build PASS; 2.58.0 installed and enabled in an isolated config |

## Phase 1 definition of done

| Item | Status | Evidence |
|---|---|---|
| World applies without FX objects | DONE | `check_no_fx`, `check_render` |
| World applies without the compositor | DONE | palette applied with no stack assigned |
| No Spatial Clouds / smoke / FX pass | DONE | modules removed; source audit |
| No FX UI or operators in the path | DONE | panels/operators/source audit |
| Persistent identity and Sun protection | DONE | `identity.py`, `ownership.py`, gate |
| Snapshot restore | DONE | gate snapshot fixture |
| Legacy data is explicit and reversible | DONE | Disable/Remove operators, `MIGRATION_2_57.md` |
| Old files are not auto-cleaned | DONE | documented, source audit |
| Phase 0 visual baseline | DONE | `preset_dev/world_baseline/` |
| Phase 2 cloudless sky | DONE | broad accent, Sun fade, `preset_dev/sky/` |

## Deliberate limits

- The World clouds are still the current 2.56 shader; the three-family rebuild
  is Phase 3. The Phase 0 comparison shows the v1 clouds are more billowy and
  the current sky/cloud shading is flatter.
- FX/cloud settings are no longer registered; old data is ignored and has no
  UI, handlers or runtime effect.
- The optional compositor is kept for general art filters; it is not part of
  the sky and is not required.
- The old World fireworks/meteors are disabled. The new controlled shooting
  stars are Phase 4.
