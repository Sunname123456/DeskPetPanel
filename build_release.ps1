param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

if (-not $PythonExe) {
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) {
        $PythonExe = $candidate.Source
    } else {
        $PythonExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python39\python.exe"
    }
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python 3.9+ x64 was not found. Pass -PythonExe with its full path."
}

$PythonInfo = (& $PythonExe -c "import json, platform, sys; print(json.dumps({'major': sys.version_info.major, 'minor': sys.version_info.minor, 'arch': platform.architecture()[0], 'version': platform.python_version()}))") | ConvertFrom-Json
if ($PythonInfo.major -ne 3 -or $PythonInfo.minor -lt 9 -or $PythonInfo.arch -ne "64bit") {
    throw "Python 3.9+ x64 is required; found $($PythonInfo.version) $($PythonInfo.arch)."
}
Write-Host "Build interpreter: Python $($PythonInfo.version) $($PythonInfo.arch)"

$Venv = Join-Path $Root ".venv-release"
if (-not (Test-Path -LiteralPath (Join-Path $Venv "Scripts\python.exe"))) {
    & $PythonExe -m venv $Venv
}
$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $Root "requirements-build.txt")

& $Py -m PyInstaller `
    --noconfirm `
    --clean `
    --noupx `
    --windowed `
    --onedir `
    --name DeskPetPanel `
    --icon (Join-Path $Root "app.ico") `
    --version-file (Join-Path $Root "packaging\version_info.txt") `
    --add-data "web;web" `
    --hidden-import PyQt6.QtWebEngineCore `
    --hidden-import PyQt6.QtWebEngineWidgets `
    --hidden-import PyQt6.QtMultimedia `
    --hidden-import PyQt6.QtMultimediaWidgets `
    (Join-Path $Root "panel.py")

$Exe = Join-Path $Root "dist\DeskPetPanel\DeskPetPanel.exe"
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Build finished without the expected executable."
}
Write-Host "Build ready: $Exe"
