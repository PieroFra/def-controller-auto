# Modulo operatori: preset, rimozione, binding ACTD, diagnostica pre-flight,
# export della mappa CTRL->DEF e preset utente JSON.
import csv
import json
import sys

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Matrix, Vector

from .ctrl_def_i18n import tr
from .ctrl_def_registry import (_forget_generated_batch, _prune_registry,
                                _read_registry, _write_registry)
from .ctrl_def_shapes import (_bonewidget_available, _bonewidget_create,
                              _is_def_bone, _mirror_name)

# Preset rapidi dei controller: solo valori ancora posseduti dalle impostazioni
# (il colore lo gestisce Bone Widget, la rotazione pure).
# Collection gestite dall'auto-organizzazione: sono le uniche su cui
# l'operatore puo' spostare un bone. Le collection dell'utente restano intatte.
_MANAGED_COLLECTIONS = ("CTRLS", "IK", "DEF", "MCH", "ORG")


def _coll_ensure(arm_data, name):
    coll = arm_data.collections.get(name)
    if coll is None:
        coll = arm_data.collections.new(name)
    return coll


def _coll_target(name, prefix_def, registrati, registry_data=None):
    """Collection gestita di destinazione per un bone, None se non pertinente.

    L'ordine di precedenza e' MCH_ , ORG_ , ruolo registrato, prefisso DEF,
    IK_ , registry: i prefissi strutturali e il ruolo dei bone meccanici
    vincono sul registro dei controller anche con prefissi personalizzati.
    """
    if name.startswith("MCH_"):
        return "MCH"
    if name.startswith("ORG_"):
        return "ORG"
    role = (registry_data or {}).get(name, {}).get("role")
    if role in ("MCH", "ORG"):
        return role
    if prefix_def and name.startswith(prefix_def):
        return "DEF"
    if name.startswith("IK_"):
        return "IK"
    if name in registrati:
        return "CTRLS"
    return None


def _coll_unassign_managed(bone, keep_name):
    """Rimuove il bone da ogni collection gestita diversa da keep_name."""
    rimossi = 0
    for coll in list(bone.collections):
        if coll.name == keep_name or coll.name not in _MANAGED_COLLECTIONS:
            continue
        coll.unassign(bone)
        rimossi += 1
    return rimossi


def _coll_assign_target(collection, bone):
    """Assegna il bone a collection e lo toglie dalle altre collection gestite."""
    if collection.name not in (c.name for c in bone.collections):
        collection.assign(bone)
    return _coll_unassign_managed(bone, collection.name)


_PRESETS = {
    "DEFAULT": {"widget_name": "Circle", "scale": 1.0,
                "parent": "CHAIN", "mirror": False},
    "BIPED_LIMB": {"widget_name": "Cube", "scale": 0.8,
                   "parent": "CHAIN", "mirror": True},
    "ROOT_CTRL": {"widget_name": "Arrow", "scale": 2.0,
                  "parent": "ROOT", "mirror": False},
    "FACE": {"widget_name": "Sphere", "scale": 0.3,
             "parent": "BONE", "mirror": True},
}


def _apply_preset_values(stg, preset_id):
    """Applica i valori del preset a stg; preset sconosciuto non tocca nulla."""
    valori = _PRESETS.get(preset_id)
    if valori is None:
        return stg
    for nome, valore in valori.items():
        setattr(stg, nome, valore)
    return stg


class CTRLDEF_OT_apply_preset(Operator):
    bl_idname = "ctrl_def.apply_preset"
    bl_label = tr("op.apply_preset")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        # Tooltip dinamico: segue la lingua attiva a ogni passaggio del mouse.
        return tr("tip.op.apply_preset")

    def execute(self, context):
        stg = context.scene.ctrl_def_settings
        _apply_preset_values(stg, stg.preset)
        return {'FINISHED'}


def _remove_ctrl_constraints(arm, nomi_rimossi):
    """Toglie dai pose bone superstiti i constraint che puntano ai controller
    rimossi, compresi i target IK e i COPY_TRANSFORMS nativi di ACTD.

    Senza questa pulizia il depsgraph resta con constraint rotti verso bone
    inesistenti dopo ctrl_def.remove.
    """
    for pbone in arm.pose.bones:
        for con in list(pbone.constraints):
            nome = getattr(con, "name", "")
            bersaglio = getattr(con, "subtarget", "")
            if nome in ("CTRL_DEF_COPY_TRANSFORMS", "CTRL_DEF_IK"):
                pbone.constraints.remove(con)
            elif bersaglio and bersaglio in nomi_rimossi:
                pbone.constraints.remove(con)


def _remove_registered_bones(arm, data):
    """Rimuove in Edit Mode i bone registrati, i target IK e i constraint orfani.

    I target IK_<ctrl> non stanno nel registry (sono derivati, non controller):
    si eliminano insieme al controller a cui appartengono, prima di ripulire
    i constraint dei pose bone sopravvissuti. Restituisce quanti edit_bones
    registrati sono stati effettivamente rimossi.
    """
    removed = 0
    if arm.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    nomi_ik = []
    for name in list(data.keys()):
        nomi_ik.append("IK_" + name)
        nomi_ik.append("IK_" + name + "_pole")
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        ebones = arm.data.edit_bones
        for name in list(data.keys()):
            ebone = ebones.get(name)
            if ebone is not None:
                ebones.remove(ebone)
                removed += 1
        for name in nomi_ik:
            ebone = ebones.get(name)
            if ebone is not None:
                ebones.remove(ebone)
    finally:
        # Il ritorno in OBJECT e' garantito anche se un remove solleva:
        # senza di esso il depsgraph e i constraint restano incoerenti.
        if arm.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    # Una sola lettura/scrittura del registro invece di una per bone.
    _forget_generated_batch(arm, list(data.keys()))
    # I nomi restano validi anche se il bone era gia' sparito (cancellazione
    # manuale in Edit Mode): i constraint che li puntano vanno tolti lo stesso.
    nomi_rimossi = set(data.keys()) | set(nomi_ik)
    _remove_ctrl_constraints(arm, nomi_rimossi)
    return removed


def _sanitize_registry_property(arm):
    """Riporta a "{}" una proprieta' registro corrotta (JSON non valido).

    _read_registry degrada a {} senza eccezioni, ma la proprieta' resta con il
    testo rotto: il .blend salva spazzatura e un lettore esterno la rilegge
    identica. Si riscrive solo quando il contenuto non e' un dict JSON valido.
    """
    grezzo = arm.get("_ctrl_def_generated", "{}")
    try:
        parsed = json.loads(grezzo)
    except Exception:
        parsed = None
    if not isinstance(parsed, dict):
        arm["_ctrl_def_generated"] = "{}"


def _purge_unused_shapes(arm):
    """Elimina le shape della collezione CTRL_Shapes rimaste inutilizzate.

    Vale per le shape per-controller CTRL_DEF_SHAPE_* e per le vecchie shape
    condivise/legacy <nome>_shape: se un pose bone dell'armatura le usa
    ancora (es. controller cancellato a mano in Edit Mode) restano.
    """
    # I pose bone si allineano ai bone solo uscendo da Edit Mode: leggere
    # custom_shape mentre i controller appena rimossi sono ancora in Edit
    # farebbe risultare "usate" le loro shape, quindi si esce prima
    if arm.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    in_uso = {pb.custom_shape.name for pb in arm.pose.bones
              if pb.custom_shape is not None}
    col = bpy.data.collections.get("CTRL_Shapes")
    nomi_col = {o.name for o in col.objects} if col is not None else set()
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or obj.name in in_uso:
            continue
        per_controller = obj.name.startswith("CTRL_DEF_SHAPE_")
        legacy = obj.name.endswith("_shape") and obj.name in nomi_col
        if per_controller or legacy:
            # La Mesh dell'oggetto widget non muore con lui: senza questo
            # remove resta orfana in bpy.data.meshes a ogni rigenerazione.
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None and getattr(mesh, "users", 0) == 0:
                bpy.data.meshes.remove(mesh)


class CTRLDEF_OT_remove(Operator):
    bl_idname = "ctrl_def.remove"
    bl_label = tr("op.remove")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.remove")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        data = _read_registry(arm)
        if not data:
            # Nessun controller registrato: si ripuliscono solo le shape orfane
            _sanitize_registry_property(arm)
            self._purge_shapes(arm)
            self.report({'INFO'}, tr("msg.removed") + ": 0")
            return {'FINISHED'}
        # Pulizia dei constraint PRIMA di entrare in Edit Mode: i COPY_TRANSFORMS
        # e gli IK lasciati attivi mentre i controller vengono cancellati
        # generano i warning depsgraph OperationKey(BONE_DONE) a ogni
        # valutazione. I target IK sono derivati e ricostruiti qui dai nomi.
        ctrl_names = set(data.keys())
        ctrl_names |= {"IK_" + nome for nome in data}
        ctrl_names |= {"IK_" + nome + "_pole" for nome in data}
        _remove_ctrl_constraints(arm, ctrl_names)
        removed = _remove_registered_bones(arm, data)
        # Le collection gestite rimaste senza bone sporcherebbero la bacheca
        # dell'animatore: si eliminano solo quelle davvero vuote.
        self._prune_empty_collections(arm)
        # Le shape sono condivise: si eliminano solo se nessun pose bone le usa
        self._purge_shapes(arm)
        self.report({'INFO'}, tr("msg.removed") + ": " + str(removed))
        return {'FINISHED'}

    @staticmethod
    def _purge_shapes(arm):
        """Compatibilita': delega alla funzione di modulo _purge_unused_shapes."""
        return _purge_unused_shapes(arm)

    @staticmethod
    def _prune_empty_collections(arm):
        """Rimuove le collection gestite rimaste con zero bone."""
        nomi = ("CTRLS", "IK", "MCH", "ORG") + tuple(_CP_GRUPPI)
        for nome in nomi:
            coll = arm.data.collections.get(nome)
            if coll is not None and len(coll.bones) == 0:
                arm.data.collections.remove(coll)


def _ensure_armature_mode(context, arm, mode):
    """Rende attiva l'armatura e la porta nella modalita' richiesta."""
    if arm is None or arm.type != 'ARMATURE':
        return
    context.view_layer.objects.active = arm
    if arm.mode != mode:
        bpy.ops.object.mode_set(mode=mode)


def _configure_actd_settings(actd, stg):
    """Imposta i token e il filtro collezione delle settings di ACTD."""
    if hasattr(actd, "source_token"):
        actd.source_token = stg.prefix_ctrl or ""
    if hasattr(actd, "source_token_type"):
        actd.source_token_type = 'PREFIX'
    if hasattr(actd, "dest_token"):
        actd.dest_token = stg.prefix_def
    if hasattr(actd, "dest_token_type"):
        actd.dest_token_type = 'PREFIX'
    # Con token sorgente vuoto il ramo nativo di ACTD usa la collezione
    if not stg.prefix_ctrl and hasattr(actd, "use_collection_filter"):
        actd.use_collection_filter = True
        if hasattr(actd, "collection_source"):
            actd.collection_source = "CTRLS"
        if hasattr(actd, "collection_dest"):
            actd.collection_dest = ""


def _count_actd_bindings_for_arm(arm, data):
    """Conta i DEF già vincolati da ACTD verso il loro controller."""
    bound = 0
    for ctrl_name, info in data.items():
        pb = arm.pose.bones.get(info.get("def", ""))
        if pb is None:
            continue
        if any(c.type == 'COPY_TRANSFORMS' and c.subtarget == ctrl_name
               for c in pb.constraints):
            bound += 1
    return bound


def _apply_native_bindings(arm, data):
    """Constraint COPY_TRANSFORMS nativi dal registro proprietario."""
    done = 0
    for ctrl_name, info in data.items():
        def_name = info.get("def")
        pb = arm.pose.bones.get(def_name) if def_name else None
        if pb is None or arm.pose.bones.get(ctrl_name) is None:
            continue
        con = pb.constraints.get("CTRL_DEF_COPY_TRANSFORMS")
        if con is None:
            con = pb.constraints.new('COPY_TRANSFORMS')
            con.name = "CTRL_DEF_COPY_TRANSFORMS"
        con.target = arm
        con.subtarget = ctrl_name
        done += 1
    return done


class CTRLDEF_OT_bind_actd(Operator):
    bl_idname = "ctrl_def.bind_actd"
    bl_label = tr("op.bind_actd")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.bind_actd")

    def _apply_actd(self, context, stg):
        """Integrazione diretta con ACTD: token sorgente CTRL, destinazione DEF."""
        # Le pipeline multi-hop (DEF <- MCH <- CTRL o DEF <- ORG <- MCH <- CTRL)
        # le vincola il percorso nativo, che copre tutte le voci del registro.
        if getattr(stg, "pipeline_mode", "DEF_CTRL") not in ("DEF_CTRL", "CUSTOM"):
            return None
        if not (hasattr(bpy.ops, "actd") and hasattr(bpy.ops.actd, "apply_transforms")):
            return None
        actd = getattr(context.scene, "actd_settings", None)
        if actd is None:
            return None
        arm = context.active_object
        try:
            # L'operatore di ACTD richiede l'armatura attiva e in modalita' POSE,
            # altrimenti il suo poll() fallisce e si ricade sul percorso nativo
            _ensure_armature_mode(context, arm, 'POSE')
            _configure_actd_settings(actd, stg)
            return bpy.ops.actd.apply_transforms()
        except Exception:
            # Qualsiasi incompatibilità ricade sul percorso nativo
            return None
        finally:
            # Si torna in OBJECT per lasciare l'armatura nello stato di partenza
            if arm is not None and arm.type == 'ARMATURE' and arm.mode != 'OBJECT':
                try:
                    context.view_layer.objects.active = arm
                    bpy.ops.object.mode_set(mode='OBJECT')
                except RuntimeError:
                    pass

    def _count_actd_bindings(self, arm, data):
        """Conta i DEF già vincolati da ACTD verso il loro controller."""
        return _count_actd_bindings_for_arm(arm, data)

    def _apply_native(self, arm, data):
        """Constraint COPY_TRANSFORMS nativi dal registro proprietario."""
        return _apply_native_bindings(arm, data)

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        stg = context.scene.ctrl_def_settings
        _ensure_armature_mode(context, arm, 'OBJECT')
        data = _read_registry(arm)
        if not data:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        res = self._apply_actd(context, stg)
        bound = 0
        if res is not None and 'FINISHED' in res:
            bound = self._count_actd_bindings(arm, data)
        # Percorso nativo: il pulsante funziona anche senza ACTD
        if bound == 0:
            bound = self._apply_native(arm, data)
        if arm.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, tr("msg.bound") + ": " + str(bound))
        return {'FINISHED'}


