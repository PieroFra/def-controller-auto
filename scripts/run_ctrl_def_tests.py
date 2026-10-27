# scripts/run_ctrl_def_tests.py — bootstrap headless per la suite CTRL_DEF.
# Eseguito da Blender tramite run_tests.ps1 / run_tests.sh:
#   carica e registra __init__.py dell'addon (single file), poi lancia
#   tutte le funzioni test_* di tests/test_ctrl_def.py.
# Stampa "RISULTATO passati=X falliti=Y totale=Z" ed esce con codice
# 0 se falliti==0, altrimenti 1.
# Uso: blender --background --factory-startup --python run_ctrl_def_tests.py -- <repo_root>
import importlib.util
import os
import sys


def _repo_root():
    # Radice del repository: primo argomento dopo "--", altrimenti il
    # genitore della cartella scripts/ (dove risiede questo file).
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv:
        return os.path.abspath(argv[0])
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    repo_root = _repo_root()
    tests_dir = os.path.join(repo_root, "tests")
    sys.path.insert(0, repo_root)
    sys.path.insert(0, tests_dir)

    addon_path = os.path.join(repo_root, "__init__.py")
    tests_path = os.path.join(tests_dir, "test_ctrl_def.py")

    if not (os.path.isfile(addon_path) and os.path.isfile(tests_path)):
        print("ERRORE: file attesi non trovati: {} / {}".format(addon_path, tests_path))
        return 1

    # Carica e registra l'addon prima dei test. La registrazione in
    # sys.modules DEVE avvenire PRIMA di exec_module: gli __init__.py dei
    # package multi-modulo e i test leggono "ctrl_def_addon" da sys.modules
    # durante l'esecuzione, altrimenti la suite fallisce con
    # ModuleNotFoundError quando l'addon viene caricato come singolo modulo.
    # Si carica come package reale: __init__.py usa solo import relativi e non
    # modifica sys.path (vietato dalla policy delle Blender Extensions), quindi
    # il percorso lo prepara questo runner.
    addon_spec = importlib.util.spec_from_file_location(
        "ctrl_def_addon", addon_path, submodule_search_locations=[repo_root])
    addon_mod = importlib.util.module_from_spec(addon_spec)
    sys.modules["ctrl_def_addon"] = addon_mod
    addon_spec.loader.exec_module(addon_mod)
    addon_mod.register()

    passati = 0
    falliti = 0
    try:
        spec = importlib.util.spec_from_file_location("test_ctrl_def", tests_path)
        tests = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tests)
        for name in sorted(dir(tests)):
            obj = getattr(tests, name)
            if callable(obj) and name.startswith("test_"):
                try:
                    obj()
                    print("PASS", name, flush=True)
                    passati += 1
                except Exception as exc:  # un test fallito non ferma la suite
                    print("FAIL", name, repr(exc), flush=True)
                    falliti += 1
    finally:
        try:
            addon_mod.unregister()
        except Exception as exc:
            print("WARN unregister:", repr(exc), flush=True)

    totale = passati + falliti
    print("RISULTATO passati={} falliti={} totale={}".format(passati, falliti, totale), flush=True)
    return 1 if falliti > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
