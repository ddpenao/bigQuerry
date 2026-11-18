"""PASO 2 - Capa oro: tablas pequeñas para dashboards, todo con porcentajes.

Se lee plata una sola vez y se arma un "cubo" mensual (mes x categorías).
De ese cubo, que cabe de sobra en memoria, salen todas las tablas:

  oro_kpi_mensual        un registro por mes (total de la ciudad)
  oro_kpi_anual          un registro por año
  oro_categoria_mensual  mes x dimensión x categoría (formato largo)
  oro_categoria_anual    año x dimensión x categoría
  oro_calidad_mensual    % de filas descartadas por motivo y mes

Métricas en porcentaje (para viajes e ingresos):
  *_var_pct_mes_ant        variación % frente al mes anterior
  *_var_pct_anio_ant       variación % frente al mismo mes del año anterior
  *_participacion_pct      peso % de la categoría en el total del periodo
  *_meta                   mismo periodo del año anterior x META_FACTOR (1,05 = +5 %)
  *_cumplimiento_pct       valor / meta x 100
  *_crec_acum_anual_pct    acumulado del año hasta el mes vs. mismo acumulado del año anterior
  *_crec_desde_inicio_pct  variación % frente al primer mes con datos (ene-2024)

Uso: python -m tlc.oro
"""
import csv
import shutil
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, Window, functions as F

from .catalogos import DIMENSIONES_ORO
from .config import CONFIG
from .registro import configurar_logs, paso
from .sesion_spark import crear_spark

METRICAS = ["viajes", "ingresos"]
DEC_MONTO = "decimal(18,2)"
DEC_PCT = "decimal(12,2)"


# --------------------------------------------------------------------------
# Cálculos en porcentaje reutilizables
# --------------------------------------------------------------------------
def pct(numerador: F.Column, denominador: F.Column) -> F.Column:
    """(num / den) x 100, nulo si el denominador es nulo o cero."""
    return F.when(denominador.isNull() | (denominador == 0), None) \
            .otherwise(numerador / denominador * 100).cast(DEC_PCT)


def variacion_pct(actual: F.Column, anterior: F.Column) -> F.Column:
    """(actual / anterior - 1) x 100."""
    return F.when(anterior.isNull() | (anterior == 0), None) \
            .otherwise((actual / anterior - 1) * 100).cast(DEC_PCT)


def agregar_metricas_mensuales(df: DataFrame, grupo: list[str], con_participacion: bool) -> DataFrame:
    """Agrega variaciones, meta, cumplimiento y crecimiento acumulado a una tabla mensual.

    df debe traer: periodo (primer día del mes), anio, mes, columnas de `grupo` y METRICAS.
    Las comparaciones se hacen uniendo por fecha (periodo - 1 mes, periodo - 12 meses),
    no por posición, para que un mes faltante no desplace la comparación.
    """
    def desplazado(meses: int, sufijo: str) -> DataFrame:
        return df.select(*grupo, F.add_months("periodo", meses).alias("periodo"),
                         *[F.col(m).alias(f"{m}_{sufijo}") for m in METRICAS])

    ytd = Window.partitionBy(*grupo, "anio").orderBy("mes").rowsBetween(Window.unboundedPreceding, 0)
    inicio = Window.partitionBy(*grupo).orderBy("periodo")
    out = df
    for m in METRICAS:
        out = out.withColumn(f"_{m}_ytd", F.sum(m).over(ytd)) \
                 .withColumn(f"_{m}_inicio", F.first(m).over(inicio))
    out = (out.join(desplazado(1, "mes_ant"), grupo + ["periodo"], "left")
              .join(desplazado(12, "anio_ant"), grupo + ["periodo"], "left"))
    ytd_ant = out.select(*grupo, F.add_months("periodo", 12).alias("periodo"),
                         *[F.col(f"_{m}_ytd").alias(f"_{m}_ytd_ant") for m in METRICAS])
    out = out.join(ytd_ant, grupo + ["periodo"], "left")

    if con_participacion:
        total_periodo = Window.partitionBy(*[g for g in grupo if g != "categoria"], "periodo")
    for m in METRICAS:
        meta = F.col(f"{m}_anio_ant") * CONFIG.meta_factor
        out = (out
               .withColumn(f"{m}_var_pct_mes_ant", variacion_pct(F.col(m), F.col(f"{m}_mes_ant")))
               .withColumn(f"{m}_var_pct_anio_ant", variacion_pct(F.col(m), F.col(f"{m}_anio_ant")))
               .withColumn(f"{m}_meta", meta.cast(DEC_MONTO))
               .withColumn(f"{m}_cumplimiento_pct", pct(F.col(m), meta))
               .withColumn(f"{m}_crec_acum_anual_pct",
                           variacion_pct(F.col(f"_{m}_ytd"), F.col(f"_{m}_ytd_ant")))
               .withColumn(f"{m}_crec_desde_inicio_pct",
                           variacion_pct(F.col(m), F.col(f"_{m}_inicio"))))
        if con_participacion:
            out = out.withColumn(f"{m}_participacion_pct", pct(F.col(m), F.sum(m).over(total_periodo)))
    # Se borran auxiliares; se conserva {m}_anio_ant porque la tabla anual lo usa
    auxiliares = [c for c in out.columns if c.startswith("_")] + [f"{m}_mes_ant" for m in METRICAS]
    return out.drop(*auxiliares)


