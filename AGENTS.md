# AGENTS.md — CTRL_DEF (Controller Automatici da DEF)

Questo file è l'unica fonte operativa per gli agenti che lavorano su questo progetto.
Rispettala alla lettera.

## 0. DOVE SIAMO
Workspace: C:\Users\checc\Desktop\BLENDER ADDONS\
Progetto: C:\Users\checc\Desktop\BLENDER ADDONS\CTRL_DEF\

```
CTRL_DEF\
   __init__.py      sorgente attiva (single file, bl_info 0.3.0, categoria Rigging)
   tests\           test headless
   .opencode\       script runner
   AGENTS.md        questo file
   README.md        documentazione
   .gitignore
```

Non creare file fuori da CTRL_DEF\.

## 1. SCOPE — COSA SI PUÒ TOCCARE
- Architettura approvata "Moduli + Build Step": la **fonte di verità** sono i moduli
  CTRL_DEF\ctrl_def_mods\*.py, assemblati nel monolite installabile CTRL_DEF\__init__.py
  da CTRL_DEF\scripts\build_monolith.py (eseguito automaticamente da `verify.ps1` / `gate.ps1`).
- Si modificano i moduli, **non** il monolite a mano (che si rigenera con la build).
  Il monolite `__init__.py` resta il solo artefatto installabile in Blender.
- Non creare actd_build\ né moduli fuori da ctrl_def_mods\.

## 2. VINCOLI DI PROGETTO (sempre validi)
- Commenti in italiano.
- Non rinominare bl_info name, categoria Rigging, né id ctrl_def.* (operatori, pannelli, proprietà).
- Non rimuovere pannelli, operatori o proprietà esposte nella UI.
- Token default: DEF_ / CTRL_.
- Registry JSON sull'armatura (_read_registry / _write_registry / _mark_generated / _is_generated / _forget_generated / _prune_registry).
- Ogni PropertyGroup usata da CollectionProperty deve comparire in _classes prima della classe che la usa.
- Si modifica un modulo alla volta (qui c'è un solo modulo).

## 3. CICLO DI VERIFICA
| Cosa | Comando |
|---|---|
| test | powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\gate.ps1 |
| mappa | .opencode\INDEX.md (generato da verify.ps1) |

Nota: il probe UI sarà introdotto in Fase 5 (lo script non è ancora presente).

Atteso: suite completa 100% verde (5 controlli e2e, compatibilità ACTD, preset), zero fallimenti.

Il verdetto lo dà il codice: `gate.ps1` esegue `verify.ps1`, si auto-audita
contro `.opencode\metrics.jsonl` e stampa una sola riga
(`VERIFY_OK | passed=5 | failed=0 | ...` oppure `VERIFY_FAIL | reason=...`).
Gli agenti riportano quella riga, non la compongono.
Configurazione del progetto: `.opencode\verify.config.psd1`.

## 4. ROADMAP
Piano a fasi verso **v0.2.0**: dettaglio completo in `docs\ROADMAP.md` (fonte di verità).
Regola: un modulo alla volta, con verifica `gate.ps1` a ogni fase.

- **Fase A (COMPLETATA):** Architettura Moduli + Build Step (9 moduli in
  `ctrl_def_mods\*.py`, builder `scripts\build_monolith.py`, `build=IN_SYNC`)
  e I18N dinamica IT/EN incluse le `EnumProperty` (`_items_*`).
- **Fase B:** Diagnostica Pre-Flight `ctrl_def.diagnose`
  (`_diagnose_def_selection`: bone DEF con lunghezza < 1e-6, specchiate .L/.R
  mancanti con mirror=True, collisioni nome non-DEF, avviso parent "DEF" con
  ACTD). Test in `tests\test_ctrl_def.py`.
- **Fase C:** Orientamento custom shape: `shape_rot` su
  `CTRLDEF_PG_settings` → `pbone.custom_shape_rotation_euler`.
- **Fase D:** Export mappa CTRL→DEF (`ctrl_def.export_json` / `.export_csv`)
  + preset utente JSON, round-trip testato.
- **Fase E:** Catena IK rapida opzionale (target + pole, `use_deform=False`)
  e rilascio `v0.3.0` (GIF demo, bump 0.2.0, ZIP, GitHub + Extensions).

## 5. RISCHI
- Scope creep: IK/FK rimandati a v2.
- Orientamento bone: gestire roll e asse locale fin dall'MVP.
- Ordine consigliato: ACTD → UV → controller.

## 6. SQUADRA E SKILL GLOBALI

- **Coder:** scrive il codice in `__init__.py` e i test headless in `tests\`.
- **Repo-Ops:** documentazione, config, packaging ed esperimenti in `_esperimenti\`.
- **Publisher** (modello Vision, scrittura dev-to-dev): prepara `docs/PROMO.md` e
  `docs/FEEDBACK.md`, verifica visivamente con `read` che GIF e screenshot siano dritti
  prima dell'upload, scrive con zero em-dash, pubblica via Chrome CDP con la regola
  Prepare & Hand-off. Permesso `edit: deny` su `*.py`.
- **Skill globali** (in `~\.config\opencode\skills\`, una copia per tutti gli addon):
  `addon-publisher` (pubblicazione multi-canale: Blender Extensions, Blender Artists,
  Reddit), `browser-personale` (pilota il Chrome personale via CDP, porta 9222, login
  già attivi) e `blender-gui-capture` (screenshot PNG, crop della Sidebar IT/EN e GIF
  animate nella GUI reale di Blender, ricetta one-shot deterministica).
