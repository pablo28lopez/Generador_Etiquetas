@echo off
title Compartir Impresora Brother QL-800 - DLS Archer Deposito
color 1F

if exist "%~dp0compartir_impresora.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compartir_impresora.ps1"
    goto :fin
)

echo ======================================================================
echo    COMPARTIR IMPRESORA BROTHER QL-800 EN ESTA COMPUTADORA
echo    DLS Archer - Deposito Neuquen
echo ======================================================================
echo.
echo [*] Buscando impresora Brother instalada...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$brother = Get-Printer | Where-Object { $_.Name -like '*Brother*' -or $_.DriverName -like '*Brother*' } | Select-Object -First 1; if ($brother) { Write-Host '   -> Impresora detectada:' $brother.Name -ForegroundColor Cyan; if (-not $brother.Shared) { try { Set-Printer -Name $brother.Name -Shared $true -ShareName 'Brother QL-800' -ErrorAction Stop; Write-Host '   -> Impresora compartida como Brother QL-800' -ForegroundColor Green; } catch { Write-Host '   -> Para compartirla por primera vez ejecuta con Clic Derecho -> Ejecutar como Administrador' -ForegroundColor Yellow; } } else { Write-Host '   -> Impresora ya se encuentra compartida.' -ForegroundColor Green; } } else { Write-Host '   -> [!] Conecta la impresora Brother QL-800 por USB.' -ForegroundColor Red; }; $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Virtual' -and $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object -ExpandProperty IPAddress -First 1); Write-Host ''; Write-Host '   -> IP DE ESTA MAQUINA:' $ip -ForegroundColor Yellow; Write-Host '';"

:fin
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
