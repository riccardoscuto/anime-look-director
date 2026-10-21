# Anime Look Director — Recap

**Versione 2.8.0** · Blender 5.1.2 · GPL-3.0-or-later

## In breve

Anime Look Director è un add-on per Blender che costruisce un **look anime
atmosferico** in modo rapido e non distruttivo: palette di atmosfera, gradiente
del cielo, tint delle ombre sui materiali, luce di contorno e uno stack compositor
completo (bloom, Kuwahara, light wrap, distorsione lens).

Non salva mai il `.blend` dell'utente e non richiede dipendenze esterne.

## Cosa fa

1. **Palette atmosferiche** — sette preset che governano world, sole, tint del
   glare e colore delle ombre, inclusa **After School Sunset**.
2. **World gradient** — cielo a 4 zone: terreno, orizzonte, mid-sky bridge e
   zenit, con offset e morbidezza dell'orizzonte. Il bridge evita la fascia
   grigia nei cieli al tramonto.
3. **Auto Sun** — se la scena non ha una SUN, ne viene creata una (`ALD | Sun`)
   e tinta dalla palette, con rotazione solare dedicata. Gli slider **Sun
   Elevation / Sun Azimuth** muovono il sole; **Stage Backlight** lo mette davanti
   alla camera e accende disco, god rays, light wrap e rim.
4. **Sun disk** — disco solare nel cielo, allineato alla direzione reale del
   sole, con dimensione e intensità.
5. **Anime clouds** — proiezione planare prospettica su un deck orizzontale, con
   fasce stratificate verso l’orizzonte. Il core denso è una silhouette
   viola/malva, il bordo sottile prende la **silver lining** dorata/rosata;
   quantità, scala e **Cloud Wind** animato dal frame.
   - **Micro starfield** — stelle Voronoi con magnitudine variabile e culling
     noise, nascoste da nuvole e disco solare, con Star Amount e Star Density;
     Golden Hour, After School, Neon Night e Twilight Dusk le attivano.
6. **Visible sky / ambient split** — la forza del world regola la luce ambientale,
   mentre il cielo visto dalla camera resta vivido.
7. **Custom palette colors** - override di cielo, orizzonte, sole, ombra e
   nuvole per scena; cambiando preset con override attivo i colori si
   riallineano al nuovo preset.
8. **Shadow tint** — node group reversibile e **moltiplicativo**, con **Hue Lift**
   additivo: le texture restano leggibili e anche i materiali caldi prendono la
   velatura blu/viola delle ombre.
9. **Cel terminator** — stacco direzionale `N·L` sincronizzato col sole, con
   Cel Shadow e Terminator Sharpness. **Terminator Warmth** aggiunge la banda
   calda subsuperficie attorno a `N·L = 0` (boost sul preset Skin).
10. **Rim light** — Fresnel con tre modalità: **Sun Side**, **360° Contour** e
    **Backlight**; colore dal sole, boost “angel ring” sul preset HAIR.
11. **Rim emission** — il rim e una frazione dello shadow tint alimentano
    l’Emission Color del Principled, così il bordo resta visibile in controluce.
12. **Stack compositor** — `Render Layers → Glare (Bloom) → Sun Beams (opzionale)
    → Kuwahara (mix per profondità) → Light Wrap → Aerial Haze (opzionale) → Ink
    Lines (opzionale) → Lens Distortion → Output`.
13. **Light Wrap** — luce sfocata che rientra sui bordi delle silhouette.
14. **Anime Ink Lines** — contorni sottili da profondità **e pass Normal** (pieghe
    e spigoli interni), tinti con lo shadow tint, con gain dedicato ai bordi.
15. **God Rays** — glare Sun Beams ancorato alla posizione schermo del sole, con
    forza e dimensione regolabili; si aggiorna durante l’animazione.
16. **Shot markers** — marker timeline `ALD:<PALETTE>` per cambiare palette alle
    inquadrature; il pulsante `Mark Shot` crea/aggiorna il marker.
