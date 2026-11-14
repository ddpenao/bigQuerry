"""Creación de la sesión de Spark local (sin clúster, sin nube)."""
from pyspark.sql import SparkSession

from .config import CONFIG


def crear_spark(nombre_app: str) -> SparkSession:
    spark = (
        SparkSession.builder.master(CONFIG.spark_master)
        .appName(nombre_app)
        .config("spark.driver.memory", CONFIG.spark_memoria)
        .config("spark.sql.shuffle.partitions", CONFIG.spark_particiones_shuffle)
        # Las fechas de TLC son hora local de NYC sin zona; UTC evita que Spark las corra
        .config("spark.sql.session.timeZone", "UTC")
        # Solo se reemplazan las particiones (días) que se reescriben
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        # Timestamps en formato estándar (BigQuery no necesita INT96)
        .config("spark.sql.parquet.outputTimestampType", "TIMESTAMP_MICROS")
        .config("spark.sql.parquet.compression.codec", "zstd")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark
