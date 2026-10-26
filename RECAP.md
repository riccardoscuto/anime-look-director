# Anime Look Director — Recap

**Versione 2.46.7** · Blender 5.1.2 · GPL-3.0-or-later

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
22. **FX 3D** — fuochi d'artificio, meteore e bolide come oggetti reali nella
    collezione `ALD | FX`, con sistemi persistenti per UID e ruoli, seeds
    stabili, launcher visibili e clock proprio (Timeline / Preview / Burst Age).
23. **Compositing FX corretto** — layer dedicati `ALD FX Base` (ambiente) e
    `ALD FX Only` (solo FX), copertura da `max(R,G,B)` clampata, occlusione per
    profondità e formula `C = (1-A)*Painted_B + F + Glare(F)`; con zero FX
    l'immagine è identica.
24. **Fumo atmosferico** — volume reale (`Principled Volume`) nella collezione
    `ALD | Smoke`, orientato all'Anchor, renderizzato dall'ambiente e rimosso
    con `Remove ALD from Scene`.
25. **Varianti e regia** — `FX Style` Classic / Soft Halo / Vivid e spettacoli
    diretti da 3 o 5 burst con ruoli hero/secondary/distant.
26. **Diagnostica e benchmark** — report esplicito `Diagnose FX` (read-only nel
    pannello, stato `UNKNOWN` finché non viene calcolato) e benchmark separati
    per creazione, update, clock, frame, memoria e render.

## Novità 2.46.7 — pacchetto installabile

- **LICENSE** GPL-3.0 completo e lista `[build]` nel manifest: il pacchetto
  contiene add-on, manifest, licenza e documenti utente, non le evidenze di
  ricerca.
- **`preset_dev/build_release.py`** costruisce
  `dist/anime_look_director-<versione>.zip` (~240 KB, contro 71 MB includendo
  `preset_dev/` e `graphify-out/`).
- **`dist/`** è ignorato da git.

## Novità 2.46.6 — world e sole di proprietà della scena

- **World isolato**: `ownership.repair` copia il world condiviso per la copia;
  applicare una palette alla copia non riscrive più il cielo dell'originale.
- **Sole auto di scena**: il sole creato dall'add-on porta `ald_sun_owner` con
  l'identità della scena; una copia non lo ritinta. Un file vecchio con sole a
  uso singolo riceve il tag alla successiva applicazione.
- **Fixture**: applica una palette diversa a una copia e verifica che world e
  sole dell'originale restino invariati.

## Novità 2.46.5 — path del pass per scena

- **Default per scena**: `_default_pass_path` include il nome della scena
  (sanificato), quindi due scene senza path esplicito non scrivono più lo
  stesso EXR. Un path personalizzato resta una scelta dell'utente; una copia
  di scena lo eredita finché non viene cambiato.

## Novità 2.46.4 — firma del pass per frame

- **Sequenze**: `render_fx_pass_animation` salva la firma di ogni frame;
  `fx_pass_state` confronta quella del frame corrente. Una camera animata non
  fa più sembrare vecchia tutta la sequenza: solo i frame realmente cambiati.
- **Gate**: verifica che il pass sia pronto a inizio e fine sequenza, stale dopo
  uno spostamento di camera e di nuovo pronto dopo il ripristino.

## Novità 2.46.3 — rimozione sicura sulle scene duplicate

- **Remove ALD from Scene / Detach** riparano la copia prima di agire: la
  rimozione non ripristina più i materiali condivisi dell'originale.
- **World e sole condivisi**: `snapshot.restore` non riscrive un world usato da
  un'altra scena e non modifica/rimuove un sole linkato altrove; l'operatore
  avvisa che il world condiviso è stato lasciato com'è.
- **Fixture**: rimuove ALD da una copia e verifica che nuvole, FX, materiali,
  nodi dei materiali e world dell'originale restino intatti.

## Novità 2.46.2 — repair automatico alla prima azione

- **Build / Apply Palette** chiamano `ownership.repair` prima di modificare la
  scena: una scena duplicata diventa indipendente senza premere il pulsante
  manuale. L'avviso nel pannello resta per la finestra prima della prima azione.
- **Fixture**: duplica la scena una seconda volta e verifica che sia proprio
  l'operatore Build a renderla indipendente (collezioni e oggetti distinti,
  originale intatto).

## Novità 2.46.1 — stato del pass consapevole del contenuto

