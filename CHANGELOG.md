# Changelog — CTRL_DEF (Auto Rig Layers)

Tutte le modifiche notevoli di questo progetto verranno documentate in questo
file. Il formato si basa su [Keep a Changelog](https://keepachangelog.com/).

## [0.5.1] - 2026-11-22

### Fixed
- Rig Score box and Naming Doctor work when a mesh is active (armature resolved via modifier/parent/selection).
- Empty rename_map is a successful no-op.
- Hardening of `_resolve_armature`/`_nd_validate_map`/mode restore.

## [0.5.0] - 2026-11-18

### Added
- Rig Health Score (`ctrl_def.rig_score`): 30 checks in 5 categories with a synthetic score out of 30.
- Remap (`ctrl_def.remap`): transfer controller poses from a source rig to a target rig using the DEF->CTRL mapping.
- Manifest + Diff (`ctrl_def.manifest` / `ctrl_def.manifest_diff`): structural JSON snapshot of the rig plus a diff command that warns about drift before regenerating.
- Auto-Collection (`ctrl_def.auto_collection`): automatic controller collections.
- Handoff Animator (`ctrl_def.handoff_animator`) and Restore Rigger (`ctrl_def.restore_rigger`): one-click handoff to the animator with a reversible restore.
- Naming Doctor Safe Rename (`ctrl_def.naming_doctor`): batch rename of DEF/CTRL bones with safe updates.
- Character Picker auto (`ctrl_def.character_picker`): automatic character picker with 7 groups.

### Fixed
- 5 post-functional-test fixes (manifest_diff baseline order and CANCELLED state, rig_score, auto_collection, character_picker Face/IK keywords, i18n).
- Complete i18n of the UI labels.
- Rig Health Score: added the 30th real check (custom shape on controllers, CONSEGNA category); now 30 measured voices out of /30, gate fix6-g1.

### Changed
- GUI redesign (v0.5.0): ergonomic reorganization of the panel.

### Fixed
- Depsgraph warning fix.

### Verified
- Gates: fix6-g1 (rig_score 30th check), harden-g2 (registry JSON dict/batch O(N) hardening, try/finally mode_set, bake_ok guard, 4.2/5.2 selection compatibility, empty collection cleanup), opt-gui-g2 (registry cache O(1), depsgraph warning fix, ergonomic GUI redesign v0.5.0), coll-polish-g2 (automatic DEF collection on generate and IK collection on add_ik, hide handoff on MCH/ORG bones, pruning of empty collections on remove, GUI operator ctrl_def.character_picker), auto-suite-35-g2 (test count alignment 35, ExpectedTotal in verify config), zero-leak-g1 (dependency cycle fix on `parent=ROOT` with multi-layer pipelines, orphaned widget Mesh datablock cleanup). 35 tests green.

### Tests
- 35 tests green.

## [0.4.0] - 2026-11-16

### Added
- Snap IK to FK: snap the IK chains back onto the FK pose in one click.
- Bake IK to FK: bake the IK result onto the FK controls with keyframes.
- Space switching for IK targets: World, Local and Object target spaces.
- IK chains up to 8 bones per chain.
- Pole direction source (`ik_pole_source`): BONE (default, bend vector of the chain) or MESH (pole direction derived from the mesh vertices).
- Remap (`ctrl_def.remap`): transfer controller poses from a source rig to a target rig using the DEF->CTRL mapping, free equivalent of the paid Remap module of competitors.
- Manifest + Diff (`ctrl_def.manifest` / `ctrl_def.manifest_diff`): structural JSON snapshot of the rig (registry, hierarchy, constraints, IK, deform) plus a diff command that warns about drift before regenerating.
- Auto Collection (`ctrl_def.auto_collection`): organize bones into the CTRLS/IK/DEF collections idempotently.
- Handoff Animator (`ctrl_def.handoff_animator`) and Restore Rigger (`ctrl_def.restore_rigger`): one-click handoff to the animator (CTRLS visible, DEF hidden, MCH/ORG locked) with a reversible restore.
- Naming Doctor Safe Rename (`ctrl_def.naming_doctor`): batch rename of DEF/CTRL bones, safely updating the registry, constraints, widget shapes, IK targets and parents.

- Character Picker auto (`ctrl_def.character_picker`): automatic character picker with 7 groups (Root / Spine / Arms / Legs / Face / IK / Pole) derived from the bone hierarchy and mirror naming.

### Fixed
- manifest_diff (gate fix1-g1): baseline-order of the manifest no longer produces a false drift; CANCELLED operation state handled correctly.
- rig_score (gate fix2-g1): eliminated false positive scores in sections 1.5, 5.1, 5.2 and 3.5.
- auto_collection (gate fix3-g1): MCH/ORG bones handled correctly and unassignment idempotent.
- character_picker (gate fix4-g1): Italian keyword for the head, Face group assignment and IK suffix recognized.
- i18n (gate fix5-g1): 22 missing translation keys added to the Italian and English dictionaries; new `test_i18n_complete` guards the coverage.

### Verified
- Gates: snap-f-g3, bake-g3, space-h-g2, module-c-g1, module-a-g5, module-b-g2, module-c3-g2, module-d4-g3, module-e5-g3, module-f6-g3, module-g7-g1, fix1-g1 (manifest_diff), fix2-g1 (rig_score), fix3-g1 (auto_collection), fix4-g1 (character_picker), fix5-g1 (i18n). 28 tests green.

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
