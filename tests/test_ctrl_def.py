# tests/test_ctrl_def.py — suite funzionale ed end-to-end per CTRL_DEF
# Eseguito dentro Blender (headless) da run_tests.ps1

import bpy
import importlib.util
import json
import math
import os
import sys
import tempfile
from mathutils import Vector

# Percorso dell'addon (entry point del package) per il caricamento diretto
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
_PATH_ADDON = os.path.join(_REPO_ROOT, "__init__.py")

# La radice del repo sta su sys.path: l'addon non tocca piu' sys.path (la
# policy delle Blender Extensions lo vieta), quindi la preparazione del
# percorso e' compito della suite.
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _addon_module():
    """Modulo dell'addon: quello del runner se presente, altrimenti dal file.

    Il caricamento da file avviene come package reale (submodule_search_locations
    e registrazione in sys.modules) e senza register(): serve solo per leggere
    bl_info e le funzioni pure (_read_registry, _mirror_name, ...).
    """
    mod = sys.modules.get("ctrl_def_addon")
    if mod is not None and isinstance(getattr(mod, "bl_info", None), dict):
        return mod
    spec = importlib.util.spec_from_file_location(
        "ctrl_def_addon", _PATH_ADDON, submodule_search_locations=[_REPO_ROOT])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ctrl_def_addon"] = mod
    spec.loader.exec_module(mod)
    return mod


def _reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _new_armature(name):
    arm_data = bpy.data.armatures.new(name + "Data")
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    return arm_obj, arm_data


def _add_bone(arm_data, name, head, tail, parent_name=None, select=True):
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    eb.select = select
    if parent_name is not None:
        eb.parent = arm_data.edit_bones[parent_name]
        eb.use_connect = False
    return eb


