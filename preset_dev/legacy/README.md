# Legacy ALD safety (Phase 0, 2.63 work)

This is the Phase 0 fix for the Legacy ALD Data panel. It is based on 2.62.0
and does not change the World shader, the clouds, the presets or the
compositor.

## Historical tags

| Data | Collection tags | Object/data tags |
|---|---|---|
| FX | `ald_fx_collection`, `ald_fx_owner` | `ald_fx`, `ald_fx_anchor`, `ald_fx_ground` |
| Spatial Clouds | `ald_clouds`, `ald_fx_owner` | `ald_clouds`, `ald_cloud_uid` |
| Smoke | `ald_smoke`, `ald_fx_owner` | `ald_smoke` |

The v2.5.0 FX collection had only `ald_fx_owner`; that owner tag is accepted as
legacy. Names are never used to identify data, so a user collection called
`ALD | FX` or `ALD | Smoke` is untouched.

## Behaviour

**Disable** finds tagged collections linked to the active scene at any depth.
It excludes them in every view layer of that scene only and stores the previous
`exclude`/`hide_viewport` values in `scene["ald_legacy_disable_state"]`.
Collections shared with another scene are excluded only in the active scene.
The operator is idempotent and can be extended after new legacy data appears.

**Restore** reads the stored state, restores the exact per-view-layer values
and clears the state. It is a separate operator (`ald.legacy_restore`) and is
disabled when there is no saved state.

**Remove** computes a conservative plan first and shows it in a confirmation
dialog with a `Remove permanently` checkbox:

- tagged collections with only tagged objects and tagged children are removed;
- nested collections are removed leaf-first;
- shared collections, objects linked to another scene, objects linked to a
  user collection, and parents with non-legacy children are skipped and
  reported;
- standalone tagged anchor/ground objects are removed only when they are
  scene-local and not inside a blocked legacy collection;
- data blocks left with zero users are removed.

Empty confirmation, direct calls without `confirm=True`, and plans with only
skipped elements do nothing.

## Tests

`preset_dev/legacy_fixture.py` - **36/36 PASS**:

| Scenario | Checks |
|---|---|
| Clean file | no legacy data, Disable no-op, no state |
| v2.56-style tags | three collections/objects found, hide, restore, remove |
| Two independent scenes | only the active scene is hidden/removed |
| Shared collection | hidden only in the active scene, Remove refuses it |
| Nested legacy collections | both found, hidden, removed |
| Parent with user child | parent kept, user data kept |
| Similar user names | untouched |
| v2.5.0 owner-only FX | detected and removed |
| Object shared with user collection | kept |
| Standalone anchor/ground | planned and removed, user collection kept |
| Two view layers | both hidden and restored |

`preset_dev/legacy_v256_check.py` - **9/9 PASS** on
`preset_dev/legacy/v256_fixture.blend`, a real file created by the v2.56.0
add-on from tag `v2.56.0` (FX, Spatial Clouds, smoke, anchor and ground). It
also checks that a user collection with an ALD-like name survives.

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\legacy_fixture.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\legacy_v256_check.py
```

## Files

- `legacy.py` - discovery, per-scene disable/restore, conservative remove plan.
- `operators.py` - `ald.legacy_disable`, `ald.legacy_restore`,
  `ald.legacy_remove` with the confirmation dialog.
- `panels.py` - Disable/Restore buttons and the tagged-collection count.
- `preset_dev/legacy_fixture.py`, `preset_dev/legacy_v256_check.py`,
  `preset_dev/legacy/` - tests and evidence.

## Limits

- Disable only hides collections. Standalone anchor/ground helpers are not
  hidden because object render visibility is not per scene; they are handled
  by Remove.
- Remove never deletes a collection or object shared with another scene; it
  reports it instead.
- The v2.56.0 `.blend` fixture is test data, not a user project. The checks
  never save it.
