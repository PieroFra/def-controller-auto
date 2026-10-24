bl_info = {
    "name": "DEF Controller Auto",
    "author": "",
    "version": (0, 1, 0),
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
        "panel.prefix_def": "Prefisso DEF",
        "panel.prefix_ctrl": "Prefisso Controller",
        "panel.shape": "Forma",
        "panel.scale": "Scala",
        "panel.color": "Colore",
        "panel.parent": "Parent",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Stato Armatura",
        "op.generate": "Genera Controller",
        "op.create": "Crea Controller",
        "op.remove": "Rimuovi Generati",
        "op.apply_preset": "Applica Preset",
        "msg.created": "Controller creati",
        "msg.removed": "Controller rimossi",
        "msg.no_armature": "Nessuna armatura attiva",
        "msg.no_def_bones": "Nessun bone DEF selezionato",
    },
    "en": {
        "panel.label": "DEF Controller",
        "panel.prefix_def": "DEF Prefix",
        "panel.prefix_ctrl": "Controller Prefix",
        "panel.shape": "Shape",
        "panel.scale": "Scale",
        "panel.color": "Color",
        "panel.parent": "Parent",
        "panel.mirror": "Mirror L/R",
        "panel.preset": "Preset",
        "panel.stats": "Armature Status",
        "op.generate": "Generate Controllers",
        "op.remove": "Remove Generated",
        "op.apply_preset": "Apply Preset",
        "msg.created": "Controllers created",
        "msg.removed": "Controllers removed",
        "msg.no_armature": "No active armature",
        "msg.no_def_bones": "No DEF bones selected",
    },
}


def tr(key, lang=None):
    if lang is None:
        lang = bpy.context.preferences.view.language if bpy.context and bpy.context.preferences else "en"
    return _I18N.get(lang, _I18N["en"]).get(key, key)


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
    base = name
    for suf in (".L", "_L", ".R", "_R"):
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    if side == "L":
        return base + ".R"
    if side == "R":
        return base + ".L"
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


def _create_shape_object(shape, radius, col):
    if shape == "CIRCLE":
        verts, edges = _make_circle(radius)
    elif shape == "CUBE":
        r = radius
        verts = [(-r, -r, -r), (r, -r, -r), (r, r, -r), (-r, r, -r),
                 (-r, -r, r), (r, -r, r), (r, r, r), (-r, r, r)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0),
                 (4, 5), (5, 6), (6, 7), (7, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
    elif shape == "SPHERE":
        verts, edges = _make_circle(radius, 12)
        verts.append((0.0, 0.0, radius))
        edges += [(i, len(verts) - 1) for i in range(len(verts) - 1)]
    elif shape == "ARROW":
        r = radius
        verts = [(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0), (0, 0, r * 2)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
    elif shape == "CROSS":
        r = radius
        verts = [(-r, 0, 0), (r, 0, 0), (0, -r, 0), (0, r, 0), (0, 0, -r), (0, 0, r)]
        edges = [(0, 1), (2, 3), (4, 5)]
    else:
        verts, edges = _make_circle(radius)
    mesh = bpy.data.meshes.new("CTRL_Shape")
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new("CTRL_Shape", mesh)
    col.objects.link(obj)
    return obj


# ===========================================================================
# PropertyGroup impostazioni utente
# ===========================================================================
class CTRLDEF_PG_settings(PropertyGroup):
    prefix_def: StringProperty(
        name=tr("panel.prefix_def"), default="DEF_")
    prefix_ctrl: StringProperty(
        name=tr("panel.prefix_ctrl"), default="CTRL_")
    shape: EnumProperty(
        name=tr("panel.shape"),
        items=[
            ("CIRCLE", "Cerchio", ""),
            ("CUBE", "Cubo", ""),
            ("SPHERE", "Sfera", ""),
            ("ARROW", "Freccia", ""),
            ("CROSS", "Croce", ""),
        ],
        default="CIRCLE")
    scale: FloatProperty(
        name=tr("panel.scale"), default=1.0, min=0.01)
    color: EnumProperty(
        name=tr("panel.color"),
        items=[
            ("NONE", "Nessuno", ""),
            ("RED", "Rosso", ""),
            ("GREEN", "Verde", ""),
            ("BLUE", "Blu", ""),
        ],
        default="NONE")
    parent: EnumProperty(
        name=tr("panel.parent"),
        items=[
            ("DEF", "DEF stesso", ""),
            ("BONE", "Bone genitore", ""),
            ("ROOT", "Root", ""),
        ],
        default="DEF")
    mirror: BoolProperty(
        name=tr("panel.mirror"), default=False)
    preset: EnumProperty(
        name=tr("panel.preset"),
        items=[
            ("DEFAULT", "Default (Cerchio / DEF)", ""),
            ("BIPED_LIMB", "Arto Bipede (Cubo / BONE)", ""),
            ("ROOT_CTRL", "Root Controller (Freccia / ROOT)", ""),
            ("FACE", "Faccia (Sfera / DEF)", ""),
        ],
        default="DEFAULT")


# ===========================================================================
# Operatori
# ===========================================================================
class CTRLDEF_OT_generate(Operator):
    bl_idname = "ctrl_def.generate"
    bl_label = tr("op.generate")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scn = context.scene
        stg = scn.ctrl_def_settings
        arm = context.active_object
        if arm is None or arm.type != "ARMATURE":
            self.report({'ERROR'}, tr("msg.no_armature"))
            return {'CANCELLED'}
        if arm.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        ebones = arm.data.edit_bones
        sel = [b for b in ebones if b.select and _is_def_bone(b, stg.prefix_def)]
        if not sel:
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'ERROR'}, tr("msg.no_def_bones"))
            return {'CANCELLED'}
        # Elabora i bone selezionati e, se richiesto, i corrispondenti specchiati L/R
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
        # Radice per l'opzione parent="ROOT": primo bone senza genitore
        root_ebone = next((eb for eb in ebones if eb.parent is None), None)
        created = []
        # Il controller è un bone dell'armatura, non un oggetto: ricalca il DEF
        for b in da_fare:
            name = stg.prefix_ctrl + b.name[len(stg.prefix_def):]
            ebone = ebones.get(name)
            if ebone is None:
                ebone = ebones.new(name)
            ebone.head = b.head.copy()
            if (b.tail - b.head).length > 1e-6:
                ebone.tail = b.tail.copy()
            else:
                ebone.tail = b.head + Vector((0.0, 0.1, 0.0))
            ebone.roll = b.roll
            # Parent del controller secondo l'opzione scelta nel pannello
            if stg.parent == "DEF":
                ebone.parent = b
            elif stg.parent == "BONE":
                ebone.parent = b.parent
            elif stg.parent == "ROOT":
                ebone.parent = None if root_ebone is b else root_ebone
            created.append((name, b.name))
        bpy.ops.object.mode_set(mode='OBJECT')
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
            shape = pbone.custom_shape
            if shape is None:
                shape = _create_shape_object(stg.shape, 1.0, col)
                shape.name = name + "_shape"
                shape.location = (0.0, 0.0, 0.0)
            pbone.custom_shape = shape
            pbone.custom_shape_scale_xyz = (stg.scale, stg.scale, stg.scale)
            # Colore del controller (se scelto un colore non NONE)
            if palette:
                pbone.color.palette = palette
            # Iscrizione alla bone collection "CTRL"
            if bone is not None and bcoll.name not in (c.name for c in bone.collections):
                bcoll.assign(bone)
            _mark_generated(arm, name, def_name)
        self.report({'INFO'}, tr("msg.created") + ": " + str(len(created)))
        return {'FINISHED'}


