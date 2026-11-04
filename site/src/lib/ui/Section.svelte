<script lang="ts">
  import type { Snippet } from 'svelte'
  let { id, title, intro, children }: { id: string; title: string; intro?: string; children: Snippet } = $props()
</script>

<section {id} aria-labelledby="{id}-titre">
  <header>
    <h2 id="{id}-titre">{title}</h2>
    {#if intro}<p>{intro}</p>{/if}
  </header>
  {@render children()}
</section>

<style>
  section {
    padding-block: clamp(40px, 6vw, 72px);
    border-top: 1px solid var(--line);
    scroll-margin-top: 64px;
  }
  header { margin-bottom: 24px; display: grid; gap: 8px; }
  header p { color: var(--text-2); }
</style>
