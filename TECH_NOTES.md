# Technical notes — Blender 5.1.2 spikes (2026-10-19)

Empirical results from live runtime tests. Target machine: Windows, Blender 5.1.2,
Python 3.13.9, NumPy 2.3.4, no SciPy/OpenCV inside Blender.

## Compositor
- `scene.compositing_node_group` exists and is assignable; `scene.node_tree` is `None`.
- `CompositorNodeComposite` does not exist; the output is `NodeGroupOutput` with an
  interface socket (`ng.interface.new_socket(..., in_out="OUTPUT", socket_type="NodeSocketColor")`).
- Glare node: properties are **inputs**. `Type` accepts `Bloom`, `Streaks`, `Fog Glow`,
  `Sun Beams`. Also available: `Threshold`, `Strength`, `Size`, `Saturation`, `Tint`,
  `Sun Position`, `Streaks`, `Iterations`, etc.
- `CompositorNodeKuwahara` exists: `Type` = `Classic` / `Anisotropic`, `Size`
  (default 6), `Uniformity`, `Sharpness`, `Eccentricity`, `High Precision`.
- `CompositorNodeLensdist` exists (`Distortion`, `Dispersion`, `Fit`).
- Render Layers outputs: `Image`, `Alpha` and — when passes are enabled —
  `Depth`, `Mist`. `view_layer.use_pass_z` / `use_pass_mist` are available.
- Generic `ShaderNodeMix`, `ShaderNodeMath`, `ShaderNodeMapRange` can be created in
  a compositor tree. `ShaderNodeSeparateColor` cannot; use `CompositorNodeSeparateColor`.
- Minimal 64×64 EEVEE render through a compositor group completed successfully.
- Viewport compositor: `View3DShading.use_compositor` enum = `DISABLED`, `CAMERA`, `ALWAYS`.

## Drivers
- Simple expressions (`1+2`, `frame/10`) work even with
  `preferences.filepaths.use_scripts_auto_execute = False`.
- Drivers on node sockets work: ShaderNodeValue output `default_value`, vector
  component (`Mapping.Location` index 0), Node Group input socket.
- `TRANSFORMS` driver variables: `LOCAL_SPACE` returned **0.0** for an Empty's
  rotation; `WORLD_SPACE` returned the correct value (1.0). Use `WORLD_SPACE`.
- `Texture Coordinate` node's `object` can target a control Empty.

## NumPy / images
- Chamfer distance transform in NumPy: 2048×2048 mask in **0.117 s** (3 sweeps).
- Image write via `image.pixels.foreach_set`: 1024×1024 RGBA in **0.003 s**;
  `image.pack()` works.

## Multi-channel painting
- Four images + packing work. `bpy.ops.paint.image_paint.poll()` is False without
  an active paint context, so brush UX must be tested in a GUI session.
- `ImagePaint` exposes `brush`, `canvas` in 5.1.

## Known environment noise
- `physical-starlight-atmosphere` render handlers raise when `scene.world` is None.
- `flip_fluids_addon` raises on file load in this profile (unrelated to this addon).
