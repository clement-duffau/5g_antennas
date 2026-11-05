<script lang="ts" module>
  export type DisplayMode = 'points' | 'groupes' | 'densite'
  export interface View { lon: number; lat: number; zoom: number }
</script>

<script lang="ts">
  import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from 'maplibre-gl'
  import 'maplibre-gl/dist/maplibre-gl.css'
  import { onDestroy, onMount } from 'svelte'
  import { communeOf, type SupportIndex } from '../supports'
  import { resolveColor, type ColorMode } from '../categories'
  import { fmt, fmt1 } from '../format'
  import { circle, fmtDistance } from '../geo'
  import { BASEMAPS, BOUNDS, fallbackStyle } from './basemap'
  import type { FeatureCollection } from 'geojson'
  import type { Zone } from '../filters'

  const EMPTY_FC: FeatureCollection = { type: 'FeatureCollection', features: [] }

  let {
    index, cats, colorMode, display, hidden, visible, selected, theme, view, onselect, onview, zone = null,
    azimuth = { cones: EMPTY_FC, fh: EMPTY_FC },
  }: {
    index: SupportIndex
    cats: Record<string, Uint8Array>
    colorMode: ColorMode
    display: DisplayMode
    /** catégories masquées (clés) du mode de coloration courant */
    hidden: number[]
    /** masque de visibilité issu des filtres (1 = affiché) ; null = tout */
    visible: Uint8Array | null
    selected: number | null
    theme: 'dark' | 'light'
    view: View
    onselect: (i: number | null) => void
    onview: (v: View) => void
    /** zone « autour de moi » dessinée sur la carte */
    zone?: Zone | null
    /** azimuts : cônes (secteurs) et traits de faisceaux hertziens */
    azimuth?: { cones: FeatureCollection; fh: FeatureCollection }
  } = $props()


  let container: HTMLDivElement
  let map: maplibregl.Map | undefined
  let popup: maplibregl.Popup | undefined
  let basemapFailed = $state(false)
  let ready = $state(false)

  // ------------------------------------------------------------------ données
  function features(withHidden = true) {
    const feats = []
    const prop = colorMode.prop
    const hid = new Set(hidden)
    for (let i = 0; i < index.n; i++) {
      if (visible && !visible[i]) continue
      if (!withHidden && hid.has(cats[prop][i])) continue
      feats.push({
        type: 'Feature' as const,
        id: i,
        geometry: { type: 'Point' as const, coordinates: [index.lon[i], index.lat[i]] },
        properties: { i, t: cats.t[i], o: cats.o[i], h: cats.h[i] },
      })
    }
    return { type: 'FeatureCollection' as const, features: feats }
  }

  function colorExpr(): maplibregl.ExpressionSpecification {
    const pairs = colorMode.categories.flatMap((c) => [c.key, resolveColor(c.color)])
    return ['match', ['get', colorMode.prop], ...pairs, '#888'] as unknown as maplibregl.ExpressionSpecification
  }
  const hiddenFilter = (): maplibregl.FilterSpecification =>
    ['!', ['in', ['get', colorMode.prop], ['literal', hidden]]] as unknown as maplibregl.FilterSpecification

  const radius: maplibregl.ExpressionSpecification = ['interpolate', ['linear'], ['zoom'], 4, 1.3, 7, 2.2, 10, 3.5, 13, 5.5, 16, 8]

  // ------------------------------------------------------------------ couches
  function addLayers() {
    if (!map) return
    const surface = resolveColor('var(--surface)')
    map.addSource('sup', { type: 'geojson', data: features(), promoteId: 'i' })
    map.addSource('sup-cl', {
      type: 'geojson', data: display === 'groupes' ? features(false) : { type: 'FeatureCollection', features: [] },
      cluster: true, clusterRadius: 46, clusterMaxZoom: 12,
    })

    map.addSource('zone', { type: 'geojson', data: zoneData() })
    map.addLayer({
      id: 'zone-fill', type: 'fill', source: 'zone', filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'fill-color': resolveColor('var(--accent)'), 'fill-opacity': 0.07 },
    })
    map.addLayer({
      id: 'zone-line', type: 'line', source: 'zone', filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'line-color': resolveColor('var(--accent)'), 'line-width': 1.5, 'line-dasharray': [3, 2] },
    })
    // Azimuts : sous les supports, sans gestionnaire de clic (ne gênent pas la sélection des supports).
    const opColorExpr = ['match', ['get', 'op'],
      0, resolveColor('var(--op-orange)'), 1, resolveColor('var(--op-bouygues)'),
      2, resolveColor('var(--op-sfr)'), 3, resolveColor('var(--op-free)'), resolveColor('var(--cat-7)'),
    ] as unknown as maplibregl.ExpressionSpecification
    map.addSource('az-cones', { type: 'geojson', data: azimuth.cones })
    map.addSource('az-fh', { type: 'geojson', data: azimuth.fh })
    map.addLayer({ id: 'az-cone-fill', type: 'fill', source: 'az-cones', paint: { 'fill-color': opColorExpr, 'fill-opacity': 0.2 } })
    map.addLayer({
      id: 'az-cone-line', type: 'line', source: 'az-cones',
      paint: { 'line-color': opColorExpr, 'line-width': 0.8, 'line-opacity': 0.85 },
    })
    map.addLayer({
      id: 'az-fh-line', type: 'line', source: 'az-fh', filter: ['==', ['get', 'kind'], 'fixe'],
      paint: { 'line-color': opColorExpr, 'line-width': 1.6, 'line-opacity': 0.9 },
    })
    map.addLayer({
      id: 'az-fh-link', type: 'line', source: 'az-fh', filter: ['==', ['get', 'kind'], 'lien'],
      layout: { 'line-cap': 'round' },
      paint: { 'line-color': opColorExpr, 'line-width': 1.6, 'line-opacity': 0.95, 'line-dasharray': [2, 2] },
    })
    // Zone de survol invisible et plus large que le trait, pour l'infobulle des faisceaux.
    map.addLayer({ id: 'az-fh-hit', type: 'line', source: 'az-fh', paint: { 'line-color': '#000', 'line-width': 12, 'line-opacity': 0 } })

    map.addLayer({
      id: 'sup-heat', type: 'heatmap', source: 'sup', maxzoom: 13,
      filter: hiddenFilter(),
      paint: {
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 4, 3, 7, 7, 10, 14, 13, 22],
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 4, 0.12, 7, 0.3, 10, 0.7, 13, 1.2],
        'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 10, 0.9, 13, 0],
        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(0,0,0,0)', 0.1, resolveColor('var(--seq-1)'), 0.3, resolveColor('var(--seq-2)'),
          0.55, resolveColor('var(--seq-3)'), 0.8, resolveColor('var(--seq-4)'), 1, resolveColor('var(--seq-5)')],
      },
    })
    map.addLayer({
      id: 'sup-points', type: 'circle', source: 'sup', filter: hiddenFilter(),
      paint: {
        'circle-color': colorExpr(),
        'circle-radius': radius,
        'circle-stroke-color': surface,
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 6, 0, 10, 0.8, 14, 1.5],
        'circle-opacity': 0.92,
      },
    })
    map.addLayer({
      id: 'cl-circles', type: 'circle', source: 'sup-cl', filter: ['has', 'point_count'],
      paint: {
        'circle-color': resolveColor('var(--seq-2)'),
        'circle-opacity': 0.85,
        'circle-radius': ['step', ['get', 'point_count'], 12, 50, 16, 250, 21, 1000, 27, 5000, 34],
        'circle-stroke-color': resolveColor('var(--seq-4)'),
        'circle-stroke-width': 1.5,
      },
    })
    map.addLayer({
      id: 'cl-count', type: 'symbol', source: 'sup-cl', filter: ['has', 'point_count'],
      layout: {
        'text-field': ['get', 'point_count_abbreviated'],
        'text-size': 11.5,
        'text-font': ['Noto Sans Regular'],
        'text-allow-overlap': true,
      },
      paint: { 'text-color': '#ffffff' },
    })
    map.addLayer({
      id: 'cl-points', type: 'circle', source: 'sup-cl', filter: ['!', ['has', 'point_count']],
      paint: { 'circle-color': colorExpr(), 'circle-radius': radius, 'circle-stroke-color': surface, 'circle-stroke-width': 1 },
    })
    map.addLayer({
      id: 'zone-center', type: 'circle', source: 'zone', filter: ['==', ['geometry-type'], 'Point'],
      paint: {
        'circle-radius': 6, 'circle-color': resolveColor('var(--accent)'),
        'circle-stroke-color': resolveColor('var(--surface)'), 'circle-stroke-width': 2.5,
      },
    })
    map.addLayer({
      id: 'sup-selected', type: 'circle', source: 'sup', filter: ['==', ['get', 'i'], selected ?? -1],
      paint: {
        'circle-color': 'rgba(0,0,0,0)',
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 6, 12, 10, 16, 14],
        'circle-stroke-color': resolveColor('var(--text)'),
        'circle-stroke-width': 2.5,
      },
    })
    applyDisplay()
    ready = true
    // Lien direct vers un support : on le garde visible à côté de la fiche.
    if (selected != null && !revealedOnce) { revealedOnce = true; reveal(selected) }
  }
  let revealedOnce = false

  function zoneData(): FeatureCollection {
    if (!zone) return { type: 'FeatureCollection', features: [] }
    return {
      type: 'FeatureCollection',
      features: [
        { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [circle(zone.lat, zone.lon, zone.r)] } },
        { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [zone.lon, zone.lat] } },
      ],
    }
  }

  /** Cadre la carte sur la zone (en laissant la place des panneaux). */
  export function fitZone() {
    if (!map || !zone) return
    const dLat = zone.r / 111320, dLon = zone.r / (111320 * Math.cos((zone.lat * Math.PI) / 180))
    const { clientWidth: w, clientHeight: h } = map.getContainer()
    const mobile = w <= 720
    map.fitBounds([[zone.lon - dLon, zone.lat - dLat], [zone.lon + dLon, zone.lat + dLat]], {
      padding: mobile ? { top: 120, bottom: h * 0.62 + 10, left: 16, right: 16 } : { top: 40, bottom: 40, left: 360, right: 480 },
      duration: 700,
    })
  }

  function applyDisplay() {
    if (!map?.getLayer('sup-points')) return
    const vis = (id: string, on: boolean) => map!.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none')
    vis('sup-heat', display === 'densite')
    vis('sup-points', display !== 'groupes')
    vis('cl-circles', display === 'groupes')
    vis('cl-count', display === 'groupes')
    vis('cl-points', display === 'groupes')
    // En mode densité, les points n'apparaissent qu'en zoomant.
    map.setPaintProperty('sup-points', 'circle-opacity',
      display === 'densite' ? ['interpolate', ['linear'], ['zoom'], 10, 0, 12, 0.92] : 0.92)
  }

  // ------------------------------------------------------------------ fond de carte
  function setBasemap() {
    if (!map) return
    ready = false
    map.setStyle(basemapFailed ? fallbackStyle() : BASEMAPS[theme], { diff: false })
  }

  // ------------------------------------------------------------------ interactions
  function hoverHtml(i: number): HTMLElement {
    const el = document.createElement('div')
    const t = document.createElement('strong')
    t.textContent = communeOf(index, i)
    const sub = document.createElement('div')
    const h = index.h[i]
    sub.textContent = [
      index.dict.nat[index.nat[i]] ?? 'Nature inconnue',
      Number.isNaN(h) ? null : `${fmt1(h)} m`,
      `${fmt(index.emr[i])} émetteur${index.emr[i] > 1 ? 's' : ''}`,
    ].filter(Boolean).join(' · ')
    const ops = document.createElement('div')
    ops.textContent = index.dict.ops.filter((_, b) => index.ops[i] & (1 << b)).join(', ')
    ops.className = 'pop-ops'
    el.append(t, sub, ops)
    return el
  }

  function onHover(e: MapLayerMouseEvent) {
    if (!map || !e.features?.length) return
    map.getCanvas().style.cursor = 'pointer'
    const i = e.features[0].properties.i as number
    if (window.matchMedia('(hover: none)').matches) return
    popup ??= new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, className: 'sup-pop' })
    popup.setLngLat([index.lon[i], index.lat[i]]).setDOMContent(hoverHtml(i)).addTo(map)
  }
  function onLeave() {
    if (!map) return
    map.getCanvas().style.cursor = ''
    popup?.remove()
  }

  interface FhProps { id: number; grp: string; az: number; kind: 'lien' | 'fixe'; level: string | null; cible: number | null; dist: number | null }
  let fhPopup: maplibregl.Popup | undefined
  function showFh(p: FhProps, at: maplibregl.LngLat) {
    if (!map) return
    const el = document.createElement('div')
    const t = document.createElement('strong')
    t.textContent = `${p.grp} · faisceau hertzien, ${p.az}°`
    const sub = document.createElement('div')
    sub.textContent = p.kind === 'lien'
      ? `Liaison ${p.level === 'retour' ? 'probable' : 'possible'} vers le support n° ${p.cible} (${fmtDistance(p.dist ?? 0)})`
      : 'Aucun support identifié dans l\'axe : trait de longueur fixe'
    el.append(t, sub)
    if (p.kind === 'lien' && p.level !== 'retour') {
      const n = document.createElement('div')
      n.className = 'pop-ops'
      n.textContent = 'Pas d\'azimut retour déclaré sur ce support.'
      el.append(n)
    }
    fhPopup ??= new maplibregl.Popup({ closeButton: false, closeOnClick: true, offset: 8, className: 'sup-pop' })
    fhPopup.setLngLat(at).setDOMContent(el).addTo(map)
  }

  onMount(() => {
    map = new maplibregl.Map({
      container,
      style: BASEMAPS[theme],
      center: [view.lon, view.lat],
      zoom: view.zoom,
      minZoom: 4,
      maxZoom: 18,
      maxBounds: BOUNDS,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
    })
    map.touchZoomRotate.disableRotation()
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: false } }), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')

    map.on('style.load', addLayers)
    // Si le fond de carte distant est inaccessible, on bascule sur les contours des départements.
    const failTimer = setTimeout(() => { if (!map?.isStyleLoaded() && !basemapFailed) { basemapFailed = true; setBasemap() } }, 8000)
    map.on('error', (e) => {
      if (!ready && !basemapFailed && !map?.getSource('sup')) {
        console.warn('Fond de carte indisponible, repli sur les contours :', e.error?.message)
        basemapFailed = true
        setBasemap()
      }
    })
    map.on('load', () => clearTimeout(failTimer))

    for (const layer of ['sup-points', 'cl-points']) {
      map.on('mousemove', layer, onHover)
      map.on('mouseleave', layer, onLeave)
      map.on('click', layer, (e) => {
        const f = e.features?.[0]
        if (f) onselect(f.properties.i as number)
      })
    }
    map.on('click', 'cl-circles', async (e) => {
      const f = e.features?.[0]
      if (!f || !map) return
      const src = map.getSource('sup-cl') as GeoJSONSource
      const z = await src.getClusterExpansionZoom(f.properties.cluster_id as number)
      map.easeTo({ center: (f.geometry as unknown as { coordinates: [number, number] }).coordinates, zoom: z + 0.3 })
    })
    map.on('mouseenter', 'cl-circles', () => { if (map) map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', 'cl-circles', () => { if (map) map.getCanvas().style.cursor = '' })
    map.on('mousemove', 'az-fh-hit', (e) => {
      if (!map || !e.features?.length) return
      if (map.queryRenderedFeatures(e.point, { layers: ['sup-points', 'cl-points'].filter((l) => map!.getLayer(l)) }).length) return
      map.getCanvas().style.cursor = 'help'
      showFh(e.features[0].properties as FhProps, e.lngLat)
    })
    map.on('mouseleave', 'az-fh-hit', () => { if (map) map.getCanvas().style.cursor = ''; fhPopup?.remove() })
    map.on('click', (e) => {
      const hits = map!.queryRenderedFeatures(e.point, { layers: ['sup-points', 'cl-points', 'cl-circles'].filter((l) => map!.getLayer(l)) })
      if (hits.length) return
      // Sur écran tactile, un appui sur un faisceau affiche son infobulle sans fermer la fiche.
      const fh = map!.getLayer('az-fh-hit') ? map!.queryRenderedFeatures(e.point, { layers: ['az-fh-hit'] }) : []
      if (fh.length) { showFh(fh[0].properties as FhProps, e.lngLat); return }
      onselect(null)
    })
    map.on('moveend', () => {
      const c = map!.getCenter()
      onview({ lon: +c.lng.toFixed(5), lat: +c.lat.toFixed(5), zoom: +map!.getZoom().toFixed(2) })
    })
  })

  onDestroy(() => map?.remove())

  // ------------------------------------------------------------------ réactions aux props
  let lastTheme: string | undefined
  $effect(() => {
    const t = theme
    if (lastTheme !== undefined && t !== lastTheme) setBasemap()
    lastTheme = t
  })
  $effect(() => {
    // couleur et catégories masquées
    const expr = colorExpr(), filt = hiddenFilter()
    if (!ready || !map) return
    map.setPaintProperty('sup-points', 'circle-color', expr)
    map.setPaintProperty('cl-points', 'circle-color', expr)
    map.setFilter('sup-points', filt)
    map.setFilter('sup-heat', filt)
  })
  $effect(() => {
    // données filtrées et regroupements
    void visible; void hidden; void colorMode
    if (!ready || !map) return
    ;(map.getSource('sup') as GeoJSONSource).setData(features())
    ;(map.getSource('sup-cl') as GeoJSONSource).setData(
      display === 'groupes' ? features(false) : { type: 'FeatureCollection', features: [] })
    applyDisplay()
  })
  let lastZone = ''
  $effect(() => {
    const key = zone ? `${zone.lat},${zone.lon},${zone.r}` : ''
    if (!ready || !map) return
    ;(map.getSource('zone') as GeoJSONSource | undefined)?.setData(zoneData())
    if (key && key !== lastZone) fitZone()
    lastZone = key
  })
  $effect(() => {
    const a = azimuth
    if (!ready || !map) return
    ;(map.getSource('az-cones') as GeoJSONSource | undefined)?.setData(a.cones)
    ;(map.getSource('az-fh') as GeoJSONSource | undefined)?.setData(a.fh)
  })
  $effect(() => {
    const sel = selected ?? -1
    if (!ready || !map) return
    map.setFilter('sup-selected', ['==', ['get', 'i'], sel])
  })

  /** Centre la carte sur un support (depuis la fiche ou l'URL). */
  export function focus(i: number, zoom = 15) {
    if (!map) return
    const { clientWidth: w, clientHeight: h } = map.getContainer()
    const mobile = w <= 720
    const offset: [number, number] = mobile ? [0, -h * 0.31] : [-Math.min(220, w / 4), 0]
    map.flyTo({ center: [index.lon[i], index.lat[i]], zoom: Math.max(zoom, map.getZoom()), offset, essential: true })
  }
  /**
   * Garde le support sélectionné visible à côté de la fiche : panneau à droite sur grand écran,
   * en bas sur mobile (62 % de la hauteur).
   */
  export function reveal(i: number) {
    if (!map) return
    const { clientWidth: w, clientHeight: h } = map.getContainer()
    const pt = map.project([index.lon[i], index.lat[i]])
    const mobile = w <= 720
    const visibleW = mobile ? w : w - Math.min(440, w)
    const visibleH = mobile ? h * 0.38 : h
    if (pt.x > 20 && pt.x < visibleW - 20 && pt.y > 20 && pt.y < visibleH - 20) return
    map.easeTo({ center: [index.lon[i], index.lat[i]], offset: [(visibleW - w) / 2, (visibleH - h) / 2], duration: 500 })
  }
  /** Cadre la carte sur les supports retenus (filtre de territoire). */
  export function fitMask(mask: Uint8Array) {
    if (!map) return
    let w = 180, e = -180, so = 90, no = -90, n = 0
    for (let i = 0; i < index.n; i++) {
      if (!mask[i]) continue
      n++
      const x = index.lon[i], y = index.lat[i]
      if (x < w) w = x
      if (x > e) e = x
      if (y < so) so = y
      if (y > no) no = y
    }
    if (!n) return
    const { clientWidth } = map.getContainer()
    const left = clientWidth > 720 ? 340 : 20
    map.fitBounds([[w, so], [e, no]], { padding: { top: 40, bottom: 40, left, right: 40 }, maxZoom: 14, duration: 700 })
  }
  export function flyTo(lon: number, lat: number, zoom: number) {
    map?.flyTo({ center: [lon, lat], zoom, essential: true })
  }
