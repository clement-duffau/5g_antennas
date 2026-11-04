<script lang="ts">
  import maplibregl, { type GeoJSONSource } from 'maplibre-gl'
  import 'maplibre-gl/dist/maplibre-gl.css'
  import { onDestroy, onMount } from 'svelte'
  import type { SupportIndex } from '../supports'
  import { resolveColor } from '../categories'
  import { BASEMAPS, BOUNDS, fallbackStyle } from './basemap'

  /**
   * Carte animée : un support apparaît le mois de sa première mise en service (pour la sélection).
   * Les données ne changent qu'avec la sélection ; l'animation ne fait que déplacer un filtre.
   */
  let { index, months, current, color, theme }: {
    index: SupportIndex
    /** mois de 1re mise en service par support (0 = jamais) */
    months: Uint16Array
    current: number
    /** couleur CSS des sites déjà en service */
    color: string
    theme: 'dark' | 'light'
  } = $props()

  let container: HTMLDivElement
  let map: maplibregl.Map | undefined
  let ready = $state(false)
  let failed = false

  function data() {
    const feats = []
    for (let i = 0; i < index.n; i++) {
      const m = months[i]
      if (!m) continue
      feats.push({ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [index.lon[i], index.lat[i]] }, properties: { m } })
    }
    return { type: 'FeatureCollection' as const, features: feats }
  }

  // Les 6 derniers mois ressortent : plus gros et dans la couleur d'accent.
  const RECENT = 6
  const oldFilter = (c: number) => ['<=', ['get', 'm'], c - RECENT] as unknown as maplibregl.FilterSpecification
  const newFilter = (c: number) =>
    ['all', ['<=', ['get', 'm'], c], ['>', ['get', 'm'], c - RECENT]] as unknown as maplibregl.FilterSpecification

  function addLayers() {
    if (!map) return
    map.addSource('tl', { type: 'geojson', data: data() })
    map.addLayer({
      id: 'tl-old', type: 'circle', source: 'tl', filter: oldFilter(current),
      paint: {
        'circle-color': resolveColor(color),
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 1.2, 8, 2.6, 12, 4.5],
        'circle-opacity': 0.7,
      },
    })
    map.addLayer({
      id: 'tl-new', type: 'circle', source: 'tl', filter: newFilter(current),
      paint: {
        'circle-color': resolveColor('var(--cat-3)'),
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 2.2, 8, 4, 12, 6.5],
        'circle-stroke-color': resolveColor('var(--surface)'),
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 5, 0, 9, 1],
        'circle-opacity': 0.95,
      },
    })
    ready = true
  }

  onMount(() => {
    map = new maplibregl.Map({
      container, style: BASEMAPS[theme], center: [2.45, 46.6], zoom: 4.9, minZoom: 4, maxZoom: 14,
      maxBounds: BOUNDS, attributionControl: { compact: true }, dragRotate: false, pitchWithRotate: false,
    })
    map.touchZoomRotate.disableRotation()
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('style.load', addLayers)
    const timer = setTimeout(() => { if (!map?.isStyleLoaded() && !failed) { failed = true; map?.setStyle(fallbackStyle()) } }, 8000)
    map.on('error', () => { if (!ready && !failed) { failed = true; map?.setStyle(fallbackStyle()) } })
    map.on('load', () => clearTimeout(timer))
  })
  onDestroy(() => map?.remove())

  let lastTheme: string | undefined
  $effect(() => {
    const t = theme
    if (lastTheme !== undefined && t !== lastTheme && map) { ready = false; map.setStyle(failed ? fallbackStyle() : BASEMAPS[t]) }
    lastTheme = t
  })
  $effect(() => {
    void months
    if (!ready || !map) return
    ;(map.getSource('tl') as GeoJSONSource).setData(data())
  })
  $effect(() => {
    const c = current
    if (!ready || !map) return
    map.setFilter('tl-old', oldFilter(c))
    map.setFilter('tl-new', newFilter(c))
  })
  $effect(() => {
    const col = resolveColor(color)
    if (ready && map) map.setPaintProperty('tl-old', 'circle-color', col)
  })
</script>

<div class="map" bind:this={container}></div>

<style>
  .map { position: absolute; inset: 0; }
  :global(.maplibregl-ctrl-group) { background: var(--surface-2); border: 1px solid var(--line-strong); box-shadow: none; }
  :global(:root:not([data-theme='light']) .maplibregl-ctrl-icon) { filter: invert(1) hue-rotate(180deg); }
</style>
