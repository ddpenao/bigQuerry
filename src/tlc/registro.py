"""Logs del pipeline: consola + archivo por etapa en /app/logs."""
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configurar_logs(etapa: str, carpeta: Path) -> logging.Logger:
    """Crea un logger que escribe en pantalla y en logs/<etapa>_<fecha>.log."""
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{etapa}_{datetime.now():%Y%m%d_%H%M%S}.log"
    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.setLevel(logging.INFO)
    for handler in (logging.StreamHandler(), logging.FileHandler(archivo, encoding="utf-8")):
        handler.setFormatter(logging.Formatter(FORMATO, "%Y-%m-%d %H:%M:%S"))
        raiz.addHandler(handler)
    # Spark y py4j hablan demasiado; solo dejamos sus advertencias
    for ruidoso in ("py4j", "pyspark", "urllib3", "google"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    log = logging.getLogger(etapa)
    log.info("Log de la etapa en %s", archivo)
    return log


@contextmanager
def paso(log: logging.Logger, descripcion: str):
    """Marca inicio y fin de un paso con su duración."""
    inicio = time.time()
    log.info("▶ %s", descripcion)
    try:
        yield
    except Exception:
        log.exception("✖ Falló: %s", descripcion)
        raise
    log.info("✔ %s (%.1f s)", descripcion, time.time() - inicio)
