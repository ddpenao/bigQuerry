# PASO 2: capa oro (tablas agregadas con porcentajes) en Parquet y CSV.
. "$PSScriptRoot\comun.ps1"
Requiere-Env
if (-not (Get-ChildItem -Path "plata\viajes" -Directory -Filter "fecha=*" -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    Fallo "La capa plata está vacía."
    Fallo "Reconstrúyela con: scripts_windows\reconstruir.bat plata   (o todo de una vez: scripts_windows\reconstruir.bat oro)"
    exit 1
}
$faltan = @(Meses-IncompletosPlata)
if ($faltan.Count -gt 0) { Log "Aviso: plata tiene meses incompletos y oro saldrá sin ellos: $($faltan -join ' ') (usa scripts_windows\reconstruir.bat oro)" }
Log "PASO 2 - Capa oro"
Salir-SiFallo (En-Contenedor tlc.oro) "La capa oro"
Log "PASO 2b - Tablas oro del dashboard (horas, días, semanas, zonas, pagos, mapas)"
Salir-SiFallo (En-Contenedor tlc.oro_dashboard) "Las tablas del dashboard"
Log "Oro en oro\parquet y oro\csv"
Get-ChildItem "oro\csv" -Filter *.csv | ForEach-Object { Write-Host "   $($_.Name)" }
