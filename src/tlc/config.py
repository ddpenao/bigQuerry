"""Configuración central del pipeline.

Todo se lee de variables de entorno (archivo .env que carga docker compose),
con valores por defecto pensados para correr dentro del contenedor.
Cambiar un umbral aquí o en .env cambia la limpieza sin tocar el código.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(nombre: str, defecto: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    return valor if valor else defecto


@dataclass(frozen=True)
class Config:
    # ---------- Rutas (dentro del contenedor) ----------
    ruta_bronce: Path = Path(_env("RUTA_BRONCE_CONTENEDOR", "/datos/bronce"))
    ruta_plata: Path = Path(_env("RUTA_PLATA", "/app/plata"))
    ruta_oro: Path = Path(_env("RUTA_ORO", "/app/oro"))
    ruta_logs: Path = Path(_env("RUTA_LOGS", "/app/logs"))
    ruta_reportes: Path = Path(_env("RUTA_REPORTES", "/app/reportes"))
    ruta_zonas: Path = Path(_env("RUTA_ZONAS", "/app/datos_referencia/taxi_zone_lookup.csv"))

    # ---------- Spark local ----------
    spark_master: str = _env("SPARK_MASTER", "local[*]")
    spark_memoria: str = _env("SPARK_MEMORIA", "4g")
    spark_particiones_shuffle: int = int(_env("SPARK_PARTICIONES_SHUFFLE", "16"))

    # ---------- Reglas de limpieza (capa plata) ----------
    duracion_max_min: float = float(_env("DURACION_MAX_MIN", "360"))        # 6 horas
    distancia_max_millas: float = float(_env("DISTANCIA_MAX_MILLAS", "100"))
    velocidad_max_mph: float = float(_env("VELOCIDAD_MAX_MPH", "80"))
    monto_max_usd: float = float(_env("MONTO_MAX_USD", "1000"))
    pasajeros_max: int = int(_env("PASAJEROS_MAX", "9"))
    zona_min: int = 1
    zona_max: int = 265

    # ---------- Capa oro ----------
    # Meta del periodo = mismo periodo del año anterior x META_FACTOR (1.05 = +5 %)
    meta_factor: float = float(_env("META_FACTOR", "1.05"))

    # ---------- BigQuery ----------
    gcp_proyecto: str = _env("GCP_PROYECTO", "")
    bq_dataset: str = _env("BQ_DATASET", "tlc_taxis")
    bq_ubicacion: str = _env("BQ_UBICACION", "US")
    # Tope de bytes por consulta: si el dry run estima más, el script se detiene
    bq_limite_consulta_gb: float = float(_env("BQ_LIMITE_CONSULTA_GB", "5"))
    # Capa gratuita de almacenamiento de BigQuery (10 GB lógicos al mes)
    bq_limite_almacenamiento_gb: float = float(_env("BQ_LIMITE_ALMACENAMIENTO_GB", "10"))
    # Meses de plata a subir: vacío = no decidir aún (el script se detiene y pregunta),
    # "todos" = todos, o una lista "2026-06,2026-07,2026-08", o "ultimos:3"
    bq_plata_meses: str = _env("BQ_PLATA_MESES", "")
    # Cómo cobra BigQuery el almacenamiento del dataset:
    #   "logico" = tamaño sin comprimir (modelo por defecto de BigQuery)
    #   "fisico" = tamaño comprimido; plata ocupa ~10 veces menos y cabe más en los 10 GB gratis
    bq_modelo_almacenamiento: str = _env("BQ_MODELO_ALMACENAMIENTO", "logico").lower()

    def asegurar_carpetas(self) -> None:
        for ruta in (self.ruta_plata, self.ruta_oro, self.ruta_logs, self.ruta_reportes):
            ruta.mkdir(parents=True, exist_ok=True)


CONFIG = Config()
