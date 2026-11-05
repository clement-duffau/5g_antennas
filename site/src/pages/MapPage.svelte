<script lang="ts">
  import { untrack } from 'svelte'
  import MapView, { type DisplayMode, type View } from '../lib/map/MapView.svelte'
  import SupportSheet from '../lib/map/SupportSheet.svelte'
  import FilterPanel, { type Facets } from '../lib/map/FilterPanel.svelte'
  import PlaceSearch, { type Place } from '../lib/map/PlaceSearch.svelte'
  import ZonePanel from '../lib/map/ZonePanel.svelte'
  import SpectrumDialog from '../lib/map/SpectrumDialog.svelte'
  import { occupation } from '../lib/spectrum'
  import AzimuthPanel from '../lib/map/AzimuthPanel.svelte'
  import { buildAzimuth, type AzimuthLayers } from '../lib/map/azimuthData'
  import { azimuts } from '../lib/azimuts.svelte'
  import { decode as decodeAz, encode as encodeAz, type AzState } from '../lib/azimuthSelection'
  import { loadSupports, type SupportIndex } from '../lib/supports'
  import { loadServices, type Services } from '../lib/services'
  import { loadJSON } from '../lib/data'
  import { categorize, COLOR_MODES } from '../lib/categories'
  import { apply, fromParams, isEmpty, needsServices, toParams, EMPTY, type Filters } from '../lib/filters'
  import { route, setParams } from '../lib/router.svelte'
  import { theme } from '../lib/theme.svelte'
  import { fmt } from '../lib/format'

  const p = route.params
  const center = (p.c ?? '').split(',').map(Number)
  let initialView = $state<View>(center.length === 2 && center.every(Number.isFinite)
    ? { lat: center[0], lon: center[1], zoom: Number(p.z) || 9 }
    : { lat: 46.6, lon: 2.45, zoom: 5.1 })

  let display = $state<DisplayMode>((['points', 'groupes', 'densite'].includes(p.m) ? p.m : 'points') as DisplayMode)
  let colorId = $state(COLOR_MODES.some((m) => m.id === p.col) ? p.col : 'techno')
  const colorMode = $derived(COLOR_MODES.find((m) => m.id === colorId)!)
  let hiddenByMode = $state<Record<string, number[]>>({})
  const hidden = $derived(hiddenByMode[colorId] ?? [])
  let selected = $state<number | null>(null)
  const wide = typeof window !== 'undefined' && window.innerWidth > 720
  let panelOpen = $state(wide)
  let tab = $state<'filtres' | 'affichage'>('filtres')
  let mapView = $state<MapView>()

  // ------------------------------------------------------------------ azimuts
  {
    const a = decodeAz(p)
    azimuts.list = a.list
    azimuts.len = a.len
    azimuts.ap = a.ap
  }
  const EMPTY_LAYERS: AzimuthLayers = { cones: { type: 'FeatureCollection', features: [] }, fh: { type: 'FeatureCollection', features: [] } }
  let azLayers = $state<AzimuthLayers>(EMPTY_LAYERS)
  let azRun = 0
  $effect(() => {
    const st = $state.snapshot(azimuts) as AzState
    const sv = services
    setParams(encodeAz(st))
    const run = ++azRun
    if (!st.list.length) { azLayers = EMPTY_LAYERS; return }
    data.then(({ index }) => buildAzimuth(index, sv, st, (l) => { if (run === azRun) azLayers = l }, () => run !== azRun))
      .catch((e) => console.warn('Azimuts :', e))
  })

  // ------------------------------------------------------------------ filtres
  let filters = $state<Filters>(fromParams(p))
  let services = $state<Services | null>(null)
  let facets = $state<Facets | null>(null)
  let servicesError = $state<string | null>(null)
  let deps = $state<{ dep: string; nom: string }[]>([])
  loadJSON<{ dep: string; nom: string }[]>('departements.json').then((d) => (deps = d)).catch(() => {})

  // Zone « autour de moi » : rayon par défaut selon le type de lieu.
  function pickPlace(pl: Place) {
    const r = filters.zone?.r ?? (pl.kind === 'commune' ? 2000 : 1000)
    filters = { ...filters, zone: { lat: pl.lat, lon: pl.lon, r, label: pl.label } }
    selected = null
    setParams({ s: null })
  }
  let spectrumOpen = $state(false)
  /** Libellé court de la sélection pour le titre du spectre. */
  function selectionTitle(index: SupportIndex) {
    if (filters.zone) return `autour de ${filters.zone.label}`
    if (filters.com) {
      const c = index.dict.com.find(([insee]) => insee === filters.com)
      return c ? `de ${c[1]}` : 'de la sélection'
    }
    if (filters.deps.length === 1) {
      const d = deps.find((x) => x.dep === filters.deps[0])
      return d ? `du département ${d.dep} (${d.nom})` : 'de la sélection'
    }
    return 'de la sélection'
  }
  const otherFilters = $derived(!isEmpty({ ...filters, zone: null }))

  const activeCount = $derived(
    filters.ops.length + filters.gens.length + filters.fams.length + filters.sys.length + filters.deps.length +
    filters.nat.length + (filters.f ? 1 : 0) + (filters.y ? 1 : 0) + (filters.com ? 1 : 0) + (filters.h ? 1 : 0))

  function computeFacets(idx: SupportIndex, sv: Services): Facets {
    // Nombre de supports distincts par exploitant, système et famille.
    const grp = new Array(sv.grps.length).fill(0), sys = new Array(sv.syss.length).fill(0)
    const lastG = new Int32Array(sv.grps.length).fill(-1), lastS = new Int32Array(sv.syss.length).fill(-1)
    const famIdx = new Map<string, number>()
    sv.syss.forEach((x) => { if (!famIdx.has(x.famille)) famIdx.set(x.famille, famIdx.size) })
    const famOf = sv.syss.map((x) => famIdx.get(x.famille)!)
    const famN = new Array(famIdx.size).fill(0), lastF = new Int32Array(famIdx.size).fill(-1)
    for (let i = 0; i < idx.n; i++) {
      for (let r = sv.start[i]; r < sv.start[i + 1]; r++) {
        const g = sv.grp[r], x = sv.sys[r], f = famOf[x]
        if (lastG[g] !== i) { lastG[g] = i; grp[g]++ }
        if (lastS[x] !== i) { lastS[x] = i; sys[x]++ }
        if (lastF[f] !== i) { lastF[f] = i; famN[f]++ }
      }
    }
    return { grp, sys, fam: new Map([...famIdx.entries()].map(([k, v]) => [k, famN[v]])) }
  }

  const data = loadSupports().then((index) => {
    const cats = categorize(index)
    const fromUrl = Number(p.s)
    if (fromUrl && index.byId.has(fromUrl)) {
      selected = index.byId.get(fromUrl)!
      // Lien direct vers un support sans position de carte : on centre sur lui.
      if (!p.c) initialView = { lat: index.lat[selected], lon: index.lon[selected], zoom: 14 }
    }
    // Les services (1,5 Mo) se chargent en arrière-plan, après l'affichage de la carte.
    loadServices()
      .then((sv) => { services = sv; facets = computeFacets(index, sv) })
      .catch((e) => (servicesError = e.message))
    return { index, cats: cats as unknown as Record<string, Uint8Array> }
  })

  // Calcul du masque : différé d'une image pour ne pas bloquer les curseurs.
  const territoryKey = (f: Filters) => `${f.deps.join('|')}#${f.com ?? ''}`
  let result = $state<{ mask: Uint8Array; count: number; territory: string } | null>(null)
  let pending = false
  $effect(() => {
    const f = $state.snapshot(filters) as Filters
    const sv = services
    setParams(toParams(f))
    data.then(({ index }) => {
      if (isEmpty(f)) { result = null; return }
      if (needsServices(f) && !sv) return // on attend les services
      if (pending) return
      pending = true
      requestAnimationFrame(() => {
        pending = false
        const cur = $state.snapshot(filters) as Filters
        result = { ...apply(index, sv, cur), territory: territoryKey(cur) }
      })
    })
  })

  // Recadrage quand le territoire change (une fois le masque correspondant calculé).
  // Au chargement, on garde la vue de l'URL si elle en donne une ; sinon on cadre sur le territoire filtré.
  let lastTerritory = untrack(() => (p.c ? territoryKey(filters) : '#'))
  $effect(() => {
    const r = result
    if (!r || r.territory === lastTerritory) return
    lastTerritory = r.territory
    if (r.territory !== '#') untrack(() => mapView?.fitMask(r.mask))
  })

  function counts(index: SupportIndex, cats: Record<string, Uint8Array>) {
    const c = new Array(colorMode.categories.length).fill(0)
    const arr = cats[colorMode.prop], m = result?.mask
    for (let i = 0; i < index.n; i++) if (!m || m[i]) c[arr[i]]++
    return c
  }

  function toggle(key: number) {
    const cur = new Set(hidden)
    if (cur.has(key)) cur.delete(key)
    else cur.add(key)
    hiddenByMode = { ...hiddenByMode, [colorId]: [...cur] }
  }
  function only(key: number) {
    const all = colorMode.categories.map((c) => c.key)
    const isOnly = hidden.length === all.length - 1 && !hidden.includes(key)
    hiddenByMode = { ...hiddenByMode, [colorId]: isOnly ? [] : all.filter((k) => k !== key) }
  }

  $effect(() => {
    setParams({ m: display === 'points' ? null : display, col: colorId === 'techno' ? null : colorId })
  })

  function select(i: number | null, index: { id: Int32Array }) {
    selected = i
    setParams({ s: i == null ? null : index.id[i] })
    if (i != null) mapView?.reveal(i)
  }

  const DISPLAYS: { id: DisplayMode; label: string }[] = [
    { id: 'points', label: 'Points' },
    { id: 'groupes', label: 'Groupes' },
    { id: 'densite', label: 'Densité' },
  ]
