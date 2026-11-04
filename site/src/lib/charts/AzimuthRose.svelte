<script lang="ts">
  import Tooltip from '../ui/Tooltip.svelte'
  import { fmt } from '../format'

  /** Rose des azimuts : secteurs de 10°, rayon proportionnel à la racine du nombre (aire fidèle). */
  let { bins, size = 300 }: { bins: { de: number; antennes: number }[]; size?: number } = $props()

  const max = $derived(Math.max(1, ...bins.map((b) => b.antennes)))
  const R = $derived(size / 2 - 22)
  const c = $derived(size / 2)
  const rad = (deg: number) => ((deg - 90) * Math.PI) / 180 // 0° = nord, sens horaire

  function wedge(de: number, n: number) {
    const r = R * Math.sqrt(n / max)
    const a0 = rad(de + 0.6), a1 = rad(de + 9.4)
    return `M${c},${c}L${c + r * Math.cos(a0)},${c + r * Math.sin(a0)}A${r},${r} 0 0 1 ${c + r * Math.cos(a1)},${c + r * Math.sin(a1)}Z`
  }

  let hover = $state<{ de: number; antennes: number } | null>(null)
  let tip = $state({ x: 0, y: 0 })
  function move(e: PointerEvent, b: { de: number; antennes: number }) {
    const r = (e.currentTarget as SVGElement).ownerSVGElement!.getBoundingClientRect()
    tip = { x: e.clientX - r.left, y: e.clientY - r.top }
    hover = b
  }
</script>

<figure class="rose">
  <div class="plot">
    <svg width={size} height={size} viewBox="0 0 {size} {size}" role="img"
      aria-label="Répartition des azimuts des antennes directionnelles par secteur de 10 degrés">
      {#each [0.25, 0.5, 1] as t}
        <circle cx={c} cy={c} r={R * Math.sqrt(t)} class="ring" />
      {/each}
      {#each [['N', 0], ['E', 90], ['S', 180], ['O', 270]] as [lab, deg]}
        <text x={c + (R + 12) * Math.cos(rad(+deg))} y={c + (R + 12) * Math.sin(rad(+deg))}
          text-anchor="middle" dy="0.32em" class="card">{lab}</text>
      {/each}
      {#each bins as b (b.de)}
        <path d={wedge(b.de, b.antennes)} class="w" class:dim={hover && hover !== b} role="presentation"
          onpointermove={(e) => move(e, b)} onpointerleave={() => (hover = null)} />
      {/each}
    </svg>
    <Tooltip x={tip.x} y={tip.y} visible={hover !== null} width={size}>
      {#if hover}
        <div class="t-head">Azimut {hover.de}° – {hover.de + 10}°</div>
        <div class="t-row"><span class="t-val">{fmt(hover.antennes)}</span><span class="t-lab">antennes</span></div>
      {/if}
    </Tooltip>
  </div>
</figure>

<style>
  .rose { margin: 0; display: flex; justify-content: center; }
  .plot { position: relative; max-width: 100%; }
  svg { display: block; max-width: 100%; height: auto; overflow: visible; }
  .ring { fill: none; stroke: var(--line); }
  .card { fill: var(--muted); font-size: 11px; }
  .w { fill: var(--seq-3); stroke: var(--surface); stroke-width: 1; transition: opacity 120ms; }
  .dim { opacity: 0.4; }
</style>
