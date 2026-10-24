# CTRL_DEF — Controller Automatici da DEF

Addon per Blender (versione >= 4.2 LTS e 5.x, categoria **Rigging**) che genera rapidamente bone controller tracciati, colorati e dotati di forme personalizzate a partire dalla catena di deformazione (`DEF_`).

---

## 🚀 Caratteristiche Principali

- **Generazione Istantanea**: crea i bone `CTRL_` identici per posizione e roll ai rispettivi `DEF_`.
- **Forme Personalizzate (Custom Shapes)**: crea e assegna automaticamente mesh wireframe (Cerchio, Cubo, Sfera, Freccia, Croce) con scala regolabile.
- **Bone Collection Dedicata**: isola automaticamente tutti i controller nella collezione `"CTRL"`.
- **Palette Colori Tematiche**: assegna rapidamente colorazioni visive (Rosso, Verde, Blu) conformi al tema di Blender.
- **Gerarchia di Parentela Flessibile**:
  - `DEF stesso`: il controller guida direttamente il DEF.
  - `Bone genitore`: il controller segue la catena genitrice del DEF.
  - `Root`: il controller viene collegato alla radice dell'armatura.
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
1. Usa **CTRL_DEF** per creare i controller dell'armatura partendo dai bone `DEF_`.
2. Usa **A.C.T.D.** per vincolare automaticamente con *Copy Transforms* i bone `DEF_` sui nuovi controller `CTRL_` appena generati.

I due addon operano in sinergia e mantengono i registri e i prefissi perfettamente isolati.

**Repository A.C.T.D.:** https://github.com/PieroFra/auto-copy-transforms-def

---

## 📦 Installazione

1. In Blender, apri **Modifica > Preferenze > Componenti aggiuntivi (Add-ons)**.
2. Clicca sulla freccia in alto a destra e seleziona **Installa da disco...**.
3. Seleziona il pacchetto o la cartella `CTRL_DEF`.
4. Troverai il pannello nella **Sidebar 3D (tasto N) > scheda "DEF Ctrl"**.