# tests/test_ctrl_def.py — suite funzionale ed end-to-end per CTRL_DEF
# Eseguito dentro Blender (headless) da run_tests.ps1

import bpy
import importlib.util
import json
import math
import os
import sys
from mathutils import Vector

# Percorso dell'addon (entry point del package) per il caricamento diretto
_PATH_ADDON = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "__init__.py"))


def _addon_module():
    """Modulo dell'addon: quello del runner se presente, altrimenti dal file.

    Il caricamento da file avviene senza register(): serve solo per leggere
    bl_info e le funzioni pure (_read_registry, _mirror_name, ...).
    """
    mod = sys.modules.get("ctrl_def_addon") or sys.modules.get("ctrl_def_src")
    if mod is not None and isinstance(getattr(mod, "bl_info", None), dict):
        return mod
    spec = importlib.util.spec_from_file_location("ctrl_def_src", _PATH_ADDON)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ctrl_def_src"] = mod
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
    assert hasattr(bpy.types.Scene, "ctrl_def_settings"), "Scene.ctrl_def_settings mancante"
    stg = bpy.context.scene.ctrl_def_settings
    assert stg.prefix_ctrl == "", f"prefix_ctrl deve essere vuoto di default, trovato {stg.prefix_ctrl!r}"
    assert stg.parent == "CHAIN", f"parent di default deve essere CHAIN, trovato {stg.parent!r}"
    assert stg.prefix_def == "DEF_", f"prefix_def di default inatteso: {stg.prefix_def!r}"
    # Metadati allineati a blender_manifest.toml (maintainer) e versione 0.1.2
    mod = _addon_module()
    assert mod is not None, "Modulo dell'addon non trovato: impossibile leggere bl_info"
    bl_info = mod.bl_info
    assert bl_info["author"] == "Pierfrancesco Diodato", \
        f"bl_info['author'] inatteso: {bl_info['author']!r}"
    assert tuple(bl_info["version"]) == (0, 1, 2), \
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
    for chiave in ("msg.no_registered", "msg.bound", "shape.circle", "shape.cube",
                   "shape.sphere", "shape.arrow", "shape.cross", "color.none",
                   "color.red", "color.green", "color.blue", "parent.chain",
                   "parent.chain_tip", "parent.bone", "parent.bone_tip",
                   "parent.root", "parent.root_tip", "parent.none",
                   "parent.none_tip", "parent.def", "parent.def_tip",
                   "preset.default", "preset.biped", "preset.root", "preset.face",
                   "op.diagnose", "msg.diag_ok", "msg.diag_issues"):
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
    # Callback delle EnumProperty: con items dinamici il default e' l'indice 0,
    # quindi la prima voce deve restare quella storica di default.
    assert mod._items_shape(None, None)[0][0] == "CIRCLE", \
        f"Prima voce di _items_shape: {mod._items_shape(None, None)[0][0]!r} invece di 'CIRCLE'"
    assert mod._items_color(None, None)[0][0] == "NONE", \
        f"Prima voce di _items_color: {mod._items_color(None, None)[0][0]!r} invece di 'NONE'"
    assert mod._items_parent(None, None)[0][0] == "CHAIN", \
        f"Prima voce di _items_parent: {mod._items_parent(None, None)[0][0]!r} invece di 'CHAIN'"
    assert mod._items_preset(None, None)[0][0] == "DEFAULT", \
        f"Prima voce di _items_preset: {mod._items_preset(None, None)[0][0]!r} invece di 'DEFAULT'"
    # Etichette delle callback in IT ed EN: si forza la lingua sostituendo tr()
    # nello spazio dei nomi del modulo che definisce _items_shape (package).
    _globs_props = mod._items_shape.__globals__
    _tr_reale = _globs_props["tr"]

    def _tr_forzato(lingua):
        return lambda chiave, lang=None: _tr_reale(chiave, lingua)

    try:
        _globs_props["tr"] = _tr_forzato("it")
        voci_it = {voce[0]: voce[1] for voce in mod._items_shape(None, None)}
        _globs_props["tr"] = _tr_forzato("en")
        voci_en = {voce[0]: voce[1] for voce in mod._items_shape(None, None)}
    finally:
        _globs_props["tr"] = _tr_reale
    assert voci_it.get("CIRCLE") == "Cerchio", f"_items_shape IT: {voci_it}"
    assert voci_it.get("CUBE") == "Cubo", f"_items_shape IT (CUBE): {voci_it}"
    assert voci_it.get("SPHERE") == "Sfera", f"_items_shape IT (SPHERE): {voci_it}"
    assert voci_it.get("ARROW") == "Freccia", f"_items_shape IT (ARROW): {voci_it}"
    assert voci_it.get("CROSS") == "Croce", f"_items_shape IT (CROSS): {voci_it}"
    assert voci_en.get("CIRCLE") == "Circle", f"_items_shape EN: {voci_en}"
    assert voci_en.get("CUBE") == "Cube", f"_items_shape EN (CUBE): {voci_en}"
    assert voci_en.get("SPHERE") == "Sphere", f"_items_shape EN (SPHERE): {voci_en}"
    assert voci_en.get("ARROW") == "Arrow", f"_items_shape EN (ARROW): {voci_en}"
    assert voci_en.get("CROSS") == "Cross", f"_items_shape EN (CROSS): {voci_en}"
    # Le altre callback espongono le stesse 5/4 voci attese
    assert [v[0] for v in mod._items_color(None, None)] == ["NONE", "RED", "GREEN", "BLUE"], \
        f"Voci di _items_color inattese: {[v[0] for v in mod._items_color(None, None)]}"
    assert [v[0] for v in mod._items_parent(None, None)] == ["CHAIN", "BONE", "ROOT", "NONE", "DEF"], \
        f"Voci di _items_parent inattese: {[v[0] for v in mod._items_parent(None, None)]}"
    assert [v[0] for v in mod._items_preset(None, None)] == ["DEFAULT", "BIPED_LIMB", "ROOT_CTRL", "FACE"], \
        f"Voci di _items_preset inattese: {[v[0] for v in mod._items_preset(None, None)]}"
    # execute di generate scomposto in helper di modulo
    for nome_helper in ("_collect_def_bones", "_create_ctrl_edit_bones",
                        "_assign_ctrl_parents", "_configure_ctrl_pose_bones"):
        assert callable(getattr(mod, nome_helper, None)), \
            f"Helper di generazione {nome_helper} mancante o non chiamabile nel modulo"
    # Builder geometrici puri, dispatcher, preset, remove e draw helpers
    for nome_helper in ("_make_cube", "_make_sphere", "_make_arrow", "_make_cross",
                        "_shape_geometry", "_apply_preset_values",
                        "_remove_registered_bones", "_draw_stats_box",
                        "_draw_preset_box", "_draw_settings", "_draw_actions",
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
    for forma in ("CIRCLE", "CUBE", "SPHERE", "ARROW", "CROSS"):
        geometria = mod._shape_geometry(forma, 1.0)
        assert isinstance(geometria, tuple) and len(geometria) == 2, \
            f"_shape_geometry('{forma}') non restituisce la coppia (verts, edges): {geometria!r}"
        verts, edges = geometria
        assert len(verts) > 0, f"_shape_geometry('{forma}') senza vertici"
        assert len(edges) > 0, f"_shape_geometry('{forma}') senza spigoli"
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
    assert arm_obj.pose.bones["hand.L"].custom_shape is not None, "custom_shape mancante su hand.L"
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

    # 5. Orientamento della custom shape: gradi nella UI, radianti nel pose bone
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.shape_rot = (90.0, 0.0, 0.0)
    arm_obj, arm_data = _new_armature("RigShapeRot")
    bpy.ops.object.mode_set(mode='EDIT')
    _add_bone(arm_data, "DEF_hand.L", (0.0, 0.0, 1.0), (0.0, 0.5, 1.0))
    bpy.ops.object.mode_set(mode='OBJECT')
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione con shape_rot fallita: {res}"
    eul = arm_obj.pose.bones["hand.L"].custom_shape_rotation_euler
    atteso = (math.radians(90.0), 0.0, 0.0)
    for i, (got, exp) in enumerate(zip(eul, atteso)):
        assert abs(got - exp) < 1e-5, \
            f"custom_shape_rotation_euler[{i}] = {got} invece di {exp} (rotazione in radianti attesa)"


def test_parent_chain_fk():
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.parent = "CHAIN"
    arm_obj, arm_data = _new_armature("RigCatena")
    bpy.ops.object.mode_set(mode='EDIT')
    _build_chain(arm_data)
    bpy.ops.object.mode_set(mode='OBJECT')
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

    # Shape condivisa: 3 controller con CUBE puntano allo stesso oggetto
    stg.shape = "CUBE"
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Rigenerazione con shape CUBE fallita: {res}"
    shape_cube = bpy.data.objects.get("CTRL_DEF_SHAPE_CUBE")
    assert shape_cube is not None, "Oggetto condiviso CTRL_DEF_SHAPE_CUBE non creato"
    assert shape_cube.data.name == "CTRL_DEF_SHAPE_CUBE", \
        f"Nome mesh della shape non canonico: {shape_cube.data.name!r}"
    for nm in ("arm.L", "forearm.L", "hand.L"):
        cs = arm_obj.pose.bones[nm].custom_shape
        assert cs is not None, f"custom_shape mancante su {nm}"
        assert cs.name == "CTRL_DEF_SHAPE_CUBE", \
            f"{nm} usa {cs.name!r} invece della shape condivisa CTRL_DEF_SHAPE_CUBE"
        assert cs.name == shape_cube.name, f"{nm} non punta allo stesso oggetto degli altri controller"
    # Tutte le shape condivise finiscono nella collezione CTRL_Shapes
    col_shapes = bpy.data.collections.get("CTRL_Shapes")
    assert col_shapes is not None, "Collezione CTRL_Shapes mancante"
    assert shape_cube.name in {o.name for o in col_shapes.objects}, \
        "CTRL_DEF_SHAPE_CUBE non e' collegata alla collezione CTRL_Shapes"

    # Doppia esecuzione: idempotente, non duplica ne' bone ne' shape
    ossa = len(arm_data.bones)
    forme = len([o for o in bpy.data.objects if o.name.startswith("CTRL_DEF_SHAPE_")])
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Seconda generazione fallita: {res}"
    assert len(arm_data.bones) == ossa, \
        f"Seconda generazione ha duplicato i bone: {ossa} -> {len(arm_data.bones)}"
    assert len([o for o in bpy.data.objects if o.name.startswith("CTRL_DEF_SHAPE_")]) == forme, \
        "Seconda generazione ha duplicato le shape condivise"
    reg = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert len(reg) == 3, f"Registry duplicato dopo doppia esecuzione: {reg}"

    # Selezione parziale: DEF_arm.L -> DEF_forearm.L -> DEF_hand.L con il
    # bone centrale non selezionato
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    stg.parent = "CHAIN"
    stg.shape = "CIRCLE"
    arm_obj, arm_data = _new_armature("RigParziale")
    bpy.ops.object.mode_set(mode='EDIT')
    _build_chain(arm_data)
    arm_data.edit_bones["DEF_forearm.L"].select = False
    bpy.ops.object.mode_set(mode='OBJECT')
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
    # Nessun controller residuo: la shape condivisa non serve piu' e va eliminata
    assert bpy.data.objects.get("CTRL_DEF_SHAPE_CIRCLE") is None, \
        "La shape condivisa inutilizzata non e' stata eliminata da remove()"


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


def test_presets():
    _reset()
    stg = bpy.context.scene.ctrl_def_settings
    attesi = {
        "DEFAULT": ("CIRCLE", 1.0, "NONE", "CHAIN", False, (0.0, 0.0, 0.0)),
        "BIPED_LIMB": ("CUBE", 0.8, "RED", "CHAIN", True, (0.0, 0.0, 0.0)),
        "ROOT_CTRL": ("ARROW", 2.0, "BLUE", "ROOT", False, (90.0, 0.0, 0.0)),
        "FACE": ("SPHERE", 0.3, "GREEN", "BONE", True, (90.0, 0.0, 0.0)),
    }
    for nome, (shape, scale, color, parent, mirror, rot) in attesi.items():
        stg.preset = nome
        res = bpy.ops.ctrl_def.apply_preset()
        assert res == {'FINISHED'}, f"apply_preset fallito per {nome}: {res}"
        assert stg.shape == shape, f"Preset {nome}: shape {stg.shape!r} invece di {shape!r}"
        assert abs(stg.scale - scale) < 1e-4, f"Preset {nome}: scale {stg.scale} invece di {scale}"
        assert stg.color == color, f"Preset {nome}: color {stg.color!r} invece di {color!r}"
        assert stg.parent == parent, f"Preset {nome}: parent {stg.parent!r} invece di {parent!r}"
        assert stg.mirror is mirror, f"Preset {nome}: mirror {stg.mirror} invece di {mirror}"
        for i in range(3):
            assert abs(stg.shape_rot[i] - rot[i]) < 1e-4, \
                f"Preset {nome}: shape_rot[{i}] = {stg.shape_rot[i]} invece di {rot[i]}"

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
    spec = importlib.util.spec_from_file_location("ctrl_def", _PATH_ADDON)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ctrl_def"] = mod
    spec.loader.exec_module(mod)
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
