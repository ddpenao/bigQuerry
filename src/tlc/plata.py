"""PASO 1 - Capa plata: limpieza de bronce.

Se procesa un archivo mensual a la vez. Así el portátil no tiene que tener los
~120 millones de filas en memoria, y si algo falla se puede repetir solo un mes.

Orden de la limpieza en cada mes:
  1. Unificar esquema, estandarizar nombres y corregir tipos.
  2. Quitar filas idénticas repetidas.
  3. Quitar anulaciones: la fila negativa y su gemela positiva (misma clave y monto).
  4. Quitar duplicados por clave de negocio (se conserva la de mayor monto).
  5. Validar rangos y atípicos (cada fila descartada queda con un único motivo).
  6. Tratar nulos y agregar descripciones de los códigos.
  7. Guardar en Parquet particionado por fecha de recogida.

Cada descarte se registra en plata/_calidad/descartes_por_mes.csv.

Uso: python -m tlc.plata                      (todos los meses)
     python -m tlc.plata --meses 2024-01,2025-06
     python -m tlc.plata --meses ultimos:2
"""
import argparse
import csv
from pathlib import Path

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, Window, functions as F

from .bronce import filtrar_meses, leer_mes_unificado, listar_archivos
from .catalogos import CLAVE_VIAJE, COLUMNAS, COMPONENTES_MONTO, FORMA_PAGO, PROVEEDOR, TIPO_TARIFA
from .config import CONFIG
from .registro import configurar_logs, paso
from .sesion_spark import crear_spark

RUTA_VIAJES = CONFIG.ruta_plata / "viajes"
RUTA_CALIDAD = CONFIG.ruta_plata / "_calidad"
ARCHIVO_DESCARTES = RUTA_CALIDAD / "descartes_por_mes.csv"

COLUMNAS_FINALES = [
    "id_viaje", "anio", "mes", "fecha_hora_recogida", "fecha_hora_llegada", "duracion_min",
    "proveedor_id", "proveedor", "tarifa_id", "tipo_tarifa", "forma_pago_id", "forma_pago",
    "num_pasajeros", "distancia_millas", "zona_origen_id", "zona_destino_id",
    "distrito_origen", "distrito_destino", "almacenado_reenviado", "origen_solicitud",
    *COMPONENTES_MONTO, "monto_total", "componente_ajustado", "fecha",
]


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def mapa_a_columna(diccionario: dict, columna: str, prefijo_otro: str) -> F.Column:
    """Convierte un código en su descripción usando un diccionario de catálogos."""
    mapa = F.create_map(*[x for k, v in diccionario.items() for x in (F.lit(k), F.lit(v))])
    return F.coalesce(mapa[F.col(columna)],
                      F.concat(F.lit(f"{prefijo_otro} ("), F.col(columna).cast("string"), F.lit(")")),
                      F.lit("Desconocido"))


def leer_zonas(spark: SparkSession, log) -> DataFrame | None:
    """Tabla de zonas de TLC (LocationID -> distrito). Es opcional."""
    if not CONFIG.ruta_zonas.exists():
        log.warning("No está %s: plata quedará sin distrito_origen/distrito_destino. "
                    "Ejecuta scripts/00_preparar.sh para descargarla.", CONFIG.ruta_zonas)
        return None
    zonas = spark.read.option("header", True).csv(str(CONFIG.ruta_zonas))
    distrito = F.when(F.col("Borough").isin("Unknown", "N/A") | F.col("Borough").isNull(), "Desconocido") \
                .when(F.col("Borough") == "EWR", "EWR (Newark)").otherwise(F.col("Borough"))
    zonas = zonas.select(F.col("LocationID").cast("smallint").alias("zona_id"), distrito.alias("distrito"))
    log.info("Tabla de zonas cargada: %d zonas", zonas.count())
    return F.broadcast(zonas)


