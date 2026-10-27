# CTRL_DEF — entry point installabile: bl_info e riesporta i simboli dei moduli.
bl_info = {
    "name": "DEF Controller Auto",
    "author": "Pierfrancesco Diodato",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > DEF Ctrl",
    "description": "Genera controller per bone DEF, tracciati e rimovibili",
    "category": "Rigging",
}

# In Blender l'addon e' sempre un package (estensione o cartella in addons/):
# l'unico caricamento previsto e' questo, con import relativi. Nessuna
# modifica al percorso di import: vietata dalle Blender Extensions, e la
# preparazione del percorso spetta ai test (tests/test_ctrl_def.py).
if __package__:
    from .ctrl_def_mods.ctrl_def_i18n import _I18N, tr
    from .ctrl_def_mods.ctrl_def_registry import (
        REGISTRY_KEY, _armature_of, _forget_generated, _is_generated,
        _mark_generated, _prune_registry, _read_registry, _write_registry)
    from .ctrl_def_mods.ctrl_def_shapes import (
        _bonewidget_available, _bonewidget_create, _is_def_bone, _mirror_name,
        _side_of)
    from .ctrl_def_mods.ctrl_def_properties import (
        _ITEMS_CACHE, CTRLDEF_PG_settings, _items_parent, _items_preset,
        _on_preset_update)
    from .ctrl_def_mods.ctrl_def_generation import (
        CTRLDEF_OT_generate, _assign_ctrl_parents, _collect_def_bones,
        _configure_ctrl_pose_bones, _create_ctrl_edit_bones)
    from .ctrl_def_mods.ctrl_def_operators import (
        _PRESETS, CTRLDEF_OT_add_ik, CTRLDEF_OT_apply_preset,
        CTRLDEF_OT_bind_actd,
        CTRLDEF_OT_create_widget,
        CTRLDEF_OT_diagnose, CTRLDEF_OT_export_csv, CTRLDEF_OT_export_json,
        CTRLDEF_OT_load_preset, CTRLDEF_OT_remove, CTRLDEF_OT_save_preset,
        _add_ik_target_chain, _apply_native_bindings, _apply_preset_values,
        _configure_actd_settings, _count_actd_bindings_for_arm,
        _diagnose_def_selection, _ensure_armature_mode, _export_rows,
        _purge_unused_shapes, _remove_registered_bones, _selected_ctrl_chains)
    from .ctrl_def_mods.ctrl_def_ui import (
        CTRLDEF_PT_panel, _draw_actions, _draw_advanced_actions,
        _draw_controller_settings, _draw_guide, _draw_preset_box,
        _draw_settings, _draw_stats_box, _draw_widget_box, _section)
    from .ctrl_def_mods.ctrl_def_main import (
        _classes, _register_class_safe, _unregister_class_safe, register,
        unregister)
