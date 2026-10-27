# Anime Look Director — Recap

**Versione 2.58.0 — Blender 5.1.2 — GPL-3.0-or-later**

## In breve

Anime Look Director costruisce **cieli anime procedurali** nel World shader:
quattro zone di cielo, Sole, nuvole World, stelle e Milky Way. Il compositor e
i materiali stilizzati sono opzionali.

La versione 2.57.0 ha rimosso FX 3D, Spatial Clouds, smoke e pass EXR. Il
progetto completo 2.56.0 resta nel tag `archive/v2.56.0-full`.

## Cosa fa

1. **Sette palette atmosferiche** per World e Sole, con Apply immediato.
2. **Cielo a quattro zone**: Ground, Horizon, Mid Sky, Zenith, con Horizon
   Offset e Softness.
3. **Sole**: disco, dimensione, glow, Sun Beams, elevazione/azimut,
   Stage Backlight. Il disco scompare sotto l'orizzonte e il glow sfuma.
4. **Nuvole World**: quantità, scala, flatness, vento, contrails, delta gain,
   rim boost, colori Cloud Shadow/Mid/Light.
5. **Stelle e Milky Way**, con densità e intensità.
6. **Override camera** e **marker shot** per cambiare palette nella timeline.
7. **Materiali**: Shadow Tint, Cel, Rim e preset, reversibili.
8. **Compositor opzionale**: halation, Kuwahara, light wrap, dispersione,
   Sun Beams, ink, aerial haze. Non serve per applicare il cielo.
9. **Legacy ALD Data**: Disable/Remove espliciti per i vecchi oggetti FX,
   nuvole spaziali e smoke. Nessuna pulizia automatica dei `.blend`.

## Fasi

- **Fase 0**: confronto World v1.0.3 / v1.1.0 / v2.56.0 in
  `preset_dev/world_baseline/`. Le nuvole v1 sono più voluminose; la base
  tecnica v2 è più controllabile.
- **Fase 1**: riduzione a World Sky Edition, rimozione dei sistemi FX e delle
  loro UI. Gate, fixture e audit dedicati.
- **Fase 2**: cielo senza nuvole. Banda Sky Accent allargata a 0.20 e disco
  solare spento sotto l'orizzonte. Evidenza in `preset_dev/sky/`.

## Verifica

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\verify.py
& $blender -b --factory-startup --python preset_dev\verify_all.py
```

Risultati attuali: `ALD GATE: PASS`, `WORLD FIXTURE: PASS`,
`ALD WORLD AUDIT 23/23`, `ALD ALL: PASS`.

## Limiti dichiarati

- Le nuvole sono ancora il generatore World 2.56; le tre famiglie
  Cumulus/Stratocumulus/Cirrus sono la Fase 3.
- I vecchi dati FX non vengono valutati né rimossi automaticamente.
- Il rollback completo è il tag `archive/v2.56.0-full`.
