# Descarga la capa bronce (Parquet de taxis amarillos de TLC), ~2 GB.
#   scripts_windows\descargar_bronce.bat                    BRONCE_DESDE a BRONCE_HASTA (por defecto 2024-01 a 2026-08)
#   scripts_windows\descargar_bronce.bat 2026-06 2026-08    solo un rango
# Los archivos que ya existen no se vuelven a descargar.
param([string]$Desde = "", [string]$Hasta = "")
. "$PSScriptRoot\comun.ps1"
# Sin argumentos y con DEMO_MESES en .env, descarga solo esos meses
if ((-not $Desde) -and (-not $Hasta) -and (@(Meses-Demo).Count -gt 0)) {
    foreach ($m in @(Meses-Demo)) { & $PSCommandPath $m $m }
    exit 0
}
if (-not $Desde) { $Desde = Bronce-Desde }
if (-not $Hasta) { $Hasta = Bronce-Hasta }
$bronce = Ruta-Bronce
$url = "https://d37ci6vzurychx.cloudfront.net/trip-data"
$usarCurl = [bool](Get-Command curl.exe -ErrorAction SilentlyContinue)

Log "Descargando $Desde -> $Hasta en $bronce"
$mes = [datetime]::ParseExact("$Desde-01", "yyyy-MM-dd", $null)
$fin = [datetime]::ParseExact("$Hasta-01", "yyyy-MM-dd", $null)
$ok = 0; $saltados = 0; $fallidos = @()
while ($mes -le $fin) {
    $m = $mes.ToString("yyyy-MM")
    $carpeta = Join-Path $bronce $mes.ToString("yyyy")
    New-Item -ItemType Directory -Force -Path $carpeta | Out-Null
    $destino = Join-Path $carpeta "yellow_tripdata_$m.parquet"
    if ((Test-Path $destino) -and (Get-Item $destino).Length -gt 0) {
        $saltados++
    } else {
        $temporal = "$destino.part"
        try {
            if ($usarCurl) {
                & curl.exe -fL --retry 3 --progress-bar -o $temporal "$url/yellow_tripdata_$m.parquet"
                if ($LASTEXITCODE -ne 0) { throw "curl falló" }
            } else {
                Invoke-WebRequest -UseBasicParsing -Uri "$url/yellow_tripdata_$m.parquet" -OutFile $temporal -ErrorAction Stop
            }
            Move-Item -Force $temporal $destino -ErrorAction Stop
            $ok++
            Log ("   {0} ({1:N0} MB)" -f $m, ((Get-Item $destino).Length / 1MB))
        } catch {
            Remove-Item $temporal -ErrorAction SilentlyContinue
            $fallidos += $m
            Fallo "   $m no se pudo descargar"
        }
    }
    $mes = $mes.AddMonths(1)
}
Log "Descargados: $ok | ya existían: $saltados | fallidos: $($fallidos.Count) $($fallidos -join ' ')"
if ($fallidos.Count -gt 0) { exit 1 }
