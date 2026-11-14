"""Lectura de la capa bronce (solo lectura, nunca se modifica)."""
import re
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, functions as F

from .catalogos import COLUMNAS

PATRON = re.compile(r"yellow_tripdata_(\d{4})-(\d{2})\.parquet$")


def listar_archivos(ruta_bronce: Path) -> dict[str, Path]:
    """Devuelve {'2024-01': ruta, ...} ordenado por mes."""
    archivos = {}
    for ruta in sorted(ruta_bronce.rglob("yellow_tripdata_*.parquet")):
        m = PATRON.search(ruta.name)
        if m:
            archivos[f"{m.group(1)}-{m.group(2)}"] = ruta
    if not archivos:
        raise FileNotFoundError(f"No hay archivos yellow_tripdata_*.parquet en {ruta_bronce}")
    return archivos


def filtrar_meses(archivos: dict[str, Path], meses: str | None) -> dict[str, Path]:
    """meses: None = todos; '2024-01,2025-03' = lista; 'ultimos:3' = los N más recientes."""
    if not meses:
        return archivos
    if meses.startswith("ultimos:"):
        n = int(meses.split(":")[1])
        return dict(list(archivos.items())[-n:])
    pedidos = [m.strip() for m in meses.split(",") if m.strip()]
    faltan = [m for m in pedidos if m not in archivos]
    if faltan:
        raise ValueError(f"Meses sin archivo en bronce: {faltan}")
    return {m: archivos[m] for m in pedidos}


def leer_mes_unificado(spark: SparkSession, ruta: Path) -> DataFrame:
    """Lee un archivo mensual y lo lleva al esquema unificado de plata.

    Los archivos cambian de esquema (cbd_congestion_fee desde 2025-01,
    request_source desde 2026-06). Las columnas que no existen en un mes
    se crean como nulas para que todos los meses tengan las mismas columnas.
    """
    df = spark.read.parquet(str(ruta))
    existentes = {c.lower(): c for c in df.columns}
    seleccion = []
    for origen, destino, tipo in COLUMNAS:
        real = existentes.get(origen.lower())       # 'Airport_fee' vs 'airport_fee'
        col = F.col(real) if real else F.lit(None)
        seleccion.append(col.cast(tipo).alias(destino))
    return df.select(*seleccion)
