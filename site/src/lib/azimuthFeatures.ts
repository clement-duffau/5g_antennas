/**
 * Entités GeoJSON des azimuts : une source pour tous les cônes, une pour les traits de faisceaux hertziens.
 */
import type { Feature, FeatureCollection, LineString, Polygon } from 'geojson'
import type { Beam } from './azimuthSelection'
import { destination, sector } from './geo'
import { MOBILE_OPS } from './colors'
import type { LinkLevel } from './fhLinks'

export interface PlacedBeam extends Beam { id: number; lat: number; lon: number }
export interface ResolvedLink { id: number; lat: number; lon: number; dist: number; level: LinkLevel }

/** Indice de couleur : 0-3 opérateurs mobiles (ordre de colors.ts), 4 autres exploitants. */
export const opIndex = (grp: string) => {
  const k = (MOBILE_OPS as readonly string[]).indexOf(grp)
  return k < 0 ? 4 : k
}
export const beamKey = (b: PlacedBeam) => `${b.id}|${b.grp}|${Math.round(b.az) % 360}`

export function coneFeatures(beams: PlacedBeam[], len: number, ap: number): FeatureCollection<Polygon> {
  return {
    type: 'FeatureCollection',
    features: beams.filter((b) => !b.fh).map((b): Feature<Polygon> => ({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [sector(b.lat, b.lon, b.az, ap, len)] },
      properties: { id: b.id, grp: b.grp, op: opIndex(b.grp), az: Math.round(b.az) },
    })),
  }
}

/**
 * Traits FH : jusqu'au support de la liaison trouvée (pointillés), sinon de longueur fixe `len`.
 * `links` : résultat de la recherche par clé de faisceau (absent = pas encore cherché, null = rien trouvé).
 */
export function fhFeatures(beams: PlacedBeam[], links: Map<string, ResolvedLink | null>, len: number): FeatureCollection<LineString> {
  return {
    type: 'FeatureCollection',
    features: beams.filter((b) => b.fh).map((b): Feature<LineString> => {
      const l = links.get(beamKey(b))
      const end: [number, number] = l ? [l.lon, l.lat] : destination(b.lat, b.lon, b.az, len)
      return {
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: [[b.lon, b.lat], end] },
        properties: {
          id: b.id, grp: b.grp, op: opIndex(b.grp), az: Math.round(b.az),
          kind: l ? 'lien' : 'fixe', level: l?.level ?? null, cible: l?.id ?? null, dist: l ? Math.round(l.dist) : null,
        },
      }
    }),
  }
}
