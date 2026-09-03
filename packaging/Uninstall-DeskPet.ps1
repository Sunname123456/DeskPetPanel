$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$InstallDir = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs\DeskPetPanel"))
$ExpectedRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs"))
if (-not $InstallDir.StartsWith($ExpectedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected install path: $InstallDir"
}
$Exe = Join-Path $InstallDir "DeskPetPanel.exe"

Get-Process -Name "DeskPetPanel" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and ([IO.Path]::GetFullPath($_.Path) -eq $Exe) } |
    Stop-Process -Force -ErrorAction SilentlyContinue

$Config = Join-Path $env:USERPROFILE ".workspace_panel\config.json"
if (Test-Path -LiteralPath $Config) {
    try {
        $Data = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($Entry in @($Data.entries)) {
            if ($Entry.hidden_by_us -and $Entry.path -and (Test-Path -LiteralPath $Entry.path)) {
                $Item = Get-Item -LiteralPath $Entry.path -Force
                $Item.Attributes = $Item.Attributes -band (-bnot [IO.FileAttributes]::Hidden)
                $Entry.hidden_by_us = $false
            }
        }
        $Json = $Data | ConvertTo-Json -Depth 8
        [IO.File]::WriteAllText($Config, $Json, (New-Object Text.UTF8Encoding($false)))
    } catch {
        Write-Warning "Desktop-item restoration needs manual review: $($_.Exception.Message)"
    }
}

Remove-ItemProperty -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WorkspacePanel" -ErrorAction SilentlyContinue
foreach ($ShortcutName in @("流萤桌宠工作面板.lnk", "桌宠工作面板.lnk")) {
    Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Desktop")) $ShortcutName) -Force -ErrorAction SilentlyContinue
}
foreach ($MenuName in @("流萤桌宠工作面板", "桌宠工作面板")) {
    Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Programs")) $MenuName) -Recurse -Force -ErrorAction SilentlyContinue
}

$Quoted = $InstallDir.Replace("'", "''")
$Cleanup = "Start-Sleep -Seconds 2; if (Test-Path -LiteralPath '$Quoted') { Remove-Item -LiteralPath '$Quoted' -Recurse -Force }"
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-WindowStyle", "Hidden", "-Command", $Cleanup) -WindowStyle Hidden
Write-Host "Uninstalled. User settings remain at: $env:USERPROFILE\.workspace_panel"
