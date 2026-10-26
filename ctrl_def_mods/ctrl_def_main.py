# MODULO ctrl_def_main.py — registrazione delle classi e blocco di avvio (intestazione di build, non fa parte del monolite)
# ===========================================================================
# Registrazione
# ===========================================================================
_classes = [
    CTRLDEF_PG_settings,
    CTRLDEF_OT_apply_preset,
    CTRLDEF_OT_generate,
    CTRLDEF_OT_bind_actd,
    CTRLDEF_OT_remove,
    CTRLDEF_PT_panel,
]


def _register_class_safe(cls):
    """Registra una classe ignorando i doppi registri (reload dell'addon)."""
    if getattr(cls, "is_registered", False):
        return
    try:
        bpy.utils.register_class(cls)
    except ValueError as exc:
        if "already registered" not in str(exc):
            raise


def _unregister_class_safe(cls):
    """Annulla la registrazione di una classe ignorando quelle gia' assenti."""
    try:
        bpy.utils.unregister_class(cls)
    except (RuntimeError, ValueError):
        pass


def register():
    for cls in _classes:
        _register_class_safe(cls)
    if not hasattr(bpy.types.Scene, "ctrl_def_settings"):
        bpy.types.Scene.ctrl_def_settings = PointerProperty(type=CTRLDEF_PG_settings)


def unregister():
    if hasattr(bpy.types.Scene, "ctrl_def_settings"):
        del bpy.types.Scene.ctrl_def_settings
    for cls in reversed(_classes):
        _unregister_class_safe(cls)


if __name__ == "__main__":
    register()
