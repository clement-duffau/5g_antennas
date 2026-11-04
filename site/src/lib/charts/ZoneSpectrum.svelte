<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'
  import DataTable, { type Column } from '../ui/DataTable.svelte'
  import { ITU_BANDS, VIEWS, type Occupation } from '../spectrum'
  import { MOBILE_OPS, opColor } from '../colors'
  import { fmt } from '../format'

  /**
   * Occupation des fréquences d'une sélection : une rangée par exploitant, une barre par bande déclarée.
   * Couleur = famille de systèmes (les réseaux mobiles gardent la couleur de l'opérateur) ;
   * opacité = part des supports de la rangée qui déclarent la bande.
   */
  let { occ, compact = false, table = true }: { occ: Occupation[]; compact?: boolean; table?: boolean } = $props()

  let viewId = $state('tout')
  const view = $derived(VIEWS.find((v) => v.id === viewId)!)
  let width = $state(400)
  const labelW = $derived(width < 420 ? 74 : 112)
  const iw = $derived(Math.max(40, width - labelW - 8))
  const rowH = $derived(compact ? 13 : 16)
  const gap = 5
  const top = 22

  const isMobileOp = (g: string) => (MOBILE_OPS as readonly string[]).includes(g)
  function color(o: Occupation) {
    if (o.famille === 'Mobile') return isMobileOp(o.grp) ? opColor(o.grp) : 'var(--cat-1)'
    if (o.famille === 'Radiodiffusion') return 'var(--cat-4)'
    if (o.famille === 'Faisceau hertzien') return 'var(--cat-5)'
    if (['PMR', 'Réseau privé', 'Ferroviaire'].includes(o.famille)) return 'var(--cat-6)'
    if (o.famille === 'Boucle locale radio') return 'var(--cat-2)'
    return 'var(--cat-7)'
  }
  const LEGEND = [
    ['Réseaux mobiles (couleur de l\'opérateur)', 'linear-gradient(90deg, var(--op-orange) 25%, var(--op-bouygues) 25% 50%, var(--op-sfr) 50% 75%, var(--op-free) 75%)'],
    ['Radio et télévision', 'var(--cat-4)'], ['Faisceaux hertziens', 'var(--cat-5)'],
    ['PMR, réseaux privés, GSM-R', 'var(--cat-6)'], ['Boucle locale radio', 'var(--cat-2)'], ['Autres', 'var(--cat-7)'],
  ]

  const x = (f: number) => {
    const { lo, hi, log } = view
    const c = Math.min(hi, Math.max(lo, f))
    return log ? (Math.log(c / lo) / Math.log(hi / lo)) * iw : ((c - lo) / (hi - lo)) * iw
  }

  const visible = $derived(occ.filter((o) => o.f1 >= view.lo && o.f0 <= view.hi))

  // Rangées : opérateurs mobiles d'abord (ordre fixe), puis les autres exploitants par volume ; au-delà de 10, « Autres ».
  const lanes = $derived.by(() => {
    const tot = new Map<string, number>()
    for (const o of visible) tot.set(o.grp, (tot.get(o.grp) ?? 0) + o.n)
    const mob = MOBILE_OPS.filter((g) => tot.has(g))
    const others = [...tot.keys()].filter((g) => !isMobileOp(g)).sort((a, b) => tot.get(b)! - tot.get(a)!)
    const MAX = compact ? 8 : 10
    const named = [...mob, ...others].slice(0, MAX)
    const rest = [...mob, ...others].slice(MAX)
    return { names: rest.length ? [...named, `Autres (${rest.length})`] : named, restSet: new Set(rest) }
  })
  const laneOf = (g: string) => (lanes.restSet.has(g) ? lanes.names.length - 1 : lanes.names.indexOf(g))
  const maxByLane = $derived.by(() => {
    const m = new Array(lanes.names.length).fill(1)
    for (const o of visible) { const l = laneOf(o.grp); if (o.n > m[l]) m[l] = o.n }
    return m
  })
  const height = $derived(top + lanes.names.length * (rowH + gap) + 26)

  // Graduations
  const ticks = $derived.by(() => {
    const { lo, hi, log } = view
    if (log) {
      const out: number[] = []
      for (let e = -1; e <= 5; e++) { const v = 10 ** e; if (v >= lo && v <= hi) out.push(v) }
      // Sur écran étroit, une décade sur deux pour éviter que les libellés se touchent.
      return iw < 340 ? out.filter((_, k) => k % 2 === 0) : out
    }
    const span = hi - lo
    const step = [10, 20, 50, 100, 200, 250, 500, 1000].find((s) => span / s <= (width < 420 ? 4 : 7)) ?? 1000
    const out: number[] = []
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(v)
    return out
  })
  const fLabel = (f: number) => (f >= 1000 ? `${+(f / 1000).toFixed(2)} GHz` : f < 1 ? `${+(f * 1000).toFixed(0)} kHz` : `${+f.toFixed(1)} MHz`)
  const fRange = (o: Occupation) => {
    const big = o.f1 >= 10000
    const k = big ? 1000 : 1
    const u = big ? 'GHz' : 'MHz'
    const n = (v: number) => (v / k).toLocaleString('fr-FR', { useGrouping: false, maximumFractionDigits: big ? 3 : 4 })
    return o.f0 === o.f1 ? `${n(o.f0)} ${u}` : `${n(o.f0)}–${n(o.f1)} ${u}`
  }

  let hover = $state<Occupation | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function move(e: PointerEvent, o: Occupation) {
    const r = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - r.left, y: e.clientY - r.top }
    hover = o
  }

  const cols: Column<Occupation>[] = [
    { key: 'f0', label: 'Fréquences', numeric: true, format: (_, r) => fRange(r) },
    { key: 'sys', label: 'Système' },
    { key: 'grp', label: 'Exploitant' },
    { key: 'n', label: 'Supports', numeric: true },
  ]
