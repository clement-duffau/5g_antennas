<script lang="ts">
  import { onDestroy } from 'svelte'
  import TimelineMap from '../lib/map/TimelineMap.svelte'
  import LineChart, { type LineSeries } from '../lib/charts/LineChart.svelte'
  import Chips from '../lib/ui/Chips.svelte'
  import { loadSupports } from '../lib/supports'
  import { loadServices } from '../lib/services'
  import { loadJSON } from '../lib/data'
  import { cumulative, firstMonths, monthName, monthOf, monthShort, undated, yearOf, MOBILE, type Selection } from '../lib/timeline'
  import { genColor, opColor } from '../lib/colors'
  import { route, setParams } from '../lib/router.svelte'
  import { theme } from '../lib/theme.svelte'
  import { fmt } from '../lib/format'
  import type { Meta } from '../lib/types'

  interface History {
    mois: string[]
    supports: number[]
    emetteurs: number[]
    sites: Record<string, Record<string, (number | null)[]>>
    systemes: Record<string, Record<string, (number | null)[]>>
  }

  const p = route.params
  let op = $state(MOBILE.includes(p.op) ? p.op : 'tous')
  let gen = $state(['2G', '3G', '4G', '5G'].includes(p.gen) ? p.gen : '5G')
  let sys = $state(p.sys || '')
  const sel = $derived<Selection>({ ops: op === 'tous' ? [] : [op], gen: gen === 'tout' ? null : gen, sys: sys || null })

  const data = Promise.all([loadSupports(), loadServices(), loadJSON<Meta>('meta.json')]).then(([index, sv, meta]) => {
    const [y, m] = meta.extraction.split('-').map(Number)
    current = monthOf(y, m)
    return { index, sv, last: monthOf(y, m) }
  })
  const history = loadJSON<History>('history.json').catch(() => null)

  // ------------------------------------------------------------------ animation
  const START = monthOf(1995)
  let current = $state(0)
  let playing = $state(false)
  let speed = $state(2) // mois par image (~8 images/s)
  let timer: ReturnType<typeof setInterval> | undefined

  function play(last: number) {
    if (playing) { pause(); return }
    if (current >= last) current = firstUseful ?? START
    playing = true
    timer = setInterval(() => {
      current = Math.min(last, current + speed)
      if (current >= last) pause()
    }, 120)
  }
  function pause() { playing = false; clearInterval(timer) }
  onDestroy(pause)

  $effect(() => { setParams({ op: op === 'tous' ? null : op, gen: gen === '5G' ? null : gen, sys: sys || null }) })

  let firstUseful = $state<number | null>(null)

  // Systèmes mobiles de la génération choisie (pour le choix de bande).
  function systemsOf(sv: Awaited<typeof data>['sv'], g: string) {
    return sv.syss.filter((x) => x.famille === 'Mobile' && (g === 'tout' || x.generation === g)).map((x) => x.nom).sort((a, b) => a.localeCompare(b, 'fr', { numeric: true }))
  }

  /** Courbes cumulées par opérateur, sur une période adaptée à la génération. */
  function cumulSeries(index: Awaited<typeof data>['index'], sv: Awaited<typeof data>['sv'], last: number) {
    const m0 = gen === '5G' ? monthOf(2019) : gen === '4G' ? monthOf(2011) : monthOf(1995)
    const xs = xsYears(m0, last)
    const series = (op === 'tous' ? MOBILE : [op]).map((o): LineSeries => ({
      key: o, label: o === 'Bouygues Telecom' ? 'Bouygues' : o, color: opColor(o),
      values: cumulative(index, sv, { ...sel, ops: [o] }, m0, last),
    }))
    return { xs, series }
  }

  const xsYears = (m0: number, m1: number) => Array.from({ length: m1 - m0 + 1 }, (_, i) => m0 + i)
  // Graduation à la première abscisse de chaque année (archives : un point par extraction).
  const firstOfYear = (xs: number[]) => (x: number, i: number) => (i === 0 || yearOf(x) !== yearOf(xs[i - 1]) ? String(yearOf(x)) : null)
  const yearTick = (step: number) => (x: number) => ((x - 1) % 12 === 0 && yearOf(x) % step === 0 ? String(yearOf(x)) : null)
