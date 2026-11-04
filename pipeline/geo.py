"""Contours des départements (métropole), simplifiés pour le web."""
from __future__ import annotations

import json
from pathlib import Path

import requests

from .config import CACHE_DIR, USER_AGENT

# Source officielle (Etalab, contours administratifs IGN), puis repli sur france-geojson (dérivé IGN).
SOURCES = (
    "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/latest/geojson/departements-1000m.geojson",
    "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/latest/geojson/departements-100m.geojson",
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson",
)


def _fetch() -> dict:
    cache = CACHE_DIR / "geo" / "departements.geojson"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    errors = []
    for url in SOURCES:
        try:
            # Pas de tentatives répétées ici : on passe vite à la source suivante.
            r = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            data = r.json()
            data["_source"] = url
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as e:  # noqa: BLE001 - on essaie la source suivante
            errors.append(f"{url}: {e}")
    raise RuntimeError("contours des départements indisponibles :\n" + "\n".join(errors))


def _round(coords, nd: int = 3):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], nd), round(coords[1], nd)]
    return [_round(c, nd) for c in coords]


def write_departements(path: Path) -> None:
    data = _fetch()
    feats = []
    for f in data["features"]:
        p = f["properties"]
        code = p.get("code") or p.get("code_insee")
        if not code or code.startswith("97") or code.startswith("98"):
            continue
        g = f["geometry"]
        feats.append({"type": "Feature", "properties": {"code": code, "nom": p.get("nom")},
                      "geometry": {"type": g["type"], "coordinates": _round(g["coordinates"])}})
    feats.sort(key=lambda f: f["properties"]["code"])
    out = {"type": "FeatureCollection", "source": data.get("_source"), "features": feats}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {path.name} : {len(feats)} départements, {path.stat().st_size / 1e3:,.0f} Ko")