</script>

<div class="spectrum">
  <div class="views" role="radiogroup" aria-label="Plage de fréquences">
    {#each VIEWS as v (v.id)}
      <button type="button" role="radio" aria-checked={viewId === v.id} onclick={() => (viewId = v.id)}>{v.label}</button>
    {/each}
  </div>

  {#if !visible.length}
    <p class="empty">Aucune bande déclarée dans cette plage pour la sélection.</p>
  {:else}
    <figure bind:clientWidth={width}>
      <div class="plot">
        <svg {width} {height} role="img" aria-label="Occupation du spectre par exploitant, {view.label}">
          <g transform="translate({labelW},0)">
            {#if view.log}
              {#each ITU_BANDS as [name, lo, hi], k}
                {#if hi > view.lo && lo < view.hi}
                  <rect x={x(lo)} y={top - 4} width={Math.max(0, x(hi) - x(lo))} height={height - top - 22} class="itu" class:alt={k % 2 === 1} />
                  <text x={(x(Math.max(lo, view.lo)) + x(Math.min(hi, view.hi))) / 2} y="12" text-anchor="middle" class="itul">{name}</text>
                {/if}
              {/each}
            {/if}
            {#each ticks as t}
              <line x1={x(t)} x2={x(t)} y1={top - 4} y2={height - 22} class="grid" />
              <text x={x(t)} y={height - 8} text-anchor="middle" class="axis">{fLabel(t)}</text>
            {/each}
            {#each visible as o (o.grp + o.sys + o.f0 + '-' + o.f1)}
              {@const l = laneOf(o.grp)}
              <rect x={x(o.f0)} y={top + l * (rowH + gap)} width={Math.max(2, x(o.f1) - x(o.f0))} height={rowH} rx="2"
                fill={color(o)} fill-opacity={0.3 + 0.7 * Math.sqrt(o.n / maxByLane[l])}
                class:dim={hover && hover !== o} role="presentation"
                onpointermove={(e) => move(e, o)} onpointerleave={() => (hover = null)} />
            {/each}
          </g>
          {#each lanes.names as name, l}
            <text x={labelW - 8} y={top + l * (rowH + gap) + rowH / 2} dy="0.32em" text-anchor="end" class="lane">
              {name === 'Bouygues Telecom' ? 'Bouygues' : name.length > 16 ? name.slice(0, 15) + '…' : name}
            </text>
          {/each}
        </svg>
        <Tooltip x={tip.x} y={tip.y} visible={hover !== null} {width}>
          {#if hover}
            <div class="t-head">{hover.grp}</div>
            <div class="t-row"><span class="t-val">{fRange(hover)}</span></div>
            <div class="t-row"><span class="t-lab">{hover.sys} · {fmt(hover.n)} support{hover.n > 1 ? 's' : ''}</span></div>
          {/if}
        </Tooltip>
      </div>
    </figure>
    <ul class="legend">
      {#each LEGEND as [label, bg]}<li><span class="sw" style:background={bg}></span>{label}</li>{/each}
    </ul>
    <p class="note">Plus une barre est opaque, plus elle est déclarée sur une grande part des supports de l'exploitant dans la sélection.</p>
    {#if table}
      <details>
        <summary>Tableau des {fmt(visible.length)} bandes</summary>
        <DataTable rows={visible} columns={cols} sortKey="f0" sortDesc={false} search={['sys', 'grp']}
          caption="bandes de fréquences" rowKey={(r) => `${r.grp}|${r.sys}|${r.f0}|${r.f1}`} limit={20} />
      </details>
    {/if}
  {/if}
</div>

<style>
  .spectrum { display: grid; gap: 10px; min-width: 0; }
  .views { display: flex; flex-wrap: wrap; gap: 5px; }
  .views button { padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line-strong); background: none; color: var(--text-2); cursor: pointer; font-size: 0.8rem; }
  .views button[aria-checked='true'] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 600; }
  figure { margin: 0; min-width: 0; }
  .plot { position: relative; }
  svg { display: block; overflow: visible; }
  .itu { fill: var(--surface-2); opacity: 0.35; }
  .itu.alt { opacity: 0.12; }
  .itul { fill: var(--muted); font-size: 10px; letter-spacing: 0.04em; }
  .grid { stroke: var(--line); }
  .axis { fill: var(--muted); font-size: 10.5px; font-variant-numeric: tabular-nums; }
  .lane { fill: var(--text-2); font-size: 11.5px; }
  rect[role='presentation'] { transition: opacity 120ms; }
  .dim { opacity: 0.35; }
  .legend { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 0.78rem; color: var(--text-2); }
  .legend li { display: flex; align-items: center; gap: 6px; }
  .sw { width: 14px; height: 9px; border-radius: 2px; }
  .note, .empty { color: var(--muted); font-size: 0.78rem; }
  details summary { cursor: pointer; font-size: 0.84rem; color: var(--text-2); margin-bottom: 8px; }
</style>
