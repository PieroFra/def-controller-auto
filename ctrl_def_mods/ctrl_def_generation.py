# Modulo generazione: helper e operatore di creazione dei controller.
import math

import bpy
from mathutils import Vector
from bpy.types import Operator

from .ctrl_def_i18n import tr
from .ctrl_def_registry import _mark_generated
from .ctrl_def_shapes import (_ensure_collection, _get_or_create_shape,
                              _is_def_bone, _mirror_name)

# ===========================================================================
# Helper della generazione controller (usati da CTRLDEF_OT_generate)
# ===========================================================================
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


def _create_ctrl_edit_bones(ebones, da_fare, stg):
    """Crea o aggiorna gli EditBone dei controller ricalcando i bone DEF.

    Il controller e' un bone dell'armatura, non un oggetto: ne copia head,
    tail e roll, con guardia sul bone di lunghezza zero, e ha sempre
    use_deform = False.
    Restituisce (created, def_to_ctrl_name): la lista delle coppie
    (nome controller, nome DEF) e la mappa DEF -> controller.
    """
    created = []
    # Mappa DEF -> nome controller, serve per ricostruire la catena FK
    def_to_ctrl_name = {}
    for b in da_fare:
        base_name = b.name[len(stg.prefix_def):] if b.name.startswith(stg.prefix_def) else b.name
        name = (stg.prefix_ctrl or "") + base_name
        # Caso limite: senza prefisso DEF il nome coinciderebbe con quello del DEF
        if name == b.name:
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


def _configure_ctrl_pose_bones(arm, created, stg):
    """In Object Mode applica shape, scala, colore e registro ai pose bone.

    Assicura la collezione oggetti "CTRL_Shapes" e la Bone Collection "CTRL",
    usa una custom shape condivisa per forma e iscrive ogni coppia nel
    registro JSON con _mark_generated. Restituisce il numero di controller
    configurati.
    """
    # Le forme sono oggetti mesh usati solo come custom_shape dei pose bone
    col = _ensure_collection()
    # Tutti i controller generati finiscono nella bone collection "CTRL"
    bcoll = arm.data.collections.get("CTRL")
    if bcoll is None:
        bcoll = arm.data.collections.new("CTRL")
    # Palette colore in funzione dell'opzione del pannello
    palette = {"RED": "THEME04", "GREEN": "THEME07", "BLUE": "THEME12"}.get(stg.color)
    for name, def_name in created:
        bone = arm.data.bones.get(name)
        pbone = arm.pose.bones.get(name)
        if pbone is None:
            continue
        # Shape condivisa per forma: ricalcolata a ogni generate, così un
        # cambio di forma aggiorna anche i controller già esistenti
        pbone.custom_shape = _get_or_create_shape(stg.shape, col)
        pbone.custom_shape_scale_xyz = (stg.scale, stg.scale, stg.scale)
        # Rotazione locale della shape in radianti (Blender usa i radianti)
        if hasattr(pbone, "custom_shape_rotation_euler"):
            rot = stg.shape_rot
            pbone.custom_shape_rotation_euler = (
                math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
        # Colore del controller (se scelto un colore non NONE)
        if palette:
            pbone.color.palette = palette
        # Iscrizione alla bone collection "CTRL"
        if bone is not None and bcoll.name not in (c.name for c in bone.collections):
            bcoll.assign(bone)
        _mark_generated(arm, name, def_name)
    return len(created)


# ===========================================================================
# Operatori
# ===========================================================================
class CTRLDEF_OT_generate(Operator):
    bl_idname = "ctrl_def.generate"
    bl_label = tr("op.generate")
    bl_options = {'REGISTER', 'UNDO'}

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
        created, def_to_ctrl_name = _create_ctrl_edit_bones(ebones, da_fare, stg)
        _assign_ctrl_parents(ebones, da_fare, def_to_ctrl_name, stg)
        bpy.ops.object.mode_set(mode='OBJECT')
        n_ctrl = _configure_ctrl_pose_bones(arm, created, stg)
        self.report({'INFO'}, tr("msg.created") + ": " + str(n_ctrl))
        return {'FINISHED'}

