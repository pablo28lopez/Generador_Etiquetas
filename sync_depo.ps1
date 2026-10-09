$depo = "C:\Users\pablo.lopez\OneDrive - DLS Archer\Escritorio\Proyecto DEPO"

Write-Host "Copiando GeneradorEtiquetas.exe..."
Copy-Item "dist\GeneradorEtiquetas.exe" -Destination (Join-Path $depo "GeneradorEtiquetas.exe") -Force

Write-Host "Copiando configurar_impresora_brother.bat..."
Copy-Item "configurar_impresora_brother.bat" -Destination (Join-Path $depo "configurar_impresora_brother.bat") -Force

Write-Host "Copiando README.md..."
Copy-Item "README.md" -Destination (Join-Path $depo "README.md") -Force

Write-Host "Generando GeneradorEtiquetas_Portable.zip..."
$zipPath = Join-Path $depo "GeneradorEtiquetas_Portable.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

# Crear carpeta temporal limpia para armar el zip sin conflictos de archivo bloqueado
$tempZipDir = Join-Path $env:TEMP "GeneradorEtiquetas_Portable_Build"
if (Test-Path $tempZipDir) { Remove-Item $tempZipDir -Recurse -Force }
New-Item -ItemType Directory -Path $tempZipDir -Force | Out-Null

Copy-Item "dist\GeneradorEtiquetas.exe" -Destination (Join-Path $tempZipDir "GeneradorEtiquetas.exe") -Force
Copy-Item "DATOS_DEPO.xlsx" -Destination (Join-Path $tempZipDir "DATOS_DEPO.xlsx") -Force
Copy-Item "configurar_impresora_brother.bat" -Destination (Join-Path $tempZipDir "configurar_impresora_brother.bat") -Force
Copy-Item "README.md" -Destination (Join-Path $tempZipDir "README.md") -Force

Compress-Archive -Path (Join-Path $tempZipDir "*") -DestinationPath $zipPath -Force
Remove-Item $tempZipDir -Recurse -Force

Write-Host "Sincronizando carpeta web..."
robocopy web (Join-Path $depo "etiquetas-web") /MIR /XD __pycache__ .pytest_cache

Write-Host "Sincronización completada exitosamente."
