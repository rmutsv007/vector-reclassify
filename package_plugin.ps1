param(
    [string]$PluginFolderName = "VectorReclassify",
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$metadataPath = Join-Path $projectRoot "metadata.txt"

if (-not (Test-Path $metadataPath)) {
    throw "metadata.txt was not found in $projectRoot"
}

$versionLine = Select-String -Path $metadataPath -Pattern '^version=' | Select-Object -First 1
if (-not $versionLine) {
    throw "version was not found in metadata.txt"
}

$version = ($versionLine.Line -replace '^version=', '').Trim()
$stagingRoot = Join-Path $projectRoot ".package-build"
$outputRoot = Join-Path $projectRoot $OutputDirectory
$pluginStagingDir = Join-Path $stagingRoot $PluginFolderName
$legacyStagingDir = Join-Path $outputRoot $PluginFolderName
$zipPath = Join-Path $outputRoot ("{0}-{1}.zip" -f $PluginFolderName, $version)

if (Test-Path $stagingRoot) {
    Remove-Item $stagingRoot -Recurse -Force
}
if (Test-Path $legacyStagingDir) {
    Remove-Item $legacyStagingDir -Recurse -Force
}

New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
New-Item -ItemType Directory -Path $pluginStagingDir -Force | Out-Null

$includeFiles = @(
    "__init__.py",
    "LICENSE",
    "metadata.txt",
    "README.md",
    "CHANGELOG.md",
    "icon.png",
    "reclassifier.py",
    "vector_reclassify_dialog.py",
    "vector_reclassify_plugin.py"
)

foreach ($file in $includeFiles) {
    $source = Join-Path $projectRoot $file
    if (-not (Test-Path $source)) {
        throw "Required file missing: $file"
    }
    Copy-Item -Path $source -Destination (Join-Path $pluginStagingDir $file) -Force
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

$zipFileStream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
try {
    $zipArchive = New-Object System.IO.Compression.ZipArchive($zipFileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        foreach ($file in $includeFiles) {
            $sourcePath = Join-Path $pluginStagingDir $file
            $entryName = ($PluginFolderName + "/" + $file) -replace "\\", "/"
            $entry = $zipArchive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
            $entryStream = $entry.Open()
            try {
                $sourceStream = [System.IO.File]::OpenRead($sourcePath)
                try {
                    $sourceStream.CopyTo($entryStream)
                }
                finally {
                    $sourceStream.Dispose()
                }
            }
            finally {
                $entryStream.Dispose()
            }
        }
    }
    finally {
        $zipArchive.Dispose()
    }
}
finally {
    $zipFileStream.Dispose()
}

Remove-Item $stagingRoot -Recurse -Force

Write-Output "Created package: $zipPath"