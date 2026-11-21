# ROADMAP — CTRL_DEF (Controller Automatici da DEF)

Piano di sviluppo a fasi verso **v0.2.0**. Approccio: **un modulo alla volta**,
con verifica completa (build, sintassi e suite headless) a ogni fase.
Il monolite `__init__.py` si rigenera con la build; non si modifica mai a mano.

## Stato corrente
- Versione: **0.2.0** (bl_info e `blender_manifest.toml`, categoria Rigging).
- Architettura attiva: "Moduli + Build Step" — fonte di verità in
  `ctrl_def_mods\*.py`, build deterministico `scripts\build_monolith.py`
  (`build=IN_SYNC` nella verifica).
- Suite headless: verifica completa (build, sintassi e suite Blender
  headless) con controllo dei conteggi attesi.

---

## Fase A (COMPLETATA) — Architettura Moduli + Build Step e I18N dinamica

- Split del monolite in **9 moduli** in `ctrl_def_mods\*.py` + builder
  deterministico `scripts\build_monolith.py` (`build=IN_SYNC`).
- Localizzazione dinamica IT/EN completa incluse le `EnumProperty`
  (`_items_*`): le etichette cambiano lingua senza riavvio.

Stato archiviato come REFERENZA: non è un gate aperto.

---

## Fase B (COMPLETATA) — Diagnostica Pre-Flight (`ctrl_def.diagnose`)

- **Moduli target:** `ctrl_def_generation.py` + `ctrl_def_operators.py`
  + `ctrl_def_ui.py` + `ctrl_def_i18n.py`.
- **Cosa:**
  - funzione pura `_diagnose_def_selection(arm, stg)`;
  - operatore `ctrl_def.diagnose` che rileva:
    - bone `DEF` di lunghezza nulla (`< 1e-6`);
    - controparti specchiate `.L`/`.R` mancanti quando `mirror=True`;
    - collisioni di nome con bone non-DEF già esistenti;
    - avviso se `parent == "DEF"` con A.C.T.D. (rischio Dependency Cycle).
- **Verifica:** test headless dedicato in `tests/test_ctrl_def.py`.

---

## Fase C (COMPLETATA) — Orientamento e Offset Custom Shape (`shape_rotation_euler` / `shape_translation`)

- **Moduli target:** `ctrl_def_properties.py` + `ctrl_def_generation.py`
  + `ctrl_def_ui.py`.
- **Cosa:**
  - proprietà `shape_rot` (`FloatVectorProperty`, subtype `XYZ` / `EULER`)
    su `CTRLDEF_PG_settings`;
  - applicata a `pbone.custom_shape_rotation_euler`, così anelli e frecce si
    orientano lungo l'asse del bone senza ruotare la mesh condivisa.
- **Verifica:** test headless di verifica orientamento shape.

Completata: proprietà `shape_rot` su `CTRLDEF_PG_settings` implementata e
verificata dai test headless (commit `f5bfdb5`, Fase C+D).

---

## Fase D (COMPLETATA) — Export Mappa CTRL→DEF (JSON/CSV) e Preset Utente JSON

- **Moduli target:** `ctrl_def_operators.py` + `ctrl_def_ui.py`.
- **Cosa:**
  - operatori `ctrl_def.export_json` e `ctrl_def.export_csv` per esportare il
    registro `_ctrl_def_generated` + metadati rig;
  - salvataggio/caricamento preset utente su file `.json`.
- **Verifica:** test headless di round-trip JSON/CSV.

Completata: operatori `ctrl_def.export_json`, `ctrl_def.export_csv`,
`ctrl_def.save_preset` e `ctrl_def.load_preset` implementati e verificati
dai test headless (commit `f5bfdb5`, Fase C+D).

---

## Fase E (COMPLETATA) — Catena IK Rapida Opzionale + Rilascio `v0.2.0`

