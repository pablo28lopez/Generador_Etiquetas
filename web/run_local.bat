@echo off
title Servidor Local - Generador de Etiquetas Web PWA
echo ======================================================================
echo           GENERADOR DE ETIQUETAS WEB PWA (SERVIDOR LOCAL)
echo ======================================================================
echo.

set PY_CMD=py -3
py -3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set PY_CMD=python
)

echo [1/2] Verificando dependencias web...
%PY_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

echo.
echo [2/2] Iniciando servidor FastAPI en http://localhost:8000 ...
echo Presione CTRL+C para detener el servidor.
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

%PY_CMD% -m uvicorn main:app --host 0.0.0.0 --port 8000
pause