<script lang="ts" module>
  /** Barres horizontales en liste : libellé, barre, valeur au bout. */
  export interface BarItem { label: string; value: number; color?: string; note?: string; href?: string }
</script>

<script lang="ts">
  import { fmt } from '../format'

  let { items, format = fmt, max, label }: {
    items: BarItem[]; format?: (n: number) => string; max?: number; label: string
  } = $props()

  const top = $derived(max ?? Math.max(1, ...items.map((d) => d.value)))
</script>

<ul class="bars" aria-label={label}>
  {#each items as d (d.label)}
    <li title="{d.label} : {format(d.value)}">
      <span class="lab">
        {#if d.href}<a href={d.href}>{d.label}</a>{:else}{d.label}{/if}
        {#if d.note}<small>{d.note}</small>{/if}
      </span>
      <span class="track">
        <span class="bar" style:width="calc((100% - 4.5rem) * {d.value / top})" style:background={d.color ?? 'var(--seq-3)'}></span>
        <span class="val num">{format(d.value)}</span>
      </span>
    </li>
  {/each}
</ul>

<style>
  .bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  li {
    display: grid;
    grid-template-columns: minmax(7rem, 38%) 1fr;
    align-items: center;
    gap: 12px;
    font-size: 0.9rem;
  }
  .lab { color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lab small { color: var(--muted); margin-left: 6px; font-size: 0.78rem; }
  .track { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .bar {
    display: block;
    height: 14px;
    min-width: 2px;
    border-radius: 0 4px 4px 0;
    flex: none;
  }
  .val { color: var(--text); font-size: 0.84rem; white-space: nowrap; }
  li:hover .lab { color: var(--text); }
  @media (max-width: 560px) { li { grid-template-columns: 1fr; gap: 2px; } }
</style>
