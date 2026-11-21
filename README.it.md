**[🇬🇧 English](README.md) | 🇮🇹 Italiano**

# CTRL_DEF — Auto Rig Layers (DEF / MCH / ORG / CTRL)

[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%E2%80%94%205.2%2B-blueviolet)](https://www.blender.org)
[![Category](https://img.shields.io/badge/Category-Rigging-orange)](https://extensions.blender.org/)
[![Version](https://img.shields.io/badge/version-0.5.0-brightgreen)](https://github.com/PieroFra/def-controller-auto/releases)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)](LICENSE)
[![Blender Extensions](https://img.shields.io/badge/Blender_Extensions-ctrl--def-orange?logo=blender)](https://extensions.blender.org/add-ons/ctrl-def/)
[![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/PieroFra/badge.svg)](https://hub.xerj.org/contributors/PieroFra)
[![Downloads](https://img.shields.io/github/downloads/PieroFra/def-controller-auto/total?label=downloads)](https://github.com/PieroFra/def-controller-auto/releases)

Genera in un click bone controller tracciati, colorati e dotati di **custom shape condivise** a partire dalla catena di deformazione (`DEF_`) — **Auto Rig Layers** (`v0.5.0`): pipeline di rigging multi-livello (`DEF -> ORG -> MCH -> CTRL` e varianti) con livelli intermedi `ORG`/`MCH` automatici e auto-nascosti, target IK allineati a `+Y` mondo con pole automatico, package modulare `ctrl_def_mods\` e sinergia 1-click con **A.C.T.D.** (Auto Copy Transforms DEF) — zero Dependency Cycle.

| | |
|---|---|
| **Compatibilità** | **Blender 4.2 LTS — 5.2+** |
| **Categoria** | **Rigging** |
| **Versione** | **0.5.0** |
| **Autore** | **Pierfrancesco Diodato** |
| **Tipo** | Add-on (ZIP installabile o cartella) |
| **Licenza** | GPL-3.0-or-later |
| **Pagina ufficiale** | [Blender Extensions — ctrl-def](https://extensions.blender.org/add-ons/ctrl-def/) |

---

## 🆕 Novità della v0.3.0 (rispetto alla v0.2.0)

| Funzionalità | v0.2.0 | v0.3.0 |
|---|---|---|
| **Pipeline di Rigging** | Solo `DEF -> CTRL` diretta | Multi-Livello `DEF -> ORG -> MCH -> CTRL`, `DEF -> MCH -> CTRL`, `MCH -> ORG`, `ORG -> CTRL`, `Custom` |
| **Livelli intermedi (`MCH` / `ORG`)** | Setup manuale | Bone Collection `MCH` e `ORG` automatiche, auto-nascoste con lock di Location/Rotation/Scale (`lock_mch_org`) |
| **Orientamento del target IK** | Roll locale del bone ereditato | Allineato a `+Y` mondo (`ik_align_world_y = True`, `roll = 0.0`) in cima alla catena + Pole Target automatico (`ik_create_pole`) lungo il vettore di piega gomito/ginocchio |
| **Vincolatura 1-click (`ctrl_def.bind_actd`)** | Singolo hop `DEF <- CTRL` | Catena di constraint multi-hop completa (`DEF <- ORG <- MCH <- CTRL`) con zero Dependency Cycle |

---

## ⚡ Quick Start (in meno di 60 secondi — 4 passaggi)

1. Seleziona l'armatura, entra in **Edit Mode** (`Tab`) e seleziona i bone con prefisso `DEF_`.
2. Apri la Sidebar (`N`) → scheda **DEF Ctrl** e scegli un preset (es. *Arto Bipede (Cubo)*) o personalizza forma/colore/scala.
3. Clicca **Genera Controller** (`ctrl_def.generate`): vengono creati i controller puliti (`hand.L`) in catena FK nella Bone Collection `"CTRLS"`.
4. Clicca **Vincola DEF ai CTRL (ACTD)** (`ctrl_def.bind_actd`): i bone `DEF_` copiano istantaneamente le trasformazioni dei controller in Pose Mode senza Dependency Cycle.

> **Risultato:** ruoti `arm.L` in Pose Mode e `DEF_arm.L` lo segue in tempo reale — la mesh si deforma tramite i DEF, il controllo passa dai controller.

---

## 🚀 Caratteristiche Principali

- **Remap animazione** (`v0.5.0`): `ctrl_def.remap` trasferisce la posa dei controller da un rig sorgente a un rig destinazione usando la mappa DEF->CTRL, equivalente gratuito al Remap a pagamento dei competitor, gate `module-b-g2` (suite 18/18).

- **Naming pulito di default**: i controller si chiamano come i bone DEF senza prefisso (`DEF_hand.L` → `hand.L`, standard Blender/Rigify); con il campo *Prefisso Controller* si ottiene il naming classico (es. `CTRL_` → `CTRL_hand.L`).
- **Custom shape condivise per tipo** (`v0.1.2`): le forme wireframe sono oggetti condivisi (`CTRL_DEF_SHAPE_CIRCLE`, `CTRL_DEF_SHAPE_CUBE`, `CTRL_DEF_SHAPE_SPHERE`, `CTRL_DEF_SHAPE_ARROW`, `CTRL_DEF_SHAPE_CROSS`) — una sola mesh per tipo, riutilizzata da tutti i controller.
- **Generazione istantanea**: controller identici per posizione, orientamento e roll ai rispettivi `DEF_`, con `use_deform = False` (non deformano la mesh).
- **Gerarchia di default "Catena CTRL (FK)"**: ricrea l'albero FK tra i controller (`forearm.L` figlio di `arm.L`), rendendoli indipendenti dai DEF: **zero Dependency Cycle** con A.C.T.D., anche con parent `Root`.
- **Bone Collection dedicata**: isola automaticamente tutti i controller nella collezione `"CTRLS"` (rinominata da `"CTRL"` in `v0.2.0`).
- **Palette colori tematiche**: assegnazione rapida conforme al tema di Blender (Rosso, Verde, Blu).
- **Integrazione opzionale Bone Widget** (`v0.2.0`): i widget dei controller sono delegati all'estensione **Bone Widget** tramite `ctrl_def.create_widget` (selettore libreria integrato); senza estensione il pannello avvisa e offre il **link diretto** alla sua pagina.
- **Target IK rapido** (`v0.2.0`): `ctrl_def.add_ik` aggiunge un bone target IK (pole opzionale, `use_deform = False`) su una catena selezionata di 2‑3 controller, con zero Dependency Cycle con A.C.T.D.
- **Catena IK e space switching** (`v0.4.0`): `ik_chain_length` (1-8) definisce quanti controller della catena selezionata copre il constraint IK; `ik_target_space` (World / Local / Object) con `ctrl_def.set_ik_target_space` cambia lo spazio del target IK con compensazione a matrice, mantenendo la posa invariata; `ik_pole_source` (BONE / MESH) sceglie la direzione del pole dal vettore di piega della catena o dai vertici della mesh (auto-fit del pole da mesh).
- **Rig Health Score** (`v0.5.0`): `ctrl_def.rig_score` valuta il rig con 30 controlli in 5 categorie e un voto sintetico in trentesimi, gate `module-a-g5` (suite 17/17).
- **Manifest + Diff** (`v0.5.0`): `ctrl_def.manifest` scrive uno snapshot JSON strutturale del rig (registro, gerarchia, constraint, IK, deform) e `ctrl_def.manifest_diff` lo confronta con il rig attuale, avvisando del drift prima di rigenerare.
- **Handoff Animatore** (`v0.5.0`): `ctrl_def.handoff_animator` passa il rig all'animatore in un click (CTRLS visibili, DEF nascosti, MCH/ORG bloccati) e `ctrl_def.restore_rigger` ripristina in modo reversibile lo stato precedente.
- **Naming Doctor Safe Rename** (`v0.5.0`): `ctrl_def.naming_doctor` rinomina in batch i bone DEF/CTRL aggiornando in modo sicuro registry, constraint, widget shape, target IK e parent.
- **Character Picker automatico** (`v0.5.0`): `ctrl_def.character_picker` costruisce un character picker automatico con 7 gruppi (Root / Spine / Braccia / Gambe / Faccia / IK / Pole) derivati dalla gerarchia e dal mirror dei bone, gate `module-g7-g1` (suite 23/23).
- **Diagnostica Pre-Flight** (`v0.2.0`): `ctrl_def.diagnose` rileva bone `DEF` di lunghezza nulla, controparti specchiate `.L`/`.R` mancanti (con mirror attivo), collisioni di nome con bone non-DEF e avvisa quando si genera con parent `"DEF"` insieme ad A.C.T.D. (rischio Dependency Cycle).
- **Export JSON/CSV e Preset Utente** (`v0.2.0`): `ctrl_def.export_json` / `ctrl_def.export_csv` esportano il registro CTRL→DEF con i metadati del rig; `ctrl_def.save_preset` / `ctrl_def.load_preset` salvano e ricaricano le impostazioni del pannello su file `.json`.
- **Package modulare** (`v0.2.0`): la fonte di verità è il package `ctrl_def_mods\`, assemblato nel monolite installabile da `scripts/build_monolith.py` (build step, mai modificato a mano).
- **Interfaccia organizzata** (`v0.2.0`): il pannello è diviso in 3 sezioni collassabili — `1 · Setup`, `2 · Controller`, `3 · Avanzate` — più una **Guida** integrata (chiusa di default), tutte localizzate IT/EN incluse le intestazioni di sezione.
- **Parentela flessibile**: `Catena CTRL (FK)` (default), `Bone genitore`, `Root`, `Nessuno (Libero)` e `DEF stesso` — quest'ultimo **solo se i DEF non copiano i CTRL**, perché genera un Dependency Cycle con A.C.T.D.
- **Vincolo DEF→CTRL in 1 click**: il pulsante **"Vincola DEF ai CTRL (ACTD)"** (`ctrl_def.bind_actd`) entra in Pose Mode, configura ed esegue automaticamente **A.C.T.D.** se installato (sorgente = controller, destinazione = `DEF_`); senza A.C.T.D. applica gli stessi constraint `COPY_TRANSFORMS` in modo nativo (fallback standalone) dal registro proprietario.
- **Mirror L/R**: genera contemporaneamente la controparte specchiata (es. `.L` → `.R`), con preservazione dei separatori `_L`/`_R` nel mirror.
- **Preset rapidi**: *Default*, *Arto Bipede*, *Root Controller*, *Faccia*.
- **Interfaccia bilingue IT/EN**: tutte le etichette, i pannelli e le voci dei menu a tendina (`EnumProperty`) seguono la lingua della preferenza di Blender, con fallback automatico su inglese.
- **Registro JSON & rimozione pulita**: traccia ogni controller generato sull'armatura (`_ctrl_def_generated`), consentendo la rimozione totale e sicura (`ctrl_def.remove`) senza toccare il rig esistente.

---

## 📸 Video Demo (v0.5.0)

| Video | Formato | Contenuto |
|---|---|---|
| `ctrldef_033_16x9.mp4` | 1920x1080 (16:9) | Genera Controller da una catena `DEF_`, target IK su `+Y` mondo con pole automatico |
| `ctrldef_033_9x16.mp4` | 1080x1920 (9:16) | Stesso flusso, taglio verticale per Reels e Shorts |

https://github.com/user-attachments/assets/9d0838c9-7527-42fc-b88b-c362dce0fd2e

**[Taglio verticale 9:16](https://github.com/PieroFra/def-controller-auto/releases/download/v0.3.3/ctrldef_033_9x16.mp4)**

Entrambi i file sono allegati alla [release GitHub v0.3.3](https://github.com/PieroFra/def-controller-auto/releases/tag/v0.3.3).

---

## 🔄 Esempio Prima / Dopo (Nomi, Gerarchia e Attributi)

Catena di esempio (braccio sinistro) con preset *Arto Bipede (Cubo)*:

| Aspetto | Bone deformanti (prima) | Controller default (dopo) | Controller con prefisso opzionale (dopo) |
|---|---|---|---|
| **Nomi** | `DEF_arm.L` → `DEF_forearm.L` → `DEF_hand.L` | `arm.L` → `forearm.L` → `hand.L` | `CTRL_arm.L` → `CTRL_forearm.L` → `CTRL_hand.L` |
| **`use_deform`** | `True` | `False` | `False` |
| **Bone Collection** | — (rig originale) | `CTRLS` | `CTRLS` |
| **Custom shape** | — | `CTRL_DEF_SHAPE_CUBE` (condivisa) | `CTRL_DEF_SHAPE_CUBE` (condivisa) |
| **Gerarchia** | Catena deformazione | Catena FK (`forearm.L` figlio di `arm.L`) | Catena FK (`CTRL_forearm.L` figlio di `CTRL_arm.L`) |
| **Dependency Cycle con A.C.T.D.** | — | **Nessuno** | **Nessuno** |

I controller copiano posizione, orientamento e roll dei corrispondenti `DEF_`, ma non deformano la mesh (`use_deform = False`) e vivono nella Bone Collection dedicata `"CTRLS"`.

---

## 🔗 Sinergia con Auto Copy Transforms DEF (A.C.T.D.)

CTRL_DEF è il complemento naturale di **A.C.T.D.** (Auto Copy Transforms DEF):

1. Usa **CTRL_DEF** per creare i controller dell'armatura partendo dai bone `DEF_` (naming pulito, gerarchia FK, forme condivise).
2. Clicca il pulsante 1-click **"Vincola DEF ai CTRL (ACTD)"** (`ctrl_def.bind_actd`):
   - se **A.C.T.D.** è installato, CTRL_DEF entra in Pose Mode, ne configura le impostazioni (sorgente = controller, destinazione = `DEF_`) ed esegue la procedura automaticamente, senza intervento manuale;
   - in uso **standalone** (A.C.T.D. assente), applica gli stessi constraint `COPY_TRANSFORMS` in modo nativo, leggendo il registro proprietario dei controller generati.

I due addon operano in sinergia mantenendo registri e prefissi perfettamente isolati.

**Verifica empirica (Blender 5.2 LTS):** con il default *Catena CTRL (FK)* e con parent *Root*, Blender riporta **0 dependency cycle**; ruotando `arm.L` di 30° e `hand.L` di 20°, `DEF_arm.L` segue con delta 0.0000°. (Evitare la parentela *DEF stesso* insieme ad A.C.T.D.: genera cicli.)

**Repository A.C.T.D.:** https://github.com/PieroFra/auto-copy-transforms-def

---

## 🧪 Procedura di Test Headless

La suite `tests/test_ctrl_def.py` è eseguibile da terminale, su qualsiasi piattaforma, con ambiente Blender pulito (`--factory-startup`).

**Windows PowerShell:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1
```

**Linux / macOS / Bash:**

```bash
./scripts/run_tests.sh
```

**Comando diretto Blender (qualsiasi OS):**

```bash
blender --background --factory-startup --python scripts/run_ctrl_def_tests.py
```

I runner stampano il verdetto della suite: `VERDETTO: OK passati=<n> falliti=0 totale=<n>` (exit code 0) oppure `VERDETTO: FAIL ...` (exit code 1). Ultimo esito locale su Blender 5.2.0 LTS: `passati=35 falliti=0 totale=35` (vedi `tests/test_out.txt`, gate auto-suite-35-g2).

---

## 📦 Creazione dello ZIP Installabile

Il pacchetto installabile per `v0.5.0` è il **package modulare**: il monolite generato più la cartella dei moduli `ctrl_def_mods\`, senza cartella contenitrice:

```
def_controller_auto_v0.5.0.zip
├── __init__.py              (monolite generato)
├── blender_manifest.toml
├── README.md
├── LICENSE
└── ctrl_def_mods\
    ├── __init__.py
    ├── ctrl_def_generation.py
    ├── ctrl_def_i18n.py
    ├── ctrl_def_main.py
    ├── ctrl_def_operators.py
    ├── ctrl_def_properties.py
    ├── ctrl_def_registry.py
    ├── ctrl_def_shapes.py
    └── ctrl_def_ui.py
```

Lo ZIP di release contiene tra i readme solo la versione inglese `README.md` (quella italiana vive nel repository); ogni archivio è accompagnato dal relativo file `.sha256` in `dist\`.

**In alternativa:** scarica direttamente il pacchetto (con file `.sha256` di verifica) dalla pagina [Releases](https://github.com/PieroFra/def-controller-auto/releases).

**Pagina ufficiale su Blender Extensions:** <https://extensions.blender.org/add-ons/ctrl-def/> — l'estensione è approvata e installabile direttamente da Blender 4.2+: *Modifica > Preferenze > Ottieni estensioni*, cerca **"DEF Controller Auto"** e clicca *Installa*.

**Installazione in Blender:** *Modifica > Preferenze > Componenti aggiuntivi > Installa da disco...*, seleziona lo ZIP (o la cartella estratta), attiva **DEF Controller Auto** e trova il pannello nella **Sidebar 3D (tasto `N`) → scheda "DEF Ctrl"**.

---

## 🧰 Riferimento Operatori

Tutti gli id operazione vivono nel namespace `ctrl_def.*` e sono raggiungibili anche tramite la ricerca *F3*. Etichette UI e descrizioni riportate corrispondono esattamente a quanto esposto dall'addon (localizzazione dinamica IT/EN):

| Operatore `bl_idname` | Etichetta UI (IT) | Descrizione (tooltip) |
|---|---|---|
| `ctrl_def.generate` | Genera Controller | Genera i bone controller nella collezione CTRLS a partire dai bone DEF selezionati |
| `ctrl_def.create_widget` | Crea Widget | Assegna il widget selezionato in Bone Widget ai controller generati |
| `ctrl_def.bind_actd` | Vincola DEF ai CTRL (ACTD) | Vincola i bone DEF ai controller generati tramite A.C.T.D. (se attivo) o constraint COPY_TRANSFORMS nativi |
| `ctrl_def.add_ik` | Aggiungi Target IK | Crea un bone target IK e un constraint IK sulla catena di 2-3 controller selezionata in Pose Mode |
| `ctrl_def.diagnose` | Diagnostica Rig | Controlla i bone DEF selezionati prima della generazione (zero-length, mirror mancanti, collisioni, cicli) |
| `ctrl_def.apply_preset` | Applica Preset | Applica il preset selezionato alle impostazioni del pannello |
| `ctrl_def.export_json` | Esporta JSON | Esporta la mappa CTRL->DEF dell'armatura attiva in formato JSON |
| `ctrl_def.export_csv` | Esporta CSV | Esporta la mappa CTRL->DEF dell'armatura attiva in formato CSV |
| `ctrl_def.save_preset` | Salva Preset JSON | Salva le impostazioni correnti del pannello in un file preset JSON |
| `ctrl_def.load_preset` | Carica Preset JSON | Carica le impostazioni del pannello da un file preset JSON |
| `ctrl_def.remove` | Rimuovi Generati | Rimuove i controller generati, gli eventuali target IK e i relativi constraint |
| `ctrl_def.remap` | Remap Animazione | Trasferisce la posa dei controller da un rig sorgente a un rig destinazione usando la mappa DEF->CTRL (equivalente gratuito al Remap a pagamento dei competitor) |
| `ctrl_def.auto_collection` | Auto Collection | Organizza i bone nelle collection CTRLS/IK/DEF in modo idempotente |
| `ctrl_def.naming_doctor` | Naming Doctor | Rinomina in batch i bone DEF/CTRL aggiornando in modo sicuro registry, constraint, shape, IK e parent |
| `ctrl_def.character_picker` | Character Picker | Costruisce un character picker automatico con 7 gruppi (Root / Spine / Braccia / Gambe / Faccia / IK / Pole) derivati da gerarchia e mirror |

---

## ⚠️ Limitazioni Note e Roadmap (post `v0.5.0`)

- I workflow supportano le catene **FK**; l'IK è coperto dal target rapido su catene di 2‑3 controller (`ctrl_def.add_ik`), mentre lo **switch automatico IK/FK** è previsto per `v2`.
- I widget si appoggiano all'estensione opzionale **Bone Widget** (il pannello offre il link diretto di installazione): nessuna libreria di widget integrata.
- La verifica automatizzata copre generazione, naming, gerarchia FK, preset, bind A.C.T.D., target IK, diagnostica pre-flight, export JSON/CSV, preset utente e registro; la UI completa resta soggetta a verifica interattiva manuale.

---

## 📋 Changelog

### `v0.4.0` — Catena IK, Space Switching, Snap e Bake IK-FK
- **Catena IK**: `ik_chain_length` (1-8) sulla catena di controller selezionata.
- **Space switching**: `ik_target_space` (World / Local / Object) con `ctrl_def.set_ik_target_space`, compensazione a matrice per mantenere la posa invariata.
- **Snap e Bake IK->FK**: `ctrl_def.snap_ik_to_fk` e `ctrl_def.bake_ik_to_fk` per riportare la posa IK sui controller FK, con bake su keyframe e rimozione del constraint.
- **Pole da mesh**: `ik_pole_source` (BONE / MESH) con auto-fit della direzione del pole dai vertici della mesh.
- Gate di verifica: `module-c-g1`.

### `v0.3.0` — Auto Rig Layers (DEF / MCH / ORG / CTRL)
- **Pipeline di rigging multi-livello**: `DEF -> ORG -> MCH -> CTRL`, `DEF -> MCH -> CTRL`, `MCH -> ORG`, `ORG -> CTRL` e `Custom` (prima solo `DEF -> CTRL` diretta).
- **Livelli intermedi automatici**: Bone Collection `MCH` e `ORG` create e nascoste automaticamente, con lock di Location/Rotation/Scale (`lock_mch_org`).
- **Target IK a +Y mondo**: allineamento `ik_align_world_y = True` (`roll = 0.0`) in cima alla catena + pole target automatico (`ik_create_pole`) lungo il vettore di piega gomito/ginocchio.
- **Vincolatura multi-hop**: `ctrl_def.bind_actd` costruisce l'intera catena `DEF <- ORG <- MCH <- CTRL` con zero Dependency Cycle.

### `v0.2.0`
- **Package modulare**: la fonte di verità è il package `ctrl_def_mods\` (9 moduli) assemblato nel monolite installabile da `scripts/build_monolith.py`.
- **Pannello ridisegnato**: 3 sezioni collassabili (`1 · Setup`, `2 · Controller`, `3 · Avanzate` — `3 · Advanced` in EN) più una `Guida` integrata in 5 passi.
- **Integrazione Bone Widget**: `ctrl_def.create_widget` delega la creazione dei widget all'estensione Bone Widget, con link diretto di installazione se assente.
- **Target IK rapido**: `ctrl_def.add_ik` sulle catene selezionate di 2‑3 controller (`use_deform = False`, zero Dependency Cycle).
- **Diagnostica Pre-Flight**: `ctrl_def.diagnose` (bone DEF di lunghezza nulla, specchiate `.L`/`.R` mancanti, collisioni di nome, avviso parent "DEF" con A.C.T.D.).
- **Export JSON/CSV e preset utente**: `ctrl_def.export_json`, `ctrl_def.export_csv`, `ctrl_def.save_preset`, `ctrl_def.load_preset` (round-trip testato).
- Orientamento delle custom shape (`shape_rot` → `custom_shape_rotation_euler`).
- Bone Collection dedicata ai controller rinominata `"CTRL"` → `"CTRLS"`.

### `v0.1.2`
- Custom shape condivise per tipo (`CTRL_DEF_SHAPE_*`): una sola mesh per forma, riutilizzata da tutti i controller.
- Localizzazione dinamica completa IT/EN: etichette, pannelli e pulsanti seguono la lingua di Blender, con fallback automatico su inglese (`tr()`).
- Localizzazione dinamica estesa anche ai **menu a tendina** (`EnumProperty`): forma, colore, parentela e preset usano callback `_items_*` che ritraducono le voci a ogni disegno del pannello.
- Scomposizione interna dell'operatore di generazione in funzioni helper (`_collect_def_bones`, `_create_ctrl_edit_bones`, `_assign_ctrl_parents`, `_configure_ctrl_pose_bones`) per un flusso più leggibile e verificabile.
- Etichette UI compatte senza troncamento IT/EN.
- Preservazione separatori `_L`/`_R` nel mirror.
- Script di test multipiattaforma (`scripts/run_tests.ps1` e `.sh`).
- Screenshot/GIF prive di splash screen.
- 10 nuovi test sui casi limite.

### `v0.1.1`
- Naming pulito senza prefisso di default.
- Gerarchia `Catena CTRL (FK)` a zero Dependency Cycle.
- Operatore 1-click `ctrl_def.bind_actd`.

### `v0.1.0`
- Release iniziale MVP.

---

## 📄 Licenza

GPL-3.0-or-later — vedi il file [LICENSE](LICENSE).


---

## Parte della Rigging Suite

CTRL_DEF è totalmente standalone (zero dipendenze), ma si unifica automaticamente nella scheda **Rigging Suite** quando installato insieme a:

- **[BBone to Bones](https://github.com/PieroFra/bbone-to-bones)** - converte le Bendy Bones in catene di ossa standard esportabili su Unity, Unreal e Godot, con Revert non distruttivo.
- **[A.C.T.D.](https://github.com/PieroFra/auto-copy-transforms-def) (Auto Copy Transforms DEF)** - riusa le ossa come sorgenti di trasformazioni non distruttive con constraint auto-prefissati.

Quale passaggio del tuo workflow di rigging ti rallenta ancora? Apri una issue con il passaggio che vuoi automatizzare.
