"""Consultas a BigQuery con protección de costo.

Reglas que se aplican a TODA consulta que haga el proyecto:
  1. Se rechaza cualquier SELECT * (también t.* y SELECT * EXCEPT).
  2. Antes de ejecutar se hace un dry run y se muestran los bytes estimados.
  3. Si el estimado pasa de BQ_LIMITE_CONSULTA_GB (5 GB), el script se detiene
     y no ejecuta: hay que revisar la consulta y autorizarla a mano.
  4. Aun así, la consulta real lleva maximum_bytes_billed como tope duro.

Uso por consola (dentro del contenedor):
  python -m tlc.bigquery_seguro "SELECT periodo, viajes FROM `proyecto.tlc_taxis.oro_kpi_mensual` LIMIT 5"
  python -m tlc.bigquery_seguro --solo-estimar "SELECT ..."
"""
import argparse
import logging
import re

from .config import CONFIG

GB = 10**9  # se usa GB decimal: 5 GB = 5.000.000.000 bytes (más estricto que GiB)

_SELECT_ASTERISCO = [
    re.compile(r"\bselect\s+(all\s+|distinct\s+)?([\w`]+\.)*\*", re.IGNORECASE),  # SELECT *, SELECT t.*
    re.compile(r",\s*([\w`]+\.)*\*\s*(,|\bfrom\b|\bexcept\b)", re.IGNORECASE),   # SELECT a, *, b
]


class ConsultaBloqueada(Exception):
    """La consulta no se ejecuta: incumple una regla o pasa el límite de bytes."""


def validar_sql(sql: str) -> None:
    sin_comentarios = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.DOTALL)
    for patron in _SELECT_ASTERISCO:
        if patron.search(sin_comentarios):
            raise ConsultaBloqueada("La consulta usa SELECT *. Escribe las columnas que necesitas.")


def estimar_bytes(cliente, sql: str) -> int:
    """Dry run: BigQuery calcula los bytes sin ejecutar ni cobrar."""
    from google.cloud import bigquery
    cfg = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    return int(cliente.query(sql, job_config=cfg).total_bytes_processed or 0)


def consulta_segura(cliente, sql: str, log: logging.Logger, solo_estimar: bool = False):
    """Valida, estima y (si está dentro del límite) ejecuta la consulta."""
    from google.cloud import bigquery
    validar_sql(sql)
    limite = int(CONFIG.bq_limite_consulta_gb * GB)
    estimado = estimar_bytes(cliente, sql)
    log.info("Dry run: %s bytes estimados (%.4f GB) | límite %.1f GB",
             f"{estimado:,}", estimado / GB, CONFIG.bq_limite_consulta_gb)
    if estimado > limite:
        raise ConsultaBloqueada(
            f"La consulta leería {estimado / GB:.2f} GB, más que el límite de "
            f"{CONFIG.bq_limite_consulta_gb} GB. Se detiene aquí: revísala y decide si la autorizas.")
    if solo_estimar:
        return None
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=limite)
    filas = cliente.query(sql, job_config=cfg).result()
    return filas


def crear_cliente():
    from google.cloud import bigquery
    if not CONFIG.gcp_proyecto:
        raise SystemExit("Falta GCP_PROYECTO en el archivo .env")
    return bigquery.Client(project=CONFIG.gcp_proyecto, location=CONFIG.bq_ubicacion)


def main() -> None:
    from .registro import configurar_logs
    parser = argparse.ArgumentParser(description="Consulta BigQuery con dry run obligatorio")
    parser.add_argument("sql")
    parser.add_argument("--solo-estimar", action="store_true")
    args = parser.parse_args()
    log = configurar_logs("consulta_bq", CONFIG.ruta_logs)
    try:
        filas = consulta_segura(crear_cliente(), args.sql, log, args.solo_estimar)
    except ConsultaBloqueada as e:
        log.error(str(e))
        raise SystemExit(2)
    if filas is not None:
        nombres = [c.name for c in filas.schema]
        print(" | ".join(nombres))
        for fila in filas:
            print(" | ".join(str(fila[n]) for n in nombres))


if __name__ == "__main__":
    main()
