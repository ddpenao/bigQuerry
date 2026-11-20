# Pipeline TLC: taxis amarillos de Nueva York (bronce → plata → oro → BigQuery)

Toma los viajes de taxi amarillo de NYC publicados por la TLC, de enero de 2024 a agosto de 2026 (32 archivos Parquet, 119.595.677 filas). Con PySpark en modo local los limpia, los resume en tablas pequeñas con indicadores en porcentaje y los deja listos para un dashboard en Looker Studio.

Todo corre en tu computador dentro de un contenedor Docker. La nube solo se usa para BigQuery, con load jobs, que son gratuitos. No hay Kafka ni streaming: es procesamiento por lotes.

```
TLC/  (capa bronce, solo lectura)       TLC_pipeline/  (este repositorio)
├── 2024/yellow_tripdata_2024-01.parquet ├── scripts/        ← lo que se ejecuta
├── 2025/...                             ├── src/tlc/        ← código PySpark
└── 2026/...                             ├── plata/          ← capa plata (no va a git)
                                         ├── oro/csv/        ← capa oro en CSV (sí va a git)
                                         ├── oro/parquet/    ← capa oro en Parquet
                                         ├── reportes/       ← reconocimiento y descartes
                                         ├── docs/           ← diseño del dashboard
                                         ├── logs/           ← un log por ejecución
                                         ├── Dockerfile, docker-compose.yml, plantilla_env.txt
                                         └── credenciales/   ← llave de Google (no va a git)
```

## Requisitos

- Linux con Docker Engine y el plugin `docker compose`
- git
- Unos 8 GB de RAM y 6 GB libres en disco (la capa plata ocupa unos 3 GB)
- La carpeta `TLC` al lado de `TLC_pipeline`. Si está en otro lugar, cambia `RUTA_BRONCE_HOST` en `.env`

No necesitas instalar Python, Java ni Spark en el equipo: la imagen Docker los trae.

## Para compañeros: clonar y ejecutar en otro PC

La guía paso a paso, para Linux y Windows, está en [`docs/guia_companeros.md`](docs/guia_companeros.md).

En Linux necesitas Docker, git y curl (en Windows, mira la sección siguiente). Los datos no están en el repositorio porque pesan 2 GB; el primer script los descarga de la página de TLC.

```bash
cd ~/Documentos
git clone https://github.com/ddpenao/bigQuerry.git
cd bigQuerry

./scripts/descargar_bronce.sh   # baja los 32 Parquet a ../TLC (~2 GB, una sola vez)
./scripts/00_preparar.sh        # .env, tabla de zonas, imagen Docker (~2 min)
./scripts/ejecutar_todo.sh      # reconocimiento → plata → oro (10 a 35 min según el equipo)
```

Al terminar quedan las tablas en `oro/csv/` y el resumen de limpieza en `reportes/`. Si solo quieres ver resultados sin ejecutar nada, `oro/csv/` ya viene en el repositorio.

Si `00_preparar.sh` falla con `docker-credential-desktop: executable file not found`, es un resto de Docker Desktop en `~/.docker/config.json`. Se corrige quitando la línea `"credsStore": "desktop"` de ese archivo.

La carga a BigQuery (paso 3) es opcional y cada quien la hace con su propio proyecto de Google Cloud y su propia llave en `credenciales/gcp-key.json`.

### En Windows

Los scripts de Windows están en `scripts_windows/` (PowerShell, con un `.bat` por paso). Los de `scripts/` son para Linux. Se necesita **Docker Desktop** abierto (que diga *Engine running*) y **Git para Windows**. Desde una terminal (cmd o PowerShell):

```bat
cd %USERPROFILE%\Documents
git clone https://github.com/ddpenao/bigQuerry.git
cd bigQuerry

rem Baja los 32 Parquet a ..\TLC (~2 GB, una sola vez)
scripts_windows\descargar_bronce.bat
rem Crea .env, descarga la tabla de zonas y construye la imagen Docker
scripts_windows\00_preparar.bat
rem Reconocimiento -> plata -> oro
scripts_windows\ejecutar_todo.bat
```

