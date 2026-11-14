"""Nombres estandarizados y catálogos de códigos (diccionario de datos de TLC)."""

# Columnas de bronce -> nombre en plata (snake_case, español) y tipo destino
COLUMNAS = [
    # (bronce, plata, tipo Spark)
    ("VendorID", "proveedor_id", "smallint"),
    ("tpep_pickup_datetime", "fecha_hora_recogida", "timestamp_ntz"),
    ("tpep_dropoff_datetime", "fecha_hora_llegada", "timestamp_ntz"),
    ("passenger_count", "num_pasajeros", "smallint"),
    ("trip_distance", "distancia_millas", "double"),
    ("RatecodeID", "tarifa_id", "smallint"),
    ("store_and_fwd_flag", "almacenado_reenviado", "string"),
    ("PULocationID", "zona_origen_id", "smallint"),
    ("DOLocationID", "zona_destino_id", "smallint"),
    ("payment_type", "forma_pago_id", "smallint"),
    ("fare_amount", "tarifa_base", "double"),
    ("extra", "recargo_extra", "double"),
    ("mta_tax", "impuesto_mta", "double"),
    ("tip_amount", "propina", "double"),
    ("tolls_amount", "peajes", "double"),
    ("improvement_surcharge", "recargo_mejora", "double"),
    ("total_amount", "monto_total", "double"),
    ("congestion_surcharge", "recargo_congestion", "double"),
    ("Airport_fee", "tarifa_aeropuerto", "double"),
    ("cbd_congestion_fee", "recargo_cbd", "double"),      # existe desde 2025-01
    ("request_source", "origen_solicitud", "string"),     # existe desde 2026-06
]

COMPONENTES_MONTO = [
    "tarifa_base", "recargo_extra", "impuesto_mta", "propina", "peajes",
    "recargo_mejora", "recargo_congestion", "tarifa_aeropuerto", "recargo_cbd",
]

# Clave de negocio del viaje (no hay ID en la fuente)
CLAVE_VIAJE = [
    "proveedor_id", "fecha_hora_recogida", "fecha_hora_llegada",
    "zona_origen_id", "zona_destino_id",
]

PROVEEDOR = {
    1: "Creative Mobile Technologies",
    2: "Curb Mobility",
    6: "Myle Technologies",
    7: "Helix",
}

TIPO_TARIFA = {
    1: "Estándar",
    2: "JFK",
    3: "Newark",
    4: "Nassau o Westchester",
    5: "Negociada",
    6: "Viaje compartido",
    99: "Desconocida",
}

# El código 0 llega sin pasajeros, tarifa ni recargos. Decisión del proyecto:
# se conserva y se etiqueta como "Desconocido". (El diccionario de TLC lo
# describe como viaje con tarifa flexible; la etiqueta se cambia aquí.)
FORMA_PAGO = {
    0: "Desconocido",
    1: "Tarjeta de crédito",
    2: "Efectivo",
    3: "Sin cargo",
    4: "Disputa",
    5: "Desconocido",
    6: "Viaje anulado",
}

# Dimensiones de la capa oro: nombre -> columna de plata
DIMENSIONES_ORO = {
    "forma_pago": "forma_pago",
    "tipo_tarifa": "tipo_tarifa",
    "proveedor": "proveedor",
    "distrito_origen": "distrito_origen",   # solo si existe la tabla de zonas
}
