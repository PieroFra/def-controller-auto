# Modulo UI: pannello della sidebar e helper di disegno.
import re

import bpy
from bpy.types import Panel

from .ctrl_def_i18n import tr
from .ctrl_def_operators import _resolve_armature
from .ctrl_def_registry import _read_registry
from .ctrl_def_shapes import _bonewidget_available, _is_def_bone

# Pagina ufficiale dell'estensione Bone Widget (dipendenza opzionale).
_BONEWIDGET_URL = "https://extensions.blender.org/add-ons/bone-widget/"

# ===========================================================================
# Panel sidebar (N)
# ===========================================================================
def _section(layout, chiave, chiusa=False):
    """Apre una sezione collassabile con titolo; fallback su box semplice
    quando l'API dei pannelli annidati non e' disponibile."""
    if hasattr(layout, "panel"):
        try:
            coppia = layout.panel(chiave, default_closed=chiusa)
        except (AttributeError, TypeError, RuntimeError):
            coppia = None
        # Con la sezione chiusa `layout.panel` restituisce (intestazione, None):
        # in quel caso si restituisce None, senza disegnare un box sempre aperto.
        if coppia is not None and len(coppia) == 2:
            intestazione, corpo = coppia
            if intestazione is not None:
                intestazione.label(text=tr(chiave))
                return corpo
    box = layout.box()
    box.label(text=tr(chiave))
    return box


def _draw_stats_box(layout, arm, stg):
    """Conteggi DEF/CTRL compattati su una riga sola."""
    data = _read_registry(arm)
    def_count = sum(1 for b in arm.data.bones if _is_def_bone(b, stg.prefix_def))
    ctrl_count = len(data)
    box = layout.box()
    row = box.row(align=True)
    row.label(text=tr("panel.stats"), icon='INFO')
    row.label(text=tr("stats.line") % (def_count, ctrl_count))


def _draw_preset_box(layout, stg):
    """Riga preset con pulsante di applicazione."""
    row = layout.row(align=True)
    row.prop(stg, "preset", text=tr("panel.preset"))
    row.operator("ctrl_def.apply_preset", text="", icon='CHECKMARK')


# Modalita' di pipeline che prevedono bone MCH/ORG da bloccare.
_LOCK_MODES = ("DEF_MCH_CTRL", "DEF_ORG_MCH_CTRL", "MCH_ORG", "ORG_CTRL")


def _draw_settings(layout, stg):
    """Setup: pipeline, prefissi dei bone e specchiatura L/R."""
    layout.prop(stg, "pipeline_mode", text=tr("panel.pipeline"))
    layout.prop(stg, "prefix_def", text=tr("panel.prefix_def"))
    layout.prop(stg, "prefix_ctrl", text=tr("panel.prefix_ctrl"))
    if getattr(stg, "pipeline_mode", "DEF_CTRL") in _LOCK_MODES:
        layout.prop(stg, "lock_mch_org", text=tr("panel.lock_mch_org"))
    layout.prop(stg, "mirror", text=tr("panel.mirror"))


def _draw_widget_box(layout, stg):
    """Riquadro Bone Widget: pulsante di creazione o avviso di installazione."""
    # I widget li crea Bone Widget: con l'estensione attiva l'utente sceglie la
    # forma dalla libreria e preme "Crea Widget", senza estensione si avvisa e
    # si offre la pagina di installazione.
    box = layout.box()
    box.label(text=tr("panel.widget"), icon='MOD_WIREFRAME')
    if _bonewidget_available():
        if hasattr(bpy.context.window_manager, "widget_list"):
            box.prop(bpy.context.window_manager, "widget_list", text="")
        box.operator("ctrl_def.create_widget",
                     text=tr("op.bw_create"), icon='MOD_WIREFRAME')
    else:
        box.label(text=tr("msg.bw_missing"), icon='ERROR')
        box.operator("wm.url_open", text=tr("op.bw_install"),
                     icon='URL').url = _BONEWIDGET_URL


def _draw_controller_settings(layout, stg):
    """Aspetto e gerarchia dei controller generati."""
    layout.prop(stg, "scale", text=tr("panel.scale"))
    layout.prop(stg, "parent", text=tr("panel.parent"))


def _draw_ik_box(layout, stg=None):
    """Target IK rapido sui controller selezionati (Fase E)."""
    if stg is None:
        stg = getattr(bpy.context.scene, "ctrl_def_settings", None)
    layout.label(text=tr("panel.ik"), icon='CONSTRAINT')
    if stg is not None:
        layout.prop(stg, "ik_align_world_y", text=tr("panel.ik_align_y"))
        layout.prop(stg, "ik_create_pole", text=tr("panel.ik_pole"))
        if getattr(stg, "ik_create_pole", False):
            layout.prop(stg, "ik_pole_source", text=tr("panel.ik_pole_source"))
        layout.prop(stg, "ik_chain_length", text=tr("panel.ik_chain_length"),
                    slider=True)
    layout.operator("ctrl_def.add_ik", text=tr("op.add_ik"), icon='CONSTRAINT')
    row = layout.row(align=True)
    row.operator("ctrl_def.snap_ik_to_fk", text=tr("op.snap_ik_to_fk"))
    row.operator("ctrl_def.bake_ik_to_fk", text=tr("op.bake_ik_to_fk"))
    if stg is not None:
        row = layout.row(align=True)
        row.prop(stg, "ik_target_space", text=tr("panel.ik_target_space"))
        row.operator("ctrl_def.set_ik_target_space",
                     text=tr("op.set_ik_target_space"))


