# Tablero en Metabase

El tablero "Dashboard TLC Taxis" tiene 5 pestañas (Resumen, Horas y días, Semanas y festivos,
Zonas, Formas de pago) y consulta solo las tablas `oro_*` del dataset `tlc_taxis` en BigQuery.

## Levantar Metabase con el tablero (automático)

`./scripts/montar_todo.sh` levanta Metabase con `docker compose up -d metabase` (servicio
`metabase` del `docker-compose.yml`, arranca solo con la máquina) y después corre
`configurar.py`, que:

1. crea tu usuario si Metabase es nuevo (pide correo y contraseña),
2. conecta la base BigQuery **TLC Taxis** (proyecto `festive-quanta-475416-k1`, dataset `tlc_taxis`)
   con la llave `credenciales/metabase-lectura.json` de la cuenta `plotly-lectura`
   (roles: Visualizador de datos y Usuario de trabajo de BigQuery),
3. oculta `plata_viajes` y `plata_descartes`,
4. crea el tablero desde `dashboard_tlc.json` si no existe.

Se puede volver a correr solo: `python3 metabase/configurar.py`. La llave no va en el repositorio.

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