</script>

<div class="page">
  {#await data}
    <p class="loading">Chargement des supports…</p>
  {:then { index, cats }}
    <MapView bind:this={mapView} {index} {cats} {colorMode} {display} {hidden} visible={result?.mask ?? null} {selected}
      zone={filters.zone} azimuth={azLayers}
      theme={theme.value} view={initialView}
      onselect={(i) => select(i, index)}
      onview={(v) => setParams({ z: v.zoom, c: `${v.lat},${v.lon}` })} />

    <div class="controls" class:open={panelOpen} class:withaz={azimuts.list.length > 0}>
      <PlaceSearch {index} onpick={pickPlace} />
      <div class="bar">
        <button class="toggle" type="button" onclick={() => (panelOpen = !panelOpen)} aria-expanded={panelOpen}>
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M4 7h16M7 12h10M10 17h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
          Filtres{activeCount ? ` (${activeCount})` : ''}
        </button>
        <p class="total" aria-live="polite">
          <strong class="num">{fmt(result ? result.count : index.n)}</strong>
          {result ? `sur ${fmt(index.n)} supports` : 'supports'}
        </p>
        {#if result && services && result.count > 0}
          <button class="spec" type="button" onclick={() => (spectrumOpen = true)} title="Occupation des fréquences de la sélection">Spectre</button>
        {/if}
      </div>
      {#if azimuts.list.length}
        <AzimuthPanel {index} onopen={(i) => { select(i, index); mapView?.focus(i) }} />
      {/if}
      {#if panelOpen}
        <div class="panel">
          <div class="tabs" role="tablist">
            <button role="tab" aria-selected={tab === 'filtres'} onclick={() => (tab = 'filtres')}>Filtres</button>
            <button role="tab" aria-selected={tab === 'affichage'} onclick={() => (tab = 'affichage')}>Affichage</button>
            {#if activeCount}
              <button class="reset" type="button" onclick={() => (filters = { ...EMPTY, zone: filters.zone })}>Tout effacer</button>
            {/if}
          </div>
          {#if tab === 'filtres'}
            <FilterPanel bind:filters {index} {services} {facets} {deps} {servicesError} />
          {:else}
            <fieldset>
              <legend>Représentation</legend>
              <div class="seg">
                {#each DISPLAYS as d (d.id)}
                  <button type="button" aria-pressed={display === d.id} onclick={() => (display = d.id)}>{d.label}</button>
                {/each}
              </div>
            </fieldset>
            <label class="field">
              <span>Couleur selon</span>
              <select bind:value={colorId}>
                {#each COLOR_MODES as m (m.id)}<option value={m.id}>{m.label}</option>{/each}
              </select>
            </label>
            {@const cnt = counts(index, cats)}
            <ul class="legend" aria-label="Légende ; cliquer pour masquer ou afficher une catégorie">
              {#each colorMode.categories as c (c.key)}
                <li>
                  <button type="button" class:off={hidden.includes(c.key)} aria-pressed={!hidden.includes(c.key)}
                    onclick={() => toggle(c.key)} ondblclick={() => only(c.key)}
                    title="Cliquer pour masquer ou afficher ; double-cliquer pour isoler">
                    <span class="dot" style:background={c.color}></span>
                    <span class="lab">{c.label}</span>
                    <span class="n num">{fmt(cnt[c.key])}</span>
                  </button>
                </li>
              {/each}
            </ul>
            <p class="hint">Cliquez sur un support pour ouvrir sa fiche.</p>
          {/if}
        </div>
      {/if}
    </div>

    {#if selected !== null}
      {@const sel = selected}
      <div class="sheet-wrap">
        <SupportSheet {index} i={sel} onclose={() => select(null, index)} onfocus={() => mapView?.focus(sel)}
          back={filters.zone ? { label: `Autour de ${filters.zone.label}`, go: () => select(null, index) } : null} />
      </div>
    {:else if filters.zone}
      {@const z = filters.zone}
      <div class="sheet-wrap">
        <ZonePanel {index} {services} zone={z} mask={result?.mask ?? null} filtered={otherFilters}
          onselect={(i) => select(i, index)}
          onradius={(r) => (filters = { ...filters, zone: { ...z, r } })}
          onclose={() => (filters = { ...filters, zone: null })} />
      </div>
    {/if}
    {#if spectrumOpen && services && result}
      <SpectrumDialog occ={occupation(services, result.mask, index.n)} count={result.count}
        title={selectionTitle(index)} onclose={() => (spectrumOpen = false)} />
    {/if}
  {:catch e}
    <p class="loading">Les supports n'ont pas pu être chargés ({e.message}).</p>
  {/await}
</div>

<style>
  .page { position: relative; height: calc(100dvh - 57px); overflow: hidden; background: var(--page); }
  .loading { padding: 40px var(--gutter); color: var(--text-2); }

  .controls { position: absolute; top: 12px; left: 12px; z-index: 3; width: min(320px, calc(100% - 70px)); display: grid; gap: 8px; }
  .bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .spec {
    padding: 6px 10px; border-radius: var(--radius); border: 1px solid var(--line-strong); cursor: pointer; font-size: 0.85rem;
    background: color-mix(in srgb, var(--surface) 88%, transparent); color: var(--text);
  }
  .spec:hover { border-color: var(--accent); }
  .bar .total {
    padding: 6px 10px; border-radius: var(--radius); background: color-mix(in srgb, var(--surface) 88%, transparent);
    border: 1px solid var(--line); white-space: nowrap; font-size: 0.85rem;
  }
  .tabs { display: flex; gap: 4px; align-items: center; border-bottom: 1px solid var(--line); margin: -4px 0 2px; }
  .tabs [role='tab'] { background: none; border: 0; padding: 6px 8px; color: var(--text-2); cursor: pointer; font-size: 0.88rem; border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tabs [role='tab'][aria-selected='true'] { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
  .reset { margin-left: auto; background: none; border: 0; color: var(--accent); cursor: pointer; font-size: 0.8rem; }
  .toggle {
    display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text); cursor: pointer; font-size: 0.88rem;
  }
  .panel {
    padding: 14px; border-radius: 10px; background: color-mix(in srgb, var(--surface) 94%, transparent);
    border: 1px solid var(--line); box-shadow: 0 10px 30px rgb(0 0 0 / 0.25); display: grid; gap: 14px;
    max-height: calc(100dvh - 57px - 130px); overflow-y: auto;
  }
  /* Avec le panneau Azimuts au-dessus, le panneau des filtres laisse la place. */
  .controls.withaz .panel { max-height: max(180px, calc(100dvh - 57px - 130px - 330px)); }
  .total { color: var(--text-2); }
  .total strong { color: var(--text); font-weight: 640; }
  fieldset { border: 0; margin: 0; padding: 0; display: grid; gap: 6px; }
  legend, .field span { font-size: 0.78rem; color: var(--muted); padding: 0; }
  .seg { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--line-strong); border-radius: var(--radius); overflow: hidden; }
  .seg button { background: transparent; border: 0; padding: 6px 4px; color: var(--text-2); cursor: pointer; font-size: 0.85rem; }
  .seg button + button { border-left: 1px solid var(--line-strong); }
  .seg button[aria-pressed='true'] { background: var(--accent); color: var(--accent-ink); font-weight: 600; }
  .field { display: grid; gap: 6px; }
  select {
    font: inherit; font-size: 0.88rem; padding: 6px 8px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text);
  }
  .legend { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
  .legend button {
    width: 100%; display: flex; align-items: center; gap: 8px; padding: 4px 6px; border-radius: 4px;
    background: none; border: 0; color: var(--text); cursor: pointer; font-size: 0.86rem; text-align: left;
  }
  .legend button:hover { background: var(--surface-2); }
  .legend button.off { color: var(--muted); }
  .legend button.off .dot { background: transparent !important; box-shadow: inset 0 0 0 1.5px var(--muted); }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
  .lab { flex: 1; }
  .n { color: var(--text-2); font-size: 0.8rem; }
  .hint { color: var(--muted); font-size: 0.78rem; }

  .sheet-wrap {
    position: absolute; z-index: 4; top: 0; right: 0; bottom: 0; width: min(440px, 100%);
    background: var(--surface); border-left: 1px solid var(--line); overflow-y: auto;
    box-shadow: -10px 0 30px rgb(0 0 0 / 0.25);
  }
  @media (max-width: 720px) {
    .sheet-wrap { top: auto; height: 62dvh; width: 100%; border-left: 0; border-top: 1px solid var(--line-strong); border-radius: 14px 14px 0 0; }
  }
</style>
