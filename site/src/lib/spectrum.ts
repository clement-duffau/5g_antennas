/** Occupation du spectre d'une sélection de supports, à partir des bandes exactes de la table des services. */
import type { Services } from './services'

export interface Occupation {
  grp: string
  sys: string
  famille: string
  f0: number
  f1: number
  /** nombre de supports de la sélection où cette bande est déclarée */
  n: number
}

export function occupation(sv: Services, mask: Uint8Array | null, n: number): Occupation[] {
  const acc = new Map<string, Occupation>()
  for (let i = 0; i < n; i++) {
    if (mask && !mask[i]) continue
    for (let r = sv.start[i], e = sv.start[i + 1]; r < e; r++) {
      const g = sv.grp[r], x = sv.sys[r]
      for (const [f0, f1] of sv.bandes[sv.bs[r]]) {
        const key = `${g}|${x}|${f0}|${f1}`
        const o = acc.get(key)
        if (o) o.n++
        else acc.set(key, { grp: sv.grps[g].nom, sys: sv.syss[x].nom, famille: sv.syss[x].famille, f0, f1, n: 1 })
      }
    }
  }
  return [...acc.values()].sort((a, b) => a.f0 - b.f0 || a.f1 - b.f1)
}

export interface View { id: string; label: string; lo: number; hi: number; log: boolean }

/** Vues proposées : tout le spectre (log) et des zooms linéaires. */
export const VIEWS: View[] = [
  { id: 'tout', label: 'Tout', lo: 0.1, hi: 100000, log: true },
  { id: 'vhf-uhf', label: '30 MHz – 1 GHz', lo: 30, hi: 1000, log: false },
  { id: 'mobile', label: 'Mobile 0,7 – 3,8 GHz', lo: 690, hi: 3820, log: false },
  { id: 'fh', label: 'Faisceaux 1 – 90 GHz', lo: 1000, hi: 90000, log: true },
]

/** Bandes de l'UIT (pour l'axe logarithmique). */
export const ITU_BANDS: [string, number, number][] = [
  ['LF', 0.03, 0.3], ['MF', 0.3, 3], ['HF', 3, 30], ['VHF', 30, 300], ['UHF', 300, 3000], ['SHF', 3000, 30000], ['EHF', 30000, 300000],
]
