# Anime Look Director — Recap

**Versione 0.6.1** · Blender 5.1.2 · GPL-3.0-or-later

## In breve

Anime Look Director è un add-on per Blender che costruisce un **look anime
atmosferico** in modo rapido e non distruttivo: palette di atmosfera, gradiente
del cielo, tint delle ombre sui materiali, luce di contorno e uno stack compositor
completo (bloom, Kuwahara, light wrap, distorsione lens).

Non salva mai il `.blend` dell'utente e non richiede dipendenze esterne.

## Cosa fa

1. **Palette atmosferiche** — sei preset che governano world, sole, tint del
   glare e colore delle ombre.
2. **World gradient** — cielo, orizzonte e terreno separati, con offset e
   morbidezza dell'orizzonte.
3. **Auto Sun** — se la scena non ha una SUN, ne viene creata una (`ALD | Sun`)
   e tinta dalla palette.
4. **Sun disk** — disco solare nel cielo, allineato alla direzione reale del
   sole, con dimensione e intensità.
5. **Anime clouds** — nuvole procedurali a due layer di rumore, colorate con
   shadow/horizon/sun della palette, con quantità e scala.
6. **Custom palette colors** — override di cielo, orizzonte, sole e ombra per
   scena.
7. **Shadow tint** — node group reversibile e **moltiplicativo**: nelle zone in
   ombra tinge la Base Color con il colore della palette preservando il dettaglio
   delle texture.
8. **Cel terminator** — stacco direzionale `N·L` sincronizzato col sole, con
   Cel Shadow e Terminator Sharpness.
9. **Rim light direzionale** — Fresnel sul lato sole, colorato con `sun_color`;
   il preset HAIR riceve un boost “angel ring”.
10. **Rim emission** — il rim e una frazione dello shadow tint alimentano
    l’Emission Color del Principled, così il bordo resta visibile in controluce.
11. **Stack compositor** — `Render Layers → Glare (Bloom) → Sun Beams (opzionale)
    → Kuwahara (mix per profondità) → Light Wrap → Ink Lines (opzionale) → Lens
    Distortion → Output`.
12. **Light Wrap** — luce sfocata che rientra sui bordi delle silhouette.
13. **Anime Ink Lines** — contorni sottili da profondità, tinti con lo shadow tint,
    con gain dedicato ai bordi interni.
14. **God Rays** — glare Sun Beams ancorato alla posizione schermo del sole, con
    forza e dimensione regolabili; si aggiorna durante l’animazione.
15. **Shot markers** — marker timeline `ALD:<PALETTE>` per cambiare palette alle
    inquadrature; il pulsante `Mark Shot` crea/aggiorna il marker.
16. **Per-camera override** — ogni camera può avere la propria palette; cambiando
    camera il look si aggiorna. Precedenza: camera > marker > palette di scena.
17. **Material presets** — Skin, Hair, Fabric, Metal, Emission applicabili agli
    oggetti selezionati.
18. **Viewport compositor** — un click per mostrare lo stack nel viewport 3D.
19. **Stack per scena** — ogni scena ha il proprio gruppo compositor.
20. **Pannello Sidebar N** — `View3D > Anime Look` per palette, mondo, ombre e
    compositor senza staccare gli occhi dalla camera.

## Flusso di lavoro

1. Seleziona il pannello **Scene Properties → Anime Look Director** oppure la
   Sidebar N **View3D → Anime Look**.
2. Scegli una **Atmosphere** e premi **Apply Palette**.
3. Premi **Build / Update Stack** per creare o aggiornare il compositor.
4. Regola le sezioni **World & Shadows** e **Compositor Stack** (sono
   sotto-pannelli richiudibili): qui trovi Sun Disk, Anime Clouds, Ink Lines e
   **Custom Colors**.
5. Per un cambio palette su un taglio: scegli la palette, vai al frame, premi
   **Mark Shot** e attiva **Shot Markers**. Per un override per-camera: seleziona
   la camera, apri **Camera Override** e scegli la palette.
