# Modulo generazione: helper e operatore di creazione dei controller.
import math

import bpy
from mathutils import Vector
from bpy.types import Operator

from .ctrl_def_i18n import tr
from .ctrl_def_registry import _mark_generated
from .ctrl_def_shapes import _is_def_bone, _mirror_name

# ===========================================================================
# Helper della generazione controller (usati da CTRLDEF_OT_generate)
# ===========================================================================
def _pipeline_steps(stg):
    """Restituisce gli step della pipeline come (src_prefix, dst_prefix, role, bcoll_name).

    "DEF_CTRL" e "CUSTOM" restano il caso storico a un solo step, con ruolo e
    bone collection dedotti dal prefisso controller scelto dall'utente.
    """
    mode = getattr(stg, "pipeline_mode", "DEF_CTRL")
    ctrl_prefix = stg.prefix_ctrl or ""
    if mode == "DEF_MCH_CTRL":
        return [("DEF_", "MCH_", "MCH", "MCH"),
                ("MCH_", ctrl_prefix, "CTRL", "CTRLS")]
    if mode == "DEF_ORG_MCH_CTRL":
        return [("DEF_", "ORG_", "ORG", "ORG"),
                ("ORG_", "MCH_", "MCH", "MCH"),
                ("MCH_", ctrl_prefix, "CTRL", "CTRLS")]
    if mode == "MCH_ORG":
        return [("MCH_", "ORG_", "ORG", "ORG")]
    if mode == "ORG_CTRL":
        return [("ORG_", ctrl_prefix, "CTRL", "CTRLS")]
    # Default ("DEF_CTRL" o "CUSTOM"): il ruolo segue il prefisso controller
    if ctrl_prefix.startswith("MCH"):
        role, bcoll_name = "MCH", "MCH"
    elif ctrl_prefix.startswith("ORG"):
        role, bcoll_name = "ORG", "ORG"
    else:
        role, bcoll_name = "CTRL", "CTRLS"
    return [(stg.prefix_def, ctrl_prefix, role, bcoll_name)]


def _collect_def_bones(ebones, stg):
    """Raccoglie i bone DEF selezionati in Edit Mode.

    Se stg.mirror e' attivo aggiunge la controparte specchiata L/R, ma solo se
    esiste davvero nell'armatura e se non e' gia' nella lista: nessun bone
    viene inventato e nessun nome viene ripetuto.
    Restituisce la lista degli EditBone da elaborare.
    """
    sel = [b for b in ebones if b.select and _is_def_bone(b, stg.prefix_def)]
    da_fare = []
    visti = set()
    for b in sel:
        da_fare.append(b)
        visti.add(b.name)
        if stg.mirror:
            mname = _mirror_name(b.name)
            if mname != b.name and mname not in visti:
                mb = ebones.get(mname)
                if mb is not None and _is_def_bone(mb, stg.prefix_def):
                    da_fare.append(mb)
                    visti.add(mname)
    return da_fare


def _create_ctrl_edit_bones(ebones, da_fare, stg, src_prefix=None, dst_prefix=None, role="CTRL"):
    """Crea o aggiorna gli EditBone dei controller ricalcando i bone sorgente.

    Il controller e' un bone dell'armatura, non un oggetto: ne copia head,
    tail e roll, con guardia sul bone di lunghezza zero, e ha sempre
    use_deform = False. src_prefix / dst_prefix servono agli step della
    pipeline multi-livello; se assenti valgono i prefissi di stg.
    Restituisce (created, def_to_ctrl_name): la lista delle coppie
    (nome controller, nome sorgente) e la mappa sorgente -> controller.
    """
    created = []
    # Mappa DEF -> nome controller, serve per ricostruire la catena FK
    def_to_ctrl_name = {}
    src_p = stg.prefix_def if src_prefix is None else src_prefix
    dst_p = (stg.prefix_ctrl or "") if dst_prefix is None else dst_prefix
    for b in da_fare:
        base_name = b.name[len(src_p):] if (src_p and b.name.startswith(src_p)) else b.name
        name = dst_p + base_name
        # Caso limite: senza prefisso il nome coinciderebbe con quello sorgente
        if name == b.name:
            if role in ("MCH", "ORG"):
                name = (role + "_") + base_name
            else:
                name = "CTRL_" + base_name
        ebone = ebones.get(name)
        if ebone is None:
            ebone = ebones.new(name)
        ebone.head = b.head.copy()
        if (b.tail - b.head).length > 1e-6:
            ebone.tail = b.tail.copy()
        else:
            # Un bone di lunghezza nulla e' invalido: si allunga di un minimo
            ebone.tail = b.head + Vector((0.0, 0.1, 0.0))
        ebone.roll = b.roll
        # I controller non devono mai deformare la mesh
        ebone.use_deform = False
        def_to_ctrl_name[b.name] = name
        created.append((name, b.name))
    return created, def_to_ctrl_name


