# Exploration des données ANFR

Synthèse de l'exploration de l'extraction du **30/09/2026** (publiée le 06/10/2026).
Les tableaux bruts (toutes les colonnes, valeurs fréquentes, comptages) sont dans
[`data-exploration-annexe.md`](data-exploration-annexe.md), générée par `scripts/explore.py`.
Les contrôles complémentaires viennent de `scripts/explore_checks.py`.

## 1. Publication sur data.gouv.fr

- Jeu `551d4ff3c751df55da0cd89f`, licence **Licence Ouverte v2** (`lov2`), fréquence mensuelle.
- **Deux zip par mois**, repérés par la date d'extraction en tête du nom de fichier :
  - `AAAAMMJJ-export-etalab-data.zip` (~66 Mo compressés, ~385 Mo décompressés) : `SUP_STATION`, `SUP_SUPPORT`, `SUP_ANTENNE`, `SUP_EMETTEUR`, `SUP_BANDE` ;
  - `AAAAMMJJ-export-etalab-ref.zip` (~5 Ko) : tables de référence `SUP_EXPLOITANT`, `SUP_NATURE`, `SUP_PROPRIETAIRE`, `SUP_TYPE_ANTENNE`.
- **92 extractions archivées**, d'août 2018 à septembre 2026 (279 zip au total), toutes encore en ligne.
  Elles permettent de reconstituer l'évolution du parc mois par mois, suppressions comprises.
- Le nom de fichier change parfois (`…-data-1.zip` en juillet 2025) : le pipeline sélectionne les ressources par la regex `/(\d{8})-export-etalab-(data|ref)`, jamais par une URL fixe.
- Le serveur coupe parfois les connexions (*connection reset*) : le téléchargement doit faire plusieurs tentatives et reprendre là où il s'est arrêté (`Range`). C'est déjà implémenté.

## 2. Format des fichiers

| Fichier | Lignes | Colonnes | Décompressé |
|---|---:|---:|---:|
| SUP_SUPPORT | 199 016 | 19 | 18,7 Mo |
| SUP_STATION | 197 902 | 7 | 11,2 Mo |
| SUP_ANTENNE | 673 480 | 8 | 29,9 Mo |
| SUP_EMETTEUR | 2 510 927 | 5 | 118,6 Mo |
| SUP_BANDE | 4 846 820 | 6 | 204,9 Mo |
| tables de référence | 38 à 188 | 2 | < 10 Ko |

- **Encodage : tous les fichiers de cette extraction sont en UTF-8** (décodage strict réussi), y compris
  SUP_SUPPORT (`Château`, `Pylône`, `n°9` sont corrects). L'hypothèse Windows-1252 ne se vérifie pas
  pour ce mois. Elle a pu être vraie sur d'anciennes extractions : le pipeline garde donc une détection
  fichier par fichier (UTF-8 strict, sinon cp1252), ce qui comptera pour l'historique depuis 2018.
- Séparateur `;`, fins de ligne CRLF, en-tête présent, **virgule décimale** (`2,7`, `906,2`).
- Dates au format `JJ/MM/AAAA`.

## 3. Modèle de données et jointures

```
SUP_EXPLOITANT (ADM_ID) ─┐
                         SUP_STATION (STA_NM_ANFR) ──┬── SUP_SUPPORT (SUP_ID, STA_NM_ANFR) ── NAT_ID, TPO_ID
                                                     ├── SUP_ANTENNE (AER_ID, STA_NM_ANFR, SUP_ID) ── TAE_ID
                                                     └── SUP_EMETTEUR (EMR_ID, STA_NM_ANFR, AER_ID)
                                                              └── SUP_BANDE (BAN_ID, EMR_ID)
```

- **Support** = l'objet physique (pylône, toit, château d'eau). **Station** = une installation d'un exploitant,
  avec un seul `ADM_ID`. Un support porte en moyenne 2 stations, jusqu'à 44.
