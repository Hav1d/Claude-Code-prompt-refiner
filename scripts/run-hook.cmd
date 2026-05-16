@echo off
REM UserPromptSubmit hook: run prompt-refiner on user input.
REM Reads CLAUDE_PLUGIN_ROOT and CLAUDE_PLUGIN_DATA from environment.

set "PLUGIN_ROOT=%CLAUDE_PLUGIN_ROOT%"
set "DATA_DIR=%CLAUDE_PLUGIN_DATA%"
if "%PLUGIN_ROOT%"=="" set "PLUGIN_ROOT=%~dp0.."
if "%DATA_DIR%"=="" set "DATA_DIR=%USERPROFILE%\.claude\plugins\data\prompt-refiner"

set "VENV_PYTHON=%DATA_DIR%\.venv\Scripts\python.exe"

REM If venv doesn't exist, pass through
if not exist "%VENV_PYTHON%" exit /b 0

REM Build runtime config from userConfig environment variables
set "CONFIG_FILE=%DATA_DIR%\runtime-config.json"
set "PROVIDER=%CLAUDE_PLUGIN_OPTION_PROVIDER%"
if "%PROVIDER%"=="" set "PROVIDER=deepseek"
set "API_KEY=%CLAUDE_PLUGIN_OPTION_API_KEY%"
set "BASE_URL=%CLAUDE_PLUGIN_OPTION_BASE_URL%"

if not "%API_KEY%"=="" (
  echo {"active_provider":"%PROVIDER%","providers":{"%PROVIDER%":{"api_key":"%API_KEY%","base_url":"%BASE_URL%"}},"history_lines":50} > "%CONFIG_FILE%"
  "%VENV_PYTHON%" -X utf8 -m src.hook_entry UserPromptSubmit --config "%CONFIG_FILE%"
) else (
  "%VENV_PYTHON%" -X utf8 -m src.hook_entry UserPromptSubmit
)