17. **Per-camera override** — ogni camera può avere la propria palette; cambiando
    camera il look si aggiorna. Precedenza: camera > marker > palette di scena.
18. **Material presets** — Skin, Hair, Fabric, Metal, Emission applicabili agli
    oggetti selezionati. **Exclude Material** esclude il materiale attivo dal
    sync globale senza modificare lo shader.
19. **Viewport compositor** — un click per mostrare lo stack nel viewport 3D.
20. **Stack per scena** — ogni scena ha il proprio gruppo compositor.
21. **Pannello Sidebar N** — `View3D > Anime Look` per palette, mondo, ombre e
    compositor senza staccare gli occhi dalla camera.

## Novità 0.9.0

- **After School Sunset**: orizzonte pesca-oro, cielo rosa salmone/malva e zenit
  indaco-lavanda, con nuvole in silhouette viola e bordi dorati.
- **Sun Glow Mie**: corona stretta `gamma+^16 * 0.65` + lobo largo
  `gamma+^3.5 * orizzonte * 0.45`, sommati, tinti dal sole e controllati da
  `Sun Glow`.
- **Proiezione su guscio curvo** esatta: `p=(Vx*t, Vy*t, Vz)` con
  `t=0.55/(max(Z,0.015)+0.18)`; **Cloud Flatness** fonde sfera grezza e guscio
  planare (0 = cumuli, 1 = bande). Ogni preset salva flatness, scala, rim e
  quantità nuvole.
- **Perlin-Worley**: Voronoi 0.38 + Perlin 0.44 + erosione 0.18.
- **Derivata solare su densità completa**: secondo campione a `p + 0.12 L`;
  `Delta Gain` e `Rim Boost` sono ora slider espliciti (default 1.0).
- **Aerial blending**: il colore delle nuvole resta indipendente dall'orizzonte;
  **Sky Accent** è opzionale per la banda turchese/corallo.
- **Micro stelle**: densità ×2.5, core 0.040/POWER 2.5, noise 45,
  magnitudine 0.48..0.78 e alone tenue per la leggibilità.
- **Contrails** opzionali, spente di default.
- **mu_s**: `L.z` spegne la corona solare sotto l’orizzonte.
- **Nuovo sky mapping**: ground solo sotto `Z=0` (-0.08..0.01), picco mid-sky
  clampato 0.05..0.65 e transizione zenitale controllata da Softness.
- Fix 0.8.1: il custom Sun non ricolora più le nuvole.

### Novità 0.8.0

- **Sun Elevation / Sun Azimuth** con sincronizzazione bidirezionale e **Stage
  Backlight** one-click.
- **Starfield** procedurale con quantità/densità e **Cloud Wind**.
- **Aerial Haze** per la foschia atmosferica in profondità.
- **Normal Ink Lines** per pieghe e spigoli interni.
- **Terminator Warmth** e **Rim Mode** (sole / contour / backlight).
- **Exclude Material** per escludere un materiale dal tint globale.
- Fix: maschera geometria condivisa tra Light Wrap e Ink; `sun_toward` rispetta
  i vincoli; lo Shadow Tint off mantiene Cel/Rim; la rotazione manuale del sole
  non viene più resettata dai refresh del world.
- **0.8.1**: il colore custom del Sole non modifica più il colore delle nuvole.

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
| Golden Hour | controluce caldo, alone arancione, cielo lavanda |
| After School Sunset | cielo salmone, nuvole viola in controluce con bordi dorati |
| Summer Noon | luce alta e pulita, cielo azzurro, ombre fresche |
| Rainy Tokyo Night | notte piovosa, blu freddo, contrasto medio |
| Cyberpunk Neon | magenta/ciano, zenit blu-viola, ombre colorate |
| Sakura Spring | cielo azzurro, orizzonte rosa, luce calda e morbida |
| Twilight Dusk | cielo indaco, orizzonte arancio, sole basso |

## Impostazioni principali