- **Firma del pass** (`fx.pass_signature` + `fx_pass_signature`): hash di
  sistema/eventi, palette, backend, stile, età, posa camera, lente e risoluzione.
  Se cambi uno di questi, `fx_pass_state` dice "outdated" — non solo quando
  cambia il frame.
- **Verifica unica**: `preset_dev/verify_all.py` esegue gate, fixture duplicazione
  e audit in Blender freschi; esce 1 se uno fallisce. Anche `audit_plan.py` ora
  esce 1 su un punto rosso (prima usciva sempre 0).
- **Limite (risolto in 2.46.4)**: con una camera animata la firma usa la posa
  del frame corrente; su altri frame può dire "outdated" anche se la sequenza
  è valida. Non dice mai "pronto" per un pass vecchio.

## Novità 2.46.0 — pass FX per animazione

- **Sequenza per frame** (`compositor.render_fx_pass_animation`,
  `ald.fx_render_pass_animation`): un EXR numerato per ogni frame dell'intervallo
  della scena. Il nodo `ALD | FX Pass` legge la sequenza (`frame_duration`,
  `frame_start`) e il compositor segue l'animazione. Costo: un pass in più per
  frame.
- **Immagine per scena**: il pass si chiama `ALD | FX Pass | <scena>`; due scene
  non si sovrascrivono più il pass a vicenda.
- **Stato reale**: `compositor.fx_pass_state` distingue pronto / stale (altro
  frame o contenuto cambiato) / fuori intervallo / mancante, verificando
  l'esistenza del file. `fx.pass_signature` codifica FX, palette, camera e
  risoluzione: se cambi qualcosa, il pannello dice "outdated".
- **Pulsante still**: dopo il render ricostruisce lo stack, così il nodo del pass
  è collegato subito senza un Build manuale.
- **Verifica unica**: `preset_dev/verify_all.py` esegue gate, fixture e audit in
  Blender freschi e fallisce se uno dei tre fallisce (l'audit ora esce con 1
  anche quando un punto è rosso).
- **Limite dichiarato**: con una camera animata la firma usa la posa del frame
  corrente: su altri frame il pannello può dire "outdated" anche se la sequenza
  è valida. Non dice mai "pronto" per un pass vecchio.

## Novità 2.45.0 — scene duplicate e ricerca volume

- **Repair Ownership** (`ownership.py`, `ald.repair_ownership`): una scena
  duplicata riceve una identità ALD propria, scollega le collezioni condivise e
  rende indipendenti oggetti, mesh e materiali della copia. Se le collezioni
  erano condivise, nuvole e FX vengono ricostruiti dai dati persistenti con
  nuovi UID; il pannello avvisa quando un'altra scena condivide le collezioni.
- **Fixture dedicata** (`preset_dev/duplicate_fixture.py`): `DUP FIXTURE: PASS`.
  La copia ha collezioni e oggetti distinti, l'originale resta intatto e
  rimuovere le nuvole della copia non tocca l'originale.
- **Spike volume PA2** (`preset_dev/PA2_VOLUME_SPIKE.md`): stesso
  posizionamento del primo layer di card, 640x360. Le card rendono in 2.2 s; il
  volume nativo in 1.05–1.09 s ma appare come un rettangolo morbido con bordi
  netti, senza sagoma anime. Le varianti con shaping (bordo sfumato, soglia
  noise, emissione 0.15) non cambiano l'esito: sotto la densità leggibile la
  nuvola sparisce, sopra torna il box. **Le card restano il default**, nessun
  backend è cambiato e nessun asset PA2 è stato copiato.

## Novità 2.44.0 — benchmark nuvole e guardia scene

- **Benchmark** (`preset_dev/bench_clouds.py`): coverage 0.16/0.5/0.9/1.0 ×
  1/3/5 layer a 720p. Da 829 a 159.729 poligoni, creazione 0.06–0.12 s per
  layer, refresh ~1 ms, render 2.6–4.3 s. Dati in `clouds_bench/metrics.json`.
- **Guardia unlink**: rimuovendo le nuvole, un oggetto condiviso con un'altra
  collezione viene scollegato, non cancellato.
- **Aperto (risolto in 2.45.0 con Repair Ownership)**: la collezione di una
  scena duplicata è ancora condivisa; il test dedicato mostra che la rimozione
  nella copia può togliere la collezione originale. Non duplicare una scena con
  nuvole spaziali finché non è corretto.

## Novità 2.43.0 — envelope di framing

- **Envelope proiettato**: `event_radius`/`event_envelope`/`event_frame_fraction`
  misurano l'ingombro dell'intera esplosione, non solo il centro.
