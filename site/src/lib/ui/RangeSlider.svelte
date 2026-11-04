<script lang="ts">
  /**
   * Curseur à deux poignées. `value` vaut null quand toute la plage est sélectionnée (pas de filtre).
   * Échelle linéaire ou logarithmique (fréquences).
   */
  let { min, max, value = $bindable(), log = false, step = 1, format, label }: {
    min: number; max: number; value: [number, number] | null; log?: boolean; step?: number
    format: (v: number) => string; label: string
  } = $props()

  const N = 1000
  const toPos = (v: number) => Math.round(log ? (N * Math.log(v / min)) / Math.log(max / min) : (N * (v - min)) / (max - min))
  const fromPos = (p: number) => {
    const v = log ? min * Math.pow(max / min, p / N) : min + ((max - min) * p) / N
    return snap(v)
  }
  function snap(v: number) {
    if (!log) return Math.round(v / step) * step
    // Valeurs « rondes » à 2 chiffres significatifs sur l'échelle logarithmique.
    const e = Math.pow(10, Math.floor(Math.log10(v)) - 1)
    return Math.round(v / e) * e
  }

  const lo = $derived(value ? toPos(value[0]) : 0)
  const hi = $derived(value ? toPos(value[1]) : N)

  function set(a: number, b: number) {
    if (a > b) [a, b] = [b, a]
    value = a <= 0 && b >= N ? null : [fromPos(a), fromPos(b)]
  }
</script>

<div class="range" role="group" aria-label={label}>
  <div class="track">
    <div class="fill" style:left="{lo / 10}%" style:right="{100 - hi / 10}%"></div>
    <input type="range" min="0" max={N} value={lo} aria-label="{label} : minimum"
      oninput={(e) => set(+e.currentTarget.value, hi)} />
    <input type="range" min="0" max={N} value={hi} aria-label="{label} : maximum"
      oninput={(e) => set(lo, +e.currentTarget.value)} />
  </div>
  <div class="values num">
    <span>{format(value ? value[0] : min)}</span>
    <span>{format(value ? value[1] : max)}</span>
  </div>
</div>

<style>
  .range { display: grid; gap: 4px; }
  .track { position: relative; height: 22px; }
  .track::before { content: ''; position: absolute; left: 0; right: 0; top: 9px; height: 4px; border-radius: 2px; background: var(--line-strong); }
  .fill { position: absolute; top: 9px; height: 4px; border-radius: 2px; background: var(--accent); }
  input[type='range'] {
    position: absolute; inset: 0; width: 100%; margin: 0; background: none; pointer-events: none;
    -webkit-appearance: none; appearance: none; height: 22px;
  }
  input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none; pointer-events: auto; width: 16px; height: 16px; border-radius: 50%;
    background: var(--surface); border: 2px solid var(--accent); cursor: grab;
  }
  input[type='range']::-moz-range-thumb {
    pointer-events: auto; width: 14px; height: 14px; border-radius: 50%;
    background: var(--surface); border: 2px solid var(--accent); cursor: grab;
  }
  input[type='range']::-moz-range-track { background: none; }
  input[type='range']:focus-visible::-webkit-slider-thumb { outline: 2px solid var(--focus); outline-offset: 2px; }
  .values { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-2); }
</style>