def _draw_export_box(layout):
    """Export della mappa CTRL->DEF e preset utente su file."""
    layout.label(text=tr("panel.export"), icon='FILEBROWSER')
    layout.operator("ctrl_def.export_json", text=tr("op.export_json"), icon='EXPORT')
    layout.operator("ctrl_def.export_csv", text=tr("op.export_csv"), icon='EXPORT')
    layout.operator("ctrl_def.save_preset", text=tr("op.save_preset"), icon='FILE_TICK')
    layout.operator("ctrl_def.load_preset", text=tr("op.load_preset"), icon='FILEBROWSER')


def _draw_actions(layout):
    """Azione principale in evidenza, poi vincolo e azioni di contorno."""
    col = layout.column(align=True)
    sub = col.row(align=True)
    sub.scale_y = 1.3
    sub.operator("ctrl_def.generate", text=tr("op.generate"), icon='BONE_DATA')
    col.operator("ctrl_def.bind_actd", text=tr("op.bind_actd"),
                 icon='CONSTRAINT_BONE')
    row = layout.row(align=True)
    row.operator("ctrl_def.auto_collection", text=tr("op.auto_collection"),
                 icon='GROUP_BONE')
    row.operator("ctrl_def.character_picker", text=tr("op.character_picker"),
                 icon='GROUP')
    row.operator("ctrl_def.handoff_animator", text=tr("op.handoff_animator"),
                 icon='HIDE_OFF')
    row.operator("ctrl_def.restore_rigger", text=tr("op.restore_rigger"),
                 icon='LOOP_BACK')


# Ordine canonico delle categorie nel report di ctrl_def.rig_score.
_RIG_SCORE_CATEGORIE = ("STRUTTURA", "CONTROLLI", "DEFORMAZIONE",
                        "MANUTENIBILITA", "CONSEGNA")


def _parse_rig_score_summary(raw):
    """Riepilogo del report `_ctrl_def_last_rig_score`, None se non valido.

    Formato atteso (output di ctrl_def.rig_score):
        "RIG_SCORE X/30 | STRUTTURA a/6 | 1.1 OK; ... ; CONTROLLI b/7 | ..."
    Tollerante: None, valori non-stringa, testo senza voto o senza categorie
    restituiscono None, cosi' la UI non disegna un box vuoto o incoerente.
    """
    if not isinstance(raw, str):
        return None
    testo = raw.strip()
    if not testo:
        return None
    testo_upper = testo.upper()
    if "RIG_SCORE" not in testo_upper:
        return None
    # Voto globale X/30: prima quello dichiarato subito dopo RIG_SCORE.
    voto = re.search(r"RIG_SCORE\s+(\d+)\s*/\s*(\d+)", testo_upper)
    if voto is None:
        voto = re.search(r"(\d+)\s*/\s*(\d+)", testo_upper)
    if voto is None:
        return None
    # Conversione difensiva: un voto non numerico non deve rompere il draw.
    try:
        punti, totale = int(voto.group(1)), int(voto.group(2))
    except (TypeError, ValueError):
        return None
    if totale <= 0 or punti < 0 or punti > totale:
        return None
    # Coppie (categoria, punteggio) nell'ordine canonico del report.
    categorie = []
    for nome in _RIG_SCORE_CATEGORIE:
        trovata = re.search(r"\b%s\s+(\d+)\s*/\s*(\d+)" % nome, testo_upper)
        if trovata is not None:
            categorie.append((nome, "%s/%s" % (trovata.group(1),
                                               trovata.group(2))))
    if not categorie:
        return None
    # Voci FAIL con l'eventuale dettaglio tra parentesi angolari.
    fail = []
    for match in re.finditer(r"(\d+\.\d+)\s+FAIL\s*(?:<([^>]*)>)?",
                             testo, re.IGNORECASE):
        codice = match.group(1)
        dettaglio = (match.group(2) or "").strip()
        fail.append("%s <%s>" % (codice, dettaglio) if dettaglio else codice)
    return {
        "score": punti,
        "total": totale,
        "score_text": "%d/%d" % (punti, totale),
        "categories": categorie,
        "fails": fail,
    }


