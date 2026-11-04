<script lang="ts" module>
  export interface CheckItem { value: string; label: string; count?: number; color?: string; note?: string }
</script>

<script lang="ts">
  import { fmt } from '../format'

  /** Liste de cases à cocher, filtrable par texte quand elle est longue. */
  let { items, selected = $bindable(), label, searchAt = 10, maxHeight = 220 }: {
    items: CheckItem[]; selected: string[]; label: string; searchAt?: number; maxHeight?: number
  } = $props()

  let query = $state('')
  const norm = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  const shown = $derived.by(() => {
    const q = norm(query.trim())
    const base = q ? items.filter((it) => norm(it.label).includes(q)) : items
    // Les éléments cochés restent en tête pour rester visibles.
    return [...base.filter((it) => selected.includes(it.value)), ...base.filter((it) => !selected.includes(it.value))]
  })

  function toggle(v: string) {
    selected = selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]
  }
</script>

<div class="checklist">
  {#if items.length >= searchAt}
    <input type="search" placeholder="Rechercher…" bind:value={query} aria-label="Rechercher dans {label}" />
  {/if}
  <ul style:max-height="{maxHeight}px" aria-label={label}>
    {#each shown as it (it.value)}
      <li>
        <label>
          <input type="checkbox" checked={selected.includes(it.value)} onchange={() => toggle(it.value)} />
          {#if it.color}<span class="dot" style:background={it.color}></span>{/if}
          <span class="lab">{it.label}{#if it.note}<small> {it.note}</small>{/if}</span>
          {#if it.count != null}<span class="n num">{fmt(it.count)}</span>{/if}
        </label>
      </li>
    {:else}
      <li class="empty">Aucun résultat.</li>
    {/each}
  </ul>
</div>

<style>
  .checklist { display: grid; gap: 6px; }
  input[type='search'] {
    font: inherit; font-size: 0.85rem; padding: 5px 8px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text);
  }
  ul { list-style: none; margin: 0; padding: 0; overflow-y: auto; overscroll-behavior: contain; }
  label { display: flex; align-items: center; gap: 8px; padding: 3px 4px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
  label:hover { background: var(--surface-2); }
  input[type='checkbox'] { accent-color: var(--accent); margin: 0; flex: none; }
  .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
  .lab { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lab small { color: var(--muted); }
  .n { color: var(--muted); font-size: 0.78rem; }
  .empty { color: var(--muted); font-size: 0.82rem; padding: 4px; }
</style>
