@echo off
rem ============================================================
rem  Inicia la app móvil "Fábrica de Pastas" (cliente Flet)
rem ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\flet.exe" (
    echo [ERROR] No se encontro flet. Ejecuta primero:
    echo         python -m venv .venv
    echo         .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\flet.exe" run app\main.py
pause