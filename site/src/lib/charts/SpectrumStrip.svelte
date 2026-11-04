<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'
  import { fmt, fmtPct } from '../format'
  import { MOBILE_OPS, opColor } from '../colors'

  /** Occupation du spectre mobile par opérateur : un panneau par bande, échelle linéaire en MHz. */
  interface Block { groupe: string; systeme: string; f_deb: number; f_fin: number; n: number; part: number }
  let { blocks }: { blocks: Block[] } = $props()

  // Bandes 3GPP utilisées en France métropolitaine et leurs sous-bandes duplex.
  const PANELS = [
    { name: '700', lo: 700, hi: 792, duplex: [['UL', 703, 733], ['DL', 758, 788]] },
    { name: '800', lo: 788, hi: 864, duplex: [['DL', 791, 821], ['UL', 832, 862]] },
    { name: '900', lo: 876, hi: 962, duplex: [['UL', 880, 915], ['DL', 925, 960]] },
    { name: '1800', lo: 1705, hi: 1885, duplex: [['UL', 1710, 1785], ['DL', 1805, 1880]] },
    { name: '2100', lo: 1915, hi: 2175, duplex: [['UL', 1920, 1980], ['DL', 2110, 2170]] },
    { name: '2600', lo: 2495, hi: 2695, duplex: [['UL', 2500, 2570], ['TDD', 2570, 2620], ['DL', 2620, 2690]] },
    { name: '3500', lo: 3390, hi: 3810, duplex: [['TDD', 3400, 3800]] },
  ] as const

  let width = $state(900)
  const narrow = $derived(width < 720)
  const gap = 12
  const rowH = 18
  const rowGap = 6
  const labelW = $derived(narrow ? 0 : 118)
  const top = 22
  const plotH = MOBILE_OPS.length * (rowH + rowGap)
  const panelH = top + plotH + 30

  // Largeur proportionnelle à la largeur en MHz (sur écran large) ; grille 2 colonnes sinon.
  const layout = $derived.by(() => {
    if (narrow) {
      const cols = width < 420 ? 1 : 2
      const w = (width - gap * (cols - 1)) / cols
      return PANELS.map((p, i) => ({ p, x: (i % cols) * (w + gap), y: Math.floor(i / cols) * (panelH + 8), w }))
    }
    const span = PANELS.reduce((s, p) => s + (p.hi - p.lo), 0)
    const avail = width - labelW - gap * (PANELS.length - 1)
    let x = labelW
    return PANELS.map((p) => {
      const w = Math.max(54, (avail * (p.hi - p.lo)) / span)
      const o = { p, x, y: 0, w }
      x += w + gap
      return o
    })
  })
  const totalH = $derived(narrow ? Math.ceil(PANELS.length / (width < 420 ? 1 : 2)) * (panelH + 8) : panelH)

  // Fusionne les systèmes partageant un même bloc (ex. GSM 1800 et LTE 1800).
  const merged = $derived.by(() => {
    const map = new Map<string, { groupe: string; f_deb: number; f_fin: number; items: Block[] }>()
    for (const b of blocks) {
      const k = `${b.groupe}|${b.f_deb}|${b.f_fin}`
      if (!map.has(k)) map.set(k, { groupe: b.groupe, f_deb: b.f_deb, f_fin: b.f_fin, items: [] })
      map.get(k)!.items.push(b)
    }
    return [...map.values()]
  })

  let hover = $state<(typeof merged)[number] | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function move(e: PointerEvent, b: (typeof merged)[number]) {
    const r = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - r.left, y: e.clientY - r.top }
    hover = b
  }
  const opLabel = (op: string) => (op === 'Bouygues Telecom' ? 'Bouygues' : op)
</script>