- Il gate richiede almeno il 15% dell'envelope in frame e stampa le frazioni;
  il report di composizione registra `frame_fraction` e `in_frame` è vero solo
  al 95%, non più sul centro.
- **Fit alla focale**: uno show multi-burst adatta distanza alla FOV verticale e
  limita lo spread laterale, così le focali strette non tagliano i bordi.
- Evidenza: l'hero dusk è al 94.9% (dichiarato non in frame), gli altri 98–100%;
  nel night 5 burst i due laterali sono tagliati e **dichiarati** (52.5%/45%).

## Novità 2.42.0 — P0 chiuso: pass FX esterno

- **F isolata**: il pulsante *Render FX Pass* renderizza la sola emissione FX
  su un EXR (view layer temporanea con la sola collezione FX); lo stack la
  legge con un nodo Image `ALD | FX Pass`. Un emettitore estraneo non può più
  entrare in F.
- **Gate**: burst + emettitore estraneo 40/20/4×3 dietro; il pass con e senza
  emettitore differisce di **0.0** (tolleranza 0.01); lo stack legge il file.
- **Workflow in due passi**: rendere il pass dopo modifiche a FX/camera/frame,
  poi lo shot; per le animazioni un pass per frame.
- **Fallback**: senza pass lo stack usa la Emission principale (limite noto ai
  bordi); il pannello mostra se il pass è pronto.

## Novità 2.41.0 — consolidamento (P0 aperto)

- **Coverage 1** non ricrea la lastra: soglia positiva e confronto stretto, il
  bordo resta vuoto.
- **Shot Locked** conserva la rotazione di creazione; Camera Facing ha la sua,
  e il ritorno alla modalità fissa non salta.
- **Materiale e LOD** corretti: la mesh rigenerata mantiene il materiale e il
  LOD usa la profondità finale.
- **Scene safety**: oggetti risolti per UID nella collezione della scena,
  collezioni condivise saltate, larghezze/palette/matte limitate agli FX della
  scena (inclusi i materiali nei modifier GN).
- **Kuwahara** e filtri ambiente dal layer base; flash con attenuazione World.
- **Test C0** riparato ed eseguibile: esce con codice 1 sul FAIL.
- **P0 aperto**: l'isolamento dell'emissione FX ai pixel parziali resta FAIL
  (0.995 fringe, 0.575 mixed con un emettitore estremo). AOV vuoto in
  EEVEE/Cycles; fallback FX-only non sincronizzato. Dettagli in
  `preset_dev/CONSOLIDATION_2_41.md`. La release non dichiara un PASS globale.

## Novità 2.40.0 — Spatial Clouds 2.0

- **Copertura reale**: Cloud Amount è la soglia del campo di densità. 0 non
  costruisce facce, 0.5 masse intermedie, 1 la copertura massima. Prima era
  ignorato (1536 poligoni per ogni valore).
- **Isole, non lastre**: campo procedurale con warp, due bande fBm e inviluppo
  ai bordi; aperture di cielo vere, nessun rettangolo.
- **Quota e profondità separate**: altitudine in unità World lungo l'Anchor,
  profondità dalla camera di creazione.
- **Layer persistenti e aggiornamenti in-place**: il colore non ricostruisce,
  quota/profondità spostano soltanto, la copertura rigenera la mesh dello
  stesso oggetto.
- **Modalità camera** Shot Locked / Camera Facing, **flash locale** guidato da
  `event.glow`, diagnostica dei layer.
- **Correzioni**: collisione di ownership FX/nuvole, `event_color` dalla
  palette, `event.size` con velocità scalata, larghezza apparente che segue
  camera/risoluzione, maschere ambiente dal layer base, palette FX in-place.
- **Aperti**: emissione non-FX ai bordi parziali (misurata), envelope di
  framing, scene duplicate. Dettagli in `preset_dev/SPATIAL_CLOUDS_2.md`.

## Novità 2.39.0 — primo piano nello showcase

- **Skyline scura** (quattro blocchi + antenna) al bordo inferiore dello shot
  1080p: è contenuto di scena per l'evidenza, non una feature dell'add-on —
  dà scala al cielo e mette alla prova ink ed occlusione.
- Materiale quasi nero (0.004) perché l'ambiente non la trasformi in un
  edificio illuminato.

## Novità 2.38.0 — showcase d'integrazione

- **Fasce 2.5D assottigliate** (0.30× la distanza, prima 0.55×), alzate e con
  più contrasto: leggono come strato di profondità, non come parete al centro
  del cielo; la luce di palette parte al 38% dell'altezza.
