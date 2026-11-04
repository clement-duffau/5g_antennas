"""Exports statiques pour le front (hors stats.json)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import duckdb

from .stats import _rows


def write_all(con: duckdb.DuckDBPyConnection, out: Path, write_json: Callable[[Path, object], None]) -> None:
    # Communes porteuses d'au moins un support : recherche et classements.
    communes = _rows(con, """
        SELECT c.insee, c.nom, c.dep, c.population, round(c.surface_km2, 2) AS surface_km2,
               round(c.lat, 4) AS lat, round(c.lon, 4) AS lon, count(s.sup_id) AS supports
        FROM communes c LEFT JOIN supports s USING (insee)
        WHERE substr(c.dep, 1, 2) NOT IN ('97', '98')
        GROUP BY ALL ORDER BY c.insee
    """)
    cols = list(communes[0].keys())
    write_json(out / "communes.json", {"colonnes": cols, "lignes": [list(r.values()) for r in communes]})
    write_json(out / "departements.json", _rows(con, """
        SELECT dep, nom, region FROM departements WHERE substr(dep, 1, 2) NOT IN ('97', '98') ORDER BY dep"""))
