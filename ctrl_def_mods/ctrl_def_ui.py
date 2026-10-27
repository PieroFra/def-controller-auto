# Modulo UI: pannello della sidebar e helper di disegno.
import bpy
from bpy.types import Panel

from .ctrl_def_i18n import tr
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
    """Conteggi DEF/CTRL; disegnati solo se c'e' un'armatura."""
    layout.label(text=tr("panel.stats"), icon='INFO')
    data = _read_registry(arm)
    def_count = sum(1 for b in arm.data.bones if _is_def_bone(b, stg.prefix_def))
    ctrl_count = len(data)
    layout.label(text=tr("stats.line") % (def_count, ctrl_count))


def _draw_preset_box(layout, stg):
    """Riga preset con pulsante di applicazione."""
    row = layout.row(align=True)
    row.prop(stg, "preset", text=tr("panel.preset"))
    row.operator("ctrl_def.apply_preset", text="", icon='CHECKMARK')


def _draw_settings(layout, stg):
    """Setup: prefissi dei bone e specchiatura L/R."""
    layout.prop(stg, "prefix_def", text=tr("panel.prefix_def"))
    layout.prop(stg, "prefix_ctrl", text=tr("panel.prefix_ctrl"))
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


def _draw_ik_box(layout):
    """Target IK rapido sui controller selezionati (Fase E)."""
    layout.label(text=tr("panel.ik"), icon='CONSTRAINT')
    layout.operator("ctrl_def.add_ik", text=tr("op.add_ik"), icon='CONSTRAINT')


def _draw_export_box(layout):
    """Export della mappa CTRL->DEF e preset utente su file."""
    layout.label(text=tr("panel.export"), icon='FILEBROWSER')
    layout.operator("ctrl_def.export_json", text=tr("op.export_json"), icon='EXPORT')
    layout.operator("ctrl_def.export_csv", text=tr("op.export_csv"), icon='EXPORT')
    layout.operator("ctrl_def.save_preset", text=tr("op.save_preset"), icon='FILE_TICK')
    layout.operator("ctrl_def.load_preset", text=tr("op.load_preset"), icon='FILEBROWSER')


def _draw_actions(layout):
    """Pulsanti delle operazioni principali (genera e vincola)."""
    layout.operator("ctrl_def.generate", text=tr("op.generate"), icon='BONE_DATA')
    layout.operator("ctrl_def.bind_actd", text=tr("op.bind_actd"), icon='CONSTRAINT_BONE')


def _draw_advanced_actions(layout):
    """Diagnostica e pulizia dei controller generati."""
    layout.operator("ctrl_def.diagnose", text=tr("op.diagnose"), icon='VIEWZOOM')
    layout.operator("ctrl_def.remove", text=tr("op.remove"), icon='TRASH')


def _draw_guide(layout):
    """Guida rapida in 5 passi, chiusa di default."""
    corpo = _section(layout, "sec.guide", chiusa=True)
    if corpo is not None:
        for passo in range(1, 6):
            corpo.label(text=tr("guide.%d" % passo))


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
        if arm is not None and arm.type != "ARMATURE":
            arm = None
        # 1 · Setup: stato, preset, prefissi e mirror (aperta)
        corpo = _section(layout, "sec.setup")
        if corpo is not None:
            if arm is not None:
                _draw_stats_box(corpo, arm, stg)
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
            _draw_ik_box(corpo)
            _draw_export_box(corpo)
            _draw_advanced_actions(corpo)
        # Guida rapida in fondo (chiusa)
        _draw_guide(layout)


