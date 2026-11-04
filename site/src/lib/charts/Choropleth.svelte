<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'

  /**
   * Carte choroplèthe des départements en SVG (projection équirectangulaire corrigée de la latitude),
   * 5 classes par quantiles sur une rampe séquentielle à une teinte.
   */
  interface Feature { properties: { code: string; nom: string }; geometry: { type: string; coordinates: any } }
  let { features, values, format, label, href }: {
    features: Feature[]
    values: Record<string, number | null>
    format: (v: number) => string
    label: string
    /** lien vers la carte filtrée sur le département */
    href?: (code: string) => string
  } = $props()

  let width = $state(480)
  const K = Math.cos((46.5 * Math.PI) / 180)

  // Emprise des départements (métropole + Corse).
  const bbox = $derived.by(() => {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
    const visit = (c: any) => {
      if (typeof c[0] === 'number') {
        const x = c[0] * K, y = -c[1]
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y
      } else c.forEach(visit)
    }
    features.forEach((f) => visit(f.geometry.coordinates))
    return { x0, x1, y0, y1 }
  })
  const scale = $derived(width / (bbox.x1 - bbox.x0))
  const height = $derived(Math.round((bbox.y1 - bbox.y0) * scale))

  function ring(r: number[][]) {
    return r.map(([lon, lat], k) => `${k ? 'L' : 'M'}${((lon * K - bbox.x0) * scale).toFixed(1)},${((-lat - bbox.y0) * scale).toFixed(1)}`).join('') + 'Z'
  }
  function path(g: Feature['geometry']) {
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates
    return polys.map((p: number[][][]) => p.map(ring).join('')).join('')
  }
  const paths = $derived(features.map((f) => ({ code: f.properties.code, nom: f.properties.nom, d: path(f.geometry) })))

  // Classes par quantiles (valeurs non nulles).
  const breaks = $derived.by(() => {
    const v = Object.values(values).filter((x): x is number => x != null).sort((a, b) => a - b)
    if (!v.length) return []
    return [0.2, 0.4, 0.6, 0.8].map((q) => v[Math.min(v.length - 1, Math.floor(q * v.length))])
  })
  const classOf = (v: number | null) => (v == null ? -1 : breaks.filter((b) => v >= b).length)
  const fill = (k: number) => (k < 0 ? 'var(--surface-2)' : `var(--seq-${k + 1})`)
  const legend = $derived(breaks.length
    ? [`< ${format(breaks[0])}`, ...breaks.slice(0, -1).map((b, i) => `${format(b)} – ${format(breaks[i + 1])}`), `≥ ${format(breaks[3])}`]
    : [])

  let hover = $state<{ code: string; nom: string } | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function move(e: PointerEvent, p: { code: string; nom: string }) {
    const r = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - r.left, y: e.clientY - r.top }
    hover = p
  }
</script>

<figure class="choro" bind:clientWidth={width}>
  <div class="plot">
    <svg {width} {height} role="group" aria-label={label}>
      {#each paths as p (p.code)}
        {@const k = classOf(values[p.code] ?? null)}
        <a href={href?.(p.code)} aria-label="{p.nom} : {values[p.code] == null ? 'pas de donnée' : format(values[p.code]!)}">
          <path d={p.d} fill={fill(k)} class:hl={hover?.code === p.code}
            onpointermove={(e) => move(e, p)} onpointerleave={() => (hover = null)} role="presentation" />
        </a>
      {/each}
    </svg>
    <Tooltip x={tip.x} y={tip.y} visible={hover !== null} {width}>
      {#if hover}
        <div class="t-head">{hover.nom} ({hover.code})</div>
        <div class="t-row"><span class="t-val">{values[hover.code] == null ? '–' : format(values[hover.code]!)}</span></div>
        {#if href}<div class="t-row"><span class="t-lab">Cliquer pour voir sur la carte</span></div>{/if}
      {/if}
    </Tooltip>
  </div>
  <ul class="legend" aria-label="Légende">
    {#each legend as l, k}<li><span class="sw" style:background={fill(k)}></span>{l}</li>{/each}
  </ul>
</figure>

<style>
  .choro { margin: 0; min-width: 0; max-width: 560px; }
  .plot { position: relative; }
  svg { display: block; }
  path { stroke: var(--surface); stroke-width: 0.6; transition: opacity 120ms; }
  path.hl { stroke: var(--text); stroke-width: 1.5; }
  a:focus-visible path { stroke: var(--focus); stroke-width: 2; }
  .legend { list-style: none; padding: 0; margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.8rem; color: var(--text-2); }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .sw { width: 14px; height: 10px; border-radius: 2px; }
</style>
