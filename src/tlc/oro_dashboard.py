"""PASO 2b - Tablas oro extra para el dashboard de Data Studio.

Salen de la capa plata y se guardan igual que el resto de oro (Parquet + CSV):

  oro_hora_mensual      mes x día de la semana x hora: viajes, distancia, duración y velocidad
  oro_viajes_diarios    un registro por día, con día de la semana y festivo
  oro_viajes_semanales  semanas (lunes a domingo) comparadas con el promedio de las 8 anteriores
  oro_zona_mensual      mes x zona de recogida: viajes, ingresos, % del mes y ranking
  oro_pago_mensual      mes x forma de pago: viajes, propinas y variación frente al año anterior
  oro_zona_mapa         como oro_zona_mensual, con una dirección de texto para ubicarla en el mapa
  oro_distrito_mapa     mes x borough, con el condado para el mapa relleno de Data Studio

Pico / Valle: una semana es "Pico" si su promedio diario supera en 10 % o más al
promedio de las 8 semanas completas anteriores y "Valle" si queda 10 % o más por debajo.

Uso: python -m tlc.oro_dashboard
"""
from datetime import date

from pyspark.sql import DataFrame, SparkSession, Window, functions as F

from .config import CONFIG
from .oro import DEC_MONTO, guardar, pct, variacion_pct
from .registro import configurar_logs, paso
from .sesion_spark import crear_spark

UMBRAL_PICO_PCT = 10
SEMANAS_REFERENCIA = 8

DIAS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}

# Festivos federales de EE. UU. en su fecha real (no la observada)
FESTIVOS = {
    "2024-01-01": "Año Nuevo", "2024-01-15": "Martin Luther King", "2024-02-19": "Día de los Presidentes",
    "2024-05-27": "Memorial Day", "2024-06-19": "Juneteenth", "2024-07-04": "4 de julio",
    "2024-09-02": "Día del Trabajo", "2024-10-14": "Día de Colón", "2024-11-11": "Día de los Veteranos",
    "2024-11-28": "Acción de Gracias", "2024-12-25": "Navidad",
    "2025-01-01": "Año Nuevo", "2025-01-20": "Martin Luther King", "2025-02-17": "Día de los Presidentes",
    "2025-05-26": "Memorial Day", "2025-06-19": "Juneteenth", "2025-07-04": "4 de julio",
    "2025-09-01": "Día del Trabajo", "2025-10-13": "Día de Colón", "2025-11-11": "Día de los Veteranos",
    "2025-11-27": "Acción de Gracias", "2025-12-25": "Navidad",
    "2026-01-01": "Año Nuevo", "2026-01-19": "Martin Luther King", "2026-02-16": "Día de los Presidentes",
    "2026-05-25": "Memorial Day", "2026-06-19": "Juneteenth", "2026-07-04": "4 de julio",
    "2026-09-07": "Día del Trabajo", "2026-10-12": "Día de Colón", "2026-11-11": "Día de los Veteranos",
    "2026-11-26": "Acción de Gracias", "2026-12-25": "Navidad",
}

# Borough -> condado, que Data Studio reconoce como "Subdivisión del país (2.º nivel)"
CONDADOS = {
    "Manhattan": "New York County, New York, United States",
    "Brooklyn": "Kings County, New York, United States",
    "Queens": "Queens County, New York, United States",
    "Bronx": "Bronx County, New York, United States",
    "Staten Island": "Richmond County, New York, United States",
    "EWR": "Essex County, New Jersey, United States",
}


def mapa(dic: dict, columna: str) -> F.Column:
    """Convierte un diccionario de Python en una expresión CASE de Spark."""
    return F.create_map(*[F.lit(x) for kv in dic.items() for x in kv])[F.col(columna)]


def con_dia_semana(df: DataFrame, col_fecha: str = "fecha") -> DataFrame:
    """Agrega dia_semana_num (1 = lunes ... 7 = domingo), dia_semana y tipo_dia."""
    num = ((F.dayofweek(col_fecha) + 5) % 7 + 1).cast("smallint")
    return (df.withColumn("dia_semana_num", num)
              .withColumn("dia_semana", mapa(DIAS, "dia_semana_num"))
              .withColumn("tipo_dia", F.when(F.col("dia_semana_num") >= 6, "Fin de semana")
                                       .otherwise("Entre semana")))


def con_periodo(df: DataFrame) -> DataFrame:
    return df.withColumn("periodo", F.make_date("anio", "mes", F.lit(1)))


def leer_zonas(spark: SparkSession) -> DataFrame:
    zonas = spark.read.option("header", True).csv(str(CONFIG.ruta_zonas))
    distrito = F.when(F.col("Borough").isin("Unknown", "N/A") | F.col("Borough").isNull(), "Desconocido") \
                .otherwise(F.col("Borough"))
    return F.broadcast(zonas.select(F.col("LocationID").cast("smallint").alias("zona_id"),
                                    F.col("Zone").alias("zona"), distrito.alias("distrito")))


