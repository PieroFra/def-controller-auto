# ROADMAP — CTRL_DEF (Controller Automatici da DEF)

Piano di sviluppo a fasi verso **v0.2.0**. Approccio: **un modulo alla volta**,
con verifica `gate.ps1` (verdetto `VERIFY_OK | ...` / `VERIFY_FAIL | ...`) a ogni fase.
Il monolite `__init__.py` si rigenera con la build; non si modifica mai a mano.

## Stato corrente
- Versione: **0.2.0** (bl_info e `blender_manifest.toml`, categoria Rigging).
- Architettura attiva: "Moduli + Build Step" — fonte di verità in
  `ctrl_def_mods\*.py`, build deterministico `scripts\build_monolith.py`
  (`build=IN_SYNC` nel gate).
- Suite headless: verifica completa tramite `.opencode\scripts\gate.ps1`
  (config: `.opencode\verify.config.psd1`).

---

## Fase A (COMPLETATA) — Architettura Moduli + Build Step e I18N dinamica

- Split del monolite in **9 moduli** in `ctrl_def_mods\*.py` + builder
  deterministico `scripts\build_monolith.py` (`build=IN_SYNC`).
- Localizzazione dinamica IT/EN completa incluse le `EnumProperty`
  (`_items_*`): le etichette cambiano lingua senza riavvio.

Stato archiviato come REFERENZA: non è un gate aperto.

---

## Fase B — Diagnostica Pre-Flight (`ctrl_def.diagnose`)

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

Nota: la pubblicazione su GitHub e Blender Extensions resta in attesa della
decisione dell'utente (nessun commit né push eseguiti).

---

## Regole trasversali (valide per ogni fase)
- Un modulo alla volta: un intervento per modulo, poi build + `gate.ps1`.
- Non rinominare `bl_info` name, categoria Rigging, né id `ctrl_def.*`.
- Fallback espliciti tra 4.2 LTS e 5.x, nessun controllo di versione sparso.
- I test headless li scrive il **Coder**; Repo-Ops non certifica gate, riporta
  solo la riga di verdetto.
- Gate interattivi e prove esplorative restano in sessioni dedicate
  (skill `addon-gui-gate`, `_esperimenti\`).
