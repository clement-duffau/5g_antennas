/**
 * Frise du déploiement à partir des dates de mise en service du parc actuel (table des services).
 * Mois codés comme dans l'index : 1 = janvier 1980, 0 = inconnu.
 */
import type { SupportIndex } from './supports'
import type { Services } from './services'

export interface Selection {
  /** opérateurs (groupes) ; vide = tous les opérateurs mobiles */
  ops: string[]
  /** génération ('2G'…'5G') ou null = toutes les générations mobiles */
  gen: string | null
  /** système ANFR précis (bande) ou null */
  sys: string | null
}

export const MOBILE = ['Orange', 'Bouygues Telecom', 'SFR', 'Free']

export const monthOf = (year: number, month = 1) => (year - 1980) * 12 + month
export const yearOf = (m: number) => 1980 + Math.floor((m - 1) / 12)
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
export const monthName = (m: number) => `${MOIS[(m - 1) % 12]} ${yearOf(m)}`
export const monthShort = (m: number) => `${String(((m - 1) % 12) + 1).padStart(2, '0')}/${yearOf(m)}`

function rowFilter(sv: Services, sel: Selection) {
  const ops = new Set(sel.ops.length ? sel.ops : MOBILE)
  const grpOk = Uint8Array.from(sv.grps, (g) => +ops.has(g.nom))
  const sysOk = Uint8Array.from(sv.syss, (x) =>
    +(x.famille === 'Mobile' && (!sel.gen || x.generation === sel.gen) && (!sel.sys || x.nom === sel.sys)))
  return { grpOk, sysOk }
}

/** Mois de première mise en service, par support, d'un service correspondant à la sélection (0 = aucun). */
export function firstMonths(idx: SupportIndex, sv: Services, sel: Selection): Uint16Array {
  const { grpOk, sysOk } = rowFilter(sv, sel)
  const out = new Uint16Array(idx.n)
  for (let i = 0; i < idx.n; i++) {
    let best = 0
    for (let r = sv.start[i], e = sv.start[i + 1]; r < e; r++) {
      if (!grpOk[sv.grp[r]] || !sysOk[sv.sys[r]]) continue
      const d = sv.d[r]
      if (d && (!best || d < best)) best = d
    }
    out[i] = best
  }
  return out
}

/** Nombre cumulé de sites en service à chaque mois [m0, m1], pour un opérateur. */
export function cumulative(idx: SupportIndex, sv: Services, sel: Selection, m0: number, m1: number): number[] {
  const fm = firstMonths(idx, sv, sel)
  const hist = new Array(m1 - m0 + 1).fill(0)
  let before = 0
  for (let i = 0; i < idx.n; i++) {
    const m = fm[i]
    if (!m || m > m1) continue
    if (m < m0) before++
    else hist[m - m0]++
  }
  let acc = before
  return hist.map((h) => (acc += h))
}

/** Sites sans date connue (exclus de la frise) pour la sélection. */
export function undated(idx: SupportIndex, sv: Services, sel: Selection): number {
  const { grpOk, sysOk } = rowFilter(sv, sel)
  let n = 0
  for (let i = 0; i < idx.n; i++) {
    let has = false, dated = false
    for (let r = sv.start[i], e = sv.start[i + 1]; r < e; r++) {
      if (!grpOk[sv.grp[r]] || !sysOk[sv.sys[r]]) continue
      has = true
      if (sv.d[r]) { dated = true; break }
    }
    if (has && !dated) n++
  }
  return n
}
