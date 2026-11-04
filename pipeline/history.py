"""Historique du parc à partir des archives mensuelles ANFR (depuis 2018).

Pour chaque extraction, on ne garde qu'un agrégat léger (data/history/<AAAAMMJJ>.json, commité) :
nombre de supports et d'émetteurs, sites par opérateur mobile et génération, émetteurs par système mobile
et par opérateur. Contrairement aux dates de mise en service, ces séries montrent les sites démontés.

    python -m pipeline history            # calcule les mois manquants (télécharge ~66 Mo par mois)
    python -m pipeline history --limit 5  # au plus 5 mois
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import duckdb

from . import clean, fetch, load
from .config import CACHE_DIR, EXCLUDED_INSEE_PREFIXES, HISTORY_DIR, RAW_DIR
from .stats import MOBILE_OPS

TABLES = ("SUP_SUPPORT", "SUP_STATION", "SUP_EMETTEUR", "SUP_EXPLOITANT")
GENERATIONS = ("2G", "3G", "4G", "5G")


def aggregate(con: duckdb.DuckDBPyConnection) -> dict:
    """Agrège une extraction chargée dans les tables raw_sup_* (mêmes définitions pour toutes les années)."""
    clean.load_refs(con)
    excluded = ", ".join(f"'{p}'" for p in EXCLUDED_INSEE_PREFIXES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _h AS
        WITH sup AS (
            SELECT DISTINCT SUP_ID AS sup, STA_NM_ANFR AS sta FROM raw_sup_support
            WHERE substr(COM_CD_INSEE, 1, 2) NOT IN ({excluded})
        ), st AS (
            SELECT s.STA_NM_ANFR AS sta, coalesce(r.groupe, e.ADM_LB_NOM, 'Inconnu') AS groupe
            FROM raw_sup_station s
            LEFT JOIN raw_sup_exploitant e ON e.ADM_ID = s.ADM_ID
            LEFT JOIN ref_exploitants r ON r.libelle = e.ADM_LB_NOM
        )
        SELECT sup.sup, st.groupe, trim(em.EMR_LB_SYSTEME) AS systeme, rs.famille, rs.generation
        FROM raw_sup_emetteur em
        JOIN st ON st.sta = em.STA_NM_ANFR
        JOIN sup ON sup.sta = em.STA_NM_ANFR
        LEFT JOIN ref_systemes rs ON rs.libelle = trim(em.EMR_LB_SYSTEME)
    """)
    one = lambda q: con.execute(q).fetchall()[0][0]  # noqa: E731
    ops = ", ".join(f"'{o}'" for o in MOBILE_OPS)
    sites: dict[str, dict[str, int]] = {o: {g: 0 for g in (*GENERATIONS, "total")} for o in MOBILE_OPS}
    for groupe, gen, n in con.execute(f"""
        SELECT groupe, coalesce(generation, '?'), count(DISTINCT sup) FROM _h
        WHERE famille = 'Mobile' AND groupe IN ({ops}) GROUP BY ALL
        UNION ALL
        SELECT groupe, 'total', count(DISTINCT sup) FROM _h
        WHERE famille = 'Mobile' AND groupe IN ({ops}) GROUP BY ALL
    """).fetchall():
        if gen in sites[groupe]:
            sites[groupe][gen] = n
    systemes: dict[str, dict[str, int]] = {}
    for systeme, groupe, n in con.execute(f"""
        SELECT systeme, CASE WHEN groupe IN ({ops}) THEN groupe ELSE 'autres' END, count(*)
        FROM _h WHERE famille = 'Mobile' GROUP BY ALL
    """).fetchall():
        d = systemes.setdefault(systeme, {"total": 0})
        d[groupe] = d.get(groupe, 0) + n
        d["total"] += n
    return {
        "supports": one("SELECT count(DISTINCT sup) FROM _h"),
        "emetteurs": one("SELECT count(*) FROM _h"),
        "sites": sites,
        "systemes": systemes,
        "systemes_non_references": sorted(r[0] for r in con.execute(
            "SELECT DISTINCT systeme FROM _h WHERE famille IS NULL AND systeme IS NOT NULL").fetchall()),
    }


def save(key: str, agg: dict, history_dir: Path = HISTORY_DIR) -> Path:
    history_dir.mkdir(parents=True, exist_ok=True)
    path = history_dir / f"{key}.json"
    path.write_text(json.dumps({"extraction": key, **agg}, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def compute_missing(limit: int | None = None, keep_raw: bool = False) -> list[str]:
    """Télécharge et agrège les extractions absentes de data/history/. Retourne les clés calculées."""
    meta = fetch.fetch_metadata()
    done = {p.stem for p in HISTORY_DIR.glob("*.json")}
    todo = [e for e in fetch.list_extractions(meta) if e.key not in done]
    if limit is not None:
        todo = todo[:limit]
    computed = []
    for k, ext in enumerate(todo, 1):
        print(f"[{k}/{len(todo)}] extraction {ext.key}", flush=True)
        try:
            zips = [z for z in fetch.download_extraction(ext) if z]
            files = load.extract(zips, f"hist-{ext.key}", tables=TABLES)
            con = duckdb.connect()
            load.load(con, files)
            agg = aggregate(con)
            con.close()
        except Exception as e:  # noqa: BLE001 - une archive défectueuse ne bloque pas les autres
            print(f"  échec : {e}", flush=True)
            continue
        finally:
            shutil.rmtree(CACHE_DIR / f"hist-{ext.key}", ignore_errors=True)
            if not keep_raw:
                for z in RAW_DIR.glob(f"{ext.key}-export-etalab-*.zip"):
                    z.unlink()
        save(ext.key, agg)
        print(f"  {agg['supports']:,} supports, {agg['emetteurs']:,} émetteurs"
              + (f" ; systèmes non référencés : {agg['systemes_non_references']}" if agg["systemes_non_references"] else ""),
              flush=True)
        computed.append(ext.key)
    return computed


def assemble(history_dir: Path = HISTORY_DIR) -> dict | None:
    """Séries temporelles pour le front (history.json), dans l'ordre chronologique."""
    files = sorted(history_dir.glob("*.json"))
    if not files:
        return None
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    mois = [f"{r['extraction'][:4]}-{r['extraction'][4:6]}" for r in rows]
    sites = {o: {g: [r["sites"].get(o, {}).get(g) for r in rows] for g in (*GENERATIONS, "total")} for o in MOBILE_OPS}
    noms = sorted({s for r in rows for s in r["systemes"]})
    cles = (*MOBILE_OPS, "autres", "total")
    systemes = {s: {c: [r["systemes"].get(s, {}).get(c, 0) for r in rows] for c in cles} for s in noms}
    return {
        "mois": mois,
        "extractions": [r["extraction"] for r in rows],
        "supports": [r["supports"] for r in rows],
        "emetteurs": [r["emetteurs"] for r in rows],
        "sites": sites,
        "systemes": systemes,
    }