# --------------------------------------------------------------------------
# Limpieza de un mes
# --------------------------------------------------------------------------
def limpiar_mes(spark: SparkSession, mes: str, ruta: Path, zonas: DataFrame | None, log):
    """Devuelve (DataFrame limpio, lista de registros de descarte)."""
    registros = []

    def registrar(etapa: str, motivo: str, filas: int):
        registros.append({"mes": mes, "etapa": etapa, "motivo": motivo, "filas": int(filas)})
        if filas:
            log.info("   %s | %-28s | %s filas", mes, motivo, f"{filas:,}")

    # 1. Esquema unificado + id_viaje (hash de todas las columnas originales)
    bruto = leer_mes_unificado(spark, ruta)
    bruto = bruto.withColumn("id_viaje", F.xxhash64(*[c for _, c, _ in COLUMNAS]))
    bruto = bruto.persist(StorageLevel.MEMORY_AND_DISK)
    n_leidas = bruto.count()
    registrar("lectura", "filas_leidas", n_leidas)

    # 2. Filas idénticas repetidas
    sin_dup = bruto.dropDuplicates([c for _, c, _ in COLUMNAS]).persist(StorageLevel.MEMORY_AND_DISK)
    n1 = sin_dup.count()
    registrar("duplicados", "duplicado_exacto", n_leidas - n1)
    bruto.unpersist()

    # 3. Anulaciones: fila negativa + gemela positiva con la misma clave y el mismo monto absoluto
    con_abs = sin_dup.withColumn("_monto_abs", F.round(F.abs("monto_total"), 2))
    clave_monto = CLAVE_VIAJE + ["_monto_abs"]
    negativas = con_abs.filter(F.col("monto_total") < 0)
    positivas = con_abs.filter(F.col("monto_total") > 0)
    neg_por_clave = negativas.groupBy(clave_monto).agg(F.count("*").alias("_n_neg"))
    orden = Window.partitionBy(clave_monto).orderBy(F.col("id_viaje"))
    pares_positivos = (positivas.join(neg_por_clave, clave_monto, "inner")
                       .withColumn("_rn", F.row_number().over(orden))
                       .filter(F.col("_rn") <= F.col("_n_neg"))
                       .select("id_viaje")).persist(StorageLevel.MEMORY_AND_DISK)
    n_pares = pares_positivos.count()
    n_neg_total = negativas.count()
    n_neg_con_par = negativas.join(positivas.select(clave_monto).distinct(), clave_monto, "left_semi").count()
    registrar("anulaciones", "anulacion_negativa_con_par", n_neg_con_par)
    registrar("anulaciones", "anulacion_par_positivo", n_pares)
    registrar("anulaciones", "negativo_sin_par", n_neg_total - n_neg_con_par)

    sin_anul = (con_abs.filter(F.col("monto_total").isNull() | (F.col("monto_total") >= 0))
                .join(pares_positivos, "id_viaje", "left_anti")
                .drop("_monto_abs"))

    # 4. Duplicados por clave de negocio. Caso típico (2024-09/10, 2026): el mismo viaje
    #    llega dos veces, una con forma de pago 0 y otra con tarjeta. Se conserva primero
    #    el que tiene forma de pago conocida y, si empatan, el de mayor monto.
    claves_rep = sin_anul.groupBy(CLAVE_VIAJE).count().filter("count > 1").drop("count")
    pago_desconocido = F.coalesce(F.col("forma_pago_id").isin(0, 5), F.lit(True))
    orden_dup = Window.partitionBy(CLAVE_VIAJE).orderBy(
        pago_desconocido.asc(), F.col("monto_total").desc_nulls_last(), "id_viaje")
    sobrantes = (sin_anul.join(claves_rep, CLAVE_VIAJE, "left_semi")
                 .withColumn("_rn", F.row_number().over(orden_dup))
                 .filter("_rn > 1").select("id_viaje")).persist(StorageLevel.MEMORY_AND_DISK)
    registrar("duplicados", "duplicado_por_clave", sobrantes.count())
    sin_dup_clave = sin_anul.join(sobrantes, "id_viaje", "left_anti")

    # 5. Validación de rangos y atípicos (primer motivo que aplique)
    c = CONFIG
    recogida = F.col("fecha_hora_recogida")
    duracion = (F.unix_timestamp(F.col("fecha_hora_llegada").cast("timestamp"))
                - F.unix_timestamp(recogida.cast("timestamp"))) / 60.0
    validado = sin_dup_clave.withColumn("duracion_min", F.round(duracion, 2))
    horas = F.col("duracion_min") / 60.0

    motivo = (
        F.when(recogida.isNull() | F.col("fecha_hora_llegada").isNull() | F.col("monto_total").isNull()
               | F.col("zona_origen_id").isNull() | F.col("zona_destino_id").isNull(), "nulos_criticos")
        .when(F.date_format(recogida, "yyyy-MM") != F.lit(mes), "fecha_fuera_del_mes_del_archivo")
        .when(F.col("duracion_min") <= 0, "duracion_cero_o_negativa")
        .when(F.col("duracion_min") > c.duracion_max_min, "duracion_excesiva")
        .when(F.col("distancia_millas").isNull() | (F.col("distancia_millas") <= 0), "distancia_cero")
        .when(F.col("distancia_millas") > c.distancia_max_millas, "distancia_excesiva")
        .when(F.col("distancia_millas") / horas > c.velocidad_max_mph, "velocidad_imposible")
        .when(F.col("monto_total") <= 0, "monto_cero")
        .when(F.col("monto_total") > c.monto_max_usd, "monto_excesivo")
        .when(F.coalesce(F.col("propina"), F.lit(0.0)) > F.col("monto_total"), "propina_mayor_que_total")
        .when(~F.col("zona_origen_id").between(c.zona_min, c.zona_max)
              | ~F.col("zona_destino_id").between(c.zona_min, c.zona_max), "zona_invalida")
    )
    validado = validado.withColumn("_motivo", motivo).persist(StorageLevel.MEMORY_AND_DISK)
    for fila in validado.filter(F.col("_motivo").isNotNull()).groupBy("_motivo").count().collect():
        registrar("validacion", fila["_motivo"], fila["count"])
    limpio = validado.filter(F.col("_motivo").isNull()).drop("_motivo")

    # 6. Tratamiento sin descartar el viaje.
    # Componentes negativos con total positivo: casi todos son viajes con forma de pago 0
    # de 2025 con tarifa_base negativa (p. ej. -4,75). El viaje y su total son válidos,
    # así que se conserva; el componente inconsistente pasa a nulo y la fila queda marcada.
    hay_negativo = F.lit(False)
    for comp in COMPONENTES_MONTO:
        hay_negativo = hay_negativo | F.coalesce(F.col(comp) < 0, F.lit(False))
    limpio = limpio.withColumn("componente_ajustado", hay_negativo)
    for comp in COMPONENTES_MONTO:
        limpio = limpio.withColumn(comp, F.when(F.col(comp) >= 0, F.col(comp)))
    tratado = limpio.persist(StorageLevel.MEMORY_AND_DISK)
    registrar("tratamiento", "componente_negativo_a_nulo", tratado.filter("componente_ajustado").count())
    limpio = tratado

    limpio = (
        limpio
        # 0 pasajeros o más del máximo no es un dato creíble: queda como nulo (no se descarta el viaje)
        .withColumn("num_pasajeros", F.when(F.col("num_pasajeros").between(1, c.pasajeros_max),
                                            F.col("num_pasajeros")))
        .withColumn("tarifa_id", F.coalesce(F.col("tarifa_id"), F.lit(99)).cast("smallint"))
        .withColumn("almacenado_reenviado", F.when(F.col("almacenado_reenviado") == "Y", True)
                                             .when(F.col("almacenado_reenviado") == "N", False))
        # El recargo CBD no existía antes de 2025: en esos meses vale 0, no "desconocido"
        .withColumn("recargo_cbd", F.when(F.col("recargo_cbd").isNull() & (recogida < F.lit("2025-01-01")), 0.0)
                                    .otherwise(F.col("recargo_cbd")))
        .withColumn("proveedor", mapa_a_columna(PROVEEDOR, "proveedor_id", "Otro"))
        .withColumn("tipo_tarifa", mapa_a_columna(TIPO_TARIFA, "tarifa_id", "Otra"))
        .withColumn("forma_pago", mapa_a_columna(FORMA_PAGO, "forma_pago_id", "Otra"))
        .withColumn("fecha", F.to_date(recogida))
        .withColumn("anio", F.year(recogida).cast("smallint"))
        .withColumn("mes", F.month(recogida).cast("smallint"))
    )
    if zonas is not None:
        limpio = (limpio
                  .join(zonas.withColumnRenamed("zona_id", "zona_origen_id")
                        .withColumnRenamed("distrito", "distrito_origen"), "zona_origen_id", "left")
                  .join(zonas.withColumnRenamed("zona_id", "zona_destino_id")
                        .withColumnRenamed("distrito", "distrito_destino"), "zona_destino_id", "left"))
        for col in ("distrito_origen", "distrito_destino"):
            limpio = limpio.withColumn(col, F.coalesce(F.col(col), F.lit("Desconocido")))
    else:
        limpio = (limpio.withColumn("distrito_origen", F.lit(None).cast("string"))
                        .withColumn("distrito_destino", F.lit(None).cast("string")))

    limpio_final = limpio.select(*COLUMNAS_FINALES)
    return limpio_final, registros, [sin_dup, pares_positivos, sobrantes, validado, tratado]