- **Moduli target:** `ctrl_def_generation.py` + `ctrl_def_operators.py` + `ctrl_def_ui.py`.
- **Cosa (implementato):**
  - operatore `ctrl_def.add_ik` su catene selezionate di 2-3 controller
    (target + pole opzionale, `use_deform=False`, zero Dependency Cycle con A.C.T.D.);
  - **delega dei widget a Bone Widget** come dipendenza opzionale:
    `ctrl_def.create_widget` invoca l'estensione (`bpy.ops.bonewidget.create_widget`)
    e il pannello mostra il link diretto di installazione quando non è presente;
    nessuna libreria di widget integrata nell'addon.
- **Verifica:** test headless dedicati (target IK, diagnostica, export, round-trip
  preset, widget) in `tests/test_ctrl_def.py` — ultimo esito locale su Blender
  5.2.0 LTS: `passati=5 falliti=0 totale=5` (vedi `tests/test_out.txt`).

---

## Ciclo `v0.2.0` (COMPLETATA) — Bump, Package Modulare e Documentazione

- Bump a **0.2.0** in `bl_info` (monolite generato) e `blender_manifest.toml`.
- ZIP di release `dist\def_controller_auto_v0.2.0.zip` con `.sha256`
  (package modulare: monolite + `ctrl_def_mods\`, con la struttura reale
  documentata nei README) + note di release in `dist\`.
- README EN/IT aggiornati all'architettura `v0.2.0` (package modulare,
  Bone Collection `"CTRLS"`, 3 sezioni collassabili + Guida, Bone Widget,
  Target IK, Diagnostica, Export JSON/CSV e Preset Utente).
- Chiusa la cartella locale degli script di test (già esclusa da `.gitignore`).

Nota: v0.2.0 è stata pubblicata su GitHub (commit `e64025f`) ed è approvata e
live su Blender Extensions (`https://extensions.blender.org/add-ons/ctrl-def/`).

---

## Ciclo `v0.3.0` — Multi-Layer Rig Pipeline (DEF / MCH / ORG / CTRL), IK World +Y & Rebranding

Estensione dell'addon a una vera pipeline di rig multi-layer, stile Rigify,
mantenendo l'estensione già approvata su Blender Extensions. Approccio:
**un modulo alla volta**, con verifica completa a ogni fase.

### Fase F — Rebranding Visuale (zero rottura compatibilità)
- **Moduli target:** `bl_info` (monolite generato) + `blender_manifest.toml`
  + titoli UI e docs.
- **Cosa:**
  - aggiornamento nome display (`bl_info["name"]`, `name` in
    `blender_manifest.toml`, titoli dei pannelli e documentazione);
  - INVARIATI `id = "ctrl_def"` su Blender Extensions e tutti i
    `bl_idname = "ctrl_def.*"` (operatori, pannelli, proprietà, UIList):
    nessuna perdita dell'estensione approvata né dei preset utente.
- **Verifica:** build `IN_SYNC` + controllo che nessun id
  registrato sia cambiato.

### Fase G — Modello Dati & Preset Pipeline Multi-Layer (`ctrl_def_properties.py` + `ctrl_def_i18n.py`)
- **Cosa:**
  - supporto per layer sorgente/destinazione flessibili: `DEF_`, `MCH_`,
    `ORG_`, `CTRL_` o nome pulito (nessun prefisso);
  - Bone Collection automatica dedicata al layer target
    (`"CTRLS"`, `"MCH"`, `"ORG"`);
  - preset rapidi di Pipeline:
    - `DEF -> CTRL` diretto (comportamento attuale);
    - `DEF -> MCH -> CTRL`;
    - `DEF -> ORG -> MCH -> CTRL` (stile Rigify);
    - `MCH -> ORG`;
    - `ORG -> CTRL`;
  - opzioni IK in `CTRLDEF_PG_settings`:
    - `ik_align_world_y` (`BoolProperty`, default `True`): il bone `IK_*`
      punta lungo `+Y` globale con `roll = 0.0` e lunghezza proporzionale
      alla catena;
    - `ik_create_pole` (`BoolProperty`, default `False`): creazione opzionale
      `POLE_*` proiettato lungo il piano di piega del gomito/ginocchio;
  - etichette IT/EN aggiornate (i18n dinamica esistente, `_items_*` incluse).
- **Verifica:** test headless dedicati in `tests/test_ctrl_def.py` + verifica completa.

### Fase H — Generazione Multi-Layer & Catene Concatenabili (`ctrl_def_generation.py` + `ctrl_def_registry.py`)
- **Cosa:**
  - estensione di `_collect_def_bones` / `_create_ctrl_edit_bones` per
    generare da qualsiasi layer sorgente (`prefix_def` = `DEF_`, `MCH_`,
    `ORG_`) verso qualsiasi layer target (`prefix_ctrl` = `""`, `CTRL_`,
    `MCH_`, `ORG_`);
  - assegnazione della Bone Collection coerente al layer target;
  - tracciamento delle coppie `source -> target` nel registro JSON
    (`ctrl_def_registry.py`), con supporto per catene multi-step
    `DEF -> MCH -> ORG -> CTRL` senza Dependency Cycle.
- **Verifica:** test headless (coppie registrate, catene multi-step, assenza
  di cicli) in `tests/test_ctrl_def.py` + verifica completa.

### Fase I — IK World-Aligned (`+Y` globale) + Binding Multi-Hop (`ctrl_def_operators.py`)
- **Cosa:**
  - raffinamento di `_add_ik_target_chain` (righe 625-683): `IK_<tip>` nasce
    alla tail della catena ma con direzione `(0, +L, 0)` (asse `+Y` globale),
    `roll = 0.0`, `use_deform = False`;
  - supporto Pole Target (`POLE_<mid>`) posizionato davanti al
    ginocchio/gomito, proiettato lungo il piano di piega;
  - estensione di `ctrl_def.bind_actd` e `_apply_native_bindings` per
    vincolare qualsiasi coppia registrata (`DEF <- MCH`, `MCH <- ORG`,
    `ORG <- CTRL` o `DEF <- CTRL`).
- **Verifica:** test headless (orientamento `+Y`, roll, pole, binding
  multi-hop) in `tests/test_ctrl_def.py` + verifica completa.

### Fase J — UI Collapsible, Test Headless & Rilascio `v0.3.0` (`ctrl_def_ui.py` + `tests\test_ctrl_def.py`)
- **Cosa:**
  - aggiornamento pannello `1 · Setup`: selettore Pipeline / Layer
    `DEF/MCH/ORG/CTRL`;
  - aggiornamento pannello `3 · Advanced`: opzioni IK `+Y World` e
    `Pole Target`;
  - test headless e probe UI (atteso `flagged=0`, nessun troncamento);
  - bump a **0.3.0**, package ZIP in `dist\` e rilascio `v0.3.0`.
- **Verifica:** verifica completa + probe UI deterministico + release ZIP/SHA256.

---

## Ciclo `v0.4.0` — Roadmap upgrade IK-FK

Estensione IK-FK dopo il ciclo multi-layer `v0.3.0`. Le fasi sotto sono
indipendenti da quelle omonime F-I del ciclo `v0.3.0` (già storico) e
ripartono da qui. Approccio: **un modulo alla volta**, gate a tag univoco.

### Fase F — Snap IK→FK — **CHIUSA** (gate verde `snap-f-g3`, suite 14/14)
- Nuovo operatore `ctrl_def.snap_ik_to_fk`: legge la matrice del target IK e
  scrive le pose FK sui controller registrati della catena.
- Rischio noto: ordine di valutazione e roll dei bone; gestione esplicita.
- **Verifica:** test headless in `tests\test_ctrl_def.py`; gate a tag univoco.

### Fase G — Bake IK→FK — **CHIUSA** (gate verde `bake-g3`, suite 14/14)
- Bake via `bpy.ops.nla.bake` con `temp_override` + rimozione del constraint IK
  al termine.
- Verificare esplicitamente la compatibilità 4.2 / 5.2 (fallback, non controlli
  di versione sparsi) e i test headless.
- **Verifica:** test headless; gate a tag univoco.

### Fase H — Space switching del target IK — **CHIUSA** (gate verde `space-h-g2`, suite 15/15)
- Operatore `ctrl_def.set_ik_target_space` e proprietà `ik_target_space`
  (enum `World / Local / Oggetto` su `CTRLDEF_PG_settings`) per lo space del
  target IK, con compensazione matrice per non rompere la posa al cambio.
- **Verifica:** test headless (posa invariante al cambio di space); gate a
  tag univoco.

### Fase I — Release `v0.4.0`
- Bump versione (bl_info + `blender_manifest.toml`), CHANGELOG, ZIP in
  `dist\` con `.sha256`, pubblicazione GitHub + Blender Extensions, GIF demo.
- Subordinata al gate completo delle fasi F-H e alla passata del visualizzatore.

---

## Note tecniche (da ciclo v0.4.0)
- Export FBX/glTF/deform-only: coperto da `bbone_to_bones` (runtime confermato).
- Checker UV: non coperto da Intelligent UV; da valutare in futuro.
- README IUV con ZIP 0.36.0 vs release 0.36.3: priorità bassa.

---

## Regole trasversali (valide per ogni fase)
- Un modulo alla volta: un intervento per modulo, poi build + verifica completa.
- Non rinominare `bl_info` name, categoria Rigging, né id `ctrl_def.*`.
- Fallback espliciti tra 4.2 LTS e 5.x, nessun controllo di versione sparso.
- I test headless fanno parte della verifica documentata; ogni fase si chiude
  con i conteggi attesi e zero fallimenti.
- Le verifiche interattive e le prove esplorative restano prove manuali
  separate: aggiornano la documentazione, non sostituiscono i test headless.

---

## Ciclo v0.5.0 — Roadmap diferenciazione e robustezza

**PREMESSA.** Obiettivo del ciclo: feature che i competitor non fanno o vendono
a pagamento (es. Auto-Rig Pro, ~$50 per il modulo Remap/Smart). Il punto forte
di CTRL_DEF resta la capacità di generare controller a partire dai DEF
esistenti di un rig già pronto, senza rifare il rig da zero. Ogni modulo segue
la catena di montaggio a 5 anelli: codice (Red → patch → Green), gate a tag
univoco, validazione (revisore + preset-compatible + audit-docs), probe UI con
`flagged=0`, avanzamento solo se tutto è verde. Ogni modulo ha test headless
prima e dopo, nessun commit intermedi, release unica finale a fine ciclo.

### Moduli in ordine

- **M1 — Rig Health Score (CHIUSA, gate module-a-g5, suite 17/17).** Modulo `ctrl_def.rig_score`: 30
  controlli ripartiti in 5 categorie, voto sintetico in trentesimi (max /30).
- **M2 — Remap DEF → CTRL (CHIUSA, gate module-b-g2, suite 18/18).** Modulo
  `ctrl_def.remap`: mapping cross-rig dei controller su nuovi rig, import
  azioni; equivale funzionalmente al modulo Remap venduto a $50.
- **M3 — Manifest + Diff (CHIUSA, gate module-c3-g2, suite 19/19).** Snapshot JSON del registry, gerarchia,
  constraint, IK e deform + comando diff con avviso di drift. Fattibilità ALTA.
- **M4 — Auto-Organizzazione Collection (CHIUSA, gate module-d4-g3, suite 20/20).**
  Assegnazione automatica di CTRLS / IK / DEF / MCH / ORG in base al registry e
  alla profondità della catena.
- **M5 — Handoff Animatore One-Click (CHIUSA, gate module-e5-g3, suite 21/21).**
  Blocca MCH/ORG, nasconde DEF, mostra solo CTRLS, scala shape e widget per
  l'animatore; restore reversibile con `ctrl_def.restore_rigger`.
- **M6 — Naming Doctor Safe Rename (CHIUSA, gate module-f6-g3, suite 22/22).** Rinomina
  batch di DEF/CTRL aggiornando registry, constraint, shape, target IK e parent
  in modo sicuro.
- **M7 — Character Picker auto (CHIUSA, gate module-g7-g1, suite 23/23).** Gruppi
  Root / Spine / Braccia / Gambe / Faccia / IK / Pole derivati da parent chain e
  mirror, esposti con `ctrl_def.character_picker`.
- **M8 — Release `v0.5.0`.** Bump versione, CHANGELOG, ZIP + sha256,
  pubblicazione GitHub + Blender Extensions, sync profilo. Subordinata al gate
  completo di tutti i moduli e alla passata del visualizzatore.

### Nota di chiusura ciclo v0.5.0

Dopo i test funzionali il ciclo ha subito sei fix di chiusura, ognuno con il
proprio gate: fix1-g1 (manifest_diff), fix2-g1 (rig_score), fix3-g1
(auto_collection), fix4-g1 (character_picker), fix5-g1 (i18n) e fix6-g1
(30esimo check rig_score). La suite finale passa completa con gate test-all-v1
(28/28) e si chiude con il gate harden-g2 (hardening del registry: JSON dict e
batch O(N), try/finally mode_set, guard bake_ok, compatibilità selezione
4.2/5.2, pulizia collection vuote), suite 30/30 (`passati=30 falliti=0
totale=30`). Il ciclo si estende con il gate opt-gui-g2: cache del registry
O(1), fix del warning depsgraph e redesign ergonomico della GUI (v0.5.0),
con il nuovo test `test_ui_and_depsgraph_optimization` a portare la suite
a 31 test. Il gate coll-polish-g1 rifinisce le collection: creazione automatica
della collection `DEF` in generate e `IK` in add_ik, handoff con hide sui bones
`MCH`/`ORG`, pruning delle collection vuote su remove, operatore GUI
`ctrl_def.character_picker` (suite 31/31, `VERIFY_OK passed=31 failed=0`).
La suite si allinea a 35 test con il gate `auto-suite-35-g2`
(`VERIFY_OK passed=35 failed=0`, run 20261119235946-ef1e59dd). Il gate
`zero-leak-g1` chiude il ciclo (`VERIFY_OK | passed=35 | failed=0`,
run 20261120001137-08332dab): fix del dependency cycle su `parent=ROOT` con
pipeline multi-layer e pulizia dei datablock Mesh orfani dei widget.

### Obiettivi trasversali

- Aumentare la copertura dei test a ogni modulo aggiunto.
- Automatizzare la catena di montaggio (meno passi manuali per anello).
- Mantenere il codice facile da mantenere: nessun `except` muto, fallback
  espliciti, i18n completa.
- GUI pulita e semplice: l'addon deve essere usabile sia da esperti sia da
  neofiti. Ogni nuovo operatore/proprieta' va esposto con etichette brevi,
  raggruppamenti logici e tooltip chiari; evitare proliferazione di controlli
  nel pannello principale. Il probe UI (flagged=0 in IT/EN) resta obbligatorio
  a ogni modulo e la leggibilita' va verificata anche a vista dal visualizzatore.
- Nota UI da ispezione (flagged=0): compattare la fascia di stato della
  sezione 1 e isolare l'azione principale in fondo alla sezione 2; ridurre lo
  scroll per i neofiti.
- Azione principale (post Modulo A, probe flagged=0): dare enfasi visiva e
  separazione al pulsante primario (box dedicato o separatore) per orientare
  i neofiti, senza aggiungere controlli.
