<script lang="ts">
  import { azimuts, clearAll, remove } from '../azimuts.svelte'
  import { AZ_LIMITS } from '../azimuthSelection'
  import { communeOf, depOf, inseeOf, type SupportIndex } from '../supports'
  import { MOBILE_OPS, opColor } from '../colors'
  import { fmtDistance } from '../geo'

  /** Réglages et liste des supports dont les azimuts sont affichés (visible dès qu'il y en a un). */
  let { index, onopen }: { index: SupportIndex; onopen: (i: number) => void } = $props()

  // Replié par défaut sur mobile, comme le panneau des filtres.
  let open = $state(typeof window === "undefined" || window.innerWidth > 720)
  const items = $derived(azimuts.list.map((e) => ({ e, i: index.byId.get(e.id) })).filter((x) => x.i !== undefined) as { e: (typeof azimuts.list)[number]; i: number }[])
  const opsOf = (i: number) => MOBILE_OPS.filter((_, b) => index.ops[i] & (1 << b))
</script>

<section class="az" aria-labelledby="az-title">
  <header>
    <button type="button" class="toggle" aria-expanded={open} onclick={() => (open = !open)}>
      <h2 id="az-title">Azimuts <span class="n">({items.length})</span></h2>
      <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" class:flip={!open}><path d="M6 15l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    </button>
    <button type="button" class="clr" onclick={clearAll}>Tout effacer</button>
  </header>

  {#if open}
    <label class="slider">
      <span>Longueur des cônes <strong class="num">{fmtDistance(azimuts.len)}</strong></span>
      <input type="range" min={AZ_LIMITS.len[0]} max={AZ_LIMITS.len[1]} step="100" bind:value={azimuts.len} />
    </label>
    <label class="slider">
      <span>Ouverture <strong class="num">{azimuts.ap}°</strong></span>
      <input type="range" min={AZ_LIMITS.ap[0]} max={AZ_LIMITS.ap[1]} step="5" bind:value={azimuts.ap} />
    </label>

    <ul class="list" aria-label="Supports affichés">
      {#each items as { e, i } (e.id)}
        <li>
          <button type="button" class="open" onclick={() => onopen(i)} title="Centrer la carte et ouvrir la fiche">
            <span class="id num">n° {e.id}</span>
            <span class="com">{communeOf(index, i)} ({depOf(inseeOf(index, i))}){e.rows ? ' · partiel' : ''}</span>
            <span class="ops">{#each opsOf(i) as op}<span class="dot" style:background={opColor(op)} title={op}></span>{/each}</span>
          </button>
          <button type="button" class="rm" onclick={() => remove(e.id)} aria-label="Retirer les azimuts du support n° {e.id}">
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
          </button>
        </li>
      {/each}
    </ul>

    <p class="note">
      Direction des antennes déclarée à l'ANFR. La longueur et l'ouverture sont indicatives et ne représentent pas une couverture réelle.
      Faisceaux hertziens : trait vers le support visé quand une liaison est identifiée (pointillés), sinon trait de longueur fixe.
    </p>
  {/if}
</section>

<style>
  .az {
    padding: 10px 12px; border-radius: 10px; background: color-mix(in srgb, var(--surface) 94%, transparent);
    border: 1px solid var(--line); box-shadow: 0 10px 30px rgb(0 0 0 / 0.2); display: grid; gap: 10px;
  }
  header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .toggle { display: flex; align-items: center; gap: 6px; background: none; border: 0; padding: 0; color: var(--text); cursor: pointer; }
  h2 { font-size: 0.92rem; font-stretch: 105%; }
  .n { color: var(--muted); font-weight: 400; }
  .flip { transform: rotate(180deg); }
  .clr { background: none; border: 0; color: var(--accent); cursor: pointer; font-size: 0.8rem; padding: 0; }
  .slider { display: grid; gap: 4px; font-size: 0.82rem; color: var(--text-2); }
  .slider span { display: flex; justify-content: space-between; }
  .slider strong { color: var(--text); font-weight: 600; }
  .slider input { accent-color: var(--accent); width: 100%; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; max-height: 180px; overflow-y: auto; }
  .list li { display: flex; align-items: center; gap: 4px; }
  .open {
    flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; background: none; border: 0; padding: 4px; border-radius: 4px;
    color: var(--text); cursor: pointer; font-size: 0.82rem; text-align: left;
  }
  .open:hover { background: var(--surface-2); }
  .id { color: var(--text-2); flex: none; }
  .com { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ops { display: flex; gap: 3px; flex: none; }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .rm { background: none; border: 1px solid transparent; border-radius: 4px; color: var(--text-2); width: 26px; height: 26px; display: grid; place-items: center; cursor: pointer; flex: none; }
  .rm:hover { color: var(--text); border-color: var(--line-strong); }
  .note { font-size: 0.74rem; color: var(--muted); }
</style>