- **Showcase 1920×1080** in `preset_dev/showcase/`: cinque burst notturni e tre
  al tramonto con nuvole e compositing completo — l'evidenza che P1, P3, P4 e
  P5 convivono nello stesso frame.
- Evidenza nuvole rigenerata in `preset_dev/clouds/`.

## Novità 2.37.0 — verifica UI e striscia temporale

- **Pannello World rotto corretto**: il box 2.5D Clouds usava l'icona `CLOUD`,
  inesistente in Blender 5.1: `UILayout.label` andava in eccezione e l'intero
  pannello World & Shadows non veniva disegnato. Ora usa `WORLD`.
- **Check UI finalmente collegati**: `check_panel_icons` e `check_ui_parity`
  erano definiti ma mai chiamati dal gate; ora girano (ecco perché l'icona
  rotta era passata).
- **ui_probe** risolveva `--out` relativo alla CWD di Blender: ora è assoluto
  rispetto all'add-on; screenshot in `preset_dev/ui/`.
- **Striscia temporale** (`preset_dev/temporal_strip.py`): 6 età per
  Crisantemo e Willow con curva di copertura. Il Crisantemo picca a 1.1 s
  (26%) e sparisce a 2.2 s (1.4%); il Willow picca a 1.6 s (27%) e tiene il
  23% a 2.2 s.

## Novità 2.36.0 — P6 matrice di validazione

- **36 render** (3 palette × 4 famiglie × 3 età) a 800×450 con background di
  riferimento per la copertura FX, metriche per cella e contact sheet 6×6:
  **36/36 PASS**, tempo medio 1.51 s.
- **Pavimento di dimensione apparente** anche per teste e grani: un bead da
  0.05 m è 0.65 px a 55 m con un 32 mm (la Peonia perdeva scintillio).
- **Nota onesta**: il primo giro era shiftato di `fx_age` (default 0.8 s); il
  tool ora lo azzera. L'orologio del prodotto era corretto, il test no.
- Report in `preset_dev/P6_REPORT.md`, dati in `preset_dev/validation/`.

## Novità 2.35.0 — P5 nuvole 2.5D

- **Fasce di nuvole reali** a 160/230/320 m: geometria a silhouette ondulata
  (512 colonne), **opaca**, quindi scrive profondità e nasconde davvero i
  fuochi che le stanno dietro (via matte Cryptomatte, nessun path extra).
- **Colori dalla palette** (`clouds.sync` a ogni apply), controlli
  `Cloud Amount`/`Cloud Height` e operatori in entrambe le superfici.
- **Remove ALD** rimuove anche le nuvole.
- Evidenza in `preset_dev/clouds/` (dusk off/on, night on); gate con la matte
  dietro una fascia portata davanti (<75% della matte libera).

## Novità 2.34.0 — P4 composizione e spazialità

- **Gerarchia di profondità corretta**: hero 1.0×, secondary 1.18×, distant
  1.42× (prima 0.78× e 0.58×, cioè più vicini e più grandi).
- **Show con spazio**: con più burst distanza ×1.4 e spread laterale ×1.3.
- **Tempi**: il distant nasce a 0.55 s, quindi ha già esploso.
- Evidenza in `preset_dev/composition/` (dusk 3, night 5, golden 3) con
  `composition.json`; gate su profondità, tempi, dimensioni e posizioni.

## Novità 2.33.0 — P3 shading, palette e glow

- **Velo grigio rimosso**: il nodo `ALD | FX Painted Punch` aveva il socket B
  non collegato (default grigio 0.5) e stendeva un velo su ogni particella.
- **Doppia copertura corretta**: la pass `Emission` è già pesata dalla
  copertura geometrica; moltiplicarla di nuovo per la matte frazionaria la
  elevava al quadrato e le scie sottili scurivano il cielo. `F` usa una
  presenza binaria, il punch tiene la matte frazionaria.
- **Istanze nere risolte**: teste, bead e scintille sono geometrie istanziate e
  non ereditano gli attributi; ora hanno materiali `INSTANCER`, i tubi
  `GEOMETRY`.
- **Glow calibrato**: soglia 0, forza 1.0, size 0.35 (misurati sul composito);
  prima era di fatto inerte.
- **Coda con profondità**: `tail_u` porta l'energia a 0.35 verso la punta;
  **palette FX** tirata al 30% verso il colore del sole del cielo.
