<script lang="ts" module>
  /** Nombre de supports par exploitant, système et famille (pour les listes). */
  export interface Facets { grp: number[]; sys: number[]; fam: Map<string, number> }
</script>

<script lang="ts">
  import CheckList from '../ui/CheckList.svelte'
  import RangeSlider from '../ui/RangeSlider.svelte'
  import { BAND_PRESETS, EMPTY, type Filters } from '../filters'
  import type { SupportIndex } from '../supports'
  import type { Services } from '../services'
  import { GENERATIONS, MOBILE_OPS, opColor } from '../colors'
  import { fmt } from '../format'

  let { filters = $bindable(), index, services, facets, deps, servicesError }: {
    filters: Filters
    index: SupportIndex
    services: Services | null
    facets: Facets | null
    deps: { dep: string; nom: string }[]
    servicesError: string | null
  } = $props()

  const thisYear = new Date().getFullYear()

  // ------------------------------------------------------------------ listes
  const isMobile = (g: string) => (MOBILE_OPS as readonly string[]).includes(g)
  const autresExploitants = $derived(
    services && facets
      ? services.grps.map((g, k) => ({ value: g.nom, label: g.nom, count: facets.grp[k], note: g.categorie }))
          .filter((g) => !isMobile(g.value) && g.count > 0).sort((a, b) => b.count - a.count)
      : [])
  const familles = $derived(
    facets ? [...facets.fam.entries()].sort((a, b) => b[1] - a[1]).map(([f, n]) => ({ value: f, label: f, count: n })) : [])
  const systemes = $derived(
    services && facets
      ? services.syss.map((x, k) => ({ value: x.nom, label: x.nom, count: facets.sys[k], note: x.famille === 'Mobile' ? '' : x.famille }))
          .filter((x) => x.count > 0).sort((a, b) => b.count - a.count)
      : [])
  const natures = $derived.by(() => {
    const c = new Array(index.dict.nat.length).fill(0)
    for (let i = 0; i < index.n; i++) if (index.nat[i] >= 0) c[index.nat[i]]++
    return index.dict.nat.map((x, k) => ({ value: x, label: x, count: c[k] })).sort((a, b) => b.count - a.count)
  })
  const depItems = $derived(deps.map((d) => ({ value: d.dep, label: `${d.dep} · ${d.nom}` })))

  // ------------------------------------------------------------------ commune
  let comQuery = $state('')
  let comOpen = $state(false)
  const norm = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').replace(/[-']/g, ' ').toLowerCase()
  const comIndex = $derived.by(() => {
    const n = new Array(index.dict.com.length).fill(0)
    for (let i = 0; i < index.n; i++) n[index.com[i]]++
    return index.dict.com.map(([insee, nom], k) => ({ insee, nom, n: n[k], key: norm(nom) }))
  })
  // Correspondance exacte, puis début du nom, puis contenu ; à égalité, les communes les plus équipées.
  const comSuggestions = $derived.by(() => {
    const q = norm(comQuery.trim())
    if (q.length < 2) return []
    const rank = (c: { key: string }) => (c.key === q ? 0 : c.key.startsWith(q) ? 1 : c.key.includes(q) ? 2 : 3)
    return comIndex
      .filter((c) => rank(c) < 3)
      .sort((a, b) => rank(a) - rank(b) || b.n - a.n)
      .slice(0, 8)
  })
  const comLabel = $derived.by(() => {
    if (!filters.com) return ''
    const c = index.dict.com.find(([insee]) => insee === filters.com)
    return c ? `${c[1]} (${c[0].slice(0, 2)})` : filters.com
  })
  function pickCommune(insee: string) {
    filters = { ...filters, com: insee, deps: [] }
    comQuery = ''
    comOpen = false
  }

  // ------------------------------------------------------------------ helpers
  function toggleIn(key: 'ops' | 'gens', v: string) {
    const cur = filters[key]
    filters = { ...filters, [key]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] }
  }
  const setOthers = (vals: string[]) => (filters = { ...filters, ops: [...filters.ops.filter(isMobile), ...vals] })
  const othersSelected = $derived(filters.ops.filter((o) => !isMobile(o)))

  const fmtMHz = (v: number) =>
    v >= 1000 ? `${(v / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} GHz`
      : v < 1 ? `${(v * 1000).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} kHz`
        : `${v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} MHz`
  const presetActive = (f: [number, number]) => filters.f !== null && filters.f[0] === f[0] && filters.f[1] === f[1]

  function clear(keys: (keyof Filters)[]) {
    const next = { ...filters }
    for (const k of keys) (next as Record<string, unknown>)[k] = EMPTY[k]
    filters = next
  }
