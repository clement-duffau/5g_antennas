<script lang="ts">
  import { onMount } from 'svelte'
  import ZoneSpectrum from '../charts/ZoneSpectrum.svelte'
  import type { Occupation } from '../spectrum'
  import { fmt } from '../format'

  /** Fenêtre plein écran : spectre de la sélection courante de la carte. */
  let { occ, count, title, onclose }: { occ: Occupation[]; count: number; title: string; onclose: () => void } = $props()

  let dialog: HTMLDialogElement
  onMount(() => dialog.showModal())
</script>

<dialog bind:this={dialog} onclose={onclose} aria-labelledby="spectre-titre">
  <header>
    <div>
      <h2 id="spectre-titre">Spectre {title}</h2>
      <p>{fmt(count)} supports · {fmt(occ.length)} bandes déclarées</p>
    </div>
    <button type="button" class="close" onclick={() => dialog.close()} aria-label="Fermer">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    </button>
  </header>
  <ZoneSpectrum {occ} />
</dialog>

<style>
  dialog {
    width: min(1100px, calc(100vw - 24px)); max-height: calc(100dvh - 40px); padding: 20px 22px; border-radius: 12px;
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--text); overflow-y: auto;
  }
  dialog::backdrop { background: rgb(0 0 0 / 0.55); }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 14px; }
  h2 { font-size: 1.3rem; }
  header p { color: var(--muted); font-size: 0.86rem; margin-top: 4px; }
  .close { background: none; border: 1px solid var(--line-strong); border-radius: var(--radius); width: 32px; height: 32px; display: grid; place-items: center; color: var(--text-2); cursor: pointer; flex: none; }
</style>
