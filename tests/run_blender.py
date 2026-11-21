import sys, os
# L'addon non modifica sys.path (policy Blender Extensions): la radice del repo
# e la cartella dei test le aggiunge il runner, prima di ogni import.
sys.path.append(r"C:\Users\checc\Desktop\BLENDER ADDONS\CTRL_DEF")
sys.path.append(os.path.dirname(r"C:\Users\checc\Desktop\BLENDER ADDONS\CTRL_DEF\tests\test_ctrl_def.py"))
import importlib.util

# Carica e registra l'addon (entry point multi-modulo) prima di eseguire i test
addon_path = os.path.join(r"C:\Users\checc\Desktop\BLENDER ADDONS\CTRL_DEF", "__init__.py")
# Caricamento come package: senza submodule_search_locations __init__.py prende
# il ramo degli import relativi e fallisce con ModuleNotFoundError 'ctrl_def_addon'.
addon_spec = importlib.util.spec_from_file_location(
    "ctrl_def_addon", addon_path,
    submodule_search_locations=[os.path.dirname(addon_path)])
mod = importlib.util.module_from_spec(addon_spec)
# Necessario: i sottoimport relativi (from .ctrl_def_mods...) cercano prima il
# genitore "ctrl_def_addon" in sys.modules; senza registrazione va su sys.path
# e fallisce con ModuleNotFoundError.
sys.modules["ctrl_def_addon"] = mod
addon_spec.loader.exec_module(mod)
mod.register()

passati = 0
falliti = 0
try:
    spec = importlib.util.spec_from_file_location("test_ctrl_def", r"C:\Users\checc\Desktop\BLENDER ADDONS\CTRL_DEF\tests\test_ctrl_def.py")
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    suites = [s.strip().lower() for s in os.environ.get("CTRLDEF_SUITES", "").split(",") if s.strip()]
    for name in sorted(dir(tests)):
        obj = getattr(tests, name)
        if callable(obj) and name.startswith("test_"):
            if suites and not any(s in name.lower() for s in suites):
                continue
            try:
                obj()
                print("PASS", name)
                passati += 1
            except Exception as e:
                print("FAIL", name, repr(e))
                falliti += 1
finally:
    try:
        mod.unregister()
    except Exception as e:
        print("WARN unregister:", repr(e))

print("RISULTATO passati={} falliti={} totale={}".format(passati, falliti, passati + falliti))
sys.exit(1 if falliti > 0 else 0)