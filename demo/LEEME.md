# Práctica rápida: 2 meses por año

Esta rama (`demo-rapida`) corre el mismo pipeline con 6 meses en lugar de 32:
enero y febrero de 2024, 2025 y 2026. Sirve para la presentación, cuando piden borrar
una capa y volver a levantarla sin esperar el procesamiento completo.

Vive en su propia carpeta, `~/Documentos/TLC_demo`. El proyecto completo
(`~/Documentos/TLC_pipeline`), la bronce original (`~/Documentos/TLC`), BigQuery y Metabase no se tocan.

| Carpeta en TLC_demo | Qué tiene |
|---|---|
| `bronce_demo/` | copia de los 6 Parquet (la original queda en ../TLC) |
| `plata/` | plata solo de esos 6 meses |
| `oro/` | las 12 tablas oro de esos 6 meses |

## Una sola vez

```bash
cd ~/Documentos/TLC_demo
./demo/preparar_demo.sh
./demo/demo.sh
```

## En la presentación

| Si piden borrar | Borrar | Volver a levantar |
|---|---|---|
| Oro | `./demo/borrar_capa.sh oro` | `./scripts/reconstruir.sh oro` |
| Plata | `./demo/borrar_capa.sh plata` | `./scripts/reconstruir.sh oro` |
| Bronce | `./demo/borrar_capa.sh bronce` | `./scripts/reconstruir.sh oro` |
| Todo | las tres anteriores | `./scripts/reconstruir.sh oro` |

`reconstruir.sh oro` revisa de abajo hacia arriba: si falta bronce la copia desde `../TLC`
(sin internet), si falta plata la rehace y al final genera oro. `./scripts/estado.sh` muestra
en cualquier momento qué tiene cada capa.

Para otros meses cambia `DEMO_MESES` en `.env`, por ejemplo
`DEMO_MESES=2024-07,2024-08,2025-07,2025-08,2026-07,2026-08`.

## Verla en Metabase

```bash
./demo/subir_bigquery.sh
```

Sube las 12 tablas oro de la práctica al dataset `tlc_taxis_demo` (nunca a `tlc_taxis`).
En Metabase la práctica tiene su propio tablero, "Dashboard TLC Taxis · Práctica", en la colección
"Práctica rápida (2 meses por año)". Tiene las mismas 5 pestañas del principal y lee solo `tlc_taxis_demo`.
El tablero principal no cambia. Si borras y reconstruyes una capa, vuelve a correr `./demo/subir_bigquery.sh`
para que Metabase muestre los datos nuevos.

## Diferencias con el proyecto completo

- Las variaciones contra el año anterior funcionan (enero 2025 contra enero 2024, etc.).
  La variación contra el mes anterior queda vacía en enero, porque falta diciembre.
- En la tabla semanal, las 8 semanas de referencia pueden venir del año anterior por el hueco entre años.
- Si alguna vez se sube a BigQuery, va al dataset `tlc_taxis_demo`, nunca a `tlc_taxis`.
