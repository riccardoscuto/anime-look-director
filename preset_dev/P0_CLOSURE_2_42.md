# P0 closure — external FX pass (v2.42.0)

## Cause

`F` was the main scene `Emission` pass multiplied by a binary presence mask.
The Emission pass contains every emissive surface; at partially covered pixels
the foreign emitter entered F. The Shader AOV is empty in EEVEE and Cycles in
this environment, and a view layer read by the compositor node group proved
unreliable (the Render Layers node does not re-resolve a recreated layer).

## Fix

A dedicated **external FX pass**:

1. `compositor.render_fx_pass(scene)` creates a temporary view layer that
   contains only the `ALD | FX` collection, renders its **Emission** pass to an
   EXR, removes the layer and stores the path on `Scene.ald.fx_pass_path`.
2. The stack reads that EXR through an `Image` node (`ALD | FX Pass`), so F
   contains only the FX, with the FX coverage and HDR values, and no foreign
   emitter can enter it.
3. The punch and the occlusion still use the main Cryptomatte matte.
4. The panel exposes **Render FX Pass**. The pass is a two-step workflow: render
   it after changing the FX, the camera or the frame; then render the shot.
   For animations the pass must be re-rendered per frame.
5. When the pass file is missing, the stack falls back to the main Emission
   (legacy path, known contamination at the edges). The panel shows whether a
   pass is ready.

## Verification

`check_fx_pass_isolation` (gate):

- a burst and a very bright foreign emitter (40/20/4 x 3) in a child
  collection, behind the burst;
- the FX pass is rendered with and without the emitter at 160x90;
- the two EXRs differ by **max 0.0000 / mean 0.00000** (checked);
- the stack reads the pass image (`ALD | FX Pass` node, matching file).

The pass excludes the foreign emitter because the temporary view layer is
created after the collections exist and excludes every child except the FX
collection. The earlier failures came from the layer collection tree not being
built (missing `view_layer.update()`) and from the path search; the direct
child exclusion fixes both.

## Honest limits

- The pass is **not automatic**: the user must render it after changes. The
  fallback keeps older files working but retains the edge leak.
- Motion blur and animation need one pass per frame; the pass is a still
  render of the current frame.
- The view layer is temporary; the stack does not read it at render time, so
  the node-resolution problem cannot affect it.

## Gate status

- STRUCTURAL: audit (updated).
- RUNTIME: `ALD GATE: PASS`, including the isolation test.
- VISUAL/INTEGRATION: the pass is isolated numerically; the composite at
  partially covered pixels still shows the background in the uncovered
  fraction, as correct compositing requires.
