"""Tests du nettoyage sur un mini-jeu de données synthétique (aucun accès réseau)."""
from __future__ import annotations

import duckdb
import pytest

from pipeline import clean, load

H = {
    "SUP_SUPPORT": "SUP_ID;STA_NM_ANFR;NAT_ID;COR_NB_DG_LAT;COR_NB_MN_LAT;COR_NB_SC_LAT;COR_CD_NS_LAT;"
                   "COR_NB_DG_LON;COR_NB_MN_LON;COR_NB_SC_LON;COR_CD_EW_LON;SUP_NM_HAUT;TPO_ID;ADR_LB_LIEU;"
                   "ADR_LB_ADD1;ADR_LB_ADD2;ADR_LB_ADD3;ADR_NM_CP;COM_CD_INSEE",
    "SUP_STATION": "STA_NM_ANFR;ADM_ID;DEM_NM_COMSIS;DTE_IMPLANTATION;DTE_MODIF;DTE_EN_SERVICE;STA_NM_USER",
    "SUP_ANTENNE": "STA_NM_ANFR;AER_ID;TAE_ID;AER_NB_DIMENSION;AER_FG_RAYON;AER_NB_AZIMUT;AER_NB_ALT_BAS;SUP_ID",
    "SUP_EMETTEUR": "EMR_ID;EMR_LB_SYSTEME;STA_NM_ANFR;AER_ID;EMR_DT_SERVICE",
    "SUP_BANDE": "STA_NM_ANFR;BAN_ID;EMR_ID;BAN_NB_F_DEB;BAN_NB_F_FIN;BAN_FG_UNITE",
    "SUP_EXPLOITANT": "ADM_ID;ADM_LB_NOM",
    "SUP_NATURE": "NAT_ID;NAT_LB_NOM",
    "SUP_PROPRIETAIRE": "TPO_ID;TPO_LB",
    "SUP_TYPE_ANTENNE": "TAE_ID;TAE_LB",
}
ROWS = {
    # Support 1 (Rennes) porte deux stations ; support 2 à Paris 17e ; support 3 à La Réunion (exclu).
    "SUP_SUPPORT": [
        "1;A;23;48;6;36;N;1;40;48;W;30,5;32;;Rue X;;;35000;35238",
        "1;B;23;48;6;36;N;1;40;48;W;30,5;32;;Rue X;;;35000;35238",
        "2;C;4;48;53;0;N;2;18;0;E;-3;;;;;;75017;75117",
        "3;D;23;21;0;0;S;55;30;0;E;20;32;;;;;97400;97411",
    ],
    "SUP_STATION": ["A;1;1;01/01/2010;;01/02/2010;1", "B;2;2;01/01/2015;;;2",
                    "C;1;3;01/01/2020;;;1", "D;1;4;01/01/2020;;;1"],
    "SUP_ANTENNE": ["A;10;16;2,7;D;120;28,5;1", "B;10;16;2,7;D;120;28,5;1", "C;11;16;1;N;;10;2", "D;12;16;1;D;0;10;3"],
    "SUP_EMETTEUR": [
        "100;LTE 800;A;10;15/03/2014",
        "101;5G NR 3500;B;10;01/01/2031",
        "102;FH;C;11;31/12/0025",
        "103;;C;11;",
        "104;LTE 800;D;12;01/01/2015",
    ],
    "SUP_BANDE": [
        "A;1;100;791;801;M",
        "A;2;100;832000;842000;M",   # kHz saisis en MHz -> corrigé
        "B;3;101;3,49;3,57;G",        # GHz -> 3490-3570 MHz
        "C;4;102;18;19;G",
        "C;5;102;;;",
        "B;6;101;100;200;M",          # hors bande 3,5 GHz -> suspecte
    ],
    "SUP_EXPLOITANT": ["1;ORANGE", "2;SFR"],
    "SUP_NATURE": ["23;Pylône autostable", "4;Immeuble"],
    "SUP_PROPRIETAIRE": ["32;TDF"],
    "SUP_TYPE_ANTENNE": ["16;Panneau"],
}


