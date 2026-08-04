@echo off
rem Install orca-vision-helper (Windows). Double-click to run.
setlocal
cd /d "%~dp0\.."
title orca-vision-helper installer

echo Checking Python...
py -3 --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.11+ is required but was not found.
    echo Install it from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^),
    echo then run this script again.
    pause
    exit /b 1
)
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo Python 3.11+ is required; an older version was found. Please upgrade Python.
    pause
    exit /b 1
)

set "CONSENT_MARKER=.venv\.cloud-upload-consent-v1"
set "RECORD_CLOUD_CONSENT="
if exist "%CONSENT_MARKER%" goto consent_done
echo.
echo Cloud image transmission consent
echo   When you configure a cloud or remote custom provider, images selected
echo   for analysis are uploaded to that external service and may contain
echo   sensitive information. Local Ollama analysis does not upload images.
set /p CLOUD_CONSENT="Do you understand and consent to install with cloud-provider support? [y/N]: "
if /I "%CLOUD_CONSENT%"=="Y" goto consent_granted
if /I "%CLOUD_CONSENT%"=="YES" goto consent_granted
echo Installation cancelled: cloud image transmission consent was not granted.
pause
exit /b 1
:consent_granted
set "RECORD_CLOUD_CONSENT=1"
:consent_done

echo Creating virtual environment...
py -3 -m venv .venv
if errorlevel 1 (
    echo Failed to create the virtual environment.
    pause
    exit /b 1
)

echo Installing orca-vision-helper...
".venv\Scripts\python.exe" -m pip install -e . -q
if errorlevel 1 (
    echo Installation failed. Check the error above.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import orca_vision_helper; print('Installed version:', orca_vision_helper.__version__)"
if defined RECORD_CLOUD_CONSENT >"%CONSENT_MARKER%" echo cloud-upload-consent-v1

echo.
set /p SETUP="Choose your default provider and model now? [Y/n]: "
if /I "%SETUP%"=="N" goto skip_setup
echo Running setup - pick a provider, model, and key...
".venv\Scripts\orca-vision-helper.exe" setup
goto after_setup
:skip_setup
echo Skipped. Configure anytime with: .venv\Scripts\orca-vision-helper setup
:after_setup

echo.
echo Registering a global 'orca-vision-helper' command (run from any directory)...
set "SHIM_DIR=%LOCALAPPDATA%\Microsoft\WindowsApps"
set "SHIM=%SHIM_DIR%\orca-vision-helper.cmd"
if not exist "%SHIM_DIR%" mkdir "%SHIM_DIR%"
(
    echo @echo off
    echo "%CD%\.venv\Scripts\orca-vision-helper.exe" %%*
) > "%SHIM%"
echo Registered: %SHIM%
where orca-vision-helper >nul 2>nul && echo OK - 'orca-vision-helper' is on PATH. || echo NOTE: WindowsApps is not on your PATH - add it manually.
if not exist "%SHIM%" (
    echo ERROR: Failed to register the global command.
    pause
    exit /b 1
)

echo.
echo Recommended: make AI agents aware of this tool (so they can "see" screenshots).
echo With your approval, copy the marked block from docs\AGENT_TOOL_RULE.md
echo into your harness's global instructions. Do NOT copy the root AGENTS.md.
echo If the marked block already exists, replace only that block; do not append
echo a duplicate or overwrite unrelated instructions.
echo See docs\AGENT_INSTALL.md for target paths and the safe merge procedure.
echo.
echo Done. Next steps:
echo   orca-vision-helper analyze shot.png
echo.
pause
