"""PASO 3 - Carga de plata y oro a BigQuery sin costo.

- Solo load jobs desde archivos locales (gratis). Nada de INSERT ni streaming.
- Oro se carga como TABLAS (materializadas), nunca como vistas.
- Antes de subir plata se estima cuánto ocuparía en BigQuery. La capa gratuita
  da 10 GB de almacenamiento al mes; si la selección de meses pasa de ahí, el
  script se detiene y pide decidir (variable BQ_PLATA_MESES en .env).
- Las verificaciones usan metadatos de la tabla (no cuestan) y una consulta
  con dry run previo (ver bigquery_seguro.py).

Uso: python -m tlc.bigquery_carga               (oro + plata según BQ_PLATA_MESES)
     python -m tlc.bigquery_carga --solo-oro
     python -m tlc.bigquery_carga --solo-estimar   (no sube nada, solo calcula tamaños)
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .bigquery_seguro import GB, ConsultaBloqueada, consulta_segura, crear_cliente
from .config import CONFIG
from .registro import configurar_logs, paso

RUTA_VIAJES = CONFIG.ruta_plata / "viajes"
TAM_LOTE_MAX = 90 * 10**6          # cada archivo subido queda por debajo de ~90 MB
SALIDA_SIN_DECISION = 3            # código de salida cuando hay que preguntar al usuario


# --------------------------------------------------------------------------
# Plata: meses disponibles y tamaño estimado en BigQuery
# --------------------------------------------------------------------------
def dias_por_mes() -> dict[str, list[Path]]:
    meses: dict[str, list[Path]] = {}
    for carpeta in sorted(RUTA_VIAJES.glob("fecha=*")):
        meses.setdefault(carpeta.name[6:13], []).append(carpeta)
    return meses


def elegir_meses(disponibles: list[str], seleccion: str) -> list[str]:
    if seleccion == "todos":
        return disponibles
    if seleccion.startswith("ultimos:"):
        return disponibles[-int(seleccion.split(":")[1]):]
    pedidos = [m.strip() for m in seleccion.split(",") if m.strip()]
    faltan = [m for m in pedidos if m not in disponibles]
    if faltan:
        raise SystemExit(f"Meses que no están en plata: {faltan}")
    return pedidos


def bytes_logicos_por_fila(muestra: pa.Table) -> float:
    """Tamaño lógico que cobra BigQuery: 8 bytes por número/fecha, 1 por booleano,
    2 + largo del texto por string. Los nulos se cuentan como 0."""
    total = 0.0
    n = muestra.num_rows
    for nombre in muestra.column_names:
        col = muestra[nombre]
        validos = n - col.null_count
        if pa.types.is_string(col.type) or pa.types.is_large_string(col.type):
            largos = sum(len(v.as_py().encode()) for v in col if v.is_valid)
            total += (2 * validos + largos) / n
        elif pa.types.is_boolean(col.type):
            total += validos / n
        else:
            total += 8 * validos / n
    return total + 8  # + columna fecha (partición)


def estimar_plata(meses: dict[str, list[Path]], seleccion: list[str], log) -> int:
    filas = {m: sum(pq.ParquetFile(f).metadata.num_rows
                    for d in meses[m] for f in d.glob("*.parquet")) for m in seleccion}
    muestra = pq.ParquetFile(next(meses[seleccion[-1]][0].glob("*.parquet"))).read_row_group(0)
    por_fila = bytes_logicos_por_fila(muestra.slice(0, 20000))
    total_filas = sum(filas.values())
    estimado = int(total_filas * por_fila)
    log.info("Plata seleccionada: %d meses, %s filas, ~%.0f bytes/fila → ~%.2f GB lógicos en BigQuery",
             len(seleccion), f"{total_filas:,}", por_fila, estimado / GB)
    return estimado


# --------------------------------------------------------------------------
# Cargas
# --------------------------------------------------------------------------
def cargar_archivo(cliente, ruta: Path, tabla: str, disposicion: str, log, particion: str | None = None,
                   clustering: list[str] | None = None, formato: str = "PARQUET", esquema=None):
    from google.cloud import bigquery
    cfg = bigquery.LoadJobConfig(source_format=getattr(bigquery.SourceFormat, formato),
                                 write_disposition=disposicion)
    if formato == "CSV":
        cfg.skip_leading_rows = 1
        cfg.schema = esquema
    if particion:
        cfg.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field=particion)
    if clustering:
        cfg.clustering_fields = clustering
    with ruta.open("rb") as f:
        job = cliente.load_table_from_file(f, tabla, job_config=cfg)
    job.result()  # espera; lanza error si el load job falla
    log.info("   load job %s → %s (%s filas)", job.job_id, tabla.split(".")[-1], f"{job.output_rows:,}")


def cargar_oro(cliente, dataset: str, log) -> list[str]:
    tablas = []
    for carpeta in sorted((CONFIG.ruta_oro / "parquet").glob("oro_*")):
        archivo = next(carpeta.glob("part-*.parquet"))
        tabla = f"{dataset}.{carpeta.name}"
        cargar_archivo(cliente, archivo, tabla, "WRITE_TRUNCATE", log)
        tablas.append(tabla)
    if not tablas:
        raise SystemExit("No hay tablas en oro/parquet. Ejecuta primero scripts/03_oro.sh")
    return tablas


def lotes_del_mes(dias: list[Path]) -> list[list[Path]]:
    """Agrupa días en lotes de hasta ~90 MB para no subir archivos gigantes."""
    lotes, actual, tam = [], [], 0
    for d in dias:
        t = sum(f.stat().st_size for f in d.glob("*.parquet"))
        if actual and tam + t > TAM_LOTE_MAX:
            lotes.append(actual); actual, tam = [], 0
        actual.append(d); tam += t
    if actual:
        lotes.append(actual)
    return lotes


def cargar_plata(cliente, dataset: str, meses: dict[str, list[Path]], seleccion: list[str], log) -> str:
    tabla = f"{dataset}.plata_viajes"
    cliente.delete_table(tabla, not_found_ok=True)   # recarga limpia (borrar tablas no cuesta)
    log.info("Tabla %s reiniciada; se cargan %d meses", tabla, len(seleccion))
    tmp = Path(tempfile.mkdtemp(prefix="plata_bq_"))
    try:
        for mes in seleccion:
            for i, lote in enumerate(lotes_del_mes(meses[mes]), 1):
                partes = []
                for dia in lote:
                    t = pq.read_table(dia)
                    fecha = pa.array([dia.name[6:]] * t.num_rows).cast(pa.date32())
                    partes.append(t.append_column("fecha", fecha))
                archivo = tmp / f"{mes}_{i}.parquet"
                pq.write_table(pa.concat_tables(partes), archivo, compression="zstd")
                cargar_archivo(cliente, archivo, tabla, "WRITE_APPEND", log,
                               particion="fecha", clustering=["forma_pago_id", "proveedor_id"])
                archivo.unlink()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    descartes = CONFIG.ruta_plata / "_calidad" / "descartes_por_mes.csv"
    if descartes.exists():
        from google.cloud import bigquery
        esquema = [bigquery.SchemaField("mes", "STRING"), bigquery.SchemaField("etapa", "STRING"),
                   bigquery.SchemaField("motivo", "STRING"), bigquery.SchemaField("filas", "INT64")]
        cargar_archivo(cliente, descartes, f"{dataset}.plata_descartes", "WRITE_TRUNCATE", log,
                       formato="CSV", esquema=esquema)
    return tabla


def verificar(cliente, dataset: str, tablas: list[str], log) -> None:
    """Conteos desde metadatos (gratis) y una consulta de prueba con dry run."""
    for t in tablas:
        info = cliente.get_table(t)
        log.info("   %-40s %12s filas  %8.3f GB", t.split(".")[-1], f"{info.num_rows:,}", info.num_bytes / GB)
    sql = (f"SELECT periodo, viajes, viajes_var_pct_mes_ant, viajes_cumplimiento_pct "
           f"FROM `{dataset}.oro_kpi_mensual` ORDER BY periodo DESC LIMIT 3")
    for fila in consulta_segura(cliente, sql, log):
        log.info("   %s | viajes %s | var mes %s %% | cumplimiento %s %%",
                 fila["periodo"], f"{fila['viajes']:,}", fila["viajes_var_pct_mes_ant"],
                 fila["viajes_cumplimiento_pct"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga plata y oro a BigQuery con load jobs")
    parser.add_argument("--solo-oro", action="store_true")
    parser.add_argument("--solo-estimar", action="store_true", help="No sube nada; solo estima tamaños")
    parser.add_argument("--plata-meses", default=None, help="Sobrescribe BQ_PLATA_MESES")
    args = parser.parse_args()

    log = configurar_logs("03_bigquery", CONFIG.ruta_logs)
    meses = dias_por_mes()
    disponibles = list(meses)
    seleccion_txt = args.plata_meses or CONFIG.bq_plata_meses
    limite_alm = int(CONFIG.bq_limite_almacenamiento_gb * GB)

    # --- Decisión sobre plata antes de tocar BigQuery ---
    seleccion = []
    if not args.solo_oro:
        if not disponibles:
            raise SystemExit("plata/viajes está vacío. Ejecuta primero scripts/02_plata.sh")
        estimado_total = estimar_plata(meses, disponibles, log)
        if not seleccion_txt:
            cabe = "cabe" if estimado_total <= limite_alm else "NO cabe"
            log.warning("Plata completa ocuparía ~%.1f GB: %s en los %.0f GB gratis de BigQuery.",
                        estimado_total / GB, cabe, CONFIG.bq_limite_almacenamiento_gb)
            log.warning("Decide qué meses subir y ponlo en .env como BQ_PLATA_MESES, por ejemplo:")
            log.warning("   BQ_PLATA_MESES=ultimos:3      (los 3 meses más recientes)")
            log.warning("   BQ_PLATA_MESES=2026-06,2026-07,2026-08")
            log.warning("   BQ_PLATA_MESES=todos          (solo si aceptas pagar el exceso)")
            log.warning("O sube solo oro: scripts/04_bigquery.sh --solo-oro")
            raise SystemExit(SALIDA_SIN_DECISION)
        seleccion = elegir_meses(disponibles, seleccion_txt)
        estimado = estimar_plata(meses, seleccion, log)
        if estimado > limite_alm and os.environ.get("BQ_ACEPTO_COSTO_ALMACENAMIENTO", "") != "si":
            log.error("La selección ocuparía ~%.2f GB > %.0f GB gratis. Reduce BQ_PLATA_MESES "
                      "(o define BQ_ACEPTO_COSTO_ALMACENAMIENTO=si si aceptas el costo).",
                      estimado / GB, CONFIG.bq_limite_almacenamiento_gb)
            raise SystemExit(SALIDA_SIN_DECISION)

    if args.solo_estimar:
        log.info("Solo estimación: no se subió nada.")
        return

    cliente = crear_cliente()
    dataset = f"{CONFIG.gcp_proyecto}.{CONFIG.bq_dataset}"
    from google.cloud import bigquery
    ds = bigquery.Dataset(dataset)
    ds.location = CONFIG.bq_ubicacion
    cliente.create_dataset(ds, exists_ok=True)
    log.info("Dataset %s listo (%s)", dataset, CONFIG.bq_ubicacion)

    tablas = []
    with paso(log, "Cargar oro (tablas materializadas)"):
        tablas += cargar_oro(cliente, dataset, log)
    if seleccion:
        with paso(log, f"Cargar plata ({len(seleccion)} meses)"):
            tablas.append(cargar_plata(cliente, dataset, meses, seleccion, log))
    with paso(log, "Verificar"):
        try:
            verificar(cliente, dataset, tablas, log)
        except ConsultaBloqueada as e:
            log.error(str(e))
            raise SystemExit(2)


if __name__ == "__main__":
    main()
