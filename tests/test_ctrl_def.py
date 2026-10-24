# tests/test_ctrl_def.py — suite funzionale ed end-to-end per CTRL_DEF
# Eseguito dentro Blender (headless) da run_tests.ps1

import bpy
from mathutils import Vector


def test_registration_elements():
    assert hasattr(bpy.types, "CTRLDEF_PT_panel"), "Panel CTRLDEF_PT_panel non registrato"
    assert hasattr(bpy.ops.ctrl_def, "generate"), "Operatore ctrl_def.generate mancante"
    assert hasattr(bpy.ops.ctrl_def, "remove"), "Operatore ctrl_def.remove mancante"
    assert hasattr(bpy.types.Scene, "ctrl_def_settings"), "Scene.ctrl_def_settings mancante"


def test_lifecycle_e2e():
    # 1. Pulisci scena
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Crea armatura di prova
    arm_data = bpy.data.armatures.new("TestArmatureData")
    arm_obj = bpy.data.objects.new("TestArmature", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    # 3. Aggiungi bone DEF in Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    ebone = arm_data.edit_bones.new("DEF_hand.L")
    ebone.head = Vector((0.0, 0.0, 1.0))
    ebone.tail = Vector((0.0, 0.5, 1.0))
    ebone.select = True
    bpy.ops.object.mode_set(mode='OBJECT')

    # 4. Genera controller
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione fallita con status: {res}"

    # 5. Verifiche creazione bone, custom shape e registry
    assert "CTRL_hand.L" in arm_data.bones, "Bone CTRL_hand.L non creato nell'armatura"
    pbone = arm_obj.pose.bones["CTRL_hand.L"]
    assert pbone.custom_shape is not None, "custom_shape non assegnata al PoseBone CTRL_hand.L"

    # Verifica registry JSON
    import json
    raw_reg = arm_obj.get("_ctrl_def_generated", "{}")
    reg_data = json.loads(raw_reg)
    assert "CTRL_hand.L" in reg_data, "CTRL_hand.L assente dal registry"
    assert reg_data["CTRL_hand.L"]["def"] == "DEF_hand.L", "Mappatura DEF errata nel registry"

    # 6. Rimozione controlli generati
    res_rem = bpy.ops.ctrl_def.remove()
    assert res_rem == {'FINISHED'}, f"Rimozione fallita con status: {res_rem}"

    # 7. Verifiche post-rimozione
    assert "CTRL_hand.L" not in arm_data.bones, "Bone CTRL_hand.L non rimosso dall'armatura"
    reg_after = json.loads(arm_obj.get("_ctrl_def_generated", "{}"))
    assert "CTRL_hand.L" not in reg_after, "CTRL_hand.L ancora presente nel registry dopo la rimozione"


def test_fase2_options():
    # 1. Pulisci scena
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 2. Impostazioni pannello: forma cubo, colore rosso, parent DEF, mirror attivo
    stg = bpy.context.scene.ctrl_def_settings
    stg.shape = "CUBE"
    stg.color = "RED"
    stg.parent = "DEF"
    stg.mirror = True
    # 3. Armatura con coppia specchiata DEF_hand.L / DEF_hand.R
    arm_data = bpy.data.armatures.new("TestArmatureData2")
    arm_obj = bpy.data.objects.new("TestArmature2", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for nm in ("DEF_hand.L", "DEF_hand.R"):
        e = arm_data.edit_bones.new(nm)
        e.head = Vector((0.0, 0.0, 1.0))
        e.tail = Vector((0.0, 0.5, 1.0))
        e.select = True
    bpy.ops.object.mode_set(mode='OBJECT')
    # 4. Genera
    res = bpy.ops.ctrl_def.generate()
    assert res == {'FINISHED'}, f"Generazione Fase 2 fallita: {res}"
    # 5. Verifiche: bone, collezione CTRL, parent, colore, custom_shape
    for dnm, cnm in (("DEF_hand.L", "CTRL_hand.L"), ("DEF_hand.R", "CTRL_hand.R")):
        assert cnm in arm_data.bones, f"Bone {cnm} non creato"
        pb = arm_obj.pose.bones[cnm]
        assert pb.custom_shape is not None, f"custom_shape mancante su {cnm}"
        assert pb.parent is not None and pb.parent.name == dnm, f"Parent di {cnm} non e' {dnm}"
        assert pb.color.palette != "DEFAULT", f"Colore non impostato su {cnm}"
    bcoll = arm_data.collections.get("CTRL")
    assert bcoll is not None, "Bone collection CTRL non creata"
    members = {b.name for b in bcoll.bones}
    assert {"CTRL_hand.L", "CTRL_hand.R"} <= members, f"Controller assenti dalla collezione CTRL: {members}"


def test_fase3_actd_compatibility():
    # Verifica che le convenzioni di naming e registry siano compatibili al 100% con ACTD
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm_data = bpy.data.armatures.new("RigCompat")
    arm_obj = bpy.data.objects.new("RigCompat", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    b = arm_data.edit_bones.new("DEF_forearm.L")
    b.head = Vector((0,0,0)); b.tail = Vector((0,1,0)); b.select = True
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.ctrl_def.generate()
    # Verifica naming standard di ACTD: CTRL_forearm.L
    assert "CTRL_forearm.L" in arm_data.bones, "Nome controller non conforme allo standard ACTD"
    # Verifica separazione dei registri JSON: non deve esistere o toccare _actd_registry
    assert "_actd_registry" not in arm_obj, "Inquinamento del registro ACTD rilevato"
    assert "_ctrl_def_generated" in arm_obj, "Registro proprietario CTRL_DEF mancante"


def test_fase4_presets():
    # Verifica corretta applicazione dei preset
    stg = bpy.context.scene.ctrl_def_settings
    stg.preset = "BIPED_LIMB"
    bpy.ops.ctrl_def.apply_preset()
    assert stg.shape == "CUBE" and stg.color == "RED" and stg.mirror is True, "Preset BIPED_LIMB non applicato correttamente"
    stg.preset = "FACE"
    bpy.ops.ctrl_def.apply_preset()
    assert stg.shape == "SPHERE" and stg.color == "GREEN" and abs(stg.scale - 0.3) < 1e-4, "Preset FACE non applicato correttamente"


if __name__ == "__main__":
    test_registration_elements()
    test_lifecycle_e2e()
    test_fase2_options()
    test_fase3_actd_compatibility()
    test_fase4_presets()
    print("RISULTATO passati=5 falliti=0 totale=5")
