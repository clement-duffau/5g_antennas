<script lang="ts">
  import type { SupportIndex } from '../supports'
  import { communeOf } from '../supports'
  import type { Services } from '../services'
  import type { Zone } from '../filters'
  import { bearing, direction, distance, fmtDistance } from '../geo'
  import { GENERATIONS, MOBILE_OPS, opColor } from '../colors'
  import { fmt, fmt1 } from '../format'
  import ZoneSpectrum from '../charts/ZoneSpectrum.svelte'
  import { occupation } from '../spectrum'

  let { index, services, zone, mask, filtered, onselect, onradius, onclose }: {
    index: SupportIndex
    services: Services | null
    zone: Zone
    /** masque courant (zone + autres filtres) */
    mask: Uint8Array | null
    /** d'autres filtres que la zone sont actifs */
    filtered: boolean
    onselect: (i: number) => void
    onradius: (r: number) => void
    onclose: () => void
  } = $props()

  const RADII = [500, 1000, 2000, 5000, 10000]
  const opShort = (op: string) => (op === 'Bouygues Telecom' ? 'Bouygues' : op)

  // Distance de chaque support au centre (calcul unique par zone).
  const dist = $derived.by(() => {
    const d = new Float32Array(index.n)
    for (let i = 0; i < index.n; i++) d[i] = distance(zone.lat, zone.lon, index.lat[i], index.lon[i])
    return d
  })

  const inZone = $derived.by(() => {
    const out: number[] = []
    for (let i = 0; i < index.n; i++) if (dist[i] <= zone.r && (!mask || mask[i])) out.push(i)
    return out.sort((a, b) => dist[a] - dist[b])
  })

  /** Par opérateur mobile : site le plus proche, site 5G le plus proche, sites par génération dans le rayon. */
  const parOperateur = $derived.by(() => {
    if (!services) return null
    const grpIdx = MOBILE_OPS.map((op) => services.grps.findIndex((g) => g.nom === op))
    const genOf = services.syss.map((x) => (x.famille === 'Mobile' ? GENERATIONS.indexOf(x.generation as never) : -1))
    const res = MOBILE_OPS.map(() => ({ near: -1, near5g: -1, gens: [0, 0, 0, 0] }))
    for (let i = 0; i < index.n; i++) {
      const d = dist[i]
      let seen = 0 // bits (op * 4 + gen) déjà comptés pour ce support
      for (let r = services.start[i]; r < services.start[i + 1]; r++) {
        const k = grpIdx.indexOf(services.grp[r])
        if (k < 0) continue
        const g = genOf[services.sys[r]]
        if (g < 0) continue
        const o = res[k]
        if (o.near < 0 || d < dist[o.near]) o.near = i
        if (g === 3 && (o.near5g < 0 || d < dist[o.near5g])) o.near5g = i
        const bit = 1 << (k * 4 + g)
        if (d <= zone.r && !(seen & bit)) { seen |= bit; o.gens[g]++ }
      }
    }
    return res
  })

  const where = (i: number) => `${fmtDistance(dist[i])} ${direction(bearing(zone.lat, zone.lon, index.lat[i], index.lon[i]), true)}`

  let tab = $state<'resume' | 'spectre'>('resume')
  const occ = $derived.by(() => {
    if (!services || tab !== 'spectre') return []
    const m = new Uint8Array(index.n)
    for (const i of inZone) m[i] = 1
    return occupation(services, m, index.n)
  })

  let limit = $state(25)
  $effect(() => { void zone; limit = 25 })
</script>