- **World Gradient / Horizon / Horizon Softness**
- **Auto Sun** (creazione automatica della SUN), **Sun Elevation / Azimuth** e
  **Stage Backlight**
- **Clouds** + quantità, scala, **Cloud Flatness**, **Cloud Wind**,
  **Contrails**, **Delta Gain** e **Rim Boost**; **Sun Glow**; **Sky Accent**;
  **Stars** + quantità e densità
- **Shadow Tint** + forza, distanza, Hue Lift, numero materiali, `Clear Shadow Tint`
- **Cel Shading** + Cel Shadow, Terminator Sharpness e Terminator Warmth
- **Rim Light** + forza, larghezza, **Rim Mode** ed emissione
- **Exclude / Include Material** per il materiale attivo
- **Camera Override** (palette specifica della camera attiva)
- **Halation** (Glare Bloom) e forza
- **Painterly (Kuwahara)** e dimensione
- **Chromatic dispersion**
- **Light Wrap** con forza e dimensione
- **Aerial Haze** con forza
- **Ink Lines** + dimensione, forza e sensibilità Normal
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
o il colore originale della Base Color. Spegnere il toggle **Shadow Tint** porta
solo l'AO a 0 e mantiene Cel/Rim; la **X** rimuove il gruppo e disattiva anche
Cel/Rim. I materiali esclusi non vengono toccati dal sync globale.

La rotazione manuale del sole (slider o Stage Backlight) resta valida durante i
refresh di world/nuvole; la `sun_rotation` del preset viene riapplicata solo
quando cambia la palette effettiva.

## Garanzie e limiti

- Nessun salvataggio automatico del `.blend`.
- Stack idempotente: rebuild non duplica gruppi o nodi.
- Shadow tint: tint moltiplicativo delle zone in ombra che preserva le texture,
  più Hue Lift additivo per i materiali caldi; il cel terminator è un tint
  direzionale, non una vera rimappatura della luce.
  Resta un proxy di contatto/occlusione, non ricolora le ombre proiettate.
- Colori palette in Scene-Linear Rec.709, non sRGB: i valori HDR (orizzonte, sole,
  nuvole) possono superare 1.0 e vengono compressi da AgX.
- La `sun_rotation` dei preset viene applicata solo alla Sun automatica, non alle
  luci sole create dall’utente.
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

Look-dev (sette palette + contact sheet 4 colonne):

```powershell
& $blender -b --factory-startup --python preset_dev\lookdev.py -- --out "$env:TEMP\ald_lookdev"
```

Il gate copre: gradient, Auto Sun, controlli solari e Stage Backlight, stelle e
cloud wind, God Rays (nodo, posizione proiettata, mute/restore), shadow tint
(inserimento/rimozione/ripristino e toggle Cel/Rim), Light Wrap, Aerial Haze,
Ink depth/Normal, terminator warmth/rim bias, esclusione materiali, shot markers,
material presets, idempotenza, multi-scena, render EEVEE e coerenza versione
`bl_info`/manifest.

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
- **0.6.2** — fix icona pannello Camera Override.
- **0.7.0** — color script Linear Rec.709, mid-sky bridge, nuvole direzionali, hue lift.
- **0.8.0** - controlli solari, Stage Backlight, stelle/cloud wind, aerial haze,
  normal ink, terminator warmth, rim mode, esclusione materiali.
- **0.8.1** - fix: il colore custom del Sole non ricolora più le nuvole.
- **0.9.0** - After School Sunset, nuvole planari prospettiche, shading
  backlit con silver lining, micro starfield, nuovo sky mapping.
- **0.9.1** - stile nuvola per-preset calibrato sulle reference (After School
  a bande, Summer Noon a cumuli) e blend sfera/guscio per Cloud Flatness.
- **0.9.2** - Cloud Amount e Cloud Scale visibili anche nella Sidebar N.
- **0.9.3** - Silver Lining edge-local: a Cloud Amount 1 il corpo resta viola.
- **0.9.4** - rimosso il residuo 8% di Cloud Light sul corpo; versione visibile
  nella Sidebar per verificare il reload.
