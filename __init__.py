# NON MODIFICARE DIRETTAMENTE.
# Generato automaticamente da scripts\build_monolith.py: edita i moduli in ctrl_def_mods\ e ricostruisci.

bl_info = {
    "name": "DEF Controller Auto",
    "author": "Pierfrancesco Diodato",
    "version": (0, 1, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > DEF Ctrl",
    "description": "Genera controller per bone DEF, tracciati e rimovibili",
    "category": "Rigging",
}

# ---------------------------------------------------------------------------
# CTRL_DEF — Controller automatici da bone DEF
# Single file autosufficiente, nessun dipendenza da ACTD.
# Commenti in italiano.
# ---------------------------------------------------------------------------
import bpy
import json
import math
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

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


# ===========================================================================
# Registro JSON sull'oggetto armatura (tracciamento controller generati)
# ===========================================================================
REGISTRY_KEY = "_ctrl_def_generated"


def _armature_of(obj):
    if obj is None:
        return None
    if obj.type == "ARMATURE":
        return obj
    if obj.type == "MESH" and obj.find_armature():
        return obj.find_armature()
    return None


def _read_registry(obj):
    arm = _armature_of(obj)
    if arm is None:
        return {}
    try:
        return json.loads(arm.get(REGISTRY_KEY, "{}"))
    except Exception:
        return {}


def _write_registry(obj, data):
    arm = _armature_of(obj)
    if arm is None:
        return False
    arm[REGISTRY_KEY] = json.dumps(data)
    return True


def _mark_generated(obj, ctrl_name, def_bone):
    data = _read_registry(obj)
    data[ctrl_name] = {"def": def_bone}
    _write_registry(obj, data)


def _is_generated(obj, ctrl_name):
    return ctrl_name in _read_registry(obj)


def _forget_generated(obj, ctrl_name):
    data = _read_registry(obj)
    data.pop(ctrl_name, None)
    _write_registry(obj, data)


def _prune_registry(obj):
    data = _read_registry(obj)
    arm = _armature_of(obj)
    if arm is None:
        return
    valid = {k: v for k, v in data.items() if k in arm.data.bones or k in bpy.data.objects}
    _write_registry(obj, valid)


# ===========================================================================
# Utilità naming, L/R, shape
# ===========================================================================
def _is_def_bone(bone, prefix="DEF_"):
    return bone.name.startswith(prefix)


def _side_of(name):
    up = name.upper()
    if up.endswith(".L") or up.endswith("_L"):
        return "L"
    if up.endswith(".R") or up.endswith("_R"):
        return "R"
    return "C"


def _mirror_name(name):
    side = _side_of(name)
    if side == "C":
        return name
    # Il separatore originale va preservato: DEF_hand_L -> DEF_hand_R,
    # DEF_hand.L -> DEF_hand.R (Rigify/standard Blender)
    opposto = {"L": "R", "R": "L"}[side]
    up = name.upper()
    for sep in (".", "_"):
        for s in ("L", "R"):
            suf = sep + s
            if up.endswith(suf):
                return name[: -len(suf)] + sep + opposto
    return name


def _ensure_collection(name="CTRL_Shapes"):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = True
    col.hide_render = True
    return col


def _make_circle(radius=1.0, segments=16):
    verts = []
    edges = []
    for i in range(segments):
        ang = 2 * math.pi * i / segments
        verts.append((radius * math.cos(ang), radius * math.sin(ang), 0.0))
    for i in range(segments):
        edges.append((i, (i + 1) % segments))
    return verts, edges


def _make_cube(radius=1.0):
    """Cubo wireframe centrato nell'origine (vertici e spigoli)."""
    r = radius
    verts = [(-r, -r, -r), (r, -r, -r), (r, r, -r), (-r, r, -r),
             (-r, -r, r), (r, -r, r), (r, r, r), (-r, r, r)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0),
             (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7)]
    return verts, edges


def _make_sphere(radius=1.0, segments=12):
    """Sfera wireframe approssimata: cerchio equatoriale piu' polo superiore."""
    verts, edges = _make_circle(radius, segments)
    verts.append((0.0, 0.0, radius))
    edges += [(i, len(verts) - 1) for i in range(len(verts) - 1)]
    return verts, edges


