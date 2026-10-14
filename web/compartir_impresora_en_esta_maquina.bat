@echo off
title Compartir Impresora Brother QL-800 - DLS Archer Deposito
color 1F

echo ======================================================================
echo    COMPARTIR IMPRESORA BROTHER QL-800 EN ESTA COMPUTADORA
echo    DLS Archer - Deposito Neuquen
echo ======================================================================
echo.

:: Verificar permisos de Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Solicitando permisos de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

echo [*] Buscando impresora Brother instalada por USB en este equipo...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = Get-Printer | Where-Object { $_.Name -like '*Brother*' -or $_.DriverName -like '*Brother*' } | Select-Object -First 1; " ^
    "if ($p) { " ^
    "   Write-Host '   -> Impresora detectada:' $p.Name; " ^
    "   Set-Printer -Name $p.Name -Shared $true -ShareName 'Brother QL-800' -ErrorAction SilentlyContinue; " ^
    "   Write-Host '   -> Impresora compartida exitosamente con nombre: Brother QL-800' -ForegroundColor Green; " ^
    "} else { " ^
    "   Write-Host '   -> [!] No se detecto la Brother instalada en este equipo. Asegurate de conectar el cable USB e instalar el driver.' -ForegroundColor Yellow; " ^
    "}"

echo.
echo [*] Habilitando permiso en Firewall de Windows (Compartir archivos e impresoras)...
netsh advfirewall firewall set rule group="Archivos e impresoras compartidos" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes >nul 2>&1

echo.
echo [*] Obteniendo direccion IP de esta maquina...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" /c:"Direcci"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)

:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo ======================================================================
echo    CONFIGURACION COMPLETADA CON EXITO
echo ======================================================================
echo.
echo  1. La impresora Brother QL-800 quedo COMPARTIDA en esta maquina.
echo  2. La direccion IP de este equipo es:  %LOCAL_IP%
echo.
echo  PARA IMPRIMIR DESDE LA WEB:
echo  En la pantalla web (http://10.12.70.105:8000):
echo    1. Haz clic en el boton azul 'En Red' (al lado de Impresora Destino).
echo    2. Escribe la IP: %LOCAL_IP%
echo    3. Haz clic en 'Conectar'.
echo.
echo  Listo, ya podran imprimir directamente por cable USB desde cualquier PC.
echo ======================================================================
echo.
pause
