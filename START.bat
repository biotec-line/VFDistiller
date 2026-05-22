@echo off
cd /d "%~dp0"
if exist "dist\VFDistiller.exe" (
    start "" "dist\VFDistiller.exe"
    exit /b
)
python "Variant_Fusion_pro_V17.py"
pause
