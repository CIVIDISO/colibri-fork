@echo off
setlocal
cd /d "%~dp0"

rem Override these variables before launching when paths differ on another computer.
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen2.5-coder:7b"
if not defined COLIBRI_MODEL set "COLIBRI_MODEL=C:\Users\Sales\Models\qwen36"
if not defined COLIBRI_PROJECT set "COLIBRI_PROJECT=%CD%\PBOMNI"

where ollama >nul 2>&1 || (
  echo Ollama was not found. Install Ollama, then run this launcher again.
  pause
  exit /b 1
)
where cargo >nul 2>&1 || set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

start "Colibri Ollama" /min ollama serve
start "Colibri Deep API" /min python "%CD%\c\coli" web --model "%COLIBRI_MODEL%" --host 127.0.0.1 --port 8000 --no-browser
start "Colibri Workbench" /min python "%CD%\workbench\server.py" --project "%COLIBRI_PROJECT%" --port 8787 --model-url http://127.0.0.1:11434/v1 --model "%OLLAMA_MODEL%"
start "Colibri Desktop" /d "%CD%\desktop" cmd /k "set PATH=%USERPROFILE%\.cargo\bin;%PATH%&& cargo tauri dev"

echo Colibri is starting.
echo Companion: local GPU model %OLLAMA_MODEL%
echo Deep API:  http://127.0.0.1:8000/
echo Workbench: http://127.0.0.1:8787/