<figure class="spectrum" bind:clientWidth={width}>
  <ul class="legend">
    {#each MOBILE_OPS as op}
      <li><span class="sw" style:background={opColor(op)}></span>{op}</li>
    {/each}
  </ul>
  <div class="plot">
    <svg {width} height={totalH} role="img"
      aria-label="Blocs de fréquences utilisés par chaque opérateur mobile, de 700 à 3800 MHz">
      {#if !narrow}
        {#each MOBILE_OPS as op, r}
          <text x="0" y={top + r * (rowH + rowGap) + rowH / 2} dy="0.32em" class="rowlab">{opLabel(op)}</text>
        {/each}
      {/if}
      {#each layout as { p, x, y, w } (p.name)}
        {@const sx = (f: number) => x + ((f - p.lo) / (p.hi - p.lo)) * w}
        <g transform="translate(0,{y})">
          <text x={x} y="12" class="band">{p.name} <tspan class="unit">MHz</tspan></text>
          <rect x={x} y={top - 4} width={w} height={plotH} class="bg" rx="3" />
          {#each MOBILE_OPS as op, r}
            {#each merged.filter((b) => b.groupe === op && b.f_fin > p.lo && b.f_deb < p.hi) as b}
              <rect
                x={sx(Math.max(b.f_deb, p.lo)) + 0.5}
                y={top + r * (rowH + rowGap)}
                width={Math.max(1.5, sx(Math.min(b.f_fin, p.hi)) - sx(Math.max(b.f_deb, p.lo)) - 1)}
                height={rowH}
                rx="2"
                fill={opColor(op)}
                class:dim={hover && hover !== b}
                role="presentation"
                onpointermove={(e) => move(e, b)}
                onpointerleave={() => (hover = null)}
              />
            {/each}
          {/each}
          {#each p.duplex as [kind, lo, hi]}
            <line x1={sx(lo) + 1} x2={sx(hi) - 1} y1={top + plotH + 2} y2={top + plotH + 2} class="duplex" />
            <text x={(sx(lo) + sx(hi)) / 2} y={top + plotH + 14} text-anchor="middle" class="dlab">{kind}</text>
          {/each}
          <text x={x} y={top + plotH + 27} class="tick">{p.lo}</text>
          <text x={x + w} y={top + plotH + 27} text-anchor="end" class="tick">{p.hi}</text>
        </g>
      {/each}
    </svg>
    <Tooltip x={tip.x} y={tip.y} visible={hover !== null} {width}>
      {#if hover}
        <div class="t-head">{hover.groupe}</div>
        <div class="t-row"><span class="t-val">{hover.f_deb} – {hover.f_fin} MHz</span></div>
        <div class="t-row"><span class="t-lab">largeur {Math.round((hover.f_fin - hover.f_deb) * 10) / 10} MHz</span></div>
        {#each hover.items as it}
          <div class="t-row"><span class="t-lab">{it.systeme} · {fmt(it.n)} émetteurs ({fmtPct(it.part)})</span></div>
        {/each}
      {/if}
    </Tooltip>
  </div>
  {#if narrow}
    <p class="note">Rangées de haut en bas : {MOBILE_OPS.map(opLabel).join(', ')}.</p>
  {/if}
</figure>

<style>
  .spectrum { margin: 0; min-width: 0; }
  .plot { position: relative; }
  svg { display: block; overflow: visible; }
  .bg { fill: var(--surface-2); opacity: 0.6; }
  .band { fill: var(--text); font-size: 13px; font-weight: 640; font-stretch: 112%; }
  .unit { fill: var(--muted); font-weight: 400; font-size: 11px; }
  .rowlab { fill: var(--text-2); font-size: 12.5px; }
  .tick { fill: var(--muted); font-size: 10.5px; font-variant-numeric: tabular-nums; }
  .duplex { stroke: var(--line-strong); stroke-width: 1; }
  .dlab { fill: var(--muted); font-size: 10px; letter-spacing: 0.04em; }
  rect[role='presentation'] { cursor: default; transition: opacity 120ms; }
  .dim { opacity: 0.35; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; list-style: none; margin: 0 0 12px; padding: 0; font-size: 0.84rem; color: var(--text-2); }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .sw { width: 10px; height: 10px; border-radius: 2px; }
  .note { font-size: 0.8rem; color: var(--muted); margin-top: 6px; }
</style>
