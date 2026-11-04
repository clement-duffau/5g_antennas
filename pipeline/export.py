"""Exports statiques pour le front (hors stats.json).

- communes.json, departements.json : référentiels (recherche, classements) ;
- supports.json : index en colonnes de tous les supports (carte, filtres côté client) ;
- detail/<dep>.json : fiche complète des supports d'un département (chargée au clic) ;
- departements.geojson : contours simplifiés (fond de carte de secours, choroplèthes).
"""
from __future__ import annotations

import gzip
import json
import sys
from array import array
from pathlib import Path
from typing import Callable

import duckdb

from . import geo
from .stats import MOBILE_OPS, _rows

WriteJson = Callable[[Path, object], None]

# Sous-ensembles utilisés comme masques de bits dans l'index (ordre figé, repris par le front).
GENERATIONS = ("2G", "3G", "4G", "5G")


def write_all(con: duckdb.DuckDBPyConnection, out: Path, write_json: WriteJson) -> None:
    write_referentiels(con, out, write_json)
    write_index(con, out, write_json)
    write_services(con, out, write_json)
    write_details(con, out, write_json)
    geo.write_departements(out / "departements.geojson")


def write_referentiels(con: duckdb.DuckDBPyConnection, out: Path, write_json: WriteJson) -> None:
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


def _dict(values: list) -> tuple[list, dict]:
    uniq = sorted({v for v in values if v is not None}, key=str)
    return uniq, {v: i for i, v in enumerate(uniq)}


def write_index(con: duckdb.DuckDBPyConnection, out: Path, write_json: WriteJson) -> None:
    """Index en colonnes : une entrée par support, valeurs codées par dictionnaire et masques de bits."""
    familles = [r[0] for r in con.execute(
        "SELECT famille FROM emr_full GROUP BY 1 ORDER BY count(*) DESC").fetchall()]
    fam_bit = {f: i for i, f in enumerate(familles)}
    ops_sql = ", ".join(
        f"max(CASE WHEN mobile AND groupe = '{op}' THEN {1 << i} ELSE 0 END)" for i, op in enumerate(MOBILE_OPS))
    gen_sql = ", ".join(
        f"max(CASE WHEN famille = 'Mobile' AND generation = '{g}' THEN {1 << i} ELSE 0 END)"
        for i, g in enumerate(GENERATIONS))
    fam_sql = ", ".join(f"max(CASE WHEN famille = '{f}' THEN {1 << i} ELSE 0 END)" for f, i in fam_bit.items())
    rows = con.execute(f"""
        WITH agg AS (
            SELECT ss.sup_id,
                   list_value({ops_sql}) AS ops_bits,
                   max(CASE WHEN NOT mobile THEN 1 ELSE 0 END) AS autres,
                   list_value({gen_sql}) AS gen_bits,
                   list_value({fam_sql}) AS fam_bits,
                   count(*) AS n_emr,
                   count(DISTINCT groupe) AS n_exp,
                   min(date_service) AS d0, max(date_service) AS d1
            FROM emr_full e JOIN support_station ss ON ss.sta = e.sta GROUP BY ss.sup_id
        )
        SELECT s.sup_id, s.lat, s.lon, s.hauteur, s.nature, s.proprietaire, s.insee,
               a.ops_bits, a.autres, a.gen_bits, a.fam_bits, a.n_emr, a.n_exp, a.d0, a.d1
        FROM supports s LEFT JOIN agg a USING (sup_id)
        ORDER BY s.insee, s.sup_id
    """).fetchall()

    natures, nat_i = _dict([r[4] for r in rows])
    proprios, tpo_i = _dict([r[5] for r in rows])
    communes, com_i = _dict([r[6] for r in rows])

    def month(d) -> int:  # mois depuis janvier 1980 (0 = inconnu)
        return 0 if d is None else (d.year - 1980) * 12 + d.month

    cols: dict[str, list] = {k: [] for k in
                             ("id", "lat", "lon", "h", "nat", "tpo", "com", "ops", "gen", "fam", "emr", "exp", "d0", "d1")}
    for (sup_id, lat, lon, h, nat, tpo, insee, ops_bits, autres, gen_bits, fam_bits,
         n_emr, n_exp, d0, d1) in rows:
        cols["id"].append(sup_id)
        cols["lat"].append(round(lat * 1e5))
        cols["lon"].append(round(lon * 1e5))
        cols["h"].append(None if h is None else round(h * 10))
        cols["nat"].append(nat_i.get(nat, -1))
        cols["tpo"].append(tpo_i.get(tpo, -1))
        cols["com"].append(com_i[insee])
        # Un support peut n'avoir aucun émetteur déclaré (stations sans émetteur) : valeurs nulles.
        cols["ops"].append(sum(ops_bits or []) | ((autres or 0) << len(MOBILE_OPS)))
        cols["gen"].append(sum(gen_bits or []))
        cols["fam"].append(sum(fam_bits or []))
        cols["emr"].append(n_emr or 0)
        cols["exp"].append(n_exp or 0)
        cols["d0"].append(month(d0))
        cols["d1"].append(month(d1))

    # Encodage différentiel (le tri par commune rend les écarts petits, donc bien compressés).
    deltas = ("id", "lat", "lon", "com")
    for k in deltas:
        v = cols[k]
        cols[k] = [v[0]] + [v[i] - v[i - 1] for i in range(1, len(v))] if v else v

    # Nom et centre (geo.api.gouv.fr) de chaque commune : recherche « autour de moi » sans réseau.
    ref = {r[0]: r[1:] for r in con.execute("SELECT insee, nom, lat, lon FROM communes").fetchall()}
    write_json(out / "supports.json", {
        "version": 1,
        "n": len(rows),
        "deltas": list(deltas),
        "echelles": {"lat": 1e-5, "lon": 1e-5, "h": 0.1, "mois_origine": "1980-01"},
        "dictionnaires": {
            "nat": natures, "tpo": proprios,
            "com": [[c, ref.get(c, (c,))[0],
                     *(round(x, 4) if x is not None else None for x in ref.get(c, (c, None, None))[1:])]
                    for c in communes],
            "ops": [*MOBILE_OPS, "Autres exploitants"],
            "gen": list(GENERATIONS),
            "fam": familles,
        },
        "colonnes": cols,
    })