</script>

<div class="filters">
  {#if servicesError}
    <p class="warn">Les filtres par exploitant, technologie, fréquence et date sont indisponibles ({servicesError}).</p>
  {/if}

  <section>
    <header><h3>Exploitant</h3>{#if filters.ops.length}<button class="clr" onclick={() => clear(['ops'])}>Effacer</button>{/if}</header>
    <div class="chips">
      {#each MOBILE_OPS as op}
        <button type="button" aria-pressed={filters.ops.includes(op)} onclick={() => toggleIn('ops', op)}>
          <span class="dot" style:background={opColor(op)}></span>{op === 'Bouygues Telecom' ? 'Bouygues' : op}
        </button>
      {/each}
    </div>
    {#if services && facets}
      <details>
        <summary>Autres exploitants{othersSelected.length ? ` (${othersSelected.length})` : ''}</summary>
        <CheckList items={autresExploitants} label="autres exploitants"
          bind:selected={() => othersSelected, setOthers} />
      </details>
    {:else if !servicesError}
      <p class="muted">Chargement des exploitants…</p>
    {/if}
  </section>

  <section>
    <header><h3>Technologie</h3>{#if filters.gens.length || filters.fams.length || filters.sys.length}<button class="clr" onclick={() => clear(['gens', 'fams', 'sys'])}>Effacer</button>{/if}</header>
    <div class="chips">
      {#each GENERATIONS as g}
        <button type="button" aria-pressed={filters.gens.includes(g)} onclick={() => toggleIn('gens', g)}>{g}</button>
      {/each}
    </div>
    {#if services && facets}
      <details>
        <summary>Familles{filters.fams.length ? ` (${filters.fams.length})` : ''}</summary>
        <CheckList items={familles} bind:selected={filters.fams} label="familles de systèmes" />
      </details>
      <details>
        <summary>Systèmes ANFR{filters.sys.length ? ` (${filters.sys.length})` : ''}</summary>
        <CheckList items={systemes} bind:selected={filters.sys} label="systèmes" />
      </details>
    {/if}
  </section>

  <section>
    <header><h3>Fréquence</h3>{#if filters.f}<button class="clr" onclick={() => clear(['f'])}>Effacer</button>{/if}</header>
    <RangeSlider min={0.1} max={100000} log bind:value={filters.f} format={fmtMHz} label="Bande de fréquence" />
    <div class="chips small">
      {#each BAND_PRESETS as b (b.label)}
        <button type="button" aria-pressed={presetActive(b.f)} title="{fmtMHz(b.f[0])} – {fmtMHz(b.f[1])}"
          onclick={() => (filters = { ...filters, f: presetActive(b.f) ? null : b.f })}>{b.label}</button>
      {/each}
    </div>
    <p class="hint">Supports dont au moins une bande déclarée chevauche l'intervalle (700 à 3500 : bandes mobiles en MHz).</p>
  </section>

  <section>
    <header><h3>Mise en service</h3>{#if filters.y}<button class="clr" onclick={() => clear(['y'])}>Effacer</button>{/if}</header>
    <RangeSlider min={1990} max={thisYear} bind:value={filters.y} format={(v) => String(v)} label="Années de mise en service" />
    <p class="hint">Première mise en service, sur le support, d'un système de l'exploitant (répondant aux autres critères) pendant la période : par exemple, les nouveaux sites 5G de Free en 2025.</p>
  </section>

  <section>
    <header><h3>Territoire</h3>{#if filters.deps.length || filters.com}<button class="clr" onclick={() => clear(['deps', 'com'])}>Effacer</button>{/if}</header>
    {#if filters.com}
      <p class="picked">Commune : <strong>{comLabel}</strong></p>
    {:else}
      <div class="combo">
        <input type="search" placeholder="Commune…" bind:value={comQuery} aria-label="Filtrer par commune"
          onfocus={() => (comOpen = true)} onblur={() => setTimeout(() => (comOpen = false), 150)}
          onkeydown={(e) => { if (e.key === 'Enter' && comSuggestions[0]) pickCommune(comSuggestions[0].insee) }} />
        {#if comOpen && comSuggestions.length}
          <ul class="suggest" role="listbox">
            {#each comSuggestions as c (c.insee)}
              <li><button type="button" role="option" aria-selected="false" onmousedown={() => pickCommune(c.insee)}>
                {c.nom} <small>({c.insee.slice(0, 2)}) · {fmt(c.n)} supports</small></button></li>
            {/each}
          </ul>
        {/if}
      </div>
      <details>
        <summary>Départements{filters.deps.length ? ` (${filters.deps.length})` : ''}</summary>
        <CheckList items={depItems} bind:selected={filters.deps} label="départements" />
      </details>
    {/if}
  </section>

  <section>
    <header><h3>Support</h3>{#if filters.nat.length || filters.h}<button class="clr" onclick={() => clear(['nat', 'h'])}>Effacer</button>{/if}</header>
    <span class="sub">Hauteur</span>
    <RangeSlider min={0} max={350} bind:value={filters.h} format={(v) => `${fmt(v)} m`} label="Hauteur du support" />
    <details>
      <summary>Nature{filters.nat.length ? ` (${filters.nat.length})` : ''}</summary>
      <CheckList items={natures} bind:selected={filters.nat} label="natures de support" />
    </details>
  </section>
</div>

<style>
  .filters { display: grid; gap: 4px; }
  section { display: grid; gap: 8px; padding: 10px 0; border-top: 1px solid var(--line); }
  section:first-of-type { border-top: 0; padding-top: 0; }
  header { display: flex; align-items: center; justify-content: space-between; }
  h3 { font-size: 0.88rem; font-stretch: 105%; }
  .sub { font-size: 0.78rem; color: var(--muted); }
  .clr { background: none; border: 0; color: var(--accent); cursor: pointer; font-size: 0.78rem; padding: 0; }
  .chips { display: flex; flex-wrap: wrap; gap: 5px; }
  .chips button {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
    border: 1px solid var(--line-strong); background: transparent; color: var(--text-2); cursor: pointer; font-size: 0.82rem;
  }
  .chips.small button { padding: 2px 8px; font-size: 0.76rem; }
  .chips button:hover { color: var(--text); border-color: var(--text-2); }
  .chips button[aria-pressed='true'] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 600; }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  details summary { cursor: pointer; font-size: 0.82rem; color: var(--text-2); padding: 2px 0; }
  details[open] summary { margin-bottom: 6px; }
  .hint { font-size: 0.74rem; color: var(--muted); }
  .muted { font-size: 0.8rem; color: var(--muted); }
  .warn { font-size: 0.8rem; color: var(--text); background: var(--surface-2); padding: 8px; border-radius: var(--radius); }
  .combo { position: relative; }
  .combo input {
    width: 100%; font: inherit; font-size: 0.85rem; padding: 5px 8px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text);
  }
  .suggest {
    position: absolute; z-index: 5; left: 0; right: 0; top: calc(100% + 4px); list-style: none; margin: 0; padding: 4px;
    background: var(--surface-2); border: 1px solid var(--line-strong); border-radius: var(--radius); box-shadow: 0 8px 20px rgb(0 0 0 / 0.3);
  }
  .suggest button { width: 100%; text-align: left; background: none; border: 0; padding: 5px 6px; border-radius: 4px; color: var(--text); cursor: pointer; font-size: 0.85rem; }
  .suggest button:hover { background: var(--surface); }
  .suggest small { color: var(--muted); }
  .picked { font-size: 0.85rem; color: var(--text-2); }
  .picked strong { color: var(--text); }
</style>