6. Per i materiali: seleziona gli oggetti, scegli un preset e premi **Apply**.
7. **Enable Viewport Compositor** per vedere il risultato nel viewport.

## Le palette

| Palette | Carattere |
| --- | --- |
| Shinkai Golden Hour | controluce caldo, alone arancione, cielo lavanda |
| Ghibli Summer Noon | luce alta e pulita, cielo azzurro, ombre fresche |
| Rainy Tokyo Night | notte piovosa, blu freddo, contrasto medio |
| Cyberpunk Neon | magenta/ciano, zenit blu-viola, ombre colorate |
| Sakura Spring | cielo azzurro, orizzonte rosa, luce calda e morbida |
| Twilight Dusk | cielo indaco, orizzonte arancio, sole basso |

## Impostazioni principali

- **World Gradient / Horizon / Horizon Softness**
- **Auto Sun** (creazione automatica della SUN)
- **Shadow Tint** + forza, distanza, numero materiali, `Clear Shadow Tint`
- **Cel Shading** + Cel Shadow e Terminator Sharpness
- **Rim Light** + forza, larghezza ed emissione
- **Camera Override** (palette specifica della camera attiva)
- **Halation** (Glare Bloom) e forza
- **Painterly (Kuwahara)** e dimensione
- **Chromatic dispersion**
- **Light Wrap** con forza e dimensione
- **God Rays** con forza e dimensione
- **Depth Near / Far** per il mix del Kuwahara
- **Material Preset** (Skin / Hair / Fabric / Metal / Emission)

## Cosa crea nel file

- `ALD | World Gradient` — gruppo shader del gradiente, con disco solare e nuvole.
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
- Shadow tint: tint moltiplicativo delle zone in ombra che preserva le texture;
  il cel terminator è un tint direzionale, non una vera rimappatura della luce.
  Resta un proxy di contatto/occlusione, non ricolora le ombre proiettate.
- Rim light: approssimazione Fresnel mascherata dal sole; non è un vero rim
  lighting fisico. L'angel ring HAIR è un boost del rim. L'emission rim viene
  saltata sui materiali che hanno già emission.
- Sun disk, God Rays e cel shading si aggiornano in tempo reale muovendo sole o
  camera; i Custom Colors aggiornano anche bloom, raggi e ink.
- Light Wrap: lavora sulle silhouette geometriche; oggetti trasparenti non
  generano il bordo.
- God Rays: durante l'animazione segue sole e camera a ogni frame; se muovi
  sole/camera **senza cambiare frame**, serve **Build / Update Stack**.
- Shot markers: override temporali, non per-camera; la palette base non viene
  sovrascritta. Gli override camera hanno precedenza sui marker.
- Camera override: vive sulla camera data, quindi è condiviso da camera linkate.
- Material presets: materiali semplici (Principled), non shader toon completi.
- Nuvole: procedurali stilizzate, non simulazione volumetrica; quantità e scala
  regolabili.
- Sun disk e nuvole seguono il sole a ogni frame; se muovi sole/camera senza
  cambiare frame, riapplica la palette o cambia frame.
- Custom Colors: override per scena, non salvati come nuovo preset nel file.
- Slider dei parametri: aggiornamento in-place (~0.34 ms); i toggle e la palette
  ricostruiscono lo stack (~5.3 ms).

## Verifica e sviluppo

Gate headless:

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $blender -b --factory-startup --python-exit-code 1 --python preset_dev\verify.py
```

Output atteso: `ALD GATE: PASS`.

Look-dev (sei palette + contact sheet 3×2):

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
- **0.3.1** — God Rays refresh/size, preset Emission, recap.
- **0.3.2** — slider in-place, shadow tint moltiplicativo, pannello Sidebar N.
- **0.4.0** — Sun Disk, Anime Clouds, Ink Lines, Sakura/Twilight, Custom Colors.
- **0.5.0** — Cel terminator, rim light direzionale, angel ring HAIR.
- **0.6.0** — override palette per-camera, coordinatore effective look.
- **0.6.1** — normalizzazione sun disk, update realtime, ink gain, rim emission.
