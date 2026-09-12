@echo off
setlocal
cd /d "%~dp0"
if exist "UsageGarden.exe" (
    start "" "UsageGarden.exe"
    exit /b 0
)
if exist "dist\UsageGarden\UsageGarden.exe" (
    start "" "dist\UsageGarden\UsageGarden.exe"
    exit /b 0
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-Source.ps1"
if errorlevel 1 pause