- Evidenza in `preset_dev/baseline_fx_p3/` e `preset_dev/calibration_p3/`;
  gate 50/50.

## Novità 2.32.0 — P2 geometria delle scie

- **Bug di fondo corretto**: `Points to Curves` richiede una *point cloud*, non
  le vertici di una mesh. Mancava `Mesh to Points`, quindi il tubo della scia era
  vuoto e si vedevano solo i grani: da qui i "puntini". Lo schema del gruppo è 4
  e i file salvati vengono ricostruiti.
- **Larghezza apparente**: il raggio fisico (0.022 m) è sub-pixel a 55 m.
  `Trail Min Pixels` (1.5) e `Trail Max Pixels` (6) lo portano in pixel usando
  sensore, lens, risoluzione, profondità e scala ortografica.
- **Tubo, non ribbon**: misurato in `preset_dev/trail_shape_spike.py`
  (tubo 1.00, ribbon 0.00 di copertura edge-on). Un burst è tridimensionale.
- **Meno regolarità**: ~35% di stelle secondarie (0.62× vita e velocità) e ogni
  stella tiene il 45–100% della coda: niente più dente di leone uniforme.
- Evidence in `preset_dev/baseline_fx_p2/` (emission/glow/full, 800×450 e
  1920×1080) più `p2_age_strip.py` a 0.12/0.30/0.60/1.10 s: la continuità si
  giudica senza Bloom. Gate 45/45.

## Novità 2.31.0 — P1 compositing FX

- **Copertura reale**: il layer principale espone il pass **Emission** e il
  **Cryptomatte Material** dei materiali FX. `A = ALD | FX Matte` è la
  copertura geometrica, non la luminanza.
- **Occlusione corretta**: `F = Emission × A` è premoltiplicato e già occluso
  dal render visibile; un muro davanti azzera sia le particelle sia il glow.
- **Formula**: `C = P(B)×(1-A) + F + Glare(F)`, con `ALD | FX Restore` in ADD
  a Factor 1 e un solo `ALD | FX Glow`.
- **Rimosso** il layer `ALD FX Only`, il world override trasparente, la
  copertura `max(R,G,B)` e il confronto di profondità per gli occlusori opachi.
- Baseline e spike in `preset_dev/baseline_fx/`, `preset_dev/P1_SPIKE.md`,
  `preset_dev/P1_REPORT.md`; gate con muro davanti/dietro, occlusore parziale,
  identità a zero FX e glow singolo.

## Novità 2.30.0 — Piano operativo P0–P3

- **P0 — dati e compositing**: baseline versionata (`preset_dev/baseline.json`),
  operatori FX sicuri (Update per UID, Remove/Duplicate coordinati, compilazione
  atomica), snapshot su ogni primo ingresso mutante con stato `REMOVED`,
  vero isolamento B/F/A con occlusione depth-based, diagnostica read-only.
- **P1 — modello persistente e parità**: ricostruzione del runtime da UID+ruolo
  (mai nomi), `random_key` stabile, migrazione `FX_SCHEMA = 2`, rebuild dopo
  undo/redo; gravità/unità/launcher dall'Anchor, Physical a `p_shell(T)`, clock
  senza rebuild, creazione al frame corrente; fallback GN→Python per singolo
  evento e sistemi misti.
- **P2 — profili e calibrazione**: il materiale legge `event_color`,
  `stable_noise`, `age_norm` e `trail_u`; profilo visivo con sotto-ruoli nel
  pannello; matrice di calibrazione AgX (notte/tramonto × nessun alone/stretto/
  ampio) in `preset_dev/calibration/`.
- **P3 — fumo, varianti, regia, benchmark**: fumo volumetrico, `FX Style`,
  spettacolo diretto 3/5 burst, benchmark con budget e hardware dichiarati in
  `preset_dev/benchmarks.json`.
