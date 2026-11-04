"""Référentiel communes / départements (geo.api.gouv.fr), mis en cache localement."""
from __future__ import annotations

import json

import duckdb

from .config import CACHE_DIR, GEO_API
from .fetch import get_json


def _cached(name: str, url: str, refresh: bool) -> list[dict]:
    path = CACHE_DIR / "geo" / f"{name}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data = get_json(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data  # type: ignore[return-value]


def fetch(refresh: bool = False) -> dict[str, list[dict]]:
    return {
        "communes": _cached(
            "communes",
            f"{GEO_API}/communes?fields=code,nom,population,surface,codeDepartement,centre&format=json",
            refresh),
        "arrondissements": _cached(
            "arrondissements",
            f"{GEO_API}/communes?type=arrondissement-municipal"
            "&fields=code,nom,population,surface,codeParent&format=json",
            refresh),
        "departements": _cached("departements", f"{GEO_API}/departements?fields=code,nom,codeRegion", refresh),
        "regions": _cached("regions", f"{GEO_API}/regions?fields=code,nom", refresh),
    }


def load(con: duckdb.DuckDBPyConnection, refresh: bool = False) -> None:
    """Crée les tables `communes`, `arrondissements`, `departements`.

    surface : geo.api la donne en hectares ; on la stocke en km².
    """
    ref = fetch(refresh)
    rows = [
        (c["code"], c["nom"], c.get("codeDepartement"), c.get("population"),
         (c["surface"] / 100) if c.get("surface") else None,
         *(c["centre"]["coordinates"] if c.get("centre") else (None, None)))
        for c in ref["communes"]
    ]
    con.execute("""CREATE OR REPLACE TABLE communes (
        insee VARCHAR PRIMARY KEY, nom VARCHAR, dep VARCHAR, population INTEGER,
        surface_km2 DOUBLE, lon DOUBLE, lat DOUBLE)""")
    con.executemany("INSERT INTO communes VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

    con.execute("CREATE OR REPLACE TABLE arrondissements (insee VARCHAR, nom VARCHAR, parent VARCHAR)")
    con.executemany("INSERT INTO arrondissements VALUES (?, ?, ?)",
                    [(a["code"], a["nom"], a.get("codeParent")) for a in ref["arrondissements"]])

    regions = {r["code"]: r["nom"] for r in ref["regions"]}
    con.execute("CREATE OR REPLACE TABLE departements (dep VARCHAR, nom VARCHAR, region VARCHAR)")
    con.executemany("INSERT INTO departements VALUES (?, ?, ?)",
                    [(d["code"], d["nom"], regions.get(d.get("codeRegion"), "")) for d in ref["departements"]])