def _month_sql(col: str) -> str:
    """Mois depuis janvier 1980 (1 = 1980-01), 0 si inconnu : même codage que l'index."""
    return f"coalesce((year({col}) - 1980) * 12 + month({col}), 0)"


def write_services(con: duckdb.DuckDBPyConnection, out: Path, write_json: WriteJson) -> None:
    """Table des services : une ligne par support × exploitant (groupe) × système, avec la date de première
    mise en service et le jeu de bandes de fréquences. Elle permet des filtres croisés exacts côté client
    (« Free en 5G NR 3500 mis en service depuis 2022 »).

    Format : services.json (dictionnaires et disposition) + services.bin.gz, colonnes binaires little-endian
    dans l'ordre des supports de supports.json :
        d   u16[m]  mois de 1re mise en service (0 = inconnu)
        bs  u16[m]  indice du jeu de bandes
        cnt u8[n]   nombre de lignes par support
        grp u8[m]   indice de l'exploitant (groupe)
        sys u8[m]   indice du système
    """
    rows = con.execute(f"""
        WITH ordre AS (
            SELECT sup_id, row_number() OVER (ORDER BY insee, sup_id) - 1 AS pos FROM supports
        ), b AS (
            SELECT emr_id, list([f_deb, f_fin] ORDER BY f_deb, f_fin) AS bl
            FROM bandes WHERE f_deb IS NOT NULL AND f_fin IS NOT NULL GROUP BY emr_id
        ), t AS (
            SELECT ss.sup_id, st.groupe, e.systeme, min(e.date_service) AS d,
                   list_sort(list_distinct(flatten(list(coalesce(b.bl, []))))) AS bands
            FROM emetteurs e
            JOIN stations st USING (sta)
            JOIN support_station ss USING (sta)
            LEFT JOIN b USING (emr_id)
            GROUP BY ALL
        )
        SELECT o.pos, t.groupe, t.systeme, {_month_sql('t.d')} AS mois, t.bands
        FROM t JOIN ordre o USING (sup_id)
        ORDER BY o.pos, t.groupe, t.systeme
    """).fetchall()
    n = con.execute("SELECT count(*) FROM supports").fetchall()[0][0]

    groupes = sorted({r[1] for r in rows})
    systemes = sorted({r[2] for r in rows})
    gi = {g: i for i, g in enumerate(groupes)}
    si = {x: i for i, x in enumerate(systemes)}
    band_sets: dict[tuple, int] = {}
    cnt = [0] * n
    d, bs, grp, sy = array("H"), array("H"), array("B"), array("B")
    for pos, g, x, mois, bands in rows:
        key = tuple(tuple(b) for b in bands)
        cnt[pos] += 1
        d.append(mois)
        bs.append(band_sets.setdefault(key, len(band_sets)))
        grp.append(gi[g])
        sy.append(si[x])
    if max(cnt) > 255 or len(band_sets) > 65535 or len(groupes) > 255 or len(systemes) > 255:
        raise ValueError("dépassement de capacité du format binaire des services")
    if sys.byteorder == "big":
        d.byteswap()
        bs.byteswap()
    payload = d.tobytes() + bs.tobytes() + array("B", cnt).tobytes() + grp.tobytes() + sy.tobytes()
    path = out / "services.bin.gz"
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    print(f"  {path.name} : {len(rows):,} lignes, {path.stat().st_size / 1e3:,.0f} Ko")

    meta = {r[0]: r[1:] for r in con.execute(
        "SELECT libelle, famille, generation, bande FROM ref_systemes").fetchall()}
    cat = dict(con.execute("SELECT DISTINCT groupe, categorie FROM stations").fetchall())
    write_json(out / "services.json", {
        "version": 1,
        "n": n,
        "m": len(rows),
        "colonnes": [["d", "u16"], ["bs", "u16"], ["cnt", "u8", "n"], ["grp", "u8"], ["sys", "u8"]],
        "dictionnaires": {
            "grp": [{"nom": g, "categorie": cat.get(g, "Autre")} for g in groupes],
            "sys": [{"nom": x, "famille": meta.get(x, ("Autre", None, None))[0],
                     "generation": meta.get(x, (None, None, None))[1],
                     "bande": meta.get(x, (None, None, None))[2]} for x in systemes],
            "bandes": [list(map(list, k)) for k in band_sets],
        },
    })