def _draw_rig_score_box(layout, riepilogo):
    """Box compatto con voto, categorie e fail dell'ultimo rig_score."""
    box = layout.box()
    riga = box.row(align=True)
    icona = 'CHECKMARK' if riepilogo["score"] == riepilogo["total"] else 'INFO'
    riga.label(text="Rig Score: %s" % riepilogo["score_text"], icon=icona)
    categorie = riepilogo["categories"]
    # Una categoria per riga: i nomi lunghi (DEFORMAZIONE, MANUTENIBILITA)
    # non vanno mai troncati nella sidebar stretta.
    for nome, punteggio in categorie:
        box.row(align=True).label(text="%s %s" % (nome, punteggio))
    # Fino a 3 FAIL, con dettaglio accorciato per restare nella sidebar.
    for voce in riepilogo["fails"][:3]:
        dettaglio = voce if len(voce) <= 34 else voce[:31] + "..."
        box.row(align=True).label(text="FAIL %s" % dettaglio, icon='ERROR')


def _draw_rig_score_from_arm(layout, arm):
    """Box dell'ultimo Rig Score letto dall'armatura attiva.

    Il box vive nella sezione Setup (sempre aperta), non in Avanzate: dopo
    aver premuto Rig Score il voto e le categorie devono essere visibili
    senza espandere nulla. Un report mancante o rotto viene ignorato.
    """
    if arm is None or getattr(arm, "type", None) != 'ARMATURE':
        return
    try:
        grezzo = arm.get("_ctrl_def_last_rig_score")
    except (AttributeError, TypeError):
        grezzo = None
    riepilogo = _parse_rig_score_summary(grezzo)
    if riepilogo is not None:
        _draw_rig_score_box(layout, riepilogo)


def _draw_advanced_actions(layout, arm=None, stg=None):
    """Diagnostica, manifest, rimappatura e pulizia su righe compatte."""
    row = layout.row(align=True)
    row.operator("ctrl_def.diagnose", text=tr("op.diagnose"), icon='VIEWZOOM')
    row.operator("ctrl_def.rig_score", text=tr("op.rig_score"), icon='SOLO_ON')
    row = layout.row(align=True)
    row.operator("ctrl_def.manifest", text=tr("op.manifest"), icon='FILE_TEXT')
    row.operator("ctrl_def.manifest_diff", text=tr("op.manifest_diff"),
                 icon='FILE_REFRESH')
    # Mappa JSON del Naming Doctor: senza il campo il pulsante inviava sempre
    # "{}" e rispondeva "nessun rename da applicare". Il campo resta vuoto o
    # "{}" di default e il pulsante gli passa il valore corrente.
    if stg is not None:
        layout.prop(stg, "naming_rename_map", text=tr("panel.rename_map_json"))
    row = layout.row(align=True)
    row.operator("ctrl_def.remap", text=tr("op.remap"), icon='ARMATURE_DATA')
    pulsante = row.operator("ctrl_def.naming_doctor", text=tr("op.naming_doctor"),
                            icon='SORTALPHA')
    if stg is not None:
        pulsante.rename_map_json = stg.naming_rename_map
    layout.operator("ctrl_def.remove", text=tr("op.remove"), icon='TRASH')


def _draw_guide(layout):
    """Guida rapida in 7 passi, chiusa di default."""
    corpo = _section(layout, "sec.guide", chiusa=True)
    if corpo is not None:
        for passo in range(1, 8):
            corpo.label(text=tr("guide.%d" % passo))


# _resolve_armature e' importato da ctrl_def_operators: unica implementazione
# condivisa, nessun duplicato tra UI e operatori (vedi import in testa al file).


class CTRLDEF_PT_panel(Panel):
    bl_label = tr("panel.label")
    bl_idname = "CTRLDEF_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DEF Ctrl"

    def draw(self, context):
        layout = self.layout
        stg = context.scene.ctrl_def_settings
        arm = _resolve_armature(context)
        # 1 · Setup: stato, preset, prefissi e mirror (aperta)
        corpo = _section(layout, "sec.setup")
        if corpo is not None:
            if arm is not None:
                _draw_stats_box(corpo, arm, stg)
            # Box Rig Score accanto allo stato: visibile subito dopo il click
            # sul pulsante, senza aprire la sezione Avanzate.
            _draw_rig_score_from_arm(corpo, arm)
            _draw_preset_box(corpo, stg)
            _draw_settings(corpo, stg)
        # 2 · Controller: aspetto, poi le due azioni principali (aperta)
        corpo = _section(layout, "sec.controller")
        if corpo is not None:
            _draw_controller_settings(corpo, stg)
            _draw_widget_box(corpo, stg)
            _draw_actions(corpo)
        # 3 · Avanzate: IK, export/preset, diagnostica e pulizia (chiusa)
        corpo = _section(layout, "sec.advanced", chiusa=True)
        if corpo is not None:
            _draw_ik_box(corpo, stg)
            _draw_export_box(corpo)
            _draw_advanced_actions(corpo, arm, stg)
        # Guida rapida in fondo (chiusa)
        _draw_guide(layout)


