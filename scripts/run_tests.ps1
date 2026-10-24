# scripts/run_tests.ps1 — runner pubblico per la suite CTRL_DEF (clone da GitHub).
# Esegue Blender headless con ambiente pulito (--factory-startup), carica e
# registra __init__.py dell'addon e lancia tutte le funzioni test_* di
# tests/test_ctrl_def.py.
# Uso:  .\scripts\run_tests.ps1 [-BlenderExe <percorso\blender.exe>]
# Exit: 0 se falliti==0, altrimenti 1.
param(
    [string]$BlenderExe = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Bootstrap = Join-Path $PSScriptRoot "run_ctrl_def_tests.py"
$LogFile = Join-Path $env:TEMP "ctrl_def_run_tests.log"

# Blender: percorso di default; se assente, cerca "blender" nel PATH
if (-not (Test-Path -LiteralPath $BlenderExe)) {
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        $BlenderExe = $cmd.Source
        Write-Host "[run_tests] Default non trovato, uso blender nel PATH: $BlenderExe"
    } else {
        Write-Host "[run_tests] ERRORE: blender.exe non trovato ('$BlenderExe' e nessun 'blender' nel PATH)."
        exit 1
    }
}

Write-Host "[run_tests] Blender: $BlenderExe"
Write-Host "[run_tests] Repository: $RepoRoot"
Write-Host "[run_tests] Log: $LogFile"

# --factory-startup: nessun addon utente caricato; "--" separa gli argomenti
# passati allo script Python (radice del repository)
$blenderArgs = @(
    "--background",
    "--factory-startup",
    "--python", $Bootstrap,
    "--python-exit-code", "1",
    "--", $RepoRoot
)

$output = & $BlenderExe @blenderArgs 2>&1 | Tee-Object -FilePath $LogFile
$blenderCode = $LASTEXITCODE

# Decodifica la riga RISULTATO stampata dal bootstrap Python
$passati = 0; $falliti = -1; $totale = 0; $trovato = $false
foreach ($line in $output) {
    $s = "$line"
    if ($s -match 'RISULTATO passati=(\d+) falliti=(\d+) totale=(\d+)') {
        $passati = [int]$Matches[1]; $falliti = [int]$Matches[2]; $totale = [int]$Matches[3]
        $trovato = $true
    }
}

if (-not $trovato) {
    Write-Host "[run_tests] ERRORE: riga RISULTATO assente (suite non eseguita). Log: $LogFile"
    Write-Host "VERDETTO: FAIL (nessun risultato)"
    exit 1
}

Write-Host "[run_tests] Exit code Blender: $blenderCode"
if ($falliti -eq 0) {
    Write-Host "VERDETTO: OK passati=$passati falliti=$falliti totale=$totale"
    exit 0
}
Write-Host "VERDETTO: FAIL passati=$passati falliti=$falliti totale=$totale"
exit 1
