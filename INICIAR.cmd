@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python ausente. Siga a instalacao no README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configurar.py
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" iniciar.py
pause