@pytest.fixture()
def con(tmp_path):
    files = {}
    for t, header in H.items():
        p = tmp_path / f"{t}.txt"
        p.write_text("\n".join([header, *ROWS[t]]) + "\n", encoding="utf-8")
        files[t] = p
    c = duckdb.connect()
    load.load(c, files)
    c.execute("""
        CREATE TABLE communes (insee VARCHAR, nom VARCHAR, dep VARCHAR, population INTEGER,
                               surface_km2 DOUBLE, lon DOUBLE, lat DOUBLE);
        INSERT INTO communes VALUES ('35238', 'Rennes', '35', 220000, 50.4, -1.68, 48.11),
                                    ('75056', 'Paris', '75', 2100000, 105.4, 2.35, 48.86);
        CREATE TABLE arrondissements (insee VARCHAR, nom VARCHAR, parent VARCHAR);
        INSERT INTO arrondissements VALUES ('75117', 'Paris 17e', '75056');
    """)
    clean.clean(c, "2026-09-30")
    return c


def q(con, sql):
    return con.execute(sql).fetchall()


def test_detect_encoding():
    assert load.detect_encoding("Château".encode("utf-8")) == "utf-8"
    assert load.detect_encoding("Château".encode("cp1252")) == "cp1252"
    assert load.detect_encoding(b"\xef\xbb\xbfabc") == "utf-8-sig"


def test_supports_dedoublonnes_et_metropole(con):
    assert q(con, "SELECT sup_id FROM supports ORDER BY 1") == [(1,), (2,)]
    assert q(con, "SELECT count(*) FROM support_station WHERE sup_id = 1") == [(2,)]


def test_coordonnees_dms(con):
    lat, lon = q(con, "SELECT lat, lon FROM supports WHERE sup_id = 1")[0]
    assert lat == pytest.approx(48 + 6 / 60 + 36 / 3600, abs=1e-6)
    assert lon == pytest.approx(-(1 + 40 / 60 + 48 / 3600), abs=1e-6)


def test_hauteur(con):
    assert q(con, "SELECT sup_id, hauteur FROM supports ORDER BY 1") == [(1, 30.5), (2, None)]


def test_rattachement_arrondissement(con):
    assert q(con, "SELECT insee, commune, rattachement FROM supports WHERE sup_id = 2") == \
        [("75056", "Paris", "arrondissement")]


def test_exploitants_regroupes(con):
    assert q(con, "SELECT sta, groupe, categorie FROM stations ORDER BY 1") == \
        [("A", "Orange", "Opérateur mobile"), ("B", "SFR", "Opérateur mobile"),
         ("C", "Orange", "Opérateur mobile")]


def test_dates_et_systemes(con):
    rows = q(con, "SELECT emr_id, systeme, generation, date_service, date_statut FROM emetteurs ORDER BY 1")
    assert [(r[0], r[1], r[2], r[4]) for r in rows] == [
        (100, "LTE 800", "4G", "ok"),
        (101, "5G NR 3500", "5G", "future"),
        (102, "FH", None, "trop ancienne"),
        (103, "Inconnu", None, "absente"),
    ]
    assert str(rows[0][3]) == "2014-03-15"
    assert rows[1][3] is None


def test_frequences(con):
    rows = dict((r[0], r[1:]) for r in q(con, "SELECT ban_id, f_deb, f_fin, statut FROM bandes"))
    assert rows[1] == (791.0, 801.0, "ok")
    assert rows[2] == (832.0, 842.0, "unité corrigée")
    assert rows[3] == (3490.0, 3570.0, "ok")
    assert rows[4] == (18000.0, 19000.0, "ok")
    assert rows[5][2] == "vide"
    assert rows[6][2] == "suspecte"


