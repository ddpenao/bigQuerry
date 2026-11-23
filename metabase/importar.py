"""Crea el tablero en cualquier Metabase a partir de dashboard_tlc.json.

Antes hay que tener en ese Metabase la conexión a BigQuery con el nombre "TLC Taxis"
(proyecto festive-quanta-475416-k1, dataset tlc_taxis).

Uso:
    python3 metabase/importar.py --email tu@correo.com
    python3 metabase/importar.py --url http://localhost:3001 --email tu@correo.com --entrada metabase/dashboard_tlc.json
"""
import argparse
import json
import uuid
from pathlib import Path

from metabase_api import Metabase


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:3001")
    p.add_argument("--email", required=True)
    p.add_argument("--entrada", default=str(Path(__file__).with_name("dashboard_tlc.json")))
    p.add_argument("--base", help="Nombre de la base en Metabase (por defecto el del JSON)")
    a = p.parse_args()

    datos = json.loads(Path(a.entrada).read_text(encoding="utf-8"))
    mb = Metabase(a.url, a.email)

    nombre_base = a.base or datos["base_de_datos"]
    bases = mb.get("/api/database")
    bases = bases.get("data", bases) if isinstance(bases, dict) else bases
    base = next((b for b in bases if b["name"] == nombre_base), None)
    if base is None:
        raise SystemExit(f"No existe la base '{nombre_base}' en Metabase. Conéctala primero.")

    tab = datos["dashboard"]
    coleccion = mb.post("/api/collection", {"name": tab["name"], "color": "#509EE3", "parent_id": None})

    nuevas = {}
    for viejo_id, c in datos["cards"].items():
        tags = {t: {"id": str(uuid.uuid4()), "name": t, "display-name": t.capitalize(), "type": "date"} for t in c["tags"]}
        creada = mb.post("/api/card", {
            "name": c["name"], "description": c.get("description"), "display": c["display"],
            "collection_id": coleccion["id"], "type": "question", "visualization_settings": c["viz"],
            "dataset_query": {"database": base["id"], "type": "native",
                              "native": {"query": c["sql"], "template-tags": tags}},
        })
        nuevas[viejo_id] = creada["id"]
        print(f"  pregunta: {c['name']}")

    tablero = mb.post("/api/dashboard", {"name": tab["name"], "description": tab.get("description"),
                                         "collection_id": coleccion["id"], "parameters": tab["parameters"]})

    id_tab = {t["id"]: -(i + 1) for i, t in enumerate(tab["tabs"])}
    pestanas = [{"id": id_tab[t["id"]], "name": t["name"]} for t in tab["tabs"]]
    tarjetas = []
    for i, x in enumerate(tab["dashcards"]):
        cid = nuevas.get(str(x["card"])) if x["card"] else None
        tarjetas.append({
            "id": -(i + 1), "card_id": cid, "dashboard_tab_id": id_tab.get(x["tab"]),
            "row": x["row"], "col": x["col"], "size_x": x["w"], "size_y": x["h"],
            "visualization_settings": x["viz"],
            "parameter_mappings": [{"parameter_id": m, "card_id": cid, "target": ["variable", ["template-tag", m]]}
                                   for m in x["mapeos"]] if cid else [],
        })
    mb.put(f"/api/dashboard/{tablero['id']}", {"tabs": pestanas, "dashcards": tarjetas, "parameters": tab["parameters"]})
    print(f"Listo: {a.url.rstrip('/')}/dashboard/{tablero['id']}")


if __name__ == "__main__":
    main()
