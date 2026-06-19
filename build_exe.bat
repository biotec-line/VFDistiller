@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)

python build_release.py
if errorlevel 1 (
    pause
    exit /b 1
)

echo [OK] EXE aktualisiert: dist\VFDistiller.exe
