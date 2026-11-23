"""Deja Metabase listo de una vez: usuario administrador, conexión a BigQuery y tablero.

Lo llama scripts/montar_todo.sh. Se puede volver a correr: lo que ya existe se salta.

    1. Si Metabase está recién instalado, crea tu usuario (pide correo y contraseña).
    2. Conecta la base "TLC Taxis" (BigQuery, dataset tlc_taxis) con la llave de solo lectura.
    3. Espera la sincronización y oculta las tablas de plata (no se consultan desde el tablero).
    4. Crea el tablero desde dashboard_tlc.json si todavía no existe.

Uso:
    python3 metabase/configurar.py
    python3 metabase/configurar.py --url http://localhost:3001 --llave credenciales/metabase-lectura.json

Correo y contraseña se pueden dar con las variables MB_EMAIL y MB_PASSWORD para no escribirlos.
"""
import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from importar import buscar_base, importar_tablero, leer_tablero  # noqa: E402
from metabase_api import Metabase  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TABLAS_OCULTAS = ("plata_viajes", "plata_descartes")


def leer_env(nombre, defecto=""):
    """Valor de una variable de .env (la del entorno tiene prioridad)."""
    if os.environ.get(nombre):
        return os.environ[nombre]
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith(f"{nombre}="):
                return linea.split("=", 1)[1].strip() or defecto
    return defecto


def pedir_json(url, ruta, cuerpo=None):
    req = urllib.request.Request(url + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 method="POST" if cuerpo is not None else "GET")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Error {e.code} en {ruta}: {e.read().decode()[:500]}")


def esperar_metabase(url, minutos=5):
    limite = time.time() + minutos * 60
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=5) as r:
                if b"ok" in r.read():
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(5)
    raise SystemExit(f"Metabase no responde en {url}. Revisa: docker logs metabase")


def credenciales(nuevo):
    email = os.environ.get("MB_EMAIL") or input("Correo para tu usuario de Metabase: ").strip()
    clave = os.environ.get("MB_PASSWORD")
    if not clave:
        clave = getpass.getpass("Contraseña de Metabase: ")
        if nuevo and getpass.getpass("Repite la contraseña: ") != clave:
            raise SystemExit("Las contraseñas no coinciden. Vuelve a correr el script.")
    return email, clave


def crear_usuario(url, email, clave):
    token = pedir_json(url, "/api/session/properties").get("setup-token")
    nombre = email.split("@")[0]
    pedir_json(url, "/api/setup", {
        "token": token,
        "user": {"email": email, "password": clave, "first_name": nombre, "last_name": "TLC", "site_name": "TLC Taxis"},
        "prefs": {"site_name": "TLC Taxis", "site_locale": "es", "allow_tracking": False},
    })
    print(f"  usuario creado: {email}")


def conectar_bigquery(mb, nombre, llave, proyecto, dataset):
    base = buscar_base(mb, nombre)
    if base:
        print(f"  la base '{nombre}' ya existe (id {base['id']})")
        return base["id"]
    if not llave.exists():
        raise SystemExit(f"Falta la llave de lectura {llave}. Créala en Google Cloud (cuenta plotly-lectura) "
                         "y guárdala con ese nombre.")
    print(f"  conectando BigQuery: proyecto {proyecto}, dataset {dataset}")
    try:
        base = crear_base(mb, nombre, llave, proyecto, dataset)
    except SystemExit as e:
        raise SystemExit(f"{e}\nNo se pudo conectar a BigQuery. Revisa que {llave} sea una llave JSON vigente "
                         "de la cuenta plotly-lectura (roles Visualizador de datos y Usuario de trabajo de BigQuery) "
                         "y vuelve a correr el script.")
    return base["id"]


def crear_base(mb, nombre, llave, proyecto, dataset):
    return mb.post("/api/database", {
        "engine": "bigquery-cloud-sdk",
        "name": nombre,
        "details": {
            "billing-project-id": proyecto,
            "project-id": proyecto,
            "service-account-json": llave.read_text(encoding="utf-8"),
            "dataset-filters-type": "inclusion",
            "dataset-filters-patterns": dataset,
        },
        "is_full_sync": True,
    })


def esperar_sincronizacion(mb, base_id, minutos=10):
    print("  esperando a que Metabase lea las tablas de BigQuery...", flush=True)
    limite = time.time() + minutos * 60
    while time.time() < limite:
        tablas = [t for t in mb.get("/api/table") if t["db_id"] == base_id]
        if mb.get(f"/api/database/{base_id}").get("initial_sync_status") == "complete" and tablas:
            print(f"  {len(tablas)} tablas leídas")
            return tablas
        time.sleep(10)
    raise SystemExit("La sincronización con BigQuery tardó demasiado. Vuelve a correr el script en unos minutos.")


def ocultar_tablas(mb, tablas):
    for t in tablas:
        if t["name"] in TABLAS_OCULTAS and t.get("visibility_type") != "hidden":
            mb.put(f"/api/table/{t['id']}", {"visibility_type": "hidden"})
            print(f"  oculta: {t['name']}")


def tablero_existe(mb, nombre):
    r = mb.get("/api/search?models=dashboard&q=" + urllib.request.quote(nombre))
    r = r.get("data", r) if isinstance(r, dict) else r
    return next((d for d in r if d["name"] == nombre and not d.get("archived")), None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=f"http://localhost:{leer_env('MB_PUERTO', '3001')}")
    p.add_argument("--llave", default=leer_env("MB_LLAVE_LECTURA", "credenciales/metabase-lectura.json"))
    p.add_argument("--entrada", default=str(Path(__file__).with_name("dashboard_tlc.json")))
    a = p.parse_args()

    url = a.url.rstrip("/")
    llave = Path(a.llave) if Path(a.llave).is_absolute() else RAIZ / a.llave
    proyecto = leer_env("GCP_PROYECTO", "festive-quanta-475416-k1")
    dataset = leer_env("BQ_DATASET", "tlc_taxis")
    datos = leer_tablero(a.entrada)

    esperar_metabase(url)
    nuevo = not pedir_json(url, "/api/session/properties").get("has-user-setup")
    if nuevo and not llave.exists():
        raise SystemExit(f"Falta la llave de lectura {llave}. Créala antes de configurar Metabase.")
    print("Metabase recién instalado: se crea tu usuario." if nuevo else "Metabase ya tiene usuario: inicia sesión.")
    email, clave = credenciales(nuevo)
    if nuevo:
        crear_usuario(url, email, clave)
    mb = Metabase(url, email, clave)

    base_id = conectar_bigquery(mb, datos["base_de_datos"], llave, proyecto, dataset)
    ocultar_tablas(mb, esperar_sincronizacion(mb, base_id))

    nombre = datos["dashboard"]["name"]
    existente = tablero_existe(mb, nombre)
    if existente:
        print(f"  el tablero '{nombre}' ya existe: {url}/dashboard/{existente['id']}")
    else:
        print(f"  creando el tablero '{nombre}'")
        importar_tablero(mb, datos)
    print(f"Metabase listo en {url}")


if __name__ == "__main__":
    main()
