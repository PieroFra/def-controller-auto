# CTRL_DEF — DEF Controller Auto

[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%E2%80%94%205.2%2B-blueviolet)](https://www.blender.org)
[![Category](https://img.shields.io/badge/Category-Rigging-orange)](https://extensions.blender.org/)
[![Version](https://img.shields.io/badge/version-0.1.2-brightgreen)](https://github.com/PieroFra/def-controller-auto/releases)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)](LICENSE)

Genera in un click bone controller tracciati, colorati e dotati di **custom shape condivise** a partire dalla catena di deformazione (`DEF_`), con gerarchia FK pulita, zero Dependency Cycle e sinergia 1-click con **A.C.T.D.** (Auto Copy Transforms DEF).

| | |
|---|---|
| **Compatibilità** | **Blender 4.2 LTS — 5.2+** |
| **Categoria** | **Rigging** |
| **Versione** | **0.1.2** |
| **Autore** | **Pierfrancesco Diodato** |
| **Tipo** | Add-on (ZIP installabile o cartella) |
| **Licenza** | GPL-3.0-or-later |

---

## ⚡ Quick Start (in meno di 60 secondi — 4 passaggi)

1. Seleziona l'armatura, entra in **Edit Mode** (`Tab`) e seleziona i bone con prefisso `DEF_`.
2. Apri la Sidebar (`N`) → scheda **DEF Ctrl** e scegli un preset (es. *Arto Bipede (Cubo)*) o personalizza forma/colore/scala.
3. Clicca **Genera Controller** (`ctrl_def.generate`): vengono creati i controller puliti (`hand.L`) in catena FK nella Bone Collection `"CTRL"`.
4. Clicca **Vincola DEF ai CTRL (ACTD)** (`ctrl_def.bind_actd`): i bone `DEF_` copiano istantaneamente le trasformazioni dei controller in Pose Mode senza Dependency Cycle.

> **Risultato:** ruoti `arm.L` in Pose Mode e `DEF_arm.L` lo segue in tempo reale — la mesh si deforma tramite i DEF, il controllo passa dai controller.

---

## 🚀 Caratteristiche Principali

- **Naming pulito di default**: i controller si chiamano come i bone DEF senza prefisso (`DEF_hand.L` → `hand.L`, standard Blender/Rigify); con il campo *Prefisso Controller* si ottiene il naming classico (es. `CTRL_` → `CTRL_hand.L`).
- **Custom shape condivise per tipo** (`v0.1.2`): le forme wireframe sono oggetti condivisi (`CTRL_DEF_SHAPE_CIRCLE`, `CTRL_DEF_SHAPE_CUBE`, `CTRL_DEF_SHAPE_SPHERE`, `CTRL_DEF_SHAPE_ARROW`, `CTRL_DEF_SHAPE_CROSS`) — una sola mesh per tipo, riutilizzata da tutti i controller.
- **Generazione istantanea**: controller identici per posizione, orientamento e roll ai rispettivi `DEF_`, con `use_deform = False` (non deformano la mesh).
- **Gerarchia di default "Catena CTRL (FK)"**: ricrea l'albero FK tra i controller (`forearm.L` figlio di `arm.L`), rendendoli indipendenti dai DEF: **zero Dependency Cycle** con A.C.T.D., anche con parent `Root`.
- **Bone Collection dedicata**: isola automaticamente tutti i controller nella collezione `"CTRL"`.
- **Palette colori tematiche**: assegnazione rapida conforme al tema di Blender (Rosso, Verde, Blu).
- **Parentela flessibile**: `Catena CTRL (FK)` (default), `Bone genitore`, `Root`, `Nessuno (Libero)` e `DEF stesso` — quest'ultimo **solo se i DEF non copiano i CTRL**, perché genera un Dependency Cycle con A.C.T.D.
- **Vincolo DEF→CTRL in 1 click**: il pulsante **"Vincola DEF ai CTRL (ACTD)"** (`ctrl_def.bind_actd`) entra in Pose Mode, configura ed esegue automaticamente **A.C.T.D.** se installato (sorgente = controller, destinazione = `DEF_`); senza A.C.T.D. applica gli stessi constraint `COPY_TRANSFORMS` in modo nativo (fallback standalone) dal registro proprietario.
- **Mirror L/R**: genera contemporaneamente la controparte specchiata (es. `.L` → `.R`), con preservazione dei separatori `_L`/`_R` nel mirror.
- **Preset rapidi**: *Default*, *Arto Bipede*, *Root Controller*, *Faccia*.
- **Registro JSON & rimozione pulita**: traccia ogni controller generato sull'armatura (`_ctrl_def_generated`), consentendo la rimozione totale e sicura (`ctrl_def.remove`) senza toccare il rig esistente.

---

## 📸 Anteprime (Screenshots & Demo GIF)

| File | Contenuto |
|---|---|
| `docs/images/01_before_def_bones.png` | Armatura con i bone `DEF_` selezionati e il pannello **DEF Ctrl** aperto nella Sidebar (`N`). |
| `docs/images/02_after_ctrl_generated.png` | Dopo **Genera Controller** con preset *Arto Bipede (Cubo/Rosso/Mirror)*: controller colorati in Pose Mode. |
| `docs/images/demo.gif` | Demo animata: onda di rotazione sulla catena di controller generati. |

![Armatura con bone DEF selezionati e pannello DEF Ctrl](docs/images/01_before_def_bones.png)

*Figura 1 — Armatura con i bone `DEF_` selezionati (nomi e assi visibili) e il pannello **Controller DEF** aperto nella Sidebar (`N`) → scheda **DEF Ctrl**.*

![Controller generati in Pose Mode](docs/images/02_after_ctrl_generated.png)

*Figura 2 — Dopo **Genera Controller** con preset **Arto Bipede** (Cubo/Rosso/Mirror): forme personalizzate condivise colorate in Pose Mode e box di stato aggiornato (`DEF trovati: 3 | CTRL generati: 3`).*

![Demo animata: rotazione della catena di controller](docs/images/demo.gif)

*Figura 3 — Demo animata: onda di rotazione sulla catena di controller generati.*

---

## 🔄 Esempio Prima / Dopo (Nomi, Gerarchia e Attributi)

Catena di esempio (braccio sinistro) con preset *Arto Bipede (Cubo)*:

| Aspetto | Bone deformanti (prima) | Controller default (dopo) | Controller con prefisso opzionale (dopo) |
|---|---|---|---|
| **Nomi** | `DEF_arm.L` → `DEF_forearm.L` → `DEF_hand.L` | `arm.L` → `forearm.L` → `hand.L` | `CTRL_arm.L` → `CTRL_forearm.L` → `CTRL_hand.L` |
| **`use_deform`** | `True` | `False` | `False` |
| **Bone Collection** | — (rig originale) | `CTRL` | `CTRL` |
| **Custom shape** | — | `CTRL_DEF_SHAPE_CUBE` (condivisa) | `CTRL_DEF_SHAPE_CUBE` (condivisa) |
| **Gerarchia** | Catena deformazione | Catena FK (`forearm.L` figlio di `arm.L`) | Catena FK (`CTRL_forearm.L` figlio di `CTRL_arm.L`) |
| **Dependency Cycle con A.C.T.D.** | — | **Nessuno** | **Nessuno** |

I controller copiano posizione, orientamento e roll dei corrispondenti `DEF_`, ma non deformano la mesh (`use_deform = False`) e vivono nella Bone Collection dedicata `"CTRL"`.

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

I runner stampano il verdetto della suite: `VERDETTO: OK passati=<n> falliti=0 totale=<n>` (exit code 0) oppure `VERDETTO: FAIL ...` (exit code 1). Ultimo esito locale su Blender 5.2.0 LTS: `passati=5 falliti=0 totale=5` (vedi `tests/test_out.txt`).

---

## 📦 Creazione dello ZIP Installabile

Il pacchetto installabile contiene esattamente 4 file alla radice dello ZIP (nessuna cartella contenitrice):

```
def_controller_auto_v0.1.2.zip
├── __init__.py
├── blender_manifest.toml
├── README.md
└── LICENSE
```

**Da terminale (Windows PowerShell):**

```powershell
Compress-Archive -Path __init__.py, blender_manifest.toml, README.md, LICENSE -DestinationPath dist\def_controller_auto_v0.1.2.zip
```

**In alternativa:** scarica direttamente il pacchetto (con file `.sha256` di verifica) dalla pagina [Releases](https://github.com/PieroFra/def-controller-auto/releases).

**Installazione in Blender:** *Modifica > Preferenze > Componenti aggiuntivi > Installa da disco...*, seleziona lo ZIP (o la cartella estratta), attiva **DEF Controller Auto** e trova il pannello nella **Sidebar 3D (tasto `N`) → scheda "DEF Ctrl"**.

---

## ⚠️ Known Limitations & Roadmap (`v0.2.0`)

- Attualmente supporta catene **FK** (IK/FK switch automatico previsto in `v0.2.0`).
- In `v0.2.0` è prevista la modularizzazione interna (`properties.py`, `registry.py`, `shapes.py`, `generation.py`, `binding.py`, `panel.py`) con build step verso il monolite.
- La verifica automatizzata copre la generazione, il naming, la gerarchia FK, i preset, il bind A.C.T.D. e gli elementi di registrazione; la UI completa resta soggetta a verifica interattiva manuale.

---

## 📋 Changelog

### `v0.1.2`
- Custom shape condivise per tipo (`CTRL_DEF_SHAPE_*`): una sola mesh per forma, riutilizzata da tutti i controller.
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
