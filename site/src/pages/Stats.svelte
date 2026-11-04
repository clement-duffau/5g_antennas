<script lang="ts">
  import { loadJSON } from '../lib/data'
  import type { CommuneRow, DepRow, Stats, SupportRow, SystemeRow } from '../lib/types'
  import { fmt, fmt1, fmt2, fmtDate, fmtPct } from '../lib/format'
  import { GENERATIONS, MOBILE_OPS, opColor, seqColor } from '../lib/colors'
  import Section from '../lib/ui/Section.svelte'
  import Panel from '../lib/ui/Panel.svelte'
  import Chips from '../lib/ui/Chips.svelte'
  import DataTable, { type Column } from '../lib/ui/DataTable.svelte'
  import BarList from '../lib/charts/BarList.svelte'
  import StackedColumns from '../lib/charts/StackedColumns.svelte'
  import SpectrumStrip from '../lib/charts/SpectrumStrip.svelte'
  import AzimuthRose from '../lib/charts/AzimuthRose.svelte'

  const statsPromise = loadJSON<Stats>('stats.json')

  const SECTIONS = [
    ['spectre', 'Spectre mobile'], ['operateurs', 'Opérateurs'], ['technologies', 'Technologies'],
    ['deploiement', 'Déploiement'], ['territoires', 'Territoires'], ['records', 'Records'],
    ['supports', 'Supports'], ['antennes', 'Antennes'],
  ] as const

  let genDeploiement = $state('5G')
  let communeVue = $state('top')

  const opShort = (op: string) => (op === 'Bouygues Telecom' ? 'Bouygues' : op)

  // ------------------------------------------------------------------ dérivés
  function sitesParGeneration(s: Stats) {
    return GENERATIONS.map((g) => ({
      g,
      items: MOBILE_OPS.map((op) => ({
        label: opShort(op),
        value: s.sites_operateur_generation.find((r) => r.groupe === op && r.generation === g)?.sites ?? 0,
        color: opColor(op),
      })),
    }))
  }

  function matrice(s: Stats) {
    const systemes = s.systemes.filter((r) => r.famille === 'Mobile' && r.generation)
    const max = Math.max(...s.sites_operateur_systeme.map((r) => r.sites))
    return {
      max,
      rows: systemes.map((sys) => ({
        sys,
        cells: MOBILE_OPS.map((op) => s.sites_operateur_systeme.find((r) => r.groupe === op && r.systeme === sys.systeme)?.sites ?? 0),
      })).sort((a, b) => (a.sys.generation! + a.sys.bande).localeCompare(b.sys.generation! + b.sys.bande, 'fr', { numeric: true })),
    }
  }

  function deploiement(s: Stats, gen: string) {
    const last = Number(s.meta.extraction.slice(0, 4))
    const first = gen === '5G' ? 2019 : gen === '4G' ? 2011 : 1992
    const years = Array.from({ length: last - first + 1 }, (_, i) => first + i)
    const values = years.map((y) => {
      const row: Record<string, number> = {}
      for (const op of MOBILE_OPS) {
        row[op] = s.deploiement
          .filter((d) => d.annee === y && d.groupe === op && (gen === 'tout' || d.generation === gen))
          .reduce((t, d) => t + d.emetteurs, 0)
      }
      return row
    })
    return { years, values }
  }

  const supportLabel = (r: SupportRow) => `${r.commune} (${r.dep})`
  const opsDots = (groupes: string[]) => groupes.filter((g) => (MOBILE_OPS as readonly string[]).includes(g))

  // ------------------------------------------------------------------ colonnes de tableaux
  const depCols: Column<DepRow>[] = [
    { key: 'dep', label: 'N°' },
    { key: 'nom', label: 'Département' },
    { key: 'supports', label: 'Supports', numeric: true, bar: true },
    { key: 'supports_par_100km2', label: 'pour 100 km²', numeric: true, format: fmt1 },
    { key: 'supports_par_10k_hab', label: 'pour 10 000 hab.', numeric: true, format: fmt1 },
    { key: 'sites_mobiles', label: 'Sites mobiles', numeric: true },
    { key: 'part_5g', label: 'dont 5G', numeric: true, format: fmtPct, title: 'Part des sites mobiles équipés en 5G' },
    { key: 'sites_4_operateurs', label: '4 opérateurs', numeric: true, title: 'Sites partagés par les 4 opérateurs mobiles' },
    { key: 'hauteur_moyenne', label: 'Hauteur moy. (m)', numeric: true, format: fmt1 },
    { key: 'population', label: 'Population', numeric: true },
  ]
  const communeCols: Column<CommuneRow>[] = [
    { key: 'nom', label: 'Commune' },
    { key: 'dep', label: 'Dép.' },
    { key: 'supports', label: 'Supports', numeric: true, bar: true },
    { key: 'supports_par_km2', label: 'par km²', numeric: true, format: fmt2 },
    { key: 'supports_par_10k_hab', label: 'pour 10 000 hab.', numeric: true, format: fmt1 },
    { key: 'sites_5g', label: 'Sites 5G', numeric: true },
    { key: 'population', label: 'Population', numeric: true },
  ]
  const sysCols: Column<SystemeRow>[] = [
    { key: 'systeme', label: 'Système ANFR' },
    { key: 'famille', label: 'Famille' },
    { key: 'description', label: 'Description' },
    { key: 'emetteurs', label: 'Émetteurs', numeric: true, bar: true },
    { key: 'supports', label: 'Supports', numeric: true },
    { key: 'debut_deploiement', label: 'Début du déploiement', numeric: true, format: (v) => (v ? String(v) : '–'), title: 'Année où 1 % du parc actuel était en service (écarte les dates aberrantes)' },
  ]
  type OpRow = Stats['operateurs'][number]
  const opCols: Column<OpRow>[] = [
    { key: 'groupe', label: 'Exploitant' },
    { key: 'categorie', label: 'Catégorie' },
    { key: 'stations', label: 'Stations', numeric: true, bar: true },
    { key: 'supports', label: 'Supports', numeric: true },
    { key: 'emetteurs', label: 'Émetteurs', numeric: true },
    { key: 'libelles_anfr', label: 'Libellés ANFR', format: (v: string[]) => v.join(', ') },
  ]
