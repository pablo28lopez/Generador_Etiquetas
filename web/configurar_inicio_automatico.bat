@echo off
setlocal
title Configurar Inicio Automatico del Servidor de Etiquetas
cd /d "%~dp0"

echo ======================================================================
echo    CONFIGURAR INICIO AUTOMATICO DEL SERVIDOR EN WINDOWS
echo ======================================================================
echo.
echo Este script creara una tarea programada para que el servidor de etiquetas
echo arranque silenciosamente en segundo plano cada vez que inicies sesion en Windows,
echo manteniendolo siempre disponible en la red sin que tengas que abrirlo a mano.
echo.

set TASK_NAME=ServidorEtiquetasDEPO
set VBS_PATH=%~dp0iniciar_app.vbs

if not exist "%VBS_PATH%" (
    echo [ERROR] No se encontro el archivo iniciar_app.vbs en esta carpeta.
    pause
    exit /b 1
)

echo Creando tarea programada: %TASK_NAME%...
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo [EXITO] Tarea configurada correctamente.
    echo El servidor iniciara automaticamente al encender o reiniciar esta PC.
    echo.
    echo Para iniciar el servidor ahora mismo:
    echo   schtasks /run /tn "%TASK_NAME%"
    echo.
    echo Para eliminar el inicio automatico en el futuro:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
    echo ======================================================================
) else (
    echo.
    echo [ERROR] No se pudo crear la tarea programada.
    echo Asegurate de ejecutar este archivo como Administrador si es necesario.
)

echo.
pause
