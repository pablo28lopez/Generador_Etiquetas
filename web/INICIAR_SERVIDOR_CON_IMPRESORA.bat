@echo off
setlocal enabledelayedexpansion
title Servidor de Impresion Brother QL-800 (Central de Deposito)
cd /d "%~dp0"

echo ======================================================================
echo       CENTRAL DE IMPRESION BROTHER QL-800 - DEPOSITO DLS ARCHER
echo ======================================================================
echo.
echo   [1] Conecta la impresora Brother QL-800 por cable USB a este equipo.
echo   [2] Asegurate de que la impresora este encendida (luz verde fija).
echo.
echo ======================================================================
echo.

:: Detectar comando de Python
set PY_CMD=py -3
py -3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set PY_CMD=python
)

%PY_CMD% --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontro Python en esta maquina.
    echo Por favor instala Python 3.11 desde la tienda de Windows o el instalador oficial.
    pause
    exit /b 1
)

:: Obtener la IP local
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0.*0.0.0.0 ^| findstr /v "Default"') do (
    if not "%%a"=="" set LOCAL_IP=%%a
)

echo [*] Python detectado:
%PY_CMD% --version
echo.
echo ======================================================================
echo   DIRECCION IP DE ESTA MAQUINA CON LA IMPRESORA:
echo.
echo   👉 http://!LOCAL_IP!:8000
echo.
echo   Cualquier companero (incluido Pablo desde su laptop) puede imprimir
echo   directo a esta impresora entrando a: http://!LOCAL_IP!:8000
echo   o configurando esta IP en el boton "En Red" de su propia aplicacion.
echo ======================================================================
echo.

:: Verificar si el puerto 8000 ya esta en uso
netstat -ano | find "LISTENING" | find ":8000" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [AVISO] El servidor ya se encuentra corriendo en el puerto 8000.
    echo Abriendo la aplicacion en el navegador...
    start http://localhost:8000
    exit /b 0
)

echo [*] Iniciando servidor de impresion en 0.0.0.0:8000...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

%PY_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
