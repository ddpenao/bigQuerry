# PASO 3: carga a BigQuery con load jobs (gratis).
#   scripts_windows\04_bigquery.bat --solo-estimar   calcula tamaños, no sube nada
#   scripts_windows\04_bigquery.bat --solo-oro       sube solo las tablas oro
#   scripts_windows\04_bigquery.bat                  sube oro + los meses de plata de BQ_PLATA_MESES
. "$PSScriptRoot\comun.ps1"
Requiere-Env
$opciones = @($args)
if ($opciones -notcontains "--solo-estimar") {
    if (-not (Leer-Env "GCP_PROYECTO")) { Fallo "Define GCP_PROYECTO en .env"; exit 1 }
    if (-not (Test-Path "credenciales\gcp-key.json")) { Fallo "Falta credenciales\gcp-key.json (ver README, sección BigQuery)"; exit 1 }
}
Log "PASO 3 - Carga a BigQuery $($opciones -join ' ')"
$codigo = En-Contenedor tlc.bigquery_carga @opciones
if ($codigo -eq 3) {
    Fallo "Detenido a propósito: hay que decidir qué meses de plata subir (BQ_PLATA_MESES en .env)."
} elseif ($codigo -ne 0) {
    Fallo "La carga terminó con error ($codigo). Revisa logs\03_bigquery_*.log"
}
exit $codigo