def _build_chain(arm_data):
    """Catena DEF_arm.L -> DEF_forearm.L -> DEF_hand.L in Edit Mode."""
    _add_bone(arm_data, "DEF_arm.L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    _add_bone(arm_data, "DEF_forearm.L", (0.0, 0.0, 1.5), (0.0, 0.0, 2.0), "DEF_arm.L")
    _add_bone(arm_data, "DEF_hand.L", (0.0, 0.0, 2.0), (0.0, 0.0, 2.2), "DEF_forearm.L")


def _seleziona_posa(arm_obj, nomi=None, stato=True):
    """Imposta la selezione dei pose bone con fallback tra versioni Blender.

    Da Blender 5.0 la selezione vive sul pose bone; in 4.x resta sul Bone.
    Si impostano entrambi gli stati perche' in headless il pose bone puo'
    non riflettere la copia Bone (e viceversa). Con nomi=None agisce su tutti
    i pose bone dell'armatura.
    """
    if nomi is None:
        bersagli = list(arm_obj.pose.bones)
    else:
        bersagli = [arm_obj.pose.bones[nm] for nm in nomi]
    for pbone in bersagli:
        if hasattr(pbone, "select"):
            pbone.select = stato
        # Da Blender 5.0 il Bone dell'armatura non espone piu' "select":
        # lo stato si copia solo se la proprieta' esiste ancora.
        if hasattr(pbone.bone, "select"):
            pbone.bone.select = stato
    bpy.context.view_layer.update()


def _seleziona_def(arm_obj, nomi):
    """Allinea la selezione dei DEF su pose bone ed edit bone.

    Blender 5.x riallinea la selezione degli edit bone a quella dei pose bone
    quando si entra in Edit Mode: senza questo passaggio generate legge uno
    stato vecchio e rifiuta con "No DEF bones selected". Stessa sorgente del
    blocco IK, che seleziona i controller in Pose Mode.
    """
    bpy.ops.object.mode_set(mode='POSE')
    _seleziona_posa(arm_obj, None, False)
    _seleziona_posa(arm_obj, nomi, True)
    # Passaggio da Edit Mode: la selezione arriva anche sugli edit bone
    bpy.ops.object.mode_set(mode='EDIT')
    for ebone in arm_obj.data.edit_bones:
        ebone.select = ebone.name in nomi
    bpy.ops.object.mode_set(mode='OBJECT')


def _walk_up(bone):
    """Risale la gerarchia restituendo la lista dei nomi visitati."""
    names = []
    cur = bone
    while cur is not None:
        names.append(cur.name)
        cur = cur.parent
    return names


def test_registration_elements():
    # Scena pulita: le suite girano in ordine alfabetico e test_presets lascia
    # stg.parent = "BONE", quindi qui si riparte dai valori di default.
    _reset()
    assert hasattr(bpy.types, "CTRLDEF_PT_panel"), "Panel CTRLDEF_PT_panel non registrato"
    assert hasattr(bpy.ops.ctrl_def, "generate"), "Operatore ctrl_def.generate mancante"
    assert hasattr(bpy.ops.ctrl_def, "remove"), "Operatore ctrl_def.remove mancante"
    assert hasattr(bpy.ops.ctrl_def, "bind_actd"), "Operatore ctrl_def.bind_actd mancante"
    assert hasattr(bpy.ops.ctrl_def, "diagnose"), "Operatore ctrl_def.diagnose mancante"
    assert hasattr(bpy.ops.ctrl_def, "create_widget"), \
        "Operatore ctrl_def.create_widget mancante"
    assert hasattr(bpy.types.Scene, "ctrl_def_settings"), "Scene.ctrl_def_settings mancante"
    stg = bpy.context.scene.ctrl_def_settings
    assert stg.prefix_ctrl == "", f"prefix_ctrl deve essere vuoto di default, trovato {stg.prefix_ctrl!r}"
    assert stg.parent == "CHAIN", f"parent di default deve essere CHAIN, trovato {stg.parent!r}"
    assert stg.prefix_def == "DEF_", f"prefix_def di default inatteso: {stg.prefix_def!r}"
    # Metadati allineati a blender_manifest.toml (maintainer) e versione 0.2.0
    mod = _addon_module()
    assert mod is not None, "Modulo dell'addon non trovato: impossibile leggere bl_info"
    bl_info = mod.bl_info
    assert bl_info["author"] == "Pierfrancesco Diodato", \
        f"bl_info['author'] inatteso: {bl_info['author']!r}"
    assert tuple(bl_info["version"]) == (0, 2, 0), \
        f"bl_info['version'] inattesa: {bl_info['version']!r}"
    # Nome, categoria e bl_idname non devono cambiare
    assert bl_info["name"] == "DEF Controller Auto", f"bl_info['name'] cambiato: {bl_info['name']!r}"
    assert bl_info["category"] == "Rigging", f"bl_info['category'] cambiata: {bl_info['category']!r}"
    # Mirror: il separatore originale va preservato (_, .)
    assert mod._mirror_name("DEF_hand_L") == "DEF_hand_R", \
        f"Mirror di DEF_hand_L: {mod._mirror_name('DEF_hand_L')!r} invece di 'DEF_hand_R'"
    assert mod._mirror_name("DEF_hand.R") == "DEF_hand.L", \
        f"Mirror di DEF_hand.R: {mod._mirror_name('DEF_hand.R')!r} invece di 'DEF_hand.L'"
    assert mod._mirror_name("DEF_hand") == "DEF_hand", "Un nome centrale non deve essere specchiato"
    # Localizzazione: le due lingue devono esistere e differire davvero
    assert mod.tr("op.generate", "it") == "Genera Controller", \
        f"tr('op.generate', 'it') inatteso: {mod.tr('op.generate', 'it')!r}"
    assert mod.tr("op.generate", "en") == "Generate Controllers", \
        f"tr('op.generate', 'en') inatteso: {mod.tr('op.generate', 'en')!r}"
    # Chiavi aggiunte per le EnumProperty e i messaggi dell'operatore di bind
    for chiave in ("msg.no_registered", "msg.bound", "msg.bw_missing",
                   "op.bw_create", "op.bw_install",
                   "parent.chain",
                   "parent.chain_tip", "parent.bone", "parent.bone_tip",
                   "parent.root", "parent.root_tip", "parent.none",
                   "parent.none_tip", "parent.def", "parent.def_tip",
                   "preset.default", "preset.biped", "preset.root", "preset.face",
                   "op.diagnose", "msg.diag_ok", "msg.diag_issues",
                   "sec.setup", "sec.controller", "sec.advanced", "sec.guide",
                   "guide.1", "guide.2", "guide.3", "guide.4", "guide.5"):
        for lingua in ("it", "en"):
            assert chiave in mod._I18N[lingua], f"Chiave {chiave!r} assente in _I18N[{lingua!r}]"
    assert mod.tr("msg.no_registered", "it") == "Nessun controller registrato", \
        f"msg.no_registered IT inatteso: {mod.tr('msg.no_registered', 'it')!r}"
    assert mod.tr("msg.no_registered", "en") == "No registered controllers", \
        f"msg.no_registered EN inatteso: {mod.tr('msg.no_registered', 'en')!r}"
    assert mod.tr("op.diagnose", "it") == "Diagnostica Rig", \
        f"op.diagnose IT inatteso: {mod.tr('op.diagnose', 'it')!r}"
    assert mod.tr("op.diagnose", "en") == "Diagnose Rig", \
        f"op.diagnose EN inatteso: {mod.tr('op.diagnose', 'en')!r}"
    assert mod.tr("msg.diag_ok", "it") == "Diagnostica OK: nessun problema rilevato", \
        f"msg.diag_ok IT inatteso: {mod.tr('msg.diag_ok', 'it')!r}"
    assert mod.tr("msg.diag_issues", "en") == "Issues found", \
        f"msg.diag_issues EN inatteso: {mod.tr('msg.diag_issues', 'en')!r}"
    # Titoli di sezione e guida rapida: presenti in IT/EN, corti per la sidebar
    assert mod.tr("sec.setup", "it") == "1 · Setup", \
        f"sec.setup IT inatteso: {mod.tr('sec.setup', 'it')!r}"
    assert mod.tr("sec.guide", "en") == "Guide", \
        f"sec.guide EN inatteso: {mod.tr('sec.guide', 'en')!r}"
    for passo in ("guide.1", "guide.2", "guide.3", "guide.4", "guide.5"):
        for lingua in ("it", "en"):
            testo = mod.tr(passo, lingua)
            assert testo and testo != passo, \
                f"Chiave {passo!r} senza traduzione in {lingua!r}: {testo!r}"
            assert len(testo) <= 28, \
                f"Testo di {passo!r} in {lingua!r} troppo lungo ({len(testo)}): {testo!r}"
    assert mod.tr("guide.1", "it") == "1 Armatura con bone DEF_", \
        f"guide.1 IT inatteso: {mod.tr('guide.1', 'it')!r}"
    assert mod.tr("guide.4", "en") == "4 Bind DEF to CTRL", \
        f"guide.4 EN inatteso: {mod.tr('guide.4', 'en')!r}"
    # Callback delle EnumProperty: con items dinamici il default e' l'indice 0,
    # quindi la prima voce deve restare quella storica di default.
    assert mod._items_parent(None, None)[0][0] == "CHAIN", \
        f"Prima voce di _items_parent: {mod._items_parent(None, None)[0][0]!r} invece di 'CHAIN'"
    assert mod._items_preset(None, None)[0][0] == "DEFAULT", \
        f"Prima voce di _items_preset: {mod._items_preset(None, None)[0][0]!r} invece di 'DEFAULT'"
    # Tooltip dinamici: IT ed EN devono avere esattamente le stesse chiavi,
    # altrimenti una delle due lingue mostra la chiave grezza nel mouseover.
    assert set(mod._I18N["it"].keys()) == set(mod._I18N["en"].keys()), \
        ("Chiavi IT/EN non simmetriche: solo IT=%r solo EN=%r" % (
            sorted(set(mod._I18N["it"]) - set(mod._I18N["en"])),
            sorted(set(mod._I18N["en"]) - set(mod._I18N["it"]))))
    assert mod.tr("op.create", "en") == "Create Controllers", \
        f"op.create EN inatteso: {mod.tr('op.create', 'en')!r}"
    # Ogni proprieta' del pannello ha il proprio tooltip in entrambe le lingue
    for _chiave_prop in ("tip.prop.prefix_def", "tip.prop.prefix_ctrl",
                         "tip.prop.scale", "tip.prop.parent",
                         "tip.prop.mirror", "tip.prop.preset"):
        for _lingua in ("it", "en"):
            _testo_prop = mod.tr(_chiave_prop, _lingua)
            assert _testo_prop and _testo_prop != _chiave_prop, \
                f"Tooltip {_chiave_prop!r} assente in {_lingua!r}: {_testo_prop!r}"
    # Gli 11 operatori devono esporre description() bilingue: si forza la lingua
    # sostituendo tr() nello spazio dei nomi del modulo che definisce la classe.
    _nomi_op = ("generate", "apply_preset", "remove", "bind_actd", "diagnose",
                "export_json", "export_csv", "save_preset", "load_preset",
                "add_ik", "create_widget")
    for _nome_op in _nomi_op:
        _cls_op = getattr(mod, "CTRLDEF_OT_" + _nome_op, None)
        assert _cls_op is not None, f"Classe CTRLDEF_OT_{_nome_op} mancante"
        _chiave_tip = "tip.op." + _nome_op
        _globs_op = _cls_op.description.__func__.__globals__
        _tr_op_reale = _globs_op["tr"]
        _testi = {}
        try:
            for _lingua in ("it", "en"):
                _globs_op["tr"] = lambda k, _l=_lingua: mod.tr(k, _l)
                _testi[_lingua] = _cls_op.description(bpy.context, None)
        finally:
            _globs_op["tr"] = _tr_op_reale
        for _lingua in ("it", "en"):
            assert _testi[_lingua] and _testi[_lingua] != _chiave_tip, \
                f"description() di CTRLDEF_OT_{_nome_op} vuota in {_lingua!r}: {_testi[_lingua]!r}"
            assert _testi[_lingua] == mod.tr(_chiave_tip, _lingua), \
                (f"description() di CTRLDEF_OT_{_nome_op} in {_lingua!r}: "
                 f"{_testi[_lingua]!r} invece di {mod.tr(_chiave_tip, _lingua)!r}")
        assert _testi["it"] != _testi["en"], \
            f"Tooltip di CTRLDEF_OT_{_nome_op} identico in IT ed EN: {_testi['it']!r}"
    # Il colore non e' piu' una proprieta' di CTRL_DEF: lo gestisce Bone Widget.
    # Come per 'shape', la rimozione va verificata (nessun controllo morto).
    assert not hasattr(mod, "_items_color"), \
        "La callback _items_color non deve piu' esistere (colore delegato a Bone Widget)"
    for chiave_morta in ("color.none", "color.red", "color.green", "color.blue",
                         "panel.color"):
        for lingua in ("it", "en"):
            assert chiave_morta not in mod._I18N[lingua], \
                f"Chiave morta {chiave_morta!r} ancora presente in _I18N[{lingua!r}]"
    # Etichette delle callback in IT ed EN: si forza la lingua sostituendo tr()
    # nello spazio dei nomi del modulo che definisce _items_parent (package).
    _globs_props = mod._items_parent.__globals__
    _tr_reale = _globs_props["tr"]

    def _tr_forzato(lingua):
        return lambda chiave, lang=None: _tr_reale(chiave, lingua)

    try:
        _globs_props["tr"] = _tr_forzato("it")
        voci_it = {voce[0]: voce[1] for voce in mod._items_parent(None, None)}
        _globs_props["tr"] = _tr_forzato("en")
        voci_en = {voce[0]: voce[1] for voce in mod._items_parent(None, None)}
    finally:
        _globs_props["tr"] = _tr_reale
    assert voci_it.get("CHAIN") == "Catena CTRL (FK)", f"_items_parent IT: {voci_it}"
    assert voci_it.get("ROOT") == "Root", f"_items_parent IT (ROOT): {voci_it}"
    assert voci_en.get("CHAIN") == "CTRL Chain (FK)", f"_items_parent EN: {voci_en}"
    assert voci_en.get("ROOT") == "Root", f"_items_parent EN (ROOT): {voci_en}"
    # I widget sono delegati a Bone Widget: l'etichetta del campo lo dichiara
    assert mod.tr("panel.shape", "it") == "Widget (Bone Widget)", \
        f"panel.shape IT inatteso: {mod.tr('panel.shape', 'it')!r}"
    assert mod.tr("panel.shape", "en") == "Widget (Bone Widget)", \
        f"panel.shape EN inatteso: {mod.tr('panel.shape', 'en')!r}"
    assert mod.tr("msg.bw_missing", "it") == "Installa Bone Widget per i widget", \
        f"msg.bw_missing IT inatteso: {mod.tr('msg.bw_missing', 'it')!r}"
    assert mod.tr("msg.bw_missing", "en") == "Install Bone Widget for the widgets", \
        f"msg.bw_missing EN inatteso: {mod.tr('msg.bw_missing', 'en')!r}"
    # Titolo del riquadro Bone Widget nella sezione 2 · Controller
    assert mod.tr("panel.widget", "it") == "Widget", \
        f"panel.widget IT inatteso: {mod.tr('panel.widget', 'it')!r}"
    assert mod.tr("panel.widget", "en") == "Widget", \
        f"panel.widget EN inatteso: {mod.tr('panel.widget', 'en')!r}"
    # Le altre callback espongono le stesse 5/4 voci attese
    assert [v[0] for v in mod._items_parent(None, None)] == ["CHAIN", "BONE", "ROOT", "NONE", "DEF"], \
        f"Voci di _items_parent inattese: {[v[0] for v in mod._items_parent(None, None)]}"
    assert [v[0] for v in mod._items_preset(None, None)] == ["DEFAULT", "BIPED_LIMB", "ROOT_CTRL", "FACE"], \
        f"Voci di _items_preset inattese: {[v[0] for v in mod._items_preset(None, None)]}"
    # execute di generate scomposto in helper di modulo
    for nome_helper in ("_collect_def_bones", "_create_ctrl_edit_bones",
                        "_assign_ctrl_parents", "_configure_ctrl_pose_bones"):
        assert callable(getattr(mod, nome_helper, None)), \
            f"Helper di generazione {nome_helper} mancante o non chiamabile nel modulo"
    # Delegati a Bone Widget, dispatcher rimosso: i widget esterni non hanno
    # geometria interna da costruire, serve solo il ponte verso l'estensione
    for nome_helper in ("_bonewidget_available", "_bonewidget_create",
                        "_apply_preset_values",
                        "_remove_registered_bones", "_draw_stats_box",
                        "_draw_preset_box", "_draw_settings", "_draw_actions",
                        "_draw_controller_settings", "_draw_advanced_actions",
                        "_draw_guide", "_section", "_draw_widget_box",
                        "_purge_unused_shapes", "_ensure_armature_mode",
                        "_configure_actd_settings", "_count_actd_bindings_for_arm",
                        "_apply_native_bindings", "_register_class_safe",
                        "_unregister_class_safe", "_diagnose_def_selection"):
        assert callable(getattr(mod, nome_helper, None)), \
            f"Helper {nome_helper} mancante o non chiamabile nel modulo"
    # register() deve essere idempotente: una seconda chiamata non tocca
    # Scene.ctrl_def_settings, che deve restare usabile
    mod.register()
    assert hasattr(bpy.types.Scene, "ctrl_def_settings"), \
        "Scene.ctrl_def_settings sparito dopo una seconda chiamata a register()"
    stg_dopo = bpy.context.scene.ctrl_def_settings
    assert stg_dopo is not None, "Scene.ctrl_def_settings non accessibile dopo register() ripetuto"
    assert stg_dopo.prefix_def == "DEF_", \
        f"prefix_def alterato da register() ripetuto: {stg_dopo.prefix_def!r}"
    # Il campo del widget e' una stringa con default "Circle" (nome del widget
    # fornito da Bone Widget): la vecchia enum interna non deve piu' esistere.
    assert stg_dopo.widget_name == "Circle", \
        f"widget_name di default inatteso: {stg_dopo.widget_name!r}"
    assert not hasattr(stg_dopo, "shape"), \
        "La vecchia proprieta' enum 'shape' non deve piu' esistere (widget delegati)"
    assert not hasattr(stg_dopo, "color"), \
        "La vecchia proprieta' enum 'color' non deve piu' esistere (colore delegato a Bone Widget)"
    # La rotazione del widget la gestisce Bone Widget: nessun controllo morto
    assert not hasattr(stg_dopo, "shape_rot"), \
        "shape_rot non deve piu' esistere: la rotazione e' delegata a Bone Widget"
    # Senza Bone Widget il ponte ritorna False, senza sollevare eccezioni
    if not mod._bonewidget_available():
        assert mod._bonewidget_create(None, [], "Circle", 1.0) is False, \
            "Senza Bone Widget _bonewidget_create deve restituire False"
    # Il sotto-modulo bpy.ops.bonewidget e' pigro: hasattr(...) risponde sempre
    # True. La disponibilita' deve dipendere dalla classe registrata.
    chiavi_addon = tuple(bpy.context.preferences.addons.keys())
    if not hasattr(bpy.types, "BONEWIDGET_OT_create_widget") and \
            not any(k == "bone_widget" or k.endswith(".bone_widget")
                    or k == "bonewidget" or k.endswith(".bonewidget")
                    for k in chiavi_addon):
        assert mod._bonewidget_available() is False, \
            "Bone Widget assente ma _bonewidget_available() dice True " \
            "(falso positivo di bpy.ops.bonewidget pigro)"
    assert isinstance(getattr(mod, "_ITEMS_CACHE", None), list), \
        "_ITEMS_CACHE deve esistere ed essere una lista (anti garbage-collection)"
    voci_cache = mod._items_parent(None, None)
    assert voci_cache in mod._ITEMS_CACHE, \
        "L'elenco restituito da _items_parent non e' trattenuto in _ITEMS_CACHE"
    voci_preset_cache = mod._items_preset(None, None)
    assert voci_preset_cache in mod._ITEMS_CACHE, \
        "L'elenco restituito da _items_preset non e' trattenuto in _ITEMS_CACHE"
    # Architettura Moduli + Package: lo script di build e gli 8 moduli
    # funzionali devono esistere su disco accanto all'entry point __init__.py
    radice_addon = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    percorso_build = os.path.join(radice_addon, "scripts", "build_monolith.py")
    assert os.path.isfile(percorso_build), f"Script di build mancante: {percorso_build}"
    percorso_package = os.path.join(radice_addon, "ctrl_def_mods", "__init__.py")
    assert os.path.isfile(percorso_package), f"Package ctrl_def_mods mancante: {percorso_package}"
    moduli_attesi = ("ctrl_def_i18n.py", "ctrl_def_registry.py",
                     "ctrl_def_shapes.py", "ctrl_def_properties.py",
                     "ctrl_def_generation.py", "ctrl_def_operators.py",
                     "ctrl_def_ui.py", "ctrl_def_main.py")
    assert len(moduli_attesi) == 8, f"Elenco dei moduli inatteso: {len(moduli_attesi)} voci"
    for nome_modulo in moduli_attesi:
        percorso_modulo = os.path.join(radice_addon, "ctrl_def_mods", nome_modulo)
        assert os.path.isfile(percorso_modulo), f"Modulo dell'addon mancante: {percorso_modulo}"
    # L'entry point resta leggero: bl_info vive qui e non in un modulo header
    percorso_entry = os.path.join(radice_addon, "__init__.py")
    with open(percorso_entry, "r", encoding="utf-8") as file_entry:
        righe_entry = file_entry.readlines()
    assert len(righe_entry) < 120, \
        f"__init__.py deve restare un entry point leggero: {len(righe_entry)} righe"
    assert not os.path.isfile(os.path.join(radice_addon, "ctrl_def_mods", "ctrl_def_header.py")), \
        "ctrl_def_header.py non deve piu' esistere: bl_info vive nell'entry point"


def test_naming_pulito_e_prefisso():
    # 1. Naming pulito di default: DEF_hand.L -> hand.L, senza deformazione
    _reset()
    arm_obj, arm_data = _new_armature("RigNaming")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_hand.L", (0.0, 0.0, 1.0), (0.0, 0.5, 1.0))
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione fallita con status: {res}"
    assert "hand.L" in arm_data.bones, f"Controller 'hand.L' non creato: {[b.name for b in arm_data.bones]}"
    assert "CTRL_hand.L" not in arm_data.bones, "Con prefix_ctrl vuoto non deve comparire 'CTRL_hand.L'"
    ctrl_bone = arm_data.bones["hand.L"]
    assert ctrl_bone.use_deform is False, "Il controller deve avere use_deform == False"
    assert ctrl_bone.parent is None, "Senza DEF genitore il controller non deve avere parent"
    # I controller non hanno piu' shape interne: i widget li crea Bone Widget
    assert not any(o.name.startswith("CTRL_DEF_SHAPE_") for o in bpy.data.objects), \
        f"CTRL_DEF non deve creare oggetti CTRL_DEF_SHAPE_*: {[o.name for o in bpy.data.objects]}"
    assert bpy.data.collections.get("CTRL_Shapes") is None, \
        "La collezione interna CTRL_Shapes non deve piu' essere creata"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert reg.get("hand.L", {}).get("def") == "DEF_hand.L", f"Registry errato: {reg}"

    # 2. Naming con prefisso esplicito: DEF_hand.L -> CTRL_hand.L
    _reset()
    bpy.context.scene.ctrl_def_settings.prefix_ctrl = "CTRL_"
    arm_obj, arm_data = _new_armature("RigPrefisso")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_hand.L", (0.0, 0.0, 1.0), (0.0, 0.5, 1.0))
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione con prefisso fallita: {res}"
    assert "CTRL_hand.L" in arm_data.bones, "Con prefix_ctrl='CTRL_' il nome atteso e' CTRL_hand.L"
    assert arm_data.bones["CTRL_hand.L"].use_deform is False, "CTRL_hand.L deve avere use_deform == False"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert reg.get("CTRL_hand.L", {}).get("def") == "DEF_hand.L", f"Registry errato con prefisso: {reg}"

    # 3. Mirror con un solo lato: esiste .L e non .R -> non crasha, crea solo .L
    _reset()
    bpy.context.scene.ctrl_def_settings.mirror = True
    arm_obj, arm_data = _new_armature("RigMirrorSoloL")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_arm.L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Mirror con solo .L fallito: {res}"
    assert "arm.L" in arm_data.bones, f"Controller arm.L assente: {[b.name for b in arm_data.bones]}"
    assert "arm.R" not in arm_data.bones, "Con mirror=True non deve nascere un .R inesistente"
    assert len(arm_data.bones) == 2, \
        f"Attesi solo DEF_arm.L + arm.L, trovati: {[b.name for b in arm_data.bones]}"

    # 4. Nomi con separatore underscore: DEF_arm_L + DEF_arm_R con mirror=True
    _reset()
    bpy.context.scene.ctrl_def_settings.mirror = True
    arm_obj, arm_data = _new_armature("RigMirrorUnderscore")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_arm_L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    _add_bone(arm_data, "DEF_arm_R", (0.0, 0.0, -1.0), (0.0, 0.0, -1.5))
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Mirror con separatore _ fallito: {res}"
    for nm in ("arm_L", "arm_R"):
        assert nm in arm_data.bones, \
            f"Controller {nm} assente (separatore _ non preservato?): {[b.name for b in arm_data.bones]}"
    for nm in ("arm.L", "arm.R"):
        assert nm not in arm_data.bones, f"Non deve comparire {nm} partendo da nomi con _"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert reg.get("arm_L", {}).get("def") == "DEF_arm_L", f"Registry errato per arm_L: {reg}"
    assert reg.get("arm_R", {}).get("def") == "DEF_arm_R", f"Registry errato per arm_R: {reg}"

    # 5. Widget separati dai controller: ctrl_def.generate NON crea widget,
    # solo ctrl_def.create_widget delega a Bone Widget (quando disponibile).
    # Il pose bone deve restare senza shape creata da CTRL_DEF: la shape la
    # mette Bone Widget, altrimenti resta vuota senza errori bloccanti.
    _reset()
    mod = _addon_module()
    assert mod is not None, "Modulo dell'addon non disponibile per il test dei widget"
    gen_mod = sys.modules.get(mod.CTRLDEF_OT_generate.__module__)
    assert gen_mod is not None, "Modulo di generazione non trovato in sys.modules"
    assert not hasattr(gen_mod, "_bonewidget_create"), \
        "La generazione non deve piu' delegare i widget a Bone Widget"
    ops_mod = sys.modules.get(mod.CTRLDEF_OT_create_widget.__module__)
    assert ops_mod is not None, "Modulo operatori non trovato in sys.modules"
    assert callable(getattr(ops_mod, "_bonewidget_create", None)), \
        "Helper _bonewidget_create mancante nel modulo operatori"
    chiamate = []

    def _spia_bonewidget(arm, nomi, widget, scala):
        """Registra la delega e non assegna shape: non spetta ai test."""
        chiamate.append((arm.name, list(nomi), widget, scala))
        return True

    originale_bw = ops_mod._bonewidget_create
    originale_avail = ops_mod._bonewidget_available
    ops_mod._bonewidget_create = _spia_bonewidget
    try:
        stg = bpy.context.scene.ctrl_def_settings
        stg.widget_name = "Cube"
        stg.scale = 1.0
        arm_obj, arm_data = _new_armature("RigWidget")
        bpy.ops.object.mode_set(mode='EDIT')
        _add_bone(arm_data, "DEF_hand.L", (0.0, 0.0, 1.0), (0.0, 0.5, 1.0))
        bpy.ops.object.mode_set(mode='OBJECT')
        res = bpy.ops.ctrl_def.generate()
        assert res == {'FINISHED'}, f"Generazione con widget_name fallita: {res}"
        assert chiamate == [], \
            f"ctrl_def.generate non deve creare widget, chiamate: {chiamate}"
        # Bone Widget assente: il wrapper rifiuta senza toccare nulla
        ops_mod._bonewidget_available = lambda: False
        res_no_bw = bpy.ops.ctrl_def.create_widget()
        assert res_no_bw == {'CANCELLED'}, \
            f"create_widget senza Bone Widget deve annullarsi: {res_no_bw}"
        assert chiamate == [], \
            f"create_widget senza Bone Widget ha delegato comunque: {chiamate}"
        # Bone Widget presente: il wrapper crea il widget sui controller
        ops_mod._bonewidget_available = lambda: True
        res_widget = bpy.ops.ctrl_def.create_widget()
    finally:
        ops_mod._bonewidget_create = originale_bw
        ops_mod._bonewidget_available = originale_avail
    assert res_widget == {'FINISHED'}, \
        f"create_widget con Bone Widget attivo fallito: {res_widget}"
    assert len(chiamate) == 1, \
        f"_bonewidget_create chiamato {len(chiamate)} volte invece di 1"
    arm_chiamata, nomi_chiamati, widget_chiamato, scala_chiamata = chiamate[0]
    assert arm_chiamata == arm_obj.name, \
        f"La delega del widget non punta all'armatura generata: {arm_chiamata!r}"
    assert nomi_chiamati == ["hand.L"], \
        f"Nomi passati a _bonewidget_create: {nomi_chiamati}"
    assert widget_chiamato == "Cube", \
        f"Widget passato a _bonewidget_create: {widget_chiamato!r}"
    assert abs(scala_chiamata - 1.0) < 1e-6, \
        f"Scala passata a _bonewidget_create: {scala_chiamata}"
    pbone_hand = arm_obj.pose.bones.get("hand.L")
    assert pbone_hand is not None, "Controller hand.L non creato con widget_name impostato"
    assert pbone_hand.custom_shape is None, \
        ("CTRL_DEF non deve assegnare custom_shape: il widget e' delegato a "
         f"Bone Widget, trovato {pbone_hand.custom_shape!r}")
    assert not any(o.name.startswith("CTRL_DEF_SHAPE_") for o in bpy.data.objects), \
        f"CTRL_DEF ha creato oggetti shape interni: {[o.name for o in bpy.data.objects]}"


def test_parent_chain_fk():
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.parent = "CHAIN"
    arm_obj, arm_data = _new_armature("RigCatena")
    bpy.ops.object.mode_set(mode='EDIT')
    _build_chain(arm_data)
    bpy.ops.object.mode_set(mode='OBJECT')
    _seleziona_def(arm_obj, ("DEF_arm.L", "DEF_forearm.L", "DEF_hand.L"))
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione catena fallita: {res}"
    for nm in ("arm.L", "forearm.L", "hand.L"):
        assert nm in arm_data.bones, f"Controller {nm} non creato"
    # FK tra controller: nessun controller figlio di un DEF
    assert arm_data.bones["arm.L"].parent is None, "arm.L non deve avere parent (radice DEF)"
    for parent_nm, child_nm in (("arm.L", "forearm.L"), ("forearm.L", "hand.L")):
        child = arm_data.bones[child_nm]
        assert child.parent is not None, f"{child_nm} deve essere figlio di {parent_nm}"
        assert child.parent.name == parent_nm, f"Parent di {child_nm}: atteso {parent_nm}, trovato {child.parent.name}"
    # Nessun anello nella gerarchia (zero Dependency Cycle)
    for nm in ("arm.L", "forearm.L", "hand.L"):
        path = _walk_up(arm_data.bones[nm])
        assert len(path) == len(set(path)), f"Anello di gerarchia rilevato per {nm}: {path}"
        assert all(not p.startswith("DEF_") for p in path), f"{nm} dipende da un bone DEF: {path}"

    # Rigenerazione con un altro widget: i controller restano validi e nessuna
    # mesh di shape viene creata da CTRL_DEF (i widget sono di Bone Widget)
    stg.widget_name = "Cube"
    _seleziona_def(arm_obj, ("DEF_arm.L", "DEF_forearm.L", "DEF_hand.L"))
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Rigenerazione con widget Cube fallita: {res}"
    nomi = ("arm.L", "forearm.L", "hand.L")
    for nm in nomi:
        assert nm in arm_data.bones, f"Controller {nm} sparito dopo la rigenerazione"
    assert not any(o.name.startswith("CTRL_DEF_SHAPE_") for o in bpy.data.objects), \
        f"Shape interne create da CTRL_DEF: {[o.name for o in bpy.data.objects]}"
    assert bpy.data.collections.get("CTRL_Shapes") is None, \
        "Collezione interna CTRL_Shapes non piu' prevista: i widget sono di Bone Widget"
    # Bone collection dei controller: "CTRLS", non piu' "CTRL"
    assert arm_data.collections.get("CTRL") is None, \
        "La bone collection dei controller non deve piu' chiamarsi CTRL"
    bcoll = arm_data.collections.get("CTRLS")
    assert bcoll is not None, "Bone collection CTRLS mancante"
    ossa_col = {b.name for b in bcoll.bones}
    for nm in nomi:
        assert nm in ossa_col, f"{nm} non e' iscritto alla bone collection CTRLS: {ossa_col}"

    # Doppia esecuzione: idempotente, non duplica bone ne' shape interne
    ossa = len(arm_data.bones)
    _seleziona_def(arm_obj, ("DEF_arm.L", "DEF_forearm.L", "DEF_hand.L"))
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Seconda generazione fallita: {res}"
    assert len(arm_data.bones) == ossa, \
        f"Seconda generazione ha duplicato i bone: {ossa} -> {len(arm_data.bones)}"
    assert not any(o.name.startswith("CTRL_DEF_SHAPE_") for o in bpy.data.objects), \
        "La seconda generazione non deve creare oggetti CTRL_DEF_SHAPE_*"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert len(reg) == 3, f"Registry duplicato dopo doppia esecuzione: {reg}"

    # Selezione parziale: DEF_arm.L -> DEF_forearm.L -> DEF_hand.L con il
    # bone centrale non selezionato
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.parent = "CHAIN"
    stg.widget_name = "Circle"
    arm_obj, arm_data = _new_armature("RigParziale")
    bpy.ops.object.mode_set(mode='EDIT')
    _build_chain(arm_data)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Solo DEF_arm.L e DEF_hand.L selezionati: DEF_forearm.L resta fuori
    _seleziona_def(arm_obj, ("DEF_arm.L", "DEF_hand.L"))
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Selezione parziale fallita: {res}"
    assert "arm.L" in arm_data.bones, "arm.L non creato con selezione parziale"
    assert "hand.L" in arm_data.bones, "hand.L non creato con selezione parziale"
    assert "forearm.L" not in arm_data.bones, \
        "forearm.L creato pur non essendo selezionato il suo DEF"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert set(reg.keys()) == {"arm.L", "hand.L"}, f"Registry inatteso: {reg}"
    for nm in ("arm.L", "hand.L"):
        path = _walk_up(arm_data.bones[nm])
        assert len(path) == len(set(path)), f"Anello di gerarchia con selezione parziale: {path}"

    # Registry corrotto: la lettura non solleva eccezioni e ritorna {}
    mod = _addon_module()
    assert mod is not None, "Modulo dell'addon non disponibile per _read_registry"
    valido = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    arm_obj["_ctrl_def_generated"] = "{bad json"
    assert mod._read_registry(arm_obj) == {}, "Registry corrotto non gestito: atteso {}"
    arm_obj["_ctrl_def_generated"] = json.dumps(valido)

    # Cancellazione manuale di un controller in Edit Mode prima di remove():
    # non deve crashare e deve pulire il registry
    bpy.ops.object.mode_set(mode='EDIT')
    ebone = arm_data.edit_bones.get("hand.L")
    assert ebone is not None, "Controller hand.L assente prima della cancellazione manuale"
    arm_data.edit_bones.remove(ebone)
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.remove()
    assert res == {'FINISHED'}, f"remove() fallito dopo cancellazione manuale: {res}"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert reg == {}, f"Registry non pulito dopo remove(): {reg}"
    assert "arm.L" not in arm_data.bones, "arm.L non rimosso da remove()"
    assert "DEF_arm.L" in arm_data.bones, "remove() non deve toccare i bone DEF"
    # Nessun controller residuo: nessuna shape interna deve restare in scena
    residui = [o.name for o in bpy.data.objects
               if o.name.startswith("CTRL_DEF_SHAPE_")]
    assert residui == [], \
        f"Shape interne non eliminate da remove(): {residui}"


def test_bind_actd_rotazione():
    _reset()
    bpy.context.scene.ctrl_def_settings.parent = "CHAIN"
    arm_obj, arm_data = _new_armature("RigBind")
    bpy.ops.object.mode_set(mode='EDIT')
    _build_chain(arm_data)
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione catena fallita: {res}"
    res_bind = bpy.ops.ctrl_def.bind_actd()
    assert res_bind == {'FINISHED'}, f"bind_actd fallito con status: {res_bind}"
    # Il DEF deve avere almeno un constraint COPY_TRANSFORMS verso il proprio CTRL
    pb_def = arm_obj.pose.bones["DEF_arm.L"]
    copies = [c for c in pb_def.constraints if c.type == 'COPY_TRANSFORMS']
    assert copies, "Nessun constraint COPY_TRANSFORMS creato su DEF_arm.L"
    assert any(c.subtarget == "arm.L" for c in copies), \
        f"Constraint non puntato al controller arm.L: {[c.subtarget for c in copies]}"
    # Rotazione del controller in Pose Mode: il DEF deve seguire esattamente.
    # In headless la matrice dei constraint si legge solo dall'oggetto valutato.
    bpy.ops.object.mode_set(mode='POSE')
    pb_ctrl = arm_obj.pose.bones["arm.L"]
    pb_ctrl.rotation_mode = 'XYZ'
    pb_ctrl.rotation_euler = (0.0, 0.0, math.radians(30.0))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    arm_eval = arm_obj.evaluated_get(dg)
    pb_def_eval = arm_eval.pose.bones["DEF_arm.L"]
    pb_ctrl_eval = arm_eval.pose.bones["arm.L"]
    rest_rot = arm_data.bones["DEF_arm.L"].matrix_local.to_3x3()
    delta = (pb_def_eval.matrix.to_3x3() @ rest_rot.inverted()).to_quaternion()
    angolo = math.degrees(delta.angle)
    assert abs(angolo - 30.0) < 0.01, f"DEF_arm.L ruotato di {angolo:.4f} gradi invece di 30 (Dependency Cycle?)"
    diff = pb_def_eval.matrix - pb_ctrl_eval.matrix
    err = max(abs(diff[r][c]) for r in range(4) for c in range(4))
    bpy.ops.object.mode_set(mode='OBJECT')
    assert err < 1e-4, f"Matrice di DEF_arm.L diversa dal controller, delta={err}"

    # Fase D: round-trip di export mappa CTRL->DEF (JSON/CSV) e preset utente.
    # Gli operatori girano senza file browser impostando filepath direttamente.
    cartella = tempfile.mkdtemp(prefix="ctrl_def_export_")
    percorso_json = os.path.join(cartella, "ctrl_def_mapping.json")
    percorso_csv = os.path.join(cartella, "ctrl_def_mapping.csv")
    percorso_preset = os.path.join(cartella, "ctrl_def_preset.json")
    # PR03: un controller registrato e poi cancellato a mano in Edit Mode non
    # deve finire nell'export: _prepare_export pota il registry prima di leggerlo
    mod = _addon_module()
    bpy.ops.object.mode_set(mode='EDIT')
    fantasma = arm_data.edit_bones.new("ghost.L")
    fantasma.head = (0.0, 0.0, 3.0)
    fantasma.tail = (0.0, 0.0, 3.2)
    bpy.ops.object.mode_set(mode='OBJECT')
    mod._mark_generated(arm_obj, "ghost.L", "DEF_ghost.L")
    assert "ghost.L" in mod._read_registry(arm_obj), \
        "Il controller orfano non e' finito nel registry prima dell'export"
    bpy.ops.object.mode_set(mode='EDIT')
    arm_data.edit_bones.remove(arm_data.edit_bones["ghost.L"])
    bpy.ops.object.mode_set(mode='OBJECT')
    res_json = bpy.ops.ctrl_def.export_json(filepath=percorso_json)
    assert res_json == {'FINISHED'}, f"export_json fallito: {res_json}"
    assert os.path.isfile(percorso_json), f"JSON di export non creato: {percorso_json}"
    with open(percorso_json, "r", encoding="utf-8") as file_json:
        mappa = json.load(file_json)
    assert mappa.get("armature") == arm_obj.name, \
        f"armature nel JSON: {mappa.get('armature')!r} invece di {arm_obj.name!r}"
    assert mappa.get("version") == "0.2.0", \
        f"version nel JSON: {mappa.get('version')!r} invece di '0.2.0'"
    assert mappa["mapping"]["arm.L"]["def"] == "DEF_arm.L", \
        f"Mappatura arm.L errata nel JSON: {mappa['mapping'].get('arm.L')!r}"
    assert set(mappa["mapping"].keys()) == {"arm.L", "forearm.L", "hand.L"}, \
        f"Chiavi della mappatura inattese: {sorted(mappa['mapping'].keys())}"
    assert "ghost.L" not in mappa["mapping"], \
        f"Il controller cancellato a mano e' finito nell'export: {sorted(mappa['mapping'].keys())}"
    registro_potato = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert "ghost.L" not in registro_potato, \
        f"export_json non ha potato il controller cancellato a mano: {sorted(registro_potato.keys())}"

    res_csv = bpy.ops.ctrl_def.export_csv(filepath=percorso_csv)
    assert res_csv == {'FINISHED'}, f"export_csv fallito: {res_csv}"
    assert os.path.isfile(percorso_csv), f"CSV di export non creato: {percorso_csv}"
    with open(percorso_csv, "r", encoding="utf-8", newline="") as file_csv:
        righe_csv = file_csv.read().splitlines()
    assert righe_csv[0] == "ctrl,def,use_deform", \
        f"Intestazione CSV inattesa: {righe_csv[0]!r}"
    assert len(righe_csv) == 4, f"Righe CSV attese 4 (intestazione + 3), trovate {righe_csv}"
    riga_arm = [r for r in righe_csv[1:] if r.startswith("arm.L,")]
    assert riga_arm == ["arm.L,DEF_arm.L,1"], \
        f"Riga CSV di arm.L inattesa: {riga_arm}"

    # Preset utente: salva lo stato corrente, lo altera e lo ricarica dal file
    stg = bpy.context.scene.ctrl_def_settings
    stg.widget_name = "Cube"
    stg.scale = 0.8
    stg.prefix_ctrl = "CTRL_"
    res_save = bpy.ops.ctrl_def.save_preset(filepath=percorso_preset)
    assert res_save == {'FINISHED'}, f"save_preset fallito: {res_save}"
    assert os.path.isfile(percorso_preset), f"Preset non creato: {percorso_preset}"
    with open(percorso_preset, "r", encoding="utf-8") as file_preset:
        preset = json.load(file_preset)
    for chiave in ("prefix_def", "prefix_ctrl", "widget_name", "scale",
                   "parent", "mirror"):
        assert chiave in preset, f"Chiave {chiave!r} assente nel preset: {preset}"
    assert preset["widget_name"] == "Cube", \
        f"widget_name salvato errato: {preset['widget_name']!r}"
    assert "color" not in preset, \
        f"Il preset non deve contenere la chiave morta 'color': {preset}"
    assert "shape" not in preset, \
        f"Il preset non deve piu' contenere la vecchia chiave 'shape': {preset}"
    assert "shape_rot" not in preset, \
        f"Il preset non deve contenere la chiave morta 'shape_rot': {preset}"
    assert abs(preset["scale"] - 0.8) < 1e-4, f"scale salvata errata: {preset['scale']!r}"
    stg.widget_name = "Circle"
    stg.scale = 1.0
    stg.prefix_ctrl = ""
    stg.mirror = True
    res_load = bpy.ops.ctrl_def.load_preset(filepath=percorso_preset)
    assert res_load == {'FINISHED'}, f"load_preset fallito: {res_load}"
    assert stg.widget_name == "Cube", \
        f"widget_name non ripristinato dal preset: {stg.widget_name!r}"
    assert abs(stg.scale - 0.8) < 1e-4, f"scale non ripristinata dal preset: {stg.scale}"
    assert stg.prefix_ctrl == "CTRL_", \
        f"prefix_ctrl non ripristinato dal preset: {stg.prefix_ctrl!r}"
    assert stg.mirror is False, f"mirror non ripristinato dal preset: {stg.mirror}"
    # Fallback legacy: un preset salvato da una versione precedente puo'
    # contenere "shape_rot" (controllo rimosso). Va ignorato, non fa fallire.
    with open(percorso_preset, "w", encoding="utf-8") as file_legacy:
        json.dump({"prefix_ctrl": "LEGACY_", "widget_name": "Sphere",
                   "scale": 1.5, "shape_rot": [90.0, 0.0, 0.0]}, file_legacy)
    res_legacy = bpy.ops.ctrl_def.load_preset(filepath=percorso_preset)
    assert res_legacy == {'FINISHED'}, \
        f"load_preset di un JSON legacy con shape_rot deve riuscire: {res_legacy}"
    assert stg.widget_name == "Sphere", \
        f"Chiavi note non applicate da un preset legacy: {stg.widget_name!r}"
    assert abs(stg.scale - 1.5) < 1e-4, \
        f"scale non applicata da un preset legacy: {stg.scale}"
    assert stg.prefix_ctrl == "LEGACY_", \
        f"prefix_ctrl non applicato da un preset legacy: {stg.prefix_ctrl!r}"
    assert not hasattr(stg, "shape_rot"), \
        "shape_rot non deve ricomparire caricando un preset legacy"
    for percorso in (percorso_json, percorso_csv, percorso_preset):
        if os.path.isfile(percorso):
            os.remove(percorso)
    os.rmdir(cartella)

    # Fase E: target IK rapido sulla catena di 3 controller arm.L ->
    # forearm.L -> hand.L gia' generata sopra (parent CHAIN).
    # La selezione si legge in Pose Mode sull'armatura attiva: si usa la stessa
    # funzione dell'addon, cosi' test e operatore partono dallo stesso stato.
    mod = _addon_module()
    mod._ensure_armature_mode(bpy.context, arm_obj, 'POSE')
    bpy.context.view_layer.update()
    for nm in ("arm.L", "forearm.L", "hand.L"):
        pbone = arm_obj.pose.bones.get(nm)
        assert pbone is not None, f"Controller {nm} assente prima di add_ik"
    registro_ik = mod._read_registry(arm_obj)
    for nm in ("arm.L", "forearm.L", "hand.L"):
        assert nm in registro_ik, f"Controller {nm} non registrato prima di add_ik: {sorted(registro_ik)}"
    _seleziona_posa(arm_obj, ("arm.L", "forearm.L", "hand.L"), True)
    # Stessa sorgente di lettura dell'operatore: pose bone selezionati.
    for nm in ("arm.L", "forearm.L", "hand.L"):
        pbone = arm_obj.pose.bones[nm]
        assert pbone.select is True, f"Pose bone {nm} non selezionato dopo _seleziona_posa"
    catene_lette = mod._selected_ctrl_chains(arm_obj)
    assert catene_lette == [["arm.L", "forearm.L", "hand.L"]], \
        f"_selected_ctrl_chains ha letto {catene_lette} invece della catena di 3"
    res_ik = bpy.ops.ctrl_def.add_ik()
    assert res_ik == {'FINISHED'}, f"add_ik fallito con status: {res_ik}"
    bone_ik = arm_data.bones.get("IK_hand.L")
    assert bone_ik is not None, "Target IK_hand.L non creato da add_ik"
    assert bone_ik.use_deform is False, "Il target IK non deve deformare la mesh"
    assert arm_data.bones.get("IK_hand.L_pole") is None, \
        "Target pole creato senza richiesta (pole=False)"
    con_ik = arm_obj.pose.bones["arm.L"].constraints.get("CTRL_DEF_IK")
    assert con_ik is not None, "Constraint CTRL_DEF_IK mancante sul primo controller arm.L"
    assert con_ik.type == 'IK', f"Constraint CTRL_DEF_IK di tipo {con_ik.type!r} invece di 'IK'"
    assert con_ik.target == arm_obj, "Il constraint IK deve puntare all'armatura stessa"
    assert con_ik.subtarget == "IK_hand.L", \
        f"subtarget del constraint IK: {con_ik.subtarget!r} invece di 'IK_hand.L'"
    assert con_ik.chain_count == 3, \
        f"chain_count del constraint IK: {con_ik.chain_count} invece di 3"
    assert con_ik.use_tail is True, "use_tail del constraint IK non attivo"
    # Nessun controller selezionato: l'operatore rifiuta l'operazione.
    # Il rifiuto arriva con report ERROR, quindi bpy.ops rilancia RuntimeError:
    # va intercettato, altrimenti il verdetto CANCELLED non e' osservabile.
    mod._ensure_armature_mode(bpy.context, arm_obj, 'POSE')
    _seleziona_posa(arm_obj, None, False)
    assert mod._selected_ctrl_chains(arm_obj) == [], \
        "La catena resta leggibile con tutti i controller deselezionati"
    res_ik_vuoto = None
    try:
        res_ik_vuoto = bpy.ops.ctrl_def.add_ik()
    except RuntimeError as exc:
        assert "No 2-3 controller chain selected" in str(exc), \
            f"Messaggio di rifiuto inatteso da add_ik: {exc}"
        res_ik_vuoto = {'CANCELLED'}
    assert res_ik_vuoto == {'CANCELLED'}, \
        f"add_ik senza controller selezionati: {res_ik_vuoto} invece di {{'CANCELLED'}}"
    # Una catena di 2 anelli (forearm.L -> hand.L) e' supportata
    mod._ensure_armature_mode(bpy.context, arm_obj, 'POSE')
    _seleziona_posa(arm_obj, ("forearm.L", "hand.L"), True)
    assert mod._selected_ctrl_chains(arm_obj) == [["forearm.L", "hand.L"]], \
        f"Catena di 2 letta da _selected_ctrl_chains: {mod._selected_ctrl_chains(arm_obj)}"
    res_ik_due = bpy.ops.ctrl_def.add_ik()
    assert res_ik_due == {'FINISHED'}, f"add_ik su catena di 2 anelli: {res_ik_due}"
    con_ik_due = arm_obj.pose.bones["forearm.L"].constraints.get("CTRL_DEF_IK")
    assert con_ik_due is not None, "Constraint CTRL_DEF_IK mancante su forearm.L (catena di 2)"
    assert con_ik_due.chain_count == 2, \
        f"chain_count della catena di 2: {con_ik_due.chain_count} invece di 2"

    # IK01/IK02: remove() deve portare via anche i target IK (compreso _pole)
    # e i constraint rimasti a puntare ai controller rimossi.
    mod._add_ik_target_chain(arm_obj, "IK", ["arm.L", "forearm.L", "hand.L"],
                             pole=True)
    assert arm_data.bones.get("IK_hand.L_pole") is not None, \
        "Target IK_hand.L_pole non creato con pole=True"
    assert arm_obj.pose.bones["arm.L"].constraints["CTRL_DEF_IK"].pole_subtarget \
        == "IK_hand.L_pole", "pole_subtarget del constraint IK non punta al target pole"
    res_remove_ik = bpy.ops.ctrl_def.remove()
    assert res_remove_ik == {'FINISHED'}, \
        f"remove() fallito con target IK presenti: {res_remove_ik}"
    assert arm_data.bones.get("IK_hand.L") is None, \
        "remove() ha lasciato il target IK_hand.L orfano"
    assert arm_data.bones.get("IK_hand.L_pole") is None, \
        "remove() ha lasciato il target IK_hand.L_pole orfano"
    nomi_rimossi = ("arm.L", "forearm.L", "hand.L", "IK_hand.L", "IK_hand.L_pole")
    for pbone in arm_obj.pose.bones:
        for con in pbone.constraints:
            assert con.name not in ("CTRL_DEF_COPY_TRANSFORMS", "CTRL_DEF_IK"), \
                f"Constraint {con.name} sopravvissuto su {pbone.name} dopo remove()"
            assert getattr(con, "subtarget", "") not in nomi_rimossi, \
                f"Constraint {con.name} su {pbone.name} punta ancora a " \
                f"{getattr(con, 'subtarget', '')!r} dopo remove()"
    assert mod._read_registry(arm_obj) == {}, \
        f"Registry non vuoto dopo remove(): {mod._read_registry(arm_obj)}"
    bpy.ops.object.mode_set(mode='OBJECT')


def test_presets():
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    # PR01/PR02: il preset utente vive nelle impostazioni di scena, quindi si
    # salva e si carica anche senza armatura e senza controller generati.
    cartella_preset = tempfile.mkdtemp(prefix="ctrl_def_preset_vuoto_")
    percorso_vuoto = os.path.join(cartella_preset, "ctrl_def_preset.json")
    stg.widget_name = "Arrow"
    stg.scale = 1.7
    res_save_vuoto = bpy.ops.ctrl_def.save_preset(filepath=percorso_vuoto)
    assert res_save_vuoto == {'FINISHED'}, \
        f"save_preset fallito a registro vuoto: {res_save_vuoto}"
    stg.widget_name = "Circle"
    stg.scale = 1.0
    res_load_vuoto = bpy.ops.ctrl_def.load_preset(filepath=percorso_vuoto)
    assert res_load_vuoto == {'FINISHED'}, \
        f"load_preset fallito a registro vuoto (serve solo la scena): {res_load_vuoto}"
    assert stg.widget_name == "Arrow" and abs(stg.scale - 1.7) < 1e-4, \
        f"Preset non applicato a registro vuoto: {stg.widget_name!r}, {stg.scale}"
    # Un file di mappatura non e' un preset: va rifiutato, non applicato a meta'
    with open(percorso_vuoto, "w", encoding="utf-8") as file_mappa:
        json.dump({"version": "0.2.0", "armature": "Rig",
                   "mapping": {"arm.L": {"def": "DEF_arm.L"}}}, file_mappa)
    stg.widget_name = "Circle"
    res_mappa = None
    try:
        res_mappa = bpy.ops.ctrl_def.load_preset(filepath=percorso_vuoto)
    except RuntimeError:
        # Il report ERROR dell'operatore arriva come RuntimeError via bpy.ops
        res_mappa = {'CANCELLED'}
    assert res_mappa == {'CANCELLED'}, \
        f"load_preset di un file di mappatura: {res_mappa} invece di {{'CANCELLED'}}"
    assert stg.widget_name == "Circle", \
        f"load_preset ha applicato un file di mappatura: widget {stg.widget_name!r}"
    os.remove(percorso_vuoto)
    os.rmdir(cartella_preset)
    # GC EnumProperty + update=: cambiare la tendina Preset applica subito i
    # valori, senza dover premere un secondo bottone
    stg.widget_name = "Circle"
    stg.scale = 1.0
    stg.parent = "CHAIN"
    stg.mirror = False
    stg.preset = "BIPED_LIMB"
    assert stg.widget_name == "Cube", \
        f"preset non applicato dall'update della tendina: {stg.widget_name!r}"
    assert abs(stg.scale - 0.8) < 1e-4, \
        f"scale non applicata dall'update della tendina: {stg.scale}"
    assert stg.parent == "CHAIN", \
        f"parent non applicato dall'update della tendina: {stg.parent!r}"
    assert stg.mirror is True, \
        f"mirror non applicato dall'update della tendina: {stg.mirror}"
    attesi = {
        "DEFAULT": ("Circle", 1.0, "CHAIN", False),
        "BIPED_LIMB": ("Cube", 0.8, "CHAIN", True),
        "ROOT_CTRL": ("Arrow", 2.0, "ROOT", False),
        "FACE": ("Sphere", 0.3, "BONE", True),
    }
    for nome, (widget, scale, parent, mirror) in attesi.items():
        stg.preset = nome
        # Con update= la tendina applica subito i valori
        assert (stg.widget_name, stg.parent, stg.mirror) == (widget, parent, mirror) \
            and abs(stg.scale - scale) < 1e-4, \
            f"Preset {nome} non applicato dall'update della tendina: " \
            f"{stg.widget_name!r}, {stg.scale}, {stg.parent!r}, {stg.mirror}"
        res = bpy.ops.ctrl_def.apply_preset()
        assert res == {'FINISHED'}, f"apply_preset fallito per {nome}: {res}"
        assert stg.widget_name == widget, \
            f"Preset {nome}: widget_name {stg.widget_name!r} invece di {widget!r}"
        assert abs(stg.scale - scale) < 1e-4, f"Preset {nome}: scale {stg.scale} invece di {scale}"
        assert stg.parent == parent, f"Preset {nome}: parent {stg.parent!r} invece di {parent!r}"
        assert stg.mirror is mirror, f"Preset {nome}: mirror {stg.mirror} invece di {mirror}"
        # Il colore non fa piu' parte dei preset (lo gestisce Bone Widget)
        assert not hasattr(stg, "color"), \
            f"Preset {nome}: la proprieta' morta 'color' non deve esistere"
    # Nessun preset deve promettere una rotazione del widget che CTRL_DEF non fa
    mod_preset = _addon_module()
    for nome, valori in mod_preset._PRESETS.items():
        assert "shape_rot" not in valori, \
            f"Preset {nome}: la chiave morta 'shape_rot' non deve esistere: {valori}"
        assert "color" not in valori, \
            f"Preset {nome}: la chiave morta 'color' non deve esistere: {valori}"
    stg_preset = bpy.context.scene.ctrl_def_settings
    assert not hasattr(stg_preset, "shape_rot"), \
        "shape_rot non deve piu' esistere nelle impostazioni dopo apply_preset"

    # Fase B: Diagnostica Pre-Flight (ctrl_def.diagnose + _diagnose_def_selection)
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    mod = _addon_module()
    assert callable(getattr(mod, "_diagnose_def_selection", None)), \
        "Helper _diagnose_def_selection mancante o non chiamabile nel modulo"

    # Caso pulito: coppia DEF_arm.L/.R completa, parent CHAIN, nessuna collisione
    arm_obj, arm_data = _new_armature("RigDiagPulita")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_arm.L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    _add_bone(arm_data, "DEF_arm.R", (0.0, 0.0, -1.0), (0.0, 0.0, -1.5))
    bpy.ops.object.mode_set(mode='OBJECT')
    diag = mod._diagnose_def_selection(arm_obj, stg)
    assert diag["zero_length"] == [], f"Bone sani segnalati come lunghezza zero: {diag}"
    assert diag["missing_mirror"] == [], f"Specchiate mancanti in una coppia completa: {diag}"
    assert diag["name_collisions"] == [], f"Collisioni inesistenti segnalate: {diag}"
    assert diag["parent_def_cycle"] is False, f"parent_def_cycle inatteso: {diag}"
    res = bpy.ops.ctrl_def.diagnose()
    assert res == {'FINISHED'}, f"ctrl_def.diagnose fallito: {res}"
    salvata = json.loads(arm_obj["_ctrl_def_last_diagnosis"])
    assert salvata == diag, f"Riepilogo JSON diverso dalla diagnosi: {salvata} != {diag}"

    # Mirror=True con .R mancante: va segnalata solo la controparte assente
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.mirror = True
    arm_obj, arm_data = _new_armature("RigDiagMirror")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_arm.L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    bpy.ops.object.mode_set(mode='OBJECT')
    diag = mod._diagnose_def_selection(arm_obj, stg)
    assert diag["missing_mirror"] == ["DEF_arm.R"], \
        f"Controparte mancante attesa ['DEF_arm.R'], trovata {diag['missing_mirror']}"
    # In Edit Mode la diagnosi legge edit_bones e deve dare lo stesso esito
    bpy.ops.object.mode_set(mode='EDIT')
    diag_edit = mod._diagnose_def_selection(arm_obj, stg)
    bpy.ops.object.mode_set(mode='OBJECT')
    assert diag_edit == diag, f"Diagnosi diversa in Edit Mode: {diag_edit} != {diag}"

    # Collisione: esiste gia' un bone "arm.L" non-DEF e non registrato
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    arm_obj, arm_data = _new_armature("RigDiagCollisione")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_arm.L", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5))
    _add_bone(arm_data, "arm.L", (0.0, 0.0, 2.0), (0.0, 0.0, 2.5))
    bpy.ops.object.mode_set(mode='OBJECT')
    diag = mod._diagnose_def_selection(arm_obj, stg)
    assert diag["name_collisions"] == ["arm.L"], \
        f"Collisione attesa ['arm.L'], trovata {diag['name_collisions']}"
    # Un controller gia' registrato non e' una collisione
    mod._mark_generated(arm_obj, "arm.L", "DEF_arm.L")
    diag = mod._diagnose_def_selection(arm_obj, stg)
    assert diag["name_collisions"] == [], \
        f"Un controller registrato non deve risultare in collisione: {diag['name_collisions']}"
    mod._forget_generated(arm_obj, "arm.L")

    # Parent "DEF": rischio Dependency Cycle segnalato anche nel riepilogo JSON
    stg.parent = "DEF"
    diag = mod._diagnose_def_selection(arm_obj, stg)
    assert diag["parent_def_cycle"] is True, f"parent='DEF' non segnalato: {diag}"
    res = bpy.ops.ctrl_def.diagnose()
    assert res == {'FINISHED'}, f"ctrl_def.diagnose fallito con parent DEF: {res}"
    salvata = json.loads(arm_obj["_ctrl_def_last_diagnosis"])
    assert salvata["parent_def_cycle"] is True, f"Riepilogo JSON senza parent_def_cycle: {salvata}"
    assert salvata["name_collisions"] == ["arm.L"], \
        f"Riepilogo JSON senza la collisione attesa: {salvata}"


def _registra_addon_se_mancante():
    """Carica e registra ../__init__.py se l'addon non e' ancora caricato.

    Serve per l'esecuzione diretta:
    blender --background --factory-startup --python tests/test_ctrl_def.py
    """
    if hasattr(bpy.ops.ctrl_def, "generate"):
        return None
    mod = _addon_module()
    mod.register()
    return mod


if __name__ == "__main__":
    _registra_addon_se_mancante()
    test_registration_elements()
    test_naming_pulito_e_prefisso()
    test_parent_chain_fk()
    test_bind_actd_rotazione()
    test_presets()
    print("RISULTATO passati=5 falliti=0 totale=5")
