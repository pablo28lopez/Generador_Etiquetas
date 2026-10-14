# ==============================================================================
# Script de Comprobación y Diagnóstico - Brother QL-800
# DLS Archer - Depósito Neuquén
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Clear-Host

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "       DIAGNOSTICO Y COMPROBACION DE IMPRESORA BROTHER QL-800         " -ForegroundColor Cyan
Write-Host "                       DLS Archer - Deposito                          " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
$ipAddr = ($([System.Net.Dns]::GetHostAddresses($env:COMPUTERNAME) | Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.IPAddressToString -notlike '169.254*' } | Select-Object -First 1 -ExpandProperty IPAddressToString))
Write-Host "Equipo actual: $env:COMPUTERNAME (IP: $ipAddr)" -ForegroundColor Gray
Write-Host "Fecha y Hora : $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Comprobación Física USB
# ------------------------------------------------------------------------------
Write-Host "--- 1. CONEXION FISICA USB ---" -ForegroundColor Yellow

$usbPresent = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { 
    $_.FriendlyName -match "Brother|QL-800" -or $_.InstanceId -match "04F9"
}

$usbStorage = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { 
    $_.FriendlyName -match "Brother.*USB Device" -or $_.InstanceId -match "USBSTOR.*04F9"
}

if ($usbPresent) {
    Write-Host "[OK] Impresora Brother QL-800 DETECTADA por cable USB en este equipo." -ForegroundColor Green
    foreach ($d in $usbPresent) {
        Write-Host "     - $($d.FriendlyName) [$($d.Class)] - Estado: $($d.Status)" -ForegroundColor Gray
    }
    
    if ($usbStorage) {
        Write-Host ""
        Write-Host "     [ATENCION] Se detecto modo 'Editor Lite' (almacenamiento USB)." -ForegroundColor Yellow
        Write-Host "     -> Si la luz verde de 'Editor Lite' esta encendida en la impresora," -ForegroundColor Yellow
        Write-Host "        manten presionado el boton 'Editor Lite' 2 segundos hasta que se apague." -ForegroundColor Yellow
    }
} else {
    Write-Host "[NO ENCHUFADA] No se detecta ninguna Brother QL-800 por USB en este equipo." -ForegroundColor Red
    Write-Host "     Posibles causas:" -ForegroundColor White
    Write-Host "     1. El cable USB esta desenchufado o conectado a otra computadora." -ForegroundColor Gray
    Write-Host "     2. La impresora esta apagada (revisa el boton de encendido y la luz)." -ForegroundColor Gray
    Write-Host "     3. Si la impresora esta en la maquina de un companero, este equipo" -ForegroundColor Gray
    Write-Host "        debe imprimir a traves de la red o la web." -ForegroundColor Gray
}
Write-Host ""

# ------------------------------------------------------------------------------
# 2. Impresoras registradas en Windows
# ------------------------------------------------------------------------------
Write-Host "--- 2. IMPRESORAS EN WINDOWS ---" -ForegroundColor Yellow

$printers = Get-Printer -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Brother|QL" }

if ($printers) {
    Write-Host "[OK] Impresora(s) registrada(s) en Windows:" -ForegroundColor Green
    foreach ($p in $printers) {
        $sharedText = if ($p.Shared) { "Compartida en red como '\\$env:COMPUTERNAME\$($p.ShareName)'" } else { "No compartida" }
        Write-Host "     - Nombre : $($p.Name)" -ForegroundColor White
        Write-Host "       Puerto : $($p.PortName)" -ForegroundColor Gray
        Write-Host "       Estado : $($p.PrinterStatus)" -ForegroundColor Gray
        Write-Host "       Driver : $($p.DriverName)" -ForegroundColor Gray
        Write-Host "       Red    : $sharedText" -ForegroundColor Gray
    }
} else {
    Write-Host "[NO INSTALADA] No hay ninguna impresora Brother QL registrada en este Windows." -ForegroundColor Red
    Write-Host "     -> Instala el driver de Brother QL-800 o ejecuta conectar_impresora_red.bat" -ForegroundColor Gray
}
Write-Host ""

# ------------------------------------------------------------------------------
# 3. Estado de la Cola de Impresión
# ------------------------------------------------------------------------------
Write-Host "--- 3. COLA DE IMPRESION ---" -ForegroundColor Yellow

$allJobs = @()
if ($printers) {
    foreach ($p in $printers) {
        $jobs = Get-PrintJob -PrinterName $p.Name -ErrorAction SilentlyContinue
        if ($jobs) {
            $allJobs += $jobs
        }
    }
}

if ($allJobs.Count -eq 0) {
    Write-Host "[OK] La cola de impresion esta LIMPIA (0 trabajos trabados)." -ForegroundColor Green
} else {
    Write-Host "[TRABAJOS EN COLA] Hay $($allJobs.Count) trabajo(s) esperando o trabados:" -ForegroundColor Yellow
    foreach ($j in $allJobs) {
        Write-Host "     - Trabajo #$($j.Id): '$($j.DocumentName)' - Estado: $($j.JobStatus) (Enviado: $($j.SubmittedTime))" -ForegroundColor Gray
    }
    Write-Host ""
    $resp = Read-Host "¿Deseas CANCELAR y limpiar todos los trabajos trabados ahora? (S/N)"
    if ($resp -match "^[sSyY]") {
        foreach ($p in $printers) {
            Get-PrintJob -PrinterName $p.Name -ErrorAction SilentlyContinue | Remove-PrintJob -ErrorAction SilentlyContinue
        }
        Write-Host "[OK] Cola de impresion vaciada exitosamente." -ForegroundColor Green
    }
}
Write-Host ""

# ------------------------------------------------------------------------------
# 4. Estado del Servidor Web (Generador de Etiquetas)
# ------------------------------------------------------------------------------
Write-Host "--- 4. SERVIDOR WEB DE ETIQUETAS ---" -ForegroundColor Yellow

$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$localIP = ($([System.Net.Dns]::GetHostAddresses($env:COMPUTERNAME) | Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.IPAddressToString -notlike '169.254*' -and $_.IPAddressToString -notlike '127.*' } | Select-Object -First 1 -ExpandProperty IPAddressToString))

if ($port8000) {
    Write-Host "[OK] Servidor Web ACTIVO y escuchando en el puerto 8000." -ForegroundColor Green
    Write-Host "     - Enlace local : http://localhost:8000" -ForegroundColor White
    if ($localIP) {
        Write-Host "     - Enlace en red: http://${localIP}:8000" -ForegroundColor White
    }
} else {
    Write-Host "[INACTIVO] El servidor web no esta corriendo en este equipo." -ForegroundColor Gray
    Write-Host "     -> Si este equipo es el servidor principal, ejecuta 'iniciar_servidor_red.bat'." -ForegroundColor Gray
}
Write-Host ""

# ------------------------------------------------------------------------------
# 5. Prueba de Impresión
# ------------------------------------------------------------------------------
if ($printers -and $usbPresent) {
    Write-Host "--- 5. PRUEBA DE IMPRESION ---" -ForegroundColor Yellow
    $testTarget = ($printers | Select-Object -First 1).Name
    $pResp = Read-Host "¿Deseas enviar una impresion de prueba a '$testTarget' ahora? (S/N)"
    if ($pResp -match "^[sSyY]") {
        Write-Host "[*] Enviando pagina de prueba a '$testTarget'..." -ForegroundColor Cyan
        rundll32 printui.dll,PrintUIEntry /k /n "$testTarget"
        Write-Host "[OK] Orden enviada. Comprueba si la impresora fisica respondio." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Diagnostico completado. Presiona cualquier tecla para salir..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
