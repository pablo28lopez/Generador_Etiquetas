@echo off
setlocal
title Detener Servidor de Etiquetas
echo Deteniendo servidor en puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo Listo. Servidor detenido.
timeout /t 2 >nul
