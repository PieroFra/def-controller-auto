# MODULO ctrl_def_i18n.py — tabelle _I18N e funzione tr (intestazione di build, non fa parte del monolite)
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
        "panel.color": "Colore",
        "panel.parent": "Genitore",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Stato Armatura",
        "stats.line": "DEF: %d  |  CTRL: %d",
        "op.generate": "Genera Controller",
        "op.create": "Crea Controller",
        "op.bind_actd": "Vincola DEF ai CTRL (ACTD)",
        "op.remove": "Rimuovi Generati",
        "op.apply_preset": "Applica Preset",
        "msg.created": "Controller creati",
        "msg.removed": "Controller rimossi",
        "msg.no_armature": "Nessuna armatura attiva",
        "msg.no_def_bones": "Nessun bone DEF selezionato",
        "msg.no_registered": "Nessun controller registrato",
        "msg.bound": "Vincoli DEF/CTRL",
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
        "panel.color": "Color",
        "panel.parent": "Parent",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Armature Status",
        "stats.line": "DEF: %d  |  CTRL: %d",
        "op.generate": "Generate Controllers",
        "op.bind_actd": "Bind DEF to CTRL (ACTD)",
        "op.remove": "Remove Generated",
        "op.apply_preset": "Apply Preset",
        "msg.created": "Controllers created",
        "msg.removed": "Controllers removed",
        "msg.no_armature": "No active armature",
        "msg.no_def_bones": "No DEF bones selected",
        "msg.no_registered": "No registered controllers",
        "msg.bound": "DEF/CTRL bindings",
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


