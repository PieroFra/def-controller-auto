# Changelog — CTRL_DEF (Auto Rig Layers)

Tutte le modifiche notevoli di questo progetto verranno documentate in questo
file. Il formato si basa su [Keep a Changelog](https://keepachangelog.com/).

## [0.3.3] - 2026-11-13

### Changed
- Packaging: repeatable package_release.ps1 build with verified clean install in an isolated Blender profile.
- Added a new end-to-end check covering the controller bone rename path.

## [0.3.2] - 2026-11-05

### Fixed
- Packaging: zip con `__init__.py` completo e package `ctrl_def_mods` incluso.

## [0.3.1] - 2026-11-05

### Fixed
- Bump di versione per nuovo upload su Blender Extensions (nessuna modifica funzionale rispetto a 0.3.0).

## [0.3.0] - 2026-11-04

### Added
- Pipeline multi-layer di rigging (`DEF -> ORG -> MCH -> CTRL` e varianti: `DEF -> MCH -> CTRL`, `MCH -> ORG`, `ORG -> CTRL`, `Custom`) con collezioni `ORG`/`MCH` automatiche, auto-nascoste e con lock di Location/Rotation/Scale (`lock_mch_org`).
- Target IK allineati al World `+Y` (`ik_align_world_y = True`, `roll = 0.0`) in punta alla catena, con Pole Target automatico (`ik_create_pole`) lungo il vettore di piega gomito/ginocchio.
- Pulsante 1-click "Vincola DEF ai CTRL (ACTD)" (`ctrl_def.bind_actd`): catena di constraint multi-hop (`DEF <- ORG <- MCH <- CTRL`) con zero Dependency Cycle; usa A.C.T.D. se presente, altrimenti applica constraint `COPY_TRANSFORMS` nativi dal registro proprietario.
- Creazione bone controller da bone con prefisso `DEF_`: naming pulito senza prefisso (standard Blender/Rigify) o prefisso personalizzabile (es. `CTRL_`), orientamento e roll identici, gerarchia predefinita "Catena CTRL (FK)" con `use_deform = False`.
- Assegnazione automatica di custom shape geometriche (Cerchio, Cubo, Sfera, Freccia, Croce) e colori palette tema Blender (Rosso, Verde, Blu).
- Raggruppamento automatico nella Bone Collection `CTRL` con scelta della gerarchia di parentela (Catena CTRL FK, Bone genitore, Root, Nessuno, DEF stesso).
- Mirroring automatico delle coppie simmetriche (`.L` / `.R`).
- Tracciamento nel registro JSON sull'armatura con rimozione pulita in un click.
- Preset veloci integrati (Default, Arto Bipede, Root Controller, Faccia).
- Piena sinergia con Auto Copy Transforms DEF (A.C.T.D.) e pacchetto modulare `ctrl_def_mods\`.
