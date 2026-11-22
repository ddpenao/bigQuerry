# Deja lista la práctica rápida (2 meses por año) en Windows. Se ejecuta una vez, dentro de la carpeta TLC_demo.
#   demo\preparar_demo.bat
# No toca el proyecto completo (..\TLC_pipeline), ni la bronce original (..\TLC), ni BigQuery, ni Metabase.
. "$PSScriptRoot\..\scripts_windows\comun.ps1"
$Completo = Join-Path (Split-Path -Parent $Raiz) "TLC_pipeline"

Log "1/4 Archivo .env de la práctica"
if (-not (Test-Path ".env")) {
    $texto = [System.IO.File]::ReadAllText((Join-Path $Raiz "plantilla_env.txt"))
    # Solo se copia el ID del proyecto, por si se sube la práctica a tlc_taxis_demo
    $envCompleto = Join-Path $Completo ".env"
    if (Test-Path $envCompleto) {
        $linea = Get-Content $envCompleto | Where-Object { $_ -match "^GCP_PROYECTO=" } | Select-Object -Last 1
        if ($linea) { $texto = $texto -replace "(?m)^GCP_PROYECTO=.*$", $linea.Trim() }
    }
    Escribir-TextoLF ".env" $texto
    Log "   .env creado (meses: $(Leer-Env 'DEMO_MESES'))"
} else {
    Log "   ya existe .env"
}

Log "2/4 Carpetas y tabla de zonas"
foreach ($c in "plata", "oro", "logs", "reportes", "datos_referencia", "credenciales", "bronce_demo") {
    New-Item -ItemType Directory -Force -Path $c | Out-Null
}
$zonas = "datos_referencia\taxi_zone_lookup.csv"
$zonasCompleto = Join-Path $Completo $zonas
if (-not ((Test-Path $zonas) -and (Get-Item $zonas).Length -gt 0)) {
    if (Test-Path $zonasCompleto) {
        Copy-Item $zonasCompleto $zonas
    } else {
        try { Invoke-WebRequest -UseBasicParsing -Uri "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv" -OutFile $zonas -ErrorAction Stop }
        catch { Remove-Item $zonas -ErrorAction SilentlyContinue }
    }
}
if (Test-Path $zonas) { Log "   tabla de zonas lista" } else { Fallo "   falta $zonas" }

Log "3/4 Imagen Docker"
& docker image inspect tlc-pipeline:1.0 *> $null
if ($LASTEXITCODE -eq 0) {
    Log "   se reutiliza tlc-pipeline:1.0 (la misma del proyecto completo)"
} else {
    & docker compose build
    Salir-SiFallo $LASTEXITCODE "La construcción de la imagen"
}

Log "4/4 Bronce de la práctica (copia desde ..\TLC, sin internet)"
& "$Raiz\scripts_windows\reconstruir.ps1" bronce
Log "Listo. Para correr la práctica: demo\demo.bat"
