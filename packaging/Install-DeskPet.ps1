$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $PackageRoot "app"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\DeskPetPanel"
$Exe = Join-Path $InstallDir "DeskPetPanel.exe"

if (-not (Test-Path -LiteralPath (Join-Path $Source "DeskPetPanel.exe"))) {
    throw "The app payload is incomplete. Extract the whole ZIP first."
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path (Join-Path $Source "*") -Destination $InstallDir -Recurse -Force

$Shell = New-Object -ComObject WScript.Shell
$DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "桌宠工作面板.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "桌宠工作面板"
New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null

foreach ($Link in @($DesktopLink, (Join-Path $StartMenuDir "桌宠工作面板.lnk"))) {
    $Shortcut = $Shell.CreateShortcut($Link)
    $Shortcut.TargetPath = $Exe
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = "$Exe,0"
    $Shortcut.Description = "桌宠工作面板"
    $Shortcut.Save()
}

$UninstallLink = $Shell.CreateShortcut((Join-Path $StartMenuDir "卸载桌宠工作面板.lnk"))
$UninstallLink.TargetPath = "powershell.exe"
$UninstallLink.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $InstallDir "Uninstall-DeskPet.ps1") + '"'
$UninstallLink.WorkingDirectory = $InstallDir
$UninstallLink.IconLocation = "$Exe,0"
$UninstallLink.Save()

Start-Process -FilePath $Exe
Write-Host "Installed: $InstallDir"
