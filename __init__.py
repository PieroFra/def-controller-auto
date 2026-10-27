# CTRL_DEF — entry point installabile: bl_info e riesporta i simboli dei moduli.
import os
import sys

bl_info = {
    "name": "DEF Controller Auto",
    "author": "Pierfrancesco Diodato",
    "version": (0, 1, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > DEF Ctrl",
    "description": "Genera controller per bone DEF, tracciati e rimovibili",
    "category": "Rigging",
}

# Nei test l'addon e' caricato con spec_from_file_location: senza package la
# sua directory deve stare in sys.path per importare ctrl_def_mods.
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

# Package reale (Blender) -> import relativo; __package__ vuoto nei test ->
# import assoluto del package locale ctrl_def_mods.
if __package__:
    from .ctrl_def_mods.ctrl_def_i18n import _I18N, tr
    from .ctrl_def_mods.ctrl_def_registry import (
        REGISTRY_KEY, _armature_of, _forget_generated, _is_generated,
        _mark_generated, _prune_registry, _read_registry, _write_registry)
    from .ctrl_def_mods.ctrl_def_shapes import (
        _create_shape_object, _ensure_collection, _get_or_create_shape,
        _is_def_bone, _make_arrow, _make_circle, _make_cross, _make_cube,
        _make_sphere, _mirror_name, _shape_geometry, _side_of)
    from .ctrl_def_mods.ctrl_def_properties import (
        CTRLDEF_PG_settings, _items_color, _items_parent, _items_preset,
        _items_shape)
    from .ctrl_def_mods.ctrl_def_generation import (
        CTRLDEF_OT_generate, _assign_ctrl_parents, _collect_def_bones,
        _configure_ctrl_pose_bones, _create_ctrl_edit_bones)
    from .ctrl_def_mods.ctrl_def_operators import (
        _PRESETS, CTRLDEF_OT_apply_preset, CTRLDEF_OT_bind_actd,
        CTRLDEF_OT_diagnose, CTRLDEF_OT_export_csv, CTRLDEF_OT_export_json,
        CTRLDEF_OT_load_preset, CTRLDEF_OT_remove, CTRLDEF_OT_save_preset,
        _apply_native_bindings, _apply_preset_values,
        _configure_actd_settings, _count_actd_bindings_for_arm,
        _diagnose_def_selection, _ensure_armature_mode, _export_rows,
        _purge_unused_shapes, _remove_registered_bones)
    from .ctrl_def_mods.ctrl_def_ui import (
        CTRLDEF_PT_panel, _draw_actions, _draw_preset_box, _draw_settings,
        _draw_stats_box)
    from .ctrl_def_mods.ctrl_def_main import (
        _classes, _register_class_safe, _unregister_class_safe, register,
        unregister)
else:
    from ctrl_def_mods.ctrl_def_i18n import _I18N, tr
    from ctrl_def_mods.ctrl_def_registry import (
        REGISTRY_KEY, _armature_of, _forget_generated, _is_generated,
        _mark_generated, _prune_registry, _read_registry, _write_registry)
    from ctrl_def_mods.ctrl_def_shapes import (
        _create_shape_object, _ensure_collection, _get_or_create_shape,
        _is_def_bone, _make_arrow, _make_circle, _make_cross, _make_cube,
        _make_sphere, _mirror_name, _shape_geometry, _side_of)
    from ctrl_def_mods.ctrl_def_properties import (
        CTRLDEF_PG_settings, _items_color, _items_parent, _items_preset,
        _items_shape)
    from ctrl_def_mods.ctrl_def_generation import (
        CTRLDEF_OT_generate, _assign_ctrl_parents, _collect_def_bones,
        _configure_ctrl_pose_bones, _create_ctrl_edit_bones)
    from ctrl_def_mods.ctrl_def_operators import (
        _PRESETS, CTRLDEF_OT_apply_preset, CTRLDEF_OT_bind_actd,
        CTRLDEF_OT_diagnose, CTRLDEF_OT_export_csv, CTRLDEF_OT_export_json,
        CTRLDEF_OT_load_preset, CTRLDEF_OT_remove, CTRLDEF_OT_save_preset,
        _apply_native_bindings, _apply_preset_values,
        _configure_actd_settings, _count_actd_bindings_for_arm,
        _diagnose_def_selection, _ensure_armature_mode, _export_rows,
        _purge_unused_shapes, _remove_registered_bones)
    from ctrl_def_mods.ctrl_def_ui import (
        CTRLDEF_PT_panel, _draw_actions, _draw_preset_box, _draw_settings,
        _draw_stats_box)
    from ctrl_def_mods.ctrl_def_main import (
        _classes, _register_class_safe, _unregister_class_safe, register,
        unregister)