def guardar_registros(nuevos: list[dict], log) -> None:
    """Actualiza el CSV de descartes reemplazando los meses reprocesados."""
    RUTA_CALIDAD.mkdir(parents=True, exist_ok=True)
    meses_nuevos = {r["mes"] for r in nuevos}
    previos = []
    if ARCHIVO_DESCARTES.exists():
        with ARCHIVO_DESCARTES.open(encoding="utf-8") as f:
            previos = [r for r in csv.DictReader(f) if r["mes"] not in meses_nuevos]
    todos = sorted(previos + nuevos, key=lambda r: (r["mes"], r["etapa"], r["motivo"]))
    with ARCHIVO_DESCARTES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["mes", "etapa", "motivo", "filas"])
        w.writeheader()
        w.writerows(todos)
    log.info("Registro de descartes actualizado: %s", ARCHIVO_DESCARTES)


def escribir_resumen(log) -> None:
    """Resumen legible de descartes para el reporte y el README (reportes/descartes_resumen.md)."""
    with ARCHIVO_DESCARTES.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    leidas = sum(int(r["filas"]) for r in filas if r["motivo"] == "filas_leidas")
    por_motivo: dict[str, int] = {}
    tratados: dict[str, int] = {}
    for r in filas:
        if r["motivo"] == "filas_leidas":
            continue
        destino = tratados if r["etapa"] == "tratamiento" else por_motivo
        destino[r["motivo"]] = destino.get(r["motivo"], 0) + int(r["filas"])
    descartadas = sum(por_motivo.values())
    meses = sorted({r["mes"] for r in filas})
    lineas = [
        "# Descartes de la capa plata", "",
        f"Meses procesados: {len(meses)} ({meses[0]} → {meses[-1]})", "",
        f"| Concepto | Filas | % de las leídas |", "|---|---:|---:|",
        f"| Leídas de bronce | {leidas:,} | 100,00 |",
    ]
    for m, n in sorted(por_motivo.items(), key=lambda x: -x[1]):
        lineas.append(f"| Descartadas: {m} | {n:,} | {100 * n / leidas:.2f} |")
    lineas.append(f"| **Total descartadas** | **{descartadas:,}** | **{100 * descartadas / leidas:.2f}** |")
    lineas.append(f"| **Quedan en plata** | **{leidas - descartadas:,}** | **{100 * (leidas - descartadas) / leidas:.2f}** |")
    if tratados:
        lineas += ["", "Filas que se conservan pero con un dato corregido:", "",
                   "| Tratamiento | Filas | % de las leídas |", "|---|---:|---:|"]
        lineas += [f"| {m} | {n:,} | {100 * n / leidas:.2f} |" for m, n in tratados.items()]
    destino = CONFIG.ruta_reportes / "descartes_resumen.md"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log.info("Leídas %s | descartadas %s (%.2f %%) | quedan %s",
             f"{leidas:,}", f"{descartadas:,}", 100 * descartadas / leidas, f"{leidas - descartadas:,}")
    log.info("Resumen en %s", destino)