- **0.9.5** - marker del World Gradient a 10: le scene esistenti ricostruiscono
  il grafo con il Cloud Light solo sul bordo.
- **0.9.6** - fix label versione nella Sidebar: il pannello non spariva più
  per colpa di `addon.module` (stringa) usato come modulo.
- **0.9.7** - Cloud Amount = copertura, delta solare dopo il Mapping e
  contrails come isolinea sottile.
- **0.9.8** - Domain warping, macro-banco, silhouette separata, luce per
  singola nuvola e contrails rettilinei in prospettiva.
- **0.9.9** - Contrails in coordinate gnomonico `X/Z`, `Y/Z` per evitare archi;
  marker World Group 13.
- **1.0.0** - Densità nuvole campionata sulla cupola con helper dedicato,
  morfologia fBm, derivata solare 2D e 3 fasce cel-shaded nette.
- **1.0.1** - Nuvole a cupole Voronoi mascherate, derivata su volume
  liscio, 4 fasce gouache e reset degli slider su Apply Palette.
- **1.0.2** - Ripristino della morfologia fBm organica v1.0.0; Cloud Light
  confinato al bordo solare, senza crown_curve, e reset di Cloud Scale/Delta
  Gain/Rim Boost su Apply Palette.
- **1.0.3** - Derivata solare su envelope a bassa frequenza, fringe esterno
  più stretto e reset di orizzonte, contrail e stelle su Apply Palette.
- **1.0.4** - Colore nuvole indipendente dall'orizzonte, starfield a cluster
  con hero stars, preset atmosferici completi e nomi UI neutri.
- **1.0.5** - Selettori Cloud Shadow/Mid/Light in Custom Colors e starfield a 3 livelli con hash Voronoi, temperature casuali e glow 6x.
- **1.0.6** - Toggle cielo sempre ripristinati, Star Amount reale senza moltiplicazioni nascoste, stelle leggibili con domain warp e pannelli allineati.
- **1.0.7** - Cielo escluso dal Kuwahara, stelle puntiformi Poisson, Horizon Offset reale, contrail tintate.
- **1.0.8** - Stelle PSF anti-aliasing con canali hash indipendenti e nuvole Perlin-Worley.
- **1.1.0** - Toggle Sun Beams/Sun Glow, stelle cadenti procedurali e fuochi d'artificio Hanabi.
- **1.1.1** - Stelle cadenti stereografiche 2D, Via Lattea e fuochi Hanabi a raggi continui.
- **1.1.2** - Piano tangente per meteore/fuochi, Milky Way cablata e colori Hanabi saturi.
- **1.1.3** - Fuochi Hanabi 2D stereografici, gusci cavi e palette cromatiche pure.
- **1.1.4** - Fuochi Hanabi a gusci sferici scorciati, scie a larghezza costante e teste hoshi HDR.
- **2.0.0** - FX particellari 3D per fuochi d'artificio e stelle cadenti con profondità e gravità reali.
- **2.0.1** - Scie particellari rastremate, gusci vuoti e gravita' piu' marcata nei fuochi FX.

- **2.1.0** - Solver FX deterministico con drag analitico, ownership per scena e selettore del backend.

- **2.2.0** - Separazione compositoriale degli FX con glow dedicato e nuclei netti.

- **2.3.0** - FX animati aggiornati in place, composizione a ruoli e famiglie sfalsate.

- **2.4.0** - Scie a corona di scintille e controllo Burst Age dal pannello FX.

- **2.5.0** - Pistil interno, editor dei sistemi FX e occlusione verificata con render.

- **2.6.0** - Scie granulari a 16 campioni, frammenti e persistent train delle meteore, controlli di composizione.

- **2.7.0** - Prototipo Geometry Nodes per le teste dei fuochi (dati su attributi, moto valutato da Scene Time).
- **2.8.0** - Geometry Nodes valuta tutta la popolazione del burst (teste, grani, pistil, scintille), con gate di parità rispetto al solver Python.

