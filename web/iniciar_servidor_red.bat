@echo off
setlocal enabledelayedexpansion
title Servidor de Etiquetas Deposito (Red / OneDrive)
cd /d "%~dp0"

echo ======================================================================
echo       SERVIDOR DE ETIQUETAS DEPOSITO DLS ARCHER (RED / ONEDRIVE)
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
    echo [ERROR] No se encontro Python instalado en este equipo.
    echo Para ejecutar el servidor web se requiere Python 3.9 o superior.
    echo Si no tienes Python, puedes usar el ejecutable portable: GeneradorEtiquetas.exe
    pause
    exit /b 1
)

:: Obtener la IP local de este equipo
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0.*0.0.0.0 ^| findstr /v "Default"') do (
    if not "%%a"=="" set LOCAL_IP=%%a
)

echo [*] Directorio de trabajo: %CD%
echo [*] Python detectado: 
%PY_CMD% --version
echo.
echo ======================================================================
echo   ENLACES DE ACCESO PARA PRUEBAS:
echo.
echo   - Tu acceso en esta maquina:
echo     👉 http://localhost:8000
echo.
echo   - Acceso para otros usuarios en la red (Wi-Fi / LAN / Deposito):
echo     👉 http://!LOCAL_IP!:8000
echo.
echo   (Cualquier dispositivo en la misma red podra entrar sin instalar nada)
echo ======================================================================
echo.

:: Verificar si el puerto 8000 ya esta en uso
netstat -ano | find "LISTENING" | find ":8000" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [AVISO] El servidor ya se encuentra corriendo en el puerto 8000.
    echo Abriendo la aplicacion en el navegador...
    start http://localhost:8000
    pause
    exit /b 0
)

echo [1/2] Iniciando servidor FastAPI / Uvicorn en 0.0.0.0:8000...
echo Presiona Ctrl + C en esta ventana cuando desees detener el servidor.
echo.

:: Abrir navegador tras 2 segundos
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Ejecutar servidor en primer plano
%PY_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000