Las demás opciones funcionan igual que en Linux:
- `scripts_windows\02_plata.bat 2026-08` procesa un solo mes.
- `scripts_windows\ejecutar_todo.bat -Demo` reprocesa solo el último mes.
- `scripts_windows\04_bigquery.bat --solo-estimar` calcula tamaños sin subir nada.

Los `.bat` ejecutan PowerShell con `-ExecutionPolicy Bypass`, así que no hay que cambiar la política de seguridad del equipo. En Windows la capa plata tarda más que en Linux porque Docker escribe en una carpeta de Windows; cuenten con 20 a 40 minutos.

## Orden de ejecución

```bash
cd ~/Documentos/TLC_pipeline

./scripts/00_preparar.sh        # una vez: .env, carpetas, tabla de zonas, imagen Docker, git
./scripts/01_reconocimiento.sh  # PASO 0: esquemas + muestra de 1.000 filas → reportes/reconocimiento.md
./scripts/02_plata.sh           # PASO 1: limpieza → plata/viajes (particionado por fecha)
./scripts/03_oro.sh             # PASO 2: tablas con porcentajes → oro/parquet y oro/csv
./scripts/04_bigquery.sh --solo-estimar   # PASO 3a: cuánto ocuparía en BigQuery (no sube nada)
./scripts/04_bigquery.sh        # PASO 3b: carga con load jobs
./scripts/06_compartir_git.sh "mensaje"   # commit y push
```

Para correr del paso 0 al 2 de una vez: `./scripts/ejecutar_todo.sh`. Si agregas `--con-bigquery`, al final también hace la carga.

**Tiempos de referencia.** En la prueba con 2 núcleos y 4 GB para Spark, la capa plata tardó unos 60 segundos por mes (~33 min en total) y la capa oro menos de 2 minutos. Con más núcleos baja.

### Si algo falla a mitad de camino

La capa plata procesa un mes a la vez y cada mes reemplaza solo sus propias particiones. Si se corta en el mes 20, puedes repetir solo lo que falta:

```bash
./scripts/02_plata.sh --meses 2025-09,2025-10,2025-11
```

## Borrar y reconstruir una capa

Cualquier capa se puede borrar y volver a crear con un comando. `reconstruir` revisa qué falta y lo rehace en orden: si a plata le falta bronce, primero recupera bronce. Solo rehace lo que falta; si se borraron 10 días de agosto, procesa solo agosto.

| Qué se borró | Linux | Windows |
|---|---|---|
| Ver qué tiene cada capa | `./scripts/estado.sh` | `scripts_windows\estado.bat` |
| Bronce (`../TLC`) | `./scripts/reconstruir.sh bronce` | `scripts_windows\reconstruir.bat bronce` |
| Plata (`plata/`) | `./scripts/reconstruir.sh plata` | `scripts_windows\reconstruir.bat plata` |
| Oro (`oro/`) | `./scripts/reconstruir.sh oro` | `scripts_windows\reconstruir.bat oro` |
| Varias o no se sabe | `./scripts/reconstruir.sh todo` | `scripts_windows\reconstruir.bat todo` |

Bronce se recupera copiándola de un respaldo, si lo hay, o descargándola de la TLC (2 GB). Para no depender de internet en clase, guarda una copia de `TLC` en una USB y pon su ruta en `.env` como `RESPALDO_BRONCE=/media/usuario/USB/TLC` (en Windows, `RESPALDO_BRONCE=E:\TLC`). También se puede indicar en el comando con `--desde RUTA` en Linux o `-Desde RUTA` en Windows. Para reprocesar plata entera aunque esté completa: `--completo` en Linux o `-Completo` en Windows.

Tiempos de referencia en Linux con 2 núcleos: bronce desde una USB, segundos; oro, menos de un minuto; un mes de plata, 20 a 90 segundos según el equipo.

## PASO 0: lo que se encontró en bronce

El detalle está en `reportes/reconocimiento.md`.

