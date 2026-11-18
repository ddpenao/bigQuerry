# Guía para ejecutar el pipeline TLC en tu computador

Con esta guía obtienes en tu equipo las tres capas del proyecto: bronce (los 32 Parquet de taxis de NYC, enero 2024 a agosto 2026), plata (112.427.731 viajes limpios) y oro (5 tablas con porcentajes). Todo se hace con scripts y dentro de Docker, así que no hay que instalar Python, Java ni Spark.

En Linux los scripts están en `scripts/` y terminan en `.sh`. En Windows están en `scripts_windows/` y terminan en `.bat`. Hacen lo mismo y dan las mismas cifras.

## 1. Lo que necesitas instalado

| | Linux | Windows |
|---|---|---|
| Docker | Docker Engine con el plugin `docker compose` | Docker Desktop, abierto y diciendo *Engine running* |
| git | `sudo apt install git` | Git para Windows (git-scm.com) |
| Descargas | `curl` (viene en casi todas las distribuciones) | viene con Windows 10 y 11 |
| Equipo | 8 GB de RAM y 6 GB libres en disco | 8 GB de RAM y 6 GB libres en disco |

En Linux tu usuario debe poder usar Docker sin `sudo`. Si `docker run --rm hello-world` falla con *permission denied*, ejecuta `sudo usermod -aG docker $USER` y vuelve a iniciar sesión.

## 2. Clonar el repositorio

Linux:

```bash
cd ~/Documentos
git clone https://github.com/ddpenao/bigQuerry.git
cd bigQuerry
chmod +x scripts/*.sh
```

Windows (cmd o PowerShell):

```bat
cd %USERPROFILE%\Documents
git clone https://github.com/ddpenao/bigQuerry.git
cd bigQuerry
```

Todos los comandos que siguen se escriben dentro de la carpeta `bigQuerry`.

## 3. Conseguir la capa bronce (una sola vez)

Los Parquet no están en GitHub porque pesan 2 GB. Hay dos formas de tenerlos.

Descargarlos de la página de la TLC:

| Linux | Windows |
|---|---|
| `./scripts/descargar_bronce.sh` | `scripts_windows\descargar_bronce.bat` |

Quedan en la carpeta `TLC`, al lado de `bigQuerry`. Si se corta el internet, vuelve a ejecutarlo: salta los archivos que ya bajó.

Si un compañero te pasa la carpeta `TLC` en una USB, cópiala al lado de `bigQuerry` y no hace falta descargar nada.

## 4. Preparar el entorno (una sola vez)

| Linux | Windows |
|---|---|
| `./scripts/00_preparar.sh` | `scripts_windows\00_preparar.bat` |

El script revisa que Docker y git funcionen, crea el archivo `.env` con la configuración, cuenta los Parquet de bronce, descarga la tabla de zonas de la TLC y construye la imagen Docker. La primera vez tarda entre 2 y 15 minutos según tu internet. Termina con el mensaje `Listo. Siguiente paso: ...`.

## 5. Ejecutar todo

| Linux | Windows |
|---|---|
| `./scripts/ejecutar_todo.sh` | `scripts_windows\ejecutar_todo.bat` |

Corre en orden el reconocimiento de bronce, la limpieza a plata y el cálculo de oro. En pantalla se ve el avance mes por mes (`[1/32] Limpiar 2024-01`). En el portátil Linux donde se probó tardó 11 minutos; en Windows cuenta con 20 a 40 minutos, porque Docker escribe más lento en carpetas de Windows.

Al terminar tienes:

| Carpeta o archivo | Contenido |
|---|---|
| `plata/viajes/` | la capa plata, una carpeta por día |
| `oro/csv/` y `oro/parquet/` | las 5 tablas oro |
| `reportes/reconocimiento.md` | esquemas y muestra de bronce |
| `reportes/descartes_resumen.md` | cuántas filas se descartaron y por qué |
| `logs/` | un registro de cada ejecución |

Las cifras deben coincidir con las de cualquier compañero: 112.427.731 viajes en plata y 7.167.946 descartados (5,99 %).

## 6. Revisar las capas y rehacer una que se borre

Para ver qué tiene cada capa:

| Linux | Windows |
|---|---|
| `./scripts/estado.sh` | `scripts_windows\estado.bat` |

Muestra por capa si está COMPLETA o INCOMPLETA, y qué meses o tablas faltan.

Si se borra una capa, se rehace con un comando. El script recupera primero la capa anterior si también falta, y solo procesa lo que falta:

| Qué se borró | Linux | Windows |
|---|---|---|
| Bronce | `./scripts/reconstruir.sh bronce` | `scripts_windows\reconstruir.bat bronce` |
| Plata | `./scripts/reconstruir.sh plata` | `scripts_windows\reconstruir.bat plata` |
| Oro | `./scripts/reconstruir.sh oro` | `scripts_windows\reconstruir.bat oro` |
| Varias o no sabes cuál | `./scripts/reconstruir.sh todo` | `scripts_windows\reconstruir.bat todo` |

Para no depender de internet al rehacer bronce, guarda una copia de `TLC` en una USB y agrega su ruta al final de `.env`: `RESPALDO_BRONCE=/media/usuario/USB/TLC` en Linux o `RESPALDO_BRONCE=E:\TLC` en Windows. También puedes pasarla en el comando con `--desde RUTA` (Linux) o `-Desde RUTA` (Windows).

## 7. BigQuery y el dashboard

No necesitas cargar nada a BigQuery: las capas plata y oro ya están cargadas en el proyecto del grupo, y el dashboard de Looker Studio lee de ahí. Para verlo, pide que te compartan el informe de Looker Studio. Para consultar las tablas, pide que te agreguen al proyecto con el rol *Lector de datos de BigQuery*.

Si quieres cargarlas a tu propio proyecto de Google Cloud, sigue la sección "PASO 3: BigQuery" del `README.md`. Necesitas tu propia llave en `credenciales/gcp-key.json` y llenar `GCP_PROYECTO` y `BQ_PLATA_MESES` en `.env`. La llave nunca se sube a GitHub: `.gitignore` la excluye.

## 8. Si algo falla

| Mensaje o síntoma | Qué hacer |
|---|---|
| `docker-credential-desktop: executable file not found` | abre `~/.docker/config.json` y borra la línea `"credsStore": "desktop"` |
| `permission denied ... docker.sock` (Linux) | `sudo usermod -aG docker $USER` y vuelve a iniciar sesión |
| Docker no responde (Windows) | abre Docker Desktop y espera a que diga *Engine running* |
| `Permission denied` al ejecutar un `.sh` | `chmod +x scripts/*.sh` |
| `La capa bronce está vacía` | ejecuta `descargar_bronce` o `reconstruir bronce` |
| `java.lang.OutOfMemoryError` | cierra otros programas o sube `SPARK_MEMORIA` en `.env` (máximo el 60 % de tu RAM) |
| La ejecución se cortó a mitad | `reconstruir todo` sigue desde donde quedó |

Los scripts de Windows se escribieron con la misma lógica que los de Linux, pero se probaron menos. Si uno falla, guarda el mensaje completo de la terminal para poder corregirlo.
