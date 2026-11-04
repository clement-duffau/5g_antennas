"""Nettoyage et normalisation (SQL DuckDB).

Entrée : tables raw_* (VARCHAR), référentiels communes et tables de correspondance (refs/*.csv).
Sortie : tables propres `supports`, `stations`, `support_station`, `antennes`, `emetteurs`, `bandes`,
plus `qualite` (compteurs de corrections, affichés sur la page méthodologie).
"""
from __future__ import annotations

import duckdb

from .config import (EXCLUDED_INSEE_PREFIXES, GENERIC_F_MAX, GENERIC_F_MIN, MIN_SERVICE_YEAR,
                     REFS_DIR)


def _num(col: str) -> str:
    """VARCHAR à virgule décimale -> DOUBLE (NULL si non numérique)."""
    return f"TRY_CAST(replace(trim({col}), ',', '.') AS DOUBLE)"


def load_refs(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"""
        CREATE OR REPLACE TABLE ref_systemes AS
        SELECT * FROM read_csv('{REFS_DIR / 'systemes.csv'}', header=true,
            columns={{'libelle':'VARCHAR','famille':'VARCHAR','generation':'VARCHAR','bande':'VARCHAR',
                      'f_min':'DOUBLE','f_max':'DOUBLE','description':'VARCHAR'}})
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE ref_exploitants AS
        SELECT * FROM read_csv('{REFS_DIR / 'exploitants.csv'}', header=true,
            columns={{'libelle':'VARCHAR','groupe':'VARCHAR','categorie':'VARCHAR'}})
    """)


