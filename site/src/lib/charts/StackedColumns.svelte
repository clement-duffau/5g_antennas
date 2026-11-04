<script lang="ts" module>
  export interface Series { key: string; label: string; color: string }
</script>

<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'
  import { fmt, fmtCompact } from '../format'

  /**
   * Colonnes empilées (ou simples si une seule série).
   * values[i][key] = valeur de la série `key` pour la catégorie i.
   */
  let {
    categories, series, values, height = 260, format = fmt, label,
    xLabel = (c: string | number) => String(c), tickEvery = 0,
  }: {
    categories: (string | number)[]
    series: Series[]
    values: Record<string, number>[]
    height?: number
    format?: (n: number) => string
    label: string
    xLabel?: (c: string | number) => string
    tickEvery?: number
  } = $props()

  let width = $state(600)
  const m = { top: 10, right: 8, bottom: 26, left: 44 }
  const innerW = $derived(Math.max(10, width - m.left - m.right))
  const innerH = $derived(height - m.top - m.bottom)

  const totals = $derived(values.map((v) => series.reduce((s, se) => s + (v[se.key] ?? 0), 0)))
  const yStep = $derived(niceStep(Math.max(1, ...totals) / 4))
  const yMax = $derived(Math.max(yStep, Math.ceil(Math.max(1, ...totals) / yStep) * yStep))
  const band = $derived(innerW / Math.max(1, categories.length))
  const barW = $derived(Math.min(24, Math.max(2, band - 2)))
  const y = (v: number) => innerH - (v / yMax) * innerH
  const ticks = $derived(Array.from({ length: Math.round(yMax / yStep) + 1 }, (_, k) => k * yStep))
  const every = $derived(tickEvery || Math.max(1, Math.ceil(categories.length / Math.max(1, Math.floor(innerW / 44)))))

  function niceStep(v: number) {
    const p = 10 ** Math.floor(Math.log10(v))
    for (const k of [1, 2, 2.5, 5, 10]) if (k * p >= v) return k * p
    return 10 * p
  }

  /** Rectangle à coins supérieurs arrondis (bout de donnée), base carrée. */
  function topRounded(x: number, yTop: number, w: number, h: number, r = 4) {
    const rr = Math.min(r, w / 2, h)
    return `M${x},${yTop + h}V${yTop + rr}Q${x},${yTop} ${x + rr},${yTop}H${x + w - rr}Q${x + w},${yTop} ${x + w},${yTop + rr}V${yTop + h}Z`
  }

  // Segments empilés, avec 2 px de surface entre segments.
  const stacks = $derived(
    values.map((v) => {
      let acc = 0
      const segs: { key: string; color: string; y: number; h: number }[] = []
      for (const se of series) {
        const val = v[se.key] ?? 0
        if (val <= 0) continue
        const y0 = y(acc), y1 = y(acc + val)
        acc += val
        segs.push({ key: se.key, color: se.color, y: y1, h: Math.max(0, y0 - y1) })
      }
      return segs.map((s, j) => (j > 0 ? { ...s, h: Math.max(0, s.h - 2) } : s))
    }),
  )

  let hover = $state<number | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function move(e: PointerEvent, i: number) {
    const r = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - r.left, y: e.clientY - r.top }
    hover = i
  }
</script>

<figure class="chart" bind:clientWidth={width}>
  {#if series.length > 1}
    <ul class="legend">
      {#each series as s (s.key)}
        <li><span class="sw" style:background={s.color}></span>{s.label}</li>
      {/each}
    </ul>
  {/if}
  <div class="plot">
    <svg {width} {height} role="img" aria-label={label}>
      <g transform="translate({m.left},{m.top})">
        {#each ticks as t}
          <line x1="0" x2={innerW} y1={y(t)} y2={y(t)} class:base={t === 0} class="grid" />
          <text x="-8" y={y(t)} dy="0.32em" text-anchor="end" class="axis">{fmtCompact(t)}</text>
        {/each}
        {#each stacks as segs, i}
          {@const cx = i * band + band / 2}
          <g class:dim={hover !== null && hover !== i}>
            {#each segs as s, j}
              {#if j === segs.length - 1}
                <path d={topRounded(cx - barW / 2, s.y, barW, s.h)} fill={s.color} />
              {:else}
                <rect x={cx - barW / 2} y={s.y} width={barW} height={s.h} fill={s.color} />
              {/if}
            {/each}
          </g>
          {#if i % every === 0}
            <text x={cx} y={innerH + 18} text-anchor="middle" class="axis">{xLabel(categories[i])}</text>
          {/if}
          <rect
            x={i * band} y="0" width={band} height={innerH} fill="transparent"
            role="presentation"
            onpointermove={(e) => move(e, i)}
            onpointerleave={() => (hover = null)}
          />
        {/each}
      </g>
    </svg>
    <Tooltip x={tip.x} y={tip.y} visible={hover !== null} {width}>
      {#if hover !== null}
        <div class="t-head">{xLabel(categories[hover])}</div>
        {#if series.length > 1}
          {#each [...series].reverse() as s (s.key)}
            <div class="t-row">
              <span class="t-key" style:background={s.color}></span>
              <span class="t-val">{format(values[hover][s.key] ?? 0)}</span>
              <span class="t-lab">{s.label}</span>
            </div>
          {/each}
          <div class="t-row"><span class="t-key"></span><span class="t-val">{format(totals[hover])}</span><span class="t-lab">total</span></div>
        {:else}
          <div class="t-row"><span class="t-val">{format(totals[hover])}</span><span class="t-lab">{series[0]?.label}</span></div>
        {/if}
      {/if}
    </Tooltip>
  </div>
</figure>

<style>
  .chart { margin: 0; position: relative; min-width: 0; }
  .plot { position: relative; }
  svg { display: block; overflow: visible; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .grid.base { stroke: var(--line-strong); }
  .axis { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
  .dim { opacity: 0.45; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; list-style: none; margin: 0 0 10px; padding: 0; font-size: 0.84rem; color: var(--text-2); }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .sw { width: 10px; height: 10px; border-radius: 2px; }
</style>