class CTRLDEF_OT_apply_preset(Operator):
    bl_idname = "ctrl_def.apply_preset"
    bl_label = tr("op.apply_preset")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        stg = context.scene.ctrl_def_settings
        p = stg.preset
        if p == "DEFAULT":
            stg.shape = "CIRCLE"
            stg.scale = 1.0
            stg.color = "NONE"
            stg.parent = "DEF"
            stg.mirror = False
        elif p == "BIPED_LIMB":
            stg.shape = "CUBE"
            stg.scale = 0.8
            stg.color = "RED"
            stg.parent = "BONE"
            stg.mirror = True
        elif p == "ROOT_CTRL":
            stg.shape = "ARROW"
            stg.scale = 2.0
            stg.color = "BLUE"
            stg.parent = "ROOT"
            stg.mirror = False
        elif p == "FACE":
            stg.shape = "SPHERE"
            stg.scale = 0.3
            stg.color = "GREEN"
            stg.parent = "DEF"
            stg.mirror = True
        return {'FINISHED'}


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
            self.report({'INFO'}, tr("msg.removed") + ": 0")
            return {'FINISHED'}
        # Raccoglie le forme da eliminare prima di entrare in Edit Mode
        shapes = []
        for name in data.keys():
            pbone = arm.pose.bones.get(name)
            if pbone is not None and pbone.custom_shape is not None:
                shapes.append(pbone.custom_shape)
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
        for shape in shapes:
            if bpy.data.objects.get(shape.name) is not None:
                bpy.data.objects.remove(shape, do_unlink=True)
        self.report({'INFO'}, tr("msg.removed") + ": " + str(removed))
        return {'FINISHED'}


# ===========================================================================
# Panel sidebar (N)
# ===========================================================================
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
            box = layout.box()
            box.label(text=tr("panel.stats"), icon='INFO')
            data = _read_registry(arm)
            eb_count = len(arm.data.bones)
            def_count = sum(1 for b in arm.data.bones if _is_def_bone(b, stg.prefix_def))
            ctrl_count = len(data)
            box.label(text=f"DEF trovati: {def_count} | CTRL generati: {ctrl_count}")
        box_p = layout.box()
        row = box_p.row(align=True)
        row.prop(stg, "preset")
        row.operator("ctrl_def.apply_preset", text="", icon='CHECKMARK')
        layout.prop(stg, "prefix_def")
        layout.prop(stg, "prefix_ctrl")
        layout.prop(stg, "shape")
        layout.prop(stg, "scale")
        layout.prop(stg, "color")
        layout.prop(stg, "parent")
        layout.prop(stg, "mirror")
        layout.separator()
        layout.operator("ctrl_def.generate")
        layout.operator("ctrl_def.remove")


# ===========================================================================
# Registrazione
# ===========================================================================
_classes = [
    CTRLDEF_PG_settings,
    CTRLDEF_OT_apply_preset,
    CTRLDEF_OT_generate,
    CTRLDEF_OT_remove,
    CTRLDEF_PT_panel,
]


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ctrl_def_settings = PointerProperty(type=CTRLDEF_PG_settings)


def unregister():
    del bpy.types.Scene.ctrl_def_settings
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
