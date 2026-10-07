@echo off
setlocal
cd /d "%~dp0"
title Generador de Etiquetas PWA

set PY_CMD=py -3
py -3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set PY_CMD=python
)

:: Verificar si el puerto 8000 ya esta en uso
netstat -ano | find "LISTENING" | find ":8000" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    goto OPEN_APP
)

:: Iniciar servidor en segundo plano minimizado
start /min "Servidor Etiquetas PWA" %PY_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 2 /nobreak >nul

:OPEN_APP
:: Abrir como aplicacion nativa en Edge o Chrome
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:8000
    exit /b 0
)

if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:8000
    exit /b 0
)

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app=http://localhost:8000
    exit /b 0
)

start http://localhost:8000
exit /b 0