- **`SUP_SUPPORT` n'est pas une table de supports** mais une table de liaison support × station :
  199 016 lignes pour **98 980 supports distincts**. Les attributs du support (coordonnées, nature,
  hauteur, propriétaire, commune) sont identiques sur toutes les lignes d'un même `SUP_ID` (vérifié :
  0 incohérence). Il faut donc dédoublonner sur `SUP_ID`.
- Une station est presque toujours sur un seul support (197 171 cas) ; 716 stations sont sur 2 à 5 supports.
- `AER_ID` n'est pas unique dans SUP_ANTENNE : 83 022 antennes sont partagées entre deux stations,
  sur le même support (RAN-sharing, typiquement Bouygues/SFR). Pour joindre, il faut la clé `(STA_NM_ANFR, AER_ID)`.
- Le plus souvent, un émetteur a **2 bandes** (voie montante et voie descendante) : 2,18 M émetteurs sur 2,51 M.
- Orphelins négligeables : 2 émetteurs et 1 ligne support sans station, 884 émetteurs sans antenne,
  17 bandes sans émetteur, 7 émetteurs sans bande.
- Les 98 980 supports ont tous au moins un émetteur.

## 4. Coordonnées

- Format **DMS entier** sur 8 colonnes : `COR_NB_DG/MN/SC_LAT`, `COR_CD_NS_LAT` (N/S), idem pour LON avec `COR_CD_EW_LON` (E/W).
  Conversion : `±(deg + min/60 + sec/3600)`. La précision est d'une seconde (~30 m).
