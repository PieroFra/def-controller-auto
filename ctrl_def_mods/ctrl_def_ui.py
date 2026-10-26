# MODULO ctrl_def_ui.py — pannello sidebar e helper di disegno (intestazione di build, non fa parte del monolite)
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


