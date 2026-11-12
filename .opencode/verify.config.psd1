@{
    # Add-on con architettura Moduli + Build Step: i moduli in ctrl_def_mods\ sono la fonte,
    # __init__.py e' il monolite installabile generato da scripts\build_monolith.py.
    Monolith      = '__init__.py'
    Sources       = @('ctrl_def_mods')
    Build         = 'scripts\build_monolith.py'
    Runner        = '.opencode\scripts\run_tests.ps1'
    RunnerArgs    = @()
    ExpectedTotal = 6
    DiffPaths     = @('__init__.py', 'ctrl_def_mods')
    IndexOutput   = '.opencode\INDEX.md'
}