- **Tres versiones de esquema.** 2024 tiene 19 columnas. Desde 2025-01 aparece `cbd_congestion_fee` (cargo por congestión del sur de Manhattan) y desde 2026-06 `request_source`.
- **Un bloque de viajes sin metadatos.** El 19,58 % de las filas tiene `payment_type = 0` y en todas ellas vienen nulos `passenger_count`, `RatecodeID`, `store_and_fwd_flag`, `congestion_surcharge` y `Airport_fee`.
- **Duplicados.** No hay filas idénticas, pero sí anulaciones: una fila con montos negativos y su gemela positiva con la misma clave. En enero de 2024 fueron 30.672 pares.
- **Fechas imposibles.** Hay viajes con fechas desde 2001 y 780 viajes que no corresponden al mes de su archivo.
- **Sin ID de viaje.** La clave candidata es `(proveedor, recogida, llegada, zona_origen, zona_destino)`. En plata se agrega `id_viaje`, un hash de toda la fila.

## PASO 1: capa plata

Código: `src/tlc/plata.py`. Se procesa mes por mes, en este orden:

1. **Tipos y nombres.** Se unifican los tres esquemas (las columnas que faltan quedan nulas) y se renombra a snake_case en español: `tpep_pickup_datetime` → `fecha_hora_recogida`, `total_amount` → `monto_total`, etc. Los códigos pasan a enteros y las fechas a timestamp.
2. **Filas idénticas.** Se quitan.
3. **Anulaciones.** Cada fila negativa se empareja con una positiva de la misma clave y el mismo monto absoluto, y se quitan las dos. Las negativas sin pareja también salen.
4. **Duplicados por clave.** Si quedan dos viajes con la misma clave, se conserva el que tiene forma de pago conocida y, si empatan, el de mayor monto. El caso típico, sobre todo en 2026, es el mismo viaje del proveedor 1 reportado una vez con pago 0 y otra con tarjeta.
5. **Validación de rangos.** Cada fila descartada queda con un solo motivo, el primero que aplique:

| Motivo | Regla (ajustable en `.env`) |
|---|---|
| `nulos_criticos` | sin fecha de recogida o llegada, sin monto o sin zona |
| `fecha_fuera_del_mes_del_archivo` | la recogida no cae en el mes del archivo (incluye las fechas de 2001) |
| `duracion_cero_o_negativa` / `duracion_excesiva` | duración ≤ 0 min o > 360 min |
| `distancia_cero` / `distancia_excesiva` | distancia ≤ 0 o > 100 millas |
| `velocidad_imposible` | más de 80 mph de promedio |
| `monto_cero` / `monto_excesivo` | total ≤ 0 o > 1.000 USD |
| `propina_mayor_que_total` | propina mayor que el total cobrado |
| `zona_invalida` | zona fuera de 1–265 |

6. **Nulos que se tratan sin descartar la fila:**
   - pasajeros = 0 o mayor que 9 → nulo;
   - `tarifa_id` nulo → 99 ("Desconocida");
   - `recargo_cbd` en 2024 → 0, porque ese cargo no existía;
   - `forma_pago` 0 → "Desconocido";
   - un cargo negativo con total positivo → ese cargo queda nulo y la fila se marca con `componente_ajustado = true`. Son 1,8 millones de viajes, casi todos de enero a noviembre de 2025 con pago 0 y `tarifa_base` negativa. Si se descartaran, 2025 perdería entre 3 y 5 % de sus viajes y el crecimiento de 2026 saldría inflado.

   El 19,6 % sin metadatos se conserva, porque sacarlo le quitaría una quinta parte de los viajes a todos los totales.
7. **Columnas derivadas y guardado.** Se agregan las descripciones de los códigos (proveedor, tipo de tarifa, forma de pago), los distritos de origen y destino (con la tabla de zonas), `duracion_min`, `anio` y `mes`. Se guarda en `plata/viajes/fecha=AAAA-MM-DD/`.

**Resultado con los 32 meses:**

