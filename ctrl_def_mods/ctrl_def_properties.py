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


def _cache_items(slot, voci):
    """Trattiene l'elenco di una callback nella sua cella della cache.

    La cache e' una lista con una cella per callback: aggiornare una cella non
    svuota le altre, cosi' gli elenchi restituiti da _items_parent,
    _items_preset e _items_pipeline restano tutti referenziati.
    """
    while len(_ITEMS_CACHE) <= slot:
        _ITEMS_CACHE.append([])
    _ITEMS_CACHE[slot] = voci
    return voci


def _items_parent(self, context):
    """Modalita' di parenting dei controller generati."""
    voci = [
        ("CHAIN", tr("parent.chain"), tr("parent.chain_tip")),
        ("BONE", tr("parent.bone"), tr("parent.bone_tip")),
        ("ROOT", tr("parent.root"), tr("parent.root_tip")),
        ("NONE", tr("parent.none"), tr("parent.none_tip")),
        ("DEF", tr("parent.def"), tr("parent.def_tip")),
    ]
    # La cache si aggiorna nella cella di questa callback: le etichette restano
    # tradotte nella lingua corrente e gli elenchi delle altre callback restano.
    return _cache_items(0, voci)


def _items_preset(self, context):
    """Preset rapidi: widget, scala, parent e mirror."""
    voci = [
        ("DEFAULT", tr("preset.default"), ""),
        ("BIPED_LIMB", tr("preset.biped"), ""),
        ("ROOT_CTRL", tr("preset.root"), ""),
        ("FACE", tr("preset.face"), ""),
    ]
    return _cache_items(1, voci)


def _items_pipeline(self, context):
    """Pipeline di trasformazione tra layer: DEF, ORG, MCH, CTRL."""
    voci = [
        ("DEF_CTRL", tr("pipeline.def_ctrl"), ""),
        ("DEF_MCH_CTRL", tr("pipeline.def_mch_ctrl"), ""),
        ("DEF_ORG_MCH_CTRL", tr("pipeline.def_org_mch_ctrl"), ""),
        ("MCH_ORG", tr("pipeline.mch_org"), ""),
        ("ORG_CTRL", tr("pipeline.org_ctrl"), ""),
        ("CUSTOM", tr("pipeline.custom"), ""),
    ]
    return _cache_items(2, voci)


def _on_pipeline_update(self, context):
    """Allinea i prefissi DEF/CTRL alla pipeline scelta.

    CUSTOM non tocca i prefissi: l'utente li imposta a mano.
    """
    modo = self.pipeline_mode
    if modo == "DEF_CTRL":
        self.prefix_def = "DEF_"
        self.prefix_ctrl = ""
    elif modo == "MCH_ORG":
        self.prefix_def = "MCH_"
        self.prefix_ctrl = "ORG_"
    elif modo == "ORG_CTRL":
        self.prefix_def = "ORG_"
        self.prefix_ctrl = ""
    elif modo in ("DEF_MCH_CTRL", "DEF_ORG_MCH_CTRL"):
        self.prefix_def = "DEF_"
        self.prefix_ctrl = ""


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
    # Default = prima voce della callback: DEF_CTRL (prefissi DEF_ / CTRL vuoto)
    pipeline_mode: EnumProperty(
        name=tr("panel.pipeline"),
        description=tr("tip.prop.pipeline"),
        items=_items_pipeline,
        update=_on_pipeline_update)
    lock_mch_org: BoolProperty(
        name=tr("panel.lock_mch_org"), default=True,
        description=tr("tip.prop.lock_mch_org"))
    ik_align_world_y: BoolProperty(
        name=tr("panel.ik_align_y"), default=True,
        description=tr("tip.prop.ik_align_y"))
    ik_create_pole: BoolProperty(
        name=tr("panel.ik_pole"), default=False,
        description=tr("tip.prop.ik_pole"))


