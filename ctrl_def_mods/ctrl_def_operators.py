# Modulo operatori: preset, rimozione, binding ACTD, diagnostica pre-flight,
# export della mappa CTRL->DEF e preset utente JSON.
import csv
import json
import sys

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Vector

from .ctrl_def_i18n import tr
from .ctrl_def_registry import _forget_generated, _read_registry
from .ctrl_def_shapes import _is_def_bone, _mirror_name

_PRESETS = {
    "DEFAULT": {"shape": "CIRCLE", "scale": 1.0, "color": "NONE",
                "parent": "CHAIN", "mirror": False,
                "shape_rot": (0.0, 0.0, 0.0)},
    "BIPED_LIMB": {"shape": "CUBE", "scale": 0.8, "color": "RED",
                   "parent": "CHAIN", "mirror": True,
                   "shape_rot": (0.0, 0.0, 0.0)},
    "ROOT_CTRL": {"shape": "ARROW", "scale": 2.0, "color": "BLUE",
                  "parent": "ROOT", "mirror": False,
                  "shape_rot": (90.0, 0.0, 0.0)},
    "FACE": {"shape": "SPHERE", "scale": 0.3, "color": "GREEN",
             "parent": "BONE", "mirror": True,
             "shape_rot": (90.0, 0.0, 0.0)},
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

    def execute(self, context):
        stg = context.scene.ctrl_def_settings
        _apply_preset_values(stg, stg.preset)
        return {'FINISHED'}


def _remove_registered_bones(arm, data):
    """Rimuove in Edit Mode i bone registrati e li dimentica dal registry.

    Restituisce quanti edit_bones sono stati effettivamente rimossi.
    """
    removed = 0
    if arm.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones
    for name in list(data.keys()):
        ebone = ebones.get(name)
        if ebone is not None:
            ebones.remove(ebone)
            removed += 1
        _forget_generated(arm, name)
    bpy.ops.object.mode_set(mode='OBJECT')
    return removed


def _purge_unused_shapes(arm):
    """Elimina le shape della collezione CTRL_Shapes rimaste inutilizzate.

    Vale per le shape condivise CTRL_DEF_SHAPE_* e per le vecchie shape
    per-controller <nome>_shape: se un pose bone dell'armatura le usa
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
        condivisa = obj.name.startswith("CTRL_DEF_SHAPE_")
        legacy = obj.name.endswith("_shape") and obj.name in nomi_col
        if condivisa or legacy:
            bpy.data.objects.remove(obj, do_unlink=True)


class CTRLDEF_OT_remove(Operator):
    bl_idname = "ctrl_def.remove"
    bl_label = tr("op.remove")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        data = _read_registry(arm)
        if not data:
            # Nessun controller registrato: si ripuliscono solo le shape orfane
            self._purge_shapes(arm)
            self.report({'INFO'}, tr("msg.removed") + ": 0")
            return {'FINISHED'}
        removed = _remove_registered_bones(arm, data)
        # Le shape sono condivise: si eliminano solo se nessun pose bone le usa
        self._purge_shapes(arm)
        self.report({'INFO'}, tr("msg.removed") + ": " + str(removed))
        return {'FINISHED'}

    @staticmethod
    def _purge_shapes(arm):
        """Compatibilita': delega alla funzione di modulo _purge_unused_shapes."""
        return _purge_unused_shapes(arm)


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
            actd.collection_source = "CTRL"
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

    def _apply_actd(self, context, stg):
        """Integrazione diretta con ACTD: token sorgente CTRL, destinazione DEF."""
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


# Proprieta' di CTRLDEF_PG_settings serializzate nel preset utente
_SETTINGS_KEYS = ("prefix_def", "prefix_ctrl", "shape", "scale", "shape_rot",
                  "color", "parent", "mirror")


def _settings_values(stg):
    """Dizionario dei valori correnti delle impostazioni (JSON-serializzabile)."""
    valori = {}
    for chiave in _SETTINGS_KEYS:
        valore = getattr(stg, chiave)
        if chiave == "shape_rot":
            valore = list(valore)
        valori[chiave] = valore
    return valori


def _apply_settings_values(stg, valori):
    """Applica al PropertyGroup i valori del preset, ignorando chiavi ignote."""
    for chiave in _SETTINGS_KEYS:
        if chiave not in valori:
            continue
        valore = valori[chiave]
        if chiave == "shape_rot":
            valore = tuple(valore)
        setattr(stg, chiave, valore)
    return stg


def _prepare_export(op, context):
    """Controlli comuni: armatura attiva e registro non vuoto.

    Restituisce (arm, data) oppure (None, None) dopo aver riportato l'errore.
    """
    arm = context.active_object
    if arm is None or arm.type != "ARMATURE":
        op.report({'ERROR'}, tr("msg.no_armature"))
        return None, None
    data = _read_registry(arm)
    if not data:
        op.report({'WARNING'}, tr("msg.no_registered"))
        return None, None
    return arm, data


class CTRLDEF_OT_export_json(Operator, ExportHelper):
    bl_idname = "ctrl_def.export_json"
    bl_label = tr("op.export_json")
    bl_options = {'REGISTER'}

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

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = "//ctrl_def_preset.json"
        return super().invoke(context, event)

    def execute(self, context):
        arm, _data = _prepare_export(self, context)
        if arm is None:
            return {'CANCELLED'}
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

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = "//ctrl_def_preset.json"
        return super().invoke(context, event)

    def execute(self, context):
        arm, _data = _prepare_export(self, context)
        if arm is None:
            return {'CANCELLED'}
        try:
            with open(self.filepath, "r", encoding="utf-8") as file_in:
                valori = json.load(file_in)
        except (OSError, ValueError) as exc:
            self.report({'ERROR'}, tr("msg.export_failed") + ": " + str(exc))
            return {'CANCELLED'}
        if not isinstance(valori, dict):
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
    return pbone.bone.select


def _selected_ctrl_chains(arm):
    """Catene di 2-3 controller registrati selezionati in Pose Mode.

    Un anello vale solo se e' registrato, se ha un genitore registrato e se
    entrambi sono selezionati: la catena si legge risalendo dal bone
    selezionato, cosi' la selezione completa di una catena produce una sola
    voce. Restituisce una lista di catene ordinate genitore -> figlio.
    """
    registro = _read_registry(arm)
    if not registro:
        return []

    def selezionato(nome):
        """Selezione letta sul pose bone del nome indicato."""
        pb = arm.pose.bones.get(nome)
        return pb is not None and _pose_bone_selected(pb)

    selezione = [pb for pb in arm.pose.bones
                 if pb.name in registro and _pose_bone_selected(pb)]
    catene = []
    for pb in selezione:
        catena = [pb.name]
        genitore = pb.bone.parent
        while (genitore is not None and genitore.name in registro
               and selezionato(genitore.name)):
            catena.insert(0, genitore.name)
            genitore = genitore.parent
        if 2 <= len(catena) <= 3 and catena not in catene:
            catene.append(catena)
    # Solo catene massimali: un prefisso piu' corto della stessa catena
    # riscriverebbe il constraint IK gia' creato sul primo controller.
    return [c for c in catene
            if not any(len(o) > len(c) and o[:len(c)] == c for o in catene)]


def _add_ik_target_chain(arm, bcoll_name, chain, pole=False):
    """Crea il target IK della catena e il vincolo IK sul primo controller.

    Il target e' un bone non-deform libero, col roll dell'ultimo controller,
    assegnato alla bone collection indicata; il constraint vive sul primo
    controller e chiude il loop su chain_count anelli. Restituisce il numero
    di target creati.
    """
    if arm is None or arm.type != 'ARMATURE' or not chain:
        return 0
    if arm.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones
    ultimo = ebones.get(chain[-1])
    if ultimo is None:
        bpy.ops.object.mode_set(mode='OBJECT')
        return 0
    bcoll = arm.data.collections.get(bcoll_name)
    if bcoll is None:
        bcoll = arm.data.collections.new(bcoll_name)
    nomi = ["IK_" + chain[-1]]
    if pole:
        nomi.append("IK_" + chain[-1] + "_pole")
    creati = 0
    for nome in nomi:
        ebone = ebones.get(nome)
        if ebone is None:
            ebone = ebones.new(nome)
        ebone.head = ultimo.head.copy()
        # Stessa guardia zero-length dei controller generati
        if (ultimo.tail - ultimo.head).length > 1e-6:
            ebone.tail = ultimo.tail.copy()
        else:
            ebone.tail = ultimo.head + Vector((0.0, 0.1, 0.0))
        ebone.roll = ultimo.roll
        ebone.use_deform = False
        ebone.parent = None
        bcoll.assign(ebone)
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

    def execute(self, context):
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        # La selezione dei bone si legge solo in Pose Mode
        _ensure_armature_mode(context, arm, 'POSE')
        # La selezione scritta dai test/pannelli va consolidata prima della lettura
        context.view_layer.update()
        catene = _selected_ctrl_chains(arm)
        if not catene:
            _ensure_armature_mode(context, arm, 'OBJECT')
            self.report({'ERROR'}, tr("msg.no_ik_chain"))
            return {'CANCELLED'}
        creati = 0
        for catena in catene:
            creati += _add_ik_target_chain(arm, "CTRL", catena)
        _ensure_armature_mode(context, arm, 'OBJECT')
        self.report({'INFO'}, tr("msg.ik_created") + ": " + str(creati))
        return {'FINISHED'}


