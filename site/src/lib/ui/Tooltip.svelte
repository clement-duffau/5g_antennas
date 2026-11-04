<script lang="ts">
  import type { Snippet } from 'svelte'

  /** Infobulle positionnée dans le conteneur (position: relative) du graphique. */
  let { x, y, visible, width = 0, children }: {
    x: number; y: number; visible: boolean; width?: number; children: Snippet
  } = $props()

  // Bascule à gauche du pointeur quand on approche du bord droit.
  const flip = $derived(width > 0 && x > width - 200)
</script>

{#if visible}
  <div class="tip" role="status" style:left="{x}px" style:top="{y}px" class:flip>
    {@render children()}
  </div>
{/if}

<style>
  .tip {
    position: absolute;
    z-index: 5;
    pointer-events: none;
    transform: translate(14px, -50%);
    min-width: 140px;
    max-width: 260px;
    padding: 8px 10px;
    background: var(--surface-2);
    border: 1px solid var(--line-strong);
    border-radius: var(--radius);
    box-shadow: 0 6px 20px rgb(0 0 0 / 0.28);
    font-size: 0.82rem;
    line-height: 1.35;
  }
  .flip { transform: translate(calc(-100% - 14px), -50%); }
  .tip :global(.t-head) { color: var(--text-2); margin-bottom: 4px; }
  .tip :global(.t-row) { display: flex; align-items: center; gap: 8px; }
  .tip :global(.t-key) { width: 12px; height: 2px; flex: none; border-radius: 1px; }
  .tip :global(.t-val) { font-weight: 640; font-variant-numeric: tabular-nums; }
  .tip :global(.t-lab) { color: var(--text-2); }
</style>
