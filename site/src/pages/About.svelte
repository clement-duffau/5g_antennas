<script lang="ts">
  import { loadJSON } from '../lib/data'
  import type { Stats } from '../lib/types'
  import { fmt, fmtDate } from '../lib/format'

  const statsPromise = loadJSON<Stats>('stats.json')
</script>

<article class="about">
  <h1>À propos et méthodologie</h1>

  {#await statsPromise then s}
    {@const q = s.qualite}
    <p class="lede">
      Extraction ANFR du <strong>{fmtDate(s.meta.extraction)}</strong>{#if s.meta.source.publication}, publiée le {fmtDate(s.meta.source.publication)}{/if}.
      Site régénéré le {fmtDate(s.meta.generation)}. Périmètre : {s.meta.perimetre}.
    </p>

    <h2>Source</h2>
    <p>
      Jeu de données <a href="https://www.data.gouv.fr/fr/datasets/donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1/">
      « Données sur les installations radioélectriques de plus de 5 watts »</a> de l'Agence nationale des fréquences (ANFR),
      publié chaque mois sur data.gouv.fr sous <a href="https://www.etalab.gouv.fr/licence-ouverte-open-licence/">Licence Ouverte 2.0</a>.
      Les populations et superficies communales viennent de <a href="https://geo.api.gouv.fr/">geo.api.gouv.fr</a>.
      La recherche d'adresse utilise le géocodeur de l'<a href="https://geoservices.ign.fr/">IGN (Géoplateforme)</a>,
      interrogé directement depuis votre navigateur ; aucune adresse n'est enregistrée par ce site.
      Le fond de carte est fourni par <a href="https://openfreemap.org/">OpenFreeMap</a>
      (© OpenMapTiles, données © <a href="https://www.openstreetmap.org/copyright">contributeurs OpenStreetMap</a>).
    </p>

    <h2>Ce que les données ne contiennent pas</h2>
    <ul>
      <li>Les installations de l'<strong>Aviation civile</strong>, de la <strong>Défense</strong> et du <strong>ministère de l'Intérieur</strong>, exclues par l'ANFR.</li>
      <li>Les installations de 5 W ou moins (petites cellules, Wi-Fi, équipements domestiques).</li>
      <li>La puissance, la PIRE, le tilt et les diagrammes d'antenne.</li>
      <li>Le nom des exploitants de réseaux privés (PMR), anonymisés en « Réseau privé » ou « Site privé ».</li>
      <li>L'outre-mer, présent dans le jeu ANFR mais volontairement laissé hors du périmètre de ce site.</li>
    </ul>

    <h2>Vocabulaire</h2>
    <dl>
      <dt>Support</dt><dd>L'ouvrage physique : pylône, toit d'immeuble, château d'eau, clocher…</dd>
      <dt>Station</dt><dd>L'installation d'un exploitant sur un support. Un support porte en moyenne deux stations.</dd>
      <dt>Antenne</dt><dd>Un aérien de la station, avec son type, son azimut et sa hauteur.</dd>
      <dt>Émetteur</dt><dd>Un émetteur relié à une antenne pour un système donné (par exemple « LTE 800 »), avec sa date de mise en service.</dd>
      <dt>Bande</dt><dd>Une plage de fréquences d'un émetteur. Les systèmes FDD en déclarent deux : voie montante et voie descendante.</dd>
      <dt>Site</dt><dd>Dans les statistiques, un support sur lequel un opérateur exploite au moins un émetteur de la technologie concernée.</dd>
    </dl>

    <h2>Traitements appliqués</h2>
    <ul>
      <li>Coordonnées converties de degrés-minutes-secondes en degrés décimaux (WGS84) ; précision d'une seconde d'arc, soit environ 30 m.
        Sur la carte, un point peut donc être décalé de quelques dizaines de mètres par rapport au pylône réel.</li>
      <li>La table SUP_SUPPORT associe supports et stations ; elle est dédoublonnée par identifiant de support.</li>
      <li>Fréquences converties en MHz. Les erreurs d'unité manifestes (facteur 1000) sont corrigées en comparant à la bande attendue du système :
        {fmt(q['bandes_unité_corrigée'] ?? 0)} bandes corrigées, {fmt(q.bandes_suspecte ?? 0)} incohérentes conservées mais signalées, {fmt(q.bandes_vide ?? 0)} sans fréquence.</li>
      <li>Dates de mise en service retenues entre 1980 et la date d'extraction :
        {fmt(q.emetteurs_date_absente ?? 0)} absentes, {fmt(q.emetteurs_date_future ?? 0)} dans le futur et {fmt(q.emetteurs_date_trop_ancienne ?? 0)} trop anciennes sont ignorées.</li>
      <li>Hauteurs nulles ou négatives écartées : {fmt(q.supports_hauteur_invalide ?? 0)} supports.</li>
      <li>Rattachement communal : {fmt(q.rattachement_direct ?? 0)} supports directement, {fmt(q.rattachement_arrondissement ?? 0)} via un arrondissement municipal,
        {fmt(q.rattachement_commune_la_plus_proche ?? 0)} au centre de commune le plus proche (anciennes communes fusionnées).</li>
      <li>Frise : la carte et les courbes cumulées utilisent la date de première mise en service, sur chaque support, d'un
        système de l'opérateur (parc actuel ; un site démonté n'y figure pas). Les courbes « archive par archive » comptent
        le parc déclaré dans chaque extraction mensuelle de l'ANFR depuis septembre 2018, démontages compris.</li>
      <li>Exploitants regroupés par groupe (par exemple ORANGE et ORANGE service fixe) ; le libellé ANFR d'origine reste visible.</li>
    </ul>

    <h2>Code et données</h2>
    <p>
      Le code du pipeline (Python, DuckDB) et du site (Svelte) est public sur
      <a href="https://github.com/clement-duffau/5g_antennas">GitHub</a>. Les fichiers sont régénérés chaque mois par une GitHub Action
      après la publication de l'ANFR.
    </p>
  {/await}
</article>

<style>
  .about { max-width: 72ch; padding-block: clamp(32px, 6vw, 64px); display: grid; gap: 14px; }
  h1 { margin-bottom: 8px; }
  h2 { margin-top: 28px; font-size: 1.3rem; }
  .lede { font-size: 1.08rem; color: var(--text-2); }
  ul { margin: 0; padding-left: 1.2em; display: grid; gap: 8px; color: var(--text-2); }
  li strong, p strong { color: var(--text); font-weight: 600; }
  p { color: var(--text-2); }
  dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 8px 20px; color: var(--text-2); }
  dt { color: var(--text); font-weight: 600; }
  dd { margin: 0; }
  @media (max-width: 560px) { dl { grid-template-columns: 1fr; } dd { margin-bottom: 8px; } }
</style>
