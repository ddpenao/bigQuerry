# Reconocimiento de la capa bronce

**Archivos:** 32  |  **Filas totales:** 119,595,677

## Versiones de esquema

### Esquema 1: 2024-01 → 2024-12 (12 archivos)

| Columna | Tipo |
|---|---|
| VendorID | int |
| tpep_pickup_datetime | timestamp_ntz |
| tpep_dropoff_datetime | timestamp_ntz |
| passenger_count | bigint |
| trip_distance | double |
| RatecodeID | bigint |
| store_and_fwd_flag | string |
| PULocationID | int |
| DOLocationID | int |
| payment_type | bigint |
| fare_amount | double |
| extra | double |
| mta_tax | double |
| tip_amount | double |
| tolls_amount | double |
| improvement_surcharge | double |
| total_amount | double |
| congestion_surcharge | double |
| Airport_fee | double |

### Esquema 2: 2025-01 → 2026-05 (17 archivos)

| Columna | Tipo |
|---|---|
| VendorID | int |
| tpep_pickup_datetime | timestamp_ntz |
| tpep_dropoff_datetime | timestamp_ntz |
| passenger_count | bigint |
| trip_distance | double |
| RatecodeID | bigint |
| store_and_fwd_flag | string |
| PULocationID | int |
| DOLocationID | int |
| payment_type | bigint |
| fare_amount | double |
| extra | double |
| mta_tax | double |
| tip_amount | double |
| tolls_amount | double |
| improvement_surcharge | double |
| total_amount | double |
| congestion_surcharge | double |
| Airport_fee | double |
| cbd_congestion_fee | double |

### Esquema 3: 2026-06 → 2026-08 (3 archivos)

| Columna | Tipo |
|---|---|
| VendorID | int |
| tpep_pickup_datetime | timestamp_ntz |
| tpep_dropoff_datetime | timestamp_ntz |
| passenger_count | bigint |
| trip_distance | double |
| RatecodeID | bigint |
| store_and_fwd_flag | string |
| PULocationID | int |
| DOLocationID | int |
| payment_type | bigint |
| fare_amount | double |
| extra | double |
| mta_tax | double |
| tip_amount | double |
| tolls_amount | double |
| improvement_surcharge | double |
| total_amount | double |
| congestion_surcharge | double |
| Airport_fee | double |
| cbd_congestion_fee | double |
| request_source | string |

## Nulos en la muestra

| Columna | Nulos | % |
|---|---|---|
| proveedor_id | 0 | 0.0 |
| fecha_hora_recogida | 0 | 0.0 |
| fecha_hora_llegada | 0 | 0.0 |
| num_pasajeros | 209 | 20.9 |
| distancia_millas | 0 | 0.0 |
| tarifa_id | 209 | 20.9 |
| almacenado_reenviado | 209 | 20.9 |
| zona_origen_id | 0 | 0.0 |
| zona_destino_id | 0 | 0.0 |
| forma_pago_id | 0 | 0.0 |
| tarifa_base | 0 | 0.0 |
| recargo_extra | 0 | 0.0 |
| impuesto_mta | 0 | 0.0 |
| propina | 0 | 0.0 |
| peajes | 0 | 0.0 |
| recargo_mejora | 0 | 0.0 |
| monto_total | 0 | 0.0 |
| recargo_congestion | 209 | 20.9 |
| tarifa_aeropuerto | 209 | 20.9 |
| recargo_cbd | 387 | 38.7 |
| origen_solicitud | 967 | 96.7 |

## Rangos numéricos

| Columna | mín | p50 | p99 | máx | negativos |
|---|---|---|---|---|---|
| proveedor_id | 1.0 | 2.0 | 2.0 | 7.0 | 0 |
| num_pasajeros | 0.0 | 1.0 | 4.0 | 6.0 | 0 |
| distancia_millas | 0.0 | 1.85 | 20.75 | 81.16 | 0 |
| tarifa_id | 1.0 | 1.0 | 99.0 | 99.0 | 0 |
| zona_origen_id | 1.0 | 161.0 | 263.0 | 265.0 | 0 |
| zona_destino_id | 1.0 | 162.0 | 263.0 | 265.0 | 0 |
| forma_pago_id | 0.0 | 1.0 | 4.0 | 4.0 | 0 |
| tarifa_base | -70.0 | 14.2 | 78.6 | 450.0 | 36 |
| recargo_extra | -1.0 | 0.0 | 7.75 | 12.5 | 9 |
| impuesto_mta | -0.5 | 0.5 | 0.5 | 0.5 | 17 |
| propina | 0.0 | 2.16 | 17.34 | 36.01 | 0 |
| peajes | -6.94 | 0.0 | 7.46 | 27.94 | 1 |
| recargo_mejora | -1.0 | 1.0 | 1.0 | 1.0 | 17 |
| monto_total | -74.0 | 21.54 | 102.92 | 461.75 | 21 |
| recargo_congestion | -2.5 | 2.5 | 2.5 | 2.5 | 13 |
| tarifa_aeropuerto | -1.75 | 0.0 | 2.0 | 2.0 | 2 |
| recargo_cbd | -0.75 | 0.75 | 0.75 | 0.75 | 2 |

## Códigos

- **proveedor_id**: 2=786, 1=207, 7=6, 6=1
- **tarifa_id**: 1=743, None=209, 2=26, 99=13, 5=7, 3=2
- **forma_pago_id**: 1=659, 0=209, 2=103, 4=22, 3=7
- **almacenado_reenviado**: N=789, None=209, Y=2
- **origen_solicitud**: None=967, HV0003=26, A=4, HV0005=2, EH0004=1

## Señales de calidad en la muestra

- Filas idénticas repetidas: 0
- Duración ≤ 0 min: 6
- Distancia = 0: 23
- Monto total ≤ 0: 21

Claves candidatas: no hay ID de viaje. Se usa la clave compuesta (proveedor_id, fecha_hora_recogida, fecha_hora_llegada, zona_origen_id, zona_destino_id) y en plata se genera `id_viaje`.