</script>

<div class="map" bind:this={container}></div>
{#if basemapFailed}
  <p class="fallback-note">Fond de carte indisponible : affichage des seuls contours des départements.</p>
{/if}

<style>
  .map { position: absolute; inset: 0; }
  .fallback-note {
    position: absolute; left: 50%; bottom: 8px; transform: translateX(-50%);
    background: var(--surface-2); color: var(--text-2); font-size: 0.78rem; padding: 4px 10px; border-radius: var(--radius);
    pointer-events: none; max-width: calc(100% - 24px);
  }
  :global(.sup-pop .maplibregl-popup-content) {
    background: var(--surface-2); color: var(--text); border: 1px solid var(--line-strong);
    border-radius: var(--radius); padding: 8px 10px; font: 13px/1.35 var(--font); box-shadow: 0 6px 20px rgb(0 0 0 / 0.3);
  }
  :global(.sup-pop .maplibregl-popup-tip) { display: none; }
  :global(.sup-pop .pop-ops) { color: var(--text-2); margin-top: 2px; }
  :global(.maplibregl-ctrl-group) { background: var(--surface-2); border: 1px solid var(--line-strong); box-shadow: none; }
  :global(.maplibregl-ctrl-group button + button) { border-top: 1px solid var(--line-strong); }
  :global(:root:not([data-theme='light']) .maplibregl-ctrl-icon) { filter: invert(1) hue-rotate(180deg); }
  :global(.maplibregl-ctrl-attrib) { background: color-mix(in srgb, var(--surface) 80%, transparent) !important; color: var(--text-2); }
  :global(.maplibregl-ctrl-attrib a) { color: var(--text-2); }
  :global(.maplibregl-ctrl-scale) { background: color-mix(in srgb, var(--surface) 70%, transparent); color: var(--text-2); border-color: var(--text-2); }
</style>
