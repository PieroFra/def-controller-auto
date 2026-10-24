# tests/test_ctrl_def.py — suite funzionale ed end-to-end per CTRL_DEF
# Eseguito dentro Blender (headless) da run_tests.ps1

import bpy
import json
import math
from mathutils import Vector


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
    assert hasattr(bpy.types.Scene, "ctrl_def_settings"), "Scene.ctrl_def_settings mancante"
    stg = bpy.context.scene.ctrl_def_settings
    assert stg.prefix_ctrl == "", f"prefix_ctrl deve essere vuoto di default, trovato {stg.prefix_ctrl!r}"
    assert stg.parent == "CHAIN", f"parent di default deve essere CHAIN, trovato {stg.parent!r}"
    assert stg.prefix_def == "DEF_", f"prefix_def di default inatteso: {stg.prefix_def!r}"


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
        "DEFAULT": ("CIRCLE", 1.0, "NONE", "CHAIN", False),
        "BIPED_LIMB": ("CUBE", 0.8, "RED", "CHAIN", True),
        "ROOT_CTRL": ("ARROW", 2.0, "BLUE", "ROOT", False),
        "FACE": ("SPHERE", 0.3, "GREEN", "BONE", True),
    }
    for nome, (shape, scale, color, parent, mirror) in attesi.items():
        stg.preset = nome
        res = bpy.ops.ctrl_def.apply_preset()
        assert res == {'FINISHED'}, f"apply_preset fallito per {nome}: {res}"
        assert stg.shape == shape, f"Preset {nome}: shape {stg.shape!r} invece di {shape!r}"
        assert abs(stg.scale - scale) < 1e-4, f"Preset {nome}: scale {stg.scale} invece di {scale}"
        assert stg.color == color, f"Preset {nome}: color {stg.color!r} invece di {color!r}"
        assert stg.parent == parent, f"Preset {nome}: parent {stg.parent!r} invece di {parent!r}"
        assert stg.mirror is mirror, f"Preset {nome}: mirror {stg.mirror} invece di {mirror}"


if __name__ == "__main__":
    test_registration_elements()
    test_naming_pulito_e_prefisso()
    test_parent_chain_fk()
    test_bind_actd_rotazione()
    test_presets()
    print("RISULTATO passati=5 falliti=0 totale=5")
