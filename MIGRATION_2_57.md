# Migration to the World Sky Edition (v2.57.0)

The v2.57.0 add-on keeps the World, Sun, clouds, stars, palette, material and
optional-compositor tools. The following systems are **not loaded and not
updated** any more:

- 3D fireworks, meteors and their Geometry Nodes;
- procedural World fireworks and World meteors (their amounts are forced to 0);
- Spatial Clouds 2.5D;
- atmospheric smoke volumes;
- the FX EXR pass, Cryptomatte isolation, FX cache and diagnostics.

## Old .blend files

Nothing is deleted or cleaned automatically when a file is opened. The old
`Scene.ald` FX/cloud properties are no longer registered: they are ignored
and have no UI, handlers or effect.

### 1. Disable (reversible)

`Scene Properties > Anime Look Director > Legacy ALD Data > Disable`
hides the collections tagged `ald_fx`, `ald_clouds` and `ald_smoke`. The objects
stay in the file and can be re-enabled in the Outliner.

### 2. Remove (explicit)

`Legacy ALD Data > Remove` deletes those collections and their objects. This is
not reversible from the panel; save a copy first or use `File > Revert`.

The old compositor stack may still contain FX nodes. `Remove Stack` deletes the
ALD compositor group; `Build / Update Stack` creates the new World-only stack.
Old pass images in the temporary directory are not referenced by the new
version.

## Rollback

The complete 2.56.0 implementation is preserved at
`archive/v2.56.0-full` and `v2.56.0`. Check out that tag to recover the FX,
Spatial Clouds, smoke and EXR-pass workflows.

## Compatibility limits

- Old FX animation, particle data and passes are not evaluated.
- Old World fireworks/meteors are not exposed; the controlled shooting-star
  system will be introduced in a later phase.
- A file saved by v2.57.0 no longer carries the old FX/cloud settings: they
  are not registered by this version.
