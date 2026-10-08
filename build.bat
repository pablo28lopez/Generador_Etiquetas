@echo off
title Compilador - Generador de Etiquetas (.exe)
echo ======================================================================
echo           COMPILADOR DE GENERADOR DE ETIQUETAS (.EXE)
echo ======================================================================
echo.

set PY_CMD=py -3
py -3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set PY_CMD=python
)

echo [1/3] Verificando e instalando librerias requeridas...
%PY_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias con pip.
    pause
    exit /b 1
)

echo.
echo [2/3] Compilando con PyInstaller e incrustando icono, fuentes y logo...
%PY_CMD% -m PyInstaller --noconsole ^
    --onefile ^
    --name "GeneradorEtiquetas" ^
    --icon "icono.ico" ^
    --add-data "arial.ttf;." ^
    --add-data "arialbd.ttf;." ^
    --add-data "icono.ico;." ^
    --add-data "logo.png;." ^
    --add-data "DATOS_DEPO.xlsx;." ^
    --collect-submodules barcode ^
    --collect-submodules PIL ^
    --collect-submodules fpdf ^
    --collect-submodules openpyxl ^
    --clean ^
    app.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo la compilacion de PyInstaller.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [3/3] COMPILACION COMPLETADA EXITOSAMENTE!
echo.
echo El archivo ejecutable (.exe) portable e independiente esta listo en:
echo     dist\GeneradorEtiquetas.exe
echo ======================================================================
echo.
pause