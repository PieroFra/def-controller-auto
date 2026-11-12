param(
    [string]$OutputDir = 'dist',
    [switch]$DryRun
)

# Packaging di rilascio di CTRL_DEF.
#
# Legge la versione da bl_info["version"] in __init__.py, verifica che coincida
# con version in blender_manifest.toml, mette in staging la struttura runtime
# ctrl_def/ (radice __init__.py + ctrl_def_mods\ + doc/meta) e produce in dist\:
#   - ctrl_def-<versione>.zip
#   - ctrl_def-<versione>.sha256     (formato sha256sum)
#   - ctrl_def-<versione>.files.txt  (file list confrontabile)
#
# Poi valida il pacchetto con Blender 5.2 locale, se presente:
#   1. blender --command extension validate
#   2. installazione del .zip in profilo isolato in %TEMP%, enable + assert
#      che la versione installata coincida, chiusura con CTRL_DEF_INSTALL_OK.
#
# Uscita attesa: righe "ZIP ...", "SHA256 ...", "G3 ..." e infine la riga
# finale "PACKAGE versione=... file=... py=... docs=...". Nessuna dipendenza
# esterna oltre a Blender gia' installato in locale.

$ErrorActionPreference = 'Stop'

# Zona oraria fissa sugli entry dello ZIP: stesso contenuto -> stesso SHA-256.
$ZipEpoch = [DateTimeOffset]::new(2000, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
$BlenderBin = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'

# Contratto di packaging: 10 .py (radice + ctrl_def_mods\) e 3 doc/meta.
$ExpectedPy = 10
$ExpectedDocs = 3
$IncludeDocs = @('blender_manifest.toml', 'LICENSE', 'README.md')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-ManifestVersion {
    param([string]$Path)

    $text = [IO.File]::ReadAllText($Path)
    # Primo match "version = ..." all'inizio riga: schema_version non matcha
    # perche' non inizia con "version".
    $m = [regex]::Match($text, '(?m)^\s*version\s*=\s*"(\d+\.\d+\.\d+)"')
    if (-not $m.Success) {
        throw "manifest.version non trovato in $Path (parsing testuale fallito)."
    }
    return $m.Groups[1].Value
}

function Get-BlInfoVersion {
    param([string]$Path)

    $text = [IO.File]::ReadAllText($Path)
    $m = [regex]::Match($text, '(?m)^\s*"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
    if (-not $m.Success) {
        throw "bl_info['version'] non trovato in $Path (parsing testuale fallito)."
    }
    return $m.Groups[1].Value + '.' + $m.Groups[2].Value + '.' + $m.Groups[3].Value
}

function Get-Sha256 {
    param([string]$Path)
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# ---------------------------------------------------------------------------
# 1. Radice e versione
# ---------------------------------------------------------------------------

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$initPath = Join-Path $root '__init__.py'
if (-not (Test-Path -LiteralPath $initPath)) { throw "Add-on non trovato: $initPath" }

$version = Get-BlInfoVersion -Path $initPath
$manifestVersion = Get-ManifestVersion -Path (Join-Path $root 'blender_manifest.toml')

if ($manifestVersion -ne $version) {
    throw ("Versione incoerente: bl_info {0} != manifest {1}" -f $version, $manifestVersion)
}

$missingDocs = @()
foreach ($doc in $IncludeDocs) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $doc))) { $missingDocs += $doc }
}
if ($missingDocs.Count -gt 0) {
    throw ('Documenti richiesti assenti: ' + ($missingDocs -join ', '))
}

# ---------------------------------------------------------------------------
# 2. Selezione dei file: solo .py di radice e ctrl_def_mods\ + i doc/meta
# ---------------------------------------------------------------------------