def agregar_metricas_anuales(mensual: DataFrame, grupo: list[str], con_participacion: bool) -> DataFrame:
    """Resume la tabla mensual por año. La comparación con el año anterior usa
    solo los meses presentes en el año actual (2026 llega hasta agosto, así que
    se compara contra ene-ago de 2025 y no contra el año completo)."""
    anual = mensual.groupBy(*grupo, "anio").agg(
        F.countDistinct("mes").alias("meses_con_datos"),
        *[F.sum(m).alias(m) for m in METRICAS],
        *[F.sum(f"{m}_anio_ant").alias(f"{m}_anio_ant_mismos_meses") for m in METRICAS],
    )
    if con_participacion:
        total_anio = Window.partitionBy(*[g for g in grupo if g != "categoria"], "anio")
    for m in METRICAS:
        base = F.col(f"{m}_anio_ant_mismos_meses")
        meta = base * CONFIG.meta_factor
        anual = (anual
                 .withColumn(f"{m}_var_pct_anio_ant", variacion_pct(F.col(m), base))
                 .withColumn(f"{m}_meta", meta.cast(DEC_MONTO))
                 .withColumn(f"{m}_cumplimiento_pct", pct(F.col(m), meta)))
        if con_participacion:
            anual = anual.withColumn(f"{m}_participacion_pct", pct(F.col(m), F.sum(m).over(total_anio)))
    return anual


# --------------------------------------------------------------------------
# Construcción de tablas
# --------------------------------------------------------------------------
def construir_cubo(spark: SparkSession, log) -> tuple[DataFrame, list[str]]:
    plata = spark.read.parquet(str(CONFIG.ruta_plata / "viajes"))
    dims = []
    for nombre, col in DIMENSIONES_ORO.items():
        if col not in plata.columns:
            continue
        if col == "distrito_origen" and plata.filter(F.col(col).isNotNull()).limit(1).count() == 0:
            log.warning("distrito_origen está vacío (falta la tabla de zonas): esa dimensión se omite")
            continue
        dims.append(col)
    log.info("Dimensiones para oro: %s", dims)
    cubo = (plata.groupBy("anio", "mes", *dims).agg(
                F.count("*").alias("viajes"),
                F.sum("monto_total").alias("ingresos"),
                F.sum("propina").alias("propinas"),
                F.sum("tarifa_base").alias("tarifas_base"),
                F.sum("distancia_millas").alias("distancia"),
                F.sum("duracion_min").alias("duracion"))
            .withColumn("periodo", F.make_date("anio", "mes", F.lit(1)))
            .cache())
    log.info("Cubo mensual: %s combinaciones", f"{cubo.count():,}")
    return cubo, dims


def tabla_kpi_mensual(cubo: DataFrame) -> DataFrame:
    base = cubo.groupBy("periodo", "anio", "mes").agg(
        *[F.sum(c).alias(c) for c in ("viajes", "ingresos", "propinas", "tarifas_base", "distancia", "duracion")])
    base = (base
            .withColumn("ticket_promedio_usd", (F.col("ingresos") / F.col("viajes")).cast(DEC_MONTO))
            .withColumn("propina_pct_sobre_tarifa", pct(F.col("propinas"), F.col("tarifas_base")))
            .withColumn("distancia_promedio_millas", (F.col("distancia") / F.col("viajes")).cast(DEC_MONTO))
            .withColumn("duracion_promedio_min", (F.col("duracion") / F.col("viajes")).cast(DEC_MONTO))
            .drop("propinas", "tarifas_base", "distancia", "duracion"))
    return agregar_metricas_mensuales(base, [], con_participacion=False)


def tabla_categoria_mensual(cubo: DataFrame, dims: list[str]) -> DataFrame:
    partes = []
    for d in dims:
        partes.append(cubo.groupBy("periodo", "anio", "mes", d)
                      .agg(F.sum("viajes").alias("viajes"), F.sum("ingresos").alias("ingresos"))
                      .select(F.lit(d).alias("dimension"), F.col(d).cast("string").alias("categoria"),
                              "periodo", "anio", "mes", "viajes", "ingresos"))
    largo = partes[0]
    for p in partes[1:]:
        largo = largo.unionByName(p)
    largo = largo.fillna({"categoria": "Desconocido"})
    return agregar_metricas_mensuales(largo, ["dimension", "categoria"], con_participacion=True)


