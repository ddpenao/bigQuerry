"""PASO 0 - Reconocimiento de la capa bronce sin transformarla.

Lee el esquema de cada archivo (solo el pie del Parquet), cuenta filas y toma
una muestra aleatoria de 1.000 filas para perfilar nulos, rangos y códigos.
Resultado: reportes/reconocimiento.md

Uso: python -m tlc.reconocimiento
"""
from pyspark.sql import functions as F

from .bronce import leer_mes_unificado, listar_archivos
from .config import CONFIG
from .registro import configurar_logs, paso
from .sesion_spark import crear_spark

TAM_MUESTRA = 1000


def main() -> None:
    CONFIG.asegurar_carpetas()
    log = configurar_logs("00_reconocimiento", CONFIG.ruta_logs)
    spark = crear_spark("tlc-reconocimiento")
    archivos = listar_archivos(CONFIG.ruta_bronce)
    lineas = ["# Reconocimiento de la capa bronce", ""]

    with paso(log, f"Leer esquemas de {len(archivos)} archivos"):
        firmas: dict[tuple, list[str]] = {}
        filas_mes = {}
        for mes, ruta in archivos.items():
            df = spark.read.parquet(str(ruta))
            firma = tuple((c.name, c.dataType.simpleString()) for c in df.schema)
            firmas.setdefault(firma, []).append(mes)
            filas_mes[mes] = df.count()
            log.info("%s: %s filas, %d columnas", mes, f"{filas_mes[mes]:,}", len(firma))
    total = sum(filas_mes.values())
    log.info("Total bronce: %s filas", f"{total:,}")

    lineas += [f"**Archivos:** {len(archivos)}  |  **Filas totales:** {total:,}", "",
               "## Versiones de esquema", ""]
    for i, (firma, meses) in enumerate(firmas.items(), 1):
        lineas.append(f"### Esquema {i}: {meses[0]} → {meses[-1]} ({len(meses)} archivos)")
        lineas += ["", "| Columna | Tipo |", "|---|---|"]
        lineas += [f"| {n} | {t} |" for n, t in firma] + [""]

    with paso(log, f"Tomar muestra aleatoria de {TAM_MUESTRA} filas"):
        partes = None
        for mes, ruta in archivos.items():
            fraccion = min(1.0, 1.5 * TAM_MUESTRA / total)
            p = leer_mes_unificado(spark, ruta).sample(False, fraccion, seed=42)
            partes = p if partes is None else partes.unionByName(p)
        # Se baraja antes del limit para que la muestra no quede cargada a los primeros meses
        muestra = partes.orderBy(F.rand(seed=7)).limit(TAM_MUESTRA).cache()
        n = muestra.count()
        log.info("Muestra: %d filas", n)

    with paso(log, "Perfilar la muestra"):
        nulos = muestra.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in muestra.columns]).first().asDict()
        lineas += ["## Nulos en la muestra", "", "| Columna | Nulos | % |", "|---|---|---|"]
        lineas += [f"| {c} | {v} | {100 * v / n:.1f} |" for c, v in nulos.items()] + [""]

        numericas = [c for c, t in muestra.dtypes if t in ("smallint", "int", "bigint", "double")]
        lineas += ["## Rangos numéricos", "", "| Columna | mín | p50 | p99 | máx | negativos |", "|---|---|---|---|---|---|"]
        for c in numericas:
            q = muestra.approxQuantile(c, [0.0, 0.5, 0.99, 1.0], 0.001)
            neg = muestra.filter(F.col(c) < 0).count()
            if q:
                lineas.append(f"| {c} | {q[0]} | {q[1]} | {q[2]} | {q[3]} | {neg} |")
        lineas.append("")

        lineas += ["## Códigos", ""]
        for c in ("proveedor_id", "tarifa_id", "forma_pago_id", "almacenado_reenviado", "origen_solicitud"):
            conteo = sorted(((r[0], r[1]) for r in muestra.groupBy(c).count().collect()), key=lambda x: -x[1])
            lineas.append(f"- **{c}**: " + ", ".join(f"{k}={v}" for k, v in conteo))
        lineas.append("")

        dur = (F.unix_timestamp(F.col("fecha_hora_llegada").cast("timestamp"))
               - F.unix_timestamp(F.col("fecha_hora_recogida").cast("timestamp"))) / 60
        dup = n - muestra.dropDuplicates().count()
        lineas += [
            "## Señales de calidad en la muestra", "",
            f"- Filas idénticas repetidas: {dup}",
            f"- Duración ≤ 0 min: {muestra.filter(dur <= 0).count()}",
            f"- Distancia = 0: {muestra.filter('distancia_millas = 0').count()}",
            f"- Monto total ≤ 0: {muestra.filter('monto_total <= 0').count()}",
            "", "Claves candidatas: no hay ID de viaje. Se usa la clave compuesta "
            "(proveedor_id, fecha_hora_recogida, fecha_hora_llegada, zona_origen_id, zona_destino_id) "
            "y en plata se genera `id_viaje`.", "",
        ]

    salida = CONFIG.ruta_reportes / "reconocimiento.md"
    salida.write_text("\n".join(lineas), encoding="utf-8")
    log.info("Reporte escrito en %s", salida)
    spark.stop()


if __name__ == "__main__":
    main()