def main() -> None:
    parser = argparse.ArgumentParser(description="Construye la capa plata")
    parser.add_argument("--meses", default=None, help="'2024-01,2024-02' o 'ultimos:3' (por defecto todos)")
    args = parser.parse_args()

    CONFIG.asegurar_carpetas()
    log = configurar_logs("01_plata", CONFIG.ruta_logs)
    spark = crear_spark("tlc-plata")
    archivos = filtrar_meses(listar_archivos(CONFIG.ruta_bronce), args.meses)
    log.info("Meses a procesar: %d (%s → %s)", len(archivos), next(iter(archivos)), list(archivos)[-1])
    zonas = leer_zonas(spark, log)

    for i, (mes, ruta) in enumerate(archivos.items(), 1):
        with paso(log, f"[{i}/{len(archivos)}] Limpiar {mes}"):
            limpio, registros, temporales = limpiar_mes(spark, mes, ruta, zonas, log)
            (limpio.repartition("fecha")
                   .write.mode("overwrite").partitionBy("fecha")
                   .parquet(str(RUTA_VIAJES)))
            inicio = F.to_date(F.lit(f"{mes}-01"))
            escritas = spark.read.parquet(str(RUTA_VIAJES)).filter(
                (F.col("fecha") >= inicio) & (F.col("fecha") < F.add_months(inicio, 1))).count()
            leidas = registros[0]["filas"]
            log.info("   %s | escritas en plata %s de %s (%.2f %% conservado)",
                     mes, f"{escritas:,}", f"{leidas:,}", 100 * escritas / leidas)
            registros.append({"mes": mes, "etapa": "resultado", "motivo": "filas_en_plata", "filas": escritas})
            # Los conteos de descartes deben cuadrar con lo escrito
            descartadas = sum(r["filas"] for r in registros if r["etapa"] not in ("lectura", "resultado", "tratamiento"))
            if leidas - descartadas != escritas:
                log.warning("   %s | descuadre: leídas-descartadas=%s, escritas=%s",
                            mes, f"{leidas - descartadas:,}", f"{escritas:,}")
            guardar_registros([r for r in registros if r["motivo"] != "filas_en_plata"], log)
            for t in temporales:
                t.unpersist()

    escribir_resumen(log)
    spark.stop()


if __name__ == "__main__":
    main()