def tabla_calidad_mensual(spark: SparkSession, log) -> DataFrame | None:
    archivo = CONFIG.ruta_plata / "_calidad" / "descartes_por_mes.csv"
    if not archivo.exists():
        log.warning("No existe %s: se omite oro_calidad_mensual", archivo)
        return None
    with archivo.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    leidas = {r["mes"]: int(r["filas"]) for r in filas if r["motivo"] == "filas_leidas"}
    datos = [(r["mes"], r["etapa"], r["motivo"], int(r["filas"]), leidas[r["mes"]])
             for r in filas if r["motivo"] != "filas_leidas"]
    df = spark.createDataFrame(datos, "anio_mes string, etapa string, motivo string, filas long, filas_leidas long")
    por_mes = Window.partitionBy("anio_mes")
    return (df.withColumn("periodo", F.to_date(F.concat("anio_mes", F.lit("-01"))))
              .withColumn("anio", F.year("periodo")).withColumn("mes", F.month("periodo"))
              .withColumn("pct_sobre_leidas", pct(F.col("filas"), F.col("filas_leidas")))
              .withColumn("pct_descartado_total_mes",
                          pct(F.sum(F.when(F.col("etapa") != "tratamiento", F.col("filas"))).over(por_mes),
                              F.col("filas_leidas")))
              .drop("anio_mes"))


def redondear(df: DataFrame) -> DataFrame:
    """Montos como decimal(18,2) para que el CSV no salga en notación científica."""
    for c, t in df.dtypes:
        if t == "double":
            df = df.withColumn(c, F.col(c).cast(DEC_MONTO))
    return df


def guardar(df: DataFrame, nombre: str, orden: list[str], log) -> None:
    """Guarda una tabla oro como un único Parquet y un único CSV."""
    df = redondear(df).orderBy(*orden).coalesce(1).cache()
    filas = df.count()
    ruta_pq = CONFIG.ruta_oro / "parquet" / nombre
    df.write.mode("overwrite").parquet(str(ruta_pq))
    tmp = CONFIG.ruta_oro / f"_tmp_{nombre}"
    df.write.mode("overwrite").option("header", True).csv(str(tmp))
    destino = CONFIG.ruta_oro / "csv" / f"{nombre}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(next(Path(tmp).glob("part-*.csv"))), destino)
    shutil.rmtree(tmp)
    log.info("   %-24s %6d filas, %2d columnas → parquet/%s y csv/%s.csv",
             nombre, filas, len(df.columns), nombre, nombre)
    df.unpersist()


def main() -> None:
    CONFIG.asegurar_carpetas()
    log = configurar_logs("02_oro", CONFIG.ruta_logs)
    spark = crear_spark("tlc-oro")

    with paso(log, "Leer plata y construir cubo mensual"):
        cubo, dims = construir_cubo(spark, log)

    with paso(log, "Calcular tablas oro"):
        kpi_m = tabla_kpi_mensual(cubo).cache()
        kpi_a = agregar_metricas_anuales(kpi_m, [], con_participacion=False)
        cat_m = tabla_categoria_mensual(cubo, dims).cache()
        cat_a = agregar_metricas_anuales(cat_m, ["dimension", "categoria"], con_participacion=True)
        calidad = tabla_calidad_mensual(spark, log)

    with paso(log, "Guardar oro (Parquet + CSV)"):
        guardar(kpi_m, "oro_kpi_mensual", ["periodo"], log)
        guardar(kpi_a, "oro_kpi_anual", ["anio"], log)
        guardar(cat_m, "oro_categoria_mensual", ["dimension", "categoria", "periodo"], log)
        guardar(cat_a, "oro_categoria_anual", ["dimension", "categoria", "anio"], log)
        if calidad is not None:
            guardar(calidad, "oro_calidad_mensual", ["periodo", "etapa", "motivo"], log)

    ultimo = kpi_m.orderBy(F.desc("periodo")).first()
    sd = lambda v: "sin dato" if v is None else f"{v} %"
    log.info("Último mes %s: %s viajes | var. vs mes anterior %s | vs año anterior %s | cumplimiento meta %s",
             ultimo["periodo"], f"{ultimo['viajes']:,}", sd(ultimo["viajes_var_pct_mes_ant"]),
             sd(ultimo["viajes_var_pct_anio_ant"]), sd(ultimo["viajes_cumplimiento_pct"]))
    spark.stop()


if __name__ == "__main__":
    main()