def _make_arrow(radius=1.0):
    """Freccia wireframe: base quadrata e punta sull'asse Z."""
    r = radius
    verts = [(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0), (0, 0, r * 2)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
    return verts, edges


def _make_cross(radius=1.0):
    """Croce wireframe: tre assi passanti per l'origine."""
    r = radius
    verts = [(-r, 0, 0), (r, 0, 0), (0, -r, 0), (0, r, 0), (0, 0, -r), (0, 0, r)]
    edges = [(0, 1), (2, 3), (4, 5)]
    return verts, edges


def _shape_geometry(shape, radius=1.0):
    """Dispatcher puro: restituisce (verts, edges) per la forma richiesta."""
    if shape == "CUBE":
        return _make_cube(radius)
    if shape == "SPHERE":
        return _make_sphere(radius)
    if shape == "ARROW":
        return _make_arrow(radius)
    if shape == "CROSS":
        return _make_cross(radius)
    # "CIRCLE" e qualunque valore non previsto ricadono sul cerchio
    return _make_circle(radius)


def _create_shape_object(shape, radius, col):
    verts, edges = _shape_geometry(shape, radius)
    mesh = bpy.data.meshes.new("CTRL_Shape")
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new("CTRL_Shape", mesh)
    col.objects.link(obj)
    return obj


def _get_or_create_shape(shape, col):
    """Restituisce la custom shape condivisa per forma (una sola per tipo).

    La dimensione per controller resta su pose bone.custom_shape_scale_xyz,
    quindi l'oggetto mesh e' unico: CTRL_DEF_SHAPE_CIRCLE, ..._CUBE, ecc.
    """
    name = f"CTRL_DEF_SHAPE_{shape}"
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = _create_shape_object(shape, 1.0, col)
        obj.name = name
        obj.location = (0.0, 0.0, 0.0)
    elif obj.name not in {o.name for o in col.objects}:
        # Ricollega alla collezione attesa se l'utente l'ha spostata/rimossa
        col.objects.link(obj)
    # Nome canonico anche per la mesh dati (evita CTRL_Shape.001)
    if obj.data is not None:
        obj.data.name = name
    return obj


# ===========================================================================
# Voci delle EnumProperty (callback: etichette tradotte a ogni disegno)
# ===========================================================================
# Con items come funzione callback il valore di default non e' piu' una
# stringa ma l'indice intero: il primo elemento (indice 0) e' il default,
# quindi non si passa default= e la prima voce resta quella attesa.
def _items_shape(self, context):
    """Forme disponibili per la custom shape del controller."""
    return [
        ("CIRCLE", tr("shape.circle"), ""),
        ("CUBE", tr("shape.cube"), ""),
        ("SPHERE", tr("shape.sphere"), ""),
        ("ARROW", tr("shape.arrow"), ""),
        ("CROSS", tr("shape.cross"), ""),
    ]


def _items_color(self, context):
    """Colori del controller (palette tema di Blender)."""
    return [
        ("NONE", tr("color.none"), ""),
        ("RED", tr("color.red"), ""),
        ("GREEN", tr("color.green"), ""),
        ("BLUE", tr("color.blue"), ""),
    ]


def _items_parent(self, context):
    """Modalita' di parenting dei controller generati."""
    return [
        ("CHAIN", tr("parent.chain"), tr("parent.chain_tip")),
        ("BONE", tr("parent.bone"), tr("parent.bone_tip")),
        ("ROOT", tr("parent.root"), tr("parent.root_tip")),
        ("NONE", tr("parent.none"), tr("parent.none_tip")),
        ("DEF", tr("parent.def"), tr("parent.def_tip")),
    ]


def _items_preset(self, context):
    """Preset rapidi: forma, scala, colore, parent e mirror."""
    return [
        ("DEFAULT", tr("preset.default"), ""),
        ("BIPED_LIMB", tr("preset.biped"), ""),
        ("ROOT_CTRL", tr("preset.root"), ""),
        ("FACE", tr("preset.face"), ""),
    ]


# ===========================================================================
# PropertyGroup impostazioni utente
# ===========================================================================
class CTRLDEF_PG_settings(PropertyGroup):
    prefix_def: StringProperty(
        name=tr("panel.prefix_def"), default="DEF_")
    # Default vuoto = nome pulito senza prefisso (standard Blender/Rigify):
    # DEF_hand.L -> hand.L. Con "CTRL_" si ottiene CTRL_hand.L.
    prefix_ctrl: StringProperty(
        name=tr("panel.prefix_ctrl"), default="")
    # Default = prima voce della callback: CIRCLE
    shape: EnumProperty(
        name=tr("panel.shape"),
        items=_items_shape)
    scale: FloatProperty(
        name=tr("panel.scale"), default=1.0, min=0.01)
    # Default = prima voce della callback: NONE
    color: EnumProperty(
        name=tr("panel.color"),
        items=_items_color)
    # Default = prima voce della callback: CHAIN
    parent: EnumProperty(
        name=tr("panel.parent"),
        items=_items_parent)
    mirror: BoolProperty(
        name=tr("panel.mirror"), default=False)
    # Default = prima voce della callback: DEFAULT
    preset: EnumProperty(
        name=tr("panel.preset"),
        items=_items_preset)


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


_PRESETS = {
    "DEFAULT": {"shape": "CIRCLE", "scale": 1.0, "color": "NONE",
                "parent": "CHAIN", "mirror": False},
    "BIPED_LIMB": {"shape": "CUBE", "scale": 0.8, "color": "RED",
                   "parent": "CHAIN", "mirror": True},
    "ROOT_CTRL": {"shape": "ARROW", "scale": 2.0, "color": "BLUE",
                  "parent": "ROOT", "mirror": False},
    "FACE": {"shape": "SPHERE", "scale": 0.3, "color": "GREEN",
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
# Panel sidebar (N)
# ===========================================================================
def _draw_stats_box(layout, arm, stg):
    """Riquadro con conteggi DEF/CTRL; disegnato solo se c'e' un'armatura."""
    box = layout.box()
    box.label(text=tr("panel.stats"), icon='INFO')
    data = _read_registry(arm)
    def_count = sum(1 for b in arm.data.bones if _is_def_bone(b, stg.prefix_def))
    ctrl_count = len(data)
    box.label(text=tr("stats.line") % (def_count, ctrl_count))


def _draw_preset_box(layout, stg):
    """Riga preset con pulsante di applicazione."""
    box_p = layout.box()
    row = box_p.row(align=True)
    row.prop(stg, "preset", text=tr("panel.preset"))
    row.operator("ctrl_def.apply_preset", text="", icon='CHECKMARK')


def _draw_settings(layout, stg):
    """Proprieta' di personalizzazione dei controller."""
    layout.prop(stg, "prefix_def", text=tr("panel.prefix_def"))
    layout.prop(stg, "prefix_ctrl", text=tr("panel.prefix_ctrl"))
    layout.prop(stg, "shape", text=tr("panel.shape"))
    layout.prop(stg, "scale", text=tr("panel.scale"))
    layout.prop(stg, "color", text=tr("panel.color"))
    layout.prop(stg, "parent", text=tr("panel.parent"))
    layout.prop(stg, "mirror", text=tr("panel.mirror"))
    layout.separator()


def _draw_actions(layout):
    """Pulsanti delle operazioni principali."""
    layout.operator("ctrl_def.generate", text=tr("op.generate"), icon='BONE_DATA')
    layout.operator("ctrl_def.bind_actd", text=tr("op.bind_actd"), icon='CONSTRAINT_BONE')
    layout.operator("ctrl_def.remove", text=tr("op.remove"), icon='TRASH')


class CTRLDEF_PT_panel(Panel):
    bl_label = tr("panel.label")
    bl_idname = "CTRLDEF_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DEF Ctrl"

    def draw(self, context):
        layout = self.layout
        stg = context.scene.ctrl_def_settings
        arm = context.active_object
        if arm and arm.type == "ARMATURE":
            _draw_stats_box(layout, arm, stg)
        _draw_preset_box(layout, stg)
        _draw_settings(layout, stg)
        _draw_actions(layout)


# ===========================================================================
# Registrazione
# ===========================================================================
_classes = [
    CTRLDEF_PG_settings,
    CTRLDEF_OT_apply_preset,
    CTRLDEF_OT_generate,
    CTRLDEF_OT_bind_actd,
    CTRLDEF_OT_remove,
    CTRLDEF_PT_panel,
]


def _register_class_safe(cls):
    """Registra una classe ignorando i doppi registri (reload dell'addon)."""
    if getattr(cls, "is_registered", False):
        return
    try:
        bpy.utils.register_class(cls)
    except ValueError as exc:
        if "already registered" not in str(exc):
            raise


def _unregister_class_safe(cls):
    """Annulla la registrazione di una classe ignorando quelle gia' assenti."""
    try:
        bpy.utils.unregister_class(cls)
    except (RuntimeError, ValueError):
        pass


def register():
    for cls in _classes:
        _register_class_safe(cls)
    if not hasattr(bpy.types.Scene, "ctrl_def_settings"):
        bpy.types.Scene.ctrl_def_settings = PointerProperty(type=CTRLDEF_PG_settings)


def unregister():
    if hasattr(bpy.types.Scene, "ctrl_def_settings"):
        del bpy.types.Scene.ctrl_def_settings
    for cls in reversed(_classes):
        _unregister_class_safe(cls)


if __name__ == "__main__":
    register()
