# Anime Look Director — Recap

**Versione 0.3.1** · Blender 5.1.2 · GPL-3.0-or-later

## In breve

Anime Look Director è un add-on per Blender che costruisce un **look anime
atmosferico** in modo rapido e non distruttivo: palette di atmosfera, gradiente
del cielo, tint delle ombre sui materiali, luce di contorno e uno stack compositor
completo (bloom, Kuwahara, light wrap, distorsione lens).

Non salva mai il `.blend` dell'utente e non richiede dipendenze esterne.

## Cosa fa

1. **Palette atmosferiche** — quattro preset che governano world, sole, tint del
   glare e colore delle ombre.
2. **World gradient** — cielo, orizzonte e terreno separati, con offset e
   morbidezza dell'orizzonte.
3. **Auto Sun** — se la scena non ha una SUN, ne viene creata una (`ALD | Sun`)
   e tinta dalla palette.
4. **Shadow tint** — un node group reversibile mescola la Base Color dei materiali
   verso il colore d'ombra della palette nelle zone occluse (maschera AO).
5. **Stack compositor** — `Render Layers → Glare (Bloom) → Sun Beams (opzionale)
   → Kuwahara (mix per profondità) → Light Wrap → Lens Distortion → Output`.
6. **Light Wrap** — luce sfocata che rientra sui bordi delle silhouette, con
   maschera da profondità e discontinuità di profondità.
7. **God Rays** — glare Sun Beams ancorato alla posizione schermo del sole, con
   forza e dimensione regolabili; si aggiorna durante l'animazione.
8. **Shot markers** — marker timeline `ALD:<PALETTE>` per cambiare palette alle
   inquadrature; il pulsante `Mark Shot` crea/aggiorna il marker.
9. **Material presets** — Skin, Hair, Fabric, Metal, Emission applicabili agli
   oggetti selezionati.
10. **Viewport compositor** — un click per mostrare lo stack nel viewport 3D.
11. **Stack per scena** — ogni scena ha il proprio gruppo compositor, senza
    conflitti tra scene multiple.

## Flusso di lavoro

1. Seleziona il pannello **Scene Properties → Anime Look Director**.
2. Scegli una **Atmosphere** e premi **Apply Palette**.
3. Premi **Build / Update Stack** per creare o aggiornare il compositor.
4. Regola le sezioni **World & Shadows** e **Compositor Stack** (sono
   sotto-pannelli richiudibili).
5. Per un cambio palette su un taglio: scegli la palette, vai al frame, premi
   **Mark Shot** e attiva **Shot Markers**.
6. Per i materiali: seleziona gli oggetti, scegli un preset e premi **Apply**.
7. **Enable Viewport Compositor** per vedere il risultato nel viewport.

## Le palette

| Palette | Carattere |
| --- | --- |
| Shinkai Golden Hour | controluce caldo, alone arancione, cielo lavanda |
| Ghibli Summer Noon | luce alta e pulita, cielo azzurro, ombre fresche |
| Rainy Tokyo Night | notte piovosa, blu freddo, contrasto medio |
| Cyberpunk Neon | magenta/ciano, zenit blu-viola, ombre colorate |

## Impostazioni principali

- **World Gradient / Horizon / Horizon Softness**
- **Auto Sun** (creazione automatica della SUN)
- **Shadow Tint** + forza, distanza, numero materiali, `Clear Shadow Tint`
- **Halation** (Glare Bloom) e forza
- **Painterly (Kuwahara)** e dimensione
- **Chromatic dispersion**
- **Light Wrap** con forza e dimensione
- **God Rays** con forza e dimensione
- **Depth Near / Far** per il mix del Kuwahara
- **Material Preset** (Skin / Hair / Fabric / Metal / Emission)

## Cosa crea nel file

- `ALD | World Gradient` — gruppo shader del gradiente.
- `ALD | Shadow Tint` — gruppo shader del tint ombre.
- `ALD | Compositor Stack` — gruppo compositor (suffissato per le scene
  successive alla prima).
- `ALD | Sun` — luce creata da Auto Sun, taggata `ald_auto_sun`.
- `ALD | Skin`, `ALD | Hair`, `ALD | Fabric`, `ALD | Metal`, `ALD | Emission` —
  materiali preset con fake user.

Lo shadow tint è **reversibile**: `Clear Shadow Tint` ripristina il collegamento
o il colore originale della Base Color.

## Garanzie e limiti

- Nessun salvataggio automatico del `.blend`.
- Stack idempotente: rebuild non duplica gruppi o nodi.
- Shadow tint: tint dei contatti/occlusione (AO), non ricolora le ombre proiettate.
- Light Wrap: lavora sulle silhouette geometriche; oggetti trasparenti non
  generano il bordo.
- God Rays: durante l'animazione segue sole e camera a ogni frame; se muovi
  sole/camera **senza cambiare frame**, serve **Build / Update Stack**.
- Shot markers: override temporali, non per-camera.
- Material presets: materiali semplici (Principled), non shader toon completi.
- Rebuild dello stack: circa 5–8 ms sulla macchina di sviluppo.

## Verifica e sviluppo

Gate headless:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
```

Output atteso: `ALD GATE: PASS`.

Look-dev (quattro palette + contact sheet):

```powershell
& $blender -b --factory-startup --python preset_dev\lookdev.py -- --out "$env:TEMP\ald_lookdev"
```

Il gate copre: gradient, Auto Sun, God Rays (nodo, posizione proiettata,
mute/restore), shadow tint (inserimento/rimozione/ripristino), Light Wrap
(struttura e test a pixel), shot markers, material presets, idempotenza,
multi-scena, render EEVEE e coerenza versione `bl_info`/manifest.

## Versioni

- **0.1** — sketch: palette, stack Glare/Kuwahara/Lensdist, gate.
- **0.2** — world gradient, shadow tint, light wrap, gate a pixel, look-dev.
- **0.2.1** — Auto Sun, stack per scena, fix manifest.
- **0.3** — God Rays, shot markers, material presets, sotto-pannelli.
- **0.3.1** — God Rays refresh/size, preset Emission, questo recap.
