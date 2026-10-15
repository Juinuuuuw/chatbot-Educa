@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    if exist "INICIAR-LOCAL.cmd" (
        call "INICIAR-LOCAL.cmd"
        exit /b
    )
    echo Ambiente Python ausente. Siga a instalacao no README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configurar.py
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" iniciar.py
pause