$selected = New-Object System.Collections.Generic.List[object]
foreach ($dir in @('.', 'ctrl_def_mods')) {
    $absDir = if ($dir -eq '.') { $root } else { Join-Path $root ($dir -replace '/', '\') }
    if (-not (Test-Path -LiteralPath $absDir)) { throw "Directory runtime assente: $absDir" }
    foreach ($f in (Get-ChildItem -LiteralPath $absDir -Filter '*.py' -File)) {
        $rel = if ($dir -eq '.') { $f.Name } else { "$dir/$($f.Name)" }
        $selected.Add([pscustomobject]@{ Rel = $rel; Full = $f.FullName })
    }
}
foreach ($doc in $IncludeDocs) {
    $selected.Add([pscustomobject]@{ Rel = $doc; Full = (Join-Path $root $doc) })
}
$selected = @($selected | Sort-Object -Property Rel -Unique)

$pyCount = @($selected | Where-Object { $_.Rel -like '*.py' }).Count
$docCount = @($selected | Where-Object { $_.Rel -notlike '*.py' }).Count
if ($pyCount -ne $ExpectedPy) {
    throw ("Conteggio .py inatteso: $pyCount != $ExpectedPy (c'e' un file nuovo da gestire?)")
}
if ($docCount -ne $ExpectedDocs) {
    throw ("Conteggio doc/meta inatteso: $docCount != $ExpectedDocs")
}
foreach ($required in @('__init__.py', 'ctrl_def_mods/__init__.py')) {
    if (-not ($selected | Where-Object { $_.Rel -eq $required })) {
        throw "File runtime richiesto assente: $required"
    }
}

# ---------------------------------------------------------------------------
# 3. Staging in ctrl_def/
# ---------------------------------------------------------------------------

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stagingRoot = Join-Path ([IO.Path]::GetTempPath()) ("opencode\ctrl_def_pkg\{0}_{1}" -f $stamp, [guid]::NewGuid().ToString('N').Substring(0, 8))
$pkgDir = Join-Path $stagingRoot 'ctrl_def'

try {
    New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null

    foreach ($f in $selected) {
        $parts = $f.Rel -split '/'
        $destDir = $pkgDir
        for ($i = 0; $i -lt ($parts.Count - 1); $i++) {
            $destDir = Join-Path $destDir $parts[$i]
        }
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $f.Full -Destination (Join-Path $destDir $parts[$parts.Count - 1]) -Force
    }

    if (-not (Test-Path -LiteralPath (Join-Path $pkgDir 'blender_manifest.toml'))) {
        throw 'Staging non valido: blender_manifest.toml non e alla radice di ctrl_def/.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $pkgDir '__init__.py'))) {
        throw 'Staging non valido: __init__.py non e alla radice di ctrl_def/.'
    }

    $staged = @(Get-ChildItem -LiteralPath $pkgDir -Recurse -File | ForEach-Object {
        [pscustomobject]@{
            Rel  = $_.FullName.Substring($pkgDir.Length + 1).Replace('\', '/')
            Full = $_.FullName
        }
    } | Sort-Object -Property Rel)

    # Nessun file di sviluppo dentro lo staging: niente di fuori radice/ctrl_def_mods.
    $leaks = @($staged | Where-Object {
        $_.Rel -match '^(tests|docs|\.git|\.github|\.opencode|__pycache__|dist|_esperimenti|scripts)/' -or
        $_.Rel -in @('AGENTS.md', 'CHANGELOG.md', 'README.it.md', 'opencode.json', '.gitignore') -or
        $_.Rel -match '\.(pyc|pyo|log|txt|ps1|png|jpg|gif|blend|blend1|zip)$'
    } | ForEach-Object { $_.Rel })
    if ($leaks.Count -gt 0) {
        throw ('Esclusione violata, file di sviluppo nello staging: ' + ($leaks -join ', '))
    }

    # -----------------------------------------------------------------------
    # 4. File list
    # -----------------------------------------------------------------------

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# ctrl_def $version - release file list")
    $lines.Add("# bl_info version $version | manifest.version $manifestVersion")
    $lines.Add("# generated $((Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')) deterministic build")
    $lines.Add("# files $($staged.Count) (py $pyCount, docs $docCount)")
    $lines.Add("# columns: sha256  bytes  relative-path")

    foreach ($s in $staged) {
        $hash = Get-Sha256 -Path $s.Full
        $size = (Get-Item -LiteralPath $s.Full).Length
        $lines.Add(('{0}  {1}  {2}' -f $hash, $size, $s.Rel))
    }

    # -----------------------------------------------------------------------
    # 5. ZIP deterministico (timestamp fisso, slash Unix, prefisso ctrl_def/)
    # -----------------------------------------------------------------------

    Add-Type -AssemblyName System.IO.Compression | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null

    $targetDir = if ($DryRun) { $stagingRoot } else {
        if ([IO.Path]::IsPathRooted($OutputDir)) { $OutputDir } else { Join-Path $root $OutputDir }
    }
    if (-not (Test-Path -LiteralPath $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    $zipName = "ctrl_def-$version.zip"
    $zipPath = Join-Path $targetDir $zipName
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

    $fs = [IO.File]::Open($zipPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try {
        $zip = [System.IO.Compression.ZipArchive]::new(
            $fs, [System.IO.Compression.ZipArchiveMode]::Create, $true, [System.Text.Encoding]::UTF8)
        try {
            foreach ($s in $staged) {
                $entry = $zip.CreateEntry(
                    ('ctrl_def/' + $s.Rel), [System.IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = $ZipEpoch.DateTime
                $outStream = $entry.Open()
                $inStream = [IO.File]::OpenRead($s.Full)
                try { $inStream.CopyTo($outStream) }
                finally { $inStream.Dispose(); $outStream.Dispose() }
            }
        }
        finally { $zip.Dispose() }
    }
    finally { $fs.Dispose() }

    # -----------------------------------------------------------------------
    # 6. Checksum e file list su disco
    # -----------------------------------------------------------------------

    $zipHash = Get-Sha256 -Path $zipPath
    $shaPath = Join-Path $targetDir ("ctrl_def-$version.sha256")
    $listPath = Join-Path $targetDir ("ctrl_def-$version.files.txt")

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($shaPath, ("{0}  {1}`n" -f $zipHash, $zipName), $utf8)
    [IO.File]::WriteAllLines($listPath, $lines.ToArray(), $utf8)

    # -----------------------------------------------------------------------
    # 7. Verifica su Blender 5.2 locale (validate + installazione profilo isolato)
    # -----------------------------------------------------------------------

    $g3Message = 'SKIP blender non presente: ' + $BlenderBin
    if (Test-Path -LiteralPath $BlenderBin) {
        # Profilo Blender isolato in %TEMP%: niente tocchi alla config utente.
        $isoRoot = Join-Path ([IO.Path]::GetTempPath()) ("opencode\ctrl_def_g3\{0}_{1}" -f $stamp, [guid]::NewGuid().ToString('N').Substring(0, 8))
        New-Item -ItemType Directory -Path $isoRoot -Force | Out-Null
        $isoArgs = @('--factory-startup', '-b', '-noaudio')
        # Profilo isolato via variabile d'ambiente (Blender non ha --user-config).
        $prevEnv = $env:BLENDER_USER_CONFIG
        $env:BLENDER_USER_CONFIG = $isoRoot

        try {
            # 1) Validazione del pacchetto.
            $valLines = & $BlenderBin @isoArgs --command extension validate $zipPath 2>&1 | ForEach-Object { $_.ToString() }
            $valCode = $LASTEXITCODE
            if ($null -eq $valCode) { $valCode = -1 }
            Write-Output ("G3_VALIDATE exit={0}" -f $valCode)
            $valLines | Where-Object { $_ } | Select-Object -Last 3 | ForEach-Object { Write-Output ("G3_VALIDATE | " + $_) }

            # 2) Installazione vera del .zip, enable e assert su versione montata.
            $expr = (
                "import bpy, addon_utils; " +
                "r = bpy.ops.preferences.addon_install(overwrite=True, filepath=r'$zipPath'); " +
                "assert r == {'FINISHED'}, r; " +
                "addon_utils.enable('ctrl_def', default_set=True, persistent=True); " +
                "assert 'ctrl_def' in bpy.context.preferences.addons, 'add-on non montato'; " +
                "mod = __import__('sys').modules.get('ctrl_def'); " +
                "v = mod.bl_info['version']; " +
                "assert v == ($($version -replace '\.', ', ')), 'versione installata %s != %s' % (v, mod.bl_info['version']); " +
                "print('CTRL_DEF_INSTALL_OK')"
            )
            $instLines = & $BlenderBin @isoArgs --python-expr $expr 2>&1 | ForEach-Object { $_.ToString() }
            $instCode = $LASTEXITCODE
            if ($null -eq $instCode) { $instCode = -1 }
            if ($instCode -ne 0 -or -not ($instLines | Where-Object { $_.Trim() -eq 'CTRL_DEF_INSTALL_OK' })) {
                throw ("Installazione G3 fallita su Blender 5.2 locale (exit=$instCode): " + (($instLines | Select-Object -Last 5) -join ' | '))
            }
            $g3Message = 'OK (validate exit=' + $valCode + ', install exit=' + $instCode + ')'
        }
        finally {
            $env:BLENDER_USER_CONFIG = $prevEnv
            if (Test-Path -LiteralPath $isoRoot) { Remove-Item -LiteralPath $isoRoot -Recurse -Force }
        }
    }
    Write-Output ("CTRL_DEF_INSTALL_OK {0}" -f $g3Message)

    # -----------------------------------------------------------------------
    # 8. Report finale
    # -----------------------------------------------------------------------

    Write-Output ("ZIP {0}" -f $zipPath)
    Write-Output ("SHA256 {0}" -f $zipHash)
    Write-Output ("CHECKSUM {0}" -f $shaPath)
    Write-Output ("FILELIST {0}" -f $listPath)
    Write-Output ("STAGING {0}" -f $stagingRoot)
    if ($DryRun) { Write-Output 'MODALITA dry-run: dist\ non e stato toccato.' }
    Write-Output ("PACKAGE versione={0} file={1} py={2} docs={3}" -f $version, $staged.Count, $pyCount, $docCount)
}
finally {
    if ((-not $DryRun) -and (Test-Path -LiteralPath $stagingRoot)) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

exit 0