# --------------------------------------------------------------------------
# Tablas
# --------------------------------------------------------------------------
def tabla_dia_hora(plata: DataFrame) -> DataFrame:
    """Base fecha x hora; de aquí salen la tabla por hora y la diaria."""
    return (plata.withColumn("hora", F.hour("fecha_hora_recogida").cast("smallint"))
                 .groupBy("fecha", "anio", "mes", "hora")
                 .agg(F.count("*").alias("viajes"),
                      F.sum("monto_total").alias("ingresos"),
                      F.sum("distancia_millas").alias("distancia_millas_total"),
                      F.sum("duracion_min").alias("duracion_min_total"))
                 .cache())


def tabla_hora_mensual(dia_hora: DataFrame) -> DataFrame:
    df = con_dia_semana(dia_hora)
    df = (df.groupBy("anio", "mes", "dia_semana_num", "dia_semana", "tipo_dia", "hora")
            .agg(F.sum("viajes").alias("viajes"), F.sum("ingresos").alias("ingresos"),
                 F.sum("distancia_millas_total").alias("distancia_millas_total"),
                 F.sum("duracion_min_total").alias("duracion_min_total"),
                 F.countDistinct("fecha").alias("dias")))
    return (con_periodo(df)
            .withColumn("viajes_promedio_por_dia", (F.col("viajes") / F.col("dias")).cast(DEC_MONTO))
            .withColumn("velocidad_promedio_mph",
                        (F.col("distancia_millas_total") / F.col("duracion_min_total") * 60).cast(DEC_MONTO)))


def tabla_viajes_diarios(dia_hora: DataFrame, spark: SparkSession) -> DataFrame:
    festivos = spark.createDataFrame([(date.fromisoformat(k), v) for k, v in FESTIVOS.items()],
                                     "fecha date, festivo string")
    df = (dia_hora.groupBy("fecha", "anio", "mes")
                  .agg(F.sum("viajes").alias("viajes"), F.sum("ingresos").alias("ingresos"))
                  .join(F.broadcast(festivos), "fecha", "left")
                  .withColumn("es_festivo", F.col("festivo").isNotNull()))
    return con_periodo(con_dia_semana(df))


def tabla_viajes_semanales(diarios: DataFrame) -> DataFrame:
    sem = (diarios.withColumn("semana_inicio", F.to_date(F.date_trunc("week", "fecha")))
                  .groupBy("semana_inicio")
                  .agg(F.count("*").alias("dias"),
                       F.sum("viajes").alias("viajes"),
                       F.sum("ingresos").alias("ingresos"),
                       F.concat_ws(", ", F.array_sort(F.collect_list("festivo"))).alias("festivos"))
                  .withColumn("semana_completa", F.col("dias") == 7)
                  .withColumn("es_semana_festivo", F.col("festivos") != "")
                  .withColumn("festivos", F.when(F.col("festivos") != "", F.col("festivos")))
                  .withColumn("viajes_promedio_diario", (F.col("viajes") / F.col("dias")).cast(DEC_MONTO)))

    # Referencia: promedio diario de las 8 semanas completas anteriores
    previas = Window.orderBy("semana_inicio").rowsBetween(-SEMANAS_REFERENCIA, -1)
    completas = (sem.filter("semana_completa")
                    .withColumn("_n", F.count("viajes_promedio_diario").over(previas))
                    .withColumn("_ref", F.avg("viajes_promedio_diario").over(previas))
                    .select("semana_inicio",
                            F.when(F.col("_n") == SEMANAS_REFERENCIA, F.col("_ref")).cast(DEC_MONTO)
                             .alias("viajes_promedio_8_semanas_previas")))
    sem = sem.join(completas, "semana_inicio", "left")
    var = variacion_pct(F.col("viajes_promedio_diario"), F.col("viajes_promedio_8_semanas_previas"))
    return (sem.withColumn("viajes_var_pct_vs_8_semanas", var)
               .withColumn("clasificacion",
                           F.when(var.isNull(), "Sin referencia")
                            .when(var >= UMBRAL_PICO_PCT, "Pico")
                            .when(var <= -UMBRAL_PICO_PCT, "Valle")
                            .otherwise("Normal"))
               .withColumn("anio", F.year("semana_inicio")).withColumn("mes", F.month("semana_inicio")))


def tabla_zona_mensual(plata: DataFrame, zonas: DataFrame) -> DataFrame:
    df = (plata.groupBy("anio", "mes", F.col("zona_origen_id").alias("zona_id"))
               .agg(F.count("*").alias("viajes"), F.sum("monto_total").alias("ingresos"))
               .join(zonas, "zona_id", "left")
               .fillna({"zona": "Desconocida", "distrito": "Desconocido"}))
    por_mes = Window.partitionBy("anio", "mes")
    return (con_periodo(df)
            .withColumn("viajes_participacion_pct", pct(F.col("viajes"), F.sum("viajes").over(por_mes)))
            .withColumn("ranking_mes", F.dense_rank().over(por_mes.orderBy(F.desc("viajes"))).cast("smallint")))


