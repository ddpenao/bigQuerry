# Sube las tablas oro de la práctica a BigQuery, en el dataset tlc_taxis_demo.
# Se niega a subir si el .env apunta al dataset del proyecto completo (tlc_taxis).
#   demo\subir_bigquery.bat
. "$PSScriptRoot\..\scripts_windows\comun.ps1"
Requiere-Env
$dataset = Leer-Env "BQ_DATASET"
if ((-not $dataset) -or ($dataset -eq "tlc_taxis")) {
    Fallo "BQ_DATASET en .env es '$dataset'. La práctica solo sube a tlc_taxis_demo; no subo nada."; exit 1
}
$faltan = @(Tablas-OroFaltantes)
if ($faltan.Count -gt 0) { Fallo "Faltan tablas oro: $($faltan -join ' '). Corre demo\demo.bat"; exit 1 }

# La llave se copia del proyecto completo solo a esta carpeta local (credenciales\ no va a git)
$llave = "credenciales\gcp-key.json"
$llaveCompleto = Join-Path (Split-Path -Parent $Raiz) "TLC_pipeline\$llave"
if ((-not (Test-Path $llave)) -and (Test-Path $llaveCompleto)) { Copy-Item $llaveCompleto $llave }

Log "Subiendo oro de la práctica a $(Leer-Env 'GCP_PROYECTO').$dataset"
& "$Raiz\scripts_windows\04_bigquery.ps1" --solo-oro
exit $LASTEXITCODE
