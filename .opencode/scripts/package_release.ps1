# package_release.ps1 - packaging release CTRL_DEF (edizione nativa Blender Extensions).
# Legge la versione da bl_info (__init__.py) e da blender_manifest.toml, verifica la
# coincidenza, costruisce lo ZIP dall'albero sorgente e ne verifica l'integrita'.
# Output: dist\ctrl_def-<versione>.zip + .sha256 + .files.txt
# Riga finale: PACKAGE_OK | zip=<path> | sha256=<hash> | files=<N>  oppure  PACKAGE_FAIL | reason=...
# Nessuna scrittura fuori da dist\: usare dalla radice del progetto.
# Attenzione: PowerShell 5.1 non ha Compress-Archive con leak di percorsi assoluti;
# si usa System.IO.Compression.ZipFile per controllare nomi e radice.

param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath)))
)

$ErrorActionPreference = 'Stop'
Set-Location $ProjectRoot

function Fail([string]$reason) {
    Write-Output "PACKAGE_FAIL | reason=$reason"
    exit 1
}

# --- 1) Versioni: bl_info vs blender_manifest.toml ----------------------------
$initPath = Join-Path $ProjectRoot '__init__.py'
$manifestPath = Join-Path $ProjectRoot 'blender_manifest.toml'
if (-not (Test-Path $initPath)) { Fail 'init_missing' }
if (-not (Test-Path $manifestPath)) { Fail 'manifest_missing' }

$initText = Get-Content $initPath -Raw
if ($initText -match '"version"\s*:\s*\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)') {
    $blInfoVersion = "{0}.{1}.{2}" -f $Matches[1], $Matches[2], $Matches[3]
} else { Fail 'bl_info_version_not_found' }

$manifestText = Get-Content $manifestPath -Raw
if ($manifestText -match '(?m)^\s*version\s*=\s*"([^"]+)"') {
    $manifestVersion = $Matches[1]
} else { Fail 'manifest_version_not_found' }

if ($blInfoVersion -ne $manifestVersion) {
    Fail "version_mismatch bl_info=$blInfoVersion manifest=$manifestVersion"
}
$version = $blInfoVersion
Write-Output "versione=$version (bl_info e manifest coincidono)"

# --- 2) Costruzione fileset dall'albero sorgente ------------------------------
$include = @('__init__.py', 'blender_manifest.toml', 'README.md', 'README.it.md', 'LICENSE')
$excludeDirs = @('.git', '_esperimenti', 'tests', '.opencode', 'dist', '__pycache__', '.github', 'scripts', 'docs')

$files = New-Object System.Collections.Generic.List[string]
foreach ($item in $include) {
    if (Test-Path (Join-Path $ProjectRoot $item)) { $files.Add($item) }
}
# Moduli: tutti i .py di ctrl_def_mods (esclusi __pycache__ e .pyc)
$modsDir = Join-Path $ProjectRoot 'ctrl_def_mods'
if (-not (Test-Path $modsDir)) { Fail 'ctrl_def_mods_missing' }
foreach ($py in (Get-ChildItem $modsDir -Filter '*.py' -File)) { $files.Add("ctrl_def_mods\$($py.Name)") }

if (-not ($files -contains '__init__.py')) { Fail 'init_not_in_fileset' }
Write-Output "file da impacchettare: $($files.Count)"

# --- 3) ZIP in dist\ ----------------------------------------------------------
$distDir = Join-Path $ProjectRoot 'dist'
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$zipPath = Join-Path $distDir "ctrl_def-$version.zip"
$shaPath = Join-Path $distDir "ctrl_def-$version.sha256"
$filesPath = Join-Path $distDir "ctrl_def-$version.files.txt"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, 'Create')
try {
    foreach ($rel in $files) {
        $src = Join-Path $ProjectRoot $rel
        $entryName = $rel -replace '\\', '/'
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $src, $entryName) | Out-Null
    }
} finally { $zip.Dispose() }

# --- 4) Verifica integrita' reale dello ZIP -----------------------------------
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $names = $zip.Entries | ForEach-Object { $_.FullName }
    $dupes = $names | Group-Object | Where-Object { $_.Count -gt 1 }
    if ($dupes) { Fail ("zip_duplicate_names: " + (($dupes | ForEach-Object { $_.Name }) -join ', ')) }

    $rootInit = $zip.Entries | Where-Object { $_.FullName -eq '__init__.py' }
    if (-not $rootInit) { Fail 'zip_init_missing_at_root' }
    $reader = New-Object System.IO.StreamReader($rootInit.Open())
    $initContent = $reader.ReadToEnd()
    $reader.Close()
    if ($initContent -notmatch 'bl_info') { Fail 'zip_init_no_bl_info' }
    if ($initContent -notmatch '\bregister\b') { Fail 'zip_init_no_register' }

    $modsEntries = $zip.Entries | Where-Object { $_.FullName -like 'ctrl_def_mods/*.py' }
    if (-not $modsEntries -or @($modsEntries).Count -lt 1) { Fail 'zip_ctrl_def_mods_missing' }

    $fileCount = @($zip.Entries).Count
} finally { $zip.Dispose() }

$hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText($shaPath, $hash, (New-Object System.Text.UTF8Encoding($false)))
$lines = @()
foreach ($rel in $files) { $lines += ($rel -replace '\\', '/') }
[System.IO.File]::WriteAllLines($filesPath, $lines, (New-Object System.Text.UTF8Encoding($false)))

# --- 5) Esito ------------------------------------------------------------------
Write-Output "PACKAGE_OK | zip=$zipPath | sha256=$hash | files=$fileCount"
