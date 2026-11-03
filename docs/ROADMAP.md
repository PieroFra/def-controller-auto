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
- Chiusa la cartella locale `_esperimenti\` (già esclusa da `.gitignore`).

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

## Regole trasversali (valide per ogni fase)
- Un modulo alla volta: un intervento per modulo, poi build + verifica completa.
- Non rinominare `bl_info` name, categoria Rigging, né id `ctrl_def.*`.
- Fallback espliciti tra 4.2 LTS e 5.x, nessun controllo di versione sparso.
- I test headless fanno parte della verifica documentata; ogni fase si chiude
  con i conteggi attesi e zero fallimenti.
- Le verifiche interattive e le prove esplorative restano prove manuali
  separate: aggiornano la documentazione, non sostituiscono i test headless.
