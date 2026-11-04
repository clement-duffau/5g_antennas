<script lang="ts">
  /** Groupe de boutons à choix unique (filtre local d'un graphique). */
  let { options, value = $bindable(), label }: {
    options: { value: string; label: string }[]; value: string; label: string
  } = $props()
</script>

<div class="chips" role="radiogroup" aria-label={label}>
  {#each options as o (o.value)}
    <button type="button" role="radio" aria-checked={value === o.value} onclick={() => (value = o.value)}>
      {o.label}
    </button>
  {/each}
</div>

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  button {
    padding: 5px 12px;
    border-radius: 999px;
    border: 1px solid var(--line-strong);
    background: transparent;
    color: var(--text-2);
    font-size: 0.85rem;
    cursor: pointer;
  }
  button:hover { color: var(--text); border-color: var(--text-2); }
  button[aria-checked='true'] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 600; }
</style>
