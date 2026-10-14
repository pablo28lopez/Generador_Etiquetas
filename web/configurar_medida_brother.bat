@echo off
title Configurar Medida de Papel Brother QL-800 - DLS Archer
echo ======================================================================
echo       CONFIGURAR MEDIDA DE ROLLO EN BROTHER QL-800 (62mm CONTINUO)
echo ======================================================================
echo.
echo Abriendo la ventana de Preferencias de la impresora Brother QL-800...
echo.
echo ----------------------------------------------------------------------
echo  PASO A SEGUIR EN LA VENTANA QUE SE ABRE:
echo.
echo  1. En "Tamano de papel" o "Formato":
echo     Cambia de "29mm x 90mm" a:
echo     👉 "62mm"  (o "62mm Cinta continua" / "DK-22205")
echo.
echo  2. Haz clic en "Aplicar" y luego en "Aceptar".
echo ----------------------------------------------------------------------
echo.
rundll32 printui.dll,PrintUIEntry /e /n "Brother QL-800"
echo.
echo Configuración abierta. Presiona cualquier tecla para cerrar esta ventana...
pause >nul
