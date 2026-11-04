<script lang="ts" module>
  export interface Column<R> {
    key: keyof R & string
    label: string
    format?: (v: any, row: R) => string
    numeric?: boolean
    /** Affiche une mini-barre proportionnelle (colonnes numériques). */
    bar?: boolean
    title?: string
  }
</script>

<script lang="ts" generics="R extends Record<string, any>">
  import { fmt } from '../format'

  let {
    rows, columns, sortKey, sortDesc = true, limit = 15, search = [], caption, rowKey,
  }: {
    rows: R[]
    columns: Column<R>[]
    sortKey?: keyof R & string
    sortDesc?: boolean
    limit?: number
    search?: (keyof R & string)[]
    caption: string
    rowKey: (r: R) => string | number
  } = $props()

  // État de tri initialisé une fois depuis les props, puis piloté par l'utilisateur.
  let key = $state<string | undefined>(undefined)
  let desc = $state(true)
  $effect.pre(() => {
    if (key === undefined) { key = sortKey; desc = sortDesc }
  })
  let query = $state('')
  let expanded = $state(false)

  const norm = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()

  const filtered = $derived.by(() => {
    const q = norm(query.trim())
    const base = q ? rows.filter((r) => search.some((k) => norm(String(r[k] ?? '')).includes(q))) : rows
    if (!key) return base
    const k = key
    return [...base].sort((a, b) => {
      const va = a[k], vb = b[k]
      if (va == null) return 1
      if (vb == null) return -1
      const c = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb), 'fr')
      return desc ? -c : c
    })
  })
  const shown = $derived(expanded ? filtered : filtered.slice(0, limit))
  const maxes = $derived(
    Object.fromEntries(columns.filter((c) => c.bar).map((c) => [c.key, Math.max(1e-9, ...rows.map((r) => Number(r[c.key]) || 0))])),
  )

  function sortBy(k: string) {
    if (key === k) desc = !desc
    else { key = k; desc = true }
  }
</script>

<div class="table-wrap">
  {#if search.length}
    <label class="search">
      <span class="visually-hidden">Filtrer {caption}</span>
      <input type="search" placeholder="Filtrer…" bind:value={query} />
    </label>
  {/if}
  <div class="scroller">
    <table>
      <caption class="visually-hidden">{caption}</caption>
      <thead>
        <tr>
          {#each columns as c}
            <th class:numeric={c.numeric} aria-sort={key === c.key ? (desc ? 'descending' : 'ascending') : 'none'} title={c.title}>
              <button type="button" onclick={() => sortBy(c.key)}>
                {c.label}<span class="arrow" aria-hidden="true">{key === c.key ? (desc ? '↓' : '↑') : ''}</span>
              </button>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each shown as r (rowKey(r))}
          <tr>
            {#each columns as c}
              {@const v = r[c.key]}
              <td class:numeric={c.numeric} class="num">
                {#if c.bar}
                  <span class="cellbar" style:width="{(100 * (Number(v) || 0)) / maxes[c.key]}%"></span>
                {/if}
                <span class="cell">{c.format ? c.format(v, r) : c.numeric ? fmt(v) : (v ?? '–')}</span>
              </td>
            {/each}
          </tr>
        {:else}
          <tr><td colspan={columns.length} class="empty">Aucune ligne ne correspond à « {query} ».</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
  {#if filtered.length > limit}
    <button type="button" class="more" onclick={() => (expanded = !expanded)}>
      {expanded ? `Réduire à ${limit} lignes` : `Afficher les ${filtered.length} lignes`}
    </button>
  {/if}
</div>

<style>
  .table-wrap { min-width: 0; }
  .search input {
    width: min(100%, 260px);
    margin-bottom: 10px;
    padding: 7px 10px;
    border-radius: var(--radius);
    border: 1px solid var(--line-strong);
    background: var(--surface);
    color: var(--text);
    font: inherit;
    font-size: 0.9rem;
  }
  .scroller { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; }
  th { font-weight: 560; color: var(--text-2); position: sticky; top: 0; background: var(--surface); }
  th button { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
  th { vertical-align: bottom; }
  th button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  th[aria-sort='descending'], th[aria-sort='ascending'] { color: var(--text); }
  .arrow { width: 0.7em; color: var(--accent); }
  .numeric { text-align: right; }
  th.numeric button { flex-direction: row-reverse; }
  td { position: relative; }
  td.numeric .cell { position: relative; }
  .cellbar {
    position: absolute; right: 10px; bottom: 3px; height: 3px;
    max-width: calc(100% - 20px);
    background: var(--seq-3); opacity: 0.7; border-radius: 2px;
  }
  tbody tr:hover td { background: var(--surface-2); }
  .empty { color: var(--muted); text-align: center; padding: 16px; }
  .more {
    margin-top: 10px; background: none; border: 1px solid var(--line-strong); color: var(--text-2);
    padding: 6px 12px; border-radius: var(--radius); cursor: pointer; font-size: 0.85rem;
  }
  .more:hover { color: var(--text); border-color: var(--text-2); }
</style>
