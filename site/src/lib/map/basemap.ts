/** Fond de carte partagé par les cartes du site : OpenFreeMap, repli sur les contours des départements. */
import type { StyleSpecification } from 'maplibre-gl'
import { resolveColor } from '../categories'

export const BASEMAPS = {
  dark: 'https://tiles.openfreemap.org/styles/dark',
  light: 'https://tiles.openfreemap.org/styles/positron',
} as const

/** Emprise autorisée : France métropolitaine et ses abords. */
export const BOUNDS: [[number, number], [number, number]] = [[-9.5, 39.5], [14, 53]]

export function fallbackStyle(): StyleSpecification {
  return {
    version: 8,
    glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
    sources: { deps: { type: 'geojson', data: `${import.meta.env.BASE_URL}data/departements.geojson` } },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': resolveColor('var(--page)') } },
      { id: 'deps-fill', type: 'fill', source: 'deps', paint: { 'fill-color': resolveColor('var(--surface)') } },
      { id: 'deps-line', type: 'line', source: 'deps', paint: { 'line-color': resolveColor('var(--line-strong)'), 'line-width': 0.8 } },
    ],
  }
}