def write_details(con: duckdb.DuckDBPyConnection, out: Path, write_json: WriteJson) -> None:
    """Une fiche par support, regroupée par département. Les émetteurs identiques (même système, même date,
    mêmes bandes) d'une station sont fusionnés avec la liste de leurs antennes : un site trisectoriel tient
    en une ligne par système."""
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _bandes AS
        SELECT emr_id, list([f_deb, f_fin] ORDER BY f_deb, f_fin) AS b
        FROM bandes WHERE f_deb IS NOT NULL AND f_fin IS NOT NULL GROUP BY emr_id;

        CREATE OR REPLACE TEMP TABLE _emr AS
        SELECT e.sta, e.systeme, e.date_service, coalesce(b.b, []) AS b,
               list(DISTINCT e.aer_id ORDER BY e.aer_id) AS aers, count(*) AS n
        FROM emetteurs e LEFT JOIN _bandes b USING (emr_id)
        GROUP BY ALL;

        CREATE OR REPLACE TEMP TABLE _sta AS
        SELECT st.sta, st.exploitant, st.groupe, st.date_implantation, st.date_service, st.date_modif,
               (SELECT list({'s': systeme, 'd': date_service, 'b': b, 'a': aers, 'n': n}
                            ORDER BY systeme, date_service) FROM _emr e WHERE e.sta = st.sta) AS emr
        FROM stations st;

        CREATE OR REPLACE TEMP TABLE _ant AS
        SELECT sup_id, sta, list({'id': aer_id, 't': type_antenne, 'dim': dimension, 'r': rayonnement,
                                  'az': azimut, 'h': hauteur_bas} ORDER BY aer_id) AS ant
        FROM antennes GROUP BY sup_id, sta;
    """)
    deps = [r[0] for r in con.execute("SELECT DISTINCT dep FROM supports ORDER BY 1").fetchall()]
    total = 0
    for dep in deps:
        rows = _rows(con, """
            SELECT s.sup_id AS id, s.lat, s.lon, s.hauteur AS h, s.nature AS nat, s.proprietaire AS tpo,
                   s.adresse AS adr, s.cp, s.insee, s.commune AS com,
                   list({'sta': t.sta, 'exp': t.exploitant, 'grp': t.groupe, 'impl': t.date_implantation,
                         'serv': t.date_service, 'mod': t.date_modif, 'emr': t.emr, 'ant': coalesce(a.ant, [])}
                        ORDER BY t.groupe, t.sta) AS st
            FROM supports s
            JOIN support_station ss USING (sup_id)
            JOIN _sta t ON t.sta = ss.sta
            LEFT JOIN _ant a ON a.sup_id = s.sup_id AND a.sta = t.sta
            WHERE s.dep = ?
            GROUP BY ALL
        """, [dep])
        path = out / "detail" / f"{dep}.json"
        write_json(path, {str(r.pop("id")): r for r in rows}, quiet=True)  # type: ignore[call-arg]
        total += path.stat().st_size
    print(f"  detail/ : {len(deps)} fichiers, {total / 1e6:.1f} Mo")
