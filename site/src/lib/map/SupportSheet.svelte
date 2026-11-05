<script lang="ts">
  import { loadSupportDetail, type Station, type SupportDetail } from '../detail'
  import { depOf, inseeOf, type SupportIndex } from '../supports'
  import { fmt, fmt1, fmtDate } from '../format'
  import { MOBILE_OPS, opColor } from '../colors'
  import { drawableRows, rowKey } from '../azimuthSelection'
  import { globalState, rowChecked, setAll, toggleRow } from '../azimuts.svelte'

  let { index, i, onclose, onfocus, back = null }: {
    index: SupportIndex; i: number; onclose: () => void; onfocus: () => void
    /** retour à la liste de la zone, le cas échéant */
    back?: { label: string; go: () => void } | null
  } = $props()

  const id = $derived(index.id[i])
  const detail = $derived(loadSupportDetail(depOf(inseeOf(index, i)), id))

  const isMobileOp = (g: string) => (MOBILE_OPS as readonly string[]).includes(g)
  const stationColor = (st: Station) => (isMobileOp(st.grp) ? opColor(st.grp) : 'var(--cat-7)')

  function dms(v: number, pos: string, neg: string) {
    const a = Math.abs(v)
    const d = Math.floor(a), m = Math.floor((a - d) * 60), s = Math.round(((a - d) * 60 - m) * 60)
    return `${d}°${String(m).padStart(2, '0')}′${String(s).padStart(2, '0')}″ ${v >= 0 ? pos : neg}`
  }

  // Fréquences : MHz sous 10 GHz (usage radio), GHz au-delà, kHz en dessous de 1 MHz.
  const num = (x: number, d = 1) => x.toLocaleString('fr-FR', { useGrouping: false, maximumFractionDigits: d })
  function bands(b: [number, number][]) {
    if (!b.length) return '–'
    const max = Math.max(...b.map(([, z]) => z)), min = Math.min(...b.map(([a]) => a))
    const [k, unit, d] = max >= 10000 ? [1 / 1000, 'GHz', 3] : min < 1 ? [1000, 'kHz', 1] : [1, 'MHz', 1]
    const one = ([a, z]: [number, number]) => (a === z ? num(a * k, d) : `${num(a * k, d)}–${num(z * k, d)}`)
    return `${b.map(one).join(' · ')} ${unit}`
  }
  const year = (d: string | null) => (d ? d.slice(0, 4) : '–')

  /** Résumé par exploitant (pour l'en-tête) : nombre d'émetteurs. */
  function summary(d: SupportDetail) {
    const m = new Map<string, { grp: string; n: number; color: string }>()
    for (const st of d.st) {
      const cur = m.get(st.grp) ?? { grp: st.grp, n: 0, color: stationColor(st) }
      cur.n += st.emr.reduce((t, e) => t + e.n, 0)
      m.set(st.grp, cur)
    }
    return [...m.values()].sort((a, b) => b.n - a.n)
  }

  /** Antennes directionnelles pour le diagramme des azimuts. */
  function petals(d: SupportDetail) {
    const out: { az: number; color: string; grp: string }[] = []
    const seen = new Set<string>()
    // Sur un site d'opérateurs mobiles, on ne montre que leurs secteurs (les paraboles FH brouillent la lecture).
    const mobiles = d.st.filter((st) => isMobileOp(st.grp))
    for (const st of mobiles.length ? mobiles : d.st)
      for (const a of st.ant) {
        if (a.r !== 'D' || a.az == null) continue
        const key = `${st.grp}|${Math.round(a.az)}`
        if (seen.has(key)) continue
        seen.add(key)
        out.push({ az: a.az, color: stationColor(st), grp: st.grp })
      }
    return out
  }

  /** Azimuts des antennes utilisées par un groupe d'émetteurs. */
  function azimuts(st: Station, aers: number[]) {
    const az = aers
      .map((a) => st.ant.find((x) => x.id === a))
      .filter((a) => a && a.r === 'D' && a.az != null)
      .map((a) => `${Math.round(a!.az!)}°`)
    return [...new Set(az)].join(' ')
  }
</script>