</script>

<article class="frise">
  <header class="intro">
    <h1>Le déploiement, mois par mois</h1>
    <p class="lede">
      Chaque support apparaît le mois où l'opérateur y a mis en service sa première antenne de la technologie choisie.
      Les points jaunes sont les mises en service des six derniers mois.
    </p>
  </header>

  {#await data}
    <p class="muted">Chargement des supports et des dates de mise en service…</p>
  {:then { index, sv, last }}
    {@const months = firstMonths(index, sv, sel)}
    {@const count = months.reduce((t, m) => t + (m && m <= current ? 1 : 0), 0)}
    {@const sansDate = undated(index, sv, sel)}
    {@const cum = cumulSeries(index, sv, last)}

    <div class="controls">
      <Chips label="Opérateur" bind:value={op}
        options={[{ value: 'tous', label: 'Tous' }, ...MOBILE.map((o) => ({ value: o, label: o === 'Bouygues Telecom' ? 'Bouygues' : o }))]} />
      <Chips label="Technologie" bind:value={gen}
        options={[...['5G', '4G', '3G', '2G'].map((g) => ({ value: g, label: g })), { value: 'tout', label: 'Toutes' }]} />
      <label class="sel">
        <span class="visually-hidden">Bande</span>
        <select bind:value={sys}>
          <option value="">Toutes les bandes</option>
          {#each systemsOf(sv, gen) as s (s)}<option value={s}>{s}</option>{/each}
        </select>
      </label>
    </div>

    <div class="stage">
      <TimelineMap {index} {months} {current} theme={theme.value}
        color={op === 'tous' ? (gen === 'tout' ? 'var(--seq-3)' : genColor(gen)) : opColor(op)} />
      <div class="hud" aria-live="polite">
        <p class="when">{monthName(current)}</p>
        <p class="count"><strong class="num">{fmt(count)}</strong> sites</p>
      </div>
      <div class="player">
        <button type="button" class="play" onclick={() => play(last)} aria-label={playing ? 'Mettre en pause' : 'Lancer la lecture'}>
          {#if playing}
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M8 5v14M16 5v14" stroke="currentColor" stroke-width="3" stroke-linecap="round" /></svg>
          {:else}
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M7 4.5v15l12-7.5z" fill="currentColor" /></svg>
          {/if}
        </button>
        <input type="range" min={START} max={last} step="1" bind:value={current} aria-label="Date" oninput={pause} />
        <select bind:value={speed} aria-label="Vitesse">
          <option value={1}>×1</option><option value={2}>×2</option><option value={4}>×4</option>
        </select>
      </div>
    </div>

    <section>
      <h2>Sites en service selon leur date de mise en service</h2>
      <p class="note">
        Parc actuel : un site démonté depuis n'apparaît pas, ce qui sous-estime les débuts de la 2G et de la 3G.
        {#if sansDate}{fmt(sansDate)} sites sans date de mise en service sont exclus.{/if}
        Cliquez sur la courbe pour vous placer à une date.
      </p>
      <LineChart xs={cum.xs} series={cum.series} cursor={current} onpick={(x) => { pause(); current = x }}
        label="Nombre cumulé de sites par opérateur" xLabel={monthName} xTick={yearTick(cum.xs.length > 150 ? 5 : 1)} height={300} />
    </section>

    {#await history then h}
      {#if h && h.mois.length > 1}
        {@const xs = h.mois.map((m) => monthOf(+m.slice(0, 4), +m.slice(5, 7)))}
        {@const g = gen === 'tout' ? 'total' : gen}
        {@const syss = Object.keys(h.systemes).filter((s) => sv.syss.find((x) => x.nom === s && x.famille === 'Mobile' && (gen === 'tout' || x.generation === gen)))}
        <section>
          <h2>Le parc déclaré, archive par archive</h2>
          <p class="note">
            {h.mois.length} extractions mensuelles de l'ANFR, de {monthName(xs[0])} à {monthName(xs[xs.length - 1])}.
            Contrairement aux dates de mise en service, ces séries montrent aussi les sites démontés : extinction de la 2G et de la 3G, refarming des bandes.
          </p>
          <div class="grid2">
            <div>
              <h3>Sites {gen === 'tout' ? 'mobiles' : gen} par opérateur</h3>
              <LineChart {xs} label="Sites par opérateur selon les archives"
                series={(op === 'tous' ? MOBILE : [op]).map((o) => ({ key: o, label: o === 'Bouygues Telecom' ? 'Bouygues' : o, color: opColor(o), values: h.sites[o]?.[g] ?? [] }))}
                xLabel={monthName} xTick={firstOfYear(xs)} height={260} />
            </div>
            <div>
              <h3>Émetteurs par bande{op === 'tous' ? '' : ` (${op === 'Bouygues Telecom' ? 'Bouygues' : op})`}</h3>
              <LineChart {xs} label="Émetteurs par système selon les archives"
                series={syss.slice(0, 8).map((s, k) => ({ key: s, label: s, color: `var(--cat-${(k % 7) + 1})`, values: h.systemes[s][op === 'tous' ? 'total' : op] ?? [] }))}
                xLabel={monthName} xTick={firstOfYear(xs)} height={260} />
            </div>
          </div>
        </section>
      {:else}
        <section>
          <h2>Le parc déclaré, archive par archive</h2>
          <p class="note">L'historique des archives n'est pas encore disponible dans cette version du site.</p>
        </section>
      {/if}
    {/await}
  {:catch e}
    <p class="muted">La frise n'a pas pu être chargée ({e.message}).</p>
  {/await}
</article>

<style>
  .frise { padding-block: clamp(28px, 5vw, 56px); display: grid; gap: 24px; }
  /* Les éléments de grille ne doivent pas s'élargir à la taille des SVG (débordement sur mobile). */
  .frise > :global(*), section > :global(*), .grid2 > :global(*) { min-width: 0; }
  .intro { display: grid; gap: 12px; }
  .lede { color: var(--text-2); font-size: 1.05rem; }
  .muted { color: var(--muted); }
  .controls { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
  .sel select { font: inherit; font-size: 0.86rem; padding: 5px 8px; border-radius: var(--radius); border: 1px solid var(--line-strong); background: var(--surface); color: var(--text); }
  .stage { position: relative; height: min(68vh, 640px); min-height: 380px; border-radius: 10px; overflow: hidden; border: 1px solid var(--line); background: var(--surface); }
  .hud { position: absolute; left: 14px; top: 12px; z-index: 2; pointer-events: none; text-shadow: 0 1px 8px var(--page); }
  .when { font-size: clamp(1.4rem, 3.5vw, 2.4rem); font-weight: 680; font-stretch: 118%; line-height: 1.1; }
  .count { color: var(--text-2); }
  .count strong { color: var(--text); font-weight: 640; }
  .player {
    position: absolute; left: 12px; right: 12px; bottom: 34px; z-index: 2; display: flex; gap: 10px; align-items: center;
    padding: 8px 10px; border-radius: 10px; background: color-mix(in srgb, var(--surface) 90%, transparent); border: 1px solid var(--line);
  }
  .play { width: 36px; height: 36px; border-radius: 50%; border: 0; background: var(--accent); color: var(--accent-ink); display: grid; place-items: center; cursor: pointer; flex: none; }
  .player input { flex: 1; accent-color: var(--accent); }
  .player select { font: inherit; font-size: 0.8rem; background: var(--surface); color: var(--text); border: 1px solid var(--line-strong); border-radius: var(--radius); padding: 3px 4px; }
  section { display: grid; gap: 10px; padding-top: 24px; border-top: 1px solid var(--line); }
  h3 { margin-bottom: 8px; }
  .note { color: var(--muted); font-size: 0.86rem; }
  .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 32px; }
</style>
