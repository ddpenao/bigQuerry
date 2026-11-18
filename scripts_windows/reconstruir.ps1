# Reconstruye una capa con un solo comando. Si le falta la capa anterior, la rehace primero.
#   scripts_windows\reconstruir.bat bronce      vuelve a bajar (o copia del respaldo) los meses que falten
#   scripts_windows\reconstruir.bat plata       rehace los meses de plata que falten (y bronce si hace falta)
#   scripts_windows\reconstruir.bat oro         rehace oro (y plata y bronce si hace falta)
#   scripts_windows\reconstruir.bat todo        revisa las tres capas y rehace lo que falte
# Opciones:
#   -Completo           en plata, reprocesa todos los meses aunque ya existan
#   -Desde RUTA         copia bronce desde esa carpeta (USB, respaldo) en vez de descargarla
#                       (también se puede fijar RESPALDO_BRONCE=RUTA en .env)
param([string]$Capa = "", [switch]$Completo, [string]$Desde = "")
. "$PSScriptRoot\comun.ps1"

if ($Capa -notin @("bronce", "plata", "oro", "todo")) {
    Get-Content $PSCommandPath | Select-Object -Skip 1 -First 8 | ForEach-Object { Write-Host ($_ -replace '^# ?', '') }
    exit 1
}
if (-not $Desde) { $Desde = Leer-Env "RESPALDO_BRONCE" }
$inicio = Get-Date
$script:PlataCambio = $false

function Construir-Bronce {
    $faltan = @(Meses-FaltantesBronce)
    if ($faltan.Count -eq 0) { Log "Bronce ya está completa"; return }
    Log "Bronce: faltan $($faltan.Count) meses"
    if ($Desde -and (Test-Path $Desde)) {
        Log "   copiando desde el respaldo $Desde"
        foreach ($m in $faltan) {
            $f = Get-ChildItem -Path $Desde -Recurse -Filter "yellow_tripdata_$m.parquet" -ErrorAction SilentlyContinue |
                 Where-Object { $_.Length -gt 0 } | Select-Object -First 1
            if ($f) {
                $carpeta = Join-Path (Ruta-Bronce) $m.Substring(0, 4)
                New-Item -ItemType Directory -Force -Path $carpeta | Out-Null
                Copy-Item -Path $f.FullName -Destination $carpeta
                Log "   $m copiado"
            } else {
                Fallo "   $m no está en el respaldo; se intentará descargar"
            }
        }
    }
    # Lo que siga faltando (sin respaldo o no estaba en él) se descarga de TLC
    foreach ($m in @(Meses-FaltantesBronce)) { & "$PSScriptRoot\descargar_bronce.ps1" $m $m }
    $siguen = @(Meses-FaltantesBronce)
    if ($siguen.Count -gt 0) { Fallo "Bronce sigue incompleta: $($siguen -join ' ')"; exit 1 }
    Log "Bronce completa"
}

function Construir-Plata {
    Construir-Bronce
    if ($Completo) {
        $script:PlataCambio = $true
        & "$PSScriptRoot\02_plata.ps1"
    } else {
        $meses = @(Meses-IncompletosPlata)
        if ($meses.Count -eq 0) { Log "Plata ya está completa (usa -Completo para reprocesarla entera)"; return }
        $script:PlataCambio = $true
        Log "Plata: se procesan los meses que faltan: $($meses -join ',')"
        & "$PSScriptRoot\02_plata.ps1" -Meses ($meses -join ',')
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Construir-Oro {
    & "$PSScriptRoot\03_oro.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Capa) {
    "bronce" { Construir-Bronce }
    "plata"  { Construir-Plata }
    "oro"    { Construir-Plata; Construir-Oro }
    "todo"   {
        Construir-Plata
        # Oro se rehace si le falta alguna tabla o si plata acaba de cambiar
        if ((@(Tablas-OroFaltantes).Count -gt 0) -or $script:PlataCambio) { Construir-Oro } else { Log "Oro ya está completa" }
    }
}
Log ("Reconstrucción de '{0}' terminada en {1:N0} min" -f $Capa, ((Get-Date) - $inicio).TotalMinutes)
& "$PSScriptRoot\estado.ps1"
