$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
if (-not (Test-Path (Join-Path $source 'UsageGarden.exe'))) {
    Write-Host 'Run this installer from the extracted Windows app download, beside UsageGarden.exe.'
    exit 1
}
$destination = Join-Path $env:LOCALAPPDATA 'Programs\UsageGarden'
$executable = Join-Path $destination 'UsageGarden.exe'
$running = Get-Process UsageGarden -ErrorAction SilentlyContinue
if ($running) { Write-Host 'Please close Usage Garden, then run this installer again.'; exit 1 }
New-Item -ItemType Directory -Path $destination -Force | Out-Null
if ([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($destination)) {
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destination -Recurse -Force
}
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {
    $shortcut = $shell.CreateShortcut((Join-Path $folder 'Usage Garden.lnk'))
    $shortcut.TargetPath = $executable
    $shortcut.WorkingDirectory = $destination
    $shortcut.IconLocation = (Join-Path $destination 'usage-garden.ico')
    $shortcut.Description = 'Usage Garden - your allowances, gently explained'
    $shortcut.Save()
}
Start-Process -FilePath $executable -WorkingDirectory $destination
Write-Host 'Usage Garden is installed. Your desktop and Start menu shortcuts are ready.'
