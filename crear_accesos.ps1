$ws = New-Object -ComObject WScript.Shell
$desktop = 'C:\Users\pablo.lopez\OneDrive - DLS Archer\Escritorio'
$targetVbs = 'C:\Users\pablo.lopez\OneDrive - DLS Archer\Escritorio\Proyecto DEPO\etiquetas-web\iniciar_app.vbs'
$iconPath = 'C:\Users\pablo.lopez\OneDrive - DLS Archer\Escritorio\Proyecto DEPO\etiquetas-web\static\img\icono.ico'
$workDir = 'C:\Users\pablo.lopez\OneDrive - DLS Archer\Escritorio\Proyecto DEPO\etiquetas-web'

# 1. Crear / actualizar 'Generador de Etiquetas (Web).lnk'
$lnkPath1 = Join-Path $desktop 'Generador de Etiquetas (Web).lnk'
$s1 = $ws.CreateShortcut($lnkPath1)
$s1.TargetPath = 'wscript.exe'
$s1.Arguments = ('"{0}"' -f $targetVbs)
$s1.WorkingDirectory = $workDir
$s1.IconLocation = $iconPath
$s1.Description = 'Generador de Etiquetas de Deposito (Web PWA con Base de Datos)'
$s1.Save()

# 2. Actualizar tambien 'Generador de Etiquetas.lnk'
$lnkPath2 = Join-Path $desktop 'Generador de Etiquetas.lnk'
$s2 = $ws.CreateShortcut($lnkPath2)
$s2.TargetPath = 'wscript.exe'
$s2.Arguments = ('"{0}"' -f $targetVbs)
$s2.WorkingDirectory = $workDir
$s2.IconLocation = $iconPath
$s2.Description = 'Generador de Etiquetas de Deposito'
$s2.Save()

Write-Output "Shortcuts creados y actualizados exitosamente en: $desktop"
