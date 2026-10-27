# Modulo proprieta': callback EnumProperty e PropertyGroup delle impostazioni.
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       StringProperty)
from bpy.types import PropertyGroup

from .ctrl_def_i18n import tr

# ===========================================================================
# Voci delle EnumProperty (callback: etichette tradotte a ogni disegno)
# ===========================================================================
# Con items come funzione callback il valore di default non e' piu' una
# stringa ma l'indice intero: il primo elemento (indice 0) e' il default,
# quindi non si passa default= e la prima voce resta quella attesa.
# La callback va passata "nuda" (items=_items_x): Blender la riconosce come
# funzione e la richiama a ogni disegno. Una lista statica congelerebbe le
# etichette alla registrazione e le tendine non seguirebbero la lingua.
# Cache degli elenchi restituiti dalle callback: le stringhe dinamiche devono
# restare referenziate, altrimenti la garbage collection di Blender puo'
# liberarle mentre l'EnumProperty le usa (tendina vuota o crash).
_ITEMS_CACHE = []


def _items_parent(self, context):
    """Modalita' di parenting dei controller generati."""
    voci = [
        ("CHAIN", tr("parent.chain"), tr("parent.chain_tip")),
        ("BONE", tr("parent.bone"), tr("parent.bone_tip")),
        ("ROOT", tr("parent.root"), tr("parent.root_tip")),
        ("NONE", tr("parent.none"), tr("parent.none_tip")),
        ("DEF", tr("parent.def"), tr("parent.def_tip")),
    ]
    # La cache si sostituisce a ogni chiamata: le etichette restano tradotte
    # nella lingua corrente, ma l'ultimo elenco non viene liberato.
    _ITEMS_CACHE[:] = [voci]
    return voci


def _items_preset(self, context):
    """Preset rapidi: widget, scala, parent e mirror."""
    voci = [
        ("DEFAULT", tr("preset.default"), ""),
        ("BIPED_LIMB", tr("preset.biped"), ""),
        ("ROOT_CTRL", tr("preset.root"), ""),
        ("FACE", tr("preset.face"), ""),
    ]
    _ITEMS_CACHE[:] = [voci]
    return voci


def _on_preset_update(self, context):
    """Applica subito i valori del preset scelto nella tendina.

    L'import e' pigro: _PRESETS vive in ctrl_def_operators, che non importa
    questo modulo, cosi' non si crea un ciclo a import-time.
    """
    try:
        from .ctrl_def_operators import _apply_preset_values
    except ImportError:
        return
    _apply_preset_values(self, self.preset)


# ===========================================================================
# PropertyGroup impostazioni utente
# ===========================================================================
class CTRLDEF_PG_settings(PropertyGroup):
    prefix_def: StringProperty(
        name=tr("panel.prefix_def"), default="DEF_",
        description=tr("tip.prop.prefix_def"))
    # Default vuoto = nome pulito senza prefisso (standard Blender/Rigify):
    # DEF_hand.L -> hand.L. Con "CTRL_" si ottiene CTRL_hand.L.
    prefix_ctrl: StringProperty(
        name=tr("panel.prefix_ctrl"), default="",
        description=tr("tip.prop.prefix_ctrl"))
    # Nome del widget creato da Bone Widget (estensione opzionale): il default
    # e' il widget "Circle" fornito dall'estensione stessa. Resta una stringa
    # editabile: il nome non e' vincolato a un elenco chiuso di widget.
    widget_name: StringProperty(
        name=tr("panel.shape"), default="Circle")
    scale: FloatProperty(
        name=tr("panel.scale"), default=1.0, min=0.01,
        description=tr("tip.prop.scale"))
    # La rotazione della custom shape non e' piu' gestita da CTRL_DEF: la fa
    # Bone Widget sul widget condiviso, quindi qui non esiste alcuna proprieta'.
    # Il colore dei controller lo gestisce Bone Widget: nessuna proprieta' qui.
    # Default = prima voce della callback: CHAIN
    parent: EnumProperty(
        name=tr("panel.parent"),
        description=tr("tip.prop.parent"),
        items=_items_parent)
    mirror: BoolProperty(
        name=tr("panel.mirror"), default=False,
        description=tr("tip.prop.mirror"))
    # Default = prima voce della callback: DEFAULT. update= applica i valori
    # del preset appena la tendina cambia, senza un secondo click.
    preset: EnumProperty(
        name=tr("panel.preset"),
        description=tr("tip.prop.preset"),
        items=_items_preset,
        update=_on_preset_update)


