# Guarda la imagen Docker en un archivo para usarla sin internet.
# En el otro equipo: docker load -i tlc-pipeline-imagen.tar
. "$PSScriptRoot\comun.ps1"
Log "Exportando tlc-pipeline:1.0 ..."
& docker save -o tlc-pipeline-imagen.tar tlc-pipeline:1.0
Salir-SiFallo $LASTEXITCODE "La exportación"
Log ("Listo: tlc-pipeline-imagen.tar ({0:N0} MB)" -f ((Get-Item "tlc-pipeline-imagen.tar").Length / 1MB))
