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
echo Merge AGENTS.md into your harness's global instructions file (append only), e.g.:
echo   type AGENTS.md ^>^> %USERPROFILE%\.config\opencode\AGENTS.md
echo   type AGENTS.md ^>^> %USERPROFILE%\.codex\AGENTS.md
echo   type AGENTS.md ^>^> %USERPROFILE%\.claude\CLAUDE.md
echo See docs\AGENT_INSTALL.md for the full list.
echo.
echo Done. Next steps:
echo   orca-vision-helper analyze shot.png
echo.
pause