- **Verifica**: gate `ALD GATE: PASS`, milestone 13/13, audit del piano 39/39,
  sheet look-dev rigenerate.

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
- **2.9.0** - Anche scie, flash e meteore sono valutati dai nodi: l'handler Python non scrive più geometria (2.5 ms per frame contro 121.7 ms).
- **2.9.1** - Limite senza drag nel gruppo di nodi e i test obbligatori della guida ancora mancanti nel gate (salto di frame, 24/30/60 fps, limiti matematici, figlie che sopravvivono alla testa, occlusione).
- **2.9.2** - Render di confronto FX con metadati registrati (`preset_dev/lookdev_fx.py`), correzione dell'elenco dei sistemi nel pannello e verifica UI con screenshot reali.
- **2.10.0** - Le cache vengono invalidate all'apertura di un nuovo file (handler `load_post`) e l'handler dei frame salta i sistemi valutati dai nodi.
- **2.10.1** - Render di confronto delle famiglie (Chrysanthemum, Peony, Willow) con stessa palette e seed: sono distinguibili per forma.
- **2.11.0** - Lo slider "Burst Age" sposta i sistemi senza ricostruire la geometria: 2.3 ms invece di 428 ms per passo (189x più veloce).
- **2.11.1** - La verifica UI diventa uno strumento del repository (`preset_dev/ui_probe.py`).
- **2.12.0** - Fase P0-A del piano operativo: decadimento corretto, energia separata dalla scala, regola di composizione dei burst, geometria delle meteore e origini delle figlie. GN e Python condividono gli stessi dati deterministici.
- **2.13.0** - Fase P0-B: schema persistente (sistemi ed eventi), identità di scena robusta con gestione della duplicazione, registry ricostruito dalla configurazione salvata e version marker dei gruppi GN.
- **2.14.0** - Fase P1-A: interfaccia unica tra Properties e sidebar, backend esclusivi (OFF / Legacy World / FX 3D), editor dei sistemi FX e controlli di look (energie per ruolo, attenuazione atmosferica).
- **2.15.0** - Fase P1-B: snapshot dello stato utente prima della prima modifica e operatore "Remove ALD from Scene" che ripristina mondo, sole, materiali, pass e compositor.
- **2.16.0** - Fase P1-C: il fuoco d'artificio è un evento completo (launcher, guscio in salita, scoppio senza discontinuità con le equazioni del piano, residui).
- **2.17.0** - Fase P1-D: le meteore sono eventi e il preset Hero Meteor (Bolide) è più grande, più luminoso e con una scia lunga e persistente.
- **2.18.0** - Fase P2: contratto materiale delle particelle (role, age_norm, energy, trail_u, stable_noise, event_color) e isolamento del layer FX nel compositor.
- **2.19.0** - Fase P3: solver numericamente stabile, camera valutata (constraint e parent), nuvole e shooting star legacy in secondi, famiglia Kamuro e backend scelto prima dell'allocazione.
- **2.20.0** - Milestone del piano: un singolo fuoco d'artificio completo e reversibile, il launcher visibile e la Definition of Done verificata da `preset_dev/milestone.py` (13/13).
- **2.20.1** - Le meteore legacy seguono il backend, i controlli legacy compaiono solo in Legacy World e la sezione FX è in cima nella sidebar.
- **2.21.0** - La sidebar View3D e le Scene properties espongono esattamente gli stessi controlli, con la stessa struttura.
- **2.22.0** - Le tre azioni sulla scena (Bypass, Remove ALD from Scene, Detach e Keep Result), i FX sono visibili subito dopo la creazione e le icone dei pannelli sono validate sull'elenco reale.
- **2.22.1** - La registrazione dell'add-on sopravvive al reload di Blender, camera e sole usano la trasformazione valutata e `preset_dev/audit_plan.py` verifica la conformità al piano operativo (69/70: resta solo il fumo atmosferico, opzionale nel piano).
- **2.24.0** - L'isolamento FX nel compositor è corretto: la DIFFERENCE algebraicamente non valida è sostituita da `C = (1-A)*Painted_B + F + Glare(F)` con layer base e layer FX-only; pannello diagnostico per evento; fisica corretta (gravità ovunque, derivata della velocità, eredità dei figli, traino del meteorita, clamp età negativa) e orologio reale per sistema.
- **2.25.0** - Risolto il crash `Writing to ID classes` durante il draw dei pannelli, aggiunto l'ALD Sky/FX Anchor (asse verticale, quota terreno, scala unità), l'avviso di conflitto camera-sotto-terreno (T15) e i test di accettazione T25-T28 (migrazione schema, undo/redo, build fallita, screenshot UI).
- **2.26.0** - Completa l'ALD Sky/FX Anchor con l'oggetto terreno esplicito: l'avviso di conflitto legge la world matrix della mesh del terreno quando assegnata, altrimenti ricade sulla quota numerica.
- **2.27.0** - Fix critico nello scrittore Python dei FX: `_update_meteors` crashava con `'NoneType' object has no attribute 'data'` perché il percorso non-GN salva trail/testa/fragmenti per evento ma l'aggiornatore li leggeva dal posto sbagliato. Aggiunto il test di accettazione T24 (tre profili FX a esposizione fissa).

