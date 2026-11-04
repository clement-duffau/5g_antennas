<script lang="ts" module>
  export interface Place { label: string; lat: number; lon: number; kind: 'commune' | 'adresse' | 'position' }
</script>

<script lang="ts">
  import type { SupportIndex } from '../supports'

  /**
   * Recherche d'un lieu : communes (index local, instantané), adresses (géocodeur IGN Géoplateforme)
   * et position de l'appareil.
   */
  let { index, onpick }: { index: SupportIndex; onpick: (p: Place) => void } = $props()

  const GEOCODER = 'https://data.geopf.fr/geocodage/search'

  let query = $state('')
  let open = $state(false)
  let active = $state(0)
  let addresses = $state<Place[]>([])
  let addrError = $state(false)
  let locating = $state(false)
  let geoError = $state('')

  const norm = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').replace(/[-']/g, ' ').toLowerCase().trim()
  const communes = $derived.by(() => {
    const n = new Array(index.dict.com.length).fill(0)
    for (let i = 0; i < index.n; i++) n[index.com[i]]++
    return index.dict.com
      .map(([insee, nom, lat, lon], k) => ({ insee, nom, lat, lon, n: n[k], key: norm(nom) }))
      .filter((c) => c.lat != null && c.lon != null)
  })

  const communeHits = $derived.by((): Place[] => {
    const q = norm(query)
    if (q.length < 2 || /\d/.test(q)) return []
    const rank = (c: { key: string }) => (c.key === q ? 0 : c.key.startsWith(q) ? 1 : c.key.includes(q) ? 2 : 3)
    return communes.filter((c) => rank(c) < 3).sort((a, b) => rank(a) - rank(b) || b.n - a.n).slice(0, 4)
      .map((c) => ({ label: `${c.nom} (${c.insee.slice(0, 2)})`, lat: c.lat!, lon: c.lon!, kind: 'commune' as const }))
  })

  // Adresses : requête au géocodeur après une courte pause de frappe.
  let timer: ReturnType<typeof setTimeout> | undefined
  let seq = 0
  $effect(() => {
    const q = query.trim()
    clearTimeout(timer)
    addresses = []
    addrError = false
    if (q.length < 4) return
    const my = ++seq
    timer = setTimeout(async () => {
      try {
        const r = await fetch(`${GEOCODER}?q=${encodeURIComponent(q)}&limit=5&autocomplete=1&index=address`)
        if (!r.ok) throw new Error(String(r.status))
        const js = await r.json()
        if (my !== seq) return
        addresses = (js.features ?? [])
          .filter((f: any) => f.properties?.type !== 'municipality' || !communeHits.length)
          .map((f: any) => ({
            label: f.properties.label as string,
            lon: f.geometry.coordinates[0] as number,
            lat: f.geometry.coordinates[1] as number,
            kind: 'adresse' as const,
          }))
      } catch {
        if (my === seq) addrError = true
      }
    }, 280)
  })

  const options = $derived([...communeHits, ...addresses])

  function pick(p: Place) {
    query = ''
    open = false
    onpick(p)
  }

  function locate() {
    geoError = ''
    if (!navigator.geolocation) { geoError = 'Géolocalisation indisponible sur cet appareil.'; return }
    locating = true
    navigator.geolocation.getCurrentPosition(
      (pos) => { locating = false; pick({ label: 'Ma position', lat: pos.coords.latitude, lon: pos.coords.longitude, kind: 'position' }) },
      (err) => {
        locating = false
        geoError = err.code === err.PERMISSION_DENIED
          ? 'Accès à la position refusé : autorisez-le dans le navigateur ou cherchez une adresse.'
          : 'Position introuvable pour le moment : cherchez une adresse.'
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    )
  }

  function onkey(e: KeyboardEvent) {
    if (!options.length) return
    if (e.key === 'ArrowDown') { active = (active + 1) % options.length; e.preventDefault() }
    else if (e.key === 'ArrowUp') { active = (active - 1 + options.length) % options.length; e.preventDefault() }
    else if (e.key === 'Enter') { pick(options[Math.min(active, options.length - 1)]); e.preventDefault() }
    else if (e.key === 'Escape') open = false
  }
  $effect(() => { void options; active = 0 })
</script>

<div class="search">
  <div class="field">
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="2" /><path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    <input type="search" placeholder="Adresse ou commune…" bind:value={query}
      role="combobox" aria-expanded={open && options.length > 0} aria-controls="place-options" aria-autocomplete="list"
      aria-label="Chercher une adresse ou une commune"
      onfocus={() => (open = true)} onblur={() => setTimeout(() => (open = false), 150)} onkeydown={onkey} />
    <button type="button" class="locate" onclick={locate} disabled={locating} title="Utiliser ma position" aria-label="Utiliser ma position">
      <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    </button>
  </div>
  {#if open && (options.length || addrError) && query.trim().length >= 2}
    <ul id="place-options" class="options" role="listbox">
      {#each options as o, k (o.kind + o.label)}
        <li role="option" aria-selected={k === active}>
          <button type="button" class:active={k === active} onmousedown={() => pick(o)}>
            <span class="kind">{o.kind === 'commune' ? 'Commune' : 'Adresse'}</span>{o.label}
          </button>
        </li>
      {/each}
      {#if addrError}<li class="err">Recherche d'adresse indisponible ; les communes restent cherchables.</li>{/if}
    </ul>
  {/if}
  {#if geoError}<p class="err small">{geoError}</p>{/if}
</div>

<style>
  .search { position: relative; }
  .field {
    display: flex; align-items: center; gap: 8px; padding: 0 4px 0 10px; border-radius: var(--radius);
    border: 1px solid var(--line-strong); background: var(--surface); color: var(--muted);
    box-shadow: 0 6px 18px rgb(0 0 0 / 0.18);
  }
  .field:focus-within { border-color: var(--accent); }
  input { flex: 1; min-width: 0; border: 0; background: transparent; color: var(--text); font: inherit; font-size: 0.9rem; padding: 8px 0; outline: none; }
  .locate { background: none; border: 0; color: var(--text-2); width: 32px; height: 32px; display: grid; place-items: center; cursor: pointer; border-radius: 4px; }
  .locate:hover { color: var(--text); background: var(--surface-2); }
  .locate:disabled { opacity: 0.5; cursor: progress; }
  .options {
    position: absolute; z-index: 6; left: 0; right: 0; top: calc(100% + 4px); list-style: none; margin: 0; padding: 4px;
    background: var(--surface-2); border: 1px solid var(--line-strong); border-radius: var(--radius); box-shadow: 0 10px 24px rgb(0 0 0 / 0.3);
  }
  .options button {
    width: 100%; text-align: left; background: none; border: 0; padding: 6px 8px; border-radius: 4px; color: var(--text);
    cursor: pointer; font-size: 0.86rem; display: flex; gap: 8px; align-items: baseline;
  }
  .options button:hover, .options button.active { background: var(--surface); }
  .kind { color: var(--muted); font-size: 0.72rem; width: 4.6em; flex: none; }
  .err { color: var(--muted); font-size: 0.78rem; padding: 6px 8px; }
  .small { padding: 6px 2px 0; }
</style>
