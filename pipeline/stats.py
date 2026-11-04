"""Statistiques nationales précalculées -> stats.json (page Statistiques)."""
from __future__ import annotations

import duckdb

# Même ordre que le front (site/src/lib/colors.ts) : il fixe les bits de l'index et les couleurs.
MOBILE_OPS = ("Orange", "Bouygues Telecom", "SFR", "Free")
GENERATIONS = ("2G", "3G", "4G", "5G")


def _rows(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(con: duckdb.DuckDBPyConnection, sql: str) -> object:
    return con.execute(sql).fetchall()[0][0]


def prepare(con: duckdb.DuckDBPyConnection) -> None:
    """Vues de travail communes aux statistiques et aux exports."""
    ops = ", ".join(f"'{o}'" for o in MOBILE_OPS)
    con.execute(f"""
        CREATE OR REPLACE TABLE emr_full AS
        SELECT e.*, st.groupe, st.categorie, st.exploitant, ss.sup_id,
               (st.groupe IN ({ops}) AND e.famille = 'Mobile') AS mobile
        FROM emetteurs e
        JOIN stations st USING (sta)
        JOIN (SELECT sta, min(sup_id) AS sup_id FROM support_station GROUP BY sta) ss USING (sta);

        -- Une station peut être sur plusieurs supports : on rattache ses émetteurs à chacun.
        CREATE OR REPLACE TABLE support_ops AS
        SELECT ss.sup_id,
               list(DISTINCT groupe ORDER BY groupe) AS groupes,
               count(DISTINCT groupe) AS n_groupes,
               count(DISTINCT groupe) FILTER (WHERE mobile) AS n_mobiles,
               count(*) AS n_emetteurs,
               bool_or(mobile AND generation = '5G') AS a_5g,
               bool_or(mobile AND generation = '4G') AS a_4g
        FROM emr_full e JOIN support_station ss ON ss.sta = e.sta GROUP BY ss.sup_id;
    """)


def build(con: duckdb.DuckDBPyConnection) -> dict:
    prepare(con)
    ops_list = list(MOBILE_OPS)

    totaux = {
        "supports": _one(con, "SELECT count(*) FROM supports"),
        "stations": _one(con, "SELECT count(*) FROM stations"),
        "antennes": _one(con, "SELECT count(*) FROM antennes"),
        "emetteurs": _one(con, "SELECT count(*) FROM emetteurs"),
        "bandes": _one(con, "SELECT count(*) FROM bandes"),
        "exploitants": _one(con, "SELECT count(DISTINCT exploitant) FROM stations"),
        "systemes": _one(con, "SELECT count(DISTINCT systeme) FROM emetteurs"),
        "communes": _one(con, "SELECT count(DISTINCT insee) FROM supports"),
        "supports_mobiles": _one(con, "SELECT count(*) FROM support_ops WHERE n_mobiles > 0"),
        "supports_5g": _one(con, "SELECT count(*) FROM support_ops WHERE a_5g"),
    }

    operateurs = _rows(con, """
        SELECT groupe, any_value(categorie) AS categorie,
               count(DISTINCT sta) AS stations, count(DISTINCT sup_id) AS supports, count(*) AS emetteurs,
               count(*) FILTER (WHERE generation = '2G') AS "2G",
               count(*) FILTER (WHERE generation = '3G') AS "3G",
               count(*) FILTER (WHERE generation = '4G') AS "4G",
               count(*) FILTER (WHERE generation = '5G') AS "5G",
               list(DISTINCT exploitant ORDER BY exploitant) AS libelles_anfr
        FROM emr_full GROUP BY groupe ORDER BY stations DESC LIMIT 40
    """)

    familles = _rows(con, """
        SELECT famille, count(*) AS emetteurs, count(DISTINCT sup_id) AS supports,
               count(DISTINCT groupe) AS exploitants
        FROM emr_full GROUP BY famille ORDER BY emetteurs DESC
    """)

    systemes = _rows(con, f"""
        SELECT e.systeme, any_value(e.famille) AS famille, any_value(e.generation) AS generation,
               any_value(e.bande) AS bande, any_value(r.description) AS description,
               count(*) AS emetteurs, count(DISTINCT e.sup_id) AS supports,
               {", ".join(f"count(DISTINCT e.sup_id) FILTER (WHERE e.groupe = '{o}') AS \"{o}\"" for o in ops_list)},
               year(quantile_disc(e.date_service, 0.01)) AS debut_deploiement
        FROM emr_full e LEFT JOIN ref_systemes r ON r.libelle = e.systeme
        GROUP BY e.systeme ORDER BY emetteurs DESC
    """)

    # Sites (supports) par opérateur mobile et par système : la mesure qui compte pour la couverture.
    sites_operateur_systeme = _rows(con, """
        SELECT groupe, systeme, generation, bande, count(DISTINCT sup_id) AS sites, count(*) AS emetteurs
        FROM emr_full WHERE mobile GROUP BY ALL ORDER BY groupe, generation, systeme
    """)

    sites_operateur_generation = _rows(con, """
        SELECT groupe, generation, count(DISTINCT sup_id) AS sites
        FROM emr_full WHERE mobile GROUP BY ALL ORDER BY groupe, generation
    """)

    # Blocs de fréquences effectivement utilisés par chaque opérateur mobile (spectre national).
    spectre = _rows(con, """
        WITH b AS (
            SELECT e.groupe, e.systeme, e.generation, b.f_deb, b.f_fin, count(*) AS n
            FROM bandes b JOIN emr_full e USING (emr_id)
            WHERE e.mobile AND b.statut IN ('ok', 'unité corrigée') AND b.f_fin > b.f_deb
            GROUP BY ALL
        )
        SELECT groupe, systeme, generation, f_deb, f_fin, n,
               n / sum(n) OVER (PARTITION BY groupe, systeme) AS part
        FROM b QUALIFY part >= 0.02 ORDER BY groupe, f_deb
    """)

    departements = _rows(con, """
        WITH s AS (
            SELECT s.dep, count(*) AS supports,
                   count(*) FILTER (WHERE o.n_mobiles > 0) AS sites_mobiles,
                   count(*) FILTER (WHERE o.a_5g) AS sites_5g,
                   count(*) FILTER (WHERE o.n_mobiles >= 4) AS sites_4_operateurs,
                   sum(o.n_emetteurs) AS emetteurs,
                   round(avg(s.hauteur), 1) AS hauteur_moyenne,
                   round(max(s.hauteur), 1) AS hauteur_max
            FROM supports s JOIN support_ops o USING (sup_id) GROUP BY s.dep
        ), c AS (
            SELECT dep, sum(population) AS population, sum(surface_km2) AS surface_km2
            FROM communes WHERE substr(dep, 1, 2) NOT IN ('97', '98') GROUP BY dep
        )
        SELECT s.dep, d.nom, d.region, s.supports, s.sites_mobiles, s.sites_5g, s.sites_4_operateurs,
               s.emetteurs, s.hauteur_moyenne, s.hauteur_max, c.population, round(c.surface_km2) AS surface_km2,
               round(100 * s.supports / c.surface_km2, 2) AS supports_par_100km2,
               round(10000 * s.supports / c.population, 2) AS supports_par_10k_hab,
               round(s.sites_5g / s.sites_mobiles, 4) AS part_5g
        FROM s JOIN departements d USING (dep) JOIN c USING (dep)
        ORDER BY s.dep
    """)

    communes_sql = """
        WITH s AS (
            SELECT s.insee, count(*) AS supports,
                   count(*) FILTER (WHERE o.a_5g) AS sites_5g,
                   sum(o.n_emetteurs) AS emetteurs
            FROM supports s JOIN support_ops o USING (sup_id) GROUP BY s.insee
        )
        SELECT c.insee, c.nom, c.dep, s.supports, s.sites_5g, s.emetteurs, c.population,
               round(c.surface_km2, 2) AS surface_km2,
               round(s.supports / c.surface_km2, 3) AS supports_par_km2,
               round(10000 * s.supports / c.population, 2) AS supports_par_10k_hab
        FROM s JOIN communes c USING (insee)
    """
    communes_top = _rows(con, f"{communes_sql} ORDER BY supports DESC LIMIT 100")
    communes_densite_km2 = _rows(con, f"{communes_sql} WHERE c.population >= 10000 ORDER BY supports_par_km2 DESC LIMIT 50")
    communes_par_hab = _rows(con, f"{communes_sql} WHERE c.population >= 10000 ORDER BY supports_par_10k_hab DESC LIMIT 50")

    support_cols = """s.sup_id, s.hauteur, s.nature, s.proprietaire, s.commune, s.insee, s.dep, s.lat, s.lon,
                      s.adresse, o.groupes, o.n_groupes, o.n_emetteurs"""
    plus_hauts = _rows(con, f"""
        SELECT {support_cols} FROM supports s JOIN support_ops o USING (sup_id)
        WHERE s.hauteur IS NOT NULL ORDER BY s.hauteur DESC LIMIT 50
    """)
    plus_exploitants = _rows(con, f"""
        SELECT {support_cols} FROM supports s JOIN support_ops o USING (sup_id)
        ORDER BY o.n_groupes DESC, o.n_emetteurs DESC LIMIT 50
    """)
    plus_emetteurs = _rows(con, f"""
        SELECT {support_cols} FROM supports s JOIN support_ops o USING (sup_id)
        ORDER BY o.n_emetteurs DESC LIMIT 50
    """)

    partage_mobile = _rows(con, """
        SELECT n_mobiles AS operateurs, count(*) AS supports FROM support_ops
        WHERE n_mobiles > 0 GROUP BY 1 ORDER BY 1
    """)

    natures = _rows(con, """
        SELECT coalesce(nature, 'Inconnue') AS nature, count(*) AS supports, round(avg(hauteur), 1) AS hauteur_moyenne
        FROM supports GROUP BY 1 ORDER BY 2 DESC
    """)
    proprietaires = _rows(con, """
        SELECT coalesce(proprietaire, 'Inconnu') AS proprietaire, count(*) AS supports
        FROM supports GROUP BY 1 ORDER BY 2 DESC LIMIT 30
    """)
    hauteurs = _rows(con, """
        SELECT least(floor(hauteur / 5) * 5, 100)::INTEGER AS de, count(*) AS supports
        FROM supports WHERE hauteur IS NOT NULL GROUP BY 1 ORDER BY 1
    """)

    deploiement = _rows(con, """
        SELECT year(date_service) AS annee, groupe, generation, count(*) AS emetteurs,
               count(DISTINCT sup_id) AS nouveaux_sites
        FROM emr_full WHERE mobile AND date_service IS NOT NULL GROUP BY ALL ORDER BY 1, 2, 3
    """)
    deploiement_systemes = _rows(con, """
        SELECT year(date_service) AS annee, systeme, count(*) AS emetteurs
        FROM emr_full WHERE mobile AND date_service IS NOT NULL GROUP BY ALL ORDER BY 1, 2
    """)

    antennes = {
        "types": _rows(con, """
            SELECT coalesce(type_antenne, 'Inconnu') AS type, count(*) AS antennes
            FROM antennes GROUP BY 1 ORDER BY 2 DESC LIMIT 15"""),
        "azimuts": _rows(con, """
            SELECT (floor(azimut / 10) * 10)::INTEGER AS de, count(*) AS antennes
            FROM antennes WHERE rayonnement = 'D' AND azimut BETWEEN 0 AND 359.999 GROUP BY 1 ORDER BY 1"""),
        "rayonnement": _rows(con, """
            SELECT coalesce(rayonnement, '?') AS rayonnement, count(*) AS antennes FROM antennes GROUP BY 1"""),
    }

    qualite = {r["indicateur"]: r["n"] for r in _rows(con, "SELECT * FROM qualite")}

    return {
        "totaux": totaux,
        "operateurs_mobiles": ops_list,
        "operateurs": operateurs,
        "familles": familles,
        "systemes": systemes,
        "sites_operateur_systeme": sites_operateur_systeme,
        "sites_operateur_generation": sites_operateur_generation,
        "spectre_national": spectre,
        "departements": departements,
        "communes_top": communes_top,
        "communes_densite_km2": communes_densite_km2,
        "communes_par_habitant": communes_par_hab,
        "plus_hauts": plus_hauts,
        "plus_exploitants": plus_exploitants,
        "plus_emetteurs": plus_emetteurs,
        "partage_mobile": partage_mobile,
        "natures": natures,
        "proprietaires": proprietaires,
        "hauteurs": hauteurs,
        "deploiement": deploiement,
        "deploiement_systemes": deploiement_systemes,
        "antennes": antennes,
        "qualite": qualite,
    }