# ===========================================================================
# Diagnostica Pre-Flight (Fase B)
# ===========================================================================
def _diagnose_def_selection(arm, stg):
    """Ispeziona i bone DEF prima della generazione.

    Funziona in Edit Mode (edit_bones) e in Object/Pose Mode (bones).
    Restituisce un dizionario con:
    - zero_length: bone DEF con lunghezza <= 1e-6;
    - missing_mirror: controparti specchiate mancanti con stg.mirror attivo;
    - name_collisions: controller che collidono con bone non-DEF non registrati;
    - parent_def_cycle: True se stg.parent == "DEF" (rischio Dependency Cycle).
    """
    bones = arm.data.edit_bones if arm.mode == 'EDIT' else arm.data.bones
    nomi = {b.name for b in bones}
    registro = _read_registry(arm)
    zero_length = []
    missing_mirror = []
    name_collisions = []
    for b in bones:
        if not _is_def_bone(b, stg.prefix_def):
            continue
        if b.length <= 1e-6:
            zero_length.append(b.name)
        if stg.mirror:
            mname = _mirror_name(b.name)
            if mname != b.name and mname not in nomi and mname not in missing_mirror:
                missing_mirror.append(mname)
        # Stesso calcolo del nome controller usato dalla generazione
        base_name = b.name[len(stg.prefix_def):] if b.name.startswith(stg.prefix_def) else b.name
        ctrl_name = (stg.prefix_ctrl or "") + base_name
        if ctrl_name == b.name:
            ctrl_name = "CTRL_" + base_name
        if (ctrl_name in nomi and not _is_def_bone(bones[ctrl_name], stg.prefix_def)
                and ctrl_name not in registro and ctrl_name not in name_collisions):
            name_collisions.append(ctrl_name)
    return {
        "zero_length": zero_length,
        "missing_mirror": missing_mirror,
        "name_collisions": name_collisions,
        "parent_def_cycle": stg.parent == "DEF",
    }


class CTRLDEF_OT_diagnose(Operator):
    bl_idname = "ctrl_def.diagnose"
    bl_label = tr("op.diagnose")
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.diagnose")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        stg = context.scene.ctrl_def_settings
        diagnosi = _diagnose_def_selection(arm, stg)
        arm["_ctrl_def_last_diagnosis"] = json.dumps(diagnosi)
        totale = (len(diagnosi["zero_length"]) + len(diagnosi["missing_mirror"])
                  + len(diagnosi["name_collisions"])
                  + (1 if diagnosi["parent_def_cycle"] else 0))
        if totale == 0:
            self.report({'INFO'}, tr("msg.diag_ok"))
        else:
            self.report({'WARNING'}, tr("msg.diag_issues") + ": " + str(totale))
        return {'FINISHED'}


# ===========================================================================
# Export mappa CTRL->DEF e preset utente JSON (Fase D)
# ===========================================================================
def _export_rows(arm, data):
    """Righe (ctrl, def, deform, registrato) del registro per export."""
    righe = []
    for ctrl_name, voce in data.items():
        def_name = voce.get("def", "") if isinstance(voce, dict) else ""
        # use_deform si legge dal bone DEF: i controller sono sempre non-deform
        bone = arm.data.bones.get(def_name)
        use_deform = bool(bone.use_deform) if bone is not None else False
        righe.append((ctrl_name, def_name, use_deform, True))
    return righe


def _addon_version():
    """Versione dell'addon come stringa "X.Y.Z" letta da bl_info del package."""
    pacchetto = __package__ or ""
    parti = pacchetto.split(".") if pacchetto else []
    # Dal package piu' profondo alla radice: il primo con bl_info vince
    candidati = [".".join(parti[:i]) for i in range(len(parti), -1, -1)]
    candidati.extend(("ctrl_def_addon", "ctrl_def_src", "ctrl_def"))
    for nome in candidati:
        modulo = sys.modules.get(nome) if nome else None
        info = getattr(modulo, "bl_info", None)
        if isinstance(info, dict) and info.get("version"):
            return ".".join(str(numero) for numero in info["version"])
    return "0.0.0"


# ===========================================================================
# Rig Health Score (voto 30esimi) - Modulo A
# ===========================================================================
def _rig_prefixes(arm, context):
    """Prefissi DEF/CTRL e settings, con fallback esplicito."""
    stg = None
    try:
        if context is not None:
            stg = context.scene.ctrl_def_settings
    except Exception:
        stg = None
    if stg is None:
        try:
            sc = getattr(bpy, "context", None)
            sc = getattr(sc, "scene", None) if sc is not None else None
            stg = getattr(sc, "ctrl_def_settings", None) if sc is not None else None
        except Exception:
            stg = None
    prefix_def = getattr(stg, "prefix_def", "DEF_") if stg is not None else "DEF_"
    prefix_ctrl = getattr(stg, "prefix_ctrl", "") if stg is not None else ""
    return prefix_def, prefix_ctrl, stg


_RIG_MECH_PREFIXES = ("ORG_", "ORG-", "MCH_", "MCH-", "MECH_", "MECH-")


def _rig_bones(arm):
    return list(arm.data.bones)


def _rig_is_mechanical(name):
    """ORG_/MCH_/MECH_ sono bone meccanici: non sono controller utente."""
    return name.startswith(_RIG_MECH_PREFIXES)


def _rig_is_deform_bone(name, prefix_def):
    """Bone deformante secondo il prefisso DEF corrente o i fallback noti."""
    for prefisso in (prefix_def, "DEF_", "DEF-"):
        if prefisso and name.startswith(prefisso):
            return True
    return False


def _rig_meshes(arm):
    try:
        return [o for o in bpy.data.objects
                if o.type == "MESH" and getattr(o, "find_armature", lambda: None)() == arm]
    except Exception:
        return []


def _rig_score_constraints(arm):
    """Elenco (pose_bone, constraint) di tutti i constraint dell'armatura.

    Restituisce (lista, errore). Nessun except silenzioso.
    """
    risultato = []
    try:
        for pbone in arm.pose.bones:
            for con in pbone.constraints:
                risultato.append((pbone, con))
    except Exception as exc:
        return risultato, str(exc)
    return risultato, None


def _rig_score_ik_constraints(arm):
    all_constraints, err = _rig_score_constraints(arm)
    if err is not None:
        return [], err
    try:
        return [(pb, c) for (pb, c) in all_constraints
                if getattr(c, "type", "") == "IK"], None
    except Exception as exc:
        return [], str(exc)


def _rig_score_drivers(arm):
    """Driver presenti sull'armatura (anim_data.drivers e fcurves).

    Restituisce (lista, errore). Nessun except silenzioso.
    """
    drivers = []
    try:
        ad = getattr(arm, "animation_data", None)
        if ad is not None and getattr(ad, "drivers", None) is not None:
            drivers.extend(list(ad.drivers))
    except Exception as exc:
        return drivers, str(exc)
    try:
        for d in getattr(arm.data, "drivers", []) or []:
            drivers.append(d)
    except Exception as exc:
        return drivers, str(exc)
    return drivers, None