<aside class="sheet" aria-labelledby="sheet-title">
  {#if back}
    <button type="button" class="back" onclick={back.go}>← {back.label}</button>
  {/if}
  <header>
    <div>
      <p class="kicker">Support n° {id}</p>
      <h2 id="sheet-title">{index.dict.com[index.com[i]][1]} <span class="dep">({depOf(inseeOf(index, i))})</span></h2>
    </div>
    <button class="close" type="button" onclick={onclose} aria-label="Fermer la fiche">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    </button>
  </header>

  {#await detail}
    <p class="muted">Chargement de la fiche…</p>
  {:then d}
    {#if !d}
      <p class="muted">Fiche introuvable pour ce support.</p>
    {:else}
      {@const p = petals(d)}
      {@const drawable = drawableRows(d).map((r) => r.key)}
      {@const gs = globalState(id)}
      {#if d.adr}<p class="adr">{d.adr}{d.cp ? `, ${d.cp}` : ''}</p>{/if}
      <dl class="facts">
        <div><dt>Nature</dt><dd>{d.nat ?? 'inconnue'}</dd></div>
        <div><dt>Hauteur</dt><dd>{d.h != null ? `${fmt1(d.h)} m` : 'inconnue'}</dd></div>
        <div><dt>Propriétaire</dt><dd>{d.tpo ?? 'inconnu'}</dd></div>
        <div><dt>Émetteurs</dt><dd class="num">{fmt(index.emr[i])}</dd></div>
        <div class="wide"><dt>Position</dt><dd class="num">{dms(d.lat, 'N', 'S')} · {dms(d.lon, 'E', 'O')}</dd></div>
      </dl>
      <p class="links">
        <button type="button" class="link" onclick={onfocus}>Centrer la carte</button>
        <a href="https://www.openstreetmap.org/?mlat={d.lat}&mlon={d.lon}#map=18/{d.lat}/{d.lon}" target="_blank" rel="noopener">OpenStreetMap</a>
        <a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={d.lat},{d.lon}" target="_blank" rel="noopener">Street View</a>
      </p>

      <div class="azctl">
        <label class:disabled={!drawable.length}>
          <input type="checkbox" disabled={!drawable.length} checked={gs === 'tout'} indeterminate={gs === 'partiel'}
            onchange={() => setAll(id, gs !== 'tout')} aria-describedby={drawable.length ? undefined : 'az-none'} />
          Afficher les azimuts sur la carte
        </label>
        {#if !drawable.length}
          <p id="az-none" class="muted small">Aucune antenne directionnelle avec azimut déclaré sur ce support.</p>
        {:else if gs === 'partiel'}
          <p class="muted small">Seules les lignes cochées ci-dessous sont affichées.</p>
        {/if}
      </div>

      <div class="overview">
        <ul class="who">
          {#each summary(d) as s (s.grp)}
            <li><span class="sw" style:background={s.color}></span>{s.grp}<span class="n num">{fmt(s.n)}</span></li>
          {/each}
        </ul>
        {#if p.length}
          <svg class="petals" viewBox="-60 -60 120 120" role="img" aria-label="Azimuts des antennes directionnelles">
            <circle r="46" class="ring" />
            <circle r="23" class="ring" />
            <text y="-50" text-anchor="middle" class="card">N</text>
            {#each p as a, k (k)}
              {@const r = (Math.PI / 180) * (a.az - 90)}
              {@const r0 = r - 0.11}
              {@const r1 = r + 0.11}
              <path d="M0,0 L{44 * Math.cos(r0)},{44 * Math.sin(r0)} A44,44 0 0 1 {44 * Math.cos(r1)},{44 * Math.sin(r1)} Z"
                fill={a.color} fill-opacity="0.75" stroke="var(--surface)" stroke-width="0.6">
                <title>{a.grp} : {Math.round(a.az)}°</title>
              </path>
            {/each}
          </svg>
        {/if}
      </div>

      {#each d.st as st (st.sta)}
        <section class="station">
          <h3>
            <span class="sw" style:background={stationColor(st)}></span>
            {st.grp}
            {#if st.exp !== st.grp}<span class="muted small">({st.exp})</span>{/if}
          </h3>
          <p class="meta">
            Station {st.sta} · implantée en {year(st.impl)}{st.serv ? ` · en service depuis ${fmtDate(st.serv)}` : ''}
            {#if st.mod} · modifiée le {fmtDate(st.mod)}{/if}
          </p>
          <div class="scroller">
            <table>
              <thead><tr><th><span class="visually-hidden">Afficher sur la carte</span></th><th>Système</th><th>Fréquences</th><th>Service</th><th>Azimuts</th></tr></thead>
              <tbody>
                {#each st.emr as e, k (k)}
                  {@const key = rowKey(st.sta, e.s)}
                  {@const can = drawable.includes(key)}
                  <tr>
                    <td class="chk">
                      <input type="checkbox" disabled={!can} checked={can && rowChecked(id, key)}
                        onchange={() => toggleRow(id, key, drawable)}
                        aria-label={can ? `Afficher sur la carte les azimuts ${e.s} de ${st.grp}` : `${e.s} : pas d'antenne directionnelle avec azimut`}
                        title={can ? 'Afficher ces secteurs sur la carte' : 'Pas d\'antenne directionnelle avec azimut'} />
                    </td>
                    <td class="sys">{e.s}{#if e.n > 1}<span class="muted small"> ×{e.n}</span>{/if}</td>
                    <td class="num">{bands(e.b)}</td>
                    <td class="num">{year(e.d)}</td>
                    <td class="num muted">{azimuts(st, e.a)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>
      {/each}
    {/if}
  {:catch err}
    <p class="muted">La fiche n'a pas pu être chargée ({err.message}).</p>
  {/await}
</aside>

<style>
  .sheet { padding: 18px 20px 28px; display: grid; gap: 14px; align-content: start; }
  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .kicker { color: var(--muted); font-size: 0.8rem; }
  .azctl { display: grid; gap: 4px; padding: 10px 12px; border-radius: var(--radius); background: var(--surface-2); }
  .azctl label { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; cursor: pointer; }
  .azctl label.disabled { color: var(--muted); cursor: default; }
  input[type='checkbox'] { accent-color: var(--accent); margin: 0; width: 16px; height: 16px; flex: none; }
  td.chk { width: 22px; padding-right: 6px; }
  .back { justify-self: start; background: none; border: 0; padding: 0; color: var(--accent); cursor: pointer; font-size: 0.85rem; }
  h2 { font-size: 1.35rem; }
  .dep { color: var(--muted); font-weight: 400; }
  .close { background: none; border: 1px solid var(--line-strong); border-radius: var(--radius); width: 32px; height: 32px; display: grid; place-items: center; color: var(--text-2); cursor: pointer; flex: none; }
  .close:hover { color: var(--text); }
  .adr { color: var(--text-2); font-size: 0.92rem; }
  .facts { margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; }
  .facts .wide { grid-column: 1 / -1; }
  dt { color: var(--muted); font-size: 0.78rem; }
  dd { margin: 0; font-size: 0.92rem; }
  .links { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.88rem; }
  .link { background: none; border: none; padding: 0; color: var(--accent); cursor: pointer; text-decoration: underline; text-underline-offset: 0.18em; font-size: inherit; }
  .overview { display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 12px 0; border-block: 1px solid var(--line); }
  .who { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: 0.88rem; flex: 1; min-width: 0; }
  .who li { display: flex; align-items: center; gap: 8px; }
  .who .n { margin-left: auto; color: var(--text-2); }
  .sw { width: 10px; height: 10px; border-radius: 2px; flex: none; display: inline-block; }
  .petals { width: 128px; height: 128px; flex: none; }
  .ring { fill: none; stroke: var(--line-strong); stroke-width: 0.6; }
  .card { fill: var(--muted); font-size: 8px; }
  .station { display: grid; gap: 4px; }
  h3 { display: flex; align-items: center; gap: 8px; font-size: 1rem; flex-wrap: wrap; }
  .meta { color: var(--muted); font-size: 0.8rem; }
  .scroller { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 4px; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 4px 8px 4px 0; border-bottom: 1px solid var(--line); }
  td { padding: 4px 8px 4px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
  td.sys { white-space: nowrap; }
  .muted { color: var(--muted); }
  .small { font-size: 0.8em; font-weight: 400; }
</style>
