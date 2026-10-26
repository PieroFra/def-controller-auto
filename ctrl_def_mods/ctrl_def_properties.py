# MODULO ctrl_def_properties.py — callback EnumProperty e PropertyGroup delle impostazioni (intestazione di build, non fa parte del monolite)
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