def test_export_index_et_details(con, tmp_path):
    import json
    from pipeline import export, stats

    stats.prepare(con)
    written = {}

    def write_json(path, data, quiet=False):
        written[path.name if path.parent.name != "detail" else f"detail/{path.name}"] = data
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, default=str), encoding="utf-8")

    export.write_index(con, tmp_path, write_json)
    export.write_details(con, tmp_path, write_json)

    idx = written["supports.json"]
    cols = idx["colonnes"]
    for k in idx["deltas"]:  # décodage différentiel, comme le front
        for i in range(1, len(cols[k])):
            cols[k][i] += cols[k][i - 1]
    assert idx["n"] == 2
    i1 = cols["id"].index(1)
    assert cols["lat"][i1] == round((48 + 6 / 60 + 36 / 3600) * 1e5)
    assert idx["dictionnaires"]["com"][0] == ["35238", "Rennes", 48.11, -1.68]
    assert idx["dictionnaires"]["ops"][:4] == ["Orange", "Bouygues Telecom", "SFR", "Free"]
    assert cols["ops"][i1] == 0b00101                        # Orange (bit 0) et SFR (bit 2)
    assert cols["gen"][i1] == 0b1100                         # 4G et 5G (une date invalide n'exclut pas l'émetteur)
    assert set(written) >= {"detail/35.json", "detail/75.json"}
    fiche = written["detail/35.json"]["1"]
    assert {s["grp"] for s in fiche["st"]} == {"Orange", "SFR"}
    emr = next(s for s in fiche["st"] if s["grp"] == "Orange")["emr"][0]
    assert emr["s"] == "LTE 800" and emr["b"] == [[791.0, 801.0], [832.0, 842.0]]


def test_export_services_binaire(con, tmp_path):
    import gzip
    import json
    import struct
    from pipeline import export, stats

    stats.prepare(con)
    export.write_services(con, tmp_path, lambda p, d, quiet=False: p.write_text(json.dumps(d), encoding="utf-8"))
    meta = json.loads((tmp_path / "services.json").read_text(encoding="utf-8"))
    raw = gzip.decompress((tmp_path / "services.bin.gz").read_bytes())
    n, m = meta["n"], meta["m"]
    assert len(raw) == 2 * m + 2 * m + n + m + m
    d = struct.unpack(f"<{m}H", raw[:2 * m])
    bs = struct.unpack(f"<{m}H", raw[2 * m:4 * m])
    cnt = list(raw[4 * m:4 * m + n])
    grp = list(raw[4 * m + n:5 * m + n])
    sy = list(raw[5 * m + n:])
    assert sum(cnt) == m
    D = meta["dictionnaires"]
    lignes = {(D["grp"][g]["nom"], D["sys"][x]["nom"]): (mois, D["bandes"][b]) for g, x, mois, b in zip(grp, sy, d, bs)}
    # support 1 (premier dans l'ordre INSEE 35238 < 75056) : Orange LTE 800 et SFR 5G NR 3500
    assert cnt[0] == 2
    assert lignes[("Orange", "LTE 800")] == ((2014 - 1980) * 12 + 3, [[791.0, 801.0], [832.0, 842.0]])
    assert lignes[("SFR", "5G NR 3500")][0] == 0           # date future -> inconnue
    assert D["sys"][sy[0]]["famille"] in {"Mobile"}


def test_historique_agregat_et_series(con, tmp_path):
    from pipeline import history

    agg = history.aggregate(con)
    # Métropole seulement : supports 1 et 2 ; émetteurs 100 à 103 (104 est à La Réunion).
    assert agg["supports"] == 2 and agg["emetteurs"] == 4
    assert agg["sites"]["Orange"]["4G"] == 1 and agg["sites"]["Orange"]["total"] == 1
    assert agg["sites"]["SFR"]["5G"] == 1 and agg["sites"]["Free"]["total"] == 0
    assert agg["systemes"]["LTE 800"] == {"total": 1, "Orange": 1}
    history.save("20250930", {**agg, "supports": 1}, tmp_path)
    history.save("20260930", agg, tmp_path)
    s = history.assemble(tmp_path)
    assert s["mois"] == ["2025-09", "2026-09"] and s["supports"] == [1, 2]
    assert s["sites"]["SFR"]["5G"] == [1, 1]
    assert s["systemes"]["5G NR 3500"]["SFR"] == [1, 1]
