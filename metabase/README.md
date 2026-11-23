# Tablero en Metabase

El tablero "Dashboard TLC Taxis" tiene 5 pestañas (Resumen, Horas y días, Semanas y festivos,
Zonas, Formas de pago) y consulta solo las tablas `oro_*` del dataset `tlc_taxis` en BigQuery.

## Levantar Metabase

```bash
mkdir -p ~/metabase-data
docker run -d -p 3001:3000 -v ~/metabase-data:/metabase-data \
  -e MB_DB_FILE=/metabase-data/metabase.db --name metabase metabase/metabase:v0.65.6.3
```

Abrir http://localhost:3001 y agregar la base BigQuery con el nombre **TLC Taxis**:
proyecto `festive-quanta-475416-k1`, dataset `tlc_taxis`, llave JSON de la cuenta de servicio
`plotly-lectura` (roles: Visualizador de datos y Usuario de trabajo de BigQuery).
La llave no va en el repositorio.

## Exportar e importar el tablero

`dashboard_tlc.json` guarda el SQL, el tipo de gráfico, las pestañas y la posición de cada pregunta.

```bash
cd metabase
python3 exportar.py --email tu@correo.com      # Metabase -> dashboard_tlc.json
python3 importar.py --email tu@correo.com      # dashboard_tlc.json -> Metabase nuevo
```

Ambos piden la contraseña de Metabase en la terminal.

## Respaldo en memoria USB

```bash
./scripts/respaldo_memoria.sh /media/$USER/NOMBRE_MEMORIA
```

Copia el repositorio (todas las ramas), las tablas oro, la carpeta `~/metabase-data`
y las imágenes de Docker. Las instrucciones para restaurar quedan en `LEEME.txt` dentro de la memoria.