def tabla_pago_mensual(plata: DataFrame) -> DataFrame:
    df = (plata.groupBy("anio", "mes", "forma_pago")
               .agg(F.count("*").alias("viajes"),
                    F.sum("monto_total").alias("ingresos"),
                    F.sum("propina").alias("propinas_total"),
                    F.sum("tarifa_base").alias("tarifa_base_total"),
                    F.count(F.when(F.col("propina") > 0, True)).alias("viajes_con_propina")))
    df = (con_periodo(df)
          .withColumn("propina_promedio_usd", (F.col("propinas_total") / F.col("viajes")).cast(DEC_MONTO))
          .withColumn("propina_pct_sobre_tarifa", pct(F.col("propinas_total"), F.col("tarifa_base_total")))
          .withColumn("viajes_con_propina_pct", pct(F.col("viajes_con_propina"), F.col("viajes")))
          .withColumn("viajes_participacion_pct",
                      pct(F.col("viajes"), F.sum("viajes").over(Window.partitionBy("periodo")))))
    # Mismo mes del año anterior: se une por fecha, no por posición
    anterior = df.select(F.add_months("periodo", 12).alias("periodo"), "forma_pago",
                         F.col("viajes").alias("viajes_anio_ant"),
                         F.col("propina_promedio_usd").alias("propina_promedio_anio_ant"))
    return (df.join(anterior, ["periodo", "forma_pago"], "left")
              .withColumn("viajes_var_pct_anio_ant", variacion_pct(F.col("viajes"), F.col("viajes_anio_ant")))
              .withColumn("propina_promedio_var_pct_anio_ant",
                          variacion_pct(F.col("propina_promedio_usd"), F.col("propina_promedio_anio_ant"))))


def tabla_zona_mapa(zona_mensual: DataFrame) -> DataFrame:
    return zona_mensual.withColumn(
        "zona_ubicacion",
        F.when(F.col("distrito").isin("Desconocido", "N/A", "Unknown"), None)
         .otherwise(F.concat_ws(", ", "zona", "distrito", F.lit("New York"))))


def tabla_distrito_mapa(zona_mensual: DataFrame) -> DataFrame:
    df = (zona_mensual.groupBy("periodo", "anio", "mes", "distrito")
                      .agg(F.sum("viajes").alias("viajes"), F.sum("ingresos").alias("ingresos")))
    return (df.withColumn("condado", mapa(CONDADOS, "distrito"))
              .withColumn("viajes_participacion_pct",
                          pct(F.col("viajes"), F.sum("viajes").over(Window.partitionBy("periodo")))))


def main() -> None:
    CONFIG.asegurar_carpetas()
    log = configurar_logs("02b_oro_dashboard", CONFIG.ruta_logs)
    spark = crear_spark("tlc-oro-dashboard")

    with paso(log, "Leer plata"):
        plata = spark.read.parquet(str(CONFIG.ruta_plata / "viajes")).select(
            "fecha", "anio", "mes", "fecha_hora_recogida", "distancia_millas", "duracion_min",
            "zona_origen_id", "forma_pago", "monto_total", "propina", "tarifa_base")
        if not CONFIG.ruta_zonas.exists():
            raise SystemExit(f"Falta {CONFIG.ruta_zonas}. Ejecuta scripts/00_preparar.sh")
        zonas = leer_zonas(spark)

    with paso(log, "Calcular tablas del dashboard"):
        dia_hora = tabla_dia_hora(plata)
        hora_m = tabla_hora_mensual(dia_hora)
        diarios = tabla_viajes_diarios(dia_hora, spark).cache()
        semanales = tabla_viajes_semanales(diarios)
        zona_m = tabla_zona_mensual(plata, zonas).cache()
        pago_m = tabla_pago_mensual(plata)

    with paso(log, "Guardar (Parquet + CSV)"):
        guardar(hora_m, "oro_hora_mensual", ["periodo", "dia_semana_num", "hora"], log)
        guardar(diarios, "oro_viajes_diarios", ["fecha"], log)
        guardar(semanales, "oro_viajes_semanales", ["semana_inicio"], log)
        guardar(zona_m, "oro_zona_mensual", ["periodo", "ranking_mes", "zona_id"], log)
        guardar(pago_m, "oro_pago_mensual", ["periodo", "forma_pago"], log)
        guardar(tabla_zona_mapa(zona_m), "oro_zona_mapa", ["periodo", "ranking_mes", "zona_id"], log)
        guardar(tabla_distrito_mapa(zona_m), "oro_distrito_mapa", ["periodo", "distrito"], log)

    spark.stop()


if __name__ == "__main__":
    main()
