@echo off
REM SessionStart hook: ensure Python venv and dependencies are installed.
REM Reads CLAUDE_PLUGIN_ROOT and CLAUDE_PLUGIN_DATA from environment.

set "PLUGIN_ROOT=%CLAUDE_PLUGIN_ROOT%"
set "DATA_DIR=%CLAUDE_PLUGIN_DATA%"
if "%PLUGIN_ROOT%"=="" set "PLUGIN_ROOT=%~dp0.."
if "%DATA_DIR%"=="" set "DATA_DIR=%USERPROFILE%\.claude\plugins\data\prompt-refiner"

set "VENV_DIR=%DATA_DIR%\.venv"
set "REQ_FILE=%PLUGIN_ROOT%\requirements.txt"
set "STAMP_FILE=%DATA_DIR%\.deps-stamp"

REM Fast path
if exist "%STAMP_FILE%" if exist "%VENV_DIR%" (
  fc "%REQ_FILE%" "%STAMP_FILE%" >nul 2>&1
  if not errorlevel 1 (
    echo {"continue":true,"suppressOutput":true}
    exit /b 0
  )
)

REM Find Python
where python >nul 2>&1
if errorlevel 1 (
  echo {"continue":true,"suppressOutput":true}
  exit /b 0
)

REM Create venv
if not exist "%VENV_DIR%" (
  python -m venv "%VENV_DIR%"
)

REM Install
"%VENV_DIR%\Scripts\pip.exe" install -q --disable-pip-version-check -r "%REQ_FILE%" 2>nul
"%VENV_DIR%\Scripts\pip.exe" install -q --disable-pip-version-check -e "%PLUGIN_ROOT%" 2>nul

REM Stamp
copy /y "%REQ_FILE%" "%STAMP_FILE%" >nul

echo {"continue":true,"suppressOutput":true}
