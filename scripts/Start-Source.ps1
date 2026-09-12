$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    $pythonCommand = $null
    $pythonPrefix = @()
    foreach ($version in @('3.12', '3.13', '3.11')) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py "-$version" -c 'import sys; print(sys.version.split()[0])' 2>$null
            if ($LASTEXITCODE -eq 0) { $pythonCommand = 'py'; $pythonPrefix = @("-$version"); break }
        }
    }
    if (-not $pythonCommand) {
        Write-Host 'The source launcher needs Python 3.11, 3.12, or 3.13.'
        Write-Host 'For an app that needs no Python installation, download the Windows app from the repository Actions page.'
        Write-Host 'Or install Python 3.12 from python.org and run this launcher again.'
        exit 1
    }
    & $pythonCommand @pythonPrefix -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
}
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install the desktop interface. Check your internet connection.' }
Start-Process -FilePath (Join-Path $root '.venv\Scripts\pythonw.exe') -ArgumentList '-m usage_garden' -WorkingDirectory $root
