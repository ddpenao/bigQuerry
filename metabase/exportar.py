"""Exporta el tablero de Metabase (preguntas SQL, pestañas y posiciones) a un JSON.

Uso:
    python3 metabase/exportar.py --email tu@correo.com
    python3 metabase/exportar.py --url http://localhost:3001 --email tu@correo.com --salida metabase/dashboard_tlc.json
"""
import argparse
import json
from pathlib import Path

from metabase_api import Metabase


def sql_y_tags(dataset_query):
    # Metabase 0.65 devuelve el formato nuevo (stages); versiones viejas, el clásico.
    if "stages" in dataset_query:
        etapa = dataset_query["stages"][0]
        tags = etapa.get("template-tags") or []
        nombres = [t["name"] for t in tags] if isinstance(tags, list) else list(tags)
        return etapa["native"], nombres
    nativo = dataset_query["native"]
    return nativo["query"], list((nativo.get("template-tags") or {}).keys())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:3001")
    p.add_argument("--email", required=True)
    p.add_argument("--tablero", default="Dashboard TLC Taxis")
    p.add_argument("--salida", default=str(Path(__file__).with_name("dashboard_tlc.json")))
    a = p.parse_args()

    mb = Metabase(a.url, a.email)
    tableros = [d for d in mb.get("/api/dashboard") if d["name"] == a.tablero and not d.get("archived")]
    if not tableros:
        raise SystemExit(f"No encontré el tablero '{a.tablero}'.")
    d = mb.get(f"/api/dashboard/{tableros[0]['id']}")

    preguntas = {}
    for x in d["dashcards"]:
        cid = x.get("card_id")
        if cid and str(cid) not in preguntas:
            c = mb.get(f"/api/card/{cid}")
            sql, tags = sql_y_tags(c["dataset_query"])
            preguntas[str(cid)] = {
                "name": c["name"], "description": c.get("description"), "display": c["display"],
                "sql": sql, "tags": tags, "viz": c.get("visualization_settings") or {},
            }

    salida = {
        "formato": "tlc-metabase-v1",
        "base_de_datos": "TLC Taxis",
        "dashboard": {
            "name": d["name"],
            "description": d.get("description"),
            "parameters": [{k: p[k] for k in ("id", "name", "slug", "type", "sectionId") if k in p} for p in d["parameters"]],
            "tabs": [{"id": t["id"], "name": t["name"], "position": t.get("position")} for t in d.get("tabs", [])],
            "dashcards": [{
                "card": x.get("card_id"), "tab": x.get("dashboard_tab_id"),
                "row": x["row"], "col": x["col"], "w": x["size_x"], "h": x["size_y"],
                "mapeos": [m["parameter_id"] for m in x.get("parameter_mappings") or []],
                "viz": {} if x.get("card_id") else x.get("visualization_settings") or {},
            } for x in d["dashcards"]],
        },
        "cards": preguntas,
    }
    Path(a.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exportadas {len(preguntas)} preguntas y {len(salida['dashboard']['tabs'])} pestañas a {a.salida}")


if __name__ == "__main__":
    main()
