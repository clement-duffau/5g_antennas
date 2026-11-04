const nf = new Intl.NumberFormat('fr-FR')
const nf1 = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })
const nf2 = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })
const pct = new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 0 })
const compact = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 })

export const fmt = (n: number | null | undefined) => (n == null ? '–' : nf.format(n))
export const fmt1 = (n: number | null | undefined) => (n == null ? '–' : nf1.format(n))
export const fmt2 = (n: number | null | undefined) => (n == null ? '–' : nf2.format(n))
export const fmtPct = (n: number | null | undefined) => (n == null ? '–' : pct.format(n))
export const fmtCompact = (n: number) => (Math.abs(n) < 10000 ? nf.format(n) : compact.format(n))

/** Fréquence en MHz -> libellé lisible (kHz / MHz / GHz). */
export function fmtFreq(mhz: number): string {
  if (mhz < 1) return `${nf2.format(mhz * 1000)} kHz`
  if (mhz >= 1000) return `${nf2.format(mhz / 1000)} GHz`
  return `${nf1.format(mhz)} MHz`
}

const df = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
export const fmtDate = (iso: string | null | undefined) => (iso ? df.format(new Date(iso)) : '–')
