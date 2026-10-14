@echo off
title Conectar Impresora Brother QL-800 - DLS Archer Deposito
echo ======================================================================
echo    CONECTAR IMPRESORA BROTHER QL-800 DE DEPOSITO EN ESTE EQUIPO
echo ======================================================================
echo.
echo Conectando a la impresora compartida en la maquina de Pablo Lopez...
echo.

:: Servidor y nombre de recurso compartido
set HOST_NAME=LOPEZPAB-NB
set HOST_IP=10.12.70.105

echo [*] Instalando impresora compartida \\%HOST_NAME%\BrotherQL800...
rundll32 printui.dll,PrintUIEntry /in /n "\\%HOST_NAME%\BrotherQL800"

if %ERRORLEVEL% neq 0 (
    echo [!] Intentando conectar directamente por IP \\%HOST_IP%\BrotherQL800...
    rundll32 printui.dll,PrintUIEntry /in /n "\\%HOST_IP%\BrotherQL800"
)

echo.
echo ======================================================================
echo   ESTADO: Impresora conectada con exito en este equipo.
echo   Ya podras imprimir directamente desde la aplicacion web o Edge.
echo ======================================================================
echo.
echo Abriendo la aplicacion en tu navegador...
start http://%HOST_IP%:8000
timeout /t 4
