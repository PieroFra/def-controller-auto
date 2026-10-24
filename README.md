# CTRL_DEF — Controller Automatici da DEF

Addon per Blender (versione >= 4.2 LTS e 5.x, categoria **Rigging**) che genera rapidamente bone controller tracciati, colorati e dotati di forme personalizzate a partire dalla catena di deformazione (`DEF_`).

---

## 🆕 Novità nella 0.1.1

- **Naming pulito di default**: i controller si chiamano come i bone DEF senza prefisso (`DEF_hand.L` → `hand.L`, standard Blender/Rigify); resta disponibile il prefisso personalizzabile (es. `CTRL_`).
- **Gerarchia di default "Catena CTRL (FK)"**: ricrea l'albero FK tra i controller con `use_deform = False` e **zero Dependency Cycle** (verificato anche con parent `Root`).
- **Pulsante 1-click "Vincola DEF ai CTRL (ACTD)"** (`ctrl_def.bind_actd`): configura ed esegue automaticamente **A.C.T.D.** se presente, altrimenti applica i constraint `COPY_TRANSFORMS` nativi.

---

## 🚀 Caratteristiche Principali

- **Naming Pulito (default)**: i controller si chiamano come i bone DEF senza prefisso (`DEF_hand.L` → `hand.L`, standard Blender/Rigify); con il campo *Prefisso Controller* si ottiene il naming classico (es. `CTRL_` → `CTRL_hand.L`).
- **Generazione Istantanea**: crea i controller identici per posizione, orientamento e roll ai rispettivi `DEF_`, con `use_deform = False` (non deformano la mesh).
- **Gerarchia di Default "Catena CTRL (FK)"**: ricrea l'albero FK tra i controller (`forearm.L` figlio di `arm.L`), rendendoli indipendenti dai DEF: **zero Dependency Cycle** con A.C.T.D., anche con parent `Root`.
- **Forme Personalizzate (Custom Shapes)**: crea e assegna automaticamente mesh wireframe (Cerchio, Cubo, Sfera, Freccia, Croce) con scala regolabile.
- **Bone Collection Dedicata**: isola automaticamente tutti i controller nella collezione `"CTRL"`.
- **Palette Colori Tematiche**: assegna rapidamente colorazioni visive (Rosso, Verde, Blu) conformi al tema di Blender.
- **Parentela Flessibile**: `Catena CTRL (FK)` (default), `Bone genitore`, `Root`, `Nessuno (Libero)` e `DEF stesso` — quest'ultimo **solo se i DEF non copiano i CTRL**, perché genera un Dependency Cycle con A.C.T.D.
- **Vincolo DEF→CTRL in 1 Click**: il pulsante **"Vincola DEF ai CTRL (ACTD)"** (`ctrl_def.bind_actd`) configura ed esegue automaticamente **A.C.T.D.** se installato (sorgente = controller, destinazione = `DEF_`); senza A.C.T.D. applica gli stessi constraint `COPY_TRANSFORMS` in modo nativo dal registro proprietario.
- **Mirror L/R**: genera contemporaneamente la controparte specchiata (es. `.L` $\rightarrow$ `.R`).
- **Preset Rapidi**: pulsanti 1-click per *Arto Bipede*, *Root Controller*, *Faccia* e *Default*.
- **Registro JSON & Rimozione Pulita**: traccia ogni controller generato sull'armatura (`_ctrl_def_generated`), consentendo la rimozione totale e sicura senza toccare il rig esistente.

---

## 📸 Anteprime

![Armatura con bone DEF selezionati e pannello DEF Ctrl](docs/images/01_before_def_bones.png)

*Figura 1 — Armatura con i bone `DEF_` selezionati (nomi e assi visibili) e il pannello **Controller DEF** aperto nella Sidebar (N) > scheda **DEF Ctrl**.*

![Controller generati in Pose Mode](docs/images/02_after_ctrl_generated.png)

*Figura 2 — Dopo **Genera Controller** con preset **Arto Bipede** (Cubo/Rosso/Mirror): forme personalizzate colorate in Pose Mode e box stato aggiornato (`DEF trovati: 3 | CTRL generati: 3`).*

![Demo animata: rotazione della catena di controller](docs/images/demo.gif)

*Figura 3 — Demo animata (5 frame): onda di rotazione sulla catena di controller generati.*

---

## 🔗 Integrazione con A.C.T.D. (Auto Copy Transforms DEF)

Questo addon è progettato per completare la pipeline di **A.C.T.D.**:
1. Usa **CTRL_DEF** per creare i controller dell'armatura partendo dai bone `DEF_` (naming pulito, gerarchia FK).
2. Clicca **"Vincola DEF ai CTRL (ACTD)"**: se **A.C.T.D.** è installato, CTRL_DEF lo configura ed lo esegue automaticamente (nessuna impostazione manuale) creando i constraint *Copy Transforms* dai `DEF_` ai controller; in uso standalone applica gli stessi constraint `COPY_TRANSFORMS` in modo nativo.

I due addon operano in sinergia e mantengono i registri e i prefissi perfettamente isolati.

**Verifica empirica (Blender 5.2 LTS, esperimento esplorativo non-gate):** con il default *Catena CTRL (FK)* e con *Root* Blender riporta **0 dependency cycle**; ruotando `arm.L` di 30° e `hand.L` di 20°, `DEF_arm.L` ruota di 30.0° con delta 0.0000°. (Evitare la parentela *DEF stesso* insieme ad A.C.T.D.: genera cicli.)

**Repository A.C.T.D.:** https://github.com/PieroFra/auto-copy-transforms-def

---

## 📦 Installazione

1. In Blender, apri **Modifica > Preferenze > Componenti aggiuntivi (Add-ons)**.
2. Clicca sulla freccia in alto a destra e seleziona **Installa da disco...**.
3. Seleziona il pacchetto o la cartella `CTRL_DEF`.
4. Troverai il pannello nella **Sidebar 3D (tasto N) > scheda "DEF Ctrl"**.