def _assign_ctrl_parents(ebones, da_fare, def_to_ctrl_name, stg):
    """Imposta il genitore di ciascun controller secondo stg.parent.

    Va chiamata dopo _create_ctrl_edit_bones: "CHAIN" richiede che tutti i
    controller esistano gia', altrimenti la catena non si chiude.
    Al termine ripristina select / select_head / select_tail sui bone DEF
    elaborati, perche' ebones.new() puo' azzerarli e una generate successiva
    deve ritrovarli senza rientrare a mano in Edit Mode.
    """
    # Radice per l'opzione parent="ROOT": primo bone senza genitore che non
    # sia un controller appena creato
    ctrl_names = set(def_to_ctrl_name.values())
    root_ebone = next((eb for eb in ebones if eb.parent is None and eb.name not in ctrl_names), None)
    # Secondo passaggio per il parent
    for b in da_fare:
        ebone = ebones.get(def_to_ctrl_name[b.name])
        if ebone is None:
            continue
        if stg.parent == "DEF":
            ebone.parent = b
        elif stg.parent == "BONE":
            ebone.parent = b.parent
        elif stg.parent == "ROOT":
            # I wrapper EditBone cambiano istanza: il confronto e' per nome
            ebone.parent = None if (root_ebone is not None and root_ebone.name == b.name) else root_ebone
        elif stg.parent == "CHAIN":
            # FK tra controller: il CTRL del figlio segue il CTRL del genitore
            if b.parent is not None and b.parent.name in def_to_ctrl_name:
                ebone.parent = ebones.get(def_to_ctrl_name[b.parent.name])
            else:
                ebone.parent = b.parent
        elif stg.parent == "NONE":
            ebone.parent = None
    for b in da_fare:
        eb = ebones.get(b.name)
        if eb is None:
            continue
        eb.select = True
        eb.select_head = True
        eb.select_tail = True


def _configure_ctrl_pose_bones(arm, created, stg, role="CTRL", bcoll_name="CTRLS"):
    """In Object Mode assegna la bone collection e iscrive i pose bone.

    Assicura la Bone Collection richiesta ("CTRLS", "MCH", "ORG") e iscrive
    ogni coppia nel registro JSON con _mark_generated, indicando il ruolo per
    i bone meccanici/originali. Con lock_mch_org attivo i bone MCH/ORG non
    vengono ne' mostrati ne' mossi, cosi' non sporcano i keyframe.
    Colore e custom shape non sono piu' gestiti qui: li governa l'estensione
    opzionale Bone Widget. Restituisce il numero di controller configurati.
    """
    bcoll = arm.data.collections.get(bcoll_name)
    if bcoll is None:
        bcoll = arm.data.collections.new(bcoll_name)
    meccanico = role in ("MCH", "ORG")
    bloccato = meccanico and getattr(stg, "lock_mch_org", True)
    for name, def_name in created:
        bone = arm.data.bones.get(name)
        pbone = arm.pose.bones.get(name)
        if pbone is None:
            continue
        # Iscrizione alla bone collection dello step corrente
        if bone is not None and bcoll.name not in (c.name for c in bone.collections):
            bcoll.assign(bone)
        if bloccato:
            pbone.lock_location = (True, True, True)
            pbone.lock_rotation = (True, True, True)
            pbone.lock_rotation_w = True
            pbone.lock_scale = (True, True, True)
        if meccanico:
            _mark_generated(arm, name, def_name, role=role)
        else:
            _mark_generated(arm, name, def_name)
    # La collection meccanica resta nascosta: si animano solo i CTRL
    if bloccato and hasattr(bcoll, "is_visible"):
        bcoll.is_visible = False
    return len(created)


# ===========================================================================
# Operatori
# ===========================================================================
class CTRLDEF_OT_generate(Operator):
    bl_idname = "ctrl_def.generate"
    bl_label = tr("op.generate")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        # Tooltip dinamico: segue la lingua attiva a ogni passaggio del mouse.
        return tr("tip.op.generate")

    def execute(self, context):
        stg = context.scene.ctrl_def_settings
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        if arm.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        ebones = arm.data.edit_bones
        da_fare = _collect_def_bones(ebones, stg)
        if not da_fare:
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'ERROR'}, tr("msg.no_def_bones"))
            return {'CANCELLED'}
        # Pipeline a uno o piu' step: ogni step consuma i bone dello step precedente
        steps = _pipeline_steps(stg)
        correnti = da_fare
        configurati = []
        for src_p, dst_p, role, bcoll_name in steps:
            created_step, mappa_step = _create_ctrl_edit_bones(
                ebones, correnti, stg,
                src_prefix=src_p, dst_prefix=dst_p, role=role)
            _assign_ctrl_parents(ebones, correnti, mappa_step, stg)
            configurati.append((created_step, role, bcoll_name))
            correnti = [ebones[nm] for nm, _ in created_step if nm in ebones]
        # La selezione torna sui bone DEF di partenza, non sugli ultimi creati
        for b in da_fare:
            eb = ebones.get(b.name)
            if eb is None:
                continue
            eb.select = True
            eb.select_head = True
            eb.select_tail = True
        bpy.ops.object.mode_set(mode='OBJECT')
        # n_ctrl resta il conteggio dell'ultimo step, cioe' i veri controller
        n_ctrl = 0
        for created_step, role, bcoll_name in configurati:
            n_ctrl = _configure_ctrl_pose_bones(
                arm, created_step, stg, role=role, bcoll_name=bcoll_name)
        # I widget non nascono con i controller: li crea l'utente a parte con
        # ctrl_def.create_widget, quando Bone Widget e' disponibile.
        # Il widget si assegna in Pose Mode: si torna in Object Mode
        if arm.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, tr("msg.created") + ": " + str(n_ctrl))
        return {'FINISHED'}