def clean(con: duckdb.DuckDBPyConnection, extraction_date: str) -> None:
    """extraction_date : AAAA-MM-JJ, borne haute des dates de mise en service."""
    load_refs(con)
    excluded = ", ".join(f"'{p}'" for p in EXCLUDED_INSEE_PREFIXES)

    # ------------------------------------------------------------------ supports
    # SUP_SUPPORT est une table de liaison support × station : un support = un SUP_ID.
    con.execute(f"""
        CREATE OR REPLACE TABLE support_station AS
        SELECT DISTINCT CAST(SUP_ID AS INTEGER) AS sup_id, STA_NM_ANFR AS sta
        FROM raw_sup_support
        WHERE substr(COM_CD_INSEE, 1, 2) NOT IN ({excluded});

        CREATE OR REPLACE TABLE supports AS
        WITH s AS (
            SELECT *, row_number() OVER (PARTITION BY SUP_ID ORDER BY STA_NM_ANFR) AS rn
            FROM raw_sup_support
            WHERE substr(COM_CD_INSEE, 1, 2) NOT IN ({excluded})
        ), c AS (
            SELECT
                CAST(SUP_ID AS INTEGER) AS sup_id,
                round((CAST(COR_NB_DG_LAT AS DOUBLE) + CAST(COR_NB_MN_LAT AS DOUBLE) / 60
                       + CAST(COR_NB_SC_LAT AS DOUBLE) / 3600)
                      * CASE WHEN COR_CD_NS_LAT = 'S' THEN -1 ELSE 1 END, 6) AS lat,
                round((CAST(COR_NB_DG_LON AS DOUBLE) + CAST(COR_NB_MN_LON AS DOUBLE) / 60
                       + CAST(COR_NB_SC_LON AS DOUBLE) / 3600)
                      * CASE WHEN COR_CD_EW_LON = 'W' THEN -1 ELSE 1 END, 6) AS lon,
                CAST(NAT_ID AS INTEGER) AS nat_id,
                {_num('SUP_NM_HAUT')} AS hauteur_brute,
                TRY_CAST(TPO_ID AS INTEGER) AS tpo_id,
                nullif(trim(concat_ws(', ', nullif(trim(ADR_LB_LIEU), ''), nullif(trim(ADR_LB_ADD1), ''),
                                      nullif(trim(ADR_LB_ADD2), ''), nullif(trim(ADR_LB_ADD3), ''))), '') AS adresse,
                ADR_NM_CP AS cp,
                COM_CD_INSEE AS insee_anfr
            FROM s WHERE rn = 1
        )
        SELECT c.*,
            CASE WHEN hauteur_brute > 0 THEN hauteur_brute END AS hauteur,
            n.NAT_LB_NOM AS nature,
            p.TPO_LB AS proprietaire
        FROM c
        LEFT JOIN raw_sup_nature n ON CAST(n.NAT_ID AS INTEGER) = c.nat_id
        LEFT JOIN raw_sup_proprietaire p ON TRY_CAST(p.TPO_ID AS INTEGER) = c.tpo_id;
    """)

    # Rattachement communal : commune actuelle, arrondissement -> commune, sinon centre le plus proche.
    con.execute("""
        CREATE OR REPLACE TABLE _rattachement AS
        WITH direct AS (
            SELECT s.sup_id, s.insee_anfr AS insee, 'direct' AS methode
            FROM supports s JOIN communes c ON c.insee = s.insee_anfr
        ), arr AS (
            SELECT s.sup_id, a.parent AS insee, 'arrondissement' AS methode
            FROM supports s JOIN arrondissements a ON a.insee = s.insee_anfr
            WHERE s.sup_id NOT IN (SELECT sup_id FROM direct)
        ), reste AS (
            SELECT * FROM supports
            WHERE sup_id NOT IN (SELECT sup_id FROM direct UNION ALL SELECT sup_id FROM arr)
        ), proche AS (
            SELECT r.sup_id, c.insee, 'commune la plus proche' AS methode,
                   row_number() OVER (PARTITION BY r.sup_id
                       ORDER BY (c.lat - r.lat) ^ 2 + ((c.lon - r.lon) * cos(radians(r.lat))) ^ 2) AS rn
            FROM reste r JOIN communes c
              ON c.lat BETWEEN r.lat - 0.2 AND r.lat + 0.2 AND c.lon BETWEEN r.lon - 0.3 AND r.lon + 0.3
        )
        SELECT * FROM direct UNION ALL SELECT * FROM arr
        UNION ALL SELECT sup_id, insee, methode FROM proche WHERE rn = 1;

        CREATE OR REPLACE TABLE supports AS
        SELECT s.*, r.insee, r.methode AS rattachement, c.nom AS commune, c.dep
        FROM supports s
        LEFT JOIN _rattachement r USING (sup_id)
        LEFT JOIN communes c ON c.insee = r.insee;
    """)

    # ------------------------------------------------------------------ stations
    con.execute("""
        CREATE OR REPLACE TABLE stations AS
        SELECT
            s.STA_NM_ANFR AS sta,
            CAST(s.ADM_ID AS INTEGER) AS adm_id,
            e.ADM_LB_NOM AS exploitant,
            coalesce(r.groupe, e.ADM_LB_NOM, 'Inconnu') AS groupe,
            coalesce(r.categorie, 'Autre') AS categorie,
            TRY_STRPTIME(s.DTE_IMPLANTATION, '%d/%m/%Y')::DATE AS date_implantation,
            TRY_STRPTIME(s.DTE_MODIF, '%d/%m/%Y')::DATE AS date_modif,
            TRY_STRPTIME(s.DTE_EN_SERVICE, '%d/%m/%Y')::DATE AS date_service
        FROM raw_sup_station s
        LEFT JOIN raw_sup_exploitant e ON e.ADM_ID = s.ADM_ID
        LEFT JOIN ref_exploitants r ON r.libelle = e.ADM_LB_NOM
        WHERE s.STA_NM_ANFR IN (SELECT sta FROM support_station);
    """)

    # ------------------------------------------------------------------ antennes
    con.execute(f"""
        CREATE OR REPLACE TABLE antennes AS
        SELECT DISTINCT
            a.STA_NM_ANFR AS sta, CAST(a.AER_ID AS BIGINT) AS aer_id, CAST(a.SUP_ID AS INTEGER) AS sup_id,
            TRY_CAST(a.TAE_ID AS INTEGER) AS tae_id, t.TAE_LB AS type_antenne,
            {_num('a.AER_NB_DIMENSION')} AS dimension,
            nullif(trim(a.AER_FG_RAYON), '') AS rayonnement,
            {_num('a.AER_NB_AZIMUT')} AS azimut,
            {_num('a.AER_NB_ALT_BAS')} AS hauteur_bas
        FROM raw_sup_antenne a
        LEFT JOIN raw_sup_type_antenne t ON t.TAE_ID = a.TAE_ID
        WHERE a.STA_NM_ANFR IN (SELECT sta FROM stations);
    """)

    # ------------------------------------------------------------------ émetteurs
    con.execute(f"""
        CREATE OR REPLACE TABLE emetteurs AS
        WITH e AS (
            SELECT
                CAST(EMR_ID AS BIGINT) AS emr_id, STA_NM_ANFR AS sta, CAST(AER_ID AS BIGINT) AS aer_id,
                CASE WHEN nullif(trim(EMR_LB_SYSTEME), '') IS NULL OR trim(EMR_LB_SYSTEME) = '0'
                     THEN 'Inconnu' ELSE trim(EMR_LB_SYSTEME) END AS systeme,
                EMR_DT_SERVICE AS date_brute,
                TRY_STRPTIME(EMR_DT_SERVICE, '%d/%m/%Y')::DATE AS d
            FROM raw_sup_emetteur
            WHERE STA_NM_ANFR IN (SELECT sta FROM stations)
        )
        SELECT e.emr_id, e.sta, e.aer_id, e.systeme,
            coalesce(r.famille, 'Autre') AS famille, r.generation, r.bande,
            CASE WHEN year(d) >= {MIN_SERVICE_YEAR} AND d <= DATE '{extraction_date}' THEN d END AS date_service,
            CASE WHEN date_brute IS NULL OR trim(date_brute) = '' THEN 'absente'
                 WHEN d IS NULL THEN 'illisible'
                 WHEN year(d) < {MIN_SERVICE_YEAR} THEN 'trop ancienne'
                 WHEN d > DATE '{extraction_date}' THEN 'future'
                 ELSE 'ok' END AS date_statut
        FROM e LEFT JOIN ref_systemes r ON r.libelle = e.systeme;
    """)

    # ------------------------------------------------------------------ bandes
    # Conversion en MHz puis correction des erreurs d'unité (×1000 / ÷1000) borne par borne,
    # en comparant à la fenêtre attendue du système (ou à une fenêtre générique).
    con.execute(f"""
        CREATE OR REPLACE TABLE bandes AS
        WITH b AS (
            SELECT
                CAST(b.BAN_ID AS BIGINT) AS ban_id, CAST(b.EMR_ID AS BIGINT) AS emr_id,
                {_num('b.BAN_NB_F_DEB')} * m.k AS f0, {_num('b.BAN_NB_F_FIN')} * m.k AS f1,
                nullif(trim(b.BAN_FG_UNITE), '') AS unite,
                coalesce(r.f_min, {GENERIC_F_MIN}) - 1e-6 AS wmin,
                coalesce(r.f_max, {GENERIC_F_MAX}) + 1e-6 AS wmax
            FROM raw_sup_bande b
            JOIN emetteurs e ON e.emr_id = CAST(b.EMR_ID AS BIGINT)
            LEFT JOIN ref_systemes r ON r.libelle = e.systeme
            LEFT JOIN (VALUES ('K', 0.001), ('M', 1.0), ('G', 1000.0)) m(u, k)
                   ON m.u = coalesce(nullif(trim(b.BAN_FG_UNITE), ''), 'M')
        ), fix AS (
            SELECT *,
                CASE WHEN f0 BETWEEN wmin AND wmax THEN f0
                     WHEN f0 / 1000 BETWEEN wmin AND wmax THEN f0 / 1000
                     WHEN f0 * 1000 BETWEEN wmin AND wmax THEN f0 * 1000 END AS g0,
                CASE WHEN f1 BETWEEN wmin AND wmax THEN f1
                     WHEN f1 / 1000 BETWEEN wmin AND wmax THEN f1 / 1000
                     WHEN f1 * 1000 BETWEEN wmin AND wmax THEN f1 * 1000 END AS g1
            FROM b
        )
        SELECT ban_id, emr_id, unite,
            round(coalesce(g0, f0), 4) AS f_deb, round(coalesce(g1, f1), 4) AS f_fin,
            CASE WHEN f0 IS NULL OR f1 IS NULL THEN 'vide'
                 WHEN g0 IS NULL OR g1 IS NULL OR g0 > g1 THEN 'suspecte'
                 WHEN g0 <> f0 OR g1 <> f1 THEN 'unité corrigée'
                 ELSE 'ok' END AS statut
        FROM fix;
    """)

    # ------------------------------------------------------------------ qualité
    con.execute("""
        CREATE OR REPLACE TABLE qualite AS
        SELECT 'supports_hauteur_invalide' AS indicateur, count(*) AS n FROM supports WHERE hauteur IS NULL
        UNION ALL SELECT 'rattachement_' || replace(rattachement, ' ', '_'), count(*) FROM supports GROUP BY rattachement
        UNION ALL SELECT 'supports_sans_commune', count(*) FROM supports WHERE insee IS NULL
        UNION ALL SELECT 'emetteurs_date_' || replace(date_statut, ' ', '_'), count(*) FROM emetteurs GROUP BY date_statut
        UNION ALL SELECT 'emetteurs_systeme_inconnu', count(*) FROM emetteurs WHERE systeme = 'Inconnu'
        UNION ALL SELECT 'emetteurs_systeme_non_reference', count(*) FROM emetteurs e
            WHERE systeme <> 'Inconnu' AND systeme NOT IN (SELECT libelle FROM ref_systemes)
        UNION ALL SELECT 'bandes_' || replace(statut, ' ', '_'), count(*) FROM bandes GROUP BY statut
        UNION ALL SELECT 'exploitants_non_references', count(DISTINCT exploitant) FROM stations
            WHERE exploitant NOT IN (SELECT libelle FROM ref_exploitants);
    """)
