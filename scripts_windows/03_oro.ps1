# PASO 2: capa oro (tablas agregadas con porcentajes) en Parquet y CSV.
. "$PSScriptRoot\comun.ps1"
Log "PASO 2 - Capa oro"
Salir-SiFallo (En-Contenedor tlc.oro) "La capa oro"
Log "Oro en oro\parquet y oro\csv"
Get-ChildItem "oro\csv" -Filter *.csv | ForEach-Object { Write-Host "   $($_.Name)" }
