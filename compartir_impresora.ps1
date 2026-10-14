Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   COMPARTIR IMPRESORA BROTHER QL-800 EN ESTA COMPUTADORA" -ForegroundColor Cyan
Write-Host "   DLS Archer - Deposito Neuquen" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Comprobar permisos de Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[!] AVISO: No se detectaron permisos de Administrador." -ForegroundColor Yellow
    Write-Host "    Si la impresora todavia no esta compartida en Windows," -ForegroundColor Yellow
    Write-Host "    cierra esta ventana, haz clic derecho sobre 'compartir_impresora_en_esta_maquina.bat'" -ForegroundColor Yellow
    Write-Host "    y selecciona 'Ejecutar como administrador'." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "[*] Permisos de Administrador: CORRECTOS" -ForegroundColor Green
    Write-Host ""
}

# 2. Buscar impresora Brother
Write-Host "[*] Buscando impresora Brother instalada..." -ForegroundColor White
$brother = Get-Printer | Where-Object { $_.Name -like "*Brother*" -or $_.DriverName -like "*Brother*" } | Select-Object -First 1

if ($brother) {
    Write-Host "   -> Impresora detectada: $($brother.Name)" -ForegroundColor Cyan
    Write-Host "   -> Estado actual compartido: $(if ($brother.Shared) { 'SI (Nombre: ' + $brother.ShareName + ')' } else { 'NO' })" -ForegroundColor White
    
    if (-not $brother.Shared) {
        try {
            Set-Printer -Name $brother.Name -Shared $true -ShareName "Brother QL-800" -ErrorAction Stop
            Write-Host "   -> Impresora compartida exitosamente como 'Brother QL-800'!" -ForegroundColor Green
        } catch {
            Write-Host "   -> [!] No se pudo cambiar el estado a compartido sin permisos de Administrador." -ForegroundColor Yellow
            Write-Host "          Por favor ejecuta el archivo con clic derecho -> 'Ejecutar como administrador'." -ForegroundColor Yellow
        }
    } else {
        Write-Host "   -> Impresora ya se encuentra compartida y lista para usar." -ForegroundColor Green
    }
} else {
    Write-Host "   -> [!] No se detecto ninguna impresora Brother instalada." -ForegroundColor Red
    Write-Host "          Conecta el cable USB de la Brother QL-800 a esta PC e instala el driver si es necesario." -ForegroundColor Yellow
}

# 3. Firewall (si es admin)
if ($isAdmin) {
    try {
        netsh advfirewall firewall set rule group="Archivos e impresoras compartidos" new enable=Yes | Out-Null
        netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes | Out-Null
        Write-Host "[*] Reglas de Firewall habilitadas para compartir impresoras." -ForegroundColor Green
    } catch {
        # Silencioso
    }
}

# 4. Obtener IP Local
Write-Host ""
Write-Host "[*] Obteniendo direccion IP de esta maquina..." -ForegroundColor White
$localIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { 
    $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Virtual|Pseudo' -and 
    $_.IPAddress -notlike '169.254*' -and 
    $_.IPAddress -ne '127.0.0.1' 
} | Select-Object -ExpandProperty IPAddress

$selectedIp = $localIps | Where-Object { $_ -like "10.*" -or $_ -like "192.168.*" } | Select-Object -First 1
if (-not $selectedIp) {
    $selectedIp = $localIps | Select-Object -First 1
}
if (-not $selectedIp) {
    $selectedIp = "No detectada (revisar ipconfig)"
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   DATOS PARA CONECTAR DESDE LA APLICACION WEB" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Impresora:                Brother QL-800" -ForegroundColor White
Write-Host "  2. DIRECCION IP DE ESTA PC:  $selectedIp" -ForegroundColor Yellow
Write-Host ""
Write-Host "  PASOS PARA IMPRIMIR DESDE CUALQUIER OTRA MAQUINA:" -ForegroundColor White
Write-Host "  a) Entra en la aplicacion web (http://10.12.70.105:8000)" -ForegroundColor Gray
Write-Host "  b) En la tarjeta de la impresora haz clic en el boton azul 'En Red'." -ForegroundColor Gray
Write-Host "  c) Escribe la IP: $selectedIp" -ForegroundColor Yellow
Write-Host "  d) Haz clic en 'Conectar'." -ForegroundColor Gray
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