<aside class="zone" aria-labelledby="zone-title">
  <header>
    <div>
      <p class="kicker">Autour de</p>
      <h2 id="zone-title">{zone.label}</h2>
    </div>
    <button class="close" type="button" onclick={onclose} aria-label="Effacer la zone">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    </button>
  </header>

  <div class="radii" role="radiogroup" aria-label="Rayon">
    {#each RADII as r}
      <button type="button" role="radio" aria-checked={zone.r === r} onclick={() => onradius(r)}>{fmtDistance(r)}</button>
    {/each}
  </div>

  <div class="tabs" role="tablist">
    <button role="tab" aria-selected={tab === 'resume'} onclick={() => (tab = 'resume')}>Résumé</button>
    <button role="tab" aria-selected={tab === 'spectre'} onclick={() => (tab = 'spectre')}>Spectre</button>
  </div>

  <p class="headline">
    <strong class="num">{fmt(inZone.length)}</strong> support{inZone.length > 1 ? 's' : ''} dans un rayon de {fmtDistance(zone.r)}{filtered ? ', selon les filtres actifs' : ''}.
  </p>

  {#if tab === 'spectre'}
    <section>
      <h3>Occupation des fréquences</h3>
      {#if services}
        <ZoneSpectrum {occ} compact />
      {:else}
        <p class="hint">Chargement des bandes…</p>
      {/if}
    </section>
  {:else}
  <section>
    <h3>Réseaux mobiles</h3>
    {#if parOperateur}
      <div class="scroller">
        <table>
          <thead>
            <tr><th>Opérateur</th><th>Site le plus proche</th><th>5G la plus proche</th>
              {#each GENERATIONS as g}<th class="numeric" title="Sites {g} dans le rayon">{g}</th>{/each}</tr>
          </thead>
          <tbody>
            {#each MOBILE_OPS as op, k}
              {@const o = parOperateur[k]}
              <tr>
                <th scope="row"><span class="dot" style:background={opColor(op)}></span>{opShort(op)}</th>
                <td>{#if o.near >= 0}<button class="lnk" onclick={() => onselect(o.near)}>{where(o.near)}</button>{:else}–{/if}</td>
                <td>{#if o.near5g >= 0}<button class="lnk" onclick={() => onselect(o.near5g)}>{where(o.near5g)}</button>{:else}–{/if}</td>
                {#each o.gens as n}<td class="numeric num" class:zero={!n}>{n || '·'}</td>{/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="hint">Distances à vol d'oiseau depuis le centre ; colonnes 2G à 5G : sites dans le rayon, tous filtres ignorés.</p>
    {:else}
      <p class="hint">Chargement des réseaux…</p>
    {/if}
  </section>

  <section>
    <h3>Supports, du plus proche au plus lointain</h3>
    {#if inZone.length}
      <ol class="list">
        {#each inZone.slice(0, limit) as i (i)}
          <li>
            <button type="button" onclick={() => onselect(i)}>
              <span class="d num">{where(i)}</span>
              <span class="main">
                <span class="t">{index.dict.nat[index.nat[i]] ?? 'Nature inconnue'}{Number.isNaN(index.h[i]) ? '' : ` · ${fmt1(index.h[i])} m`}</span>
                <span class="s">{communeOf(index, i)} · {fmt(index.emr[i])} émetteur{index.emr[i] > 1 ? 's' : ''}</span>
              </span>
              <span class="ops">
                {#each MOBILE_OPS as op, b}{#if index.ops[i] & (1 << b)}<span class="dot" style:background={opColor(op)} title={op}></span>{/if}{/each}
              </span>
            </button>
          </li>
        {/each}
      </ol>
      {#if inZone.length > limit}
        <button class="more" type="button" onclick={() => (limit += 50)}>Afficher 50 supports de plus ({fmt(inZone.length - limit)} restants)</button>
      {/if}
    {:else}
      <p class="hint">Aucun support dans ce rayon. Élargissez-le ou allégez les filtres.</p>
    {/if}
  </section>
  {/if}
</aside>

<style>
  .zone { padding: 18px 20px 28px; display: grid; gap: 16px; align-content: start; }
  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .kicker { color: var(--muted); font-size: 0.8rem; }
  h2 { font-size: 1.3rem; }
  h3 { font-size: 0.95rem; margin-bottom: 8px; }
  .close { background: none; border: 1px solid var(--line-strong); border-radius: var(--radius); width: 32px; height: 32px; display: grid; place-items: center; color: var(--text-2); cursor: pointer; flex: none; }
  .radii { display: flex; flex-wrap: wrap; gap: 6px; }
  .radii button { padding: 4px 12px; border-radius: 999px; border: 1px solid var(--line-strong); background: none; color: var(--text-2); cursor: pointer; font-size: 0.84rem; }
  .radii button[aria-checked='true'] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); font-weight: 600; }
  .headline { color: var(--text-2); }
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); }
  .tabs button { background: none; border: 0; padding: 6px 8px; color: var(--text-2); cursor: pointer; font-size: 0.9rem; border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tabs button[aria-selected='true'] { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
  .headline strong { color: var(--text); font-size: 1.25rem; font-weight: 640; }
  .scroller { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
  th, td { text-align: left; padding: 5px 8px 5px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
  thead th { color: var(--muted); font-weight: 500; font-size: 0.78rem; }
  tbody th { font-weight: 500; }
  .numeric { text-align: right; }
  .zero { color: var(--muted); }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; flex: none; }
  .lnk { background: none; border: 0; padding: 0; color: var(--accent); cursor: pointer; font: inherit; font-variant-numeric: tabular-nums; }
  .lnk:hover { text-decoration: underline; }
  .hint { color: var(--muted); font-size: 0.78rem; margin-top: 6px; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; }
  .list button {
    width: 100%; display: grid; grid-template-columns: 5.6rem 1fr auto; gap: 10px; align-items: center; text-align: left;
    background: none; border: 0; border-bottom: 1px solid var(--line); padding: 7px 2px; color: var(--text); cursor: pointer; font: inherit;
  }
  .list button:hover { background: var(--surface-2); }
  .d { color: var(--text-2); font-size: 0.84rem; }
  .main { display: grid; min-width: 0; }
  .t { font-size: 0.88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .s { font-size: 0.78rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ops { display: flex; }
  .ops .dot { margin: 0 0 0 3px; }
  .more { margin-top: 10px; background: none; border: 1px solid var(--line-strong); color: var(--text-2); padding: 6px 12px; border-radius: var(--radius); cursor: pointer; font-size: 0.84rem; }
</style>
