# Anime Look Director - Recap

**Versione 2.62.0 - Blender 5.1.2 - GPL-3.0-or-later**

## In breve

Anime Look Director costruisce **cieli anime procedurali** nel World shader:
quattro zone di cielo, Sole, nuvole World, stelle, Milky Way e shooting stars.
Il compositor e i materiali stilizzati sono opzionali.

La versione 2.57.0 ha rimosso FX 3D, Spatial Clouds, smoke e pass EXR. Il
progetto completo 2.56.0 resta nel tag `archive/v2.56.0-full`.

## Cosa fa

1. **Dodici palette atmosferiche** per World e Sole, con Apply immediato.
2. **Cielo a quattro zone**: Ground, Horizon, Mid Sky, Zenith, con Horizon
   Offset e Softness.
3. **Sole**: disco, dimensione, glow, Sun Beams, elevazione/azimut,
   Stage Backlight. Il disco scompare sotto l'orizzonte e il glow sfuma.
4. **Nuvole World**: tre famiglie (Cumulus, Stratocumulus, Cirrus), quantita,
   scala, verticalita, flatness, breakup, detail, seed, vento, contrails,
   delta gain, rim boost e colori Cloud Shadow/Mid/Light.
5. **Stelle e Milky Way**, con densita e intensita.
6. **Override camera** e **marker shot** per cambiare palette nella timeline.
7. **Materiali**: Shadow Tint, Cel, Rim e preset, reversibili.
8. **Compositor opzionale**: halation, Kuwahara, light wrap, dispersione,
   Sun Beams, ink, aerial haze. Non serve per applicare il cielo.
9. **Shooting stars controllate**: fino a 4 eventi persistenti; Add le mette
   nella vista corrente, Preview mira la camera e il campo si aggiorna subito.
10. **UI compatta**: Quick Look + Advanced Sky, sezioni complete nelle Scene
    properties.
11. **Legacy ALD Data**: Disable/Remove espliciti per i vecchi oggetti FX,
    nuvole spaziali e smoke. Nessuna pulizia automatica dei `.blend`.

## Fasi

- **Fase 0**: confronto World v1.0.3 / v1.1.0 / v2.56.0 in
  `preset_dev/world_baseline/`.
- **Fase 1**: riduzione a World Sky Edition, rimozione dei sistemi FX e delle
  loro UI. Gate, fixture e audit dedicati.
- **Fase 2**: cielo senza nuvole, banda Sky Accent a 0.20 e disco solare spento
  sotto l'orizzonte. Evidenza in `preset_dev/sky/`.
- **Fase 3**: tre famiglie World; gate Cumulus diurno e tramonto approvati.
- **Fase 4**: shooting stars controllate, Preview e aggiornamento immediato.
- **Fase 5**: cinque nuovi preset, Quick Look + Advanced Sky, compositor
  esplicito e Reset/Save as Custom.
- **Fase 6**: matrice finale di 22 celle, gate tecnico 17/17, pacchetto e merge
  su `master`.

## Verifica

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python preset_dev\verify.py
& $blender -b --factory-startup --python preset_dev\verify_all.py
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\phase6_technical.py
```

Risultati attuali: `ALD GATE: PASS`, `WORLD FIXTURE: PASS`,
`ALD WORLD AUDIT 40/40`, `ALD ALL: PASS`, `ALD PHASE6 TECHNICAL 17/17 PASS`.

## Limiti dichiarati

- Stratocumulus e Cirrus sono documentate nella matrice di rilascio ma non
  hanno un'approvazione estetica individuale; Cumulus resta la famiglia
  approvata.
- I vecchi dati FX non vengono valutati ne rimossi automaticamente.
- Il rollback completo e il tag `archive/v2.56.0-full`.
