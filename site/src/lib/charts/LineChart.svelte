<script lang="ts" module>
  export interface LineSeries { key: string; label: string; color: string; values: (number | null)[] }
</script>

<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'
  import { fmt, fmtCompact } from '../format'

  /**
   * Courbes sur un axe commun. Réticule et infobulle au survol (toutes les séries à la position),
   * curseur optionnel (position courante d'une animation), clic pour choisir une position.
   */
  let {
    xs, series, label, xLabel, xTick, height = 260, cursor = null, onpick, format = fmt, endLabels = true,
  }: {
    xs: number[]
    series: LineSeries[]
    label: string
    /** libellé complet d'une abscisse (infobulle) */
    xLabel: (x: number) => string
    /** libellé de graduation, ou null pour ne pas graduer cette abscisse */
    xTick: (x: number, i: number) => string | null
    height?: number
    cursor?: number | null
    onpick?: (x: number) => void
    format?: (n: number) => string
    endLabels?: boolean
  } = $props()

  let width = $state(600)
  const m = $derived({ top: 12, right: endLabels && series.length > 1 ? 86 : 12, bottom: 26, left: 46 })
  const iw = $derived(Math.max(10, width - m.left - m.right))
  const ih = $derived(height - m.top - m.bottom)
  const yMax = $derived(nice(Math.max(1, ...series.flatMap((s) => s.values.filter((v): v is number => v != null)))))
  const x = (i: number) => (xs.length > 1 ? (i / (xs.length - 1)) * iw : iw / 2)
  const y = (v: number) => ih - (v / yMax) * ih
  const yTicks = $derived([0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax))

  function nice(v: number) {
    const p = 10 ** Math.floor(Math.log10(v))
    for (const k of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (k * p >= v) return k * p
    return v
  }
  function path(vals: (number | null)[]) {
    let d = '', pen = false
    vals.forEach((v, i) => {
      if (v == null) { pen = false; return }
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
      pen = true
    })
    return d
  }
  const lastIdx = (vals: (number | null)[]) => { for (let i = vals.length - 1; i >= 0; i--) if (vals[i] != null) return i; return -1 }

  // Libellés de fin de courbe, écartés s'ils se chevauchent.
  const ends = $derived.by(() => {
    const e = series.map((s) => { const i = lastIdx(s.values); return { s, i, y: i < 0 ? 0 : y(s.values[i]!) } }).filter((e) => e.i >= 0)
    e.sort((a, b) => a.y - b.y)
    for (let k = 1; k < e.length; k++) if (e[k].y - e[k - 1].y < 13) e[k].y = e[k - 1].y + 13
    return e
  })

  let hover = $state<number | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function idxAt(e: PointerEvent) {
    const r = (e.currentTarget as SVGElement).getBoundingClientRect()
    const px = e.clientX - r.left
    return Math.max(0, Math.min(xs.length - 1, Math.round((px / iw) * (xs.length - 1))))
  }
  function move(e: PointerEvent) {
    const svg = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - svg.left, y: e.clientY - svg.top }
    hover = idxAt(e)
  }
  const cursorIdx = $derived(cursor == null ? -1 : xs.indexOf(cursor))
</script>

<figure class="chart" bind:clientWidth={width}>
  {#if series.length > 1}
    <ul class="legend">
      {#each series as s (s.key)}<li><span class="key" style:background={s.color}></span>{s.label}</li>{/each}
    </ul>
  {/if}
  <div class="plot">
    <svg {width} {height} role="img" aria-label={label}>
      <g transform="translate({m.left},{m.top})">
        {#each yTicks as t}
          <line x1="0" x2={iw} y1={y(t)} y2={y(t)} class="grid" class:base={t === 0} />
          <text x="-8" y={y(t)} dy="0.32em" text-anchor="end" class="axis">{fmtCompact(t)}</text>
        {/each}
        {#each xs as xv, i}
          {@const t = xTick(xv, i)}
          {#if t}<text x={x(i)} y={ih + 18} text-anchor="middle" class="axis">{t}</text>{/if}
        {/each}
        {#if cursorIdx >= 0}
          <line x1={x(cursorIdx)} x2={x(cursorIdx)} y1="0" y2={ih} class="cursor" />
        {/if}
        {#each series as s (s.key)}
          <path d={path(s.values)} fill="none" stroke={s.color} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        {/each}
        {#if endLabels && series.length > 1}
          {#each ends as e (e.s.key)}
            <circle cx={x(e.i)} cy={y(e.s.values[e.i]!)} r="4" fill={e.s.color} stroke="var(--surface)" stroke-width="2" />
            <text x={x(e.i) + 9} y={e.y} dy="0.32em" class="end">{e.s.label}</text>
          {/each}
        {/if}
        {#if hover !== null}
          <line x1={x(hover)} x2={x(hover)} y1="0" y2={ih} class="cross" />
          {#each series as s (s.key)}
            {#if s.values[hover] != null}<circle cx={x(hover)} cy={y(s.values[hover]!)} r="4" fill={s.color} stroke="var(--surface)" stroke-width="2" />{/if}
          {/each}
        {/if}
        <rect width={iw} height={ih} fill="transparent" role="presentation" style:cursor={onpick ? 'pointer' : 'default'}
          onpointermove={move} onpointerleave={() => (hover = null)}
          onclick={(e) => onpick?.(xs[idxAt(e as unknown as PointerEvent)])} />
      </g>
    </svg>
    <Tooltip x={tip.x} y={tip.y} visible={hover !== null} {width}>
      {#if hover !== null}
        <div class="t-head">{xLabel(xs[hover])}</div>
        {#each [...series].sort((a, b) => (b.values[hover!] ?? -1) - (a.values[hover!] ?? -1)) as s (s.key)}
          <div class="t-row"><span class="t-key" style:background={s.color}></span>
            <span class="t-val">{s.values[hover] == null ? '–' : format(s.values[hover]!)}</span><span class="t-lab">{s.label}</span></div>
        {/each}
      {/if}
    </Tooltip>
  </div>
</figure>

<style>
  .chart { margin: 0; min-width: 0; }
  .plot { position: relative; }
  svg { display: block; overflow: visible; }
  .grid { stroke: var(--line); }
  .grid.base { stroke: var(--line-strong); }
  .axis { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
  .end { fill: var(--text-2); font-size: 11.5px; }
  .cursor { stroke: var(--text-2); stroke-width: 1; }
  .cross { stroke: var(--line-strong); stroke-width: 1; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; list-style: none; margin: 0 0 10px; padding: 0; font-size: 0.84rem; color: var(--text-2); }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .key { width: 14px; height: 2px; border-radius: 1px; }
</style>
