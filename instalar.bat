@echo off
title Instalando Relaciones
echo ============================================
echo   Preparando Relaciones. Espera un momento.
echo ============================================
echo.

python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo ============================================
echo   Listo. Ya puedes abrir Relaciones.bat
echo ============================================
pause
