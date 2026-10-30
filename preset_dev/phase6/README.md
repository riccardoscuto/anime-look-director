# Phase 6 - release matrix

Evidence for the World Sky Edition release. All renders use EEVEE at
640x360, 32 samples, AgX, no compositor and the same camera and Sun energy;
only the documented control changes between cells.

- `contact.png` - 22 cells, 4 columns, read left to right, top to bottom.
- `metrics.json` - file order, labels, control values and luminance.
- `technical.json` - the 17-check technical gate.

## Matrix order

| # | Cell | Change |
|---|---|---|
| 1-9 | `family_*` | Cumulus, Stratocumulus, Cirrus x Sun front / side / back at noon |
| 10-12 | `palette_*` | SUMMER_NOON, GOLDEN_HOUR, NEON_NIGHT with the approved Cumulus |
| 13-16 | `coverage_*` | Cloud Amount 0.00, 0.25, 0.50, 1.00 |
| 17-18 | `camera_*` | Horizon and elevated camera, same sky |
| 19-20 | `wind_*` | Cloud Wind 1.0 at frames 1 and 12 |
| 21-22 | `stars_*` | Two shooting-star events at frames 8 and 16, clouds off |

`front` means the Sun is in the camera view (azimuth 180 for this camera);
`side` is azimuth 90 and `back` is azimuth 0. The shooting stars use the same
gnomonic coordinates as the Sky panel and are inside the camera frame.

## Technical gate

`phase6_technical.py` reports **17/17 PASS**:

- apply is idempotent and its render is byte-identical;
- a second scene generates the same World values and the same render;
- wind advances the cloud field and returns deterministically to frame 1;
- disabling one shooting star leaves the other slot intact and changes the
  render; re-enabling restores the exact slot;
- a plain scene copy shares identity and World, repair gives both a new
  identity and a new World, and the original sky is untouched;
- the World has four fixed star slots, no FX objects or legacy collections;
- apply costs 1.3 ms and a 320x180 render 172 ms on this machine;
- two events and the gradient group survive save/reload.

## Reading the matrix

- The three families are distinguishable at the same coverage: Cumulus is
  compact and tall, Stratocumulus is a flat deck, Cirrus is stretched and thin.
- The Sun direction changes the cloud lighting; the front cell includes the
  disk, so use the side/back pair to compare shading rather than mean
  luminance.
- Cirrus wisps partially occlude the disk, which is expected for that family
  and is not a broken disk.
- Coverage 0.00 still shows the flat ground color; that band is the World
  ground, not a cloud.
- Stratocumulus and Cirrus are documented here but have no individual
  aesthetic sign-off. **Closed on 2026-10-30 as accepted documented limits**:
  no further aesthetic work on these families is planned for the 2.63 line.
  Cumulus remains the approved family.

## Commands

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_matrix.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_technical.py
```
