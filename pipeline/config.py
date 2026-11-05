"""Chemins et constantes du pipeline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"          # archives zip ANFR (jamais commitées)
CACHE_DIR = DATA / "cache"      # fichiers extraits, référentiels téléchargés (jamais commités)
HISTORY_DIR = DATA / "history"  # agrégats mensuels de l'historique (légers, commités)
REFS_DIR = Path(__file__).resolve().parent / "refs"
OUT_DIR = ROOT / "site" / "public" / "data"  # fichiers servis par le site

DATASET_SLUG = "donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1"
DATASET_API = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"
DATASET_PAGE = f"https://www.data.gouv.fr/fr/datasets/{DATASET_SLUG}/"
GEO_API = "https://geo.api.gouv.fr"
USER_AGENT = "atlas-antennes-pipeline/0.1 (+https://github.com/clement-duffau/atlas-antennes)"

# Périmètre : France métropolitaine (Corse comprise). Les codes INSEE 97x/98x sont exclus.
EXCLUDED_INSEE_PREFIXES = ("97", "98")

# Bornes de validité des dates de mise en service.
MIN_SERVICE_YEAR = 1980

# Fenêtre de fréquence générique (MHz) pour les systèmes sans bande attendue.
GENERIC_F_MIN = 0.001
GENERIC_F_MAX = 1_000_000.0
