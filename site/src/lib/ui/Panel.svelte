<script lang="ts">
  import type { Snippet } from 'svelte'
  /** Bloc titré à l'intérieur d'une section (un graphique, un tableau). */
  let { title, note, children, wide = false }: { title: string; note?: string; children: Snippet; wide?: boolean } = $props()
</script>

<div class="panel" class:wide>
  <h3>{title}</h3>
  {#if note}<p class="note">{note}</p>{/if}
  <div class="body">{@render children()}</div>
</div>

<style>
  .panel { min-width: 0; display: flex; flex-direction: column; gap: 6px; }
  .wide { grid-column: 1 / -1; }
  .note { color: var(--muted); font-size: 0.85rem; }
  .body { margin-top: 10px; min-width: 0; }
</style>
