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
set "EXPECTED_EXE=%CD%\.venv\Scripts\orca-vision-helper.exe"
if not exist "%SHIM_DIR%" mkdir "%SHIM_DIR%"
if exist "%SHIM%" (
    findstr /L /C:"%EXPECTED_EXE%" "%SHIM%" >nul
    if errorlevel 1 (
        echo ERROR: Refusing to overwrite existing command: %SHIM%
        echo Inspect and remove or rename it explicitly, then run this installer again.
        pause
        exit /b 1
    )
    echo Already registered: %SHIM%
) else (
    (
        echo @echo off
        echo "%EXPECTED_EXE%" %%*
    ) > "%SHIM%"
    echo Registered: %SHIM%
)
where orca-vision-helper >nul 2>nul && echo OK - 'orca-vision-helper' is on PATH. || echo NOTE: WindowsApps is not on your PATH - add it manually.
if not exist "%SHIM%" (
    echo ERROR: Failed to register the global command.
    pause
    exit /b 1
)

echo.
echo Agent awareness is only for vision-limited models or harness surfaces.
echo Do NOT add the rule to Codex, Claude, or Cursor global instructions; their
echo built-in vision should remain the default. See docs\AGENT_INSTALL.md.
echo Remove any legacy marked block from those global surfaces only with approval.
echo For another vision-limited harness, explicit approval is still required
echo before adding docs\AGENT_TOOL_RULE.md to its global instructions.
echo If the marked block already exists, replace only that block; do not append
echo a duplicate or overwrite unrelated instructions.
echo See docs\AGENT_INSTALL.md for target paths and the safe merge procedure.
echo.
echo Done. Next steps:
echo   orca-vision-helper analyze shot.png
echo.
pause
