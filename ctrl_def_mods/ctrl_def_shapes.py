# Modulo shape: naming, mirror L/R e delega dei widget all'estensione
# Bone Widget (WayneDixon). CTRL_DEF non crea piu' mesh di custom shape.
import bpy

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


# ===========================================================================
# Widget: delega all'estensione opzionale Bone Widget
# ===========================================================================
# Nomi con cui il pacchetto puo' comparire: estensione Blender.org caricata
# come bl_ext.<repo>.bone_widget oppure addon storico copiato in addons/ con
# il nome storico "bonewidget".
_BONEWIDGET_SUFFISSI = ("bone_widget", "bonewidget")


def _bonewidget_available():
    """True se Bone Widget e' installato e attivo nelle preferenze o caricato."""
    chiavi = ()
    try:
        chiavi = tuple(bpy.context.preferences.addons.keys())
    except (AttributeError, RuntimeError):
        chiavi = ()
    for chiave in chiavi:
        for suffisso in _BONEWIDGET_SUFFISSI:
            if chiave == suffisso or chiave.endswith("." + suffisso):
                return True
    # Fallback: non si puo' usare hasattr(bpy.ops.bonewidget, "create_widget"),
    # perche' il sotto-modulo degli operatori e' pigro e risponde True anche
    # senza l'estensione. La classe registrata su bpy.types esiste invece solo
    # se il modulo dell'estensione e' davvero caricato.
    return hasattr(bpy.types, "BONEWIDGET_OT_create_widget")


def _bonewidget_create(arm, names, shape_name, size):
    """Crea i widget dei controller indicati tramite Bone Widget.

    I pose bone vengono selezionati e `widget_list` del window manager riceve
    il nome del widget scelto: a quel punto l'operatore dell'estensione assegna
    la custom shape a ogni osso selezionato. Restituisce False (senza
    sollevare eccezioni) quando Bone Widget non e' disponibile o non e'
    possibile applicare i widget.
    """
    if not _bonewidget_available():
        return False
    if arm is None or arm.type != "ARMATURE" or not names:
        return False
    try:
        if arm.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        # Solo i controller generati devono ricevere il widget
        for pbone in arm.pose.bones:
            pbone.select = pbone.name in set(names)
        bpy.context.window_manager.widget_list = shape_name
        bpy.ops.bonewidget.create_widget(
            relative_size=True, global_size_simple=size)
        # Redo Panel e strumenti di Bone Widget restano attivi: l'armatura
        # deve restare in Pose Mode con il primo controller come bone attivo.
        primo = arm.data.bones.get(names[0])
        if primo is not None:
            arm.data.bones.active = primo
        if arm.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
    except (AttributeError, RuntimeError, TypeError):
        # Estensione presente ma operatore non invocabile in questo contesto
        return False
    return True


