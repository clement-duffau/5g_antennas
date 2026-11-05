/**
 * Recherche de la liaison probable d'une antenne de faisceau hertzien (FH).
 *
 * Une antenne FH est directive : son azimut déclaré vise un autre support. On cherche, dans l'index des
 * supports, ceux qui sont dans l'axe (écart d'azimut ≤ 2°, distance ≤ 60 km), puis on classe :
 *   1. « retour » : le candidat porte du FH du même exploitant avec un azimut qui pointe vers l'origine (± 5°) ;
 *   2. « exploitant » : le candidat porte du FH du même exploitant, sans azimut retour trouvé ;
 * à niveau égal, le plus petit écart angulaire puis la plus courte distance. Un support dans l'axe sans FH
 * du même exploitant n'est pas retenu (presque toujours une coïncidence).
 *
 * Sur l'Ille-et-Vilaine, 93 % des antennes FH trouvent un candidat « retour », 6 % un candidat « exploitant ».
 */
import { angleDiff, bearing, distance } from './geo'

export interface Points { n: number; lat: ArrayLike<number>; lon: ArrayLike<number> }
export interface Candidate { i: number; dist: number; err: number }
export type LinkLevel = 'retour' | 'exploitant'
export interface Link extends Candidate { level: LinkLevel }

export const FH_DEFAULTS = { maxErr: 2, maxDist: 60000, minDist: 30, backTol: 5, shortlist: 6 }

/** Supports dans l'axe d'un azimut, triés par écart angulaire puis distance. `self` est exclu. */
export function candidatesInAxis(
  lat: number, lon: number, az: number, pts: Points, self = -1,
  { maxErr, maxDist, minDist } = FH_DEFAULTS,
): Candidate[] {
  const dLat = maxDist / 111320
  const dLon = maxDist / (111320 * Math.cos((lat * Math.PI) / 180))
  const out: Candidate[] = []
  for (let i = 0; i < pts.n; i++) {
    if (i === self) continue
    const la = pts.lat[i], lo = pts.lon[i]
    if (Math.abs(la - lat) > dLat || Math.abs(lo - lon) > dLon) continue
    const dist = distance(lat, lon, la, lo)
    if (dist > maxDist || dist < minDist) continue
    const err = Math.abs(angleDiff(az, bearing(lat, lon, la, lo)))
    if (err <= maxErr) out.push({ i, dist, err })
  }
  return out.sort((a, b) => a.err - b.err || a.dist - b.dist)
}

/** Vrai si l'un des azimuts du candidat vise l'origine, à `tol` degrés près. */
export function pointsBack(candLat: number, candLon: number, lat: number, lon: number, azimuths: number[], tol = FH_DEFAULTS.backTol): boolean {
  const back = bearing(candLat, candLon, lat, lon)
  return azimuths.some((a) => Math.abs(angleDiff(a, back)) <= tol)
}

export interface LinkContext {
  pts: Points
  /** le candidat porte-t-il du FH de cet exploitant ? (table des services, synchrone) */
  hasFh: (i: number, grp: string) => boolean
  /** azimuts FH de cet exploitant sur le candidat (fiches détaillées, chargées à la demande) */
  fhAzimuths: (i: number, grp: string) => Promise<number[]>
}

/** Meilleure liaison pour une antenne FH (support d'origine `self`), ou null. */
export async function findLink(self: number, az: number, grp: string, ctx: LinkContext, opts = FH_DEFAULTS): Promise<Link | null> {
  const lat = ctx.pts.lat[self], lon = ctx.pts.lon[self]
  const short = candidatesInAxis(lat, lon, az, ctx.pts, self, opts).filter((c) => ctx.hasFh(c.i, grp)).slice(0, opts.shortlist)
  if (!short.length) return null
  for (const c of short) {
    const azs = await ctx.fhAzimuths(c.i, grp)
    if (pointsBack(ctx.pts.lat[c.i], ctx.pts.lon[c.i], lat, lon, azs, opts.backTol)) return { ...c, level: 'retour' }
  }
  return { ...short[0], level: 'exploitant' }
}