def _rig_check_1_1(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        def_bones = [b for b in bones if _is_def_bone(b, prefix_def)]
        has_org = any(b.name.startswith("ORG_") for b in bones)
        has_mch = any(b.name.startswith("MCH_") or b.name.startswith("INT_ORG_")
                      for b in bones)
        registry = _read_registry(arm)
        ik_constraints, err = _rig_score_ik_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura IK: %s" % err)
        # La pipeline DEF_CTRL non produce ORG_/MCH_: un controller registrato
        # e' prova sufficiente che l'armatura e' controllabile, altrimenti il
        # check darebbe un falso FAIL sui rig nativi composti da soli DEF.
        if not def_bones or not (has_org or has_mch or registry):
            return (FAIL, "DEF_/ORG_/controller mancanti")
        if ik_constraints and not has_mch:
            return (FAIL, "MCH_/INT_ORG_ mancanti con IK")
        return (OK, "")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_1_2(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        bad_deform = []
        for b in bones:
            is_def = _is_def_bone(b, prefix_def)
            if is_def and not b.use_deform:
                bad_deform.append(b.name)
            if (not is_def) and b.use_deform:
                bad_deform.append(b.name)
        return (OK if not bad_deform else FAIL, "; ".join(bad_deform[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_1_3(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        parent_map = {b.name: (b.parent.name if b.parent is not None else None)
                      for b in bones}
        parent_ok = True
        dettaglio = ""
        for nome, genitore in parent_map.items():
            if genitore is not None and genitore not in bone_names:
                parent_ok = False
                dettaglio = "parent inesistente: %s" % nome
                break
        if parent_ok:
            for nome in parent_map:
                visitati = set()
                corrente = nome
                while corrente is not None:
                    if corrente in visitati:
                        parent_ok = False
                        dettaglio = "ciclo: %s" % nome
                        break
                    visitati.add(corrente)
                    corrente = parent_map.get(corrente)
                if not parent_ok:
                    break
        return (OK if parent_ok else FAIL, dettaglio)
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_1_4(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        bad_names = [b.name for b in bones
                     if " " in b.name or "__" in b.name or b.name != b.name.strip()]
        for b in bones:
            if b.name.startswith("DEF") and not b.name.startswith(prefix_def):
                bad_names.append(b.name)
        return (OK if not bad_names else FAIL, "; ".join(bad_names[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_1_5(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        meshes = _rig_meshes(arm)
        if not meshes:
            return (NT, "nessuna mesh collegata")
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        referenziati = set()
        for (pb, c) in all_constraints:
            # Il pole IK e' referenziato solo da pole_subtarget, non da subtarget.
            for attributo in ("subtarget", "pole_subtarget"):
                tgt = getattr(c, attributo, "")
                if isinstance(tgt, str) and tgt:
                    referenziati.add(tgt)
            tgt = getattr(c, "target", None)
            if isinstance(tgt, str) and tgt:
                referenziati.add(tgt)
        try:
            registry = _read_registry(arm)
            if isinstance(registry, dict):
                referenziati.update(registry.keys())
        except Exception as exc:
            return (FAIL, "errore lettura registry: %s" % exc)
        dead = []
        for b in bones:
            # ORG_/MCH_/MECH_ sono meccanici: foglia per definizione, non morti.
            if _rig_is_mechanical(b.name):
                continue
            has_child = any(bb.parent is not None and bb.parent.name == b.name
                            for bb in bones)
            if (not has_child) and (b.name not in referenziati):
                morto = True
                for mesh in meshes:
                    for vg in mesh.vertex_groups:
                        if vg.name == b.name:
                            morto = False
                            break
                    if not morto:
                        break
                if morto:
                    dead.append(b.name)
        return (OK if not dead else FAIL, "; ".join(dead[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_1_6(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        try:
            registry = _read_registry(arm)
        except Exception as exc:
            return (FAIL, "errore lettura registry: %s" % exc)
        if not registry:
            return (NT, "registro vuoto")
        mancanti = []
        for ctrl_name, voce in registry.items():
            def_name = voce.get("def", "") if isinstance(voce, dict) else ""
            if ctrl_name not in bone_names:
                mancanti.append(ctrl_name)
            if def_name and def_name not in bone_names:
                mancanti.append(def_name)
        return (OK if not mancanti else FAIL, "; ".join(mancanti[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_1(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        ctrl_names = set()
        try:
            registry = _read_registry(arm)
            if isinstance(registry, dict):
                ctrl_names.update(registry.keys())
        except Exception as exc:
            return (FAIL, "errore lettura registry: %s" % exc)
        for b in bones:
            if prefix_ctrl and b.name.startswith(prefix_ctrl):
                ctrl_names.add(b.name)
            if b.name.startswith("CTRL_") or b.name.startswith("CTRL."):
                ctrl_names.add(b.name)
        ctrl_bones = [b for b in bones if b.name in ctrl_names]
        if not ctrl_bones:
            return (NT, "nessun controller")
        senza_shape = []
        for b in ctrl_bones:
            pb = arm.pose.bones.get(b.name)
            shape = getattr(pb, "custom_shape", None) if pb is not None else None
            if shape is None:
                senza_shape.append(b.name)
        return (OK if not senza_shape else FAIL, "; ".join(senza_shape[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_2(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        drivers, err = _rig_score_drivers(arm)
        if err is not None:
            return (FAIL, "errore lettura driver: %s" % err)
        if not drivers:
            return (NT, "nessun driver")
        exprs = []
        for d in drivers:
            expr = getattr(d, "driver", None)
            expr_str = getattr(expr, "expression", "") if expr is not None else ""
            if expr_str:
                exprs.append(expr_str)
        if not exprs:
            return (NT, "espressioni driver non leggibili")
        complementari = False
        for e in exprs:
            low = e.replace(" ", "").lower()
            if "1-" in low or "1 -" in e:
                complementari = True
                break
        if complementari:
            return (OK, "")
        return (NT, "complementarieta' non verificabile")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_3(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        ik_constraints, err = _rig_score_ik_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura IK: %s" % err)
        if not ik_constraints:
            return (NT, "nessuna catena IK")
        senza_pole = []
        for (pb, c) in ik_constraints:
            pole = getattr(c, "pole_target", None)
            if pole is None:
                senza_pole.append(pb.name)
        return (OK if not senza_pole else FAIL, "; ".join(senza_pole[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_4(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        ik_constraints, err = _rig_score_ik_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura IK: %s" % err)
        if not ik_constraints:
            return (NT, "nessuna catena IK")
        poles = [(pb.name, getattr(c, "pole_angle", None))
                 for (pb, c) in ik_constraints]
        if any(v is None for (_, v) in poles):
            return (NT, "pole_angle assente")
        speculari = True
        nomi = [p[0] for p in poles]
        for i, (n, a) in enumerate(poles):
            m = _mirror_name(n)
            if m in nomi:
                j = nomi.index(m)
                a2 = poles[j][1]
                s = (a + a2)
                if not (abs(s) < 1e-3 or abs(s - (2 * 3.14159265)) < 1e-3
                        or abs(s - 3.14159265) < 1e-3):
                    speculari = False
        return (OK if speculari else FAIL, "")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_5(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        ik_constraints, err = _rig_score_ik_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura IK: %s" % err)
        if not ik_constraints:
            return (NT, "nessuna catena IK")
        problemi = []
        for (pb, c) in ik_constraints:
            sub = getattr(c, "subtarget", "")
            if not sub or sub not in bone_names:
                problemi.append("subtarget %s" % sub)
            cc = getattr(c, "chain_count", None)
            if cc is not None and not (1 <= cc <= 10):
                problemi.append("chain_count %s" % cc)
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_6(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        ik_constraints, err = _rig_score_ik_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura IK: %s" % err)
        if not ik_constraints:
            return (NT, "nessuna catena IK")
        drivers, derr = _rig_score_drivers(arm)
        if derr is not None:
            return (FAIL, "errore lettura driver: %s" % derr)
        if not drivers:
            return (NT, "nessun driver")
        pilotato = False
        for d in drivers:
            dp = getattr(d, "data_path", "") or ""
            if "influence" in dp.lower():
                pilotato = True
                break
        if pilotato:
            return (OK, "")
        return (NT, "influence non pilotata da switch")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_2_7(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        ctrl_names = set()
        try:
            registry = _read_registry(arm)
            if isinstance(registry, dict):
                ctrl_names.update(registry.keys())
        except Exception as exc:
            return (FAIL, "errore lettura registry: %s" % exc)
        for b in bones:
            if prefix_ctrl and b.name.startswith(prefix_ctrl):
                ctrl_names.add(b.name)
            if b.name.startswith("CTRL_") or b.name.startswith("CTRL."):
                ctrl_names.add(b.name)
        ctrl_bones = [b for b in bones if b.name in ctrl_names]
        if not ctrl_bones:
            return (NT, "nessun controller")
        bad = [b.name for b in ctrl_bones if b.use_deform]
        return (OK if not bad else FAIL, "; ".join(bad[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_1(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        meshes = _rig_meshes(arm)
        if not meshes:
            return (NT, "nessuna mesh")
        problemi = []
        for mesh in meshes:
            for v in mesh.data.vertices:
                totale = 0.0
                for g in v.groups:
                    try:
                        totale += g.weight
                    except Exception as exc:
                        problemi.append("peso illeggibile v%d: %s" % (v.index, exc))
                        if len(problemi) > 5:
                            break
                if len(problemi) > 5:
                    break
                if len(v.groups) > 0 and abs(totale - 1.0) > 1e-4:
                    problemi.append("v%d=%.4f" % (v.index, totale))
                    if len(problemi) > 5:
                        break
            if len(problemi) > 5:
                break
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_2(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        meshes = _rig_meshes(arm)
        if not meshes:
            return (NT, "nessuna mesh")
        zeri = 0
        for mesh in meshes:
            for v in mesh.data.vertices:
                if len(v.groups) == 0:
                    zeri += 1
        return (OK if zeri == 0 else FAIL, "%d vertici a peso 0" % zeri if zeri else "")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_3(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        def_bones = [b for b in bones if _is_def_bone(b, prefix_def)]
        meshes = _rig_meshes(arm)
        if not meshes:
            return (NT, "nessuna mesh")
        problemi = []
        for mesh in meshes:
            for vg in mesh.vertex_groups:
                if vg.name not in bone_names:
                    problemi.append("vgroup orfano %s" % vg.name)
        for b in def_bones:
            trovato = False
            for mesh in meshes:
                if b.name in [vg.name for vg in mesh.vertex_groups]:
                    trovato = True
                    break
            if not trovato:
                problemi.append("DEF senza gruppo %s" % b.name)
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_4(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        ct = [(pb, c) for (pb, c) in all_constraints
              if getattr(c, "type", "") == "COPY_TRANSFORMS"]
        if not ct:
            return (NT, "nessun Copy Transforms")
        problemi = []
        for (pb, c) in ct:
            from_space = (getattr(c, "from_space", None)
                          or getattr(c, "owner_space", None))
            to_space = (getattr(c, "to_space", None)
                        or getattr(c, "target_space", None))
            if from_space is None and to_space is None:
                problemi.append("spazi non leggibili: %s" % pb.name)
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_5(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        st = [(pb, c) for (pb, c) in all_constraints
              if getattr(c, "type", "") == "STRETCH_TO"]
        if not st:
            # Stretch To e' una feature opzionale, non un requisito di consegna.
            return (OK, "")
        problemi = []
        for (pb, c) in st:
            nome_low = pb.name.lower()
            if "finger" in nome_low or "phalan" in nome_low or "toe" in nome_low:
                problemi.append(pb.name)
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_6(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        if not all_constraints:
            return (NT, "nessun constraint")
        contatori = {}
        for (pb, c) in all_constraints:
            chiave = (pb.name, getattr(c, "type", ""))
            contatori[chiave] = contatori.get(chiave, 0) + 1
        duplicati = [k for k, v in contatori.items() if v > 1]
        return (OK if not duplicati else FAIL,
                "; ".join("%s/%s" % (k[0], k[1]) for k in duplicati[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_3_7(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        meshes = _rig_meshes(arm)
        if not meshes:
            return (NT, "nessuna mesh")
        problemi = 0
        for mesh in meshes:
            for v in mesh.data.vertices:
                for coord in v.co:
                    if coord != coord:
                        problemi += 1
                    elif abs(coord) > 1e4:
                        problemi += 1
        return (OK if problemi == 0 else FAIL,
                "%d vertici anomali" % problemi if problemi else "")
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_4_1(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        drivers, err = _rig_score_drivers(arm)
        if err is not None:
            return (FAIL, "errore lettura driver: %s" % err)
        if not drivers:
            return (NT, "nessun driver")
        driver_invalidi = []
        for d in drivers:
            try:
                if hasattr(d, "is_valid") and not d.is_valid:
                    driver_invalidi.append(str(getattr(d, "data_path", "?")))
            except Exception as exc:
                driver_invalidi.append("errore: %s" % exc)
        return (OK if not driver_invalidi else FAIL,
                "; ".join(driver_invalidi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_4_2(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        subtarget_vuoti = []
        for (pb, c) in all_constraints:
            sub = getattr(c, "subtarget", None)
            if sub is not None and hasattr(c, "subtarget"):
                if sub == "" or (sub and sub not in bone_names):
                    subtarget_vuoti.append("%s.%s" % (pb.name, sub))
        return (OK if not subtarget_vuoti else FAIL,
                "; ".join(subtarget_vuoti[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_4_3(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        orfani = []
        for (pb, c) in all_constraints:
            sub = getattr(c, "subtarget", None)
            if sub and sub not in bone_names and not any(o.name == sub for o in bpy.data.objects):
                orfani.append("%s.%s" % (pb.name, sub))
        return (OK if not orfani else FAIL, "; ".join(orfani[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_4_4(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        action_presente = False
        dettaglio = ""
        try:
            ad = getattr(arm, "animation_data", None)
            if ad is not None and getattr(ad, "action", None) is not None:
                action_presente = True
            if getattr(arm.data, "animation_data", None) is not None and \
                    getattr(arm.data.animation_data, "action", None) is not None:
                action_presente = True
        except Exception as exc:
            action_presente = True
            dettaglio = "errore lettura action: %s" % exc
        return (OK if not action_presente else FAIL, dettaglio)
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


# Gruppi pubblici del picker: l'ordine e' quello mostrato all'animatore.
_CP_GRUPPI = ("Root", "Spine", "Braccia", "Gambe", "Faccia", "IK", "Pole")


def _rig_check_5_1(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        collections = list(getattr(arm.data, "collections", []) or [])
        if not collections:
            return (NT, "nessuna bone collection")
        senza_coll = []
        for b in bones:
            # I DEF appena generati restano fuori dalle collection create
            # da generate/auto_collection: l'assenza non e' un difetto.
            if _rig_is_deform_bone(b.name, prefix_def):
                continue
            colls = getattr(b, "collections", None)
            if colls is not None and len(list(colls)) == 0:
                senza_coll.append(b.name)
        # Le collection del picker (_CP_GRUPPI) sono opzionali: su rig
        # parziali o creature il distretto anatomico puo' non esistere e
        # una collection vuota non e' un difetto. Le collection utente o
        # di layer restano invece segnalate quando vuote.
        picker = set(_CP_GRUPPI)
        coll_vuote = [c.name for c in collections
                      if c.name not in picker
                      and len(list(getattr(c, "bones", []))) == 0]
        problemi = senza_coll + ["coll vuota %s" % c for c in coll_vuote]
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_5_2(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        prefix_def, prefix_ctrl, stg = _rig_prefixes(arm, context)
        bones = _rig_bones(arm)
        bone_names = {b.name for b in bones}
        all_constraints, err = _rig_score_constraints(arm)
        if err is not None:
            return (FAIL, "errore lettura constraint: %s" % err)
        limit_types = {"LIMIT_ROTATION", "LIMIT_LOCATION", "LIMIT_SCALE"}
        limit_bones = [pb.name for (pb, c) in all_constraints
                       if getattr(c, "type", "") in limit_types]
        # I LIMIT vanno sui controller: shin/thigh/finger/toe deformanti sono
        # anatomia valida e non devono pretendere un LIMIT.
        target_names = [b.name for b in bones
                        if not _rig_is_mechanical(b.name)
                        and not _rig_is_deform_bone(b.name, prefix_def)
                        and any(k in b.name.lower() for k in
                                ("knee", "gomit", "elbow", "finger", "phalan", "toe"))]
        if not target_names:
            return (NT, "nessun ginocchio/gomito/dito")
        mancanti = [n for n in target_names if n not in limit_bones]
        return (OK if not mancanti else FAIL, "; ".join(mancanti[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_5_3(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        bones = _rig_bones(arm)
        root_bones = [b for b in bones
                      if b.name.lower() in ("root", "root_ctrl", "rootctrl")
                      or b.name.lower().startswith("root")]
        if not root_bones:
            return (NT, "nessun root")
        problemi = []
        for b in root_bones:
            v = b.tail_local - b.head_local
            if abs(v.x) > abs(v.y) and abs(v.x) > abs(v.z) and v.length > 1e-6:
                problemi.append(b.name)
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_5_4(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        posa_zero = True
        problemi = []
        try:
            for pb in arm.pose.bones:
                loc = getattr(pb, "location", None)
                rot = getattr(pb, "rotation_euler", None)
                sca = getattr(pb, "scale", None)
                if loc is not None and any(abs(x) > 1e-6 for x in loc):
                    posa_zero = False
                    problemi.append(pb.name)
                if rot is not None and any(abs(x) > 1e-6 for x in rot):
                    posa_zero = False
                    if pb.name not in problemi:
                        problemi.append(pb.name)
                if sca is not None and any(abs(x - 1.0) > 1e-6 for x in sca):
                    posa_zero = False
                    if pb.name not in problemi:
                        problemi.append(pb.name)
        except Exception as exc:
            posa_zero = False
            problemi.append("errore: %s" % exc)
        return (OK if posa_zero else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_5_5(arm, context):
    OK, FAIL = "OK", "FAIL"
    try:
        dirty = False
        errore_dirty = None
        try:
            if hasattr(arm.data, "is_dirty") and arm.data.is_dirty:
                dirty = True
        except Exception as exc:
            dirty = True
            errore_dirty = str(exc)
        probe_names = [o.name for o in bpy.data.objects
                       if any(k in o.name.lower() for k in ("test", "probe", "tmp", "debug"))]
        problemi = (["dirty"] if dirty else []) + probe_names
        if errore_dirty:
            problemi = ["errore is_dirty: %s" % errore_dirty] + problemi
        return (OK if not problemi else FAIL, "; ".join(problemi[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_check_5_6(arm, context):
    OK, FAIL, NT = "OK", "FAIL", "NON TROVATO"
    try:
        try:
            registry = _read_registry(arm)
        except Exception as exc:
            return (FAIL, "errore lettura registry: %s" % exc)
        if not isinstance(registry, dict):
            return (FAIL, "registro non valido")
        if not registry:
            return (NT, "registro vuoto")
        senza_shape = []
        for ctrl_name in registry:
            pb = arm.pose.bones.get(ctrl_name)
            shape = getattr(pb, "custom_shape", None) if pb is not None else None
            if shape is None:
                senza_shape.append(ctrl_name)
        return (OK if not senza_shape else FAIL, "; ".join(senza_shape[:5]))
    except Exception as exc:
        return (FAIL, "errore: %s" % exc)


def _rig_health_score(arm, context):
    """Esegue i controlli misurati e restituisce (report, punteggio)."""
    cat = {"STRUTTURA": [], "CONTROLLI": [], "DEFORMAZIONE": [],
           "MANUTENIBILITA": [], "CONSEGNA": []}

    def add(categoria, codice, stato, dettaglio=""):
        cat[categoria].append((codice, stato, dettaglio))

    # STRUTTURA
    add("STRUTTURA", "1.1", *_rig_check_1_1(arm, context))
    add("STRUTTURA", "1.2", *_rig_check_1_2(arm, context))
    add("STRUTTURA", "1.3", *_rig_check_1_3(arm, context))
    add("STRUTTURA", "1.4", *_rig_check_1_4(arm, context))
    add("STRUTTURA", "1.5", *_rig_check_1_5(arm, context))
    add("STRUTTURA", "1.6", *_rig_check_1_6(arm, context))

    # CONTROLLI
    add("CONTROLLI", "2.1", *_rig_check_2_1(arm, context))
    add("CONTROLLI", "2.2", *_rig_check_2_2(arm, context))
    add("CONTROLLI", "2.3", *_rig_check_2_3(arm, context))
    add("CONTROLLI", "2.4", *_rig_check_2_4(arm, context))
    add("CONTROLLI", "2.5", *_rig_check_2_5(arm, context))
    add("CONTROLLI", "2.6", *_rig_check_2_6(arm, context))
    add("CONTROLLI", "2.7", *_rig_check_2_7(arm, context))

    # DEFORMAZIONE
    add("DEFORMAZIONE", "3.1", *_rig_check_3_1(arm, context))
    add("DEFORMAZIONE", "3.2", *_rig_check_3_2(arm, context))
    add("DEFORMAZIONE", "3.3", *_rig_check_3_3(arm, context))
    add("DEFORMAZIONE", "3.4", *_rig_check_3_4(arm, context))
    add("DEFORMAZIONE", "3.5", *_rig_check_3_5(arm, context))
    add("DEFORMAZIONE", "3.6", *_rig_check_3_6(arm, context))
    add("DEFORMAZIONE", "3.7", *_rig_check_3_7(arm, context))

    # MANUTENIBILITA
    add("MANUTENIBILITA", "4.1", *_rig_check_4_1(arm, context))
    add("MANUTENIBILITA", "4.2", *_rig_check_4_2(arm, context))
    add("MANUTENIBILITA", "4.3", *_rig_check_4_3(arm, context))
    add("MANUTENIBILITA", "4.4", *_rig_check_4_4(arm, context))

    # CONSEGNA
    add("CONSEGNA", "5.1", *_rig_check_5_1(arm, context))
    add("CONSEGNA", "5.2", *_rig_check_5_2(arm, context))
    add("CONSEGNA", "5.3", *_rig_check_5_3(arm, context))
    add("CONSEGNA", "5.4", *_rig_check_5_4(arm, context))
    add("CONSEGNA", "5.5", *_rig_check_5_5(arm, context))
    add("CONSEGNA", "5.6", *_rig_check_5_6(arm, context))

    # ---------- Report ----------
    punteggio = 0
    righe_cat = []
    for nome_cat in ("STRUTTURA", "CONTROLLI", "DEFORMAZIONE",
                     "MANUTENIBILITA", "CONSEGNA"):
        voci = cat[nome_cat]
        pt = sum(1 for (_, s, _) in voci if s == "OK")
        punteggio += pt
        maxpt = len(voci)
        dettagli = []
        for (codice, stato, det) in voci:
            # Ogni voce compare nel report, anche quando e' OK: cosi' il
            # verdetto per codice resta leggibile e verificabile.
            etichetta = "%s %s" % (codice, stato)
            if det:
                etichetta += " <%s>" % det
            dettagli.append(etichetta)
        riga = "%s %d/%d" % (nome_cat, pt, maxpt)
        if dettagli:
            riga += " | " + "; ".join(dettagli)
        righe_cat.append(riga)

    totale_voci = sum(len(v) for v in cat.values())
    report = "RIG_SCORE %d/%d" % (punteggio, totale_voci)
    if totale_voci != 30:
        report = "RIG_SCORE %d/30" % punteggio
    report += " | " + " ; ".join(righe_cat)
    if "/30" not in report:
        report = report.replace("%d/%d" % (punteggio, totale_voci),
                                "%d/30" % punteggio)
    return report, punteggio


class CTRLDEF_OT_rig_score(Operator):
    bl_idname = "ctrl_def.rig_score"
    bl_label = tr("op.rig_score")
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.rig_score")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        report, punteggio = _rig_health_score(arm, context)
        print(report)
        errori_storage = []
        for chiave in ("_ctrl_def_last_rig_score", "_ctrl_def_rig_score",
                       "ctrl_def_rig_score", "_ctrl_def_last_score"):
            try:
                arm[chiave] = report
            except Exception as exc:
                errori_storage.append("%s: %s" % (chiave, exc))
        if errori_storage:
            self.report({'WARNING'},
                        "memorizzazione score fallita: " + "; ".join(errori_storage))
        self.report({'INFO'}, "%d/30" % punteggio)
        return {'FINISHED'}



# Proprieta' di CTRLDEF_PG_settings serializzate nel preset utente.
# La vecchia chiave "shape_rot" dei preset salvati con versioni precedenti non
# e' piu' letta: viene ignorata come qualsiasi chiave sconosciuta (fallback legacy).
_SETTINGS_KEYS = ("pipeline_mode", "prefix_def", "prefix_ctrl", "widget_name",
                  "scale", "parent", "mirror", "lock_mch_org",
                  "ik_align_world_y", "ik_create_pole", "ik_chain_length",
                  "ik_pole_source", "ik_target_space")


def _settings_values(stg):
    """Dizionario dei valori correnti delle impostazioni (JSON-serializzabile)."""
    valori = {}
    for chiave in _SETTINGS_KEYS:
        valori[chiave] = getattr(stg, chiave)
    return valori


def _apply_settings_values(stg, valori):
    """Applica al PropertyGroup i valori del preset, ignorando chiavi ignote.

    Un valore non valido (enum obsoleto, tipo sbagliato) viene saltato: un
    preset vecchio non deve far fallire l'intero caricamento. Un payload che
    non e' un dizionario lascia le impostazioni invariate.
    """
    if not isinstance(valori, dict):
        return stg
    for chiave in _SETTINGS_KEYS:
        if chiave not in valori:
            continue
        try:
            setattr(stg, chiave, valori[chiave])
        except (TypeError, ValueError, AttributeError):
            continue
    return stg


def _prepare_export(op, context):
    """Controlli comuni: armatura attiva e registro non vuoto.

    Il registry viene potato prima della lettura: un controller cancellato a
    mano in Edit Mode non deve finire nel JSON/CSV esportato.
    Restituisce (arm, data) oppure (None, None) dopo aver riportato l'errore.
    """
    arm = context.active_object
    if arm is None or arm.type != "ARMATURE":
        op.report({'ERROR'}, tr("msg.no_armature"))
        return None, None
    _prune_registry(arm)
    data = _read_registry(arm)
    if not data:
        op.report({'WARNING'}, tr("msg.no_registered"))
        return None, None
    return arm, data


class CTRLDEF_OT_export_json(Operator, ExportHelper):
    bl_idname = "ctrl_def.export_json"
    bl_label = tr("op.export_json")
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.export_json")

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        # Proposta accanto al .blend, senza salvare nulla a mano
        self.filepath = "//ctrl_def_mapping.json"
        return super().invoke(context, event)

    def execute(self, context):
        arm, data = _prepare_export(self, context)
        if arm is None:
            return {'CANCELLED'}
        contenuto = {"version": _addon_version(), "armature": arm.name,
                     "mapping": data}
        try:
            with open(self.filepath, "w", encoding="utf-8") as file_out:
                json.dump(contenuto, file_out, indent=2, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            self.report({'ERROR'}, tr("msg.export_failed") + ": " + str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.exported") + ": " + self.filepath)
        return {'FINISHED'}


class CTRLDEF_OT_export_csv(Operator, ExportHelper):
    bl_idname = "ctrl_def.export_csv"
    bl_label = tr("op.export_csv")
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.export_csv")

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = "//ctrl_def_mapping.csv"
        return super().invoke(context, event)

    def execute(self, context):
        arm, data = _prepare_export(self, context)
        if arm is None:
            return {'CANCELLED'}
        try:
            with open(self.filepath, "w", encoding="utf-8", newline="") as file_out:
                writer = csv.writer(file_out)
                writer.writerow(("ctrl", "def", "use_deform"))
                for ctrl_name, def_name, use_deform, _reg in _export_rows(arm, data):
                    writer.writerow((ctrl_name, def_name, int(use_deform)))
        except OSError as exc:
            self.report({'ERROR'}, tr("msg.export_failed") + ": " + str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.exported") + ": " + self.filepath)
        return {'FINISHED'}


class CTRLDEF_OT_save_preset(Operator, ExportHelper):
    bl_idname = "ctrl_def.save_preset"
    bl_label = tr("op.save_preset")
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.save_preset")

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = "//ctrl_def_preset.json"
        return super().invoke(context, event)

    def execute(self, context):
        # Il preset riguarda solo le impostazioni della scena: non serve
        # un'armatura e si puo' salvare prima di generare i controller.
        stg = context.scene.ctrl_def_settings
        try:
            with open(self.filepath, "w", encoding="utf-8") as file_out:
                json.dump(_settings_values(stg), file_out, indent=2,
                          ensure_ascii=False)
        except (OSError, TypeError) as exc:
            self.report({'ERROR'}, tr("msg.export_failed") + ": " + str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.exported") + ": " + self.filepath)
        return {'FINISHED'}


class CTRLDEF_OT_load_preset(Operator, ImportHelper):
    bl_idname = "ctrl_def.load_preset"
    bl_label = tr("op.load_preset")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.load_preset")

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = "//ctrl_def_preset.json"
        return super().invoke(context, event)

    def execute(self, context):
        # Il preset riguarda solo le impostazioni della scena: si carica anche
        # senza armatura e senza che sia stato generato alcun controller.
        try:
            with open(self.filepath, "r", encoding="utf-8") as file_in:
                valori = json.load(file_in)
        # File assente o JSON non valido: WARNING, cosi' bpy.ops restituisce
        # CANCELLED senza trasformare il report in RuntimeError.
        except (OSError, ValueError) as exc:
            self.report({'WARNING'}, tr("msg.export_failed") + ": " + str(exc))
            return {'CANCELLED'}
        # Un JSON che non e' nemmeno un oggetto non e' un preset: si rifiuta
        # con WARNING, cosi' il chiamante riceve CANCELLED senza eccezioni.
        if not isinstance(valori, dict):
            self.report({'WARNING'}, tr("msg.export_failed") + ": " + self.filepath)
            return {'CANCELLED'}
        # Un file che non e' un preset (es. ctrl_def_mapping.json) non deve
        # passare come caricamento riuscito: serve almeno una chiave nota.
        if not any(k in valori for k in _SETTINGS_KEYS):
            self.report({'ERROR'}, tr("msg.export_failed") + ": " + self.filepath)
            return {'CANCELLED'}
        _apply_settings_values(context.scene.ctrl_def_settings, valori)
        self.report({'INFO'}, tr("msg.loaded") + ": " + self.filepath)
        return {'FINISHED'}


# ===========================================================================
# Target IK rapido sui controller selezionati (Fase E)
# ===========================================================================
def _pose_bone_selected(pbone):
    """Stato di selezione del controller, con fallback tra versioni Blender.

    Da Blender 5.0 la selezione vive sul pose bone; nelle versioni precedenti
    (4.2 - 4.5) resta sulla copia Bone dell'armatura. In headless i due stati
    possono divergere: si accetta la selezione se e' attiva su almeno uno dei
    due, cosi' la catena resta leggibile in Pose Mode su Blender 5.x.
    """
    if hasattr(pbone, "select") and pbone.select:
        return True
    # Da Blender 5.0 il Bone non espone piu' "select": il fallback vale
    # solo sulle versioni in cui la proprieta' esiste ancora.
    return bool(getattr(pbone.bone, "select", False))


def _set_pose_bone_selected(pbone, stato):
    """Imposta la selezione del controller con fallback tra versioni Blender.

    Da Blender 5.0 la selezione vive sul pose bone; nelle versioni precedenti
    (4.2 - 4.5) resta sulla copia Bone dell'armatura. Si scrivono entrambe le
    proprieta' quando esistono, cosi' il bake NLA legge lo stato giusto in
    entrambe le versioni.
    """
    if hasattr(pbone, "select"):
        pbone.select = bool(stato)
    bone = getattr(pbone, "bone", None)
    if bone is not None and hasattr(bone, "select"):
        bone.select = bool(stato)


def _selected_ctrl_chains(arm, max_chain_length=None):
    """Catene di 1..N controller registrati selezionati in Pose Mode.

    Un anello vale solo se e' registrato, se ha un genitore registrato e se
    entrambi sono selezionati: la catena si legge risalendo dal bone
    selezionato, cosi' la selezione completa di una catena produce una sola
    voce. `max_chain_length` (default letto da ctrl_def_settings.ik_chain_length,
    fallback 2) limita la lunghezza massima accettata: catene piu' lunghe
    vengono ignorate. Restituisce una lista di catene ordinate genitore -> figlio.
    """
    if max_chain_length is None:
        try:
            stg = getattr(getattr(bpy, "context", None), "scene", None)
            stg = getattr(stg, "ctrl_def_settings", None) if stg is not None else None
            max_chain_length = getattr(stg, "ik_chain_length", 2) if stg is not None else 2
        except Exception:
            max_chain_length = 2
    if not isinstance(max_chain_length, int) or max_chain_length < 1:
        max_chain_length = 2
    if max_chain_length > 8:
        max_chain_length = 8

    registro = _read_registry(arm)
    if not registro:
        return []

    def selezionato(nome):
        """Selezione letta sul pose bone del nome indicato."""
        pb = arm.pose.bones.get(nome)
        return pb is not None and _pose_bone_selected(pb)

    selezione = [pb for pb in arm.pose.bones
                 if pb.name in registro and not pb.name.startswith("IK_")
                 and _pose_bone_selected(pb)]
    catene = []
    for pb in selezione:
        catena = [pb.name]
        genitore = pb.bone.parent
        while (genitore is not None and genitore.name in registro
               and selezionato(genitore.name)):
            catena.insert(0, genitore.name)
            genitore = genitore.parent
        if catena not in catene:
            catene.append(catena)
    # Solo catene massimali: un prefisso piu' corto della stessa catena
    # riscriverebbe il constraint IK gia' creato sul primo controller.
    # La massimalita' si calcola PRIMA del filtro di lunghezza: cosi' una
    # catena piu' lunga del limite scarta anche i suoi prefissi, invece di
    # lasciarne sopravvivere uno troncato.
    catene = [c for c in catene
              if not any(len(o) > len(c) and o[:len(c)] == c for o in catene)]
    # Controllo di lunghezza DOPO la costruzione della catena massimale:
    # catene troppo lunghe vengono ignorate (l'avviso e' emesso dal chiamante).
    return [c for c in catene if 1 <= len(c) <= max_chain_length]


def _mesh_pole_direction(arm, mid_pos):
    """Direzione del pole calcolata dai vertici della mesh deformata associata.

    Cerca gli oggetti mesh collegati all'armatura (modificatore Armature o
    parent) e ne ricava la normale media delle facce in spazio armatura.
    Restituisce None in caso di fallimento, cosi' il chiamante applica il
    fallback bend_dir.
    """
    try:
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
    except Exception:
        dg = None
    risultato = Vector((0.0, 0.0, 0.0))
    trovato = False
    try:
        arm_inv = arm.matrix_world.inverted()
    except Exception:
        return None
    try:
        oggetti = list(bpy.data.objects)
    except Exception:
        return None
    for obj in oggetti:
        try:
            if getattr(obj, "type", "") != "MESH":
                continue
            associato = False
            for mod in getattr(obj, "modifiers", []):
                try:
                    if (getattr(mod, "type", "") == "ARMATURE"
                            and getattr(mod, "object", None) == arm):
                        associato = True
                        break
                except Exception:
                    pass
            if not associato:
                try:
                    if getattr(obj, "parent", None) == arm:
                        associato = True
                except Exception:
                    pass
            if not associato:
                continue
            eval_obj = obj.evaluated_get(dg) if dg is not None else obj
            mesh = getattr(eval_obj, "data", None)
            if mesh is None:
                continue
            # Normale media delle facce in spazio armatura.
            for poly in getattr(mesh, "polygons", []):
                try:
                    verts = [mesh.vertices[i].co for i in poly.vertices]
                    if len(verts) < 3:
                        continue
                    # Trasforma i vertici in spazio armatura.
                    local_verts = []
                    for v in verts:
                        try:
                            world = obj.matrix_world @ v
                            local = arm_inv @ world
                            local_verts.append(local)
                        except Exception:
                            local_verts = []
                            break
                    if len(local_verts) < 3:
                        continue
                    a = local_verts[1] - local_verts[0]
                    b = local_verts[2] - local_verts[0]
                    n = a.cross(b)
                    if n.length > 1e-9:
                        risultato += n.normalized()
                        trovato = True
                except Exception:
                    continue
            # Fallback su centroide dei vertici se nessuna faccia valida.
            if not trovato:
                coords = []
                for v in getattr(mesh, "vertices", []):
                    try:
                        world = obj.matrix_world @ v.co
                        local = arm_inv @ world
                        coords.append(local)
                    except Exception:
                        coords = []
                        break
                if coords:
                    centro = Vector((0.0, 0.0, 0.0))
                    for c in coords:
                        centro += c
                    centro /= len(coords)
                    diff = centro - mid_pos
                    if diff.length > 1e-6:
                        risultato = diff
                        trovato = True
        except Exception:
            continue
    if not trovato:
        return None
    try:
        if risultato.length <= 1e-6:
            return None
        return risultato.normalized()
    except Exception:
        return None


def _add_ik_target_chain(arm, bcoll_name, chain, pole=False, align_world_y=True,
                         pole_source="BONE"):
    """Crea il target IK della catena e il vincolo IK sul primo controller.

    Il target e' un bone non-deform libero assegnato alla bone collection
    indicata. Con align_world_y vive sulla punta finale della catena (la head
    del subtarget e' il punto mirato dal constraint IK) ed e' orientato lungo
    +Y globale, roll compreso; altrimenti conserva il comportamento legacy
    (head, tail e roll dell'ultimo controller). Il constraint vive sul primo
    controller e chiude il loop su chain_count anelli. Restituisce il numero
    di target creati.
    """
    if arm is None or arm.type != 'ARMATURE' or not chain:
        return 0
    if arm.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones
    # Catena valida solo se ogni nome esiste ancora in Edit Mode: si esce
    # prima di creare le collection, cosi' non restano CTRLS/IK vuote.
    validi = all(ebones.get(nome) is not None for nome in chain)
    if not validi:
        bpy.ops.object.mode_set(mode='OBJECT')
        return 0
    ultimo = ebones.get(chain[-1])
    if ultimo is None:
        bpy.ops.object.mode_set(mode='OBJECT')
        return 0
    bcoll = arm.data.collections.get(bcoll_name)
    if bcoll is None:
        bcoll = arm.data.collections.new(bcoll_name)
    # I target IK vivono anche nella collection IK dedicata: compare subito
    # dopo add_ik, senza attendere auto_collection.
    bcoll_ik = arm.data.collections.get("IK")
    if bcoll_ik is None:
        bcoll_ik = arm.data.collections.new("IK")
    # Stessa guardia zero-length dei controller generati
    lung = (ultimo.tail - ultimo.head).length
    if lung <= 1e-6:
        lung = 0.15
    # Snodo della catena: base del pole target e punto di piega
    primo = ebones.get(chain[0])
    medio = ebones.get(chain[1]) if len(chain) >= 2 else None
    mid_pos = medio.head.copy() if medio is not None else ultimo.head.copy()
    bend_dir = Vector((0.0, -1.0, 0.0))
    # Sorgente del pole: mesh associata oppure bend_dir del bone (default).
    if str(pole_source).upper() == "MESH":
        try:
            dir_mesh = _mesh_pole_direction(arm, mid_pos)
            if dir_mesh is not None and dir_mesh.length > 1e-6:
                bend_dir = dir_mesh
            else:
                # Fallback esplicito a BONE
                if primo is not None:
                    asse = ultimo.tail - primo.head
                    if asse.length > 1e-6:
                        proiezione = primo.head + asse * (
                            (mid_pos - primo.head).dot(asse) / asse.length_squared)
                        piega = mid_pos - proiezione
                        if piega.length >= 1e-4:
                            bend_dir = piega.normalized()
        except Exception:
            # Fallback esplicito a BONE (4.2/5.2)
            if primo is not None:
                try:
                    asse = ultimo.tail - primo.head
                    if asse.length > 1e-6:
                        proiezione = primo.head + asse * (
                            (mid_pos - primo.head).dot(asse) / asse.length_squared)
                        piega = mid_pos - proiezione
                        if piega.length >= 1e-4:
                            bend_dir = piega.normalized()
                except Exception:
                    pass
    else:
        if primo is not None:
            try:
                asse = ultimo.tail - primo.head
                if asse.length > 1e-6:
                    proiezione = primo.head + asse * (
                        (mid_pos - primo.head).dot(asse) / asse.length_squared)
                    piega = mid_pos - proiezione
                    if piega.length >= 1e-4:
                        bend_dir = piega.normalized()
            except Exception:
                pass
    if align_world_y:
        # Il constraint IK mira la head del subtarget: il target nasce sulla
        # punta finale della catena e si estende lungo +Y globale
        if (ultimo.tail - ultimo.head).length > 1e-6:
            base_head = ultimo.tail.copy()
        else:
            base_head = ultimo.head.copy()
    else:
        base_head = ultimo.head.copy()
    nomi = ["IK_" + chain[-1]]
    if pole:
        nomi.append("IK_" + chain[-1] + "_pole")
    creati = 0
    for nome in nomi:
        ebone = ebones.get(nome)
        if ebone is None:
            ebone = ebones.new(nome)
        if nome.endswith("_pole"):
            ebone.head = mid_pos + bend_dir * max(lung * 1.5, 0.25)
            ebone.tail = ebone.head + Vector((0.0, max(lung * 0.5, 0.1), 0.0))
            ebone.roll = 0.0
        elif align_world_y:
            ebone.head = base_head
            ebone.tail = ebone.head + Vector((0.0, max(lung, 0.1), 0.0))
            ebone.roll = 0.0
        else:
            ebone.head = ultimo.head.copy()
            if (ultimo.tail - ultimo.head).length > 1e-6:
                ebone.tail = ultimo.tail.copy()
            else:
                ebone.tail = ultimo.head + Vector((0.0, 0.1, 0.0))
            ebone.roll = ultimo.roll
        ebone.use_deform = False
        ebone.parent = None
        bcoll.assign(ebone)
        bcoll_ik.assign(ebone)
        creati += 1
    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = arm.pose.bones.get(chain[0])
    if pbone is None:
        return creati
    con = pbone.constraints.get("CTRL_DEF_IK")
    if con is not None and con.type != 'IK':
        pbone.constraints.remove(con)
        con = None
    if con is None:
        con = pbone.constraints.new('IK')
    con.name = "CTRL_DEF_IK"
    con.target = arm
    con.subtarget = "IK_" + chain[-1]
    con.chain_count = len(chain)
    con.use_tail = True
    if pole:
        con.pole_target = arm
        con.pole_subtarget = "IK_" + chain[-1] + "_pole"
    return creati


class CTRLDEF_OT_add_ik(Operator):
    bl_idname = "ctrl_def.add_ik"
    bl_label = tr("op.add_ik")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.add_ik")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        # Modalita' di partenza: chi lancia l'operatore da Pose Mode deve
        # ritrovarsi in Pose Mode, con i target appena creati selezionati.
        modo_iniziale = arm.mode
        # La selezione dei bone si legge solo in Pose Mode
        _ensure_armature_mode(context, arm, 'POSE')
        # La selezione scritta dai test/pannelli va consolidata prima della lettura
        context.view_layer.update()
        stg = getattr(context.scene, "ctrl_def_settings", None)
        limite = getattr(stg, "ik_chain_length", 2) if stg is not None else 2
        catene = _selected_ctrl_chains(arm)
        if catene and limite >= 2 and all(len(c) == 1 for c in catene):
            # Con il solo controller di punta selezionato la catena si
            # ricostruisce risalendo i genitori registrati finche' il limite
            # lo consente: ["hand.L"] -> ["upperarm.L", "forearm.L", "hand.L"].
            registro = _read_registry(arm)
            estese = []
            for catena in catene:
                nuova = list(catena)
                pb = arm.pose.bones.get(nuova[0])
                while pb is not None and len(nuova) < limite:
                    genitore = pb.parent
                    if genitore is None or genitore.name not in registro:
                        break
                    nuova.insert(0, genitore.name)
                    pb = genitore
                # Deduplica: stessa catena o catena gia' contenuta come coda
                # di una piu' lunga (caso di punte selezionate in parallelo).
                if any(nuova[-len(k):] == k for k in estese):
                    continue
                estese = [k for k in estese if nuova[-len(k):] != k]
                estese.append(nuova)
            catene = estese
        if not catene:
            # Avviso chiaro quando i bone selezionati formano una catena
            # piu' lunga del limite impostato: non si scarta in silenzio.
            catene_lunghe = _selected_ctrl_chains(arm, max_chain_length=8)
            if catene_lunghe:
                _ensure_armature_mode(context, arm, 'OBJECT')
                self.report({'WARNING'},
                            "Catena IK troppo lunga: massimo %d controller consecutivi"
                            % limite)
                return {'CANCELLED'}
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}
        stg = getattr(context.scene, "ctrl_def_settings", None)
        pole = bool(getattr(stg, "ik_create_pole", False))
        align_world_y = bool(getattr(stg, "ik_align_world_y", True))
        pole_source = getattr(stg, "ik_pole_source", "BONE")
        creati = 0
        for catena in catene:
            creati += _add_ik_target_chain(arm, "CTRLS", catena, pole=pole,
                                           align_world_y=align_world_y,
                                           pole_source=pole_source)
        if modo_iniziale == 'POSE':
            # Si resta in Pose Mode e si selezionano i target creati, cosi'
            # l'utente puo' subito posare la catena senza cambiare modalita'.
            _ensure_armature_mode(context, arm, 'POSE')
            for catena in catene:
                pb_ik = arm.pose.bones.get("IK_" + catena[-1])
                if pb_ik is not None:
                    _set_pose_bone_selected(pb_ik, True)
            context.view_layer.update()
        else:
            _ensure_armature_mode(context, arm, 'OBJECT')
        self.report({'INFO'}, tr("msg.ik_created") + ": " + str(creati))
        return {'FINISHED'}


class CTRLDEF_OT_set_ik_target_space(Operator):
    bl_idname = "ctrl_def.set_ik_target_space"
    bl_label = tr("op.set_ik_target_space")
    bl_options = {'REGISTER', 'UNDO'}

    space: EnumProperty(
        name=tr("panel.ik_target_space"),
        description=tr("tip.prop.ik_target_space"),
        items=[
            ("WORLD", tr("space.world"), ""),
            ("LOCAL", tr("space.local"), ""),
            ("OBJECT", tr("space.object"), ""),
        ],
        default="WORLD",
    )

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.set_ik_target_space")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        stg = getattr(context.scene, "ctrl_def_settings", None)
        _ensure_armature_mode(context, arm, 'POSE')
        try:
            context.view_layer.update()
        except Exception:
            pass
        try:
            _prune_registry(arm)
        except Exception:
            pass
        targets = []
        try:
            for pb in arm.pose.bones:
                con = pb.constraints.get("CTRL_DEF_IK")
                if con is None or getattr(con, "type", "") != 'IK':
                    continue
                sub = getattr(con, "subtarget", "")
                if not sub:
                    continue
                targets.append((pb, con, sub))
        except Exception:
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}
        if not targets:
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}

        new_space_raw = getattr(self, "space", "WORLD")
        mapping = {"WORLD": "WORLD", "LOCAL": "LOCAL", "OBJECT": "CUSTOM",
                   "OGGETTO": "CUSTOM", "CUSTOM": "CUSTOM"}
        new_constraint_space = mapping.get(str(new_space_raw).upper(), "WORLD")
        new_ui_space = "OBJECT" if new_constraint_space == "CUSTOM" else new_constraint_space

        captured = []
        try:
            dg = context.evaluated_depsgraph_get()
            dg.update()
            arm_eval = arm.evaluated_get(dg)
        except Exception:
            arm_eval = arm
        for pb, con, sub in targets:
            tb = arm.pose.bones.get(sub)
            if tb is None:
                continue
            try:
                rest = arm.data.bones[sub].matrix_local.copy()
            except Exception:
                rest = Matrix.Identity(4)
            cur_cs = getattr(con, "target_space", "WORLD")
            if cur_cs == 'LOCAL':
                try:
                    eff = tb.matrix_basis.copy()
                except Exception:
                    eff = Matrix.Identity(4)
            else:
                try:
                    eff = arm_eval.pose.bones[sub].matrix.copy()
                except Exception:
                    try:
                        eff = tb.matrix.copy()
                    except Exception:
                        eff = Matrix.Identity(4)
            captured.append((pb, con, sub, rest, cur_cs, eff))

        try:
            for pb, con, sub, rest, cur_cs, eff in captured:
                tb = arm.pose.bones.get(sub)
                if tb is None:
                    continue
                try:
                    con.target_space = new_constraint_space
                except Exception:
                    _ensure_armature_mode(context, arm, 'OBJECT')
                    self.report({'ERROR'}, tr("msg.no_ik_chain"))
                    return {'CANCELLED'}
                if new_constraint_space == 'CUSTOM':
                    try:
                        con.space_object = arm
                    except Exception:
                        _ensure_armature_mode(context, arm, 'OBJECT')
                        self.report({'ERROR'}, tr("msg.no_ik_chain"))
                        return {'CANCELLED'}
                try:
                    if new_constraint_space == 'LOCAL':
                        tb.matrix_basis = eff.copy()
                    else:
                        try:
                            tb.matrix_basis = rest.inverted() @ eff
                        except Exception:
                            tb.matrix_basis = eff.copy()
                except Exception:
                    _ensure_armature_mode(context, arm, 'OBJECT')
                    self.report({'ERROR'}, tr("msg.no_ik_chain"))
                    return {'CANCELLED'}
            context.view_layer.update()
            try:
                dg2 = context.evaluated_depsgraph_get()
                dg2.update()
            except Exception:
                pass
        except Exception:
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}

        if stg is not None:
            try:
                stg.ik_target_space = new_ui_space
            except Exception:
                try:
                    stg.ik_target_space = str(new_space_raw).upper()
                except Exception:
                    pass

        _ensure_armature_mode(context, arm, 'OBJECT')
        self.report({'INFO'}, tr("msg.ik_created"))
        return {'FINISHED'}


class CTRLDEF_OT_create_widget(Operator):
    bl_idname = "ctrl_def.create_widget"
    bl_label = tr("op.bw_create")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.create_widget")

    def execute(self, context):
        # I widget sono delegati a Bone Widget: senza l'estensione non si
        # crea nulla e non si sollevano eccezioni.
        if not _bonewidget_available():
            self.report({'WARNING'}, tr("msg.bw_missing"))
            return {'CANCELLED'}
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        # La selezione dei bone si legge solo in Pose Mode
        _ensure_armature_mode(context, arm, 'POSE')
        # La selezione scritta dai test/pannelli va consolidata prima della lettura
        context.view_layer.update()
        registro = _read_registry(arm)
        scelti = [pb.name for pb in arm.pose.bones
                  if pb.name in registro and _pose_bone_selected(pb)]
        if not scelti:
            # Nessun controller selezionato: il widget va a tutti i registrati
            scelti = list(registro.keys())
        if not scelti:
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        stg = context.scene.ctrl_def_settings
        if not _bonewidget_create(arm, scelti, stg.widget_name, stg.scale):
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'WARNING'}, tr("msg.bw_missing"))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("op.bw_create") + ": " + str(len(scelti)))
        return {'FINISHED'}


 
 
def _collect_ik_chains(arm, data):
    """Catene di controller registrati vincolate da un constraint IK."""
    chains = []
    seen = set()
    if arm is None or not data:
        return chains
    for pb in arm.pose.bones:
        con = pb.constraints.get("CTRL_DEF_IK")
        if con is None or getattr(con, "type", "") != 'IK':
            continue
        chain_count = getattr(con, "chain_count", 1)
        if not isinstance(chain_count, int) or chain_count < 1:
            chain_count = 1
        if chain_count > 8:
            chain_count = 8
        if pb.name not in data:
            continue
        chain = [pb.name]
        current = pb
        for _ in range(chain_count - 1):
            next_name = None
            for child_bone in getattr(current.bone, "children", []):
                if (child_bone.name in data and child_bone.name not in chain
                        and not child_bone.name.startswith("IK_")):
                    next_name = child_bone.name
                    break
            if next_name is None:
                for cand in arm.pose.bones:
                    if (cand.bone.parent is current.bone
                            and cand.name in data and cand.name not in chain
                            and not cand.name.startswith("IK_")):
                        next_name = cand.name
                        break
            if next_name is None:
                break
            chain.append(next_name)
            current = arm.pose.bones.get(next_name)
            if current is None:
                break
        if tuple(chain) not in seen:
            seen.add(tuple(chain))
            chains.append(chain)
    if not chains:
        try:
            for catena in _selected_ctrl_chains(arm):
                if not catena:
                    continue
                first_pb = arm.pose.bones.get(catena[0])
                if first_pb is None:
                    continue
                if first_pb.constraints.get("CTRL_DEF_IK") is not None:
                    if tuple(catena) not in seen:
                        seen.add(tuple(catena))
                        chains.append(list(catena))
        except Exception:
            pass
    return chains


class CTRLDEF_OT_snap_ik_to_fk(Operator):
    bl_idname = "ctrl_def.snap_ik_to_fk"
    bl_label = tr("op.snap_ik_to_fk")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.snap_ik_to_fk")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, arm, 'POSE')
        try:
            _prune_registry(arm)
        except Exception:
            pass
        data = _read_registry(arm)
        if not data:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        context.view_layer.update()
        dg = context.evaluated_depsgraph_get()
        dg.update()
        arm_eval = arm.evaluated_get(dg)
        chains = _collect_ik_chains(arm, data)
        if not chains:
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}
        visual_matrix = {}
        parent_visual_matrix = {}
        for chain in chains:
            for name in chain:
                if name not in visual_matrix:
                    pb_eval = arm_eval.pose.bones.get(name)
                    if pb_eval is not None:
                        visual_matrix[name] = pb_eval.matrix.copy()
                pb = arm.pose.bones.get(name)
                if pb is None:
                    continue
                parent = pb.parent
                if parent is not None and parent.name not in parent_visual_matrix:
                    if parent.name in arm_eval.pose.bones:
                        parent_visual_matrix[parent.name] = (
                            arm_eval.pose.bones[parent.name].matrix.copy())
                    else:
                        parent_visual_matrix[parent.name] = parent.matrix.copy()
        total = 0
        for chain in chains:
            for name in chain:
                pb = arm.pose.bones.get(name)
                if pb is None or name not in visual_matrix:
                    continue
                target = visual_matrix[name]
                parent = pb.parent
                if parent is None:
                    rest_local = pb.bone.matrix_local.copy()
                    pm = None
                else:
                    rest_local = (parent.bone.matrix_local.inverted()
                                  @ pb.bone.matrix_local)
                    pm = parent_visual_matrix.get(parent.name)
                if pm is None:
                    basis = rest_local.inverted() @ target
                else:
                    basis = rest_local.inverted() @ pm.inverted() @ target
                pb.matrix_basis = basis
                total += 1
        context.view_layer.update()
        try:
            dg2 = context.evaluated_depsgraph_get()
            dg2.update()
        except Exception:
            pass
        self.report({'INFO'}, tr("msg.ik_created") + ": " + str(total))
        return {'FINISHED'}


def _remap_armature_by_name(name):
    if not name:
        return None
    try:
        obj = bpy.data.objects.get(name)
    except Exception:
        return None
    if obj is None or getattr(obj, "type", None) != "ARMATURE":
        return None
    return obj


def _remap_registry_def_to_ctrl(data):
    out = {}
    if not isinstance(data, dict):
        return out
    for ctrl_name, voce in data.items():
        def_name = voce.get("def", "") if isinstance(voce, dict) else ""
        if def_name and def_name not in out:
            out[def_name] = ctrl_name
    return out


def _remap_shared_defs(src_data, dst_data):
    src_defs = set(_remap_registry_def_to_ctrl(src_data).keys())
    dst_defs = set(_remap_registry_def_to_ctrl(dst_data).keys())
    return sorted(src_defs & dst_defs)


def _remap_pose_depth(pbone):
    depth = 0
    cur = getattr(pbone, "parent", None)
    while cur is not None:
        depth += 1
        cur = getattr(cur, "parent", None)
    return depth


class CTRLDEF_OT_remap(Operator):
    bl_idname = "ctrl_def.remap"
    bl_label = tr("op.remap")
    bl_options = {'REGISTER', 'UNDO'}

    source_armature: StringProperty(name="Source Armature", default="")
    target_armature: StringProperty(name="Target Armature", default="")

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.remap")

    def execute(self, context):
        src_obj = _remap_armature_by_name(self.source_armature)
        dst_obj = _remap_armature_by_name(self.target_armature)
        if src_obj is None or dst_obj is None:
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        if src_obj == dst_obj:
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        try:
            _prune_registry(src_obj)
        except Exception:
            pass
        try:
            _prune_registry(dst_obj)
        except Exception:
            pass
        src_data = _read_registry(src_obj)
        dst_data = _read_registry(dst_obj)
        if not src_data or not dst_data:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        src_def_to_ctrl = _remap_registry_def_to_ctrl(src_data)
        dst_def_to_ctrl = _remap_registry_def_to_ctrl(dst_data)
        shared_defs = _remap_shared_defs(src_data, dst_data)
        if not shared_defs:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, src_obj, 'POSE')
        try:
            context.view_layer.update()
        except Exception:
            pass
        src_world_by_dst = {}
        try:
            dg = context.evaluated_depsgraph_get()
            dg.update()
            src_eval = src_obj.evaluated_get(dg)
            for def_name in shared_defs:
                sc = src_def_to_ctrl.get(def_name)
                dc = dst_def_to_ctrl.get(def_name)
                if sc is None or dc is None:
                    continue
                pb_src = src_eval.pose.bones.get(sc)
                if pb_src is not None:
                    src_world_by_dst[dc] = pb_src.matrix.copy()
        except Exception:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        if not src_world_by_dst:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, dst_obj, 'POSE')
        try:
            context.view_layer.update()
        except Exception:
            pass
        dst_ctrls = sorted(src_world_by_dst.keys(),
                           key=lambda n: _remap_pose_depth(dst_obj.pose.bones[n])
                           if dst_obj.pose.bones.get(n) is not None else 0)
        total = 0
        for name in dst_ctrls:
            pb = dst_obj.pose.bones.get(name)
            if pb is None:
                continue
            desired = src_world_by_dst.get(name)
            if desired is None:
                continue
            parent = pb.parent
            if parent is None:
                rest_local = pb.bone.matrix_local.copy()
                pm = None
            else:
                try:
                    rest_local = (parent.bone.matrix_local.inverted()
                                  @ pb.bone.matrix_local)
                except Exception:
                    rest_local = pb.bone.matrix_local.copy()
                pm = parent.matrix.copy()
            try:
                if pm is None:
                    basis = rest_local.inverted() @ desired
                else:
                    basis = rest_local.inverted() @ pm.inverted() @ desired
                pb.matrix_basis = basis
                total += 1
            except Exception:
                continue
            try:
                context.view_layer.update()
            except Exception:
                pass
        try:
            dg2 = context.evaluated_depsgraph_get()
            dg2.update()
        except Exception:
            pass
        if total == 0:
            self.report({'WARNING'}, tr("msg.remap_done") + ": " + str(total))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.remap_done") + ": " + str(total))
        return {'FINISHED'}


class CTRLDEF_OT_bake_ik_to_fk(Operator):
    bl_idname = "ctrl_def.bake_ik_to_fk"
    bl_label = tr("op.bake_ik_to_fk")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.bake_ik_to_fk")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, arm, 'POSE')
        try:
            _prune_registry(arm)
        except Exception:
            pass
        data = _read_registry(arm)
        if not data:
            self.report({'ERROR'}, tr("msg.no_registered"))
            return {'CANCELLED'}
        context.view_layer.update()
        chains = _collect_ik_chains(arm, data)
        if not chains:
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}

        # Seleziona i controller delle catene IK per il bake NLA.
        try:
            for pb in arm.pose.bones:
                _set_pose_bone_selected(pb, False)
        except Exception as exc:
            self.report({'WARNING'}, 'Impossibile deselezionare i pose bone prima del bake: %s' % exc)
            return {'CANCELLED'}
        try:
            for chain in chains:
                for name in chain:
                    pb = arm.pose.bones.get(name)
                    if pb is not None:
                        _set_pose_bone_selected(pb, True)
        except Exception as exc:
            self.report({'WARNING'}, 'Impossibile selezionare il pose bone per il bake: %s' % exc)
            return {'CANCELLED'}

        scene = context.scene
        frame_start = getattr(scene, "frame_start", 1)
        frame_end = getattr(scene, "frame_end", frame_start)
        if not isinstance(frame_start, int):
            try:
                frame_start = int(frame_start)
            except (TypeError, ValueError):
                frame_start = 1
        if not isinstance(frame_end, int):
            try:
                frame_end = int(frame_end)
            except (TypeError, ValueError):
                frame_end = frame_start
        if frame_end < frame_start:
            frame_end = frame_start

        window = getattr(context, "window", None)
        if window is None and getattr(bpy.context, "window", None) is not None:
            window = bpy.context.window
        area = None
        if window is not None:
            aree = getattr(window.screen, "areas", [])
            for tipo in ("NLA_EDITOR", "DOPESHEET_EDITOR", "TIMELINE", "VIEW_3D"):
                for cand in aree:
                    if getattr(cand, "type", None) == tipo:
                        area = cand
                        break
                if area is not None:
                    break
            if area is None and aree:
                area = aree[0]
        region = None
        if area is not None:
            for reg in getattr(area, "regions", []):
                if getattr(reg, "type", None) == 'WINDOW':
                    region = reg
                    break
            if region is None and area.regions:
                region = area.regions[0]

        bake_ok = False
        try:
            override = {}
            if window is not None:
                override["window"] = window
            if area is not None:
                override["area"] = area
            if region is not None:
                override["region"] = region
            override["object"] = arm
            override["active_object"] = arm
            with context.temp_override(**override):
                res = bpy.ops.nla.bake(
                    frame_start=frame_start,
                    frame_end=frame_end,
                    step=1,
                    only_selected=True,
                    visual_keying=True,
                    clear_constraints=False,
                    clear_parents=False,
                    use_current_action=False,
                    clean_curves=False,
                    bake_types={'POSE'},
                )
            if isinstance(res, set) and 'FINISHED' in res:
                bake_ok = True
        except Exception:
            bake_ok = False

        if not bake_ok:
            # Bake fallito: i constraint IK restano (non si perde la posa IK)
            # e si ripristina la selezione prima di annullare l'operazione.
            try:
                for pb in arm.pose.bones:
                    _set_pose_bone_selected(pb, False)
            except Exception:
                pass
            self.report({'WARNING'}, "Bake IK->FK non riuscito: constraint IK mantenuti")
            return {'CANCELLED'}

        # Rimozione del constraint IK preservando la posa baked sui controller FK
        try:
            for chain in chains:
                if not chain:
                    continue
                first_name = chain[0]
                pb = arm.pose.bones.get(first_name)
                if pb is None:
                    continue
                con = pb.constraints.get("CTRL_DEF_IK")
                if con is not None:
                    try:
                        pb.constraints.remove(con)
                    except Exception:
                        try:
                            # Fallback esplicito: rimozione per indice
                            for idx, c in enumerate(list(pb.constraints)):
                                if getattr(c, "name", "") == "CTRL_DEF_IK":
                                    pb.constraints.remove(c)
                        except Exception:
                            pass
        except Exception:
            pass

        # Deselezione ripristino
        try:
            for pb in arm.pose.bones:
                _set_pose_bone_selected(pb, False)
        except Exception:
            pass

        context.view_layer.update()
        try:
            dg = context.evaluated_depsgraph_get()
            dg.update()
        except Exception:
            pass

        self.report({'INFO'}, tr("msg.ik_created") + ": " + str(len(chains)))
        return {'FINISHED'}


# Registrazione autonoma: garantisce la disponibilita' dell'operatore anche
# quando i moduli di registrazione (main/__init__) non lo elencano esplicitamente.
try:
    import bpy as _bpy_reg
    if not getattr(CTRLDEF_OT_bake_ik_to_fk, "is_registered", False):
        _bpy_reg.utils.register_class(CTRLDEF_OT_bake_ik_to_fk)
except Exception:
    pass
# ===========================================================================
# Manifest strutturale + Diff (M3)
# ===========================================================================

def _manifest_collect_registry(arm):
    try:
        from .ctrl_def_registry import _read_registry
        return _read_registry(arm)
    except Exception:
        return {}


def _manifest_collect_hierarchy(arm):
    out = {}
    try:
        for b in arm.data.bones:
            out[b.name] = (b.parent.name if b.parent else None)
    except Exception:
        pass
    return out


def _manifest_collect_constraints(arm):
    out = {}
    try:
        for pb in arm.pose.bones:
            cons = []
            for c in pb.constraints:
                cons.append({
                    "type": getattr(c, "type", ""),
                    "name": getattr(c, "name", ""),
                    "subtarget": getattr(c, "subtarget", ""),
                    "target": getattr(getattr(c, "target", None), "name", None),
                    "influence": getattr(c, "influence", None),
                })
            out[pb.name] = sorted(cons, key=lambda x: (x.get("name", ""), x.get("type", "")))
    except Exception:
        pass
    try:
        for b in arm.data.bones:
            out.setdefault(b.name, [])
    except Exception:
        pass
    return out


def _manifest_collect_ik(arm):
    out = []
    try:
        for pb in arm.pose.bones:
            for c in pb.constraints:
                if getattr(c, "type", "") == "IK":
                    out.append({
                        "bone": pb.name,
                        "target": getattr(getattr(c, "target", None), "name", None),
                        "subtarget": getattr(c, "subtarget", ""),
                        "chain_count": getattr(c, "chain_count", None),
                        "pole_target": getattr(getattr(c, "pole_target", None), "name", None),
                        "pole_subtarget": getattr(c, "pole_subtarget", ""),
                    })
    except Exception:
        pass
    out.sort(key=lambda x: (x.get("bone", ""), x.get("subtarget", "")))
    return out


def _manifest_collect_deform(arm):
    out = {}
    try:
        for b in arm.data.bones:
            out[b.name] = bool(getattr(b, "use_deform", False))
    except Exception:
        pass
    return out


def _manifest_collect(arm):
    return {
        "registry": _manifest_collect_registry(arm),
        "hierarchy": _manifest_collect_hierarchy(arm),
        "constraints": _manifest_collect_constraints(arm),
        "ik": _manifest_collect_ik(arm),
        "deform": _manifest_collect_deform(arm),
    }


def _manifest_compare(old, new):
    diff = {"added": [], "removed": [], "changed": []}
    old_reg = (old or {}).get("registry", {}) or {}
    new_reg = (new or {}).get("registry", {}) or {}
    for k in new_reg:
        if k not in old_reg:
            diff["added"].append(k)
        elif old_reg.get(k) != new_reg.get(k):
            diff["changed"].append(k)
    for k in old_reg:
        if k not in new_reg:
            diff["removed"].append(k)
    for cat in ("hierarchy", "constraints", "ik", "deform"):
        if (old or {}).get(cat) != (new or {}).get(cat):
            diff["changed"].append(cat)
    for key in ("added", "removed", "changed"):
        diff[key] = sorted(set(diff[key]))
    if not diff["added"] and not diff["removed"] and not diff["changed"]:
        return {}
    return {k: v for k, v in diff.items() if v}


_MANIFEST_DIFF_KEYS = ("_ctrl_def_last_manifest_diff", "_ctrl_def_manifest_diff",
                       "ctrl_def_manifest_diff", "_ctrl_def_last_diff")


def _manifest_store(arm, diff):
    """Memorizza il diff del manifest sull'armatura.

    Restituisce True solo se almeno una chiave e' stata scritta con successo:
    in caso di fallimento della serializzazione JSON o della scrittura delle
    proprieta' custom non maschera l'errore con un True fittizio.
    """
    if arm is None:
        return False
    try:
        payload = diff if isinstance(diff, str) else json.dumps(
            diff, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return False
    stored = False
    for key in _MANIFEST_DIFF_KEYS:
        try:
            arm[key] = payload
            stored = True
        except Exception:
            # Tentativo sulla chiave successiva; l'esito finale riflette il reale.
            continue
    return stored


class CTRLDEF_OT_manifest(Operator):
    bl_idname = "ctrl_def.manifest"
    bl_label = tr("op.manifest")
    bl_options = {'REGISTER'}

    filepath: StringProperty(default="", subtype='FILE_PATH')

    def execute(self, context):
        arm = context.active_object
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            for o in getattr(context, "selected_objects", []) or []:
                if getattr(o, "type", None) == "ARMATURE":
                    arm = o
                    break
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            self.report({'ERROR'}, "No armature")
            return {'CANCELLED'}
        snap = _manifest_collect(arm)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2, sort_keys=True, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class CTRLDEF_OT_manifest_diff(Operator):
    bl_idname = "ctrl_def.manifest_diff"
    bl_label = tr("op.manifest_diff")
    bl_options = {'REGISTER'}

    filepath: StringProperty(default="", subtype='FILE_PATH')
    baseline: StringProperty(default="", subtype='FILE_PATH')

    def execute(self, context):
        arm = context.active_object
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            for o in getattr(context, "selected_objects", []) or []:
                if getattr(o, "type", None) == "ARMATURE":
                    arm = o
                    break
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            self.report({'ERROR'}, "No armature")
            return {'CANCELLED'}
        snap = _manifest_collect(arm)
        # Legge la baseline prima di toccare il percorso di output: quando
        # filepath e baseline puntano allo stesso file, scrivere prima
        # sovrascriverebbe il riferimento e il diff risulterebbe sempre vuoto.
        try:
            with open(self.baseline, "r", encoding="utf-8") as f:
                base = json.load(f)
        except (OSError, ValueError) as exc:
            # WARNING e non ERROR: con ERROR Blender trasforma il CANCELLED
            # restituito in un RuntimeError per il chiamante.
            self.report({'WARNING'}, "Baseline unreadable, nothing written: {}".format(exc))
            return {'CANCELLED'}
        diff = _manifest_compare(base, snap)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2, sort_keys=True, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if not _manifest_store(arm, diff):
            self.report({'WARNING'}, "manifest store failed")
            return {'CANCELLED'}
        return {'FINISHED'}


class CTRLDEF_OT_auto_collection(Operator):
    bl_idname = "ctrl_def.auto_collection"
    bl_label = tr("op.auto_collection")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.auto_collection")

    def execute(self, context):
        arm = context.active_object
        if arm is None:
            for o in getattr(context, "selected_objects", []) or []:
                if getattr(o, "type", None) == "ARMATURE":
                    arm = o
                    break
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        if arm.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as exc:
                self.report({'WARNING'}, 'Failed to switch to OBJECT mode: %s' % exc)
                return {'CANCELLED'}
        stg = getattr(context.scene, "ctrl_def_settings", None)
        prefix_def = getattr(stg, "prefix_def", "DEF_") or "DEF_"
        data = _read_registry(arm)
        colls = {nome: _coll_ensure(arm.data, nome)
                 for nome in _MANAGED_COLLECTIONS}
        registrati = set(data.keys()) if data else set()
        for bone in arm.data.bones:
            target = _coll_target(bone.name, prefix_def, registrati, data)
            if target is None:
                continue
            _coll_assign_target(colls[target], bone)
        # Le collection gestite rimaste vuote farebbero fallire rig_score 5.1:
        # si eliminano MCH/ORG/IK solo se non hanno ricevuto nessun bone.
        # CTRLS e DEF restano perche' sono le destinazioni principali.
        for nome in ("MCH", "ORG", "IK"):
            coll = arm.data.collections.get(nome)
            if coll is not None and len(list(coll.bones)) == 0:
                arm.data.collections.remove(coll)
        self.report({'INFO'}, tr("msg.auto_collection"))
        return {'FINISHED'}


# ===========================================================================
# Character Picker automatico (M7)
# ===========================================================================
# Keyword per radice: il primo gruppo che combacia vince, quindi i distretti
# specifici (faccia, arti) precedono la colonna. Il lato .L/.R non conta:
# la controparte specchiata finisce nello stesso gruppo per costruzione.
_CP_KEYWORDS = (
    ("Faccia", ("jaw", "eye", "brow", "lip", "tongue", "teeth", "ear",
                "nose", "cheek", "head", "testa", "bocca", "occhio",
                "mascella", "lingua", "orecchio", "naso", "guancia",
                "sopracciglio", "palpebra")),
    ("Braccia", ("arm", "forearm", "hand", "upperarm", "lowerarm", "shoulder",
                 "clavicle", "wrist", "elbow", "finger", "thumb", "palm",
                 "braccio", "mano", "ala", "wing", "spalla", "dito")),
    ("Gambe", ("thigh", "shin", "calf", "foot", "toe", "leg", "knee",
               "ankle", "hip", "gamba", "coscia", "polpaccio", "piede",
               "anca", "ginocchio", "caviglia")),
    ("Spine", ("spine", "chest", "neck", "pelvis", "torso", "hips",
               "collo", "bacino", "schiena", "coda", "tail")),
)


def _cp_ensure_collection(arm_data, nome):
    """Restituisce la Bone Collection col nome richiesto, creandola se assente."""
    return _coll_ensure(arm_data, nome)


def _cp_root(nome):
    """Radice del bone, senza lato .L/.R ne' suffisso _pole."""
    base = str(nome).lower()
    if base.endswith("_pole"):
        base = base[:-len("_pole")]
    if base.endswith((".l", ".r")):
        base = base[:-2]
    return base


def _cp_tokens(nome):
    """Token della radice del bone, senza lato .L/.R ne' suffisso _pole."""
    return [tok for tok in _cp_root(nome).replace("-", "_").replace(".", "_").split("_") if tok]


def _cp_classify(nome):
    """Classifica un controller nel gruppo del picker tramite radice e keyword.

    Restituisce il nome del gruppo oppure None se nessuna keyword combacia;
    il chiamante applica il fallback gerarchico. Target e pole IK vengono
    riconosciuti dal suffisso _pole, dal suffisso _ik/.ik e dal prefisso IK_
    prima delle keyword anatomiche.
    """
    low = str(nome).lower()
    if low.endswith("_pole"):
        return "Pole"
    radice = _cp_root(nome)
    if radice.endswith(("_ik", ".ik")) or radice.startswith("ik_"):
        return "IK"
    tokens = _cp_tokens(nome)
    if "root" in tokens or "radice" in tokens:
        return "Root"
    for gruppo, chiavi in _CP_KEYWORDS:
        for tok in tokens:
            if tok in chiavi:
                return gruppo
    return None


def _cp_assign(bone, collection):
    """Assegna il bone alla collection se non ne fa gia' parte. Idempotente."""
    if collection.name in (c.name for c in bone.collections):
        return 0
    collection.assign(bone)
    return 1


def character_picker(arm_obj):
    """Pubblica il mapping gruppo -> controller nelle Bone Collection.

    Crea (o riusa, senza duplicare) le collection Root, Spine, Braccia,
    Gambe, Faccia, IK e Pole e vi assegna i bone non-DEF secondo radice e
    keyword del nome, con i lati .L/.R nello stesso gruppo. Rientra
    {'FINISHED'} oppure {'CANCELLED'} se l'armatura non e' valida. E'
    idempotente: un secondo richiamo non crea collection ne' assegnazioni
    doppie e rimuove solo i bone finiti in un gruppo sbagliato.
    """
    if arm_obj is None or getattr(arm_obj, "type", None) != "ARMATURE":
        return {'CANCELLED'}
    arm_data = getattr(arm_obj, "data", None)
    if arm_data is None:
        return {'CANCELLED'}
    stg = getattr(bpy.context.scene, "ctrl_def_settings", None)
    prefix_def = getattr(stg, "prefix_def", "DEF_") or "DEF_"
    collections = {nome: _cp_ensure_collection(arm_data, nome)
                   for nome in _CP_GRUPPI}

    # Prima passata: classificazione per nome. I bone DEF e i livelli
    # meccanici (MCH/ORG) restano fuori dal picker: sono invisibili ai
    # controlli dell'animatore.
    assegnazioni = {}
    for bone in arm_data.bones:
        if _is_def_bone(bone, prefix_def):
            continue
        if bone.name.startswith(("MCH_", "ORG_")):
            continue
        gruppo = _cp_classify(bone.name)
        if gruppo is None:
            # Fallback deterministico: eredita il gruppo del primo genitore
            # classificato, altrimenti Root per le radici e Spine per il resto.
            gruppo = "Spine"
            genitore = bone.parent
            while genitore is not None:
                trovato = assegnazioni.get(genitore.name)
                if trovato is not None:
                    gruppo = trovato
                    break
                genitore = genitore.parent
            else:
                if bone.parent is None:
                    gruppo = "Root"
        assegnazioni[bone.name] = gruppo

    # Seconda passata: applica il mapping e toglie il bone dai gruppi del
    # picker sbagliati, lasciando intatte le collection esterne (CTRLS, DEF).
    for nome, gruppo in assegnazioni.items():
        bone = arm_data.bones.get(nome)
        if bone is None:
            continue
        for altro, collection in collections.items():
            if altro == gruppo:
                _cp_assign(bone, collection)
            elif collection.name in (c.name for c in bone.collections):
                collection.unassign(bone)
    return {'FINISHED'}


class CTRLDEF_OT_character_picker(Operator):
    bl_idname = "ctrl_def.character_picker"
    bl_label = tr("op.character_picker")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.character_picker")

    def execute(self, context):
        arm = context.active_object
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            for o in getattr(context, "selected_objects", []) or []:
                if getattr(o, "type", None) == "ARMATURE":
                    arm = o
                    break
        if arm is None or getattr(arm, "type", None) != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        if character_picker(arm) == {'CANCELLED'}:
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.character_picker"))
        return {'FINISHED'}


# ===========================================================================
# Handoff Animatore (M5)
# ===========================================================================
_HANDOFF_SNAPSHOT_KEY = "_ctrl_def_handoff_snapshot"
_HANDOFF_COLL_NOMI = ("CTRLS", "IK", "DEF", "MCH", "ORG")


def _handoff_snapshot_stato(arm):
    if arm is None:
        return None
    esistente = None
    try:
        esistente = arm.get(_HANDOFF_SNAPSHOT_KEY)
    except Exception:
        esistente = None
    if esistente is not None:
        try:
            return json.loads(esistente if isinstance(esistente, str) else str(esistente))
        except Exception:
            esistente = None
    vis = {}
    for cn in _HANDOFF_COLL_NOMI:
        coll = arm.data.collections.get(cn)
        if coll is not None:
            vis[cn] = bool(getattr(coll, "is_visible", True))
    lock = {}
    for cn in ("MCH", "ORG"):
        coll = arm.data.collections.get(cn)
        if coll is None:
            continue
        for b in coll.bones:
            pb = arm.pose.bones.get(b.name)
            if pb is None:
                continue
            lock[b.name] = {
                "lock_location": list(getattr(pb, "lock_location", (False, False, False))),
                "lock_rotation": list(getattr(pb, "lock_rotation", (False, False, False))),
                "lock_rotation_w": bool(getattr(pb, "lock_rotation_w", False)),
                "lock_scale": list(getattr(pb, "lock_scale", (False, False, False))),
            }
    snapshot = {"visibility": vis, "locks": lock}
    arm[_HANDOFF_SNAPSHOT_KEY] = json.dumps(snapshot, ensure_ascii=False)
    return snapshot


def _handoff_applica(arm):
    if arm is None:
        return
    coll_ctrls = arm.data.collections.get("CTRLS")
    if coll_ctrls is not None:
        coll_ctrls.is_visible = True
    coll_ik = arm.data.collections.get("IK")
    if coll_ik is not None:
        coll_ik.is_visible = True
    for cn in ("DEF", "MCH", "ORG"):
        coll = arm.data.collections.get(cn)
        if coll is not None:
            coll.is_visible = False
    for cn in ("MCH", "ORG"):
        coll = arm.data.collections.get(cn)
        if coll is None:
            continue
        for b in coll.bones:
            pb = arm.pose.bones.get(b.name)
            if pb is None:
                continue
            pb.lock_location = (True, True, True)
            pb.lock_rotation = (True, True, True)
            pb.lock_rotation_w = True
            pb.lock_scale = (True, True, True)


def _handoff_ripristina(arm):
    if arm is None:
        return {'CANCELLED'}
    raw = None
    try:
        raw = arm.get(_HANDOFF_SNAPSHOT_KEY)
    except Exception:
        raw = None
    snapshot = None
    corrupt = False
    if raw is not None:
        try:
            snapshot = json.loads(raw if isinstance(raw, str) else str(raw))
        except Exception:
            snapshot = None
            corrupt = True
    if raw is None or corrupt or not isinstance(snapshot, dict):
        return {'CANCELLED'}
    vis = snapshot.get("visibility") or {}
    for cn, val in vis.items():
        coll = arm.data.collections.get(cn)
        if coll is None:
            continue
        coll.is_visible = bool(val)
    lock = snapshot.get("locks") or {}
    for nome, stato in lock.items():
        pb = arm.pose.bones.get(nome)
        if pb is None:
            continue
        pb.lock_location = tuple(stato.get("lock_location", (False, False, False)))
        pb.lock_rotation = tuple(stato.get("lock_rotation", (False, False, False)))
        pb.lock_rotation_w = bool(stato.get("lock_rotation_w", False))
        pb.lock_scale = tuple(stato.get("lock_scale", (False, False, False)))
    try:
        del arm[_HANDOFF_SNAPSHOT_KEY]
    except Exception:
        arm[_HANDOFF_SNAPSHOT_KEY] = None
    return {'FINISHED'}


class CTRLDEF_OT_handoff_animator(Operator):
    bl_idname = "ctrl_def.handoff_animator"
    bl_label = tr("op.handoff_animator")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.handoff_animator")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, arm, 'OBJECT')
        _handoff_snapshot_stato(arm)
        _handoff_applica(arm)
        self.report({'INFO'}, tr("msg.handoff_done"))
        return {'FINISHED'}


class CTRLDEF_OT_restore_rigger(Operator):
    bl_idname = "ctrl_def.restore_rigger"
    bl_label = tr("op.restore_rigger")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.restore_rigger")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        _ensure_armature_mode(context, arm, 'OBJECT')
        res = _handoff_ripristina(arm)
        if res == {'CANCELLED'}:
            self.report({'WARNING'}, "handoff snapshot missing or corrupt")
            return {'CANCELLED'}
        self.report({'INFO'}, tr("msg.restore_done"))
        return {'FINISHED'}


# ===========================================================================
# Naming Doctor: rinomina sicura dei bone con aggiornamento registro/vincoli
# ===========================================================================

def _nd_validate_map(arm_obj, rename_map):
    if not isinstance(rename_map, dict) or not rename_map:
        return False
    arm_data = arm_obj.data
    existing = set(b.name for b in arm_data.bones)
    try:
        reg = _read_registry(arm_obj)
    except Exception:
        return False
    reg_keys = set(reg.keys()) if isinstance(reg, dict) else set()
    olds = set(rename_map.keys())
    news = list(rename_map.values())
    for old, new in rename_map.items():
        if not isinstance(old, str) or not isinstance(new, str):
            return False
        if not old or not new:
            return False
        if old not in existing:
            return False
    if len(set(news)) != len(news):
        return False
    for new in news:
        if new in existing and new not in olds:
            return False
        if new in reg_keys and new not in olds:
            return False
    return True


def _nd_rename_bones(arm_obj, rename_map):
    arm_data = arm_obj.data
    temp_to_new = {}
    idx = 0
    for old, new in rename_map.items():
        if old == new:
            continue
        if old not in arm_data.bones:
            continue
        temp = "__nd_tmp_%d__" % idx
        while temp in arm_data.bones:
            temp += "_"
        arm_data.bones[old].name = temp
        temp_to_new[temp] = new
        idx += 1
    for temp, new in temp_to_new.items():
        if temp in arm_data.bones:
            arm_data.bones[temp].name = new


def _nd_update_registry(arm_obj, rename_map):
    reg = _read_registry(arm_obj)
    if not isinstance(reg, dict):
        return
    new_reg = {}
    for ctrl, entry in reg.items():
        new_ctrl = rename_map.get(ctrl, ctrl)
        if isinstance(entry, dict):
            new_entry = dict(entry)
            def_name = new_entry.get("def")
            if def_name in rename_map:
                new_entry["def"] = rename_map[def_name]
        else:
            new_entry = entry
        new_reg[new_ctrl] = new_entry
    _write_registry(arm_obj, new_reg)


def _nd_update_constraints(arm_obj, rename_map):
    for pb in arm_obj.pose.bones:
        for con in pb.constraints:
            if hasattr(con, "subtarget") and con.subtarget in rename_map:
                con.subtarget = rename_map[con.subtarget]
            if hasattr(con, "pole_subtarget") and con.pole_subtarget in rename_map:
                con.pole_subtarget = rename_map[con.pole_subtarget]


def _nd_update_parents(arm_obj, rename_map, captured_parents=None):
    """Verifica i parent dopo la rinomina e ripristina quelli persi.

    I parent dei bone sono puntatori Blender: rinominare un bone non spezza
    il puntatore (il figlio continua a puntare allo stesso bone, il cui .name
    segue la rinomina), quindi nel percorso normale non c'e' nulla da fare.
    Questa funzione resta come rete di sicurezza: ripara parent stale (nome
    vecchio) e parent persi (puntatore diventato None) usando la mappa
    old->new e, se disponibile, la mappa dei parent catturata prima della
    rinomina.
    """
    bones = getattr(getattr(arm_obj, "data", None), "bones", None)
    if bones is None:
        return None

    # Calcola se serve un intervento riparatore.
    needs_repair = False
    if isinstance(captured_parents, dict):
        for old_child, old_parent in captured_parents.items():
            new_child_name = rename_map.get(old_child, old_child)
            child_bone = bones.get(new_child_name)
            if child_bone is not None and child_bone.parent is None:
                needs_repair = True
                break
    if not needs_repair:
        for bone in bones:
            parent = bone.parent
            if parent is not None and parent.name in rename_map:
                needs_repair = True
                break

    if not needs_repair:
        return None

    # Riparazione in edit mode: Bone.parent e' read-only in object/pose mode.
    try:
        _ensure_armature_mode(bpy.context, arm_obj, 'EDIT')
    except Exception:
        return None
    try:
        ebones = arm_obj.data.edit_bones
        # Ripristina parent persi a partire dalla mappa catturata.
        if isinstance(captured_parents, dict):
            for old_child, old_parent in captured_parents.items():
                new_child_name = rename_map.get(old_child, old_child)
                if new_child_name not in ebones:
                    continue
                echild = ebones[new_child_name]
                if echild.parent is not None:
                    continue
                if old_parent is None:
                    echild.parent = None
                    continue
                new_parent_name = rename_map.get(old_parent, old_parent)
                if new_parent_name in ebones:
                    echild.parent = ebones[new_parent_name]
        # Ripara parent stale (nome vecchio) residui.
        for ename in list(ebones.keys()):
            ebone = ebones[ename]
            if ebone.parent is not None and ebone.parent.name in rename_map:
                new_parent_name = rename_map[ebone.parent.name]
                if new_parent_name in ebones:
                    ebone.parent = ebones[new_parent_name]
    except Exception:
        pass
    try:
        _ensure_armature_mode(bpy.context, arm_obj, 'POSE')
    except Exception:
        pass
    return None


def _nd_preserve_shapes(arm_obj, rename_map, captured=None):
    if captured is None:
        captured = {}
        for old in rename_map:
            pb = arm_obj.pose.bones.get(old)
            if pb is not None and getattr(pb, "custom_shape", None) is not None:
                captured[old] = pb.custom_shape
        return captured
    for old, new in rename_map.items():
        shape = captured.get(old)
        if shape is None:
            continue
        pb = arm_obj.pose.bones.get(new)
        if pb is not None:
            try:
                pb.custom_shape = shape
            except Exception as exc:
                # Non nascondere la perdita dello shape: propaga l'errore
                # al chiamante, che annulla l'operazione con report.
                raise RuntimeError("custom_shape non preservabile: %r" % exc)
    return captured


def naming_doctor(arm_obj, rename_map):
    if arm_obj is None or getattr(arm_obj, "type", None) != "ARMATURE":
        return {'CANCELLED'}
    if not _nd_validate_map(arm_obj, rename_map):
        return {'CANCELLED'}
    try:
        _ensure_armature_mode(bpy.context, arm_obj, 'POSE')
    except Exception:
        return {'CANCELLED'}
    shapes = _nd_preserve_shapes(arm_obj, rename_map)
    # Cattura i parent prima della rinomina per poterli ripristinare.
    parents_before = {}
    try:
        for b in arm_obj.data.bones:
            parents_before[b.name] = (b.parent.name if b.parent is not None else None)
    except Exception:
        parents_before = {}
    try:
        _ensure_armature_mode(bpy.context, arm_obj, 'OBJECT')
        _nd_rename_bones(arm_obj, rename_map)
    except Exception:
        return {'CANCELLED'}
    try:
        _nd_update_registry(arm_obj, rename_map)
    except Exception:
        return {'CANCELLED'}
    try:
        _ensure_armature_mode(bpy.context, arm_obj, 'POSE')
        _nd_update_constraints(arm_obj, rename_map)
    except Exception:
        return {'CANCELLED'}
    # I constraint puntano ai bone per nome: l'update del depsgraph deve
    # avvenire solo DOPO aver riallineato i subtarget, altrimenti la
    # valutazione usa i nomi vecchi e fallisce sulla relazione.
    bpy.context.view_layer.update()
    try:
        _nd_update_parents(arm_obj, rename_map, parents_before)
    except Exception:
        return {'CANCELLED'}
    try:
        _nd_preserve_shapes(arm_obj, rename_map, shapes)
    except Exception:
        return {'CANCELLED'}
    return {'FINISHED'}


class CTRLDEF_OT_naming_doctor(Operator):
    bl_idname = "ctrl_def.naming_doctor"
    bl_label = tr("op.naming_doctor")
    bl_options = {'REGISTER', 'UNDO'}

    rename_map_json: StringProperty(
        name=tr("prop.rename_map_json"), default="{}",
        description=tr("tip.prop.rename_map_json"))

    @classmethod
    def description(cls, context, properties):
        return tr("tip.op.naming_doctor")

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        try:
            rename_map = json.loads(self.rename_map_json or "{}")
        except (ValueError, TypeError):
            self.report({'ERROR'}, tr("msg.invalid_rename_map"))
            return {'CANCELLED'}
        if not isinstance(rename_map, dict):
            self.report({'ERROR'}, tr("msg.invalid_rename_map"))
            return {'CANCELLED'}
        res = naming_doctor(arm, rename_map)
        if res == {'FINISHED'}:
            self.report({'INFO'}, tr("op.naming_doctor"))
            return {'FINISHED'}
        self.report({'ERROR'}, tr("op.naming_doctor"))
        return {'CANCELLED'}
