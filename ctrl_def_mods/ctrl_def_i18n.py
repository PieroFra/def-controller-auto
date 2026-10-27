# Modulo I18N: tabelle IT/EN e funzione tr().
import bpy

# ===========================================================================
# Internazionalizzazione (IT / EN)
# ===========================================================================
_I18N = {
    "it": {
        "panel.label": "Controller DEF",
        "panel.prefix_def": "DEF",
        "panel.prefix_ctrl": "CTRL",
        "panel.shape": "Forma",
        "panel.scale": "Scala",
        "panel.shape_rot": "Rotazione Shape",
        "panel.color": "Colore",
        "panel.parent": "Genitore",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Stato Armatura",
        "panel.export": "Esporta / Preset",
        "panel.ik": "Target IK",
        "stats.line": "DEF: %d  |  CTRL: %d",
        "op.generate": "Genera Controller",
        "op.create": "Crea Controller",
        "op.bind_actd": "Vincola DEF ai CTRL (ACTD)",
        "op.remove": "Rimuovi Generati",
        "op.apply_preset": "Applica Preset",
        "op.diagnose": "Diagnostica Rig",
        "op.add_ik": "Aggiungi Target IK",
        "op.export_json": "Esporta JSON",
        "op.export_csv": "Esporta CSV",
        "op.save_preset": "Salva Preset JSON",
        "op.load_preset": "Carica Preset JSON",
        "msg.created": "Controller creati",
        "msg.removed": "Controller rimossi",
        "msg.no_armature": "Nessuna armatura attiva",
        "msg.no_def_bones": "Nessun bone DEF selezionato",
        "msg.no_registered": "Nessun controller registrato",
        "msg.bound": "Vincoli DEF/CTRL",
        "msg.diag_ok": "Diagnostica OK: nessun problema rilevato",
        "msg.diag_issues": "Problemi rilevati",
        "msg.ik_created": "Target IK creati",
        "msg.no_ik_chain": "Nessuna catena di 2-3 controller selezionata",
        "msg.exported": "Esportato in",
        "msg.loaded": "Caricato da",
        "msg.export_failed": "Esportazione fallita",
        # Voci delle EnumProperty (callback _items_shape/_items_color/...)
        "shape.circle": "Cerchio",
        "shape.cube": "Cubo",
        "shape.sphere": "Sfera",
        "shape.arrow": "Freccia",
        "shape.cross": "Croce",
        "color.none": "Nessuno",
        "color.red": "Rosso",
        "color.green": "Verde",
        "color.blue": "Blu",
        "parent.chain": "Catena CTRL (FK)",
        "parent.chain_tip": "Ricrea la gerarchia tra i controller generati (zero Dependency Cycle con ACTD)",
        "parent.bone": "Bone genitore",
        "parent.bone_tip": "Usa il genitore del bone DEF",
        "parent.root": "Root",
        "parent.root_tip": "Collega alla radice dell'armatura",
        "parent.none": "Nessuno (Libero)",
        "parent.none_tip": "Controller senza genitore",
        "parent.def": "DEF stesso (solo senza ACTD)",
        "parent.def_tip": "Collega al bone DEF stesso",
        "preset.default": "Default (Cerchio)",
        "preset.biped": "Arto Bipede (Cubo)",
        "preset.root": "Root (Freccia)",
        "preset.face": "Faccia (Sfera)",
    },
    "en": {
        "panel.label": "DEF Controller",
        "panel.prefix_def": "DEF",
        "panel.prefix_ctrl": "CTRL",
        "panel.shape": "Shape",
        "panel.scale": "Scale",
        "panel.shape_rot": "Shape Rotation",
        "panel.color": "Color",
        "panel.parent": "Parent",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Armature Status",
        "panel.export": "Export / Preset",
        "panel.ik": "IK Target",
        "stats.line": "DEF: %d  |  CTRL: %d",
        "op.generate": "Generate Controllers",
        "op.bind_actd": "Bind DEF to CTRL (ACTD)",
        "op.remove": "Remove Generated",
        "op.apply_preset": "Apply Preset",
        "op.diagnose": "Diagnose Rig",
        "op.add_ik": "Add IK Target",
        "op.export_json": "Export JSON",
        "op.export_csv": "Export CSV",
        "op.save_preset": "Save Preset JSON",
        "op.load_preset": "Load Preset JSON",
        "msg.created": "Controllers created",
        "msg.removed": "Controllers removed",
        "msg.no_armature": "No active armature",
        "msg.no_def_bones": "No DEF bones selected",
        "msg.no_registered": "No registered controllers",
        "msg.bound": "DEF/CTRL bindings",
        "msg.diag_ok": "Diagnostics OK: no issues found",
        "msg.diag_issues": "Issues found",
        "msg.ik_created": "IK targets created",
        "msg.no_ik_chain": "No 2-3 controller chain selected",
        "msg.exported": "Exported to",
        "msg.loaded": "Loaded from",
        "msg.export_failed": "Export failed",
        "shape.circle": "Circle",
        "shape.cube": "Cube",
        "shape.sphere": "Sphere",
        "shape.arrow": "Arrow",
        "shape.cross": "Cross",
        "color.none": "None",
        "color.red": "Red",
        "color.green": "Green",
        "color.blue": "Blue",
        "parent.chain": "CTRL Chain (FK)",
        "parent.chain_tip": "Rebuilds the hierarchy between generated controllers (no Dependency Cycle with ACTD)",
        "parent.bone": "Parent Bone",
        "parent.bone_tip": "Uses the parent of the DEF bone",
        "parent.root": "Root",
        "parent.root_tip": "Links to the armature root",
        "parent.none": "None (Free)",
        "parent.none_tip": "Controller without a parent",
        "parent.def": "DEF itself (only without ACTD)",
        "parent.def_tip": "Links to the DEF bone itself",
        "preset.default": "Default (Circle)",
        "preset.biped": "Biped Limb (Cube)",
        "preset.root": "Root (Arrow)",
        "preset.face": "Face (Sphere)",
    },
}


def tr(key, lang=None):
    # La lingua attiva si legge dalla preferenza della UI e, in mancanza, dal
    # locale delle traduzioni: entrambe arrivano come "it_IT" / "en_US", quindi
    # si normalizza il prefisso. Fallback su "en".
    if lang is None:
        lang = "en"
        try:
            lang = bpy.context.preferences.view.language or lang
        except (AttributeError, RuntimeError):
            lang = "en"
        if not str(lang).lower().startswith(("it", "en")):
            try:
                lang = bpy.app.translations.locale or lang
            except AttributeError:
                pass
    k = "it" if str(lang).lower().startswith("it") else "en"
    return _I18N.get(k, _I18N["en"]).get(key, key)


