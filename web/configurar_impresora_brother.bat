@echo off
chcp 65001 >nul
title Configurador de Impresora Brother QL - DLS Archer Depósito Neuquén
cls
echo ===============================================================================
echo       CONFIGURADOR PERMANENTE DE MEDIDA - BROTHER QL-800 / QL SERIES
echo       DLS Archer - Depósito Neuquén
echo ===============================================================================
echo.
echo Este asistente abrirá la ventana de PREFERENCIAS DE IMPRESIÓN de Windows
echo para que la medida de la etiqueta quede guardada PERMANENTEMENTE en el equipo.
echo.
echo De esta forma, Chrome y Edge utilizarán siempre la medida correcta sin
echo que tengas que volver a cambiarla en la configuración del driver de Brother.
echo.
echo -------------------------------------------------------------------------------
echo INSTRUCCIONES (Se realiza por única vez en la máquina con la Brother):
echo -------------------------------------------------------------------------------
echo 1. En la ventana que se abrirá a continuación:
echo    - Ve a la pestaña "Básica" (o "General").
echo    - En "Formato" / "Tamaño de papel", selecciona:
echo        • "62mm x 29mm" (si usas la etiqueta chica DK-11209)
echo        • "62mm"        (si usas el rollo continuo DK-22205)
echo        • "62mm x 100mm"(si usas la etiqueta grande DK-11202)
echo 2. Haz clic en el botón "Aplicar" y luego en "Aceptar".
echo -------------------------------------------------------------------------------
echo.
echo Abriendo Preferencias de Impresión de Windows para Brother QL-800...
echo.

rundll32 printui.dll,PrintUIEntry /e /n "Brother QL-800"

if %errorlevel% neq 0 (
    echo [Aviso] Si la impresora tiene otro nombre en Windows, abriendo el selector general...
    control printers
)

echo.
echo ===============================================================================
echo Configuración guardada en Windows. A partir de ahora los navegadores
echo imprimirán directamente sin pedir cambiar la medida.
echo ===============================================================================
pause
