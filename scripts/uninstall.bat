@echo off
rem Uninstall orca-vision-helper (Windows). Double-click to run.
setlocal
cd /d "%~dp0\.."
title orca-vision-helper uninstaller

if exist ".venv\Scripts\orca-vision-helper.exe" (
    echo Removing registered providers ^(and their keychain keys^)...
    ".venv\Scripts\python.exe" "scripts\remove_providers.py" ".venv\Scripts\orca-vision-helper.exe"
)

echo Deleting configuration...
if exist "%USERPROFILE%\.config\orca-vision-helper" rmdir /s /q "%USERPROFILE%\.config\orca-vision-helper"

echo Removing the global command (if any)...
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\orca-vision-helper.cmd" del "%LOCALAPPDATA%\Microsoft\WindowsApps\orca-vision-helper.cmd"

echo Deleting the virtual environment...
if exist ".venv" rmdir /s /q ".venv"

echo.
echo Uninstalled.
echo If provider keys could not be removed, delete them manually from
echo Windows Credential Manager ^(entries under "orca-vision-helper"^).
echo.
pause