| | Filas | % |
|---|---:|---:|
| Leídas de bronce | 119.595.677 | 100,00 |
| Distancia 0 | 2.837.483 | 2,37 |
| Anulaciones (negativa + gemela positiva) | 2.779.274 | 2,32 |
| Duración ≤ 0 | 931.219 | 0,78 |
| Negativas sin pareja | 355.263 | 0,30 |
| Duplicados por clave | 177.465 | 0,15 |
| Otras reglas (duración/distancia excesiva, velocidad, montos, fechas, idénticas) | 87.242 | 0,07 |
| **Quedan en plata** | **112.427.731** | **94,01** |

**Registro de descartes.** Queda en `plata/_calidad/descartes_por_mes.csv`, con mes, etapa, motivo y filas, y el resumen en `reportes/descartes_resumen.md`. El script comprueba en cada mes que leídas − descartadas = escritas.

## PASO 2: capa oro

Código: `src/tlc/oro.py`. Son tablas pequeñas, cada una en `oro/parquet/<tabla>/` y en `oro/csv/<tabla>.csv`.

| Tabla | Grano | Uso |
|---|---|---|
| `oro_kpi_mensual` | mes | indicadores de la ciudad mes a mes |
| `oro_kpi_anual` | año | resumen anual; 2026 se compara contra ene-ago 2025 |
| `oro_categoria_mensual` | mes × dimensión × categoría | participación y crecimiento por categoría |
| `oro_categoria_anual` | año × dimensión × categoría | ranking de crecimiento por categoría |
| `oro_calidad_mensual` | mes × motivo | % de filas descartadas, para mostrar la limpieza |
| `oro_hora_mensual` | mes × día de la semana × hora | demanda por hora y velocidad promedio (congestión) |
| `oro_viajes_diarios` | día | viajes por día, día de la semana y festivo |
| `oro_viajes_semanales` | semana | promedio diario frente a las 8 semanas anteriores; Pico (+10 %) o Valle (−10 %) |
| `oro_zona_mensual` | mes × zona de recogida | viajes, ingresos, % del mes y ranking |
| `oro_pago_mensual` | mes × forma de pago | propina promedio, % sobre tarifa y variación vs. año anterior |
| `oro_zona_mapa` / `oro_distrito_mapa` | mes × zona / borough | ubicación en texto para los mapas de Data Studio |

Las siete últimas las calcula `src/tlc/oro_dashboard.py`; `03_oro` las genera después de las demás.

Las dimensiones son `forma_pago`, `tipo_tarifa`, `proveedor` y `distrito_origen`. Esta última solo aparece si existe `datos_referencia/taxi_zone_lookup.csv`, que `00_preparar.sh` descarga de la TLC.

Cada métrica (viajes e ingresos) viene con sus porcentajes:

| Campo | Cálculo |
|---|---|
| `*_var_pct_mes_ant` | (mes / mes anterior − 1) × 100 |
| `*_var_pct_anio_ant` | (mes / mismo mes del año anterior − 1) × 100 |
| `*_participacion_pct` | categoría / total del periodo × 100 |
| `*_meta` | mismo periodo del año anterior × 1,05 |
| `*_cumplimiento_pct` | valor / meta × 100 |
| `*_crec_acum_anual_pct` | acumulado ene→mes / mismo acumulado del año anterior − 1 |
| `*_crec_desde_inicio_pct` | (mes / ene-2024 − 1) × 100 |

Las comparaciones se hacen por fecha y no por posición de fila, así que un mes faltante no corre los cálculos. 2024 no tiene meta ni variación anual porque no hay 2023 en los datos.

## PASO 3: BigQuery a costo cero

Código: `src/tlc/bigquery_carga.py` y `src/tlc/bigquery_seguro.py`.

**Reglas que cumple el código:**
- Solo load jobs desde archivos locales, que BigQuery no cobra. No hay `INSERT` ni streaming.
- Se suben plata y oro. Oro se carga como tablas, nunca como vistas.
- Toda consulta pasa primero por un dry run que muestra los bytes estimados. Si pasa de 5 GB, se detiene sin ejecutar. Además, la consulta real lleva `maximum_bytes_billed` como tope.
- `SELECT *` está bloqueado (también `t.*` y `SELECT * EXCEPT`).
- Las verificaciones de conteo usan los metadatos de la tabla, que no generan costo.

