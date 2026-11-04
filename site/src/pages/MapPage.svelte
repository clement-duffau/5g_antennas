<script lang="ts">
  import MapView, { type DisplayMode, type View } from '../lib/map/MapView.svelte'
  import SupportSheet from '../lib/map/SupportSheet.svelte'
  import { loadSupports } from '../lib/supports'
  import { categorize, COLOR_MODES } from '../lib/categories'
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
  let panelOpen = $state(typeof window !== 'undefined' && window.innerWidth > 720)
  let mapView = $state<MapView>()

  const data = loadSupports().then((index) => {
    const cats = categorize(index)
    const counts: Record<string, number[]> = {}
    for (const m of COLOR_MODES) {
      const c = new Array(m.categories.length).fill(0)
      for (let i = 0; i < index.n; i++) c[cats[m.prop as 't' | 'o' | 'h'][i]]++
      counts[m.id] = c
    }
    const fromUrl = Number(p.s)
    if (fromUrl && index.byId.has(fromUrl)) {
      selected = index.byId.get(fromUrl)!
      // Lien direct vers un support sans position de carte : on centre sur lui.
      if (!p.c) initialView = { lat: index.lat[selected], lon: index.lon[selected], zoom: 14 }
    }
    return { index, cats: cats as unknown as Record<string, Uint8Array>, counts }
  })

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
    <p class="loading">Chargement des {fmt(93000)} supports…</p>
  {:then { index, cats, counts }}
    <MapView bind:this={mapView} {index} {cats} {colorMode} {display} {hidden} visible={null} {selected}
      theme={theme.value} view={initialView}
      onselect={(i) => select(i, index)}
      onview={(v) => setParams({ z: v.zoom, c: `${v.lat},${v.lon}` })} />

    <div class="controls" class:open={panelOpen}>
      <button class="toggle" type="button" onclick={() => (panelOpen = !panelOpen)} aria-expanded={panelOpen}>
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M4 7h16M7 12h10M10 17h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
        Affichage
      </button>
      {#if panelOpen}
        <div class="panel">
          <p class="total"><strong class="num">{fmt(index.n)}</strong> supports</p>
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
          <ul class="legend" aria-label="Légende ; cliquer pour masquer ou afficher une catégorie">
            {#each colorMode.categories as c (c.key)}
              <li>
                <button type="button" class:off={hidden.includes(c.key)} aria-pressed={!hidden.includes(c.key)}
                  onclick={() => toggle(c.key)} ondblclick={() => only(c.key)}
                  title="Cliquer pour masquer ou afficher ; double-cliquer pour isoler">
                  <span class="dot" style:background={c.color}></span>
                  <span class="lab">{c.label}</span>
                  <span class="n num">{fmt(counts[colorMode.id][c.key])}</span>
                </button>
              </li>
            {/each}
          </ul>
          <p class="hint">Cliquez sur un support pour ouvrir sa fiche.</p>
        </div>
      {/if}
    </div>

    {#if selected !== null}
      {@const sel = selected}
      <div class="sheet-wrap">
        <SupportSheet {index} i={sel} onclose={() => select(null, index)} onfocus={() => mapView?.focus(sel)} />
      </div>
    {/if}
  {:catch e}
    <p class="loading">Les supports n'ont pas pu être chargés ({e.message}).</p>
  {/await}
</div>

<style>
  .page { position: relative; height: calc(100dvh - 57px); overflow: hidden; background: var(--page); }
  .loading { padding: 40px var(--gutter); color: var(--text-2); }

  .controls { position: absolute; top: 12px; left: 12px; z-index: 3; width: min(300px, calc(100% - 70px)); }
  .toggle {
    display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text); cursor: pointer; font-size: 0.88rem;
  }
  .panel {
    margin-top: 8px; padding: 14px; border-radius: 10px; background: color-mix(in srgb, var(--surface) 94%, transparent);
    border: 1px solid var(--line); box-shadow: 0 10px 30px rgb(0 0 0 / 0.25); display: grid; gap: 14px;
    max-height: calc(100dvh - 57px - 80px); overflow-y: auto;
  }
  .total { font-size: 0.95rem; color: var(--text-2); }
  .total strong { color: var(--text); font-size: 1.15rem; font-weight: 640; }
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
