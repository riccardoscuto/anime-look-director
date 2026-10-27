# Anime Look Director — validation report

Current release: **2.55.1** (Blender 5.1.2, Windows 11). This report maps the
checks to the categories the operational plan requires: structural, Blender
runtime, FX isolation, scene/lifecycle, visual and performance.

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
& $blender -b --factory-startup --python preset_dev\verify_all.py
& $blender -b --factory-startup --python preset_dev\build_release.py
```

`verify_all` runs the gate, the duplicate fixture and the audit in fresh
factory-startup processes and exits 1 on any failure.

## Latest results

| Category | Command / evidence | Result |
|---|---|---|
| Structural / runtime / visual | `verify.py` | **ALD GATE: PASS** |
| FX isolation | `check_fx_pass_isolation`, `check_fx_pass_atomic`, `check_fx_pass_strict`, `check_fx_render_orchestration` | PASS |
| Scene / lifecycle | `duplicate_fixture.py` (shared start, repair, remove, save/reload) | **DUP FIXTURE: PASS** |
| Plan / coverage | `audit_plan.py` | **125/125** |
| Whole chain | `verify_all.py` | **ALD ALL: PASS** |
| Visual matrix | `preset_dev/validation/metrics.json` | **36/36 PASS**, mean 1.44 s |
| Composition | `preset_dev/composition/composition.json` | all events `in_frame`, hero 0.5/0.5, fractions 0.954–1.0 |
| Clouds | `preset_dev/clouds_bench/metrics.json` | 3 runs, medians: creation 0.10–1.46 s, refresh 1.7–6.6 ms, render 2.15–3.64 s at 720p |
| Showcase | `preset_dev/showcase/` | 1920x1080 dusk 3-burst and night 5-burst |
| Package | `dist/anime_look_director-2.55.1.zip` | extension build PASS; 2.55.1 package installed and enabled in an isolated config |

## Plan Definition of Done

| Item | Status | Evidence |
|---|---|---|
| EXR per scene/shot/frame recognised and invalidated | DONE | scene UUID + per-scene path/image + frame range + signature; `fx_pass_state` |
| Missing/stale external references never accepted silently | DONE for UI FX | READY/STALE/MISSING state; `Require FX Pass`; `ALD | FX Strict Black` |
| Animation operator produces coherent pass + composite | DONE | `ald.fx_render_animation`; two-frame gate test |
| Pass operations restore every altered setting | DONE | group, format, color mode, filepath, `use_compositing`; atomic `os.replace` |
| Duplicated scenes edit/remove independently | DONE | `ownership.repair`, world/sun copy, fixture + save/reload |
| Mutable materials do not alter other scenes | DONE | per-scene key + `ald_fx_owner`; old ownerless migration |
| No auto show claimed as fit with cut bursts | DONE | solver reach, 0.95 fit, `Intentional Crop`, 0.95 gate |
| Cloud renders have deliberate edges | DONE | marching squares + `ald_edge` rim |
| World/Spatial overlap governable | PARTIAL | global `World Cloud Blend`; no regional mask |
| Local flash with simultaneous/PHYSICAL events | DONE | `fx.light_events`, two sources, `cloud_flash` |
| Benchmark comparable with 2.39 | NOT REPRODUCIBLE | 2.39 code is not in the repository; hardware/medians recorded |
| Gate categories recorded separately | DONE (report) | this report + `verify_all` labels; the gate checks are not individually tagged |
| PA2 volume research GO/NO-GO | NO-GO | `preset_dev/PA2_VOLUME_SPIKE.md`; cards stay default |

## Deliberate limits

- **Direct Python API**: `fx.create_fireworks` and `create_meteors` do not set
  `fx_pass_required`; the UI operators do. Scripts and fixtures keep the
  fallback for compatibility.
- **2.39 comparison**: impossible without the old source; the benchmark file
  records the machine and the medians.
- **World/Spatial regional masking**: the global blend is the current control.
- **Card billboards**: smooth contour and rim, but they remain vertical cards;
  a free viewport view still shows their plane.
- **Legacy emission isolation**: `preset_dev/emission_isolation/metrics.json`
  is the historical FAIL of the retired path; see the README in that folder.
- **Animation cost**: the final operators render the pass and the composite,
  two renders per frame.

## Reproducibility notes

- The validation matrix was generated at 1280x720 with seed 17, AgX, exposure 0.
- The cloud benchmark records three runs per scenario, the medians and the
  platform; the GPU name is unavailable in background mode.
- The UI screenshots in `preset_dev/ui/` are from a fresh Blender 5.1.2 window.
- No `.blend` of the user is saved by the tests; fixtures use the temporary
  directory.