- Déjà en WGS84 : la métropole tombe entièrement dans la boîte 41–51,5° N / 5,5° W–10° E (0 point hors boîte).
- Une seconde vaut `60` (cas limite, sans conséquence pour la conversion).
- **Outre-mer inclus** : 5 608 supports en 97x/98x (974 La Réunion 1 497, 987 Polynésie 1 009,
  988 Nouvelle-Calédonie 944, Antilles, Guyane, Mayotte, Saint-Martin, SPM, Wallis-et-Futuna, TAAF jusqu'à 66,7° S).
  La carte aura besoin de raccourcis de navigation vers ces territoires.

## 5. Rattachement géographique

- `COM_CD_INSEE` est toujours renseigné (5 caractères, `2A`/`2B` pour la Corse). `ADR_NM_CP` est le code postal.
- Le département se déduit de l'INSEE : 2 caractères, ou 3 pour `97x`/`98x`.
- Le référentiel `geo.api.gouv.fr/communes` (34 969 communes, avec `population` et `surface` en hectares)
  **ne couvre pas 4 930 supports** (5 %) :
  - arrondissements municipaux de Paris (`751xx`, 2 993 supports), Marseille (`132xx`, 1 101) et Lyon (`6938x`, ~713) ;
  - quelques communes déléguées ou fusionnées (49, 12, 79, 85…).

  Correctif : rattacher les arrondissements à la commune (75056, 13055, 69123) et passer les anciens
  codes par la table des communes déléguées (`type=commune-deleguee,commune-associee`, via `chefLieu`).
  Tous les supports pourront alors être rattachés à une commune avec sa population et sa surface.

## 6. Supports

- **Nature** (`NAT_ID`, 34 valeurs utilisées sur 38) : pylône autostable 44 210, bâtiment 15 769,
  immeuble 14 187, pylône tubulaire 9 236, château d'eau 3 920, mâts, monuments religieux 1 089, tunnels 1 071, pylône arbre 882…
- **Propriétaire** (`TPO_ID`, 79 valeurs) : TOTEM 10 649, société privée 9 258, TDF 8 094, copropriétés 7 169,
  communes 6 205, HIVORY 5 607, HLM 5 358, SNCF Réseau 3 976, On Tower 3 966, ATC 3 902, Cellnex 2 867…
- **Hauteur** `SUP_NM_HAUT` (m, virgule décimale) : médiane 26,5 m, 99ᵉ centile 65 m, 55 supports > 200 m.
  Les plus hauts : deux supports de 350 m (INSEE 18005), 343 m (72191), la Tour Eiffel à 331 m (75107), 330 m (79164), 308 m (62170) — pylônes de radiodiffusion pour la plupart.
  À nettoyer : **773 valeurs ≤ 0** (jusqu'à −14 m, sans doute des installations souterraines ou des erreurs
  de saisie) et 34 valeurs non numériques. Je propose de les garder, mais signalées « hauteur inconnue/non significative ».

## 7. Exploitants

- `SUP_EXPLOITANT` compte 188 libellés, dont **86 utilisés**. L'exploitant est porté par la **station**, pas par le support.
- Stations par exploitant : Bouygues Telecom 35 188, Orange 34 766, Free Mobile 33 772, SFR 33 048, TDF 12 675,
  « RESEAU PRIVE » 12 344 (PMR anonymisée), Orange service fixe 7 724 (FH), Towercast 6 306,
  « Site privé » 4 669, SNCF Réseau 4 188, EDF 3 146…
- Opérateurs ultramarins : Outremer Telecom, Digicel, SRR, Free Caraïbes, ONATI, Telco OI, Zeop, Dauphin, PMT/Vodafone, Viti…
- Il faudra regrouper les libellés (« Orange » et « Orange service fixe », par exemple), mais garder le libellé ANFR dans la fiche.
- **Supports mobiles (GSM/UMTS/LTE/NR) : 76 615**. Nombre d'opérateurs mobiles par support :
  1 → 40 158 ; 2 → 16 934 ; 3 → 8 355 ; **4 → 11 117** ; 5 → 51.

## 8. Systèmes (`EMR_LB_SYSTEME`)

66 valeurs distinctes, plus 16 vides et 3 `0`. Elles se regroupent en familles :

| Famille | Libellés ANFR (émetteurs) |
|---|---|
| 2G | `GSM 900` 155 398, `GSM 1800` 1 561 |
| 3G | `UMTS 900` 285 247, `UMTS 2100` 24 138 |
| 4G | `LTE 700` 309 031, `LTE 800` 304 103, `LTE 900` 79 974, `LTE 1800` 310 217, `LTE 2100` 256 286, `LTE 2600` 228 986, `LTE 700 P` 650, `LTE 2600 P` 1 001 (réseaux privés) |
| 5G | `5G NR 700` 122 789, `5G NR 2100` 122 455, `5G NR 3500` 163 643 ; expérimentations : `5G NR 1400 Expe`, `5G NR 3800-4200 Expe`, `5G NR 26 GHz Expe`, `5G Broadcast Expe` |
| Ferroviaire | `GSM R` 7 832 (SNCF Réseau) |
| BLR / THD radio | `BLR LTE 3500` 320, `BLR 3 GHZ`, `BLR 26 GHZ` |
| Faisceaux hertziens | `FH` 92 348, `FH ABI` 257 |
| Radiodiffusion | `FM` 10 871, `RDF DVB-T` (TNT) 10 354, `RDF T-DAB` (DAB+) 1 106, `RDF AM`, `RDF TV-AN` |
| PMR | `PMR` 14 588, `TETRA` 901, `TETRAPOL` 1, `RMU-POCSAG` 378 (radiomessagerie), `COM TER` 3 349 (EDF, routes) |
| Maritime / aéro | `COM MAR` 873, `AIS` 213, `COM AERTER`, `COM AER`, `ADS-B`, `DME`, `VOR-C`, `GONIO` |
| Radars / science | `RDR`, `RDR MTO`, `RDR PFL`, `RDR COT`, `RADIOASTRO`, `RS` |
| Satellite | `SAT`, `SAT GEO`, `SAT NGEO`, `GPS`, `GPS D` |
| Divers | `TELEM`, `TELECD`, `TELECD/TELEM`, `TELEM/TELECD`, `EM`, `REC`, `EM/REC`, `ANM`, `ANA`, `TROPO`, `AIS/GPS` |

Pour les systèmes mobiles, le libellé contient la bande (`LTE 800`) : technologie et bande nominale se lisent directement.
Pour FH, PMR ou SAT, il faut les fréquences de `SUP_BANDE`.

## 9. Fréquences (`SUP_BANDE`)

- `BAN_NB_F_DEB` / `BAN_NB_F_FIN` (virgule décimale) et unité `BAN_FG_UNITE` : `M` (MHz, 4 743 369),
  `G` (GHz, 96 987, surtout FH et satellite), `K` (kHz, 559 : AM, maritime, PMR), vide (5 905).
- Une fois converties en MHz, les plages sont cohérentes pour l'immense majorité des lignes. Exemples :
  - LTE 800 : blocs de 10 MHz, 791–801 / 801–811 / 811–821 en descendant, 832–862 en montant ;
  - 5G NR 3500 en métropole : SFR 3490–3570, Bouygues 3570–3640, Free 3640–3710, Orange 3710–3800 ;
  - FM 87,5–108 ; TNT 470–790 ; DAB 174–223.
- **Anomalies d'unité** à corriger : quelques valeurs ×1000 ou ÷1000, par exemple LTE 800 jusqu'à 862 000 (kHz saisis en MHz),
  LTE 2100 jusqu'à 2 130 000, LTE 1800 à 18, 5G NR 700 à 0,71, FH jusqu'à 6 425 000.
  Correctif proposé : pour chaque système dont la bande est connue (mobiles, GSM-R, FM, TNT, DAB…),
  si la plage tombe hors de la fenêtre attendue, essayer ×1000 puis ÷1000, sinon marquer la ligne `freq_suspecte`.
  Pour FH et SAT, garder la fenêtre 1 MHz–100 GHz.
- 1 065 bandes de largeur nulle (fréquence unique), 0 bande inversée.

## 10. Dates

- `EMR_DT_SERVICE` (mise en service de l'émetteur) : renseignée pour 91 % des émetteurs.
  Il manque surtout des dates sur la 4G/5G récente (déclarée mais pas encore en service ?).
- Il y a des valeurs aberrantes : années `0025` et `25`, 286 émetteurs en 1951, et **371 dates dans le futur** (jusqu'en 2029).
  Je propose de borner à [1980, date d'extraction] et de traiter le reste comme « date inconnue ».
- La progression de la 5G NR 3500 est nette : 3 468 émetteurs en 2020, 26 216 en 2021, 29 885 en 2022, puis environ 25 000 par an.
- `SUP_STATION` porte aussi `DTE_IMPLANTATION`, `DTE_MODIF` et `DTE_EN_SERVICE` (date de la station).
- Limite : `EMR_DT_SERVICE` ne décrit que le parc *actuel*. Un émetteur démonté n'apparaît plus, par exemple le GSM 1800 quasi éteint
  (1 561 émetteurs restants) ou la 3G en cours d'extinction. Pour représenter aussi les extinctions, la frise doit
  s'appuyer sur les **archives mensuelles**.

## 11. Antennes

- `TAE_ID` (type), `AER_NB_DIMENSION` (m), `AER_FG_RAYON` (D directionnelle / N non directionnelle),
  `AER_NB_AZIMUT` (°, souvent 0/120/240 : trisectoriel), `AER_NB_ALT_BAS` (hauteur du bas de l'antenne, m).
- Avec l'azimut, on peut dessiner les secteurs des antennes sur la fiche du support (pétales orientés).

## 12. Ce que le jeu ne contient pas

- Les installations de l'Aviation civile, de la Défense et de l'Intérieur (exclues par l'ANFR). Pas non plus de puissance, de PIRE, de tilt ni de diagramme d'antenne.
- Les noms des exploitants PMR, anonymisés en « RESEAU PRIVE » ou « Site privé ».
- Les petites installations de moins de 5 W (small cells, Wi-Fi…).

## 13. Conséquences pour l'architecture

- **98 980 supports seulement** : l'ensemble des points tient dans le navigateur. Un index compact par support
  (coordonnées, exploitants, familles de systèmes, bandes, dates) se filtre côté client en quelques ms.
- **2,5 M émetteurs / 4,8 M bandes** : trop lourd à charger en une fois. Le détail (fiche, spectre exact)
  sera découpé par département et chargé à la demande.
