# Atlas des antennes radio en France

Site statique pour explorer les **installations radioélectriques de plus de 5 W** déclarées à l'ANFR en
France métropolitaine : supports (pylônes, toits, châteaux d'eau…), exploitants, technologies
(GSM, UMTS, LTE, 5G NR, FM, TNT, PMR, faisceaux hertziens…), bandes de fréquences et dates de mise en service.

Les données sont régénérées chaque mois par une GitHub Action, puis le site est publié sur GitHub Pages.

> Le jeu ANFR exclut les installations de l'Aviation civile, de la Défense et du ministère de l'Intérieur.

## État d'avancement

| Étape | Contenu | État |
|---|---|---|
| 1 | Pipeline, statistiques, page Statistiques, déploiement | fait |
| 2 | Carte des supports et fiche support | à faire |
| 3 | Filtres combinables | à faire |
| 4 | Recherche « autour de moi » | à faire |
| 5 | Frise du déploiement (avec les archives depuis 2018) | à faire |
| 6 | Spectre d'une zone | à faire |
| 7 | Finitions, page À propos complète | en partie (page À propos déjà en ligne) |

## Démarrage rapide

Prérequis : Python 3.11+ et Node.js 20+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python -m pipeline build
```

```bash
cd site && npm install && npm run dev
```

`python -m pipeline build` télécharge la dernière extraction ANFR (~66 Mo) et le référentiel des communes,
nettoie les données et écrit les fichiers du site dans `site/public/data/`. Il faut compter environ
une minute une fois les fichiers téléchargés.

### Commandes du pipeline

| Commande | Effet |
|---|---|
| `python -m pipeline build` | dernière extraction publiée |
| `python -m pipeline build --extraction 20260831` | une extraction précise (AAAAMMJJ) |
| `python -m pipeline build --zip data.zip ref.zip --date 2026-09-30` | archives déjà téléchargées, sans réseau ANFR |
| `python -m pipeline build --refresh-geo` | re-télécharge le référentiel communes |
| `python -m pytest tests` | tests du nettoyage sur un mini-jeu synthétique |
| `python scripts/explore.py` | régénère le rapport brut `docs/data-exploration-annexe.md` |

### Commandes du site (`site/`)

| Commande | Effet |
|---|---|
| `npm run dev` | serveur de développement |
| `npm run check` | vérification des types (svelte-check) |
| `npm run build` | build statique dans `site/dist/` |

## Architecture

```
pipeline/                 Python + DuckDB
  fetch.py                découverte des extractions via l'API data.gouv.fr, téléchargement avec reprise
  load.py                 extraction des zip, détection d'encodage (UTF-8 / Windows-1252), tables brutes
  communes.py             référentiel geo.api.gouv.fr (population, superficie, arrondissements)
  clean.py                nettoyage : supports dédoublonnés, DMS -> WGS84, unités de fréquence,
                          dates, rattachement communal, indicateurs de qualité
  stats.py                stats.json
  export.py               communes.json, departements.json (puis index de la carte, détails…)
  refs/systemes.csv       système ANFR -> famille, génération, bande, fenêtre de fréquences attendue
  refs/exploitants.csv    libellé ANFR -> groupe, catégorie
site/                     Vite + Svelte 5 + TypeScript, sans backend
  src/pages/              Statistiques, À propos
  src/lib/charts/         graphiques SVG faits main (spectre, barres, colonnes, rose des azimuts)
  src/lib/ui/             tableau triable, sections, puces de filtre, infobulle
docs/                     exploration des données (synthèse + annexe générée)
tests/                    tests pytest du nettoyage
.github/workflows/        ci.yml (tests + build), deploy.yml (données mensuelles + Pages)
```

### Choix techniques

- **DuckDB** lit directement les CSV ANFR à virgule décimale et fait les jointures sur 2,4 M émetteurs
  et 4,7 M bandes en quelques secondes, avec peu de mémoire.
- **Filtrage côté navigateur plutôt que tuiles vectorielles.** Avec ~93 000 supports en métropole, un index
  compact tient en mémoire et permet des filtres combinés exacts (opérateur × système × bande × date),
  ce que des PMTiles ne permettent pas sur des attributs à plusieurs valeurs. Le détail d'un support
  (émetteurs, bandes, antennes) sera découpé par département et chargé à la demande.
- **Aucune donnée générée n'est commitée.** Les archives brutes (`data/raw/`), le cache et `site/public/data/`
  sont ignorés par git ; la CI les reconstruit et publie le résultat comme artefact GitHub Pages.
- **Svelte 5** pour un front léger et réactif. Les graphiques sont écrits à la main en SVG
  (~32 Ko gzip de JavaScript pour tout le site à ce stade).

## Déploiement

1. Dans le dépôt GitHub : *Settings → Pages → Build and deployment → Source : **GitHub Actions***.
2. Le workflow `deploy.yml` s'exécute à chaque push sur `main`, les 9 et 16 de chaque mois
   (après la publication ANFR) et à la demande (onglet *Actions*, avec une extraction au choix).

## Sources et licence

- ANFR, [Données sur les installations radioélectriques de plus de 5 watts](https://www.data.gouv.fr/fr/datasets/donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1/),
  Licence Ouverte 2.0.
- [geo.api.gouv.fr](https://geo.api.gouv.fr/) (populations et superficies communales).

Les limites et traitements des données sont décrits dans [`docs/data-exploration.md`](docs/data-exploration.md)
et sur la page *À propos* du site.