</script>

{#await statsPromise}
  <p class="loading">Chargement des statistiques…</p>
{:then s}
  {@const t = s.totaux}
  <div class="intro">
    <h1><span class="num">{fmt(t.supports)}</span> supports d'antennes en France métropolitaine</h1>
    <p class="lede">
      {fmt(t.stations)} stations, {fmt(t.antennes)} antennes et {fmt(t.emetteurs)} émetteurs de plus de 5 watts,
      répartis sur {fmt(t.communes)} communes. {fmt(t.supports_5g)} supports portent de la 5G.
      Données ANFR au {fmtDate(s.meta.extraction)}.
    </p>
    <nav class="toc" aria-label="Sections de la page">
      {#each SECTIONS as [id, label]}<a href="#/statistiques#{id}">{label}</a>{/each}
    </nav>
  </div>

  <Section id="spectre" title="Qui émet sur quelles fréquences"
    intro="Blocs de fréquences effectivement déclarés par chaque opérateur mobile, toutes technologies confondues. Chaque bande est à l'échelle de sa largeur en MHz ; UL = voie montante, DL = voie descendante, TDD = duplex temporel.">
    <SpectrumStrip blocks={s.spectre_national} />
  </Section>

  <Section id="operateurs" title="Opérateurs"
    intro="Un site est un support (pylône, toit, château d'eau…) sur lequel l'opérateur exploite au moins un émetteur de la génération concernée.">
    <div class="grid4">
      {#each sitesParGeneration(s) as { g, items } (g)}
        <Panel title="Sites {g}">
          <BarList {items} label="Sites {g} par opérateur" />
        </Panel>
      {/each}
    </div>

    <div class="grid2 gap-top">
      <Panel title="Sites par opérateur et par bande" note="Nombre de supports équipés ; la teinte suit la valeur.">
        {@const mx = matrice(s)}
        <div class="scroller">
          <table class="heat">
            <thead>
              <tr><th>Système</th>{#each MOBILE_OPS as op}<th class="numeric"><span class="dot" style:background={opColor(op)}></span>{opShort(op)}</th>{/each}</tr>
            </thead>
            <tbody>
              {#each mx.rows as { sys, cells } (sys.systeme)}
                <tr>
                  <th scope="row">{sys.systeme}</th>
                  {#each cells as v}
                    <td class="num numeric" style:background={v ? seqColor(0.15 + (0.85 * v) / mx.max) : 'transparent'}
                      class:light={v / mx.max > 0.55}>{v ? fmt(v) : '·'}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Partage des supports" note="Nombre d'opérateurs mobiles présents sur un même support.">
        {@const tot = s.partage_mobile.reduce((a, b) => a + b.supports, 0)}
        <div class="segbar" role="img" aria-label="Répartition des supports mobiles selon le nombre d'opérateurs présents">
          {#each s.partage_mobile as p (p.operateurs)}
            <div class="seg" style:flex-grow={p.supports} style:background={seqColor(p.operateurs / 4)}
              class:light={p.operateurs >= 3} title="{p.operateurs} opérateur(s) : {fmt(p.supports)} supports">
              {#if p.supports / tot > 0.08}<span>{fmtPct(p.supports / tot)}</span>{/if}
            </div>
          {/each}
        </div>
        <ul class="seglegend">
          {#each s.partage_mobile as p (p.operateurs)}
            <li><span class="sw" style:background={seqColor(p.operateurs / 4)}></span>
              {p.operateurs} opérateur{p.operateurs > 1 ? 's' : ''} : <strong class="num">{fmt(p.supports)}</strong></li>
          {/each}
        </ul>
        <p class="aside">
          {fmt(s.partage_mobile.find((p) => p.operateurs === 4)?.supports)} supports accueillent les quatre opérateurs :
          pylônes de « towercos » (TOTEM, Cellnex, On Tower, ATC…) et points hauts mutualisés.
        </p>
      </Panel>
    </div>

    <div class="gap-top">
      <Panel title="Tous les exploitants" note="Les libellés ANFR sont regroupés par groupe (par exemple « ORANGE » et « ORANGE service fixe »).">
        <DataTable rows={s.operateurs} columns={opCols} sortKey="stations" search={['groupe', 'categorie']}
          caption="exploitants" rowKey={(r) => r.groupe} limit={12} />
      </Panel>
    </div>
  </Section>

  <Section id="technologies" title="Technologies et systèmes"
    intro="L'ANFR déclare chaque émetteur avec un système (EMR_LB_SYSTEME). Un émetteur correspond en général à une cellule sur une bande : un site 4G trisectoriel compte trois émetteurs par bande.">
    <div class="grid2">
      <Panel title="Émetteurs par famille">
        <BarList label="Émetteurs par famille de systèmes"
          items={s.familles.map((f) => ({ label: f.famille, value: f.emetteurs, note: `${fmt(f.supports)} supports` }))} />
      </Panel>
      <Panel title="Hors réseaux mobiles" note="Les familles minoritaires, à leur propre échelle.">
        <BarList label="Émetteurs par famille hors mobile"
          items={s.familles.filter((f) => f.famille !== 'Mobile').map((f) => ({ label: f.famille, value: f.emetteurs, note: `${fmt(f.supports)} supports` }))} />
      </Panel>
    </div>
    <div class="gap-top">
      <Panel title="Les {s.systemes.length} systèmes déclarés">
        <DataTable rows={s.systemes} columns={sysCols} sortKey="emetteurs" search={['systeme', 'famille', 'description']}
          caption="systèmes" rowKey={(r) => r.systeme} limit={15} />
      </Panel>
    </div>
  </Section>

  <Section id="deploiement" title="Déploiement dans le temps"
    intro="Émetteurs des réseaux mobiles par année de mise en service (EMR_DT_SERVICE). Seul le parc actuel est compté : un émetteur démonté depuis n'apparaît pas, ce qui sous-estime les anciennes années de la 2G et de la 3G.">
    <div class="controls">
      <Chips label="Génération" bind:value={genDeploiement}
        options={[...[...GENERATIONS].reverse().map((g) => ({ value: g as string, label: g as string })), { value: 'tout', label: 'Toutes' }]} />
    </div>
    {@const d = deploiement(s, genDeploiement)}
    <StackedColumns categories={d.years} values={d.values}
      series={MOBILE_OPS.map((op) => ({ key: op, label: op, color: opColor(op) }))}
      label="Émetteurs {genDeploiement} mis en service par année et par opérateur" height={300} />
  </Section>

  <Section id="territoires" title="Territoires"
    intro="Densités calculées avec la population et la superficie des communes (geo.api.gouv.fr). Les arrondissements de Paris, Lyon et Marseille sont rattachés à leur commune.">
    <div class="grid2">
      <Panel title="Supports pour 100 km²">
        <BarList label="Départements les plus denses en supports"
          items={[...s.departements].sort((a, b) => b.supports_par_100km2 - a.supports_par_100km2).slice(0, 10)
            .map((d) => ({ label: `${d.nom} (${d.dep})`, value: d.supports_par_100km2 }))} format={fmt1} />
      </Panel>
      <Panel title="Supports pour 10 000 habitants">
        <BarList label="Départements avec le plus de supports par habitant"
          items={[...s.departements].sort((a, b) => b.supports_par_10k_hab - a.supports_par_10k_hab).slice(0, 10)
            .map((d) => ({ label: `${d.nom} (${d.dep})`, value: d.supports_par_10k_hab }))} format={fmt1} />
      </Panel>
    </div>
    <div class="gap-top">
      <Panel title="Les 96 départements">
        <DataTable rows={s.departements} columns={depCols} sortKey="supports" search={['nom', 'dep', 'region']}
          caption="départements" rowKey={(r) => r.dep} limit={12} />
      </Panel>
    </div>
    <div class="gap-top">
      <Panel title="Communes">
        <div class="controls">
          <Chips label="Classement des communes" bind:value={communeVue} options={[
            { value: 'top', label: 'Plus de supports' },
            { value: 'km2', label: 'Densité au km²' },
            { value: 'hab', label: 'Par habitant' },
          ]} />
        </div>
        {#key communeVue}
          <DataTable
            rows={communeVue === 'top' ? s.communes_top : communeVue === 'km2' ? s.communes_densite_km2 : s.communes_par_habitant}
            columns={communeCols}
            sortKey={communeVue === 'top' ? 'supports' : communeVue === 'km2' ? 'supports_par_km2' : 'supports_par_10k_hab'}
            search={['nom', 'dep']} caption="communes" rowKey={(r) => r.insee} limit={12} />
        {/key}
        {#if communeVue !== 'top'}<p class="aside">Classements limités aux communes de plus de 10 000 habitants.</p>{/if}
      </Panel>
    </div>
  </Section>

  <Section id="records" title="Records">
    <div class="grid3">
      {#each [
        { title: 'Les plus hauts', rows: s.plus_hauts, val: (r: SupportRow) => `${fmt1(r.hauteur)} m` },
        { title: "Le plus d'exploitants", rows: s.plus_exploitants, val: (r: SupportRow) => `${r.n_groupes} exploitants` },
        { title: "Le plus d'émetteurs", rows: s.plus_emetteurs, val: (r: SupportRow) => `${fmt(r.n_emetteurs)} émetteurs` },
      ] as rec (rec.title)}
        <Panel title={rec.title}>
          <ol class="records">
            {#each rec.rows.slice(0, 10) as r (r.sup_id)}
              <li>
                <div class="rec-main">
                  <strong class="num">{rec.val(r)}</strong>
                  <span>{supportLabel(r)}</span>
                </div>
                <div class="rec-sub">
                  {r.nature ?? 'Nature inconnue'}{r.adresse ? ` · ${r.adresse}` : ''}
                </div>
                <div class="rec-ops" title={r.groupes.join(', ')}>
                  {#each opsDots(r.groupes) as g}<span class="dot" style:background={opColor(g)} title={g}></span>{/each}
                  <span class="rec-groupes">{r.groupes.join(', ')}</span>
                </div>
              </li>
            {/each}
          </ol>
        </Panel>
      {/each}
    </div>
  </Section>

  <Section id="supports" title="Supports"
    intro="La nature, la hauteur et le propriétaire du support sont déclarés par l'exploitant. {fmt(s.qualite.supports_hauteur_invalide)} hauteurs nulles ou négatives sont écartées.">
    <div class="grid2">
      <Panel title="Nature du support">
        <BarList label="Supports par nature" items={s.natures.slice(0, 14).map((n) => ({ label: n.nature, value: n.supports, note: n.hauteur_moyenne ? `${fmt1(n.hauteur_moyenne)} m en moy.` : undefined }))} />
      </Panel>
      <Panel title="Propriétaire du support">
        <BarList label="Supports par propriétaire" items={s.proprietaires.slice(0, 14).map((p) => ({ label: p.proprietaire, value: p.supports }))} />
      </Panel>
      <Panel title="Hauteur des supports" note="Par tranches de 5 m ; la dernière colonne regroupe les supports de 100 m et plus." wide>
        <StackedColumns categories={s.hauteurs.map((h) => h.de)} values={s.hauteurs.map((h) => ({ n: h.supports }))}
          series={[{ key: 'n', label: 'supports', color: 'var(--seq-3)' }]}
          xLabel={(c) => (+c >= 100 ? '100+' : `${c}`)} label="Histogramme des hauteurs de supports" height={220} />
      </Panel>
    </div>
  </Section>

  <Section id="antennes" title="Antennes"
    intro="Chaque antenne est décrite par son type, sa dimension, son azimut et sa hauteur. Les antennes sectorielles des réseaux mobiles visent souvent 0°, 120° et 240°.">
    <div class="grid2">
      <Panel title="Types d'antennes">
        <BarList label="Antennes par type" items={s.antennes.types.map((a) => ({ label: a.type, value: a.antennes }))} />
      </Panel>
      <Panel title="Azimut des antennes directionnelles" note="Secteurs de 10° ; l'aire de chaque secteur est proportionnelle au nombre d'antennes.">
        <AzimuthRose bins={s.antennes.azimuts} />
      </Panel>
    </div>
  </Section>
{:catch e}
  <p class="loading">Les statistiques n'ont pas pu être chargées ({e.message}). Lancez le pipeline : <code>python -m pipeline build</code>.</p>
{/await}

<style>
  .intro { padding-block: clamp(32px, 6vw, 72px) clamp(24px, 4vw, 40px); display: grid; gap: 18px; }
  h1 { max-width: 18ch; }
  h1 .num { color: var(--accent); }
  .lede { font-size: 1.1rem; color: var(--text-2); max-width: 62ch; }
  .toc { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 0.92rem; }
  .toc a { color: var(--text-2); text-decoration: none; border-bottom: 1px solid var(--line-strong); padding-bottom: 1px; }
  .toc a:hover { color: var(--text); border-color: var(--accent); }
  .loading { padding: 80px 0; color: var(--text-2); }

  .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 40px 48px; }
  .grid3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 32px 40px; }
  .grid4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr)); gap: 28px clamp(20px, 3vw, 36px); }
  .gap-top { margin-top: 48px; }
  .controls { margin-bottom: 16px; }
  .aside { color: var(--muted); font-size: 0.85rem; margin-top: 12px; }
  .scroller { overflow-x: auto; }

  .heat { border-collapse: separate; border-spacing: 2px; font-size: 0.85rem; width: 100%; }
  .heat th { font-weight: 500; color: var(--text-2); text-align: left; padding: 4px 8px; white-space: nowrap; }
  .heat thead th { font-weight: 560; }
  .heat td { padding: 4px 8px; border-radius: 3px; color: var(--text); }
  .heat td.light { color: var(--accent-ink); }
  .numeric { text-align: right; }
  .dot { display: inline-block; flex: none; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: 0.05em; }

  .segbar { display: flex; height: 28px; gap: 2px; }
  .seg { min-width: 2px; border-radius: 4px; display: flex; align-items: center; padding-left: 8px; font-size: 0.8rem; font-weight: 600; color: var(--text); }
  .seg.light { color: var(--accent-ink); }
  .seglegend { list-style: none; padding: 0; margin: 12px 0 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 16px; font-size: 0.86rem; color: var(--text-2); }
  .seglegend li { display: flex; align-items: center; gap: 6px; }
  .seglegend strong { color: var(--text); font-weight: 600; }
  .sw { width: 10px; height: 10px; border-radius: 2px; flex: none; }

  .records { list-style: none; counter-reset: rec; margin: 0; padding: 0; display: grid; gap: 12px; }
  .records li { counter-increment: rec; display: grid; gap: 2px; padding-left: 28px; position: relative; }
  .records li::before {
    content: counter(rec); position: absolute; left: 0; top: 1px; width: 20px; text-align: right;
    color: var(--muted); font-size: 0.8rem; font-variant-numeric: tabular-nums;
  }
  .rec-main { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
  .rec-main strong { font-weight: 640; }
  .rec-main span { color: var(--text-2); }
  .rec-sub { color: var(--muted); font-size: 0.82rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rec-ops { display: flex; align-items: center; font-size: 0.78rem; color: var(--muted); min-width: 0; }
  .rec-groupes { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
