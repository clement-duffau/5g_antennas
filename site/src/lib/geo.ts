/** Petits calculs géographiques (sphère de rayon moyen terrestre). */
const R = 6371008.8
const rad = (d: number) => (d * Math.PI) / 180

/** Distance orthodromique en mètres. */
export function distance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)))
}

/** Azimut initial en degrés (0 = nord, sens horaire). */
export function bearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const y = Math.sin(rad(lon2 - lon1)) * Math.cos(rad(lat2))
  const x = Math.cos(rad(lat1)) * Math.sin(rad(lat2)) - Math.sin(rad(lat1)) * Math.cos(rad(lat2)) * Math.cos(rad(lon2 - lon1))
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360
}

const DIRS = ['nord', 'nord-est', 'est', 'sud-est', 'sud', 'sud-ouest', 'ouest', 'nord-ouest']
const DIRS_SHORT = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']
export const direction = (deg: number, short = false) => (short ? DIRS_SHORT : DIRS)[Math.round(deg / 45) % 8]

export function fmtDistance(m: number): string {
  if (m < 1000) return `${Math.round(m / 10) * 10} m`
  return `${(m / 1000).toLocaleString('fr-FR', { maximumFractionDigits: m < 10000 ? 1 : 0 })} km`
}

/** Polygone approximant un cercle (GeoJSON), pour dessiner la zone. */
export function circle(lat: number, lon: number, r: number, steps = 96): [number, number][] {
  const pts: [number, number][] = []
  for (let k = 0; k <= steps; k++) {
    const t = (2 * Math.PI * k) / steps
    const dLat = (r * Math.cos(t)) / 111320
    const dLon = (r * Math.sin(t)) / (111320 * Math.cos(rad(lat)))
    pts.push([lon + dLon, lat + dLat])
  }
  return pts
}

/** Écart angulaire signé le plus court de a vers b, en degrés, dans ]-180, 180]. */
export function angleDiff(a: number, b: number): number {
  const d = (((b - a) % 360) + 540) % 360 - 180
  return d === -180 ? 180 : d
}

/** Point atteint depuis (lat, lon) en suivant le cap `brg` (degrés) sur `dist` mètres (sphère). */
export function destination(lat: number, lon: number, brg: number, dist: number): [number, number] {
  const d = dist / R, t = rad(brg), p1 = rad(lat), l1 = rad(lon)
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(t))
  const l2 = l1 + Math.atan2(Math.sin(t) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2))
  return [(((l2 * 180) / Math.PI + 540) % 360) - 180, (p2 * 180) / Math.PI]
}

/**
 * Secteur circulaire (anneau GeoJSON fermé, [lon, lat]) : le centre, puis un arc de `steps` + 1 points
 * de az − ouverture/2 à az + ouverture/2, à `dist` mètres, puis retour au centre.
 */
export function sector(lat: number, lon: number, az: number, aperture: number, dist: number, steps = 24): [number, number][] {
  const ring: [number, number][] = [[lon, lat]]
  const a0 = az - aperture / 2
  for (let k = 0; k <= steps; k++) ring.push(destination(lat, lon, a0 + (aperture * k) / steps, dist))
  ring.push([lon, lat])
  return ring
}