**Ojo con el almacenamiento.** La capa gratuita de BigQuery es de 10 GB al mes, y la capa plata completa ocupa bastante más en BigQuery, porque allá se cuenta sin comprimir. Por eso el script calcula el tamaño antes de subir y se detiene si no has decidido qué meses cargar. La decisión va en `.env`:

```
BQ_PLATA_MESES=ultimos:3                    # los 3 meses más recientes
BQ_PLATA_MESES=2026-06,2026-07,2026-08      # meses concretos
```

Los dashboards no dependen de esto: la capa oro se calcula con los 32 meses en Spark local y sube completa.

**Configuración de Google Cloud (una sola vez):**
1. En https://console.cloud.google.com crea un proyecto. Sin tarjeta queda en *modo sandbox*: gratis, con 10 GB de almacenamiento y 1 TB de consultas al mes, y las tablas vencen a los 60 días.
2. En *IAM y administración → Cuentas de servicio* crea una cuenta, por ejemplo `tlc-pipeline`, con los roles **Editor de datos de BigQuery** y **Usuario de trabajos de BigQuery**.
3. En esa cuenta entra a *Claves → Agregar clave → JSON* y guarda el archivo como `credenciales/gcp-key.json`.
4. En `.env` completa `GCP_PROYECTO=<id-del-proyecto>` y `BQ_PLATA_MESES`.
5. Ejecuta `./scripts/04_bigquery.sh --solo-estimar` y después `./scripts/04_bigquery.sh`.

Para consultar desde la terminal (con dry run incluido):

```bash
./scripts/05_consulta_bq.sh "SELECT periodo, viajes, viajes_var_pct_anio_ant FROM \`MI_PROYECTO.tlc_taxis.oro_kpi_mensual\` ORDER BY periodo"
```

## PASO 4: dashboard

El diseño de los 5 gráficos está en [`docs/dashboard_looker.md`](docs/dashboard_looker.md): scorecards de variación, barras apiladas al 100 %, línea de variación mensual, crecimiento por categoría y avance frente a la meta. Para cada uno se indica la tabla oro y los campos.

## Compartir con git

```bash
./scripts/06_compartir_git.sh "Capas plata y oro" https://github.com/USUARIO/tlc-pipeline.git   # la primera vez
./scripts/06_compartir_git.sh "Ajuste de reglas"                                                # después
```

Se suben el código, Docker, los scripts, la documentación, los reportes y `oro/csv`. No se suben la capa plata (pesa varios GB), los Parquet de oro, los logs, `.env` ni la llave de Google. Quien clone el repositorio ejecuta `00_preparar.sh` con su propia carpeta `TLC` y regenera todo.

## Para la presentación en clase

1. **Llevar la imagen sin depender de internet.** En casa ejecuta `./scripts/exportar_imagen.sh`. En el equipo de la clase: `docker load -i tlc-pipeline-imagen.tar.gz`.
2. **Llevar la capa plata ya procesada**, para no esperar media hora.
3. En vivo: `./scripts/ejecutar_todo.sh --demo`. Hace el reconocimiento, reprocesa solo el último mes en plata (1 a 2 minutos) y recalcula oro completo.
4. Muestra `reportes/descartes_resumen.md`, una tabla de `oro/csv` y el dashboard.

## Problemas comunes

| Síntoma | Solución |
|---|---|
| `permission denied ... docker.sock` | `sudo usermod -aG docker $USER` y volver a iniciar sesión |
| `java.lang.OutOfMemoryError` | sube `SPARK_MEMORIA` en `.env` (hasta ~60 % de tu RAM) o cierra otros programas mientras corre |
| La imagen base no descarga | en el Dockerfile cambia `IMAGEN_BASE` a `python:3.12-slim-bookworm` |
| Oro sale sin `distrito_origen` | falta `datos_referencia/taxi_zone_lookup.csv`: vuelve a correr `00_preparar.sh` con internet |
| `04_bigquery.sh` termina con código 3 | es a propósito: falta decidir `BQ_PLATA_MESES` |
