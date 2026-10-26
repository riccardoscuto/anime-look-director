# P0 baseline — evidence and expected failures

This file records the state the operational plan (`Anime_Look_Director_Audit_Piano_v2.27.0`)
calls the **baseline** (P0-A), and the defects the P0 phases had to remove. The
machine-readable record is `preset_dev/baseline.json`, written by:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\baseline.py
```

The gate that must stay green:

```powershell
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
# expected: ALD GATE: PASS
```

## Baseline record

`baseline.json` contains:

- `version` / `version_text`: the declared `bl_info` version;
- `hashes`: SHA-256 of every Python file of the add-on (the exact code the
  record refers to);
- `schemas`: `FX_SCHEMA`, `fx_nodes.SCHEMA` and the `ald_schema` marker of the
  burst and trail node groups, plus the FX collection name;
- `flows`: the record/geometry counts of the public flows `create`, `update`,
  `duplicate`, `remove`.

Reference values at the time of writing (v2.27.2 + P0):

| flow | records | objects | invariant |
| --- | --- | --- | --- |
| create | 1 | 14 | the record and its geometry exist |
| update | 1 | 14 | `uid_kept = true`: no duplicate, no identity change |
| duplicate | 2 | 14 | the copy has a new UID **and** its own geometry |
| remove | 1 | 0 for the removed UID | the record and the geometry go together |

## Expected failures before the fix

These are the failures the P0 tests were written against. They are listed here
because the fixes are already applied: the tests now assert the fixed
behaviour, and this note keeps the original failure signature auditable.

### N01 — occlusion leak (P0-D)

- Symptom: a particle behind an opaque wall was still added on top of the wall.
  The FX-only layer excluded the environment, so F had no depth against it.
- Old test: `check_fx_occlusion` only verified that the wall pixel was red; it
  also passed when the FX leaked through the wall, and it was never called by
  `main()`.
- Expected after the fix: behind the wall the image with FX and without FX is
  identical (`behind ≈ 0`), while without the wall the two images differ
  (`free > 0`). The gate prints:
  `ALD GATE occlusion: behind=0.000000 free=0.004795`.

### N02 — zero FX is not the identity (P0-D)

- Symptom: with no FX systems the recomposition changed the image (the FX layer
  contributed the world or other emissive surfaces).
- Expected after the fix: rendering with `fx_backend = "OFF"` and with
  `"FX3D"` on a scene with zero FX must produce the same pixels
  (`check_fx_identity`).

### Update FX used the legacy path (P0-B)

- Symptom: `ald.fx_update` read `ald_fx_config` and called `create_fireworks` /
  `create_meteors`, which created a **new** system: records 2 instead of 1 and
  a new UID.
- Expected after the fix: the selected system is rebuilt through
  `fx.update_system`; records stay 1, UID unchanged, geometry rebuilt from the
  persistent events (launcher positions re-read).

### Remove System left the geometry (P0-B)

- Symptom: the operator removed only the `PropertyGroup`; the objects stayed in
  the scene and the registry still referenced them.
- Expected after the fix: `fx.remove_system` removes objects, runtime state and
  record in one operation (`objects_of_removed = 0`).

### Duplicate System created only a record (P0-B)

- Symptom: the copy existed in the panel but had no geometry
  (`objects = 0`).
- Expected after the fix: the copy is compiled immediately
  (`objects = 14`, `uid_changed = true`).

### No backup when the palette was never applied (P0-C)

- Symptom: creating FX (or building the stack) modified the scene without a
  snapshot; Remove ALD from Scene could not restore the user's world,
  materials or compositor.
- Expected after the fix: `snapshot.ensure` runs before every first mutation
  (`compositor.build`, `fx.create_*`, `fx.compile_system`, `fx.apply_backend`),
  and the gate checks the snapshot exists and holds the user's world.

### Automatic re-entry after removal (P0-C)

- Symptom: after Remove ALD from Scene the frame/camera handlers could apply
  the look again on the next change.
- Expected after the fix: `snapshot.restore` sets `scene["ald_removed"] = True`;
  `snapshot.is_inactive` blocks every handler until an explicit Apply/Build
  takes a new snapshot. The Scene panel reports `Removed`.

### Detach discarded the look (P0-C)

- Symptom: Detach and Keep Result called `materials.clear_scene`, which removed
  the shadow-tint wiring and restored the original base colours — the opposite
  of keeping the result.
- Expected after the fix: Detach removes only the live FX, the markers and the
  internal properties; the materials, world, sun and compositor stay.

### Read-only diagnostic wrote and claimed OK (P0-E)

- Symptom: the panel called `event_state`, which evaluated the depsgraph
  (`realized_centers`) during `draw()`, and returned `OK` without proving the
  projection.
- Expected after the fix: `event_state` is read-only and ends in `UNKNOWN`;
  only the explicit `ald.fx_diagnose` operator evaluates the position and may
  return `OK`. The panel displays the cached report.

## How to re-check the baseline

1. Run `preset_dev/baseline.py` and compare `baseline.json` with the committed
   record (hashes change on every edit; the flows must keep the invariants in
   the table).
2. Run `preset_dev/verify.py`: the gate must print `ALD GATE: PASS` and the
   occlusion line above.
3. For the render evidence, the gate writes `ald_gate_occ_*.png`,
   `ald_gate_identity_*.png` and `ald_gate_fx_occlusion.png` under the system
   temporary directory.
