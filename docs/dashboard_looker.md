# Dashboard en Looker Studio: 5 gráficos en porcentaje

Todos los gráficos leen tablas **oro** de BigQuery (`tlc_taxis.oro_*`). Son tablas pequeñas, de cientos o pocos miles de filas, así que Looker Studio no consume casi nada de la cuota gratuita de consultas.

## Antes de armar los gráficos

**Conectar las tablas.** En Looker Studio: *Crear → Fuente de datos → BigQuery → tu proyecto → `tlc_taxis`*. Agrega una fuente por cada tabla que uses: `oro_kpi_mensual`, `oro_categoria_mensual` y `oro_categoria_anual`.

**Cómo están guardados los porcentajes.** Los campos `*_pct` ya vienen multiplicados por 100: un 5,23 significa 5,23 %. En la fuente de datos tienes dos opciones:
- dejarlos como *Número* y agregar " %" como sufijo en el estilo del gráfico, o
- crear un campo calculado `viajes_var_pct_mes_ant / 100` con tipo *Porcentaje*.

**Agregación.** Un porcentaje no se suma entre meses. En cada campo `*_pct` cambia la agregación predeterminada de *Suma* a *Promedio*. Si el gráfico muestra un solo mes por fila, el promedio devuelve el valor exacto.

**Controles de la página:**
- *Control de periodo* sobre el campo `periodo`.
- *Lista desplegable* sobre `dimension`, con valores `forma_pago`, `tipo_tarifa`, `proveedor` y `distrito_origen`. Afecta solo a las fuentes `oro_categoria_*`. Configúralo de selección única, con `forma_pago` por defecto.

---

## Gráfico 1: Scorecards con variación %

| | |
|---|---|
| Tipo | Fila de 3 *Cuadros de resultados* (scorecards) |
| Tabla | `oro_kpi_mensual` |
| Filtro | `periodo` = último mes con datos (2026-08-01). Puede ser un rango fijo o el control de periodo |
| Scorecard A | `viajes_var_pct_mes_ant`: viajes frente al mes anterior |
| Scorecard B | `viajes_var_pct_anio_ant`: viajes frente al mismo mes del año anterior |
| Scorecard C | `ingresos_var_pct_anio_ant`: ingresos frente al mismo mes del año anterior |
| Formato | 1 decimal, sufijo " %"; color condicional: verde ≥ 0, rojo < 0 |

## Gráfico 2: Barras apiladas al 100 % (participación por categoría)

| | |
|---|---|
| Tipo | *Gráfico de columnas apiladas* |
| Tabla | `oro_categoria_mensual` |
| Filtro | `dimension` (con el control desplegable; por defecto `forma_pago`) |
| Dimensión (eje X) | `periodo`, con granularidad *Año y mes* |
| Desglose | `categoria` |
| Métrica | `viajes_participacion_pct` (agregación Promedio). Cada columna suma 100 |
| Alternativa | `ingresos_participacion_pct` para ver la participación en ingresos |

Muestra, por ejemplo, cómo la tarjeta le gana terreno al efectivo mes a mes, o qué peso tiene cada distrito.

## Gráfico 3: Línea de variación mensual

| | |
|---|---|
| Tipo | *Gráfico de líneas* |
| Tabla | `oro_kpi_mensual` |
| Dimensión | `periodo` (Año y mes) |
| Métricas | `viajes_var_pct_mes_ant`, `ingresos_var_pct_mes_ant` |
| Métrica opcional | `viajes_var_pct_anio_ant` en línea punteada (quita la estacionalidad) |
| Estilo | Línea de referencia en 0; eje Y con sufijo " %" |

El primer mes (ene-2024) queda vacío porque no tiene mes anterior.

## Gráfico 4: Barras de crecimiento por categoría

| | |
|---|---|
| Tipo | *Gráfico de barras* horizontal |
| Tabla | `oro_categoria_anual` |
| Filtros | `anio` = 2026 y `dimension` (control desplegable) |
| Dimensión | `categoria` |
| Métricas | `viajes_var_pct_anio_ant` y `ingresos_var_pct_anio_ant` |
| Orden | `viajes_var_pct_anio_ant` descendente |
| Nota | 2026 llega hasta agosto. La tabla anual lo compara contra ene-ago de 2025, no contra 2025 completo (campo `meses_con_datos`) |

Para 2025 frente a 2024 cambia el filtro a `anio` = 2025.

## Gráfico 5: Progreso frente a la meta

**Meta:** el mismo mes del año anterior + 5 % (`META_FACTOR=1.05` en `.env`). 2024 no tiene meta porque no hay año anterior en los datos.

| | |
|---|---|
| Tipo principal | *Medidor* (gauge) |
| Tabla | `oro_kpi_mensual` |
| Filtro | `periodo` = último mes con datos |
| Métrica | `viajes_cumplimiento_pct` |
| Rango | 0 a 150, con objetivo en 100 |
| Bandas | rojo < 90, amarillo 90–100, verde ≥ 100 |
| Gráfico de apoyo | *Columnas* con `periodo` desde 2025-01 y `viajes_cumplimiento_pct`, más una línea de referencia en 100 |
| Variante | `ingresos_cumplimiento_pct` para la meta de ingresos |

Para el avance del año usa `oro_kpi_anual`, `anio` = 2026 y el campo `viajes_cumplimiento_pct` (acumulado ene-ago contra la misma meta acumulada).

---

## Campos disponibles por tabla

**oro_kpi_mensual** (un registro por mes)
`periodo, anio, mes, viajes, ingresos, ticket_promedio_usd, propina_pct_sobre_tarifa, distancia_promedio_millas, duracion_promedio_min` y, para viajes e ingresos: `*_anio_ant, *_var_pct_mes_ant, *_var_pct_anio_ant, *_meta, *_cumplimiento_pct, *_crec_acum_anual_pct, *_crec_desde_inicio_pct`

**oro_kpi_anual** (un registro por año)
`anio, meses_con_datos, viajes, ingresos, *_anio_ant_mismos_meses, *_var_pct_anio_ant, *_meta, *_cumplimiento_pct`

**oro_categoria_mensual** (mes × dimensión × categoría)
`dimension, categoria, periodo, anio, mes, viajes, ingresos` + los mismos campos `*_pct` de la tabla mensual + `*_participacion_pct`

**oro_categoria_anual** (año × dimensión × categoría)
`dimension, categoria, anio, meses_con_datos, viajes, ingresos, *_var_pct_anio_ant, *_meta, *_cumplimiento_pct, *_participacion_pct`

**oro_calidad_mensual** (opcional, para mostrar la limpieza)
`periodo, anio, mes, etapa, motivo, filas, filas_leidas, pct_sobre_leidas, pct_descartado_total_mes`
