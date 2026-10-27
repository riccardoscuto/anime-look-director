# Legacy emission isolation — expected failure

`metrics.json` in this folder is the **historical** measurement of the retired
path: the FX contribution was taken from the main `Emission` pass, so a bright
foreign emitter behind the burst leaked into the FX at partially covered
pixels. The script still exits 1 on this folder by design; the FAIL is the
evidence of why the external pass exists.

Do not use this folder as the current isolation verdict. The current path is
covered by the gate:

- `check_fx_pass_isolation` — an emitter behind the burst cannot enter the
  external pass;
- `check_fx_pass_atomic` — a failed EXR write leaves the valid pass intact;
- `check_fx_pass_strict` — a missing pass can hide the FX instead of the
  contaminated fallback;
- `check_fx_render_orchestration` — the shot and animation render the pass and
  the composite;
- `preset_dev/P0_CLOSURE_2_42.md` — the closure report.

The legacy FAIL is deliberately kept: deleting it would erase the measured
defect.
